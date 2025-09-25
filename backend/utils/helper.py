from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_mcp_adapters.client import MultiServerMCPClient


def read_from_txt_path(txt_path: str):
    with open(txt_path, "r", encoding="utf-8") as file:
        return file.read()


async def get_mcp_tools(mcp_client: MultiServerMCPClient, mcp_server_name: str):
    async with mcp_client.session(mcp_server_name) as session:
        return await load_mcp_tools(session)