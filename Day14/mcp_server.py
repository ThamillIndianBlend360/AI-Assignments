"""
Day 14: Model Context Protocol (MCP) Server
- Exposes existing safe tools (leave balance lookup & leave request creation) via FastMCP.
- Standardizes tool schemas, input validation, and request/result flows.
"""

import json
from fastmcp import FastMCP

# Initialize the FastMCP server instance
mcp = FastMCP(name="Enterprise HR Leave MCP Server")

# Mock In-Memory Database (carried over from Day 10/12)
LEAVE_DATA = {
    "E101": {"name": "Priya", "leave_balance": 3},
    "E102": {"name": "Rahul", "leave_balance": 0},
    "E103": {"name": "Anita", "leave_balance": 5}
}

IDEMPOTENCY_CACHE = {}

@mcp.tool()
def get_available_leave_balance(user_id: str) -> str:
    """[READ-ONLY] Lookup the available leave balance for an employee user ID."""
    user_id = user_id.upper()
    user = LEAVE_DATA.get(user_id)
    if user is None:
        return json.dumps({"status": "ERROR", "error_code": "USER_NOT_FOUND", "message": f"No user found with ID {user_id}"})
    return json.dumps({
        "status": "SUCCESS",
        "user_id": user_id,
        "name": user["name"],
        "leave_balance": user["leave_balance"]
    })

@mcp.tool()
def create_leave_request(user_id: str, date: str, reason: str) -> str:
    """[WRITE-ACTION] Submit a formal leave request with deterministic balance checks and idempotency."""
    user_id = user_id.upper()
    
    # Idempotency check
    key = f"{user_id}:{date}"
    if key in IDEMPOTENCY_CACHE:
        return json.dumps({
            "status": "SUCCESS",
            "idempotent_replay": True,
            "message": f"Leave request for {date} already processed.",
            "details": IDEMPOTENCY_CACHE[key]
        })

    user = LEAVE_DATA.get(user_id)
    if not user:
        return json.dumps({"status": "ERROR", "error_code": "USER_NOT_FOUND", "message": f"User {user_id} not found."})

    # Deterministic balance rule check
    if user["leave_balance"] < 1:
        return json.dumps({
            "status": "ERROR",
            "error_code": "INSUFFICIENT_BALANCE",
            "message": f"Balance check failed. User {user['name']} has {user['leave_balance']} leave days remaining."
        })

    # State mutation
    user["leave_balance"] -= 1
    record = {
        "user_id": user_id,
        "name": user["name"],
        "date": date,
        "reason": reason,
        "remaining_balance": user["leave_balance"]
    }
    IDEMPOTENCY_CACHE[key] = record

    return json.dumps({
        "status": "SUCCESS",
        "idempotent_replay": False,
        "message": f"Leave successfully created for {date}.",
        "remaining_balance": user["leave_balance"]
    })

if __name__ == "__main__":
    # Run the MCP server over stdio transport
    mcp.run()