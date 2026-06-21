import os
import json
import datetime
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class Project(Base):
    __tablename__ = 'projects'

    id = Column(String(50), primary_key=True)
    filename = Column(String(255), nullable=False)
    status = Column(String(50), default='uploaded')
    file_path = Column(String(500), nullable=True)
    cleaned_path = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    dataset_info = Column(Text, nullable=True) # JSON
    selected_analyses = Column(Text, nullable=True) # JSON list
    business_requirements = Column(Text, nullable=True) # JSON
    analytics_strategy = Column(Text, nullable=True) # JSON
    quality_report = Column(Text, nullable=True) # JSON
    dashboard_spec = Column(Text, nullable=True) # JSON
    executive_report = Column(Text, nullable=True) # Text
    approval_certificate = Column(Text, nullable=True) # JSON

class AgentLog(Base):
    __tablename__ = 'agent_logs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String(50), nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    agent_name = Column(String(100), nullable=False)
    target_agent = Column(String(100), nullable=True)
    message = Column(Text, nullable=False)
    log_type = Column(String(50), default='system') # system, chat, error, artifact
    payload = Column(Text, nullable=True) # JSON

# Establish database directory
DB_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(DB_DIR, "analytics_platform.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False, "timeout": 30})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
