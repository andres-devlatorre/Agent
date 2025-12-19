from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool

load_dotenv()

# --- UPDATE 1: Stricter Tool Definition ---
@tool
def book_meeting(person: str, time: str):
    """
    Call this function ONLY when you have BOTH:
    1. The person's name.
    2. The specific time or date.

    DO NOT call this function if the time is missing. Ask the user for the time instead.
    """
    return f"✅ Success! Meeting booked with {person} at {time}."

llm = ChatOpenAI(model="gpt-3.5-turbo")
llm_with_tools = llm.bind_tools([book_meeting])

# --- UPDATE 2: Stricter System Prompt ---
chat_history = [
    SystemMessage(content="""
    You are a scheduling assistant.
    Your goal is to book meetings using the 'book_meeting' tool.

    IMPORTANT RULES:
    1. You MUST collect both the 'person' and the 'time' from the user.
    2. If the user only gives a name, ask "When would you like to meet?"
    3. If the user only gives a time, ask "Who is this meeting with?"
    4. DO NOT call the tool until you have both pieces of information.
    """)
]

print("🤖 AI: Ready to schedule! (Type 'exit' to quit)")

while True:
    user_input = input("You: ")
    if user_input.lower() == "exit": break

    chat_history.append(HumanMessage(content=user_input))

    response = llm_with_tools.invoke(chat_history)

    # We append the AI's response to history so it remembers what it just did
    chat_history.append(response)

    if response.tool_calls:
        print(f"🎉 ACTION TRIGGERED: The AI wants to book a meeting!")
        for tool_call in response.tool_calls:
            print(f"   Function Name: {tool_call['name']}")
            print(f"   Arguments: {tool_call['args']}")
            print("   (Simulating Google Calendar API call...)")
        break
    else:
        print(f"🤖 AI: {response.content}")
