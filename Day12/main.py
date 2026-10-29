"""
Day 12: Reliable Agentic Workflows
- Move critical rules out of prompts and into deterministic code/tools.
- Enforce balance checks, idempotency, strict step order, and audit trails.
"""

import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ValidationError
import ollama

# Configure Audit Trail Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("day12_audit_trail.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("ReliableAgent")

MODEL = os.getenv("OLLAMA_MODEL", "llama3")
MAX_LOOPS = 6
client = ollama.Client(timeout=180)


# ==========================================
# 1. Deterministic Backend & State Storage
# ==========================================

LEAVE_DATA = {
    "E101": {"name": "Priya", "leave_balance": 3},
    "E102": {"name": "Rahul", "leave_balance": 0},
    "E103": {"name": "Anita", "leave_balance": 5}
}

FESTIVALS = {
    "festivals": [
        {"name": "Diwali",   "date": "2026-11-08"},
        {"name": "Dussehra", "date": "2026-10-20"},
        {"name": "Holi",     "date": "2027-03-04"},
        {"name": "Onam",     "date": "2026-08-26"},
        {"name": "Pongal",   "date": "2027-01-14"}
    ]
}

# Idempotency registry: tracks (user_id, date) -> result
IDEMPOTENCY_CACHE: Dict[str, Dict[str, Any]] = {}
APPROVED_REQUESTS: List[Dict[str, Any]] = []


# ==========================================
# 2. Pydantic Schemas for Strict Input Validation
# ==========================================

class BalanceInput(BaseModel):
    user_id: str = Field(..., description="Employee User ID, e.g., 'E101'")

class FestivalInput(BaseModel):
    festival_name: str = Field(..., description="Name of the festival")

class LeaveRequestInput(BaseModel):
    user_id: str = Field(..., description="Employee User ID")
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    reason: str = Field(..., description="Reason or festival name for leave")


# ==========================================
# 3. Deterministic Tool Functions
# ==========================================

def get_available_leave_balance(user_id: str) -> str:
    """Return structured JSON leave balance for a user ID."""
    user = LEAVE_DATA.get(user_id.upper())
    if user is None:
        return json.dumps({"status": "ERROR", "error_code": "USER_NOT_FOUND", "message": f"No user found with ID {user_id}"})
    return json.dumps({
        "status": "SUCCESS",
        "user_id": user_id.upper(),
        "name": user["name"],
        "leave_balance": user["leave_balance"]
    })

def get_festival_date(festival_name: str) -> str:
    """Return date of a festival matched case-insensitively."""
    for festival in FESTIVALS["festivals"]:
        if festival["name"].lower() == festival_name.strip().lower():
            return json.dumps({"status": "SUCCESS", "festival": festival["name"], "date": festival["date"]})
    return json.dumps({"status": "ERROR", "error_code": "FESTIVAL_NOT_FOUND", "message": f"No festival named '{festival_name}' found."})

def create_leave_request(user_id: str, date: str, reason: str) -> str:
    """
    Deterministically creates a leave request with:
    - Balance validation in code (rejects if balance < 1)
    - Idempotency checking (returns original result if duplicate request)
    """
    user_id = user_id.upper()
    
    # 1. Idempotency Key check: (user_id, date)
    idempotency_key = f"{user_id}:{date}"
    if idempotency_key in IDEMPOTENCY_CACHE:
        logger.info(f"[IDEMPOTENCY HIT] Duplicate request caught for key '{idempotency_key}'")
        return json.dumps({
            "status": "SUCCESS",
            "idempotent_replay": True,
            "message": f"Request for {date} already processed.",
            "details": IDEMPOTENCY_CACHE[idempotency_key]
        })

    # 2. Verify User Exists
    user = LEAVE_DATA.get(user_id)
    if not user:
        return json.dumps({"status": "ERROR", "error_code": "USER_NOT_FOUND", "message": f"User {user_id} not found."})

    # 3. Enforce Balance Rule in Code (Deterministic comparison)
    if user["leave_balance"] < 1:
        logger.warning(f"[POLICY REJECTION] User {user_id} has insufficient balance ({user['leave_balance']})")
        return json.dumps({
            "status": "ERROR",
            "error_code": "INSUFFICIENT_BALANCE",
            "message": f"Balance check failed. User {user['name']} has {user['leave_balance']} leave days remaining."
        })

    # 4. Mutate State Safely
    user["leave_balance"] -= 1
    record = {
        "user_id": user_id,
        "name": user["name"],
        "date": date,
        "reason": reason,
        "remaining_balance": user["leave_balance"]
    }
    
    IDEMPOTENCY_CACHE[idempotency_key] = record
    APPROVED_REQUESTS.append(record)
    logger.info(f"[STATE MUTATION SUCCESS] Leave created for {user_id} on {date}. Remaining: {user['leave_balance']}")

    return json.dumps({
        "status": "SUCCESS",
        "idempotent_replay": False,
        "message": f"Leave successfully created for {date}.",
        "remaining_balance": user["leave_balance"]
    })


