"""
Database models for THCA Community Platform
SQLAlchemy ORM models with relationships
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, Table, JSON, Enum as SQLEnum
from sqlalchemy.orm import declarative_base, relationship
import enum

Base = declarative_base()

# Many-to-many relationship tables
product_terpenes = Table(
    'product_terpenes',
    Base.metadata,
    Column('product_id', Integer, ForeignKey('products.id')),
    Column('terpene_id', Integer, ForeignKey('terpenes.id'))
)

strain_effects = Table(
    'strain_effects',
    Base.metadata,
    Column('strain_id', Integer, ForeignKey('strains.id')),
    Column('effect_id', Integer, ForeignKey('effects.id'))
)

user_favorites = Table(
    'user_favorites',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('product_id', Integer, ForeignKey('products.id'))
)


class ProductType(enum.Enum):
    FLOWER = "flower"
    LIVE_RESIN = "live_resin"
    LIVE_ROSIN = "live_rosin"
    ROSIN = "rosin"
    SHATTER = "shatter"
    WAX = "wax"
    CRUMBLE = "crumble"
    BUDDER = "budder"
    SAUCE = "sauce"
    DIAMONDS = "diamonds"
    BUBBLE_HASH = "bubble_hash"
    DRY_SIFT = "dry_sift"
    DISTILLATE = "distillate"
    VAPE_CART = "vape_cart"
    DISPOSABLE = "disposable"
    PRE_ROLL = "pre_roll"
    EDIBLE = "edible"
    OTHER = "other"


class Vendor(Base):
    __tablename__ = 'vendors'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(200), unique=True, nullable=False, index=True)
    url = Column(String(500))
    logo_url = Column(String(500))
    description = Column(Text)
    
    # Contact & social
    email = Column(String(200))
    discord = Column(String(200))
    instagram = Column(String(200))
    
    # Shipping & payment
    ships_to = Column(JSON)  # List of states
    payment_methods = Column(JSON)  # ["Credit Card", "Crypto", etc.]
    min_order = Column(Float)
    free_shipping_threshold = Column(Float)
    
    # Ratings
    avg_rating = Column(Float, default=0.0)
    total_reviews = Column(Integer, default=0)
    
    # Drop schedule info
    typical_drop_days = Column(JSON)  # ["Monday", "Friday"]
    typical_drop_time = Column(String(50))  # "6PM EST"
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    products = relationship("Product", back_populates="vendor")
    promo_codes = relationship("PromoCode", back_populates="vendor")
    reviews = relationship("VendorReview", back_populates="vendor")


class Strain(Base):
    __tablename__ = 'strains'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(200), unique=True, nullable=False, index=True)
    normalized_name = Column(String(200), index=True)  # lowercase, no spaces
    
    # Genetics
    parent1 = Column(String(200))
    parent2 = Column(String(200))
    lineage_verified = Column(Boolean, default=False)
    
    # Classification
    strain_type = Column(String(50))  # Indica, Sativa, Hybrid
    indica_percentage = Column(Float)
    sativa_percentage = Column(Float)
    
    # Descriptions
    description = Column(Text)
    flavor_profile = Column(Text)
    aroma_profile = Column(Text)
    
    # Common terpenes (stored as JSON for flexibility)
    primary_terpenes = Column(JSON)
    
    # Average cannabinoid percentages
    avg_thca = Column(Float)
    avg_thc = Column(Float)
    avg_cbd = Column(Float)
    avg_total_cannabinoids = Column(Float)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Source tracking
    scraped_from = Column(JSON)  # ["Leafly", "Wikileaf", "AllBud"]
    last_scraped = Column(DateTime)
    
    # Relationships
    effects = relationship("Effect", secondary=strain_effects, back_populates="strains")
    products = relationship("Product", back_populates="strain")


class Product(Base):
    __tablename__ = 'products'
    
    id = Column(Integer, primary_key=True)
    external_id = Column(String(200), unique=True, nullable=False, index=True)  # vendor's product ID
    
    # Basic info
    title = Column(String(500), nullable=False)
    url = Column(String(1000), nullable=False)
    image_url = Column(String(1000))
    
    # Vendor relationship
    vendor_id = Column(Integer, ForeignKey('vendors.id'), nullable=False, index=True)
    vendor = relationship("Vendor", back_populates="products")
    
    # Strain relationship
    strain_id = Column(Integer, ForeignKey('strains.id'), index=True)
    strain = relationship("Strain", back_populates="products")
    
    # Product classification
    product_type = Column(SQLEnum(ProductType), index=True)
    
    # Pricing
    current_price = Column(Float)
    original_price = Column(Float)
    
    # Weight info
    weight_grams = Column(Float)
    price_per_gram = Column(Float)
    
    # Lab results
    thca_percentage = Column(Float)
    thc_percentage = Column(Float)
    cbd_percentage = Column(Float)
    total_cannabinoids = Column(Float)
    coa_url = Column(String(1000))  # Certificate of Analysis
    
    # Stock & availability
    in_stock = Column(Boolean, default=True)
    stock_quantity = Column(Integer)
    
    # Tracking
    first_seen = Column(DateTime, default=datetime.utcnow, index=True)
    last_seen = Column(DateTime, default=datetime.utcnow)
    last_price_change = Column(DateTime)
    view_count = Column(Integer, default=0)
    
    # Flags
    is_featured = Column(Boolean, default=False)
    is_new = Column(Boolean, default=True)  # New in last 7 days
    is_deal = Column(Boolean, default=False)  # Marked as good deal
    
    # Relationships
    price_history = relationship("PriceHistory", back_populates="product", cascade="all, delete-orphan")
    reviews = relationship("ProductReview", back_populates="product", cascade="all, delete-orphan")
    terpenes = relationship("Terpene", secondary=product_terpenes, back_populates="products")
    favorited_by = relationship("User", secondary=user_favorites, back_populates="favorite_products")


class PriceHistory(Base):
    __tablename__ = 'price_history'
    
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False, index=True)
    product = relationship("Product", back_populates="price_history")
    
    price = Column(Float, nullable=False)
    in_stock = Column(Boolean, default=True)
    recorded_at = Column(DateTime, default=datetime.utcnow, index=True)


class PromoCode(Base):
    __tablename__ = 'promo_codes'
    
    id = Column(Integer, primary_key=True)
    code = Column(String(100), nullable=False, index=True)
    
    vendor_id = Column(Integer, ForeignKey('vendors.id'), nullable=False)
    vendor = relationship("Vendor", back_populates="promo_codes")
    
    # Discount info
    discount_type = Column(String(20))  # "percentage", "fixed_amount", "free_shipping"
    discount_value = Column(Float)  # 10 for 10%, 5.00 for $5 off
    description = Column(Text)
    
    # Restrictions
    min_purchase = Column(Float)
    max_uses = Column(Integer)
    current_uses = Column(Integer, default=0)
    
    # Validity
    valid_from = Column(DateTime)
    valid_until = Column(DateTime)
    is_active = Column(Boolean, default=True)
    
    # Tracking
    submitted_by_user_id = Column(Integer, ForeignKey('users.id'))
    submitted_by = relationship("User", back_populates="submitted_codes")
    verified = Column(Boolean, default=False)
    verified_at = Column(DateTime)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(200), unique=True, index=True)
    password_hash = Column(String(200))
    
    # Discord integration
    discord_id = Column(String(100), unique=True, index=True)
    discord_username = Column(String(100))
    
    # Preferences
    notification_preferences = Column(JSON)  # Email, Discord, etc.
    favorite_strains = Column(JSON)  # List of strain names
    favorite_vendors = Column(JSON)  # List of vendor IDs
    
    # Price alerts
    price_alerts = Column(JSON)  # [{"strain": "Jealousy", "max_price": 25, "notify_via": "discord"}]
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    
    # Relationships
    favorite_products = relationship("Product", secondary=user_favorites, back_populates="favorited_by")
    submitted_codes = relationship("PromoCode", back_populates="submitted_by")
    product_reviews = relationship("ProductReview", back_populates="user")
    vendor_reviews = relationship("VendorReview", back_populates="user")


class ProductReview(Base):
    __tablename__ = 'product_reviews'
    
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    product = relationship("Product", back_populates="reviews")
    
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    user = relationship("User", back_populates="product_reviews")
    
    # Review content
    rating = Column(Float, nullable=False)  # 1-5 stars
    title = Column(String(200))
    review_text = Column(Text)
    
    # Specific ratings
    quality_rating = Column(Float)  # 1-5
    value_rating = Column(Float)  # 1-5
    potency_rating = Column(Float)  # 1-5
    flavor_rating = Column(Float)  # 1-5
    
    # Helpful votes
    helpful_count = Column(Integer, default=0)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    verified_purchase = Column(Boolean, default=False)


class VendorReview(Base):
    __tablename__ = 'vendor_reviews'
    
    id = Column(Integer, primary_key=True)
    vendor_id = Column(Integer, ForeignKey('vendors.id'), nullable=False)
    vendor = relationship("Vendor", back_populates="reviews")
    
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    user = relationship("User", back_populates="vendor_reviews")
    
    # Review content
    rating = Column(Float, nullable=False)  # 1-5 stars
    title = Column(String(200))
    review_text = Column(Text)
    
    # Specific ratings
    product_quality = Column(Float)
    shipping_speed = Column(Float)
    customer_service = Column(Float)
    packaging = Column(Float)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    helpful_count = Column(Integer, default=0)


class Terpene(Base):
    __tablename__ = 'terpenes'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    effects = Column(Text)  # e.g., "Relaxing, Anti-inflammatory"
    aroma = Column(String(200))  # e.g., "Earthy, Pine"
    
    products = relationship("Product", secondary=product_terpenes, back_populates="terpenes")


class Effect(Base):
    __tablename__ = 'effects'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    category = Column(String(50))  # "positive", "negative", "medical"
    description = Column(Text)
    
    strains = relationship("Strain", secondary=strain_effects, back_populates="effects")


class DropEvent(Base):
    """Scheduled product drops"""
    __tablename__ = 'drop_events'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(300), nullable=False)
    url = Column(String(1000))
    
    vendor_id = Column(Integer, ForeignKey('vendors.id'))
    vendor = relationship("Vendor")
    
    drop_time = Column(DateTime, nullable=False, index=True)
    image_url = Column(String(1000))
    
    # Notification tracking
    reminded_4days = Column(Boolean, default=False)
    reminded_6hours = Column(Boolean, default=False)
    reminded_drop = Column(Boolean, default=False)
    
    # Source
    source = Column(String(50))  # "email", "manual", "scraped"
    event_source_id = Column(String(200), unique=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class SearchLog(Base):
    """Track searches for analytics"""
    __tablename__ = 'search_logs'
    
    id = Column(Integer, primary_key=True)
    query = Column(String(300), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    results_count = Column(Integer)
    searched_at = Column(DateTime, default=datetime.utcnow)
