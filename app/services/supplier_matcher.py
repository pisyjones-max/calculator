from typing import List, Dict
from sqlalchemy.orm import Session
from app.database import Supplier, SupplierPrice, Product
from app.services.calculators import CalcItem


class SupplierOffer:
    def __init__(self, supplier: Supplier, items_priced: list, total: float, coverage: float):
        self.supplier = supplier
        self.items_priced = items_priced   # [{slug, qty, unit, price, subtotal, in_stock}]
        self.total = total
        self.coverage = coverage           # 0..1  — доля позиций в наличии


def match_suppliers(items: List[CalcItem], db: Session) -> List[SupplierOffer]:
    """
    Для каждого активного поставщика:
    1. Находим цены на все позиции
    2. Если позиции нет — берём base_price из CalcItem (резерв)
    3. Считаем total и coverage
    4. Сортируем: сначала по coverage (desc), потом по total (asc)
    """
    suppliers = db.query(Supplier).filter(Supplier.is_active == True).all()
    slugs = [it.product_slug for it in items]

    # Загружаем все цены одним запросом
    all_prices: List[SupplierPrice] = (
        db.query(SupplierPrice)
        .join(Product)
        .filter(Product.slug.in_(slugs))
        .all()
    )

    # price_map[supplier_id][slug] = SupplierPrice
    price_map: Dict[int, Dict[str, SupplierPrice]] = {}
    for p in all_prices:
        price_map.setdefault(p.supplier_id, {})[p.product.slug] = p

    offers = []
    for sup in suppliers:
        sup_prices = price_map.get(sup.id, {})
        items_priced = []
        in_stock_count = 0

        for it in items:
            sp = sup_prices.get(it.product_slug)
            price    = sp.price    if sp else it.base_price
            in_stock = sp.in_stock if sp else False
            if in_stock:
                in_stock_count += 1
            items_priced.append({
                "slug":      it.product_slug,
                "name":      it.name,
                "qty":       it.qty,
                "unit":      it.unit,
                "price":     price,
                "subtotal":  round(price * it.qty, 2),
                "in_stock":  in_stock,
            })

        total    = round(sum(x["subtotal"] for x in items_priced), 2)
        coverage = round(in_stock_count / len(items), 2) if items else 0

        offers.append(SupplierOffer(
            supplier=sup,
            items_priced=items_priced,
            total=total,
            coverage=coverage,
        ))

    # Скоринг: 70% цена, 30% наличие
    if offers:
        max_total = max(o.total for o in offers) or 1
        for o in offers:
            price_rank = 1 - (o.total / max_total)
            o.score = 0.7 * price_rank + 0.3 * o.coverage

        offers.sort(key=lambda o: -o.score)

    return offers
