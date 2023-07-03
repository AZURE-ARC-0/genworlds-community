from typing import List

from genworlds.worlds.base_world import BaseObject
from genworlds.objects.base_object import BaseObject
from use_cases.roundtable.events import (
    AgentReadsBlackboardEvent,
    AgentDeletesJobFromBlackboardEvent,
    AgentAddsJobToBlackboardEvent,
    BlackboardSendsContentEvent,
    UserAddsJobToBlackboardEvent,
)
from use_cases.roundtable.objects.job import Job


class Blackboard(BaseObject):
    content: List[Job] = []

    def __init__(
        self,
        name: str,
        description: str,
        id: str = None,
        websocket_url: str = "ws://127.0.0.1:7456/ws",
    ):
        super().__init__(
            name,
            description,
            id=id,
            websocket_url=websocket_url,
        )

        self.register_event_listeners(
            [
                (AgentReadsBlackboardEvent, self.agent_reads_blackboard_listener),
                (
                    AgentAddsJobToBlackboardEvent,
                    self.agent_adds_job_to_blackboard_listener,
                ),
                (
                    UserAddsJobToBlackboardEvent,
                    self.user_adds_job_to_blackboard_listener,
                ),
                (
                    AgentDeletesJobFromBlackboardEvent,
                    self.agent_deletes_job_from_blackboard_listener,
                ),
            ]
        )

    def _add_job(self, new_job: Job):
        self.content.append(new_job)

    def _delete_job(self, job_id: str):
        self.content = [job for job in self.content if job.id != job_id]

    def agent_reads_blackboard_listener(self, event: AgentReadsBlackboardEvent):
        print(f"Agent {event.sender_id} reads blackboard {self.id}.")
        self.send_event(
            BlackboardSendsContentEvent,
            target_id=event.sender_id,
            blackboard_content=self.content,
        )

    def agent_deletes_job_from_blackboard_listener(
        self, event: AgentDeletesJobFromBlackboardEvent
    ):
        self._delete_job(event.job_id)

    def agent_adds_job_to_blackboard_listener(
        self, event: AgentAddsJobToBlackboardEvent
    ):
        self._add_job(event.new_job)

    def user_adds_job_to_blackboard_listener(self, event: UserAddsJobToBlackboardEvent):
        self._add_job(event.new_job)
