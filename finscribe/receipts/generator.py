"""
Synthetic Receipt Generator for training PaddleOCR-VL on receipt data.
Generates diverse, realistic receipt images with ground truth metadata.
"""

import json
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass, asdict
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from faker import Faker
import yaml

@dataclass
class ReceiptItem:
    """Represents a single item on a receipt"""
    description: str
    quantity: int
    unit_price: float
    discount: float = 0.0
    
    @property
    def total(self) -> float:
        return self.quantity * self.unit_price - self.discount

@dataclass
class ReceiptMetadata:
    """Complete receipt metadata for ground truth"""
    receipt_id: str
    merchant_name: str
    merchant_address: str
    merchant_phone: str
    transaction_date: str
    transaction_time: str
    cashier_id: str
    register_id: str
    items: List[ReceiptItem]
    subtotal: float
    tax_rate: float
    tax_amount: float
    discount_total: float
    total_paid: float
    payment_method: str
    change_given: float
    currency: str
    receipt_type: str  # 'grocery', 'restaurant', 'retail', 'gas', 'pharmacy'
    
    def to_json(self) -> Dict:
        """Convert to JSON-serializable dictionary"""
        data = asdict(self)
        data['items'] = [asdict(item) for item in self.items]
        return data

class SyntheticReceiptGenerator:
    """Generate synthetic receipts for training"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config = self._load_config(config_path) if config_path else self._default_config()
        self.faker = Faker()
        self.receipt_types = ['grocery', 'restaurant', 'retail', 'gas', 'pharmacy']
        
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            return self._default_config()
    
    def _default_config(self) -> Dict:
        """Default configuration"""
        return {
            'generation': {
                'num_receipts': 1000,
                'output_dir': './receipt_dataset',
                'receipt_types': self.receipt_types
            },
            'augmentation': {
                'apply_thermal_effect': True,
                'add_noise': True,
                'noise_level': [5, 15],
                'random_rotation': [-5, 5]
            }
        }
    
    def generate_grocery_items(self, num_items: int) -> List[ReceiptItem]:
        """Generate grocery items"""
        grocery_items = [
            ("Organic Apples", 2.99),
            ("Bananas", 0.69),
            ("Milk 2%", 3.49),
            ("Bread", 2.99),
            ("Eggs (Dozen)", 3.79),
            ("Chicken Breast", 8.99),
            ("Ground Beef", 5.99),
            ("Cereal", 4.49),
            ("Coffee", 7.99),
            ("Toilet Paper", 12.99)
        ]
        
        items = []
        for _ in range(num_items):
            description, base_price = random.choice(grocery_items)
            quantity = random.randint(1, 5)
            unit_price = round(base_price * random.uniform(0.9, 1.1), 2)
            discount = round(unit_price * quantity * random.choice([0, 0, 0, 0.1, 0.2]), 2)
            
            items.append(ReceiptItem(
                description=description,
                quantity=quantity,
                unit_price=unit_price,
                discount=discount
            ))
        
        return items
    
    def generate_restaurant_items(self, num_items: int) -> List[ReceiptItem]:
        """Generate restaurant items"""
        menu_items = [
            ("Burger & Fries", 12.99),
            ("Pizza", 14.99),
            ("Salad", 9.99),
            ("Pasta", 13.99),
            ("Steak", 24.99),
            ("Fish & Chips", 16.99),
            ("Soft Drink", 2.49),
            ("Coffee", 3.49),
            ("Dessert", 6.99),
            ("Wine Glass", 8.99)
        ]
        
        items = []
        for _ in range(num_items):
            description, base_price = random.choice(menu_items)
            quantity = random.randint(1, 3)
            unit_price = round(base_price, 2)
            
            items.append(ReceiptItem(
                description=description,
                quantity=quantity,
                unit_price=unit_price,
                discount=0.0
            ))
        
        return items
    
    def generate_receipt(self, receipt_type: Optional[str] = None) -> ReceiptMetadata:
        """Generate a complete receipt"""
        if receipt_type is None:
            receipt_type = random.choice(self.receipt_types)
        
        # Generate items based on receipt type
        num_items = random.randint(3, 15)
        if receipt_type == 'grocery':
            items = self.generate_grocery_items(num_items)
            merchant_names = ["Walmart", "Target", "Kroger", "Whole Foods", "Trader Joe's"]
        elif receipt_type == 'restaurant':
            items = self.generate_restaurant_items(num_items)
            merchant_names = ["McDonald's", "Starbucks", "Burger King", "Local Diner", "Pizza Hut"]
        elif receipt_type == 'pharmacy':
            items = self.generate_grocery_items(num_items)  # Reuse for now
            merchant_names = ["CVS Pharmacy", "Walgreens", "Rite Aid"]
        elif receipt_type == 'gas':
            items = [ReceiptItem("Gasoline", 1, round(random.uniform(20, 60), 2))]
            merchant_names = ["Shell", "BP", "Exxon", "Chevron"]
        else:
            items = self.generate_grocery_items(num_items)
            merchant_names = ["Best Buy", "Home Depot", "7-Eleven"]
        
        # Calculate totals
        subtotal = sum(item.total for item in items)
        tax_rate = random.choice([0.07, 0.08, 0.085, 0.09])
        tax_amount = round(subtotal * tax_rate, 2)
        discount_total = sum(item.discount for item in items)
        total_paid = round(subtotal + tax_amount, 2)
        
        # Payment methods
        payment_methods = ["CASH", "VISA", "MASTERCARD", "AMEX", "DEBIT"]
        
        return ReceiptMetadata(
            receipt_id=f"REC-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}",
            merchant_name=random.choice(merchant_names),
            merchant_address=self.faker.street_address(),
            merchant_phone=self.faker.phone_number(),
            transaction_date=self.faker.date_this_year().strftime('%m/%d/%Y'),
            transaction_time=self.faker.time(pattern='%I:%M %p'),
            cashier_id=f"C{random.randint(1, 99)}",
            register_id=f"R{random.randint(1, 99)}",
            items=items,
            subtotal=subtotal,
            tax_rate=tax_rate,
            tax_amount=tax_amount,
            discount_total=discount_total,
            total_paid=total_paid,
            payment_method=random.choice(payment_methods),
            change_given=round(random.uniform(0, 20), 2),
            currency="$",
            receipt_type=receipt_type
        )
    
    def create_receipt_image(self, metadata: ReceiptMetadata, output_path: str) -> str:
        """Create a receipt image from metadata"""
        # Receipt dimensions (thermal paper style)
        width = 384  # Standard thermal receipt width
        height = 600 + len(metadata.items) * 30
        
        # Create blank image
        image = Image.new('RGB', (width, height), 'white')
        draw = ImageDraw.Draw(image)
        
        # Load font (simulate thermal printer font)
        try:
            font = ImageFont.truetype("Courier.ttf", 12)
            font_bold = ImageFont.truetype("Courier-Bold.ttf", 14)
        except:
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Courier.ttf", 12)
                font_bold = ImageFont.truetype("/System/Library/Fonts/Courier-Bold.ttf", 14)
            except:
                font = ImageFont.load_default()
                font_bold = ImageFont.load_default()
        
        y_position = 20
        
        # Draw receipt header
        draw.text((width//2, y_position), metadata.merchant_name, fill='black', font=font_bold, anchor='mm')
        y_position += 25
        draw.text((width//2, y_position), metadata.merchant_address, fill='black', font=font, anchor='mm')
        y_position += 20
        draw.text((width//2, y_position), f"Phone: {metadata.merchant_phone}", fill='black', font=font, anchor='mm')
        y_position += 30
        
        # Draw separator line
        draw.line([(10, y_position), (width-10, y_position)], fill='black', width=1)
        y_position += 20
        
        # Draw transaction info
        draw.text((10, y_position), f"DATE: {metadata.transaction_date}", fill='black', font=font)
        draw.text((width-10, y_position), f"TIME: {metadata.transaction_time}", fill='black', font=font, anchor='rm')
        y_position += 20
        draw.text((10, y_position), f"CASHIER: {metadata.cashier_id}", fill='black', font=font)
        draw.text((width-10, y_position), f"REGISTER: {metadata.register_id}", fill='black', font=font, anchor='rm')
        y_position += 30
        
        # Draw items header
        draw.line([(10, y_position), (width-10, y_position)], fill='black', width=1)
        y_position += 10
        draw.text((10, y_position), "ITEM", fill='black', font=font_bold)
        draw.text((width-120, y_position), "QTY", fill='black', font=font_bold, anchor='rm')
        draw.text((width-60, y_position), "PRICE", fill='black', font=font_bold, anchor='rm')
        draw.text((width-10, y_position), "TOTAL", fill='black', font=font_bold, anchor='rm')
        y_position += 20
        draw.line([(10, y_position), (width-10, y_position)], fill='black', width=1)
        y_position += 10
        
        # Draw items
        for item in metadata.items:
            # Wrap description if too long
            desc = item.description
            if len(desc) > 20:
                desc = desc[:17] + "..."
            
            draw.text((10, y_position), desc, fill='black', font=font)
            draw.text((width-120, y_position), str(item.quantity), fill='black', font=font, anchor='rm')
            draw.text((width-60, y_position), f"{metadata.currency}{item.unit_price:.2f}", fill='black', font=font, anchor='rm')
            draw.text((width-10, y_position), f"{metadata.currency}{item.total:.2f}", fill='black', font=font, anchor='rm')
            y_position += 25
        
        # Draw separator
        draw.line([(10, y_position), (width-10, y_position)], fill='black', width=1)
        y_position += 20
        
        # Draw totals
        draw.text((width-100, y_position), "SUBTOTAL:", fill='black', font=font)
        draw.text((width-10, y_position), f"{metadata.currency}{metadata.subtotal:.2f}", fill='black', font=font, anchor='rm')
        y_position += 20
        
        draw.text((width-100, y_position), f"TAX ({metadata.tax_rate*100:.1f}%):", fill='black', font=font)
        draw.text((width-10, y_position), f"{metadata.currency}{metadata.tax_amount:.2f}", fill='black', font=font, anchor='rm')
        y_position += 20
        
        if metadata.discount_total > 0:
            draw.text((width-100, y_position), "DISCOUNT:", fill='black', font=font)
            draw.text((width-10, y_position), f"-{metadata.currency}{metadata.discount_total:.2f}", fill='black', font=font, anchor='rm')
            y_position += 20
        
        draw.line([(width-100, y_position), (width-10, y_position)], fill='black', width=2)
        y_position += 10
        
        draw.text((width-100, y_position), "TOTAL:", fill='black', font=font_bold)
        draw.text((width-10, y_position), f"{metadata.currency}{metadata.total_paid:.2f}", fill='black', font=font_bold, anchor='rm')
        y_position += 30
        
        # Draw payment info
        draw.text((10, y_position), f"PAYMENT: {metadata.payment_method}", fill='black', font=font_bold)
        y_position += 20
        draw.text((10, y_position), f"CHANGE: {metadata.currency}{metadata.change_given:.2f}", fill='black', font=font)
        y_position += 30
        
        # Draw footer
        draw.text((width//2, y_position), "THANK YOU FOR YOUR BUSINESS!", fill='black', font=font, anchor='mm')
        y_position += 20
        draw.text((width//2, y_position), "PLEASE COME AGAIN", fill='black', font=font, anchor='mm')
        
        # Apply thermal printer effects (dithering)
        if self.config.get('augmentation', {}).get('apply_thermal_effect', True):
            image = self._apply_thermal_effect(image)
        
        # Save image
        image.save(output_path)
        return output_path
    
    def _apply_thermal_effect(self, image: Image.Image) -> Image.Image:
        """Apply thermal printer effects to image"""
        # Convert to grayscale
        gray = image.convert('L')
        
        # Add noise (simulate thermal print artifacts)
        np_image = np.array(gray)
        noise_level = self.config.get('augmentation', {}).get('noise_level', [5, 15])
        noise = np.random.normal(0, random.uniform(noise_level[0], noise_level[1]), np_image.shape)
        noisy_image = np.clip(np_image + noise, 0, 255).astype(np.uint8)
        
        # Apply dithering (Floyd-Steinberg)
        height, width = noisy_image.shape
        for y in range(height-1):
            for x in range(1, width-1):
                old_pixel = noisy_image[y, x]
                new_pixel = 255 if old_pixel > 128 else 0
                noisy_image[y, x] = new_pixel
                quant_error = old_pixel - new_pixel
                
                # Distribute error
                noisy_image[y, x+1] = np.clip(noisy_image[y, x+1] + quant_error * 7/16, 0, 255)
                noisy_image[y+1, x-1] = np.clip(noisy_image[y+1, x-1] + quant_error * 3/16, 0, 255)
                noisy_image[y+1, x] = np.clip(noisy_image[y+1, x] + quant_error * 5/16, 0, 255)
                noisy_image[y+1, x+1] = np.clip(noisy_image[y+1, x+1] + quant_error * 1/16, 0, 255)
        
        # Convert back to RGB
        result = Image.fromarray(noisy_image).convert('RGB')
        return result
    
    def generate_dataset(self, num_receipts: int, output_dir: str) -> List[Dict]:
        """Generate a dataset of synthetic receipts"""
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        images_dir = Path(output_dir) / "images"
        labels_dir = Path(output_dir) / "labels"
        images_dir.mkdir(exist_ok=True)
        labels_dir.mkdir(exist_ok=True)
        
        dataset = []
        
        for i in range(num_receipts):
            try:
                # Generate receipt
                receipt_type = random.choice(self.receipt_types)
                metadata = self.generate_receipt(receipt_type)
                
                # Create image
                image_path = images_dir / f"receipt_{i:04d}.png"
                self.create_receipt_image(metadata, str(image_path))
                
                # Create label in PaddleOCR-VL format
                label = self._create_paddleocr_label(metadata, str(image_path))
                label_path = labels_dir / f"receipt_{i:04d}.json"
                
                with open(label_path, 'w', encoding='utf-8') as f:
                    json.dump(label, f, indent=2, ensure_ascii=False)
                
                dataset.append({
                    'image_path': str(image_path),
                    'label_path': str(label_path),
                    'metadata': metadata.to_json(),
                    'receipt_type': receipt_type
                })
                
                if (i + 1) % 100 == 0:
                    print(f"Generated {i + 1}/{num_receipts} receipts...")
                    
            except Exception as e:
                print(f"Error generating receipt {i}: {e}")
                continue
        
        # Save dataset manifest
        manifest_path = Path(output_dir) / "dataset_manifest.json"
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(dataset, f, indent=2, ensure_ascii=False)
        
        print(f"\nDataset generation complete!")
        print(f"Total receipts: {len(dataset)}")
        print(f"Output directory: {output_dir}")
        
        return dataset
    
    def _create_paddleocr_label(self, metadata: ReceiptMetadata, image_path: str) -> Dict:
        """Create label in PaddleOCR-VL instruction format"""
        
        # Instruction-response pairs for training
        instruction_pairs = [
            {
                "instruction": "<image>\nExtract the merchant information from this receipt.",
                "response": json.dumps({
                    "merchant_name": metadata.merchant_name,
                    "merchant_address": metadata.merchant_address,
                    "merchant_phone": metadata.merchant_phone
                }, ensure_ascii=False)
            },
            {
                "instruction": "<image>\nWhat is the transaction date, time, and receipt number?",
                "response": json.dumps({
                    "receipt_id": metadata.receipt_id,
                    "transaction_date": metadata.transaction_date,
                    "transaction_time": metadata.transaction_time
                }, ensure_ascii=False)
            },
            {
                "instruction": "<image>\nExtract all line items from the receipt.",
                "response": json.dumps([
                    {
                        "description": item.description,
                        "quantity": item.quantity,
                        "unit_price": item.unit_price,
                        "total": item.total
                    }
                    for item in metadata.items
                ], ensure_ascii=False)
            },
            {
                "instruction": "<image>\nExtract the financial summary including subtotal, tax, and total.",
                "response": json.dumps({
                    "subtotal": metadata.subtotal,
                    "tax_rate": metadata.tax_rate,
                    "tax_amount": metadata.tax_amount,
                    "discount_total": metadata.discount_total,
                    "total_paid": metadata.total_paid
                }, ensure_ascii=False)
            },
            {
                "instruction": "<image>\nWhat was the payment method and change given?",
                "response": json.dumps({
                    "payment_method": metadata.payment_method,
                    "change_given": metadata.change_given,
                    "currency": metadata.currency
                }, ensure_ascii=False)
            }
        ]
        
        return {
            "image_path": image_path,
            "receipt_type": metadata.receipt_type,
            "metadata": metadata.to_json(),
            "instruction_pairs": instruction_pairs
        }


