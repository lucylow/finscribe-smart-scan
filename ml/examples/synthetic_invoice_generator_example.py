#!/usr/bin/env python3
"""
Synthetic Invoice Generator - Practical Example
===============================================

This script demonstrates a complete workflow for generating synthetic training data:
1. Generate structured data using Faker
2. Design visual layouts with ReportLab
3. Render to PDF
4. Create annotation files (ground truth JSON)

This approach avoids copyright issues by generating completely synthetic data.

Usage:
    python synthetic_invoice_generator_example.py --count 100 --output ./synthetic_data

Requirements:
    pip install faker reportlab pillow pdf2image
"""

import argparse
import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

from faker import Faker
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class InvoiceItem:
    """Represents a single line item in an invoice"""
    description: str
    quantity: int
    unit_price: float
    tax_rate: float = 0.0
    
    @property
    def subtotal(self) -> float:
        return self.quantity * self.unit_price
    
    @property
    def tax_amount(self) -> float:
        return self.subtotal * self.tax_rate / 100
    
    @property
    def total(self) -> float:
        return self.subtotal + self.tax_amount


@dataclass
class InvoiceData:
    """Complete invoice data structure"""
    invoice_id: str
    issue_date: str
    due_date: str
    vendor_name: str
    vendor_address: str
    vendor_email: str
    vendor_phone: str
    client_name: str
    client_address: str
    client_email: str
    currency: str
    items: List[InvoiceItem]
    notes: str = ""
    
    @property
    def subtotal(self) -> float:
        return sum(item.subtotal for item in self.items)
    
    @property
    def tax_total(self) -> float:
        return sum(item.tax_amount for item in self.items)
    
    @property
    def grand_total(self) -> float:
        return self.subtotal + self.tax_total


# ============================================================================
# Data Generation with Faker
# ============================================================================

class InvoiceDataGenerator:
    """Generates realistic invoice data using Faker"""
    
    def __init__(self, locale: str = 'en_US'):
        self.fake = Faker(locale)
        self.currencies = ['USD', 'EUR', 'GBP', 'JPY', 'CNY']
        self.product_categories = [
            'Software License', 'Consulting Services', 'Hardware', 
            'Cloud Services', 'Training', 'Support', 'Maintenance',
            'Development', 'Design', 'Marketing'
        ]
    
    def generate_invoice_id(self) -> str:
        """Generate a realistic invoice ID"""
        prefix = random.choice(['INV', 'INVOICE', 'BILL', 'INV-'])
        year = datetime.now().year
        number = random.randint(1000, 99999)
        return f"{prefix}-{year}-{number:05d}"
    
    def generate_line_items(self, count: int = None) -> List[InvoiceItem]:
        """Generate realistic line items"""
        if count is None:
            count = random.randint(3, 15)
        
        items = []
        for _ in range(count):
            # Generate product description
            category = random.choice(self.product_categories)
            description = f"{category}: {self.fake.sentence(nb_words=3).rstrip('.')}"
            
            # Generate pricing
            quantity = random.randint(1, 10)
            unit_price = round(random.uniform(50, 5000), 2)
            tax_rate = random.choice([0.0, 5.0, 10.0, 15.0, 20.0])
            
            items.append(InvoiceItem(
                description=description,
                quantity=quantity,
                unit_price=unit_price,
                tax_rate=tax_rate
            ))
        
        return items
    
    def generate_invoice(self, invoice_id: Optional[str] = None) -> InvoiceData:
        """Generate a complete invoice with all fields"""
        if invoice_id is None:
            invoice_id = self.generate_invoice_id()
        
        # Generate dates
        issue_date = self.fake.date_between(start_date='-1y', end_date='today')
        due_date = issue_date + timedelta(days=random.randint(15, 45))
        
        # Generate vendor (company selling)
        vendor_name = self.fake.company()
        vendor_address = self.fake.address().replace('\n', ', ')
        vendor_email = self.fake.company_email()
        vendor_phone = self.fake.phone_number()
        
        # Generate client (company buying)
        client_name = self.fake.company()
        client_address = self.fake.address().replace('\n', ', ')
        client_email = self.fake.email()
        
        # Generate line items
        items = self.generate_line_items()
        
        # Generate currency
        currency = random.choice(self.currencies)
        
        # Generate notes (optional)
        notes = ""
        if random.random() < 0.3:  # 30% chance of having notes
            notes = self.fake.sentence(nb_words=10)
        
        return InvoiceData(
            invoice_id=invoice_id,
            issue_date=issue_date.strftime('%Y-%m-%d'),
            due_date=due_date.strftime('%Y-%m-%d'),
            vendor_name=vendor_name,
            vendor_address=vendor_address,
            vendor_email=vendor_email,
            vendor_phone=vendor_phone,
            client_name=client_name,
            client_address=client_address,
            client_email=client_email,
            currency=currency,
            items=items,
            notes=notes
        )


