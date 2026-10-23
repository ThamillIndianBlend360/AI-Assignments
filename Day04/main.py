"""Run from Project1 with: python -m uvicorn Day04.main:app --reload."""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query, Response, status
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .models import (
    CustomerCreate,
    CustomerDB,
    CustomerResponse,
    TaskCreate,
    TaskDB,
    TaskResponse,
    TaskUpdate,
)


def create_app(database_engine: Engine = engine) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        Base.metadata.create_all(bind=database_engine)
        yield

    app = FastAPI(
        title="Unified Task & Customer API", version="1.0", lifespan=lifespan
    )

    def find_task(task_id: int, db: Session) -> TaskDB:
        task = db.get(TaskDB, task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found")
        return task

    @app.post("/tasks/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
    def create_task(task: TaskCreate, db: Session = Depends(get_db)):
        db_task = TaskDB(**task.model_dump())
        db.add(db_task)
        db.commit()
        db.refresh(db_task)
        return db_task

    @app.get("/tasks/", response_model=list[TaskResponse])
    def list_tasks(
        skip: int = Query(default=0, ge=0),
        limit: int = Query(default=100, ge=1),
        db: Session = Depends(get_db),
    ):
        return db.scalars(select(TaskDB).order_by(TaskDB.id).offset(skip).limit(limit)).all()

    @app.get("/tasks/{task_id}", response_model=TaskResponse)
    def get_task(task_id: int, db: Session = Depends(get_db)):
        return find_task(task_id, db)

    @app.put("/tasks/{task_id}", response_model=TaskResponse)
    def update_task(task_id: int, task_update: TaskUpdate, db: Session = Depends(get_db)):
        task = find_task(task_id, db)
        for key, value in task_update.model_dump(exclude_unset=True).items():
            setattr(task, key, value)
        db.commit()
        db.refresh(task)
        return task

    @app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_task(task_id: int, db: Session = Depends(get_db)):
        task = find_task(task_id, db)
        db.delete(task)
        db.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @app.post(
        "/customers/", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED
    )
    def create_customer(customer: CustomerCreate, db: Session = Depends(get_db)):
        db_customer = CustomerDB(**customer.model_dump())
        db.add(db_customer)
        db.commit()
        db.refresh(db_customer)
        return db_customer

    return app


app = create_app()
