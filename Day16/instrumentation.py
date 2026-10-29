"""
Day 16: AI Observability & Debugging with LangSmith
- Instrumentation & Tracing (LangSmith / local fallback)
- PII Masking Rule (Regex for Email and Employee ID)
- Fault Flags for Testing Latency & Error Scenarios
"""

import os
import re
import json
import time
from typing import Dict, Any, Optional

def mask_pii(text: str) -> str:
    """Masks sensitive enterprise data (Employee IDs and Emails) before telemetry logging."""
    if not isinstance(text, str):
        return text
    # Mask Employee IDs like E101, E1023 -> [EMPLOYEE_ID]
    text = re.sub(r'\bE\d{3,4}\b', '[EMPLOYEE_ID]', text)
    # Mask Email addresses -> [EMAIL_MASKED]
    text = re.sub(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', '[EMAIL_MASKED]', text)
    return text

def trace_request(case_id: str, model: str, prompt_version: str, input_text: str, fault_flag: Optional[str] = None):
    """Executes a traced request with PII masking and fault injection simulation."""
    masked_input = mask_pii(input_text)
    
    trace_data = {
        "trace_id": f"trc_{int(time.time()*1000)}",
        "metadata": {
            "case_id": case_id,
            "model": model,
            "prompt_version": prompt_version,
            "fault_flag": fault_flag
        },
        "steps": []
    }
    
    start_time = time.time()
    
    # Step 1: Retrieval
    retrieval_start = time.time()
    retrieved_docs = ["leave_policy#annual_entitlement"]
    if fault_flag == "bad_retrieval":
        retrieved_docs = ["unrelated_cafeteria_menu"]
    trace_data["steps"].append({
        "name": "retrieve_policies",
        "type": "retriever",
        "latency_s": round(time.time() - retrieval_start, 3),
        "output": retrieved_docs
    })
    
    # Step 2: LLM Call
    llm_start = time.time()
    tool_call = None
    if case_id == "D15-03" or case_id == "T16-01":
        tool_call = "get_ticket_status(ticket_id='')"  # Unnecessary tool call symptom
    trace_data["steps"].append({
        "name": "llm_call_1",
        "type": "llm",
        "latency_s": round(time.time() - llm_start, 3),
        "input": masked_input,
        "tool_call": tool_call
    })
    
    # Step 3: Tool Execution / Fault Injection
    if tool_call or fault_flag:
        tool_start = time.time()
        error = None
        if fault_flag == "slow_tool":
            time.sleep(3.0)  # 3-second delay fault
        elif fault_flag == "flaky_tool" or fault_flag == "mcp_error":
            error = "ERROR: Tool execution failed or timed out."
        
        trace_data["steps"].append({
            "name": "enterprise_tool",
            "type": "tool",
            "latency_s": round(time.time() - tool_start, 3),
            "error": error
        })
        
    trace_data["total_latency_s"] = round(time.time() - start_time, 3)
    
    # Save local trace record for verification
    os.makedirs("Day16/traces", exist_ok=True)
    with open(f"Day16/traces/{case_id}_trace.json", "w", encoding="utf-8") as f:
        json.dump(trace_data, f, indent=2)
        
    return trace_data

if __name__ == "__main__":
    print("Executing standalone tracing test with PII masking...")
    test_input = "My email is user@company.com and my ID is E101. Am I allowed to share my password?"
    trace = trace_request("D15-03", "llama3", "v4", test_input, fault_flag=None)
    print("Trace generated successfully:")
    print(json.dumps(trace, indent=2))