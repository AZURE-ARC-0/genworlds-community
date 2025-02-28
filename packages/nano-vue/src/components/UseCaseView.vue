<script setup>
import ReconnectingWebSocket from 'reconnecting-websocket';
import { ref, watch, onMounted, onBeforeUnmount, computed, nextTick, defineProps } from 'vue';
import { useUseCaseActionStore } from '@/stores/useCaseActionStore';
import { useSettingsStore } from '@/stores/settingsStore';
import { useRoute } from 'vue-router';
import WorldInstance from '@/api/resources/WorldInstance';
import TTS from '@/api/resources/TTS';
import WorldDetails from './WorldDetails.vue';

const props = defineProps({
  use_case: {
    type: String,
    required: true,
  },
  world_definition: {
    type: String,
    required: true,
  },
})

const useCaseStarted = ref(false);
const activeScreen = ref('');
const screens = ref([]);
const yamlData = ref('');
const useCaseName = computed(() => yamlData.value ? yamlData.value.world_definition.world.name : '');
const websocketPort = ref(null);
const showAlert = ref(true);
const webSocket = ref(null);
const fullEventHistory = ref([]);
const activeScreenObject = computed(() => screens.value.find(screen => screen.name === activeScreen.value));
const shouldRenderIframe = computed(() => activeScreen.value === '16bit');
const iframeSrc = computed(() => {
    let tankId = "1234";
    if (window.location.pathname.endsWith("all_in_podcast.yaml")) {
        tankId = "1";
    }
    const protocol = window.location.protocol === 'https:' ? 'https' : 'http';
    const currentHostName = window.location.hostname;
    return `${protocol}://${currentHostName}:9000/16bit-front/?tankId=${tankId}`;
});

const settingsStore = useSettingsStore();

const loadUseCase = async (use_case, world_definition) => {
  console.log('Loading use case:', use_case, world_definition)

  useCaseStarted.value = true;

  stopTTS();
  
  // Fetch configuration from REST API
  const config = await fetchConfig(use_case, world_definition);
  // Set the screens
  screens.value = config.event_stream_config.screens;
  for (const screen of screens.value) {
    screen.event_history = [];
  }
  if (screens.value.length > 0) {
    activeScreen.value = screens.value[0].name;
  }

  // Set the YAML data
  yamlData.value = config.yaml_data;

  // Set the use case name
  useCaseName.value = config.event_stream_config.name;

  // Connect to WebSocket
  websocketPort.value = config.port;
  connectToWebSocket();
};

const findAgentById = (agentId) => {
  return yamlData.value.world_definition.world.agents.find(agent => agent.id === agentId);
};

// Chat events
const mod = (n, m) => {
  return ((n % m) + m) % m;
}

const message = ref("");
const showSuggestions = ref(false);
const suggestions = ref([]);
let availableAgents = ref([]);
let selectedAgent = ref("");

let availableEvents = ref([]);
let selectedEvent = ref("");

const focusedSuggestionIndex = ref(0);

const handleInput = () => {
  if (message.value.startsWith("/")) {
    // If agent and event are already selected, no need to show dropdown again
    if (selectedAgent.value && selectedEvent.value) {
      showSuggestions.value = false;
      return;
    }
    
    if (!selectedAgent.value) {
      // If agent is not selected, show agents suggestions
      suggestions.value = availableAgents.value;
    } else {
      // If agent is selected, show events suggestions
      // look for the speaking events of this agent
      suggestions.value = ["user_speaks_with_agent_event"]; // temporal
    }
    showSuggestions.value = true;
  } else {
    showSuggestions.value = false;
  }
};

const handleKeydown = (event) => {
  switch (event.key) {
    case 'ArrowUp':
      // prevent cursor from going to the start of textarea
      event.preventDefault();
      focusedSuggestionIndex.value = mod(focusedSuggestionIndex.value - 1, suggestions.value.length);
      break;
    case 'ArrowDown':
      // prevent cursor from going to the end of textarea
      event.preventDefault();
      focusedSuggestionIndex.value = mod(focusedSuggestionIndex.value + 1, suggestions.value.length);
      break;
    case 'Enter':
    case 'Tab':
      event.preventDefault();
      // 'Enter' selects the focused suggestion
      selectSuggestion(suggestions.value[focusedSuggestionIndex.value]);
      focusedSuggestionIndex.value = 0;
      break;
    case 'Backspace':
      // If there is no input and there is a selected event, remove the event.
      if (message.value === '' && selectedEvent.value) {
        removeEvent();
      }
      // If there is no input and no selected event, but there is a selected agent, remove the agent.
      else if (message.value === '' && !selectedEvent.value && selectedAgent.value) {
        removeAgent();
      }
      focusedSuggestionIndex.value = 0;
      break;
  }
};

