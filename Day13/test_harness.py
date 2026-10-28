"""
Day 13: Automated Golden Regression Test Harness
- Runs local Ollama ReAct agent against a fixed test suite.
- Validates tool schema accuracy, balance enforcement, idempotency, and error handling.
- Logs test outcomes and outputs a structured evaluation summary.
"""

import json
import logging
import time
from typing import Any, Dict, List

# Import agent components from Day 12
from Day12.main import run_reliable_agent, APPROVED_REQUESTS, IDEMPOTENCY_CACHE

# Configure Test Harness Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("TestHarness")

# ==========================================
# 1. Golden Test Suite Definition
# ==========================================

GOLDEN_TEST_CASES = [
    {
        "id": "TC01",
        "name": "Normal Path - Valid Leave Request",
        "query": "My user ID is E101. Create a leave request for Diwali.",
        "expected_status": "PASS",
        "validation_key": "Diwali"
    },
    {
        "id": "TC02",
        "name": "Idempotency - Duplicate Submission",
        "query": "My user ID is E101. Create a leave request for Diwali.",
        "expected_status": "PASS",
        "validation_key": "already processed"
    },
    {
        "id": "TC03",
        "name": "Balance Guard - Insufficient Balance",
        "query": "My user ID is E102. Create a leave request for Holi.",
        "expected_status": "BLOCKED",
        "validation_key": "insufficient balance"
    },
    {
        "id": "TC04",
        "name": "Lookup - Check Leave Balance",
        "query": "What is the leave balance for user E103?",
        "expected_status": "PASS",
        "validation_key": "5"
    },
    {
        "id": "TC05",
        "name": "Edge Case - Unknown Festival",
        "query": "My user ID is E101. Create a leave request for Christmas.",
        "expected_status": "HANDLED_ERROR",
        "validation_key": "not found"
    }
]


# ==========================================
# 2. Evaluation Execution Engine
# ==========================================

def run_golden_suite() -> Dict[str, Any]:
    print("=" * 60)
    print("🚀 Starting Day 13 Golden Test Harness Suite")
    print("=" * 60)

    results = []
    passed_count = 0
    start_time = time.time()

    for tc in GOLDEN_TEST_CASES:
        print(f"\n[Running {tc['id']}] {tc['name']}")
        print(f"  Input Query: '{tc['query']}'")
        
        tc_start = time.time()
        try:
            agent_response = run_reliable_agent(tc["query"])
            duration = round(time.time() - tc_start, 2)
            
            # Outcome Verification
            key_matched = tc["validation_key"].lower() in agent_response.lower()
            
            if key_matched:
                status = "PASSED"
                passed_count += 1
                print(f"  ✅ Status: PASSED ({duration}s)")
            else:
                status = "FAILED"
                print(f"  ❌ Status: FAILED ({duration}s)")
                print(f"     Expected key phrase: '{tc['validation_key']}'")
                print(f"     Actual Response: '{agent_response}'")

            results.append({
                "id": tc["id"],
                "name": tc["name"],
                "status": status,
                "latency_seconds": duration,
                "response_snippet": agent_response[:100] + "..." if len(agent_response) > 100 else agent_response
            })

        except Exception as exc:
            duration = round(time.time() - tc_start, 2)
            print(f"  💥 Status: EXCEPTION ({duration}s) - {str(exc)}")
            results.append({
                "id": tc["id"],
                "name": tc["name"],
                "status": "EXCEPTION",
                "latency_seconds": duration,
                "error": str(exc)
            })

    total_time = round(time.time() - start_time, 2)
    pass_rate = round((passed_count / len(GOLDEN_TEST_CASES)) * 100, 1)

    summary = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_cases": len(GOLDEN_TEST_CASES),
        "passed": passed_count,
        "failed": len(GOLDEN_TEST_CASES) - passed_count,
        "pass_rate_percent": pass_rate,
        "total_duration_seconds": total_time,
        "details": results
    }

    # Output Summary Table
    print("\n" + "=" * 60)
    print("📊 GOLDEN TEST SUITE EVALUATION SUMMARY")
    print("=" * 60)
    print(f"Total Test Cases : {summary['total_cases']}")
    print(f"Passed           : {summary['passed']}")
    print(f"Failed           : {summary['failed']}")
    print(f"Pass Rate        : {summary['pass_rate_percent']}%")
    print(f"Total Latency    : {summary['total_duration_seconds']}s")
    print("=" * 60)

    # Save Results to JSON Report
    report_filename = "Day13/golden_test_results.json"
    with open(report_filename, "w") as f:
        json.dump(summary, f, indent=2)
    
    print(f"💾 Results saved to {report_filename}")
    return summary


if __name__ == "__main__":
    run_golden_suite()