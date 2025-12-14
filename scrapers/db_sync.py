from __future__ import annotations

import sys
from pathlib import Path
from datetime import datetime
from typing import Iterable

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Make project root importable: backend/, shared/, etc.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from shared.settings import get_database_url  # noqa: E402
from backend.models import Base, Vendor, Product, PriceHistory, ProductType  # noqa: E402


def _to_product_type(ptype: str | None) -> ProductType:
    if not ptype:
        return ProductType.FLOWER
    key = ptype.strip().upper().replace("-", "_")
    try:
        return ProductType[key]
    except KeyError:
        return ProductType.FLOWER


def _db_engine():
    url = get_database_url()

    # SQLite concurrency tuning for “backend running + scraper writing”
    if url.startswith("sqlite"):
        engine = create_engine(
            url,
            connect_args={"check_same_thread": False, "timeout": 30},
            future=True,
        )
        # Enable WAL to reduce "database is locked" issues
        with engine.connect() as conn:
            conn.exec_driver_sql("PRAGMA journal_mode=WAL;")
            conn.exec_driver_sql("PRAGMA synchronous=NORMAL;")
        return engine

    return create_engine(url, future=True)


_ENGINE = _db_engine()
SessionLocal = sessionmaker(bind=_ENGINE, autoflush=False, autocommit=False, future=True)

# Ensure tables exist
Base.metadata.create_all(bind=_ENGINE)


def sync_seen_to_db(seen: dict, ids: Iterable[str]) -> int:
    """
    Upsert only the provided IDs from the in-memory `seen` dict into the DB.
    Returns number of products processed.
    """
    ids = list(ids)
    if not ids:
        return 0

    with SessionLocal() as db:
        for pid in ids:
            data = seen.get(pid)
            if not data:
                continue

            site_name = (data.get("site") or "").strip() or "Unknown"
            ptype = _to_product_type(data.get("type"))
            title = data.get("title") or ""
            url = data.get("url") or ""
            image_url = data.get("image_url")
            in_stock = bool(data.get("in_stock", True))
            last_price = data.get("last_price", None)

            first_seen = data.get("first_seen")
            last_seen = data.get("last_seen")
            # Keep as ISO strings in seen.json; convert for DB
            def _parse_dt(s: str | None):
                if not s:
                    return None
                try:
                    return datetime.fromisoformat(s.replace("Z", "+00:00"))
                except Exception:
                    return None

            first_seen_dt = _parse_dt(first_seen)
            last_seen_dt = _parse_dt(last_seen)

            # Vendor upsert
            vendor = db.query(Vendor).filter(Vendor.name == site_name).one_or_none()
            if not vendor:
                vendor = Vendor(name=site_name)
                db.add(vendor)
                db.flush()  # get vendor.id

            # Product upsert by external_id
            product = db.query(Product).filter(Product.external_id == pid).one_or_none()
            if not product:
                product = Product(
                    external_id=pid,
                    vendor_id=vendor.id,
                    type=ptype,
                    name=title[:255] if title else pid[:255],
                    description=None,
                    current_price=last_price,
                    url=url,
                    image_url=image_url,
                    is_new=True,
                    first_seen=first_seen_dt,
                    last_seen=last_seen_dt,
                    in_stock=in_stock,
                )
                db.add(product)
                db.flush()

                if last_price is not None:
                    db.add(PriceHistory(product_id=product.id, price=last_price))

            else:
                # Update fields
                product.vendor_id = vendor.id
                product.type = ptype
                if title:
                    product.name = title[:255]
                if url:
                    product.url = url
                if image_url:
                    product.image_url = image_url
                product.in_stock = in_stock
                if first_seen_dt:
                    product.first_seen = product.first_seen or first_seen_dt
                if last_seen_dt:
                    product.last_seen = last_seen_dt

                # Price change -> update + history
                if last_price is not None and product.current_price != last_price:
                    product.current_price = last_price
                    db.add(PriceHistory(product_id=product.id, price=last_price))

            db.commit()

    return len(ids)
