from typing import Dict, Any
from openenv.core import EnvClient
from openenv.core.client_types import StepResult
from models import DevOpsAction, DevOpsObservation, DevOpsState

class DevOpsEnvClient(EnvClient[DevOpsAction, DevOpsObservation, DevOpsState]):
    """Client for the DevOps SRE Environment."""

    def _step_payload(self, action: DevOpsAction) -> Dict[str, Any]:
        return {"command": action.command}

    def _parse_result(self, payload: Dict[str, Any]) -> StepResult[DevOpsObservation]:
        obs_data = payload.get("observation", {})
        observation = DevOpsObservation(
            stdout=obs_data.get("stdout", ""),
            stderr=obs_data.get("stderr", ""),
            pwd=obs_data.get("pwd", "/root"),
            echoed_message=obs_data.get("echoed_message", ""),
            done=payload.get("done", False),
            reward=payload.get("reward", 0.0),
            metadata=obs_data.get("metadata", {})
        )
        return StepResult(
            observation=observation,
            reward=payload.get("reward", 0.0),
            done=payload.get("done", False),
        )

    def _parse_state(self, payload: Dict[str, Any]) -> DevOpsState:
        return DevOpsState(
            task_id=payload.get("task_id", "easy"),
            steps_taken=payload.get("steps_taken", 0),
            current_directory=payload.get("current_directory", "/root"),
            current_score=payload.get("current_score", 0.0)
        )