const selectSuggestion = (item) => {
  if (!selectedAgent.value) {
    selectedAgent.value = item;
    // Clear the input message once the agent has been selected
    message.value = "";
  } else if (!selectedEvent.value) {
    selectedEvent.value = item;
    // Clear the input message once the event has been selected
    message.value = "";
  }
  showSuggestions.value = false;
};

const removeEvent = () => {
  selectedEvent.value = "";
};

const removeAgent = () => {
  selectedAgent.value = "";
};

// Text to speech
const ttsEventQueue = ref([]);
const ttsAudioPlayer = ref(null);
const ttsIsLoading = ref(false);
const processTTSQueue = async () => {
  // If already loading playing, do nothing
  if (ttsIsLoading.value || (ttsAudioPlayer.value && !ttsAudioPlayer.value.paused)) {
    console.log('Already playing');
    return;
  }

  if (ttsEventQueue.value.length > 0) {
    try {
      ttsIsLoading.value = true;
      const event = ttsEventQueue.value.shift();
      console.log('Playing TTS:', event.message);

      const blob = await loadEventTTS(event);   

      if (event.tts_cancelled) {
        console.log('TTS cancelled');
        return;
      }

      const audioSrc = URL.createObjectURL(blob);

      if (!ttsAudioPlayer.value) {
        ttsAudioPlayer.value = new Audio();
        ttsAudioPlayer.value.type = "audio/mpeg";
        ttsAudioPlayer.value.addEventListener('ended', () => {
          console.log('TTS ended');
          processTTSQueue();
        });
      }

      ttsAudioPlayer.value.src = audioSrc;
      ttsAudioPlayer.value.play();

      // Preload the next TTS
      if (ttsEventQueue.value.length > 0) {
        const nextEvent = ttsEventQueue.value[0];
        loadEventTTS(nextEvent);
      }

      ttsIsLoading.value = false;
    } catch (error) {
      console.error('Error playing TTS:', error);
      processTTSQueue();
    }
  }
};

const loadEventTTS = async (event) => {
  if (event.tts_promise) {
    console.log('Already loading TTS for this event', event.message);
    return event.tts_promise;
  }

  console.log('Loading TTS for event:', event.message);
  const agent = findAgentById(event.sender_id);
  const voiceId = agent.eleven_labs_voice_id || '21m00Tcm4TlvDq8ikWAM';
  
  event.tts_promise = TTS.convert(voiceId, event.message);   
  return event.tts_promise; 
}


const stopTTS = () => {
  // Empty the TTS queue and stop audio
  for (const event of ttsEventQueue.value) {
    event.tts_cancelled = true;
  }

  ttsEventQueue.value = [];
  if (ttsAudioPlayer.value)
    ttsAudioPlayer.value.pause();
    ttsAudioPlayer.value = null;
};

watch(() => settingsStore.settings.enableTTS, (newVal) => {
  if (!newVal) {
    stopTTS();
  }
}, { deep: true });

const sendMessage = () => {
  // Checking if necessary data is filled
  if (!selectedAgent.value || !selectedEvent.value || !message.value) {
    console.warn('Cannot send message: not all required fields are filled.');
    return;
  }

  const payload = JSON.stringify({
    event_type: "user_speaks_with_agent_event",
    description: "The user speaks with an agent",
    created_at: new Date().toISOString(),
    sender_id: "user_id",  // Replace with actual user id
    target_id: selectedAgent.value,
    message: message.value
  });

  // Sending the message through the WebSocket
  try {
    webSocket.value.send(payload);
  } catch (error) {
    console.error('Failed to send message:', error);
  }

  // Reset the message input and selected values
  message.value = "";
  selectedAgent.value = "";
  selectedEvent.value = "";
};