# ============================================================================
# PDF Generation with ReportLab
# ============================================================================

class InvoicePDFGenerator:
    """Generates PDF invoices using ReportLab with different layouts"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles"""
        # Title style
        self.styles.add(ParagraphStyle(
            name='InvoiceTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=30,
            alignment=1  # Center
        ))
        
        # Header style
        self.styles.add(ParagraphStyle(
            name='InvoiceHeader',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=colors.HexColor('#333333'),
            spaceAfter=12
        ))
        
        # Section header
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#555555'),
            spaceAfter=10
        ))
    
    def generate_classic_layout(self, invoice: InvoiceData, output_path: Path):
        """Generate a classic invoice layout (vendor left, client right)"""
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=LETTER,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        story = []
        
        # Title
        story.append(Paragraph("INVOICE", self.styles['InvoiceTitle']))
        story.append(Spacer(1, 0.2*inch))
        
        # Invoice metadata
        metadata_data = [
            ['Invoice ID:', invoice.invoice_id],
            ['Issue Date:', invoice.issue_date],
            ['Due Date:', invoice.due_date],
        ]
        metadata_table = Table(metadata_data, colWidths=[2*inch, 3*inch])
        metadata_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(metadata_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Vendor and Client side by side
        vendor_client_data = [
            ['Vendor', 'Client'],
            [
                f"<b>{invoice.vendor_name}</b><br/>{invoice.vendor_address}<br/>{invoice.vendor_email}<br/>{invoice.vendor_phone}",
                f"<b>{invoice.client_name}</b><br/>{invoice.client_address}<br/>{invoice.client_email}"
            ]
        ]
        vendor_client_table = Table(vendor_client_data, colWidths=[3*inch, 3*inch])
        vendor_client_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f0f0')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#333333')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('FONTSIZE', (0, 1), (-1, 1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 1), (-1, 1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#cccccc')),
        ]))
        story.append(vendor_client_table)
        story.append(Spacer(1, 0.4*inch))
        
        # Line items table
        items_data = [['Description', 'Qty', 'Unit Price', 'Tax %', 'Total']]
        for item in invoice.items:
            items_data.append([
                item.description,
                str(item.quantity),
                f"{invoice.currency} {item.unit_price:.2f}",
                f"{item.tax_rate:.1f}%",
                f"{invoice.currency} {item.total:.2f}"
            ])
        
        items_table = Table(items_data, colWidths=[3*inch, 0.8*inch, 1.2*inch, 0.8*inch, 1.2*inch])
        items_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4a90e2')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
            ('ALIGN', (3, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (4, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')]),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dddddd')),
        ]))
        story.append(items_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Totals
        totals_data = [
            ['Subtotal:', f"{invoice.currency} {invoice.subtotal:.2f}"],
            ['Tax Total:', f"{invoice.currency} {invoice.tax_total:.2f}"],
            ['Grand Total:', f"<b>{invoice.currency} {invoice.grand_total:.2f}</b>"],
        ]
        totals_table = Table(totals_data, colWidths=[1.5*inch, 1.5*inch])
        totals_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTNAME', (0, 2), (1, 2), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('FONTSIZE', (0, 2), (1, 2), 14),
            ('TEXTCOLOR', (0, 2), (1, 2), colors.HexColor('#2c3e50')),
            ('TOPPADDING', (0, 2), (1, 2), 12),
            ('BOTTOMPADDING', (0, 2), (1, 2), 12),
        ]))
        story.append(totals_table)
        
        # Notes
        if invoice.notes:
            story.append(Spacer(1, 0.3*inch))
            story.append(Paragraph(f"<b>Notes:</b> {invoice.notes}", self.styles['Normal']))
        
        # Build PDF
        doc.build(story)
    
    def generate_modern_layout(self, invoice: InvoiceData, output_path: Path):
        """Generate a modern, compact invoice layout"""
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            rightMargin=50,
            leftMargin=50,
            topMargin=50,
            bottomMargin=50
        )
        
        story = []
        
        # Header with invoice ID and date
        header_data = [
            [f"<b>INVOICE</b>", f"ID: {invoice.invoice_id}<br/>Date: {invoice.issue_date}<br/>Due: {invoice.due_date}"]
        ]
        header_table = Table(header_data, colWidths=[4*inch, 2*inch])
        header_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
            ('FONTSIZE', (0, 0), (0, 0), 20),
            ('FONTSIZE', (1, 0), (1, 0), 9),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 0.4*inch))
        
        # Vendor and Client (stacked)
        story.append(Paragraph("<b>From:</b>", self.styles['SectionHeader']))
        story.append(Paragraph(
            f"{invoice.vendor_name}<br/>{invoice.vendor_address}<br/>{invoice.vendor_email}",
            self.styles['Normal']
        ))
        story.append(Spacer(1, 0.2*inch))
        
        story.append(Paragraph("<b>To:</b>", self.styles['SectionHeader']))
        story.append(Paragraph(
            f"{invoice.client_name}<br/>{invoice.client_address}<br/>{invoice.client_email}",
            self.styles['Normal']
        ))
        story.append(Spacer(1, 0.3*inch))
        
        # Line items (simplified)
        items_data = [['Item', 'Qty', 'Price', 'Total']]
        for item in invoice.items:
            items_data.append([
                item.description,
                str(item.quantity),
                f"{item.unit_price:.2f}",
                f"{item.total:.2f}"
            ])
        
        items_table = Table(items_data, colWidths=[3.5*inch, 0.7*inch, 1*inch, 1*inch])
        items_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
            ('ALIGN', (3, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#ecf0f1')]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdc3c7')),
        ]))
        story.append(items_table)
        story.append(Spacer(1, 0.2*inch))
        
        # Totals (right-aligned)
        totals_data = [
            ['Subtotal', f"{invoice.currency} {invoice.subtotal:.2f}"],
            ['Tax', f"{invoice.currency} {invoice.tax_total:.2f}"],
            ['<b>TOTAL</b>', f"<b>{invoice.currency} {invoice.grand_total:.2f}</b>"],
        ]
        totals_table = Table(totals_data, colWidths=[1*inch, 1.5*inch])
        totals_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONTSIZE', (0, 2), (1, 2), 12),
            ('TOPPADDING', (0, 2), (1, 2), 8),
            ('BOTTOMPADDING', (0, 2), (1, 2), 8),
        ]))
        story.append(totals_table)
        
        if invoice.notes:
            story.append(Spacer(1, 0.3*inch))
            story.append(Paragraph(f"<i>{invoice.notes}</i>", self.styles['Normal']))
        
        doc.build(story)
    
    def generate(self, invoice: InvoiceData, output_path: Path, layout: str = 'classic'):
        """Generate PDF with specified layout"""
        if layout == 'classic':
            self.generate_classic_layout(invoice, output_path)
        elif layout == 'modern':
            self.generate_modern_layout(invoice, output_path)
        else:
            raise ValueError(f"Unknown layout: {layout}")


