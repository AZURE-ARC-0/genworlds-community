import os
from dotenv import load_dotenv
import concurrent.futures


from genworlds.simulation.simulation import Simulation
from genworlds.agents.yeager_autogpt.agent import YeagerAutoGPT
from genworlds.worlds.world_2d.world_2d import World2D
from use_cases.roundtable.objects.microphone import Microphone

thread_pool_ref = concurrent.futures.ThreadPoolExecutor

load_dotenv(dotenv_path=".env")
openai_api_key = os.getenv("OPENAI_API_KEY")

ABS_PATH = os.path.dirname(os.path.abspath(__file__))

podcast_host = YeagerAutoGPT(
    id="maria",
    ai_name="Maria",
    description="The host of the podcast",
    goals=[
        (
            "Host an episode of the Roundtable podcast, discussing AI technology. \n",
            "Only the holder of the microphone can speak to the audience, if you don't have the microphone in your inventory, wait to receive it from the previous speaker. \n",
            "Don't repeat yourself, respond to questions and points made by other co-hosts to advance the conversation. \n",
            "Don't hog the microphone for a long time, make sure to give it to other participants. \n",
        )
    ],
    openai_api_key=openai_api_key,
    interesting_events={
        "agent_speaks_into_microphone",
        "agent_gives_object_to_agent_event",
    },
)

podcast_guest = YeagerAutoGPT(
    id="jimmy",
    ai_name="Jimmy",
    description="A co-host of the podcast",
    goals=[
        (
            "Participate an episode of the Roundtable podcast, discussing AI technology. \n",
            "Only the holder of the microphone can speak to the audience, if you don't have the microphone in your inventory, wait to receive it from the previous speaker. \n",
            "Don't repeat yourself, respond to questions and points made by other co-hosts to advance the conversation. \n",
            "Don't hog the microphone for a long time, make sure to give it to other participants. \n",
        )
    ],
    openai_api_key=openai_api_key,
    interesting_events={
        "agent_speaks_into_microphone",
        "agent_gives_object_to_agent_event",
    },
)


microphone = Microphone(
    id="microphone",
    name="Microphone",
    description="A podcast microphone that allows the holder of it to speak to the audience",
    host=podcast_host.id,
)


world = World2D(
    id="world",
    name="Roundtable",
    description="This is a podcast studio, where you record the Roundtable podcast. There is a microphone, and only the holder of the microphone can speak to the audience",
    locations=["roundtable"],
)

simulation = Simulation(
    name="Roundable",
    description="This is a podcast studio, where you record the Roundtable podcast. There is a microphone, and only the holder of the microphone can speak to the audience",
    world=world,
    objects=[
        (microphone, {"held_by": podcast_host.id}),
    ],
    agents=[
        (podcast_host, {"location": "roundtable"}),
        (podcast_guest, {"location": "roundtable"}),
    ],
)

# this attaches to the websocket all the objects and agents in the world
simulation.launch()