function removeDuplicates(arr) {
  return [...new Set(arr)];
}

// Websocket
const connectToWebSocket = () => {
  if (webSocket.value) {
    webSocket.value.close();
  }
  let wsProtocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
  const currentHost = window.location.hostname;
  let wsUrl;
  
  if (websocketPort.value == 7456) {
      wsUrl = `${wsProtocol}://${currentHost}:9000/real-ws/ws`;
  } else {
      wsUrl = `${wsProtocol}://${currentHost}:9000/mocked-ws/ws`;
  }
  webSocket.value = new ReconnectingWebSocket(wsUrl, [], {maxRetries: 0});

  webSocket.value.addEventListener('message', (msg) => {
    let socketEvent;
    console.log(typeof msg.data);
    if (typeof msg.data === 'object') {
      socketEvent = JSON.stringify(msg.data);
    } else {
      try {
        socketEvent = JSON.parse(msg.data);
      } catch (error) {
        console.error('Failed to parse message:', error);
        socketEvent = msg.data; // If parsing fails, set socketEvent to the original string.
      }
    }
    console.log('Received message:', socketEvent)

    fullEventHistory.value.push(socketEvent);
    
    // Check if the message contains all necessary data
    if (!socketEvent || socketEvent.event_type === null || socketEvent.event_type === undefined || socketEvent.created_at === null || socketEvent.created_at === undefined) {
        console.warn('Invalid message received:', msg.data);
        return; // Don't process this message
    } 

    // Check if the event type is 'world_sends_nearby_entities_event' and process entities
    if (socketEvent.event_type === 'world_sends_nearby_entities_event') {
      let events = [];
      socketEvent.nearby_entities.forEach(entity => {
        if (entity.entity_type === 'AGENT') {
          availableAgents.value.push(entity.id);
        }
      });

      // Update available agents and events
      availableEvents.value.push(...events);
      
      // Make sure the arrays you're passing to removeDuplicates are defined
      if (availableAgents.value) {
        availableAgents.value = removeDuplicates(availableAgents.value);
      }
      
      if (availableEvents.value) {
        availableEvents.value = removeDuplicates(availableEvents.value);
      }
    }

    // TTS
    if (settingsStore.settings.elevenLabsApiKey && settingsStore.settings.enableTTS && 'message' in socketEvent) {
      ttsEventQueue.value.push(socketEvent);

      // Preload the next TTS
      if (ttsEventQueue.value.length == 1) {
        const nextEvent = ttsEventQueue.value[0];
        loadEventTTS(nextEvent);
      }

      processTTSQueue();
    }

    for (const screen of screens.value) {
        for (const trackedEvent of screen.tracked_events) {
            if (trackedEvent.event_type === socketEvent.event_type) {
                const filteredEvent = {
                    event_type: socketEvent.event_type,
                    created_at: socketEvent.created_at,
                    sender_id: socketEvent.sender_id,
                }

                for (const field of trackedEvent.fields_to_display) {
                    filteredEvent[field.name] = socketEvent[field.name];
                }

                screen.event_history.push(filteredEvent);

                break;
              }
            }
        }
    });
};

// Auto scroll chat to bottom
const chatContainer = ref(null);
watch(() => activeScreenObject, async () => {
  await nextTick();

  if (chatContainer.value) {
    // Check if the user is near the bottom
    const isNearBottom =
      chatContainer.value.scrollHeight - chatContainer.value.scrollTop - chatContainer.value.clientHeight < 400;

    // Only scroll to the bottom if the user is near the bottom
    if (isNearBottom) {
      chatContainer.value.scrollTo({top: chatContainer.value.scrollHeight, behavior: 'instant'});
    }
  }      
}, { deep: true });

// Handle route changes
const route = useRoute();
watch(route, () => {
  useCaseStarted.value = false;
  stopUseCase();
});


// Handle API key changes
watch(() => settingsStore.settings.openaiApiKey, () => {
  useCaseStarted.value = false;
}, { deep: true });

onMounted(async () => {
  const _keyListener = function(e) {
      if (e.key === "s" && (e.ctrlKey || e.metaKey)) {
          e.preventDefault();

          downloadEventHistory();
      }
  };

  document.addEventListener('keydown', _keyListener);  

  onBeforeUnmount(() => {
    document.removeEventListener('keydown', _keyListener);
  });
});

