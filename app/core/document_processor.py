import os
import uuid
from typing import Dict, Any, List
from PIL import Image
from io import BytesIO
from .models.ocr_service import OCRService
import aiofiles
from .models.llm_service import LLMService
from ..api.v1.endpoints import ExtractedField, AnalysisResult # Import Pydantic models

# Initialize services (using mock URLs as per project context)
ocr_service = OCRService(model_url="http://localhost:8002/v1/ocr")
llm_service = LLMService(model_url="http://localhost:8001/v1/infer")

class DocumentProcessor:
    """
    Orchestrates the AI pipeline: ETL -> OCR -> Semantic Parsing -> Validation.
    """
    
    def __init__(self, upload_dir: str = "/tmp/finscribe_uploads", active_learning_file: str = "../active_learning.jsonl"):
        self.upload_dir = upload_dir
        self.active_learning_file = os.path.join(os.path.dirname(__file__), active_learning_file)
        os.makedirs(self.upload_dir, exist_ok=True)
        self.upload_dir = upload_dir
        os.makedirs(self.upload_dir, exist_ok=True)

    async def process_document(self, file_content: bytes, filename: str, model_type: str = "fine_tuned") -> AnalysisResult:
        """
        Processes a document from raw bytes through the AI pipeline.
        
        Args:
            file_content: The raw bytes of the uploaded file.
            filename: The original filename.
            model_type: 'fine_tuned' or 'baseline' to determine which model to use (mocked for now).
            
        Returns:
            An AnalysisResult Pydantic model.
        """
        document_id = str(uuid.uuid4())
        file_path = os.path.join(self.upload_dir, f"{document_id}_{filename}")
        
        # 1. ETL: Save file to disk (simple ingestion)
        try:
            # Simple file type check and conversion to image if needed (mocked)
            if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                img = Image.open(BytesIO(file_content))
                img.save(file_path)
            else:
                # For PDF, we would convert to image pages here (out of scope for credit limit)
                # For now, we'll just save the raw file and assume the OCR service handles it
                with open(file_path, "wb") as f:
                    f.write(file_content)
        except Exception as e:
            return AnalysisResult(
                document_id=document_id,
                status="failed",
                extracted_data=[],
                raw_ocr_output={},
                validation_status=f"ETL Failed: {str(e)}"
            )

        # 2. AI Pipeline: OCR
        raw_ocr_output = ocr_service.process_document(file_path)
        
        # 3. AI Pipeline: Semantic Parsing (LLM)
        structured_data = llm_service.parse_financial_data(raw_ocr_output)
        
        # 4. Validation & Lineage
        extracted_fields: List[ExtractedField] = []
        for item in structured_data:
            # Mock lineage ID and validation
            lineage_id = str(uuid.uuid4())
            extracted_fields.append(ExtractedField(
                field_name=item["field_name"],
                value=item["value"],
                confidence=item["confidence"],
                source_model=item["source_model"],
                lineage_id=lineage_id
            ))
            
        # 5. Active Learning Check (Mock)
        active_learning_ready = len(extracted_fields) > 0 and model_type == "fine_tuned"
        
        # 6. Active Learning Data Logging
        if active_learning_ready:
            await self._log_active_learning_data(document_id, filename, extracted_fields)
            
        # 7. Cleanup (Optional, but good practice)
        os.remove(file_path)

        return AnalysisResult(
            document_id=document_id,
            status="completed",
            extracted_data=extracted_fields,
            raw_ocr_output=raw_ocr_output,
            validation_status="validated",
            active_learning_ready=active_learning_ready
        )

    async def _log_active_learning_data(self, document_id: str, filename: str, extracted_fields: List[ExtractedField]):
        """Logs data to active_learning.jsonl for LoRA SFT."""
        log_entry = {
            "document_id": document_id,
            "source_file": filename,
            "extracted_data": [f.model_dump() for f in extracted_fields],
            "timestamp": "2025-12-20T10:00:00Z" # Placeholder for real timestamp
        }
        
        try:
            async with aiofiles.open(self.active_learning_file, mode="a") as f:
                await f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            print(f"Warning: Could not log to active learning file: {e}")

    async def compare_documents(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """
        Processes the document with both fine-tuned and baseline models.
        """
        # Mocking the baseline model by simply changing the model_type flag
        fine_tuned_result = await self.process_document(file_content, filename, model_type="fine_tuned")
        baseline_result = await self.process_document(file_content, filename, model_type="baseline")
        
        # Mock comparison logic
        comparison_summary = {
            "fine_tuned_confidence_avg": sum(f.confidence for f in fine_tuned_result.extracted_data) / len(fine_tuned_result.extracted_data),
            "baseline_confidence_avg": sum(f.confidence for f in baseline_result.extracted_data) / len(baseline_result.extracted_data),
            "accuracy_gain": "20% (Mock)"
        }
        
        return {
            "document_id": fine_tuned_result.document_id,
            "status": "completed",
            "fine_tuned_result": fine_tuned_result,
            "baseline_result": baseline_result,
            "comparison_summary": comparison_summary
        }

processor = DocumentProcessor()
