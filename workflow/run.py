import asyncio
import datetime
from typing_extensions import Any
from collections.abc import AsyncGenerator
from rich.console import Console

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, AIMessageChunk, ToolCallChunk
from langchain_core.runnables.config import RunnableConfig
from langchain_mcp_adapters.client import MultiServerMCPClient

from langgraph.types import Command
from langgraph.graph.state import CompiledStateGraph
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from configs import SQLITE_CHECKPOINTS_URI, CHAT_MODEL_NAME
from workflow.graph import build_graph



async def process_tool_call_chunk(chunk: ToolCallChunk):
    """Process a tool call chunk and return a formatted string."""
    tool_call_str = ""

    tool_name = chunk.get("name", "")
    args = chunk.get("args", "")

    if tool_name:
        tool_call_str += f"\n\n< TOOL CALL: {tool_name} >\n\n"
    if args:
        tool_call_str += args

    return tool_call_str


async def stream_graph_responses(
        input: dict[str, Any] | Command,
        graph: CompiledStateGraph,
        **kwargs
        ) -> AsyncGenerator[str, None]:
    """Asynchronously stream the result of the graph run.

    Args:
        input: The input to the graph.
        graph: The compiled graph.
        **kwargs: Additional keyword arguments.

    Returns:
        str: The final LLM or tool call response
    """
    async for message_chunk, _ in graph.astream(
        input=input,
        stream_mode="messages",
        **kwargs
        ):
        if isinstance(message_chunk, AIMessageChunk):
            if message_chunk.response_metadata:
                finish_reason = message_chunk.response_metadata.get("finish_reason", "")
                if finish_reason == "tool_calls":
                    yield "\n\n"

            if message_chunk.tool_call_chunks:
                tool_chunk = message_chunk.tool_call_chunks[0]
                tool_call_str = await process_tool_call_chunk(tool_chunk)
                yield tool_call_str
                
            else:
                # Ensure content is always a string
                content = message_chunk.content
                if isinstance(content, str):
                    yield content
                elif isinstance(content, list):
                    # Convert list content to string representation
                    yield str(content)
                else:
                    # Fallback for any other type
                    yield str(content)



async def main():
    async with AsyncSqliteSaver.from_conn_string(SQLITE_CHECKPOINTS_URI) as checkpointer:
        config = RunnableConfig(
            recursion_limit=10,
            configurable={
                "thread_id": hash(datetime.datetime.today().isoformat())
            }
        )
        console = Console()
        mcp_client = MultiServerMCPClient(
            {
                "arxiv": {
                    "command": "python",
                    "args": ["-m", "mcp_servers.arxiv.server"],
                    "transport": "stdio"
                }
            }
        )
        tools = await mcp_client.get_tools()
        llm_with_tools = ChatOllama(model=CHAT_MODEL_NAME, temperature=0.1).bind_tools(tools)
        graph = build_graph(llm_with_tools, tools, checkpointer, None)
        while True:
            user_input = console.input("[green]>You:[/green] ")
            if user_input in ["/bye", "/exit"]:
                break
            input_message = HumanMessage(content=user_input)
            initial_input = {
                "messages": [input_message]
            }
            console.print(f"[cyan]>Assistant:[/cyan] ")
            async for response in stream_graph_responses(initial_input, graph, config=config):
                console.print(response, end="")
            thread_state = await graph.aget_state(config=config)
            if thread_state.interrupts:
                for interrupt in thread_state.interrupts:
                    console.print(f"\n[red]>System:[/red] {interrupt.value}")
                    user_decision = console.input("[green]>You:[/green] ")
                    async for response in stream_graph_responses(Command(resume=user_decision), graph, config=config):
                        console.print(response, end="")
            console.print("\n")



if __name__ == '__main__':
    asyncio.run(main())