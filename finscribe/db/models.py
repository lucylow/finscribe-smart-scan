from sqlalchemy import Column, String, JSON, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True)
    status = Column(String, default="pending")
    created_at = Column(DateTime, server_default=func.now())


class OCRResult(Base):
    __tablename__ = "ocr_results"

    job_id = Column(String, primary_key=True)
    data = Column(JSON)
    created_at = Column(DateTime, server_default=func.now())


class ParsedResult(Base):
    __tablename__ = "parsed_results"

    job_id = Column(String, primary_key=True)
    structured = Column(JSON)
    created_at = Column(DateTime, server_default=func.now())