# ============================================================================
# Ground Truth Annotation Generation
# ============================================================================

def create_ground_truth(invoice: InvoiceData, pdf_path: Path, layout: str) -> Dict[str, Any]:
    """Create ground truth JSON annotation for training"""
    
    # Convert invoice items to dict format
    items_dict = []
    for item in invoice.items:
        items_dict.append({
            'description': item.description,
            'quantity': item.quantity,
            'unit_price': item.unit_price,
            'tax_rate': item.tax_rate,
            'subtotal': item.subtotal,
            'tax_amount': item.tax_amount,
            'total': item.total
        })
    
    return {
        'invoice_id': invoice.invoice_id,
        'pdf_path': str(pdf_path),
        'layout_type': layout,
        'metadata': {
            'issue_date': invoice.issue_date,
            'due_date': invoice.due_date,
            'currency': invoice.currency,
            'vendor': {
                'name': invoice.vendor_name,
                'address': invoice.vendor_address,
                'email': invoice.vendor_email,
                'phone': invoice.vendor_phone
            },
            'client': {
                'name': invoice.client_name,
                'address': invoice.client_address,
                'email': invoice.client_email
            },
            'items': items_dict,
            'subtotal': invoice.subtotal,
            'tax_total': invoice.tax_total,
            'grand_total': invoice.grand_total,
            'notes': invoice.notes
        }
    }


