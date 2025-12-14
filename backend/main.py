"""
FastAPI Backend for THCA Community Platform

Features:
- Product browsing with advanced filters
- Strain database with lineage
- Promo codes
- User accounts and favorites
- Reviews and ratings
- Price history and analytics
- Search functionality
"""
from fastapi import FastAPI, HTTPException, Depends, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, or_, and_, func, desc
from sqlalchemy.orm import sessionmaker, Session
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import os
import sys
from pathlib import Path

# Ensure project root is on sys.path for shared imports
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.settings import get_database_url

from models import (
    Base, Product, Vendor, Strain, PromoCode, User, ProductReview,
    VendorReview, PriceHistory, DropEvent, ProductType, Terpene, Effect
)

# Database setup
DATABASE_URL = get_database_url()
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="THCA Community Platform API",
    description="Comprehensive API for THCA product tracking and community features",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ========== Pydantic Schemas ==========

class ProductBase(BaseModel):
    title: str
    url: str
    vendor_id: int
    product_type: str
    current_price: Optional[float] = None
    weight_grams: Optional[float] = None

class ProductResponse(BaseModel):
    id: int
    external_id: str
    title: str
    url: str
    image_url: Optional[str]
    vendor_name: str
    strain_name: Optional[str]
    product_type: str
    current_price: Optional[float]
    original_price: Optional[float]
    weight_grams: Optional[float]
    price_per_gram: Optional[float]
    thca_percentage: Optional[float]
    total_cannabinoids: Optional[float]
    in_stock: bool
    is_new: bool
    is_deal: bool
    first_seen: datetime
    last_seen: datetime
    
    class Config:
        from_attributes = True

class StrainResponse(BaseModel):
    id: int
    name: str
    parent1: Optional[str]
    parent2: Optional[str]
    strain_type: Optional[str]
    description: Optional[str]
    flavor_profile: Optional[str]
    aroma_profile: Optional[str]
    avg_thca: Optional[float]
    effects: List[str] = []
    
    class Config:
        from_attributes = True

class VendorResponse(BaseModel):
    id: int
    name: str
    url: Optional[str]
    logo_url: Optional[str]
    description: Optional[str]
    avg_rating: float
    total_reviews: int
    ships_to: Optional[List[str]]
    
    class Config:
        from_attributes = True

class PromoCodeResponse(BaseModel):
    id: int
    code: str
    vendor_name: str
    discount_type: str
    discount_value: float
    description: Optional[str]
    min_purchase: Optional[float]
    valid_until: Optional[datetime]
    is_active: bool
    verified: bool
    
    class Config:
        from_attributes = True

class PriceHistoryResponse(BaseModel):
    price: float
    in_stock: bool
    recorded_at: datetime
    
    class Config:
        from_attributes = True


# ========== Product Endpoints ==========

