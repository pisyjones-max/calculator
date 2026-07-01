"""
Наполняет БД реальными данными: эталонный каталог товаров + прайсы поставщиков.

Идемпотентный: можно запускать повторно — существующие записи обновляются
(upsert), а не дублируются.

Источники:
- catalog.json               — эталонный список товаров (slug -> name/unit/category)
- krovmaterial_noginsk.json  — прайс поставщика "КровМатериалы" (Ногинск)
- stroymag_mo.json           — прайс поставщика "СтройМаркет МО"
- PLATFORMA_PRICES (ниже)    — реальные цены из собственного магазина
                                (см. platforma-next-v2/src/catalog.json,
                                источник mk4s.ru). Заполнены только позиции,
                                где есть точное совпадение по бренду и
                                единице измерения — остальное оставлено
                                пустым, чтобы не выдумывать цифры.

Запуск: python scripts/seed_db.py
"""
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, create_tables, Product, Supplier, SupplierPrice

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ── Реальные цены из собственного магазина (mk4s.ru / platforma-msk.ru) ──────
# Проверено вручную по platforma-next-v2/src/catalog.json на 2026-07-01.
# Только точные совпадения бренда — остальные позиции пока не нашли аналог,
# лучше показать "нет в наличии", чем придумать цену.
PLATFORMA_PRICES = {
    "profnastil_c20": {
        "price": 763,
        "in_stock": True,
        "source_url": "https://mk4s.ru/krovlya/profnastil/grand-line/s-20-poliester-05/",
        "note": "Профнастил С-20 Grand Line Полиэстер 0,5 мм",
    },
    "soft_roof_shinglas": {
        "price": 774,
        "in_stock": True,
        "source_url": "https://mk4s.ru/krovlya/myagkaya-krovlya/tehnonikol/kantri/bronza-bazalt/",
        "note": "Технониколь Shinglas Кантри Бронза базальт",
    },
    "screw_roofing_250": {
        "price": 910,
        "in_stock": True,
        "source_url": "https://mk4s.ru/krepezh/samorezy/samorezy-35/",
        "note": "Саморезы кровельные 4,8×35мм, уп. 250шт",
    },
    "facade_panel_docke": {
        "price": 236.5,
        "in_stock": True,
        "source_url": "https://mk4s.ru/fasadnye-materialy/fasadnye-paneli/docke/dufour/standard-davos/",
        "note": "Фасадные панели Docke Dufour Standard Давос (цена за панель 0,43м²)",
    },
    # TODO: остальные позиции каталога (металлочерепица Grand/Monterrey,
    # утеплители Кнауф/ПСБ, крепёж, планки, гидро/пароизоляция Изоспан)
    # требуют либо реального прайса из 1С, либо подбора корректного аналога
    # с проверкой единиц измерения — сделать отдельной задачей.
}

PLATFORMA_SUPPLIER = {
    "ext_id": "platforma_msk",
    "name": "PLATFORMA Склад",
    "region": "Богородский р-н, Московская область",
    "delivery_days": 0,
    "min_order_rub": 0,
    "phone": "+7 (496) 345-67-89",
    "website": "https://platforma-msk.ru",  # переезжает с platforma-pro.vercel.app
    "is_active": True,
}


def upsert_products(db, catalog_path):
    with open(catalog_path, encoding="utf-8") as f:
        data = json.load(f)
    count = 0
    for p in data["products"]:
        prod = db.query(Product).filter(Product.slug == p["slug"]).first()
        if prod:
            prod.name = p["name"]
            prod.unit = p["unit"]
            prod.category = p["category"]
        else:
            prod = Product(slug=p["slug"], name=p["name"], unit=p["unit"], category=p["category"])
            db.add(prod)
        count += 1
    db.commit()
    print(f"  products: {count} upserted from {os.path.basename(catalog_path)}")


def upsert_supplier(db, supplier_dict):
    sup = db.query(Supplier).filter(Supplier.ext_id == supplier_dict["ext_id"]).first()
    if sup:
        for k, v in supplier_dict.items():
            setattr(sup, k, v)
    else:
        sup = Supplier(**supplier_dict)
        db.add(sup)
    db.commit()
    db.refresh(sup)
    return sup


def upsert_price(db, supplier, product_slug, price, in_stock, source_url=None):
    product = db.query(Product).filter(Product.slug == product_slug).first()
    if not product:
        print(f"    ! пропущен {product_slug} — нет в products (проверь catalog.json)")
        return False
    sp = (
        db.query(SupplierPrice)
        .filter(SupplierPrice.supplier_id == supplier.id, SupplierPrice.product_id == product.id)
        .first()
    )
    if sp:
        sp.price = price
        sp.in_stock = in_stock
        sp.source_url = source_url
        sp.updated_at = datetime.utcnow()
    else:
        sp = SupplierPrice(
            supplier_id=supplier.id,
            product_id=product.id,
            price=price,
            in_stock=in_stock,
            source_url=source_url,
        )
        db.add(sp)
    return True


def load_supplier_json(db, json_path):
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    sup_data = data["supplier"]
    supplier = upsert_supplier(
        db,
        {
            "ext_id": sup_data["id"],
            "name": sup_data["name"],
            "region": sup_data.get("region"),
            "delivery_days": sup_data.get("delivery_days", 2),
            "min_order_rub": sup_data.get("min_order_rub", 0),
            "phone": sup_data.get("phone"),
            "website": sup_data.get("website"),
            "is_active": True,
        },
    )
    n = 0
    for row in data["prices"]:
        ok = upsert_price(
            db, supplier, row["slug"], row["price"], row.get("in_stock", True), row.get("url")
        )
        n += 1 if ok else 0
    db.commit()
    print(f"  {supplier.name}: {n} цен из {os.path.basename(json_path)}")


def load_platforma_supplier(db):
    supplier = upsert_supplier(db, PLATFORMA_SUPPLIER)
    n = 0
    for slug, info in PLATFORMA_PRICES.items():
        ok = upsert_price(db, supplier, slug, info["price"], info["in_stock"], info["source_url"])
        n += 1 if ok else 0
    db.commit()
    print(f"  {supplier.name}: {n} реальных цен (остальные позиции — нет в наличии, требуют подбора)")


def main():
    print("Создаю таблицы (если ещё не созданы)...")
    create_tables()

    db = SessionLocal()
    try:
        print("\n1. Товары из эталонного каталога:")
        upsert_products(db, os.path.join(BASE_DIR, "catalog.json"))

        print("\n2. Поставщики из парсинга сайтов:")
        load_supplier_json(db, os.path.join(BASE_DIR, "krovmaterial_noginsk.json"))
        load_supplier_json(db, os.path.join(BASE_DIR, "stroymag_mo.json"))

        print("\n3. Собственный магазин (реальные цены mk4s.ru):")
        load_platforma_supplier(db)

        print("\nГотово. Проверка:")
        print(f"  products:        {db.query(Product).count()}")
        print(f"  suppliers:       {db.query(Supplier).count()}")
        print(f"  supplier_prices: {db.query(SupplierPrice).count()}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
