from sqlalchemy import Column, String, JSON, DateTime, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Job(Base):
    """Job tracking table for document processing."""
    __tablename__ = "jobs"

    id = Column(String, primary_key=True)
    status = Column(String, default="pending", index=True)  # pending, processing, completed, failed
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<Job(id={self.id}, status={self.status})>"


class OCRResult(Base):
    """Stored OCR results for a job."""
    __tablename__ = "ocr_results"

    id = Column(String, primary_key=True)  # Use composite or separate id
    job_id = Column(String, index=True)
    page_index = Column(String, default="0")  # page_0, page_1, etc.
    data = Column(JSON)  # OCR regions/output
    created_at = Column(DateTime, server_default=func.now())
    
    def __repr__(self):
        return f"<OCRResult(job_id={self.job_id}, page={self.page_index})>"


class ParsedResult(Base):
    """Stored structured parsing results for a job."""
    __tablename__ = "parsed_results"

    id = Column(String, primary_key=True)
    job_id = Column(String, index=True, unique=True)  # One result per job
    structured = Column(JSON)  # Structured invoice/document data
    ocr_json = Column(JSON)  # Full OCR output for reference
    error = Column(Text, nullable=True)  # Error message if parsing failed
    created_at = Column(DateTime, server_default=func.now())
    
    def __repr__(self):
        return f"<ParsedResult(job_id={self.job_id})>"

