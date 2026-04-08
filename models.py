from pydantic import BaseModel, Field

class DevOpsAction(BaseModel):
    """What the AI agent sends to the environment."""
    command: str = Field(..., description="The bash command to execute in the terminal.")

class DevOpsObservation(BaseModel):
    """What the environment returns to the AI agent."""
    stdout: str = Field(..., description="Standard output from the executed command.")
    stderr: str = Field(..., description="Standard error from the executed command.")
    pwd: str = Field(..., description="The current working directory.")
    echoed_message: str = Field(default="", description="The last command executed.")
    # Required OpenEnv tracking fields
    done: bool = Field(default=False)
    reward: float = Field(default=0.0)
    metadata: dict = Field(default_factory=dict)

class DevOpsState(BaseModel):
    """Metadata about the current episode."""
    task_id: str
    steps_taken: int
    current_directory: str
    current_score: float