const handleTabClick = (screenName) => {
  activeScreen.value = screenName;
};

const fetchConfig = async (use_case, world_definition) => {
  try {
    return WorldInstance.triggerUseCase(use_case, world_definition);
  } catch (error) {
    console.error('Error fetching config:', error);
  }
  return { screens: [], settings: {}, yamlData: '' };
};

const downloadEventHistory = () => {
  // Suppose this is your JSON object
  const data = {
    events: fullEventHistory.value,
  }

  // Convert it to JSON string
  const jsonStr = JSON.stringify(data, null, 2);

  // Create a Blob from the JSON string
  const blob = new Blob([jsonStr], { type: 'application/json' });

  // Create an object URL from the Blob
  const url = URL.createObjectURL(blob);

  // Create a link element
  const link = document.createElement('a');

  // Set the href and download attributes of the link
  link.href = url;
  link.download = 'websocket_event_history.json';

  // Append the link to the body
  document.body.appendChild(link);

  // Click the link to start the download
  link.click();

  // Remove the link after the download starts
  document.body.removeChild(link);
};

const getFieldValue = (event, fieldName) => {
  return fieldName in event ? event[fieldName] : '';
};

const getEventCssClasses = (event) => {
  const eventInfo = activeScreenObject.value.tracked_events.find((trackedEvent) => trackedEvent.event_type === event.event_type);
  return 'css_classes' in eventInfo ? eventInfo.css_classes : '';
};


// Handle use case actions
const useCaseActionsStore = useUseCaseActionStore();
const stopUseCase = async () => {
  console.log('Stopping use case');

  try {
    await WorldInstance.stopAllUseCases();
  } catch (error) {
    console.error('Error stopping use case:', error);
  }

  stopTTS();

  if (webSocket.value) {
    webSocket.value.close();
    webSocket.value = null;
  }
};


watch(() => useCaseActionsStore.performStopUseCaseAction, (newVal) => {
  if (newVal) {
    stopUseCase();
    useCaseActionsStore.setPerformStopUseCaseAction(false);
  }
});
watch(() => useCaseActionsStore.performRestartUseCaseAction, (newVal) => {
  if (newVal) {
    loadUseCase(props.use_case, props.world_definition);
    useCaseActionsStore.setPerformRestartUseCaseAction(false);
  }
});
watch(() => useCaseActionsStore.performDownloadUseCaseEventHistoryAction, (newVal) => {
  if (newVal) {
    downloadEventHistory();
    useCaseActionsStore.setPerformDownloadUseCaseEventHistoryAction(false);
  }
});
</script>

