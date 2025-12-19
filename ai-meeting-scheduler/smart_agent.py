from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from langchain_core.tools import tool

load_dotenv()

# 1. Define the "Tool" (The Action)
# The docstring ("""...""") is crucial! The AI reads it to know WHEN to use this tool.
@tool
def book_meeting(person: str, time: str):
    """Call this when the user wants to schedule a meeting. Requires person and time."""
    # In the real world, this is where the Google Calendar API code goes.
    return f"✅ Success! Meeting booked with {person} at {time}."

# 2. Setup the Brain with Tools
llm = ChatOpenAI(model="gpt-3.5-turbo")

# We "bind" the tool to the model. This gives the AI the ability to press this button.
llm_with_tools = llm.bind_tools([book_meeting])

# 3. Memory
chat_history = [
    SystemMessage(content="You are a scheduling assistant. If the user wants to meet, ask for details until you can book it.")
]

print("🤖 AI: Ready to schedule! (Type 'exit' to quit)")

while True:
    user_input = input("You: ")
    if user_input.lower() == "exit": break

    # A. Add user message
    chat_history.append(HumanMessage(content=user_input))

    # B. Get response from AI
    response = llm_with_tools.invoke(chat_history)

    # C. Add AI response to history
    chat_history.append(response)

    # D. CHECK: Did the AI decide to use the tool?
    if response.tool_calls:
        # The AI wants to run the function!
        print(f"🎉 ACTION TRIGGERED: The AI wants to book a meeting!")

        # Let's see what data it extracted
        for tool_call in response.tool_calls:
            print(f"   Function Name: {tool_call['name']}")
            print(f"   Arguments: {tool_call['args']}")

            # We assume we are running the tool now...
            # (In a complex app, we would run the function and feed the result back.
            #  For now, let's just pretend.)
            print("   (Simulating Google Calendar API call...)")

        # Stop the loop for this demo so you can see the result clearly
        break
    else:
        # No tool called yet, just normal conversation
        print(f"🤖 AI: {response.content}")
