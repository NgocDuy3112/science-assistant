import asyncio
import sys


async def main():
    arxiv_proc = await asyncio.create_subprocess_exec(
        sys.executable, "-m", "mcp_servers.arxiv.server"
    )
    # qdrant_proc = await asyncio.create_subprocess_exec(
    #     sys.executable, "-m", "mcp_servers.qdrant.server"
    # )

    await asyncio.gather(arxiv_proc.wait())


if __name__ == "__main__":
    asyncio.run(main())