# ============================================================================
# Main Generation Pipeline
# ============================================================================

def generate_synthetic_invoices(
    count: int,
    output_dir: Path,
    layouts: List[str] = ['classic', 'modern'],
    locale: str = 'en_US'
):
    """
    Main function to generate synthetic invoices
    
    Args:
        count: Number of invoices to generate
        output_dir: Output directory for PDFs and annotations
        layouts: List of layout types to use (rotates through them)
        locale: Faker locale for data generation
    """
    # Create output directories
    pdf_dir = output_dir / 'pdfs'
    annotations_dir = output_dir / 'annotations'
    pdf_dir.mkdir(parents=True, exist_ok=True)
    annotations_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize generators
    data_generator = InvoiceDataGenerator(locale=locale)
    pdf_generator = InvoicePDFGenerator()
    
    # Generate invoices
    training_manifest = []
    
    print(f"Generating {count} synthetic invoices...")
    for i in range(count):
        # Generate invoice data
        invoice = data_generator.generate_invoice()
        
        # Select layout (rotate through available layouts)
        layout = layouts[i % len(layouts)]
        
        # Generate PDF
        pdf_path = pdf_dir / f"{invoice.invoice_id}.pdf"
        pdf_generator.generate(invoice, pdf_path, layout=layout)
        
        # Create ground truth annotation
        ground_truth = create_ground_truth(invoice, pdf_path, layout)
        annotation_path = annotations_dir / f"{invoice.invoice_id}.json"
        with open(annotation_path, 'w') as f:
            json.dump(ground_truth, f, indent=2)
        
        # Add to training manifest
        training_manifest.append({
            'invoice_id': invoice.invoice_id,
            'pdf_path': str(pdf_path.relative_to(output_dir)),
            'annotation_path': str(annotation_path.relative_to(output_dir)),
            'layout': layout,
            'currency': invoice.currency,
            'total': invoice.grand_total
        })
        
        if (i + 1) % 10 == 0:
            print(f"  Generated {i + 1}/{count} invoices...")
    
    # Save training manifest
    manifest_path = output_dir / 'training_manifest.json'
    with open(manifest_path, 'w') as f:
        json.dump(training_manifest, f, indent=2)
    
    # Generate summary
    summary = {
        'total_invoices': count,
        'layouts_used': layouts,
        'currencies': list(set(item['currency'] for item in training_manifest)),
        'total_value': sum(item['total'] for item in training_manifest),
        'generation_date': datetime.now().isoformat()
    }
    summary_path = output_dir / 'dataset_summary.json'
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\n✓ Generation complete!")
    print(f"  - PDFs: {pdf_dir}")
    print(f"  - Annotations: {annotations_dir}")
    print(f"  - Manifest: {manifest_path}")
    print(f"  - Summary: {summary_path}")
    
    return training_manifest


# ============================================================================
# Command Line Interface
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Generate synthetic invoice training data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate 100 invoices with default settings
  python synthetic_invoice_generator_example.py --count 100
  
  # Generate 500 invoices with custom output directory
  python synthetic_invoice_generator_example.py --count 500 --output ./my_dataset
  
  # Generate invoices with only classic layout
  python synthetic_invoice_generator_example.py --count 50 --layouts classic
        """
    )
    
    parser.add_argument(
        '--count',
        type=int,
        default=100,
        help='Number of invoices to generate (default: 100)'
    )
    
    parser.add_argument(
        '--output',
        type=Path,
        default=Path('./synthetic_invoices'),
        help='Output directory (default: ./synthetic_invoices)'
    )
    
    parser.add_argument(
        '--layouts',
        nargs='+',
        choices=['classic', 'modern'],
        default=['classic', 'modern'],
        help='Layout types to use (default: classic modern)'
    )
    
    parser.add_argument(
        '--locale',
        type=str,
        default='en_US',
        help='Faker locale for data generation (default: en_US)'
    )
    
    args = parser.parse_args()
    
    # Generate invoices
    generate_synthetic_invoices(
        count=args.count,
        output_dir=args.output,
        layouts=args.layouts,
        locale=args.locale
    )


if __name__ == '__main__':
    main()

