"""Day 12: deterministic leave tools with validation and an audit trail.

Run: python Day12/main.py
This local demo resets its in-memory balances and idempotency keys each run.
The audit log is appended to across runs. No LLM or external service is needed.
"""

import json
import logging
from datetime import date
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, ValidationError


LOG_PATH = Path(__file__).resolve().parent.parent / "day12_audit_trail.log"


class LeaveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    idempotency_key: str = Field(min_length=1)
    user_id: str = Field(pattern=r"^E\d{3}$")
    start_date: date
    days: int = Field(strict=True, gt=0, le=30)
    reason: str = Field(min_length=3)


class LeaveService:
    """Single-process demo; successful requests are cached for this instance."""

    def __init__(self, logger):
        self.logger = logger
        self.run_id = str(uuid4())
        self.balances = {"E101": 3, "E102": 0, "E103": 5}
        self.requests = {}

    def audit(self, event, **details):
        self.logger.info(json.dumps({"run_id": self.run_id, "event": event, **details}))

    def create_leave_request(self, raw_args):
        try:
            request = LeaveRequest.model_validate(raw_args)
        except ValidationError as exc:
            result = {"status": "VALIDATION_FAILED", "errors": json.loads(exc.json())}
            self.audit("validation_failed", **result)
            return result

        payload = request.model_dump(mode="json")
        key = request.idempotency_key
        if key in self.requests:
            previous_payload, previous_result = self.requests[key]
            if payload != previous_payload:
                self.audit("idempotency_conflict", key=key)
                return {"status": "IDEMPOTENCY_CONFLICT"}
            self.audit("duplicate_replayed", key=key, result=previous_result)
            return dict(previous_result)

        if request.user_id not in self.balances:
            self.audit("unknown_employee", user_id=request.user_id)
            return {"status": "UNKNOWN_EMPLOYEE"}

        balance = self.balances[request.user_id]
        if request.days > balance:
            result = {"status": "INSUFFICIENT_BALANCE", "available": balance,
                      "requested": request.days}
            self.audit("balance_rejected", request=payload, **result)
            return result

        self.balances[request.user_id] -= request.days
        result = {"status": "APPROVED", "request_id": f"LR-{len(self.requests) + 1001}",
                  "remaining_balance": self.balances[request.user_id]}
        self.requests[key] = (payload, dict(result))
        self.audit("leave_created", request=payload, balance_before=balance, **result)
        return result


def main():
    logger = logging.getLogger("day12")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    handler = logging.FileHandler(LOG_PATH, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
    logger.addHandler(handler)
    try:
        service = LeaveService(logger)
        service.audit("demo_started", balances=service.balances.copy())
        request = {"idempotency_key": "day12-demo-001", "user_id": "E101",
                   "start_date": "2026-11-10", "days": 2, "reason": "Personal trip"}

        approved = service.create_leave_request(request)
        assert approved["status"] == "APPROVED"
        print(f"Created request: {approved}")

        replay = service.create_leave_request(request)
        assert replay == approved and service.balances["E101"] == 1
        print("PASS: Idempotency - duplicate request did not deduct leave again.")

        conflict = service.create_leave_request({**request, "days": 1})
        assert conflict["status"] == "IDEMPOTENCY_CONFLICT"
        print("PASS: Reusing a key with changed arguments was rejected.")

        rejected = service.create_leave_request({**request, "idempotency_key": "too-many"})
        assert rejected["status"] == "INSUFFICIENT_BALANCE"
        assert service.balances["E101"] == 1
        print("PASS: Balance enforcement - insufficient balance blocked the request.")

        for invalid in ({"days": 0}, {"days": "2"}, {"start_date": "invalid"}):
            result = service.create_leave_request({**request, **invalid})
            assert result["status"] == "VALIDATION_FAILED"
        assert len(service.requests) == 1 and service.balances["E101"] == 1
        print("PASS: Pydantic rejected invalid days, types, and dates.")
        service.audit("demo_completed", checks="PASSED", balances=service.balances)
        print(f"Audit trail saved to: {LOG_PATH}")
    finally:
        logger.removeHandler(handler)
        handler.close()


if __name__ == "__main__":
    main()
