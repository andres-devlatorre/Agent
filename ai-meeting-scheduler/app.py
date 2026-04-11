import datetime
import os
import uuid
from flask import Flask, render_template, request, jsonify, session
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool

# Import our new helper
from calendar_helper import add_event_to_calendar

load_dotenv()

app = Flask(__name__)
# SECRET_KEY is required for signing session cookies.
# Set a strong random value in .env for production.
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-change-in-production")

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

# --- SYSTEM PROMPT ---
def _make_system_prompt():
    """Build the system prompt with today's date so relative times resolve correctly."""
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    return f"""
You are a smart scheduling assistant. Today is {today}.

RULES:
1. Ask for the Person and Time.
2. Once you have them, convert the user's natural language time (e.g., "next Friday at 2pm")
   into a strict ISO 8601 string (e.g., "{today}T14:00:00") based on today's date.
3. Call the 'book_meeting' tool with that ISO string.
"""

# Per-session chat histories: { session_id: [SystemMessage, ...] }
session_histories = {}

# --- ROUTES ---
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    body = request.get_json(silent=True)
    if not body:
        return jsonify({"error": "Request body must be valid JSON"}), 400
    user_text = body.get("message")
    if not user_text or not isinstance(user_text, str) or not user_text.strip():
        return jsonify({"error": "Field 'message' is required and must be a non-empty string"}), 400
    user_text = user_text.strip()

    # Resolve (or create) a history for this browser session
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
    session_id = session["session_id"]
    if session_id not in session_histories:
        session_histories[session_id] = [SystemMessage(content=_make_system_prompt())]
    history = session_histories[session_id]

    history.append(HumanMessage(content=user_text))

    # Invoke AI
    response = llm_with_tools.invoke(history)
    history.append(response)

    # Handle Tool Call
    if response.tool_calls:
        for tool_call in response.tool_calls:
            args = tool_call["args"]
            tool_call_id = tool_call["id"]

            result_text = book_meeting.invoke(args)

            tool_msg = ToolMessage(content=result_text, tool_call_id=tool_call_id)
            history.append(tool_msg)

            reply_text = result_text
    else:
        reply_text = response.content

    return jsonify({"reply": reply_text})

if __name__ == "__main__":
    app.run(debug=True, port=5000)
