# Internal Operations Handbook

This fictional handbook describes everyday operating rules for Northstar Labs.
It is a training document, not an actual organizational policy. Team members
should use the section headings to locate the rule that applies to their work.

## Human Resources

### Annual Leave

Employees receive 24 days of paid annual leave per calendar year.
Annual leave must be requested two weeks in advance.
Annual leave longer than three consecutive days requires manager approval.

### Sick Leave

Employees taking sick leave should notify their manager as early as practical.

## Access and Security

### Temporary Access

Temporary access must be requested through the service desk with a named owner,
a business reason, and an expiry date. The owner must confirm that the requested
permissions are limited to the systems required for the assignment. Security
reviews the request before any credentials are issued. Temporary access expires
after seven calendar days. Extensions require a new approval before the original
expiry; an open support ticket does not extend access automatically. When the
assignment ends early, the owner must request revocation on the same day.

### Incident Reporting

Report suspected credential exposure immediately to the service desk. Include
the affected system and the time of discovery, but never paste a password or
access token into the ticket. Security coordinates containment and records the
actions taken so that the next responder can continue the investigation.

Emergency contact: **extension 771**.

## Travel and Expenses

### International Travel

International business trips require approval from the employee's manager and
the business unit before travel is booked.

### Travel Receipts

Itemized receipts are required for reimbursable travel expenses.
Card statements alone are insufficient evidence for reimbursement.

### Reimbursement Rules

Employees must submit itemized receipts within thirty calendar days of travel.
The manager must verify the business purpose before approving reimbursement.
If a receipt is missing, attach a signed explanation and obtain finance approval;
a manager's approval alone does not waive the receipt requirement.

### Approval Checklist

- Record the business purpose and cost center.
- Attach itemized receipts; card statements alone are insufficient.
- For claims over INR 10,000, obtain finance approval.
- Submit the claim using the [expense portal](https://example.invalid/expenses).

## Service Operations

### Response Targets

| Priority | First response | Escalation owner |
| --- | --- | --- |
| P1 | 15 minutes | On-call lead |
| P2 | 4 business hours | Service desk |
| P3 | 2 business days | Team coordinator |

Response targets measure initial acknowledgement, not final resolution.
The escalation owner must document any change in priority in the ticket.

### Shift Handoff

1. Record unresolved incidents and their current owners.
2. List the next action for each incident.
3. Confirm that the incoming responder can access the incident log.

Use the following template without including secrets:

```text
incident_id: OPS-123
owner: incoming-responder
next_action: verify service recovery
```

<!-- Editorial note: remove this comment during parsing. -->

The outgoing responder remains responsible until the incoming responder
acknowledges the handoff.