@app.get("/api/products", response_model=List[ProductResponse])
def get_products(
    skip: int = 0,
    limit: int = Query(50, le=200),
    vendor_id: Optional[int] = None,
    product_type: Optional[str] = None,
    strain_id: Optional[int] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    in_stock_only: bool = False,
    is_new: Optional[bool] = None,
    is_deal: Optional[bool] = None,
    sort_by: str = "newest",  # newest, oldest, price_asc, price_desc, ppg_asc, ppg_desc
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get products with advanced filtering and sorting
    """
    query = db.query(Product).join(Vendor)
    
    # Filters
    if vendor_id:
        query = query.filter(Product.vendor_id == vendor_id)
    
    if product_type:
        try:
            ptype = ProductType[product_type.upper()]
            query = query.filter(Product.product_type == ptype)
        except KeyError:
            pass
    
    if strain_id:
        query = query.filter(Product.strain_id == strain_id)
    
    if min_price is not None:
        query = query.filter(Product.current_price >= min_price)
    
    if max_price is not None:
        query = query.filter(Product.current_price <= max_price)
    
    if in_stock_only:
        query = query.filter(Product.in_stock == True)
    
    if is_new is not None:
        query = query.filter(Product.is_new == is_new)
    
    if is_deal is not None:
        query = query.filter(Product.is_deal == is_deal)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Product.title.ilike(search_term),
                Strain.name.ilike(search_term)
            )
        )
    
    # Sorting
    if sort_by == "newest":
        query = query.order_by(desc(Product.first_seen))
    elif sort_by == "oldest":
        query = query.order_by(Product.first_seen)
    elif sort_by == "price_asc":
        query = query.filter(Product.current_price.isnot(None)).order_by(Product.current_price)
    elif sort_by == "price_desc":
        query = query.filter(Product.current_price.isnot(None)).order_by(desc(Product.current_price))
    elif sort_by == "ppg_asc":
        query = query.filter(Product.price_per_gram.isnot(None)).order_by(Product.price_per_gram)
    elif sort_by == "ppg_desc":
        query = query.filter(Product.price_per_gram.isnot(None)).order_by(desc(Product.price_per_gram))
    
    products = query.offset(skip).limit(limit).all()
    
    # Convert to response format
    result = []
    for p in products:
        result.append({
            "id": p.id,
            "external_id": p.external_id,
            "title": p.title,
            "url": p.url,
            "image_url": p.image_url,
            "vendor_name": p.vendor.name,
            "strain_name": p.strain.name if p.strain else None,
            "product_type": p.product_type.value if p.product_type else None,
            "current_price": p.current_price,
            "original_price": p.original_price,
            "weight_grams": p.weight_grams,
            "price_per_gram": p.price_per_gram,
            "thca_percentage": p.thca_percentage,
            "total_cannabinoids": p.total_cannabinoids,
            "in_stock": p.in_stock,
            "is_new": p.is_new,
            "is_deal": p.is_deal,
            "first_seen": p.first_seen,
            "last_seen": p.last_seen,
        })
    
    return result


@app.get("/api/products/{product_id}")
def get_product(product_id: int, db: Session = Depends(get_db)):
    """Get detailed product information"""
    product = db.query(Product).filter(Product.id == product_id).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Increment view count
    product.view_count += 1
    db.commit()
    
    return {
        "id": product.id,
        "external_id": product.external_id,
        "title": product.title,
        "url": product.url,
        "image_url": product.image_url,
        "vendor": {
            "id": product.vendor.id,
            "name": product.vendor.name,
            "logo_url": product.vendor.logo_url,
        },
        "strain": {
            "id": product.strain.id,
            "name": product.strain.name,
            "parent1": product.strain.parent1,
            "parent2": product.strain.parent2,
            "strain_type": product.strain.strain_type,
            "description": product.strain.description,
        } if product.strain else None,
        "product_type": product.product_type.value if product.product_type else None,
        "current_price": product.current_price,
        "original_price": product.original_price,
        "weight_grams": product.weight_grams,
        "price_per_gram": product.price_per_gram,
        "thca_percentage": product.thca_percentage,
        "thc_percentage": product.thc_percentage,
        "cbd_percentage": product.cbd_percentage,
        "total_cannabinoids": product.total_cannabinoids,
        "coa_url": product.coa_url,
        "in_stock": product.in_stock,
        "first_seen": product.first_seen,
        "last_seen": product.last_seen,
        "view_count": product.view_count,
    }


@app.get("/api/products/{product_id}/price-history")
def get_price_history(product_id: int, days: int = 30, db: Session = Depends(get_db)):
    """Get price history for a product"""
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    history = db.query(PriceHistory).filter(
        PriceHistory.product_id == product_id,
        PriceHistory.recorded_at >= cutoff_date
    ).order_by(PriceHistory.recorded_at).all()
    
    return [
        {
            "price": h.price,
            "in_stock": h.in_stock,
            "recorded_at": h.recorded_at
        }
        for h in history
    ]


# ========== Strain Endpoints ==========

@app.get("/api/strains")
def get_strains(
    skip: int = 0,
    limit: int = Query(100, le=500),
    search: Optional[str] = None,
    strain_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get strains with filtering"""
    query = db.query(Strain)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(Strain.name.ilike(search_term))
    
    if strain_type:
        query = query.filter(Strain.strain_type == strain_type)
    
    query = query.order_by(Strain.name)
    strains = query.offset(skip).limit(limit).all()
    
    return [
        {
            "id": s.id,
            "name": s.name,
            "parent1": s.parent1,
            "parent2": s.parent2,
            "strain_type": s.strain_type,
            "description": s.description,
            "flavor_profile": s.flavor_profile,
            "avg_thca": s.avg_thca,
            "effects": [e.name for e in s.effects],
        }
        for s in strains
    ]


@app.get("/api/strains/{strain_id}")
def get_strain(strain_id: int, db: Session = Depends(get_db)):
    """Get detailed strain information including lineage"""
    strain = db.query(Strain).filter(Strain.id == strain_id).first()
    
    if not strain:
        raise HTTPException(status_code=404, detail="Strain not found")
    
    # Get available products for this strain
    products = db.query(Product).filter(Product.strain_id == strain_id, Product.in_stock == True).all()
    
    return {
        "id": strain.id,
        "name": strain.name,
        "parent1": strain.parent1,
        "parent2": strain.parent2,
        "lineage_verified": strain.lineage_verified,
        "strain_type": strain.strain_type,
        "indica_percentage": strain.indica_percentage,
        "sativa_percentage": strain.sativa_percentage,
        "description": strain.description,
        "flavor_profile": strain.flavor_profile,
        "aroma_profile": strain.aroma_profile,
        "primary_terpenes": strain.primary_terpenes,
        "avg_thca": strain.avg_thca,
        "avg_total_cannabinoids": strain.avg_total_cannabinoids,
        "effects": [{"name": e.name, "category": e.category} for e in strain.effects],
        "available_products": len(products),
        "cheapest_price": min([p.current_price for p in products if p.current_price]) if products else None,
    }


@app.get("/api/strains/{strain_id}/lineage")
def get_strain_lineage(strain_id: int, db: Session = Depends(get_db)):
    """Get full lineage tree for a strain"""
    def get_parents(strain_name: str, depth: int = 0, max_depth: int = 5):
        if depth >= max_depth or not strain_name:
            return None
        
        strain = db.query(Strain).filter(Strain.name == strain_name).first()
        if not strain:
            return {"name": strain_name, "parents": []}
        
        lineage = {
            "name": strain.name,
            "strain_type": strain.strain_type,
            "parents": []
        }
        
        if strain.parent1:
            lineage["parents"].append(get_parents(strain.parent1, depth + 1, max_depth))
        if strain.parent2:
            lineage["parents"].append(get_parents(strain.parent2, depth + 1, max_depth))
        
        return lineage
    
    strain = db.query(Strain).filter(Strain.id == strain_id).first()
    if not strain:
        raise HTTPException(status_code=404, detail="Strain not found")
    
    return get_parents(strain.name)


# ========== Vendor Endpoints ==========

@app.get("/api/vendors")
def get_vendors(
    skip: int = 0,
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db)
):
    """Get all vendors"""
    vendors = db.query(Vendor).filter(Vendor.is_active == True).offset(skip).limit(limit).all()
    
    return [
        {
            "id": v.id,
            "name": v.name,
            "url": v.url,
            "logo_url": v.logo_url,
            "description": v.description,
            "avg_rating": v.avg_rating,
            "total_reviews": v.total_reviews,
            "ships_to": v.ships_to,
            "typical_drop_days": v.typical_drop_days,
        }
        for v in vendors
    ]


