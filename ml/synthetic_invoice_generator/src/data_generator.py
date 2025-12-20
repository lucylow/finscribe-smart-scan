"""
Core data generator for synthetic invoices
"""
import os
import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass, asdict
import yaml

from faker import Faker
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, LETTER, legal
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


@dataclass
class InvoiceItem:
    """Represents a single line item in an invoice"""
    description: str
    quantity: int
    unit_price: float
    tax_rate: float = 0.0
    discount: float = 0.0
    
    @property
    def subtotal(self) -> float:
        return self.quantity * self.unit_price
    
    @property
    def tax_amount(self) -> float:
        return self.subtotal * self.tax_rate / 100
    
    @property
    def total(self) -> float:
        return self.subtotal + self.tax_amount - self.discount


@dataclass
class CompanyInfo:
    """Company information for vendor and client"""
    name: str
    address: str
    city: str
    country: str
    postal_code: str
    phone: str
    email: str
    tax_id: str
    website: str = ""
    logo_path: str = ""


@dataclass
class InvoiceMetadata:
    """Complete invoice metadata for ground truth"""
    invoice_id: str
    issue_date: str
    due_date: str
    currency: str
    language: str
    layout_type: str
    invoice_type: str  # commercial, service, proforma, industry_specific
    challenge_category: str  # complex_table, key_value, visual_noise, multi_page, dense_data, multi_currency
    vendor: CompanyInfo
    client: CompanyInfo
    items: List[InvoiceItem]
    payment_terms: str
    notes: str
    subtotal: float
    tax_total: float
    discount_total: float
    grand_total: float
    # Additional fields for commercial invoices
    hs_codes: Optional[List[str]] = None
    incoterms: str = ""
    country_of_origin: str = ""
    customs_value: float = 0.0
    # Additional fields for industry-specific invoices
    industry: str = ""
    contract_number: str = ""
    project_code: str = ""
    
    def to_json(self) -> Dict:
        """Convert to JSON-serializable dictionary"""
        data = asdict(self)
        data['vendor'] = asdict(self.vendor)
        data['client'] = asdict(self.client)
        data['items'] = [asdict(item) for item in self.items]
        # Remove None values
        data = {k: v for k, v in data.items() if v is not None}
        return data


