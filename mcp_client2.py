# Create server parameters for stdio connection
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent
import asyncio
from langchain_groq import ChatGroq
from langchain.callbacks.base import BaseCallbackHandler

class MessageTracker(BaseCallbackHandler):
    def on_llm_start(self, serialized, prompts, **kwargs):
        print(f"\n🔄 LLM PROMPT:\n{prompts[0]}\n")

    def on_llm_end(self, response, **kwargs):
        print(f"\n✅ LLM RESPONSE:\n{response.generations[0][0].text}\n")

    def on_tool_start(self, serialized, input_str, **kwargs):
        print(f"\n🔧 TOOL CALLED: {serialized['name']}\nInput: {input_str}\n")

    def on_tool_end(self, output, **kwargs):
        print(f"\n🔧 TOOL RESULT:\n{output}\n")
server_params = StdioServerParameters(command="python",args=["D://fundaura-chatbot//mcp_server.py"])
model = ChatGroq(
    model="qwen-qwq-32b",
    api_key="",
    temperature=0.8,
)
async def run_agent():
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the connection
            await session.initialize()
            # Get tools
            tools = await load_mcp_tools(session)
            # Create and run the agent
            agent = create_react_agent(model, tools)
            agent_response = await agent.ainvoke({"messages":'can you tell me how total amount spent on day date 2025-02-19. Query from transaction collection'}, config = {"callbacks": [MessageTracker()]})
            return agent_response

# Run the async function
if __name__ == "__main__":
    result = asyncio.run(run_agent())
    # print(result)