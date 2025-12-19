from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
# SystemMessage = Instructions for the AI's behavior
# HumanMessage = What you say
# AIMessage = What the AI says
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

load_dotenv()

# 1. Setup the Brain
llm = ChatOpenAI(model="gpt-3.5-turbo")

# 2. Create the "Memory" (A simple list)
# We start with a SystemMessage to give the AI a persona.
chat_history = [
    SystemMessage(content="You are a helpful executive assistant. Your goal is to help me book meetings.")
]

print("🤖 AI: Hello! I am your scheduling assistant. (Type 'exit' to quit)")

# 3. The Conversation Loop
while True:
    # Get input from you
    user_input = input("You: ")

    # Break the loop if you want to quit
    if user_input.lower() == "exit":
        print("Goodbye!")
        break

    # A. Add YOUR message to history
    chat_history.append(HumanMessage(content=user_input))

    # B. Send the WHOLE history to the AI
    response = llm.invoke(chat_history)

    # C. Print the AI's reply
    print(f"🤖 AI: {response.content}")

    # D. Add the AI's reply to history (so it remembers it next time)
    chat_history.append(AIMessage(content=response.content))
