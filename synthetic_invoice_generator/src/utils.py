"""
Utility functions for PDF processing and training pair creation
"""
import fitz  # PyMuPDF
from PIL import Image as PILImage
import io
import os
from pathlib import Path
from typing import List, Dict, Optional


class PDFProcessor:
    """Convert PDF invoices to images for training"""
    
    @staticmethod
    def pdf_to_images(pdf_path: str, output_dir: str, dpi: int = 200) -> List[str]:
        """Convert PDF pages to high-quality images"""
        image_paths = []
        
        try:
            # Open PDF
            pdf_document = fitz.open(pdf_path)
            
            for page_num in range(len(pdf_document)):
                page = pdf_document[page_num]
                
                # Render page to image
                mat = fitz.Matrix(dpi / 72, dpi / 72)  # Scale factor
                pix = page.get_pixmap(matrix=mat)
                
                # Convert to PIL Image
                img_data = pix.tobytes("ppm")
                pil_image = PILImage.open(io.BytesIO(img_data))
                
                # Save image
                pdf_stem = Path(pdf_path).stem
                output_path = Path(output_dir) / f"{pdf_stem}_page_{page_num+1}.png"
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                pil_image.save(output_path, "PNG", dpi=(dpi, dpi))
                image_paths.append(str(output_path))
            
            pdf_document.close()
        except Exception as e:
            print(f"Error converting PDF {pdf_path} to images: {e}")
            raise
        
        return image_paths
    
    @staticmethod
    def create_training_pairs(
        pdf_dir: str, 
        gt_dir: str, 
        image_dir: str, 
        augmented_dir: Optional[str] = None
    ) -> List[Dict]:
        """Create training pairs linking images to ground truth"""
        training_pairs = []
        
        pdf_dir = Path(pdf_dir)
        gt_dir = Path(gt_dir)
        image_dir = Path(image_dir)
        
        for pdf_file in pdf_dir.glob("*.pdf"):
            # Extract invoice ID from filename
            invoice_id = pdf_file.stem
            
            # Corresponding ground truth file
            gt_file = gt_dir / f"{invoice_id}.json"
            
            if not gt_file.exists():
                print(f"Warning: No ground truth for {invoice_id}")
                continue
            
            try:
                # Convert PDF to images
                invoice_image_dir = image_dir / invoice_id
                image_paths = PDFProcessor.pdf_to_images(
                    str(pdf_file), 
                    str(invoice_image_dir)
                )
                
                for img_path in image_paths:
                    page_num = 1
                    # Extract page number from filename if present
                    img_stem = Path(img_path).stem
                    if '_page_' in img_stem:
                        try:
                            page_num = int(img_stem.split('_page_')[-1])
                        except ValueError:
                            pass
                    
                    training_pairs.append({
                        'invoice_id': invoice_id,
                        'pdf_path': str(pdf_file),
                        'image_path': img_path,
                        'ground_truth_path': str(gt_file),
                        'page_num': page_num,
                        'is_augmented': False
                    })
            except Exception as e:
                print(f"Error processing {pdf_file}: {e}")
                continue
        
        # Add augmented images if directory exists
        if augmented_dir and Path(augmented_dir).exists():
            for aug_file in Path(augmented_dir).glob("*.png"):
                # Extract original invoice ID from augmented filename
                # Format: aug_INV-YYYY-NNNNNN_page_N.png
                aug_stem = aug_file.stem
                if aug_stem.startswith('aug_'):
                    original_stem = aug_stem[4:]  # Remove 'aug_' prefix
                    invoice_id = '_'.join(original_stem.split('_')[:-1])  # Remove _page_N
                    
                    gt_file = gt_dir / f"{invoice_id}.json"
                    if gt_file.exists():
                        page_num = 1
                        if '_page_' in original_stem:
                            try:
                                page_num = int(original_stem.split('_page_')[-1])
                            except ValueError:
                                pass
                        
                        training_pairs.append({
                            'invoice_id': invoice_id,
                            'pdf_path': str(pdf_dir / f"{invoice_id}.pdf"),
                            'image_path': str(aug_file),
                            'ground_truth_path': str(gt_file),
                            'page_num': page_num,
                            'is_augmented': True
                        })
        
        return training_pairs
    
    @staticmethod
    def create_paddleocr_vl_ground_truth(
        invoice_metadata: Dict,
        image_path: str,
        bounding_boxes: Optional[List[Dict]] = None
    ) -> Dict:
        """
        Create ground truth in format suitable for PaddleOCR-VL training
        
        Args:
            invoice_metadata: The invoice metadata dictionary
            image_path: Path to the image file
            bounding_boxes: Optional list of bounding boxes for text regions
        
        Returns:
            Dictionary in PaddleOCR-VL ground truth format
        """
        gt = {
            "invoice_id": invoice_metadata.get('invoice_id', ''),
            "image_path": image_path,
            "ground_truth": {
                "document_type": "invoice",
                "vendor": invoice_metadata.get('vendor', {}),
                "client": invoice_metadata.get('client', {}),
                "line_items": [
                    {
                        "description": item.get('description', ''),
                        "quantity": item.get('quantity', 0),
                        "unit_price": item.get('unit_price', 0.0),
                        "line_total": item.get('total', 0.0)
                    }
                    for item in invoice_metadata.get('items', [])
                ],
                "totals": {
                    "subtotal": invoice_metadata.get('subtotal', 0.0),
                    "tax": invoice_metadata.get('tax_total', 0.0),
                    "discount": invoice_metadata.get('discount_total', 0.0),
                    "grand_total": invoice_metadata.get('grand_total', 0.0)
                },
                "metadata": {
                    "issue_date": invoice_metadata.get('issue_date', ''),
                    "due_date": invoice_metadata.get('due_date', ''),
                    "currency": invoice_metadata.get('currency', ''),
                    "payment_terms": invoice_metadata.get('payment_terms', '')
                }
            }
        }
        
        if bounding_boxes:
            gt["layout_regions"] = bounding_boxes
        
        return gt

