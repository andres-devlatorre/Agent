import datetime
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool

# Import our new helper
from calendar_helper import add_event_to_calendar

load_dotenv()

app = Flask(__name__)

# --- THE TOOL ---
@tool
def book_meeting(person: str, start_time_iso: str):
    """
    Call this when you have a Name and a CONFIRMED specific time.
    - person: The name of the person.
    - start_time_iso: The date and time in ISO 8601 format (YYYY-MM-DDTHH:MM:SS).
    """
    try:
        print(f"📅 Booking for {person} at {start_time_iso}...")
        link = add_event_to_calendar(person, start_time_iso)
        return f"✅ Success! Meeting booked. View it here: {link}"
    except Exception as e:
        return f"❌ Error booking meeting: {str(e)}"

llm = ChatOpenAI(model="gpt-3.5-turbo")
llm_with_tools = llm.bind_tools([book_meeting])

# --- DYNAMIC PROMPT ---
# We need to tell the AI what "Today" is, so it can calculate "Next Friday" correctly.
current_date = datetime.datetime.now().strftime("%Y-%m-%d")

system_prompt = f"""
You are a smart scheduling assistant. Today is {current_date}.

RULES:
1. Ask for the Person and Time.
2. Once you have them, convert the user's natural language time (e.g., "next Friday at 2pm")
   into a strict ISO 8601 string (e.g., "{current_date}T14:00:00") based on today's date.
3. Call the 'book_meeting' tool with that ISO string.
"""

chat_history = [SystemMessage(content=system_prompt)]

# --- ROUTES ---
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    user_text = request.json.get("message")
    chat_history.append(HumanMessage(content=user_text))

    # Invoke AI
    response = llm_with_tools.invoke(chat_history)
    chat_history.append(response)

    # C. Handle Tool Call
    if response.tool_calls:
        for tool_call in response.tool_calls:
            args = tool_call["args"]
            tool_call_id = tool_call["id"] # We need this ID to keep the history clean

            # 1. Run the tool. This returns a STRING (not a message object)
            result_text = book_meeting.invoke(args)

            # 2. Create the Message Object manually for the history
            # This tells the AI: "Here is the result for the tool request you just made."
            tool_msg = ToolMessage(content=result_text, tool_call_id=tool_call_id)
            chat_history.append(tool_msg)

            # 3. Send the plain text string to the user
            reply_text = result_text
    else:
        reply_text = response.content

    return jsonify({"reply": reply_text})

if __name__ == "__main__":
    app.run(debug=True, port=5000)