<template>
  <div v-if="!useCaseStarted" class="flex-1 mb-4 h-full w-full">
    <button @click="loadUseCase(props.use_case, props.world_definition)" class="btn btn-ghost btn-lg h-full w-full">
      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-32 h-32">
        <path stroke-linecap="round" stroke-linejoin="round" d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.348a1.125 1.125 0 010 1.971l-11.54 6.347a1.125 1.125 0 01-1.667-.985V5.653z" />
      </svg>
    </button>
  </div>
  <div v-else-if="screens.length > 0" class="p-4 flex flex-col h-full">
    <div v-if="showAlert && websocketPort == 7455" class="alert alert-warning mb-4">
      <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
      <p>
        You are currently connected to a simulated websocket server, 
        which means that the data you are seeing has been pre-recorded and is not live. 
        To initiate a real-time simulation, 
        please configure the <a class="link" onclick="settings_modal.showModal()">OpenAI API Key in the settings</a>
      </p>
      <button @click="showAlert = false" class="btn btn-sm">OK</button>
    </div>
    <h1 class="text-xl mb-4">{{ useCaseName }}</h1>
    <div class="tabs tabs-boxed mb-4">
      <button
        v-for="screen in screens"
        :key="screen.name"
        @click="handleTabClick(screen.name)"
        :class="{ 'tab-active': activeScreen === screen.name }"
        class="tab"
      >
        {{ screen.name }}
      </button>
      <button
        :key="'16bit'"
        @click="handleTabClick('16bit')"
        :class="{ 'tab-active': activeScreen === '16bit' }"
        class="tab"
      >
        16bit
      </button>
      <button
        :key="'world_details'"
        @click="handleTabClick('world_details')"
        :class="{ 'tab-active': activeScreen === 'world_details' }"
        class="tab"
      >
        World Details
      </button>
    </div>
    <div class="overflow-y-auto flex-1 mb-4" ref="chatContainer">
      <div v-if="shouldRenderIframe" class="w-full h-full">
          <iframe 
            :src="iframeSrc" 
            class="w-full h-full"
            frameborder="0"
            allow="autoplay; encrypted-media" 
            allowfullscreen
            >
          </iframe>
      </div>
      <div v-else-if="shouldRenderWorldDetails" class="w-full h-full">
        <WorldDetails :yamlData="yamlData" class="w-full h-full"/>
      </div>
      <div v-else>
        <div v-if="activeScreenObject" class="p-6 rounded-lg shadow-md">
            <ul class="space-y-4">
              <li v-for="(event, index) in activeScreenObject.event_history" :key="index">
                <div class="chat chat-start">
                  <div class="chat-header" >
                    From: {{ getFieldValue(event, 'sender_id') }}         
                    <template v-if="getFieldValue(event, 'target_id')">
                              To: {{ getFieldValue(event, 'target_id') }}
                    </template>
                    <time class="text-xs opacity-50">{{ getFieldValue(event, 'created_at') }}</time>
                  </div>
                  <div class="chat-bubble" :class="getEventCssClasses(event)">
                    <template v-if="getFieldValue(event, 'message')">
                      {{ getFieldValue(event, 'message') }}
                    </template>
                    <template v-else-if="getFieldValue(event, 'summary')">
                      {{ getFieldValue(event, 'summary') }}
                    </template>
                    <template v-else>
                      <pre class="overflow-x-auto"><code>{{ JSON.stringify(event, null, 2) }}</code></pre>
                    </template>
                  </div>
                  <div class="chat-footer">
                    <p class="text-xs opacity-50">Event Type: {{ getFieldValue(event, 'event_type') }}</p>
                  </div>
                </div>
              </li>
              <li class="pl-[12px]" v-if="webSocket">
                <span class="loading loading-dots loading-lg"></span>
              </li>
            </ul>
        </div>
      </div>
    </div>
    <div class="flex flex-col">
      <div class="flex relative items-end w-full">
    <div class="flex-grow bg-white shadow rounded p-2 flex items-center" 
         :class="{ 'cursor-not-allowed': websocketPort != 7455 }"
         :disabled="websocketPort != 7455">

        <!-- Render the selected agent as a badge -->
        <span class="bg-green-200 rounded-full px-3 py-1 text-sm font-semibold text-gray-700 mr-2" 
              v-if="selectedAgent">
          {{ selectedAgent }}
          <button @click="removeAgent()">x</button>
        </span>

        <!-- Render the selected event as a badge -->
        <span class="bg-blue-200 rounded-full px-3 py-1 text-sm font-semibold text-gray-700 mr-2" 
              v-if="selectedEvent">
          {{ selectedEvent }}
          <button @click="removeEvent()">x</button>
        </span>

      <!-- Only show input field when the textarea is not disabled -->
      <input v-show="websocketPort != 7455" 
             type="text" 
             class="flex-grow bg-transparent outline-none" 
             v-model="message" 
             @input="handleInput" 
             @keydown="handleKeydown"
             :placeholder="getPlaceholder">
    </div>
    
    <div class="absolute bg-white shadow rounded p-2 w-full" v-show="showSuggestions" style="bottom: 100%;">
      <div v-for="(item, index) in suggestions" 
           :key="index" 
           @click="selectSuggestion(item)" 
           :class="{ 'bg-gray-200': index === focusedSuggestionIndex }" 
           class="cursor-pointer hover:bg-gray-200">
        {{ item }}
      </div>
    </div>
    
    <button class="ml-2 bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded" 
            @click="sendMessage" 
            :disabled="websocketPort == 7455">
      Send
    </button>
  </div>
  </div>
  </div>

</template>

<style scoped>
[format*="bold"] {
  font-weight: bold;
}
</style>