class SyntheticInvoiceGenerator:
    """Main class for generating synthetic invoices with variations"""
    
    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config" / "config.yaml"
        self.config = self._load_config(str(config_path))
        self.fakers = {}  # Language-specific Faker instances
        self._initialize_fakers()
        self._register_fonts()
        
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file"""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def _initialize_fakers(self):
        """Initialize Faker instances for different languages"""
        for lang in self.config['variations']['languages']:
            try:
                self.fakers[lang] = Faker(lang)
            except Exception as e:
                print(f"Warning: Could not initialize Faker for {lang}: {e}")
                # Fallback to default locale
                self.fakers[lang] = Faker('en_US')
    
    def _register_fonts(self):
        """Register custom fonts for multi-language support"""
        # Register standard fonts (these should be available on most systems)
        try:
            # Try to register Helvetica (standard)
            from reportlab.pdfbase.pdfmetrics import registerFontFamily
            registerFontFamily('Helvetica',
                             normal='Helvetica',
                             bold='Helvetica-Bold',
                             italic='Helvetica-Oblique',
                             boldItalic='Helvetica-BoldOblique')
        except Exception as e:
            print(f"Warning: Could not register fonts: {e}")
        
        # Register additional fonts for different languages if available
        font_dir = Path(__file__).parent.parent / "config" / "fonts"
        if font_dir.exists():
            for font_file in font_dir.glob("*.ttf"):
                try:
                    font_name = font_file.stem
                    pdfmetrics.registerFont(TTFont(font_name, str(font_file)))
                except Exception as e:
                    print(f"Warning: Could not register font {font_file}: {e}")
    
    def generate_company_info(self, language: str, is_vendor: bool = True) -> CompanyInfo:
        """Generate realistic company information"""
        faker = self.fakers.get(language, self.fakers.get('en_US', Faker()))
        
        if is_vendor:
            company_type = random.choice(['GmbH', 'LLC', 'Inc.', 'Ltd.', 'Corp.', 'AG', 'S.A.', 'S.L.', 'KK'])
        else:
            company_type = random.choice(['', 'GmbH', 'LLC', 'Ltd.'])
        
        name = f"{faker.company()} {company_type}".strip()
        
        return CompanyInfo(
            name=name,
            address=faker.street_address(),
            city=faker.city(),
            country=faker.country(),
            postal_code=faker.postcode(),
            phone=faker.phone_number(),
            email=faker.company_email(),
            tax_id=faker.bothify('??#########'),  # Simulated tax ID
            website=faker.url(),
            logo_path=self._get_random_logo() if is_vendor else ""
        )
    
    def generate_invoice_items(self, language: str, num_items: int) -> List[InvoiceItem]:
        """Generate realistic invoice line items"""
        faker = self.fakers.get(language, self.fakers.get('en_US', Faker()))
        items = []
        
        product_categories = [
            ('Software License', 100, 5000),
            ('Consulting Hours', 80, 300),
            ('Cloud Services', 50, 2000),
            ('Hardware', 200, 10000),
            ('Training', 150, 500),
            ('Maintenance', 100, 3000),
            ('Custom Development', 120, 8000)
        ]
        
        for _ in range(num_items):
            category, min_price, max_price = random.choice(product_categories)
            description = f"{category}: {faker.bs()}"
            quantity = random.randint(1, 20)
            unit_price = random.uniform(min_price, max_price)
            tax_rate = random.choice([0.0, 7.0, 19.0, 21.0])  # Common VAT rates
            discount = random.choice([0.0, 0.0, 0.0, 5.0, 10.0])  # Occasional discounts
            
            items.append(InvoiceItem(
                description=description,
                quantity=quantity,
                unit_price=round(unit_price, 2),
                tax_rate=tax_rate,
                discount=round(discount, 2)
            ))
        
        return items
    
    def generate_commercial_invoice_items(self, language: str, num_items: int) -> Tuple[List[InvoiceItem], List[str]]:
        """Generate items for commercial invoice with HS codes"""
        faker = self.fakers.get(language, self.fakers.get('en_US', Faker()))
        items = []
        hs_codes = []
        
        # HS codes are 6-10 digit codes for product classification
        hs_code_prefixes = [
            '8471',  # Automatic data processing machines
            '8517',  # Telephone sets, smartphones
            '8528',  # Monitors and projectors
            '8529',  # Parts for reception apparatus
            '8536',  # Electrical apparatus for switching
            '8708',  # Parts for motor vehicles
            '9027',  # Instruments for physical/chemical analysis
        ]
        
        product_categories = [
            ('Electronic Components', 50, 500),
            ('Machinery Parts', 200, 5000),
            ('Finished Goods', 100, 3000),
            ('Raw Materials', 30, 200),
            ('Packaging Materials', 10, 100),
        ]
        
        for _ in range(num_items):
            category, min_price, max_price = random.choice(product_categories)
            description = f"{category}: {faker.bs()}"
            quantity = random.randint(1, 100)
            unit_price = random.uniform(min_price, max_price)
            tax_rate = 0.0  # Commercial invoices often have 0% tax (duty calculated separately)
            discount = 0.0
            
            # Generate HS code (6-10 digits)
            prefix = random.choice(hs_code_prefixes)
            hs_code = prefix + ''.join([str(random.randint(0, 9)) for _ in range(6 - len(prefix))])
            hs_codes.append(hs_code)
            
            items.append(InvoiceItem(
                description=description,
                quantity=quantity,
                unit_price=round(unit_price, 2),
                tax_rate=tax_rate,
                discount=round(discount, 2)
            ))
        
        return items, hs_codes
    
    def generate_service_invoice_items(self, language: str, num_items: int) -> List[InvoiceItem]:
        """Generate items for service invoice with descriptive text"""
        faker = self.fakers.get(language, self.fakers.get('en_US', Faker()))
        items = []
        
        service_types = [
            ('Consulting Services', 80, 300),
            ('Software Development', 100, 250),
            ('Design Services', 75, 200),
            ('Training Services', 150, 500),
            ('Maintenance & Support', 50, 150),
            ('Cloud Services Subscription', 100, 500),
        ]
        
        for _ in range(num_items):
            service_type, min_rate, max_rate = random.choice(service_types)
            # For services, description is more detailed
            hours = random.randint(1, 40)
            hourly_rate = random.uniform(min_rate, max_rate)
            description = f"{service_type}: {faker.text(max_nb_chars=80)}"
            quantity = hours  # Hours for services
            unit_price = hourly_rate
            tax_rate = random.choice([0.0, 7.0, 19.0, 21.0])
            discount = random.choice([0.0, 0.0, 5.0, 10.0])
            
            items.append(InvoiceItem(
                description=description,
                quantity=quantity,
                unit_price=round(unit_price, 2),
                tax_rate=tax_rate,
                discount=round(discount, 2)
            ))
        
        return items
    
    def determine_challenge_category(
        self, 
        invoice_type: str, 
        num_items: int, 
        layout: str,
        currency: str,
        language: str
    ) -> str:
        """Determine challenge category based on invoice characteristics"""
        # Multi-page if many items
        if num_items > 25 or layout == 'multi_page':
            return 'multi_page'
        
        # Complex table for commercial invoices or dense layouts
        if invoice_type == 'commercial' or num_items > 15:
            return 'complex_table'
        
        # Visual noise for branded/industry-specific
        if invoice_type == 'industry_specific':
            return 'visual_noise'
        
        # Multi-currency if currency differs from standard
        if currency not in ['USD', 'EUR'] or language != 'en_US':
            if random.random() < 0.3:  # 30% chance
                return 'multi_currency'
        
        # Dense data for complex invoices
        if num_items > 10:
            return 'dense_data'
        
        # Default to key-value extraction
        return 'key_value'
    
    def _create_classic_layout(self, invoice_data: InvoiceMetadata, filename: str):
        """Create classic left-aligned invoice layout"""
        doc = SimpleDocTemplate(
            filename,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        story = []
        styles = getSampleStyleSheet()
        
        # Header with vendor info on left, invoice details on right
        header_data = [
            [invoice_data.vendor.name, f"Invoice #: {invoice_data.invoice_id}"],
            [invoice_data.vendor.address, f"Date: {invoice_data.issue_date}"],
            [f"{invoice_data.vendor.city}, {invoice_data.vendor.postal_code}", f"Due Date: {invoice_data.due_date}"],
            [invoice_data.vendor.country, f"Currency: {invoice_data.currency}"],
            [f"Tax ID: {invoice_data.vendor.tax_id}", ""]
        ]
        
        header_table = Table(header_data, colWidths=[3*inch, 3*inch])
        header_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ]))
        
        story.append(header_table)
        story.append(Spacer(1, 24))
        
        # Bill To section
        story.append(Paragraph("Bill To:", styles['Heading2']))
        story.append(Paragraph(invoice_data.client.name, styles['Normal']))
        story.append(Paragraph(invoice_data.client.address, styles['Normal']))
        story.append(Spacer(1, 24))
        
        # Line items table
        table_data = [['Description', 'Qty', 'Unit Price', 'Tax %', 'Discount', 'Total']]
        
        for item in invoice_data.items:
            table_data.append([
                item.description,
                str(item.quantity),
                f"{invoice_data.currency} {item.unit_price:.2f}",
                f"{item.tax_rate:.1f}%" if item.tax_rate > 0 else "0%",
                f"{invoice_data.currency} {item.discount:.2f}",
                f"{invoice_data.currency} {item.total:.2f}"
            ])
        
        items_table = Table(table_data, colWidths=[2.5*inch, 0.5*inch, inch, 0.6*inch, 0.8*inch, inch])
        items_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4F81BD')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#DCE6F1')),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
        ]))
        
        story.append(items_table)
        story.append(Spacer(1, 24))
        
        # Totals section
        totals_data = [
            ['Subtotal:', f"{invoice_data.currency} {invoice_data.subtotal:.2f}"],
            ['Tax Total:', f"{invoice_data.currency} {invoice_data.tax_total:.2f}"],
            ['Discount Total:', f"{invoice_data.currency} {invoice_data.discount_total:.2f}"],
            ['GRAND TOTAL:', f"{invoice_data.currency} {invoice_data.grand_total:.2f}"]
        ]
        
        totals_table = Table(totals_data, colWidths=[4*inch, 2*inch])
        totals_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 12),
            ('TOPPADDING', (-1, -1), (-1, -1), 12),
            ('LINEABOVE', (-1, -1), (-1, -1), 2, colors.black),
        ]))
        
        story.append(totals_table)
        
        # Notes and payment terms
        story.append(Spacer(1, 36))
        story.append(Paragraph("Payment Terms:", styles['Heading3']))
        story.append(Paragraph(invoice_data.payment_terms, styles['Normal']))
        story.append(Spacer(1, 12))
        story.append(Paragraph("Notes:", styles['Heading3']))
        story.append(Paragraph(invoice_data.notes, styles['Normal']))
        
        # Footer
        story.append(Spacer(1, 48))
        footer = Paragraph(
            f"Generated by Synthetic Invoice System • Page 1 of 1 • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            ParagraphStyle(name='Footer', fontName='Helvetica', fontSize=8, textColor=colors.gray)
        )
        story.append(footer)
        
        doc.build(story)
    
    def _create_modern_layout(self, invoice_data: InvoiceMetadata, filename: str):
        """Create modern centered layout with different styling"""
        doc = SimpleDocTemplate(
            filename,
            pagesize=A4,
            rightMargin=54,
            leftMargin=54,
            topMargin=54,
            bottomMargin=54
        )
        
        story = []
        styles = getSampleStyleSheet()
        
        # Centered title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#2C3E50'),
            alignment=1,  # Center alignment
            spaceAfter=30
        )
        story.append(Paragraph("INVOICE", title_style))
        story.append(Spacer(1, 20))
        
        # Two-column header
        header_data = [
            [f"<b>From:</b><br/>{invoice_data.vendor.name}<br/>{invoice_data.vendor.address}<br/>{invoice_data.vendor.city}, {invoice_data.vendor.postal_code}",
             f"<b>To:</b><br/>{invoice_data.client.name}<br/>{invoice_data.client.address}<br/>{invoice_data.client.city}, {invoice_data.client.postal_code}"]
        ]
        
        header_table = Table(header_data, colWidths=[3.5*inch, 3.5*inch])
        header_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
        ]))
        story.append(header_table)
        
        # Invoice details in a box
        story.append(Spacer(1, 20))
        details_data = [
            [f"<b>Invoice #:</b> {invoice_data.invoice_id}", f"<b>Date:</b> {invoice_data.issue_date}"],
            [f"<b>Due Date:</b> {invoice_data.due_date}", f"<b>Currency:</b> {invoice_data.currency}"]
        ]
        details_table = Table(details_data, colWidths=[3.5*inch, 3.5*inch])
        details_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#ECF0F1')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#BDC3C7')),
        ]))
        story.append(details_table)
        
        story.append(Spacer(1, 24))
        
        # Line items table (similar to classic)
        table_data = [['Description', 'Qty', 'Unit Price', 'Total']]
        for item in invoice_data.items:
            table_data.append([
                item.description,
                str(item.quantity),
                f"{invoice_data.currency} {item.unit_price:.2f}",
                f"{invoice_data.currency} {item.total:.2f}"
            ])
        
        items_table = Table(table_data, colWidths=[3*inch, 0.8*inch, 1.2*inch, 1*inch])
        items_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495E')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#95A5A6')),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
        ]))
        story.append(items_table)
        story.append(Spacer(1, 24))
        
        # Totals
        totals_data = [
            ['Subtotal:', f"{invoice_data.currency} {invoice_data.subtotal:.2f}"],
            ['Tax:', f"{invoice_data.currency} {invoice_data.tax_total:.2f}"],
            ['<b>TOTAL:</b>', f"<b>{invoice_data.currency} {invoice_data.grand_total:.2f}</b>"]
        ]
        totals_table = Table(totals_data, colWidths=[4.5*inch, 1.5*inch])
        totals_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTSIZE', (0, 0), (-1, -2), 10),
            ('FONTSIZE', (0, -1), (-1, -1), 14),
        ]))
        story.append(totals_table)
        
        doc.build(story)
    
    def _create_multi_page_invoice(self, invoice_data: InvoiceMetadata, filename: str):
        """Create multi-page invoice with continuation"""
        doc = SimpleDocTemplate(
            filename,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        story = []
        styles = getSampleStyleSheet()
        
        # Header (appears on every page)
        header_data = [
            [invoice_data.vendor.name, f"Invoice #: {invoice_data.invoice_id}"],
            [invoice_data.vendor.address, f"Date: {invoice_data.issue_date}"]
        ]
        header_table = Table(header_data, colWidths=[4*inch, 2*inch])
        header_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 24))
        
        # Bill To
        story.append(Paragraph("Bill To:", styles['Heading2']))
        story.append(Paragraph(invoice_data.client.name, styles['Normal']))
        story.append(Spacer(1, 24))
        
        # Line items table
        table_data = [['Description', 'Qty', 'Unit Price', 'Tax %', 'Total']]
        items_per_page = 20
        
        for idx, item in enumerate(invoice_data.items):
            table_data.append([
                item.description,
                str(item.quantity),
                f"{invoice_data.currency} {item.unit_price:.2f}",
                f"{item.tax_rate:.1f}%",
                f"{invoice_data.currency} {item.total:.2f}"
            ])
            
            # Add page break if needed
            if (idx + 1) % items_per_page == 0 and idx < len(invoice_data.items) - 1:
                items_table = Table(table_data, colWidths=[2.5*inch, 0.5*inch, inch, 0.6*inch, inch])
                items_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4F81BD')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ]))
                story.append(items_table)
                story.append(PageBreak())
                story.append(header_table)
                story.append(Spacer(1, 24))
                table_data = [['Description', 'Qty', 'Unit Price', 'Tax %', 'Total']]
        
        # Final table
        items_table = Table(table_data, colWidths=[2.5*inch, 0.5*inch, inch, 0.6*inch, inch])
        items_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4F81BD')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        story.append(items_table)
        story.append(Spacer(1, 24))
        
        # Totals on last page
        totals_data = [
            ['Subtotal:', f"{invoice_data.currency} {invoice_data.subtotal:.2f}"],
            ['Tax Total:', f"{invoice_data.currency} {invoice_data.tax_total:.2f}"],
            ['GRAND TOTAL:', f"{invoice_data.currency} {invoice_data.grand_total:.2f}"]
        ]
        totals_table = Table(totals_data, colWidths=[4*inch, 2*inch])
        totals_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 12),
        ]))
        story.append(totals_table)
        
        doc.build(story)
    
    def _get_random_logo(self) -> str:
        """Get path to a random logo image or generate one"""
        logo_dir = Path(__file__).parent.parent / "config" / "logos"
        if logo_dir.exists() and any(logo_dir.iterdir()):
            logos = list(logo_dir.glob("*.png"))
            if logos:
                return str(random.choice(logos))
        return ""
    
    def calculate_totals(self, items: List[InvoiceItem]) -> Tuple[float, float, float, float]:
        """Calculate invoice totals"""
        subtotal = sum(item.subtotal for item in items)
        tax_total = sum(item.tax_amount for item in items)
        discount_total = sum(item.discount for item in items)
        grand_total = subtotal + tax_total - discount_total
        
        return subtotal, tax_total, discount_total, grand_total
    
    def generate_single_invoice(self, invoice_id: int) -> Tuple[str, Dict]:
        """Generate a single invoice with random variations"""
        # Randomly select variations
        language = random.choice(self.config['variations']['languages'])
        layout = random.choice(self.config['variations']['layouts'])
        currency = random.choice(self.config['variations']['currencies'])
        complexity_key = random.choice(list(self.config['variations']['complexity_levels'].keys()))
        complexity = self.config['variations']['complexity_levels'][complexity_key]
        
        # Select invoice type based on configured distribution or default
        invoice_types_config = self.config.get('variations', {}).get('invoice_types', {})
        if invoice_types_config:
            # Weighted selection based on distribution
            invoice_types = list(invoice_types_config.keys())
            weights = [invoice_types_config[t].get('weight', 1.0) for t in invoice_types]
            invoice_type = random.choices(invoice_types, weights=weights)[0]
        else:
            # Default distribution: 30% commercial, 25% service, 15% proforma, 30% industry_specific
            invoice_type = random.choices(
                ['commercial', 'service', 'proforma', 'industry_specific'],
                weights=[0.30, 0.25, 0.15, 0.30]
            )[0]
        
        faker = self.fakers.get(language, self.fakers.get('en_US', Faker()))
        
        # Generate company information
        vendor = self.generate_company_info(language, is_vendor=True)
        client = self.generate_company_info(language, is_vendor=False)
        
        # Generate invoice items based on invoice type and complexity
        num_items = random.randint(complexity['min_items'], complexity['max_items'])
        hs_codes = None
        industry = ""
        contract_number = ""
        project_code = ""
        incoterms = ""
        country_of_origin = ""
        
        if invoice_type == 'commercial':
            items, hs_codes = self.generate_commercial_invoice_items(language, num_items)
            # Commercial invoice specific fields
            incoterms = random.choice(['FOB', 'CIF', 'EXW', 'DDP', 'CFR', 'CPT'])
            country_of_origin = vendor.country
        elif invoice_type == 'service':
            items = self.generate_service_invoice_items(language, num_items)
            contract_number = faker.bothify('CON-####-??')
        elif invoice_type == 'industry_specific':
            items = self.generate_invoice_items(language, num_items)
            industries = ['construction', 'healthcare', 'retail', 'freelancing', 'manufacturing']
            industry = random.choice(industries)
            project_code = faker.bothify('PRJ-####')
        else:  # proforma
            items = self.generate_invoice_items(language, num_items)
        
        # Calculate totals
        subtotal, tax_total, discount_total, grand_total = self.calculate_totals(items)
        
        # Determine challenge category
        challenge_category = self.determine_challenge_category(
            invoice_type, num_items, layout, currency, language
        )
        
        # Create invoice metadata
        issue_date_obj = faker.date_this_year()
        invoice_id_str = f"INV-{datetime.now().year}-{invoice_id:06d}"
        
        # For proforma, prefix with PROFORMA
        if invoice_type == 'proforma':
            invoice_id_str = f"PROFORMA-{invoice_id_str}"
        
        invoice_data = InvoiceMetadata(
            invoice_id=invoice_id_str,
            issue_date=issue_date_obj.strftime('%Y-%m-%d'),
            due_date=(issue_date_obj + timedelta(days=30)).strftime('%Y-%m-%d'),
            currency=currency,
            language=language,
            layout_type=layout,
            invoice_type=invoice_type,
            challenge_category=challenge_category,
            vendor=vendor,
            client=client,
            items=items,
            payment_terms=random.choice([
                "Net 30 days",
                "Due upon receipt",
                "50% advance, 50% on delivery",
                "Net 15 days with 2% discount for early payment"
            ]),
            notes=faker.text(max_nb_chars=200),
            subtotal=round(subtotal, 2),
            tax_total=round(tax_total, 2),
            discount_total=round(discount_total, 2),
            grand_total=round(grand_total, 2),
            hs_codes=hs_codes,
            incoterms=incoterms,
            country_of_origin=country_of_origin,
            customs_value=round(subtotal, 2) if invoice_type == 'commercial' else 0.0,
            industry=industry,
            contract_number=contract_number,
            project_code=project_code
        )
        
        # Generate PDF based on layout type
        # Resolve output_dir relative to config file location or current directory
        output_dir_str = self.config['generation']['output_dir']
        if not os.path.isabs(output_dir_str):
            # Relative to the synthetic_invoice_generator directory
            base_dir = Path(__file__).parent.parent
            output_dir = base_dir / output_dir_str
        else:
            output_dir = Path(output_dir_str)
        
        pdf_path = output_dir / 'pdfs' / f"{invoice_data.invoice_id}.pdf"
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        
        if layout == 'classic_left':
            self._create_classic_layout(invoice_data, str(pdf_path))
        elif layout == 'modern_centered':
            self._create_modern_layout(invoice_data, str(pdf_path))
        elif layout == 'multi_page':
            self._create_multi_page_invoice(invoice_data, str(pdf_path))
        else:
            # Default to classic layout
            self._create_classic_layout(invoice_data, str(pdf_path))
        
        # Save ground truth
        gt_path = output_dir / 'ground_truth' / f"{invoice_data.invoice_id}.json"
        gt_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(gt_path, 'w', encoding='utf-8') as f:
            json.dump(invoice_data.to_json(), f, indent=2, ensure_ascii=False)
        
        return str(pdf_path), invoice_data.to_json()
    
    def generate_batch(self, start_id: int = 1, batch_size: int = None):
        """Generate a batch of invoices"""
        if batch_size is None:
            batch_size = self.config['generation']['batch_size']
        
        metadata_list = []
        
        for i in range(start_id, start_id + batch_size):
            try:
                pdf_path, metadata = self.generate_single_invoice(i)
                metadata_list.append({
                    'id': i,
                    'pdf_path': pdf_path,
                    'metadata': metadata
                })
                
                if i % 100 == 0:
                    print(f"Generated {i} invoices...")
                    
            except Exception as e:
                print(f"Error generating invoice {i}: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        # Save batch metadata
        output_dir_str = self.config['generation']['output_dir']
        if not os.path.isabs(output_dir_str):
            base_dir = Path(__file__).parent.parent
            output_dir = base_dir / output_dir_str
        else:
            output_dir = Path(output_dir_str)
        
        batch_file = output_dir / 'metadata' / f'batch_{start_id}_{start_id+batch_size-1}.json'
        batch_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(batch_file, 'w', encoding='utf-8') as f:
            json.dump(metadata_list, f, indent=2, ensure_ascii=False)
        
        print(f"Generated {len(metadata_list)} invoices in batch {start_id}-{start_id+batch_size-1}")
        
        return metadata_list
    
    def generate_full_dataset(self):
        """Generate the complete dataset"""
        total_invoices = self.config['generation']['num_invoices']
        batch_size = self.config['generation']['batch_size']
        
        all_metadata = []
        
        for batch_start in range(1, total_invoices + 1, batch_size):
            current_batch_size = min(batch_size, total_invoices - batch_start + 1)
            batch_metadata = self.generate_batch(batch_start, current_batch_size)
            all_metadata.extend(batch_metadata)
        
        # Create dataset summary
        summary = {
            'total_invoices': len(all_metadata),
            'generation_date': datetime.now().isoformat(),
            'languages_used': list(set(m['metadata']['language'] for m in all_metadata)),
            'currencies_used': list(set(m['metadata']['currency'] for m in all_metadata)),
            'layouts_used': list(set(m['metadata']['layout_type'] for m in all_metadata)),
            'invoice_types': list(set(m['metadata'].get('invoice_type', 'standard') for m in all_metadata)),
            'challenge_categories': list(set(m['metadata'].get('challenge_category', 'key_value') for m in all_metadata)),
            'invoice_type_distribution': {
                inv_type: sum(1 for m in all_metadata if m['metadata'].get('invoice_type') == inv_type)
                for inv_type in ['commercial', 'service', 'proforma', 'industry_specific']
            },
            'challenge_category_distribution': {
                cat: sum(1 for m in all_metadata if m['metadata'].get('challenge_category') == cat)
                for cat in ['complex_table', 'key_value', 'visual_noise', 'multi_page', 'dense_data', 'multi_currency']
            }
        }
        
        output_dir_str = self.config['generation']['output_dir']
        if not os.path.isabs(output_dir_str):
            base_dir = Path(__file__).parent.parent
            output_dir = base_dir / output_dir_str
        else:
            output_dir = Path(output_dir_str)
        
        summary_file = output_dir / 'dataset_summary.json'
        summary_file.parent.mkdir(parents=True, exist_ok=True)
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        print(f"\nDataset generation complete!")
        print(f"Total invoices: {summary['total_invoices']}")
        print(f"Languages: {summary['languages_used']}")
        print(f"Currencies: {summary['currencies_used']}")
        print(f"Layouts: {summary['layouts_used']}")
        print(f"Invoice types: {summary['invoice_types']}")
        print(f"Challenge categories: {summary['challenge_categories']}")
        print(f"\nInvoice Type Distribution:")
        for inv_type, count in summary['invoice_type_distribution'].items():
            percentage = (count / summary['total_invoices']) * 100 if summary['total_invoices'] > 0 else 0
            print(f"  {inv_type}: {count} ({percentage:.1f}%)")
        print(f"\nChallenge Category Distribution:")
        for cat, count in summary['challenge_category_distribution'].items():
            percentage = (count / summary['total_invoices']) * 100 if summary['total_invoices'] > 0 else 0
            print(f"  {cat}: {count} ({percentage:.1f}%)")
        
        return all_metadata

