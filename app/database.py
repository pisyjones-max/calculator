from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, JSON, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

DATABASE_URL = "sqlite:///./platforma.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── MODELS ──────────────────────────────────────────────────────────────────

class Product(Base):
    __tablename__ = "products"
    id       = Column(Integer, primary_key=True, index=True)
    slug     = Column(String, unique=True, index=True, nullable=False)
    name     = Column(String, nullable=False)
    unit     = Column(String, nullable=False)   # м², шт, пог.м, уп, меш
    category = Column(String, nullable=False)   # roofing, facade, insulation ...
    prices   = relationship("SupplierPrice", back_populates="product")


class Supplier(Base):
    __tablename__ = "suppliers"
    id            = Column(Integer, primary_key=True, index=True)
    ext_id        = Column(String, unique=True, index=True)   # "stroymag_mo"
    name          = Column(String, nullable=False)
    region        = Column(String)
    delivery_days = Column(Integer, default=2)
    min_order_rub = Column(Float, default=0)
    phone         = Column(String)
    website       = Column(String)
    is_active     = Column(Boolean, default=True)
    prices        = relationship("SupplierPrice", back_populates="supplier")


class SupplierPrice(Base):
    __tablename__ = "supplier_prices"
    id          = Column(Integer, primary_key=True, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    product_id  = Column(Integer, ForeignKey("products.id"),  nullable=False)
    price       = Column(Float, nullable=False)
    in_stock    = Column(Boolean, default=True)
    source_url  = Column(String)
    updated_at  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    supplier    = relationship("Supplier", back_populates="prices")
    product     = relationship("Product",  back_populates="prices")


class Calculation(Base):
    __tablename__ = "calculations"
    id          = Column(Integer, primary_key=True, index=True)
    calc_type   = Column(String, nullable=False)   # roofing / facade / insulation
    input_params = Column(JSON, nullable=False)
    created_at  = Column(DateTime, default=datetime.utcnow)
    contact     = Column(JSON)                     # {name, phone} — опционально
    items       = relationship("CalculationItem", back_populates="calc")
    quotes      = relationship("Quote", back_populates="calc")


class CalculationItem(Base):
    __tablename__ = "calculation_items"
    id         = Column(Integer, primary_key=True, index=True)
    calc_id    = Column(Integer, ForeignKey("calculations.id"), nullable=False)
    product_slug = Column(String, nullable=False)
    name       = Column(String, nullable=False)
    qty        = Column(Float, nullable=False)
    unit       = Column(String, nullable=False)
    base_price = Column(Float, nullable=False)    # цена без поставщика
    category   = Column(String)
    calc       = relationship("Calculation", back_populates="items")


class Quote(Base):
    __tablename__ = "quotes"
    id          = Column(Integer, primary_key=True, index=True)
    number      = Column(String, unique=True)     # "КП-4827"
    calc_id     = Column(Integer, ForeignKey("calculations.id"), nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    total_price = Column(Float)
    pdf_path    = Column(String)
    created_at  = Column(DateTime, default=datetime.utcnow)
    requests    = relationship("QuoteRequest", back_populates="quote")
    calc        = relationship("Calculation", back_populates="quotes")
    supplier    = relationship("Supplier")


class QuoteRequest(Base):
    __tablename__ = "quote_requests"
    id          = Column(Integer, primary_key=True, index=True)
    quote_id    = Column(Integer, ForeignKey("quotes.id"), nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    contact     = Column(JSON)     # {name, phone, email}
    status      = Column(String, default="pending")   # pending / sent / viewed
    sent_at     = Column(DateTime)
    quote       = relationship("Quote", back_populates="requests")
    supplier    = relationship("Supplier")


def create_tables():
    Base.metadata.create_all(bind=engine)
