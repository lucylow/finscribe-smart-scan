"""
Airflow DAG for FinScribe Invoice ETL Pipeline

This DAG orchestrates batch invoice processing with:
- Automatic retries
- Email notifications on failure
- Comprehensive logging
- Scheduling support
"""
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.email import send_email
from datetime import datetime, timedelta
from typing import Dict, Any
import glob
import os

from data_pipeline.ingestion import ingest_from_local
from data_pipeline.preprocess import preprocess
from data_pipeline.ocr_client import run_ocr
from data_pipeline.semantic_parser import parse
from data_pipeline.normalizer import normalize_invoice_data
from data_pipeline.validator import validate
from data_pipeline.persistence import save_invoice


def etl_pipeline(**context):
    """
    Execute ETL pipeline for a single invoice.
    
    Args:
        context: Airflow context dictionary
        
    Returns:
        Invoice ID
    """
    path = context["params"].get("invoice_path")
    if not path:
        raise ValueError("invoice_path parameter required")
    
    # Extract
    src = ingest_from_local(path)
    clean = preprocess(src)
    ocr_json = run_ocr(clean)
    
    # Transform
    structured = parse(ocr_json)
    normalized = normalize_invoice_data(structured)
    
    # Validate
    validation = validate(normalized)
    
    # Load
    inv_id = save_invoice(normalized, ocr_json, src)
    
    return {
        "invoice_id": inv_id,
        "validation": validation,
        "status": "success"
    }


def etl_batch(**context):
    """
    Execute ETL pipeline for multiple invoices in a directory.
    
    Args:
        context: Airflow context dictionary
        
    Returns:
        Summary of processed invoices
    """
    input_dir = context["params"].get("input_dir", "/mnt/incoming")
    pattern = context["params"].get("pattern", "*.png")
    
    files = glob.glob(os.path.join(input_dir, pattern))
    
    results = []
    for file_path in files:
        try:
            result = etl_pipeline(**{"params": {"invoice_path": file_path}})
            results.append({
                "file": file_path,
                "success": True,
                "invoice_id": result["invoice_id"]
            })
        except Exception as e:
            results.append({
                "file": file_path,
                "success": False,
                "error": str(e)
            })
    
    return {
        "total": len(files),
        "successful": sum(1 for r in results if r["success"]),
        "failed": sum(1 for r in results if not r["success"]),
        "results": results
    }


def notify_failure(context):
    """
    Send email notification on DAG failure.
    
    Args:
        context: Airflow context dictionary
    """
    subject = "FinScribe ETL Pipeline Failed"
    html_content = f"""
    <h2>ETL Pipeline Failure</h2>
    <p><strong>DAG:</strong> {context['dag'].dag_id}</p>
    <p><strong>Task:</strong> {context['task_instance'].task_id}</p>
    <p><strong>Execution Date:</strong> {context['execution_date']}</p>
    <p><strong>Error:</strong> {context.get('exception', 'Unknown error')}</p>
    <pre>{context.get('exception', '')}</pre>
    """
    
    send_email(
        to=["team@finscribe.ai"],  # Configure in Airflow
        subject=subject,
        html_content=html_content
    )


# Default arguments for DAG
default_args = {
    "owner": "finscribe",
    "depends_on_past": False,
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 3,
    "retry_delay": timedelta(seconds=15),
    "on_failure_callback": notify_failure,
}

# Create DAG
with DAG(
    dag_id="finscribe_invoice_etl",
    default_args=default_args,
    description="FinScribe Invoice ETL Pipeline",
    schedule_interval=None,  # Manual trigger or set to "@hourly", "@daily", etc.
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["etl", "invoices", "finscribe"],
) as dag:

    # Single invoice processing task
    run_etl = PythonOperator(
        task_id="run_invoice_etl",
        python_callable=etl_pipeline,
        params={"invoice_path": "examples/sample_invoice_1.png"},
    )

    # Batch processing task (alternative)
    run_batch = PythonOperator(
        task_id="run_batch_etl",
        python_callable=etl_batch,
        params={
            "input_dir": "/mnt/incoming",
            "pattern": "*.png"
        },
    )

    # Task dependencies (uncomment if using both)
    # run_etl >> run_batch

