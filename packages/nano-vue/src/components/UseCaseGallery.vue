<script setup>
import { ref, onMounted, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useUseCaseActionStore } from '@/stores/useCaseActionStore';
import WorldInstance from '@/api/resources/WorldInstance';
import AppSettings from './AppSettings.vue';


const route = useRoute();
const router = useRouter();

const useCases = ref([]);
const currentUseCase = ref(
  route.params.use_case
    ? {
        use_case: route.params.use_case,
        world_definition: route.params.world_definition,
      }
    : null
);

const navigateToCurentUseCase = () => {
  router.push({
    name: "useCaseView",
    params: {
      use_case: currentUseCase.value.use_case,
      world_definition: currentUseCase.value.world_definition,
    },
  });
};

const fetchUseCases = async () => {
  try {
    const data = await WorldInstance.listUseCases();
    console.log("Use cases:", data)
    useCases.value = data.sort((a, b) => (a.use_case+a.world_definition).localeCompare(b.use_case+b.world_definition));
  } catch (error) {
    console.error("There was a problem reading use cases:", error);
  }
};

onMounted(fetchUseCases);

watch(route, (to) => {
  currentUseCase.value = {
    use_case: to.params.use_case,
    world_definition: to.params.world_definition,
  };
});

const useCaseActionsStore = useUseCaseActionStore();
const stopUseCase = () => {
  useCaseActionsStore.setPerformStopUseCaseAction(true);
}
const restartUseCase = () => {
  useCaseActionsStore.setPerformRestartUseCaseAction(true);
}
const downloadEventHistory = () => {
  useCaseActionsStore.setPerformDownloadUseCaseEventHistoryAction(true);
}
</script>

<template>
  <div class="h-screen flex flex-col">
    <div class="navbar">
      <div class="navbar-start space-x-4">
       
        <select id="use-case-select" class="select select-sm w-full max-w-xs"
          v-model="currentUseCase" @change="navigateToCurentUseCase">
          <option :value="null" disabled selected>Select a World</option>
          <option v-for="useCase in useCases" :key="useCase.use_case + useCase.world_definition" :value="useCase">{{ useCase.use_case + "/" + useCase.world_definition }}</option>
        </select>       

      </div>
      

      <div class="navbar-center space-x-4">
        <div class="join">
          <div class="tooltip tooltip-bottom" data-tip="Stop the current use case">
            <button class="btn btn-square btn-outline btn-sm btn-error join-item" @click="stopUseCase" :disabled="!currentUseCase">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-5 h-5">
                <path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
              </svg>
            </button>
          </div>
          
          <div class="tooltip tooltip-bottom" data-tip="Reload the use case">
            <button class="btn btn-square btn-outline btn-sm btn-success join-item" @click="restartUseCase" :disabled="!currentUseCase">
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6">
                <path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" />
              </svg>            
            </button>
          </div>

          <div class="tooltip tooltip-bottom" data-tip="Download the event history json">
            <button class="btn btn-square btn-outline btn-sm btn-info join-item" @click="downloadEventHistory" :disabled="!currentUseCase">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-5 h-5">
                <path fill-rule="evenodd" d="M10 3a.75.75 0 01.75.75v10.638l3.96-4.158a.75.75 0 111.08 1.04l-5.25 5.5a.75.75 0 01-1.08 0l-5.25-5.5a.75.75 0 111.08-1.04l3.96 4.158V3.75A.75.75 0 0110 3z" clip-rule="evenodd" />
              </svg>

            </button>
          </div>
        </div>  
      </div>

      <div class="navbar-end">
        <a class="btn btn-ghost normal-case text-xl" href="https://www.genworlds.com/">🧬🌍 GenWorlds</a>

        <button class="btn btn-square btn-ghost" onclick="settings_modal.showModal()">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-5 h-5">
            <path fill-rule="evenodd" d="M7.84 1.804A1 1 0 018.82 1h2.36a1 1 0 01.98.804l.331 1.652a6.993 6.993 0 011.929 1.115l1.598-.54a1 1 0 011.186.447l1.18 2.044a1 1 0 01-.205 1.251l-1.267 1.113a7.047 7.047 0 010 2.228l1.267 1.113a1 1 0 01.206 1.25l-1.18 2.045a1 1 0 01-1.187.447l-1.598-.54a6.993 6.993 0 01-1.929 1.115l-.33 1.652a1 1 0 01-.98.804H8.82a1 1 0 01-.98-.804l-.331-1.652a6.993 6.993 0 01-1.929-1.115l-1.598.54a1 1 0 01-1.186-.447l-1.18-2.044a1 1 0 01.205-1.251l1.267-1.114a7.05 7.05 0 010-2.227L1.821 7.773a1 1 0 01-.206-1.25l1.18-2.045a1 1 0 011.187-.447l1.598.54A6.993 6.993 0 017.51 3.456l.33-1.652zM10 13a3 3 0 100-6 3 3 0 000 6z" clip-rule="evenodd" />
          </svg>
        </button>
      </div>
    </div>
    <div class="flex-grow  min-h-0">
      <router-view />
    </div>
  </div>

  <AppSettings />
</template>


