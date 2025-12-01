from __future__ import annotations
from typing_extensions import Annotated, Literal
from pydantic import BaseModel, Field

from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage



class State(BaseModel):
    """The state of the agent.
    
    Attributes:
        messages: The list of messages in the conversation.
        pdf_path: The path of the paper need to be summarized.
        summary: The summary of a paper need to be summarized.
        decision: Decide which action to do next
    """
    messages: Annotated[list[BaseMessage], add_messages] = []
    pdf_path: str
    summary: str | None = None
    decision: Literal["continue", "reject"] | None = Field(default=None)