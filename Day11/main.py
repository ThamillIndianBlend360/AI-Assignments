"""
Simple ReAct agent for leave requests using Ollama.

Loop:  Reason (Thought) -> Action -> Observation -> ... -> Final Answer
Setup: pip install ollama
       Ensure Ollama is running locally (ollama serve) and llama3 is pulled.
"""

import json
import re
import os
import ollama

MODEL = os.getenv("OLLAMA_MODEL", "llama3")  # Local Ollama model
MAX_LOOPS = 5                                # Safety limit so the agent can't loop forever

client = ollama.Client(timeout=180)          # Local Ollama client


# ---------- Tool 1: leave balance (dummy data) ----------

# Dummy leave data for 3 users, stored as JSON
LEAVE_DATA = json.loads("""
{
  "E101": {"name": "Priya", "leave_balance": 3},
  "E102": {"name": "Rahul", "leave_balance": 0},
  "E103": {"name": "Anita", "leave_balance": 5}
}
""")

def get_available_leave_balance(user_id):
    """Return the leave balance for a user ID."""
    user = LEAVE_DATA.get(user_id)
    if user is None:
        return f"No user found with ID {user_id}"
    return json.dumps({"user_id": user_id,
                       "name": user["name"],
                       "leave_balance": user["leave_balance"]})


# ---------- Tool 2: create leave request (just prints) ----------

def create_leave_request(user, date):
    """Pretend to create a leave request by printing it."""
    print(f"leave request created for {user} on {date}")
    return f"Leave request created for {user} on {date}"


# ---------- Tool 3: festival dates (dummy data) ----------

# 5 festivals with dummy dates, stored as JSON
FESTIVALS = json.loads("""
{
  "festivals": [
    {"name": "Diwali",   "date": "2026-11-08"},
    {"name": "Dussehra", "date": "2026-10-20"},
    {"name": "Holi",     "date": "2027-03-04"},
    {"name": "Onam",     "date": "2026-08-26"},
    {"name": "Pongal",   "date": "2027-01-14"}
  ]
}
""")

def get_festival_date(festival_name):
    """Return the date of a festival, matched by name (case-insensitive)."""
    for festival in FESTIVALS["festivals"]:
        if festival["name"].lower() == festival_name.lower():
            return json.dumps(festival)
    return f"No festival named {festival_name} found"


# Map tool names (what the model writes) to the Python functions
TOOLS = {
    "get_available_leave_balance": get_available_leave_balance,
    "create_leave_request": create_leave_request,
    "get_festival_date": get_festival_date,
}


# ---------- The agent ----------

# Tells the model what it can do, the rules to follow, and the output format
SYSTEM_PROMPT = """You are a leave assistant. Today's date is 2026-10-21.

You have these tools:
- get_available_leave_balance: Action Input {"user_id": "<id>"}. Returns the user's leave balance.
- get_festival_date: Action Input {"festival_name": "<name>"}. Returns a festival's date.
- create_leave_request: Action Input {"user": "<user_id>", "date": "<YYYY-MM-DD>"}. Creates a one-day leave request.

Rules:
- Use one tool at a time and wait for the Observation before the next step.
- Each festival needs 1 leave day.
- Check the leave balance BEFORE creating any leave request.
- Skip any festival whose date is before today.
- Only create leave requests if the balance covers all of them. If it doesn't, create none and explain why in the Final Answer.

Use this format for each step:

Thought: your reasoning about the next step
Action: the tool name
Action Input: a JSON object with the tool's inputs

When you are done, use this format instead:

Thought: your reasoning
Final Answer: your reply to the user
"""


def parse_step(text):
    """Split the model's reply into its Thought, Action, and Action Input."""
    thought = re.search(r"Thought:\s*(.*?)(?=\nAction:|\nFinal Answer:|$)", text, re.S)
    action = re.search(r"Action:\s*(\w+)", text)
    action_input = re.search(r"Action Input:\s*(\{.*?\})", text, re.S)

    thought_text = thought.group(1).strip() if thought else "(no thought given)"
    tool_name = action.group(1) if action else None

    # Turn the Action Input JSON string into a Python dict
    try:
        inputs = json.loads(action_input.group(1)) if action_input else {}
    except json.JSONDecodeError:
        inputs = {}

    return thought_text, tool_name, inputs


def run_agent(question):
    """Run the Thought -> Action -> Observation loop until a Final Answer using Ollama."""
    # Ollama accepts system messages inside the messages array or via options; 
    # passing system role as part of messages is standard for Ollama Python client.
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question}
    ]

    for loop in range(1, MAX_LOOPS + 1):
        print(f"\n===== Loop {loop} =====")

        # Call local Ollama model
        response = client.chat(
            model=MODEL,
            messages=messages,
            options={
                "temperature": 0,
                "num_predict": 300,
            }
        )
        reply = response["message"]["content"].strip()
        messages.append({"role": "assistant", "content": reply})

        # Split the reply into its parts and print the reason
        thought, tool_name, tool_input = parse_step(reply)
        print(f"Reason:       {thought}")

        # If the model has a final answer, print it and stop
        if "Final Answer:" in reply:
            answer = reply.split("Final Answer:")[-1].strip()
            print(f"Final Answer: {answer}")
            return answer

        # Otherwise print the action and run the requested tool
        print(f"Action:       {tool_name}")
        print(f"Action Input: {tool_input}")

        if tool_name not in TOOLS:
            observation = f"Error: unknown tool. Use one of {list(TOOLS)}."
        else:
            try:
                observation = TOOLS[tool_name](**tool_input)
            except Exception as e:
                observation = f"Error running {tool_name}: {e}"

        # Print the observation, then feed it back to the model
        print(f"Observation:  {observation}")
        messages.append({"role": "user", "content": f"Observation: {observation}"})

    return "Stopped: reached the maximum number of loops."


if __name__ == "__main__":
    question = "My user ID is E101. Create a leave request for Diwali and Dussehra."
    answer = run_agent(question)
    print("\n----- Done -----")