# Tool Registry mapping names to functions and Pydantic validators
TOOLS = {
    "get_available_leave_balance": {"fn": get_available_leave_balance, "schema": BalanceInput},
    "get_festival_date": {"fn": get_festival_date, "schema": FestivalInput},
    "create_leave_request": {"fn": create_leave_request, "schema": LeaveRequestInput},
}


# ==========================================
# 4. Reliable Workflow Execution Engine
# ==========================================

SYSTEM_PROMPT = """You are a reliable HR Leave Assistant. Today's date is 2026-10-21.

Tools:
- get_available_leave_balance: Action Input {"user_id": "<id>"}
- get_festival_date: Action Input {"festival_name": "<name>"}
- create_leave_request: Action Input {"user_id": "<id>", "date": "<YYYY-MM-DD>", "reason": "<name>"}

Rules:
1. Always verify the user's leave balance BEFORE creating any leave requests.
2. Check festival dates to get their exact YYYY-MM-DD strings.
3. Skip any festival whose date is before today (2026-10-21).
4. Return steps using this format:
Thought: your reasoning
Action: tool_name
Action Input: {"arg": "val"}

When finished, reply with:
Thought: final summary
Final Answer: your response to the user
"""

def parse_step(text):
    import re
    thought = re.search(r"Thought:\s*(.*?)(?=\nAction:|\nFinal Answer:|$)", text, re.S)
    action = re.search(r"Action:\s*(\w+)", text)
    action_input = re.search(r"Action Input:\s*(\{.*?\})", text, re.S)

    thought_text = thought.group(1).strip() if thought else "(no thought)"
    tool_name = action.group(1) if action else None
    try:
        inputs = json.loads(action_input.group(1)) if action_input else {}
    except json.JSONDecodeError:
        inputs = {}
    return thought_text, tool_name, inputs


def run_reliable_agent(question: str):
    logger.info(f"--- [START RUN] Question: {question} ---")
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question}
    ]

    for step_num in range(1, MAX_LOOPS + 1):
        logger.info(f"Step {step_num}: Querying model...")
        
        response = client.chat(model=MODEL, messages=messages, options={"temperature": 0})
        reply = response["message"]["content"].strip()
        messages.append({"role": "assistant", "content": reply})

        thought, tool_name, tool_input = parse_step(reply)
        logger.info(f"Thought: {thought}")

        if "Final Answer:" in reply:
            final_ans = reply.split("Final Answer:")[-1].strip()
            logger.info(f"Final Answer: {final_ans}")
            return final_ans

        if not tool_name or tool_name not in TOOLS:
            observation = json.dumps({"status": "ERROR", "message": f"Invalid tool '{tool_name}' requested."})
        else:
            # Pydantic Argument Validation before execution
            tool_spec = TOOLS[tool_name]
            try:
                validated_args = tool_spec["schema"](**tool_input)
                observation = tool_spec["fn"](**validated_args.model_dump())
            except ValidationError as ve:
                observation = json.dumps({"status": "ERROR", "error_code": "VALIDATION_ERROR", "details": str(ve)})
                logger.error(f"Validation error for {tool_name}: {ve}")
            except Exception as e:
                observation = json.dumps({"status": "ERROR", "error_code": "EXEC_EXCEPTION", "message": str(e)})
                logger.error(f"Execution exception: {e}")

        logger.info(f"Observation: {observation}")
        messages.append({"role": "user", "content": f"Observation: {observation}"})

    return "Agent terminated: Reached maximum execution steps without final answer."


if __name__ == "__main__":
    # Test case: Valid request + duplicate test for idempotency
    query = "My user ID is E101. Create a leave request for Diwali."
    print("=== First Execution ===")
    print(run_reliable_agent(query))
    
    print("\n=== Second Execution (Idempotency Test) ===")
    print(run_reliable_agent(query))