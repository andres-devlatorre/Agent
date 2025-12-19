# Import the tool to load our .env file
from dotenv import load_dotenv
# Import the specific "Chat" model from LangChain
from langchain_openai import ChatOpenAI

# 1. Load the secrets
load_dotenv()

# 2. Initialize the AI (The "Brain")
# model="gpt-3.5-turbo" is cheaper/faster. You can use "gpt-4" if you want to pay more.
llm = ChatOpenAI(model="gpt-3.5-turbo")

# 3. Send a message
print("Sending message to OpenAI...")
response = llm.invoke("Hello! Are you ready to help me book a meeting?")

# 4. Print the result
# The response object has a .content attribute, which is the actual text
print("AI Replied:")
print(response.content)
