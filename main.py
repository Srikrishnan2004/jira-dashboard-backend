import logging
import json
import os
import requests
from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from requests.auth import HTTPBasicAuth
from pydantic_settings import BaseSettings
from typing import List, Optional

# --- SQLAlchemy Database Imports ---
from sqlalchemy import create_engine, Column, Integer, String, Text, Enum, TIMESTAMP, ForeignKey, JSON
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.sql import func

logging.basicConfig(level=logging.INFO)


# --- Main Configuration using BaseSettings ---
class Settings(BaseSettings):
    # Database Credentials
    db_user: str
    db_password: str
    db_host: str
    db_name: str

    class Config:
        env_file = ".env"


settings = Settings()
app = FastAPI()

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Database Setup ---
DATABASE_URL = f"mysql+pymysql://{settings.db_user}:{settings.db_password}@{settings.db_host}/{settings.db_name}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# --- SQLAlchemy ORM Models ---
class GenerationRequestDB(Base):
    __tablename__ = "generation_requests"
    request_id = Column(Integer, primary_key=True, index=True)
    request_type = Column(Enum('developer', 'client'), nullable=False)
    raw_input = Column(Text, nullable=False)
    repository = Column(String(255))
    assignee_email = Column(String(255))
    request_timestamp = Column(TIMESTAMP, server_default=func.now())


class ClassificationLogDB(Base):
    __tablename__ = "classification_logs"
    log_id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey("generation_requests.request_id"))
    model_name = Column(String(100), nullable=False)
    decision = Column(Enum('approved', 'rejected'), nullable=False)
    rejection_reason = Column(String(255))
    raw_response_json = Column(JSON)
    processed_timestamp = Column(TIMESTAMP, server_default=func.now())


class GeneratedTicketDB(Base):
    __tablename__ = "generated_tickets"
    ticket_log_id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey("generation_requests.request_id"))
    classification_log_id = Column(Integer, ForeignKey("classification_logs.log_id"))
    jira_issue_key = Column(String(50), nullable=False, unique=True)
    jira_issue_id = Column(String(50), nullable=False)
    summary = Column(Text, nullable=False)
    issue_type = Column(String(50), nullable=False)
    parent_issue_key = Column(String(50))
    assignee_account_id = Column(String(100))
    generated_by_model = Column(String(100), nullable=False)
    raw_generated_json = Column(JSON)
    creation_timestamp = Column(TIMESTAMP, server_default=func.now())


# Dependency to get a DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- Pydantic Response Models for Database Routes ---
class GenerationRequestResponse(BaseModel):
    request_id: int
    request_type: str
    raw_input: str
    repository: Optional[str]
    assignee_email: Optional[str]
    request_timestamp: str

    class Config:
        orm_mode = True


class ClassificationLogResponse(BaseModel):
    log_id: int
    request_id: int
    model_name: str
    decision: str
    rejection_reason: Optional[str]
    raw_response_json: Optional[dict]
    processed_timestamp: str

    class Config:
        orm_mode = True


class GeneratedTicketResponse(BaseModel):
    ticket_log_id: int
    request_id: int
    classification_log_id: int
    jira_issue_key: str
    summary: str
    issue_type: str
    parent_issue_key: Optional[str]
    assignee_account_id: Optional[str]
    creation_timestamp: str

    class Config:
        orm_mode = True


class FullLogResponse(BaseModel):
    request: GenerationRequestResponse
    classification: Optional[ClassificationLogResponse]
    ticket: Optional[GeneratedTicketResponse]


# --- Existing Jira Endpoint ---
@app.get("/simplified-jira-issues")
def get_simplified_issues(
        jira_url: str = Query(..., description="Jira API URL"),
        email: str = Query(..., description="Your Jira email address"),
        api_token: str = Query(..., description="Your Jira API token")
):
    try:
        response = requests.get(jira_url, auth=HTTPBasicAuth(email, api_token), headers={"Accept": "application/json"})
        response.raise_for_status()
        data = response.json()
        table_data = []
        for issue in data.get("issues", []):
            fields = issue.get("fields", {})
            issue_type = fields.get("issuetype", {}).get("name", "")
            parent_key = None if issue_type == "Epic" else fields.get("parent", {}).get("key")
            entry = {
                "issue_key": issue.get("key", ""),
                "summary": fields.get("summary", ""),
                "issue_type": issue_type,
                "parent": parent_key,
                "status": fields.get("status", {}).get("name", ""),
                "assignee": fields.get("assignee", {}).get("displayName", "N/A") if fields.get("assignee") else "N/A",
                "reporter": fields.get("reporter", {}).get("displayName", "N/A") if fields.get("reporter") else "N/A",
            }
            table_data.append(entry)
        return {"data": table_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- NEW: Database Query Endpoints ---

@app.get("/requests", response_model=List[GenerationRequestResponse])
def get_all_requests(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Retrieves all initial generation requests from the database.
    """
    requests = db.query(GenerationRequestDB).offset(skip).limit(limit).all()
    return requests


@app.get("/classifications", response_model=List[ClassificationLogResponse])
def get_all_classifications(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Retrieves all classification (gatekeeper) logs from the database.
    """
    classifications = db.query(ClassificationLogDB).offset(skip).limit(limit).all()
    return classifications


@app.get("/tickets", response_model=List[GeneratedTicketResponse])
def get_all_tickets(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Retrieves all successfully generated Jira ticket logs from the database.
    """
    tickets = db.query(GeneratedTicketDB).offset(skip).limit(limit).all()
    return tickets


@app.get("/full_log/{request_id}", response_model=FullLogResponse)
def get_full_log_by_request_id(request_id: int, db: Session = Depends(get_db)):
    """
    Retrieves the complete audit trail for a single request, including the
    initial request, its classification, and the final ticket if created.
    """
    request = db.query(GenerationRequestDB).filter(GenerationRequestDB.request_id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")

    classification = db.query(ClassificationLogDB).filter(ClassificationLogDB.request_id == request_id).first()
    ticket = db.query(GeneratedTicketDB).filter(GeneratedTicketDB.request_id == request_id).first()

    return FullLogResponse(
        request=request,
        classification=classification,
        ticket=ticket
    )