@app.get("/api/vendors/{vendor_id}")
def get_vendor(vendor_id: int, db: Session = Depends(get_db)):
    """Get detailed vendor information"""
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    # Get product stats
    product_count = db.query(Product).filter(Product.vendor_id == vendor_id).count()
    in_stock_count = db.query(Product).filter(
        Product.vendor_id == vendor_id,
        Product.in_stock == True
    ).count()
    
    # Get active promo codes
    active_promos = db.query(PromoCode).filter(
        PromoCode.vendor_id == vendor_id,
        PromoCode.is_active == True,
        or_(PromoCode.valid_until.is_(None), PromoCode.valid_until > datetime.utcnow())
    ).all()
    
    return {
        "id": vendor.id,
        "name": vendor.name,
        "url": vendor.url,
        "logo_url": vendor.logo_url,
        "description": vendor.description,
        "email": vendor.email,
        "discord": vendor.discord,
        "instagram": vendor.instagram,
        "ships_to": vendor.ships_to,
        "payment_methods": vendor.payment_methods,
        "min_order": vendor.min_order,
        "free_shipping_threshold": vendor.free_shipping_threshold,
        "avg_rating": vendor.avg_rating,
        "total_reviews": vendor.total_reviews,
        "typical_drop_days": vendor.typical_drop_days,
        "typical_drop_time": vendor.typical_drop_time,
        "product_count": product_count,
        "in_stock_count": in_stock_count,
        "active_promo_codes": [
            {
                "code": p.code,
                "description": p.description,
                "discount_type": p.discount_type,
                "discount_value": p.discount_value,
            }
            for p in active_promos
        ]
    }


# ========== Promo Code Endpoints ==========

