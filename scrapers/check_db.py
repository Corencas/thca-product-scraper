#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))

# Ensure project root is on sys.path for shared imports
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from shared.settings import get_database_url

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Product, Vendor

engine = create_engine(get_database_url(), connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

products = db.query(Product).all()
vendors = db.query(Vendor).all()

print(f'Products in database: {len(products)}')
print(f'Vendors in database: {len(vendors)}')

if products:
    print(f'\nFirst 5 products:')
    for p in products[:5]:
        print(f'  - {p.title} (${p.current_price})')
else:
    print('\nNo products in database!')

db.close()
