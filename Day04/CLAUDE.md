# Day 04: Unified Task & Customer API

Keep this assignment self-contained in the `Day04` package. Use relative imports;
do not depend on the root-level `main.py` or `test_main.py`.

## Architecture

- `database.py`: SQLite engine, declarative Base, sessions, and `get_db` dependency.
- `models.py`: TaskDB and CustomerDB tables and Pydantic schemas.
- `main.py`: FastAPI app factory, startup table creation, and API routes.
- `test_main.py`: TestClient tests with a fresh in-memory SQLite database per test.

The production database is `Day04/tasks_customers.db`, resolved relative to
`database.py`. Tests must not create or modify the production database. Use
StaticPool so TestClient threads share the same in-memory connection. Close
sessions, clear dependency overrides, and dispose the test engine after tests.

Task statuses must match `^(pending|in_progress|completed)$`. Customers use
EmailStr validation. Task updates apply only supplied fields; description can
be cleared with null, but title and status cannot be null. Missing tasks return
404; invalid request bodies return 422. Successful creates return 201, and
successful deletion returns an empty 204 response. SQLite stores created_at as
a UTC timestamp without a timezone offset.

## Verification

From the Project1 directory, using its existing virtual environment:

```powershell
.\venv\Scripts\Activate.ps1
python -m pytest Day04/test_main.py -v
python -m uvicorn Day04.main:app --reload
```

Interactive API documentation: http://127.0.0.1:8000/docs

Verify task CRUD, pagination, all valid statuses, invalid create/update bodies,
missing-task GET/PUT/DELETE, valid customer persistence, and invalid emails.
The root test suite belongs to earlier work and is separate from this assignment.
