from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import random
import os

try:
    from dotenv import load_dotenv
    load_dotenv()  # подхватывает .env локально; на проде переменные обычно задаются платформой
except ImportError:
    pass

from app.database import get_db, create_tables, Calculation, CalculationItem, Quote, QuoteRequest, Supplier
from app.services.calculators import calc_roofing, calc_facade, calc_insulation, CalcItem
from app.services.supplier_matcher import match_suppliers
from app.services.pdf_generator import generate_pdf
from app.services.telegram_notifier import notify_new_lead

app = FastAPI(title="PLATFORMA API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup():
    create_tables()

@app.get("/")
def read_root():
    # index.html — единственный источник правды для фронтенда
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    elif os.path.exists("app/index.html"):
        return FileResponse("app/index.html")
    return {
        "message": "Бэкенд работает, но файл index.html не найден в корне проекта. "
                   "Убедитесь, что он лежит в той же папке, что и main.py!"
    }


@app.get("/platforma-calc.html")
def legacy_url_redirect():
    # Раньше калькулятор дублировался в этом файле — теперь это просто
    # редирект на "/", чтобы не сломать старые ссылки/закладки.
    return RedirectResponse(url="/")


# ── 1. SCHEMAS (СТРОГО ВЫШЕ ФУНКЦИЙ) ────────────────────────────────────────

class RoofingInput(BaseModel):
    length: float
    width: float
    angle: float = 30
    material: str = "metal_tile_grand"

class FacadeInput(BaseModel):
    length: float
    width: float
    height: float
    windows: int = 0
    doors: int = 1
    material: str = "siding"

class InsulationInput(BaseModel):
    area: float
    thickness: float = 0.15
    material: str = "mineral"

class SendRequestBody(BaseModel):
    quote_id: int
    supplier_id: int
    name: str
    phone: str
    email: Optional[str] = None


# ── 2. HELPERS ──────────────────────────────────────────────────────────────

def items_to_dict(items: List[CalcItem]):
    return [it.model_dump() for it in items]

def save_calculation(db: Session, calc_type: str, input_params: dict, items: List[CalcItem]) -> Calculation:
    calc = Calculation(calc_type=calc_type, input_params=input_params)
    db.add(calc)
    db.flush()
    for it in items:
        db.add(CalculationItem(
            calc_id=calc.id,
            product_slug=it.product_slug,
            name=it.name,
            qty=it.qty,
            unit=it.unit,
            base_price=it.base_price,
            category=it.category,
        ))
    db.commit()
    db.refresh(calc)
    return calc

def format_offers(offers):
    result = []
    for o in offers:
        result.append({
            "supplier": {
                "id":            o.supplier.id,
                "name":          o.supplier.name,
                "region":        o.supplier.region,
                "delivery_days": o.supplier.delivery_days,
                "min_order_rub": o.supplier.min_order_rub,
                "phone":         o.supplier.phone,
                "website":       o.supplier.website,
            },
            "total":              o.total,
            "coverage":           o.coverage,
            "items_priced":       o.items_priced,
            "prices_updated_at":  o.prices_updated_at.isoformat() if o.prices_updated_at else None,
        })
    return result


# ── 3. CALCULATOR ROUTES ────────────────────────────────────────────────────

@app.post("/api/calculate/roofing")
def calculate_roofing(body: RoofingInput, db: Session = Depends(get_db)):
    items = calc_roofing(body.length, body.width, body.angle, body.material)
    calc  = save_calculation(db, "roofing", body.model_dump(), items)
    offers = match_suppliers(items, db)
    return {
        "calc_id": calc.id,
        "items":   items_to_dict(items),
        "base_total": round(sum(it.qty * it.base_price for it in items), 2),
        "suppliers": format_offers(offers),
    }

@app.post("/api/calculate/facade")
def calculate_facade(body: FacadeInput, db: Session = Depends(get_db)):
    items = calc_facade(body.length, body.width, body.height, body.windows, body.doors, body.material)
    calc  = save_calculation(db, "facade", body.model_dump(), items)
    offers = match_suppliers(items, db)
    return {
        "calc_id": calc.id,
        "items":   items_to_dict(items),
        "base_total": round(sum(it.qty * it.base_price for it in items), 2),
        "suppliers": format_offers(offers),
    }

@app.post("/api/calculate/insulation")
def calculate_insulation(body: InsulationInput, db: Session = Depends(get_db)):
    items = calc_insulation(body.area, body.thickness, body.material)
    calc  = save_calculation(db, "insulation", body.model_dump(), items)
    offers = match_suppliers(items, db)
    return {
        "calc_id": calc.id,
        "items":   items_to_dict(items),
        "base_total": round(sum(it.qty * it.base_price for it in items), 2),
        "suppliers": format_offers(offers),
    }


# ── 4. QUOTES & PDF ─────────────────────────────────────────────────────────

@app.post("/api/quotes")
def create_quote(calc_id: int, supplier_id: int, db: Session = Depends(get_db)):
    calc     = db.query(Calculation).filter(Calculation.id == calc_id).first()
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not calc or not supplier:
        raise HTTPException(404, "Calculation or supplier not found")

    items_q = calc.items
    items_c = [CalcItem(
        product_slug=it.product_slug, name=it.name,
        qty=it.qty, unit=it.unit, base_price=it.base_price, category=it.category
    ) for it in items_q]
    offers = match_suppliers(items_c, db)
    offer  = next((o for o in offers if o.supplier.id == supplier_id), None)
    if not offer:
        raise HTTPException(400, "No pricing data for this supplier")

    number = f"КП-{random.randint(1000,9999)}"
    quote  = Quote(
        number=number,
        calc_id=calc_id,
        supplier_id=supplier_id,
        total_price=offer.total,
    )
    db.add(quote)
    db.commit()
    db.refresh(quote)

    pdf_path = generate_pdf(
        quote_number=number,
        calc_type=calc.calc_type,
        supplier_name=supplier.name,
        delivery_days=supplier.delivery_days,
        phone=supplier.phone or "",
        items=offer.items_priced,
        total=offer.total,
    )
    if pdf_path:
        quote.pdf_path = pdf_path
        db.commit()

    return {
        "quote_id": quote.id,
        "number":   quote.number,
        "total":    quote.total_price,
        "pdf_ready": bool(pdf_path),
        "items":    offer.items_priced,
    }

@app.get("/api/quotes/{quote_id}/pdf")
def download_pdf(quote_id: int, db: Session = Depends(get_db)):
    quote = db.query(Quote).filter(Quote.id == quote_id).first()
    if not quote or not quote.pdf_path or not os.path.exists(quote.pdf_path):
        raise HTTPException(404, "PDF not ready")
    return FileResponse(quote.pdf_path, media_type="application/pdf", filename=f"{quote.number}.pdf")


# ── 5. OTHER ROUTES ─────────────────────────────────────────────────────────

@app.post("/api/quotes/send-request")
def send_request(body: SendRequestBody, db: Session = Depends(get_db)):
    quote = db.query(Quote).filter(Quote.id == body.quote_id).first()
    if not quote:
        raise HTTPException(404, "Смета не найдена")
    supplier = db.query(Supplier).filter(Supplier.id == body.supplier_id).first()
    if not supplier:
        raise HTTPException(404, "Поставщик не найден")

    req = QuoteRequest(
        quote_id=body.quote_id,
        supplier_id=body.supplier_id,
        contact={"name": body.name, "phone": body.phone, "email": body.email},
        status="sent",
        sent_at=datetime.utcnow(),
    )
    db.add(req)
    db.commit()

    calc = db.query(Calculation).filter(Calculation.id == quote.calc_id).first()
    notified = notify_new_lead(
        quote_number=quote.number,
        quote_id=quote.id,
        calc_type=calc.calc_type if calc else "",
        total=quote.total_price,
        supplier_name=supplier.name,
        client_name=body.name,
        client_phone=body.phone,
        client_email=body.email,
    )

    return {"status": "ok", "message": "Заявка принята.", "manager_notified": notified}

@app.get("/api/suppliers")
def list_suppliers(db: Session = Depends(get_db)):
    return db.query(Supplier).filter(Supplier.is_active == True).all()

@app.get("/health")
def health():
    return {"status": "ok"}