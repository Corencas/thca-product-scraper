#!/usr/bin/env python3
"""
Import products from seen_products.json into the database

Run this to sync your existing products to the database so the frontend can see them.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

# Ensure project root is on sys.path for shared imports
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from shared.settings import get_database_url

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Product, Vendor, Strain, ProductType
import re

DATABASE_URL = get_database_url()

# Setup database
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
Base.metadata.create_all(bind=engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

SEEN_FILE = Path("seen_products.json")


def extract_weight(title: str):
    """Extract weight in grams from title"""
    match = re.search(r'(\d+\.?\d*)\s*(g|gram|grams|oz|ounce)', title, re.IGNORECASE)
    if not match:
        return None
    
    amount = float(match.group(1))
    unit = match.group(2).lower()
    
    if unit.startswith('g'):
        return amount
    elif 'oz' in unit or 'ounce' in unit:
        return amount * 28.35
    
    return None


def classify_product_type(title: str):
    """Classify product type from title"""
    title_lower = title.lower()
    
    if any(word in title_lower for word in ['live resin', 'live-resin']):
        return ProductType.LIVE_RESIN
    elif any(word in title_lower for word in ['live rosin', 'live-rosin']):
        return ProductType.LIVE_ROSIN
    elif 'rosin' in title_lower:
        return ProductType.ROSIN
    elif 'shatter' in title_lower:
        return ProductType.SHATTER
    elif any(word in title_lower for word in ['flower', 'bud', 'smalls', 'exotic']):
        return ProductType.FLOWER
    
    return ProductType.FLOWER  # Default


def main():
    """Import products from JSON to database"""
    
    if not SEEN_FILE.exists():
        print(f"[ERROR] {SEEN_FILE} not found!")
        print("Make sure newthcaproductwatcher.py has run and created seen_products.json")
        return
    
    print(f"[INFO] Loading products from {SEEN_FILE}...")
    
    with SEEN_FILE.open('r') as f:
        seen = json.load(f)
    
    print(f"[INFO] Found {len(seen)} products in JSON file")
    
    db = SessionLocal()
    
    imported = 0
    skipped = 0
    
    for product_id, info in seen.items():
        title = info.get('title')
        url = info.get('url')
        site = info.get('site', 'Unknown')
        price = info.get('last_price') or info.get('price')
        first_seen = info.get('first_seen')
        last_seen = info.get('last_seen') or first_seen
        image_url = info.get('image_url', '')
        
        if not title or not url:
            skipped += 1
            continue
        
        # Check if already exists
        existing = db.query(Product).filter(Product.external_id == product_id).first()
        if existing:
            skipped += 1
            continue
        
        # Get or create vendor
        vendor = db.query(Vendor).filter(Vendor.name == site).first()
        if not vendor:
            # Extract base URL (e.g., https://example.com)
            from urllib.parse import urlparse
            parsed = urlparse(url)
            base_url = f"{parsed.scheme}://{parsed.netloc}"
            
            vendor = Vendor(name=site, url=base_url, is_active=True)
            db.add(vendor)
            db.commit()
            print(f"[INFO] Created vendor: {site}")
        
        # Extract weight and calculate price per gram
        weight_grams = extract_weight(title)
        price_per_gram = None
        if price and weight_grams and weight_grams > 0:
            price_per_gram = price / weight_grams
        
        # Classify product type
        product_type = classify_product_type(title)
        
        # Parse timestamps
        try:
            first_seen_dt = datetime.fromisoformat(first_seen.replace('Z', '')) if first_seen else datetime.utcnow()
            last_seen_dt = datetime.fromisoformat(last_seen.replace('Z', '')) if last_seen else first_seen_dt
        except:
            first_seen_dt = datetime.utcnow()
            last_seen_dt = first_seen_dt
        
        # Create product
        new_product = Product(
            external_id=product_id,
            title=title,
            url=url,
            image_url=image_url,
            vendor_id=vendor.id,
            product_type=product_type,
            current_price=price,
            weight_grams=weight_grams,
            price_per_gram=price_per_gram,
            in_stock=True,  # Assume in stock
            is_new=False,   # These are historical
            first_seen=first_seen_dt,
            last_seen=last_seen_dt
        )
        
        db.add(new_product)
        imported += 1
        
        if imported % 50 == 0:
            db.commit()
            print(f"[INFO] Imported {imported} products so far...")
    
    db.commit()
    db.close()
    
    print(f"\n[SUCCESS] Import complete!")
    print(f"  Imported: {imported} products")
    print(f"  Skipped: {skipped} products (already in database)")
    print(f"\nRefresh your frontend (http://localhost:5173) to see the products!")


if __name__ == "__main__":
    main()