"""
Day 10: Enterprise Knowledge & Action Assistant
- Read-only lookup tool vs. State-mutating write tool
- Strict argument validation via Pydantic
- Application-controlled execution boundary with human confirmation for write actions
- Audit logging & failure resilience
"""

import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ValidationError
import ollama

# Configure Execution Audit Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("day10_execution.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("Day10_Assistant")

MODEL = os.getenv("OLLAMA_MODEL", "llama3")
client = ollama.Client(timeout=180)


# ==========================================
# 1. Pydantic Schemas for Tool Arguments
# ==========================================

class LeaveBalanceInput(BaseModel):
    user_id: str = Field(..., description="Employee User ID, e.g., 'E101'")

class CreateLeaveRequestInput(BaseModel):
    user_id: str = Field(..., description="Employee User ID, e.g., 'E101'")
    start_date: str = Field(..., description="Start date in YYYY-MM-DD format")
    days: int = Field(..., gt=0, le=30, description="Number of days requested (1-30)")
    reason: str = Field(..., min_length=3, description="Reason for leave request")


# ==========================================
# 2. Mock Backend & Tools
# ==========================================

EMPLOYEE_DATABASE = {
    "E101": {"name": "Priya", "balance": 12, "department": "Engineering"},
    "E102": {"name": "Rahul", "balance": 2, "department": "Marketing"},
    "E103": {"name": "Anita", "balance": 20, "department": "Operations"},
}

LEAVE_REQUESTS_DB = []

def get_employee_leave_balance(user_id: str) -> str:
    """[READ-ONLY] Lookup employee leave balance."""
    logger.info(f"[READ-ONLY TOOL EXECUTION] get_employee_leave_balance for user_id='{user_id}'")
    user = EMPLOYEE_DATABASE.get(user_id.upper())
    if not user:
        return json.dumps({"error": f"Employee with ID '{user_id}' not found."})
    return json.dumps({
        "user_id": user_id.upper(),
        "name": user["name"],
        "leave_balance": user["balance"],
        "department": user["department"]
    })

def create_leave_request(user_id: str, start_date: str, days: int, reason: str) -> str:
    """[WRITE-ACTION] Mutate state by submitting a formal leave request."""
    logger.info(f"[WRITE TOOL EXECUTION] create_leave_request for {user_id}: {days} days from {start_date}")
    user_id_upper = user_id.upper()
    user = EMPLOYEE_DATABASE.get(user_id_upper)
    if not user:
        return json.dumps({"error": f"Employee with ID '{user_id}' not found."})
    
    if user["balance"] < days:
        return json.dumps({
            "error": "Insufficient balance",
            "requested": days,
            "available": user["balance"]
        })
    
    # Mutate DB state
    user["balance"] -= days
    request_entry = {
        "request_id": f"LR-{len(LEAVE_REQUESTS_DB) + 1001}",
        "user_id": user_id_upper,
        "name": user["name"],
        "start_date": start_date,
        "days": days,
        "reason": reason,
        "status": "APPROVED"
    }
    LEAVE_REQUESTS_DB.append(request_entry)
    
    return json.dumps({
        "status": "SUCCESS",
        "message": f"Successfully scheduled {days} day(s) leave for {user['name']}.",
        "remaining_balance": user["balance"],
        "details": request_entry
    })


# Tool Metadata Registry for LLM
TOOL_METADATA = [
    {
        "name": "get_employee_leave_balance",
        "description": "Read-only lookup to fetch available leave balance for an employee.",
        "is_write_action": False,
        "schema": LeaveBalanceInput,
        "function": get_employee_leave_balance
    },
    {
        "name": "create_leave_request",
        "description": "Write action that submits a new leave request and reduces the available leave balance.",
        "is_write_action": True,
        "schema": CreateLeaveRequestInput,
        "function": create_leave_request
    }
]

TOOLS_BY_NAME = {t["name"]: t for t in TOOL_METADATA}


# ==========================================
# 3. Application Execution Boundary & Security
# ==========================================

