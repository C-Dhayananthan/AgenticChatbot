import asyncio
import getpass
import traceback

# LangChain imports
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage, HumanMessage
from langchain_groq import ChatGroq
from langchain.agents import AgentExecutor, create_structured_chat_agent
from langchain.agents.structured_chat.prompt import FORMAT_INSTRUCTIONS, PREFIX
from langchain.callbacks.base import BaseCallbackHandler

# MCP imports
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools


# Custom callback handler for debugging
class MessageTracker(BaseCallbackHandler):
    def on_llm_start(self, serialized, prompts, **kwargs):
        print(f"\n🔄 LLM PROMPT:\n{prompts[0]}\n")

    def on_llm_end(self, response, **kwargs):
        print(f"\n✅ LLM RESPONSE:\n{response.generations[0][0].text}\n")

    def on_tool_start(self, serialized, input_str, **kwargs):
        print(f"\n🔧 TOOL CALLED: {serialized['name']}\nInput: {input_str}\n")

    def on_tool_end(self, output, **kwargs):
        print(f"\n🔧 TOOL RESULT:\n{output}\n")


# Initialize LLM
llm = ChatGroq(
    model="llama3-70b-8192",
    api_key=getpass.getpass("Enter your Groq API key: "),
    temperature=0.2,
)


async def main():
    async with stdio_client(StdioServerParameters(
        command="python",
        args=["D://fundaura-chatbot//mcp_server.py"],
    )) as (read, write):

        async with ClientSession(read, write) as session:
            await session.initialize()
            def format_log_to_messages(intermediate_steps):
                """Construct the scratchpad that lets the agent continue its thought process."""
                thoughts = []
                for action, observation in intermediate_steps:
                    thoughts.append(AIMessage(content=action.log))
                    human_message = HumanMessage(content=f"Observation: {observation}")
                    thoughts.append(human_message)
                return thoughts
            agent_scratchpad = format_log_to_messages([])  # Initialize with an empty list
            # Load MCP tools
            mcp_tools = await load_mcp_tools(session)

            # Create the structured chat prompt with agent_scratchpad placeholder
            prompt = ChatPromptTemplate.from_messages([ 
                ("system", PREFIX + "\n\n{tools}"),
                ("human", "{input}"),
                ("system", FORMAT_INSTRUCTIONS),
                ("ai", "{agent_scratchpad}"), # Add agent_scratchpad here
            ])

            # Build the structured agent
            structured_agent = create_structured_chat_agent(
                llm=llm,
                tools=mcp_tools,
                prompt=prompt,
            )

            # Set up the agent executor
            agent_executor = AgentExecutor(
                agent=structured_agent,
                tools=mcp_tools,
                verbose=True,
                callbacks=[MessageTracker()],
                handle_parsing_errors=True,
                max_iterations=5
            )

            # Execute a sample query
            try:
                query = 'give count of documents in transactions collection in mongo db on date 2025-04-19'
                print(f"\n📝 QUERY: {query}\n")
                
                # Pass agent_scratchpad as a list of HumanMessage or AIMessage objects
                agent_response = await agent_executor.ainvoke({
                    "input": query,
                })
                
                print("FINAL RESPONSE:", agent_response)
                return agent_response
            except Exception as e:
                print(f"Error executing agent: {e}")
                traceback.print_exc()
                return {"error": str(e)}

# Run the async function
agent_response = asyncio.run(main())
print("Final result:", agent_response)