@app.get("/api/promo-codes")
def get_promo_codes(
    vendor_id: Optional[int] = None,
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """Get promo codes"""
    query = db.query(PromoCode).join(Vendor)
    
    if active_only:
        query = query.filter(
            PromoCode.is_active == True,
            or_(PromoCode.valid_until.is_(None), PromoCode.valid_until > datetime.utcnow())
        )
    
    if vendor_id:
        query = query.filter(PromoCode.vendor_id == vendor_id)
    
    codes = query.order_by(desc(PromoCode.created_at)).all()
    
    return [
        {
            "id": c.id,
            "code": c.code,
            "vendor_name": c.vendor.name,
            "vendor_id": c.vendor_id,
            "discount_type": c.discount_type,
            "discount_value": c.discount_value,
            "description": c.description,
            "min_purchase": c.min_purchase,
            "valid_until": c.valid_until,
            "is_active": c.is_active,
            "verified": c.verified,
        }
        for c in codes
    ]


# ========== Analytics Endpoints ==========

@app.get("/api/analytics/popular-strains")
def get_popular_strains(limit: int = 10, db: Session = Depends(get_db)):
    """Get most popular strains by product count"""
    results = db.query(
        Strain.name,
        Strain.id,
        func.count(Product.id).label('product_count')
    ).join(Product).filter(
        Product.in_stock == True
    ).group_by(Strain.id).order_by(desc('product_count')).limit(limit).all()
    
    return [
        {
            "strain_name": r.name,
            "strain_id": r.id,
            "product_count": r.product_count
        }
        for r in results
    ]


@app.get("/api/analytics/price-trends")
def get_price_trends(
    product_type: Optional[str] = None,
    days: int = 30,
    db: Session = Depends(get_db)
):
    """Get average price trends over time"""
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    query = db.query(
        func.date(PriceHistory.recorded_at).label('date'),
        func.avg(PriceHistory.price).label('avg_price')
    ).join(Product)
    
    if product_type:
        try:
            ptype = ProductType[product_type.upper()]
            query = query.filter(Product.product_type == ptype)
        except KeyError:
            pass
    
    query = query.filter(
        PriceHistory.recorded_at >= cutoff_date
    ).group_by('date').order_by('date')
    
    results = query.all()
    
    return [
        {
            "date": str(r.date),
            "avg_price": round(float(r.avg_price), 2)
        }
        for r in results
    ]


@app.get("/api/analytics/deals")
def get_best_deals(
    limit: int = 20,
    product_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get best deals by price per gram"""
    query = db.query(Product).join(Vendor).filter(
        Product.in_stock == True,
        Product.price_per_gram.isnot(None),
        Product.current_price.isnot(None)
    )
    
    if product_type:
        try:
            ptype = ProductType[product_type.upper()]
            query = query.filter(Product.product_type == ptype)
        except KeyError:
            pass
    
    products = query.order_by(Product.price_per_gram).limit(limit).all()
    
    return [
        {
            "title": p.title,
            "url": p.url,
            "vendor_name": p.vendor.name,
            "strain_name": p.strain.name if p.strain else None,
            "current_price": p.current_price,
            "weight_grams": p.weight_grams,
            "price_per_gram": p.price_per_gram,
        }
        for p in products
    ]


# ========== Search Endpoint ==========

@app.get("/api/search")
def search_all(
    q: str,
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db)
):
    """Universal search across products, strains, and vendors"""
    search_term = f"%{q}%"
    
    # Search products
    products = db.query(Product).join(Vendor).filter(
        or_(
            Product.title.ilike(search_term),
            Vendor.name.ilike(search_term)
        )
    ).limit(limit).all()
    
    # Search strains
    strains = db.query(Strain).filter(
        Strain.name.ilike(search_term)
    ).limit(20).all()
    
    # Search vendors
    vendors = db.query(Vendor).filter(
        Vendor.name.ilike(search_term)
    ).limit(10).all()
    
    return {
        "products": [
            {
                "id": p.id,
                "title": p.title,
                "url": p.url,
                "vendor_name": p.vendor.name,
                "price": p.current_price,
            }
            for p in products
        ],
        "strains": [
            {
                "id": s.id,
                "name": s.name,
                "strain_type": s.strain_type,
            }
            for s in strains
        ],
        "vendors": [
            {
                "id": v.id,
                "name": v.name,
                "url": v.url,
            }
            for v in vendors
        ]
    }


# ========== Health Check ==========

@app.get("/health")
def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