def execute_tool_call(tool_name: str, raw_args: Dict[str, Any]) -> str:
    """Validates arguments, enforces human confirmation for write actions, and handles errors safely."""
    if tool_name not in TOOLS_BY_NAME:
        logger.warning(f"Model requested unknown tool: {tool_name}")
        return json.dumps({"error": f"Unknown tool '{tool_name}'."})

    tool_info = TOOLS_BY_NAME[tool_name]

    # 1. Input Validation via Pydantic
    try:
        validated_args = tool_info["schema"](**raw_args)
    except ValidationError as ve:
        error_msg = f"Argument validation failed for '{tool_name}': {ve.errors()}"
        logger.error(error_msg)
        return json.dumps({"error": "Invalid tool arguments", "details": ve.errors()})

    # 2. Security & Human-in-the-loop Confirmation for Write Actions
    if tool_info["is_write_action"]:
        print(f"\n==================================================")
        print(f"⚠️  SECURITY ACTION CONFIRMATION REQUIRED")
        print(f"Tool: {tool_name}")
        print(f"Proposed Mutation Arguments: {validated_args.model_dump_json(indent=2)}")
        print(f"==================================================")
        
        # Check environment or prompt user
        auto_confirm = os.getenv("AUTO_CONFIRM_WRITES", "false").lower() == "true"
        if not auto_confirm:
            confirm = input("Do you authorize the application to execute this WRITE action? [y/N]: ").strip().lower()
            if confirm != 'y':
                logger.warning(f"User REJECTED write execution for tool '{tool_name}' with args {raw_args}")
                return json.dumps({
                    "error": "Action cancelled by user authorization policy.",
                    "status": "REJECTED_BY_USER"
                })
        logger.info(f"User APPROVED write action '{tool_name}'")

    # 3. Controlled Application Execution
    try:
        result = tool_info["function"](**validated_args.model_dump())
        return result
    except Exception as exc:
        logger.exception(f"Unexpected crash during execution of '{tool_name}'")
        return json.dumps({"error": f"Execution error: {str(exc)}"})


# ==========================================
# 4. Agent Loop
# ==========================================

SYSTEM_PROMPT = """You are an Enterprise HR Assistant. Today's date is 2026-10-28.
You help employees check leave balances and submit leave requests.

Available tools:
1. get_employee_leave_balance(user_id: string) -> read-only balance check.
2. create_leave_request(user_id: string, start_date: string, days: integer, reason: string) -> submits leave request.

Rules:
- Always check an employee's leave balance using get_employee_leave_balance BEFORE creating a leave request.
- If balance is sufficient, request create_leave_request.
- Return structured tool requests in JSON format when calling tools:
  {"tool": "<tool_name>", "args": { ... }}
- If answering directly, reply with plain text.
"""

def run_day10_assistant(user_prompt: str):
    logger.info(f"User Query: {user_prompt}")
    print(f"\n💬 User Query: {user_prompt}")

    # Step 1: Query Model
    response = client.chat(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        options={"temperature": 0}
    )

    content = response["message"]["content"].strip()
    print(f"🤖 Assistant Initial Response:\n{content}")

    # Parse potential JSON tool call from LLM output
    if "{" in content and "}" in content:
        try:
            json_str = content[content.find("{"):content.rfind("}")+1]
            data = json.loads(json_str)
            if "tool" in data and "args" in data:
                tool_name = data["tool"]
                args = data["args"]
                
                print(f"\n⚙️ Model requested tool: {tool_name}")
                obs = execute_tool_call(tool_name, args)
                print(f"🔍 Observation: {obs}")

                # Feed observation back to model
                final_res = client.chat(
                    model=MODEL,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                        {"role": "assistant", "content": content},
                        {"role": "user", "content": f"Tool Observation: {obs}"}
                    ],
                    options={"temperature": 0}
                )
                print(f"\n🏁 Final Response:\n{final_res['message']['content']}")
                return
        except json.JSONDecodeError:
            pass

    print(f"\n🏁 Final Response:\n{content}")


if __name__ == "__main__":
    # Example Query testing both Read lookup and Write mutation
    query = "My user ID is E101. Please submit a 3-day leave request starting 2026-11-10 for a personal trip."
    run_day10_assistant(query)