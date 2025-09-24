from __future__ import annotations
from typing_extensions import Annotated, Literal
from pydantic import BaseModel, Field

from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage



class OverallState(BaseModel):
    """The state of the agent.
    
    Attributes:
        messages: The list of messages in the conversation.
        decision
    """
    messages: Annotated[list[BaseMessage], add_messages] = []
    decision: Literal["continue", "reject"] | None = Field(default=None)