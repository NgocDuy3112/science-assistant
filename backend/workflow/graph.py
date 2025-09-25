from langgraph.types import Command, interrupt
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

from langchain_core.messages import (
    SystemMessage, 
    AIMessage, 
    ToolMessage, 
)
from langchain_core.language_models.chat_models import BaseChatModel

from typing_extensions import Literal
from uuid import uuid4


from backend.workflow.state import OverallState
from utils.helper import read_from_txt_path
from configs import PAPERS_DIR


RISKY_TOOLS = ["download_papers", "delete_papers"]
CONTINUE_COMMANDS = ['continue', 'y', 'yes']


def assistant_node(llm_with_tools: BaseChatModel):
    def _assistant_node(state: OverallState) -> OverallState:
        response = llm_with_tools.invoke(
            [SystemMessage(content=read_from_txt_path("prompts/arxiv.txt").format(output_dir=PAPERS_DIR))] + state.messages
        )
        state.messages = state.messages + [response]
        return state
    return _assistant_node



def assistant_router(state: OverallState) -> Literal["tools_node", "human_node", END]: # type: ignore
    response: AIMessage = state.messages[-1]
    if response.tool_calls:
        if any(tool_call["name"] in RISKY_TOOLS for tool_call in response.tool_calls):
            return "human_node"
        return "tools_node"
    else:
        return END



def tools_node(tools: list):
    return ToolNode(tools)



def human_node(state: OverallState) -> Command[Literal["tools_node", END]]: # type: ignore
    response: AIMessage = state.messages[-1]
    tool_call_name = response.tool_calls[0]["name"]
    prompt  = f"Do you want me to process this tool: {tool_call_name}?" 
    while True:
        user_input = interrupt(prompt)
        try:
            if user_input.lower() in CONTINUE_COMMANDS:
                return Command(
                    goto="tools_node"
                )
            else:
                tool_message = ToolMessage(
                    content="Skip the tool calling!",
                    tool_call_id=str(uuid4())
                )
                return Command(
                    goto=END,
                    update={'messsages': tool_message}
                )
        except TypeError:
            prompt = f"{user_input} is not valid. Only accepts 'continue' or 'reject'"



def build_graph(llm_with_tools: BaseChatModel, tools: list, checkpointer, image_path: str | None = "images/graph.png"):
    builder = StateGraph(OverallState)
    builder.add_node("assistant_node", assistant_node(llm_with_tools))
    builder.add_node("human_node", human_node)
    builder.add_node("tools_node", tools_node(tools))
    builder.add_edge(START, "assistant_node")
    builder.add_conditional_edges(
        "assistant_node",
        assistant_router
    )
    builder.add_edge("tools_node", "assistant_node")
    graph = builder.compile(checkpointer=checkpointer)
    if image_path is not None:
        with open(image_path, "wb") as f:
            f.write(graph.get_graph().draw_mermaid_png())
    return graph