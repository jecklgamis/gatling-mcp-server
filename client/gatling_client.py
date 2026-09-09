import asyncio
import os

from langchain.agents import create_agent
from langchain_mcp_adapters.tools import load_mcp_tools
from client.llm_factory import create_llm
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


async def main():
    base_url = os.environ.get("MCP_SERVER_URL", "http://localhost:58090")
    provider = os.environ.get("LLM_PROVIDER", "ollama")
    async with streamable_http_client(f"{base_url}/gatling_mcp/") as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await load_mcp_tools(session)
            llm = create_llm(provider)
            agent = create_agent(llm, tools)
            print("MCP Gatling Client (type 'quit' to exit)")
            while True:
                try:
                    query = input("\nQuery: ").strip()
                except (EOFError, KeyboardInterrupt):
                    break
                if not query or query.lower() in ("quit", "exit"):
                    break
                agent_response = await agent.ainvoke({"messages": [("user", query)]})
                messages = agent_response.get("messages", [])
                for msg in messages:
                    if msg.type == "ai" and msg.content and not msg.tool_calls:
                        print(f"Response: {msg.content}")


if __name__ == '__main__':
    asyncio.run(main())
