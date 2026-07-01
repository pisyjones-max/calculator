from datetime import date
from typing import List, Dict
import os

# WeasyPrint генерирует PDF из HTML. Устанавливается: pip install weasyprint
# Fallback: если weasyprint не установлен — возвращаем None, фронт скачивает через window.print()
try:
    from weasyprint import HTML as WeasyHTML
    WEASY_AVAILABLE = True
except ImportError:
    WEASY_AVAILABLE = False

PDF_DIR = "pdfs"
os.makedirs(PDF_DIR, exist_ok=True)


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8"/>
<style>
  @page {{ margin: 20mm 18mm; }}
  body {{ font-family: Arial, Helvetica, sans-serif; font-size: 12px; color: #1a1a18; line-height: 1.5; }}
  .header {{ display: flex; justify-content: space-between; padding-bottom: 14px; border-bottom: 2px solid #1a1a18; margin-bottom: 20px; }}
  .logo {{ font-size: 22px; font-weight: 700; letter-spacing: -1px; }}
  .logo-sub {{ font-size: 11px; color: #888; margin-top: 2px; }}
  .meta {{ text-align: right; font-size: 11px; color: #888; line-height: 1.8; }}
  .meta b {{ color: #1a1a18; font-size: 14px; }}
  .supplier-block {{ background: #f5f5f2; padding: 10px 14px; border-radius: 6px; margin: 14px 0; font-size: 12px; }}
  table {{ width: 100%; border-collapse: collapse; margin: 14px 0; }}
  th {{ text-align: left; font-size: 10px; text-transform: uppercase; letter-spacing: 0.5px; padding: 7px 5px; border-bottom: 1.5px solid #1a1a18; color: #888; }}
  td {{ padding: 7px 5px; border-bottom: 0.5px solid #e8e8e0; font-size: 12px; }}
  .r {{ text-align: right; }}
  .c {{ text-align: center; }}
  .total-row td {{ font-weight: 700; font-size: 14px; border-top: 2px solid #1a1a18; border-bottom: none; padding-top: 10px; }}
  .footer {{ margin-top: 28px; padding-top: 12px; border-top: 0.5px solid #e0e0e0; font-size: 10px; color: #aaa; }}
  .cat-header {{ font-size: 10px; color: #aaa; text-transform: uppercase; letter-spacing: 0.5px; padding: 10px 5px 4px; font-weight: 600; }}
</style>
</head>
<body>
<div class="header">
  <div>
    <div class="logo">PLATFORMA</div>
    <div class="logo-sub">Кровельные и фасадные материалы</div>
    <div class="logo-sub">Богородский р-н, Московская область</div>
  </div>
  <div class="meta">
    <b>{number}</b><br/>
    Дата: {date}<br/>
    Тип расчёта: {calc_type}
  </div>
</div>

<div class="supplier-block">
  <b>Поставщик:</b> {supplier_name} &nbsp;·&nbsp;
  Доставка: {delivery} &nbsp;·&nbsp;
  {phone}
</div>

<table>
  <thead>
    <tr>
      <th>Наименование</th>
      <th class="c">Кол-во</th>
      <th class="r">Ед.</th>
      <th class="r">Цена</th>
      <th class="r">Сумма</th>
    </tr>
  </thead>
  <tbody>
    {rows}
    <tr class="total-row">
      <td colspan="4">Итого к оплате</td>
      <td class="r">{total} ₽</td>
    </tr>
  </tbody>
</table>

<div class="footer">
  Коммерческое предложение действительно 14 дней с даты выставления.<br/>
  Цены указаны с учётом скидки поставщика. Доставка рассчитывается отдельно.<br/>
  PLATFORMA — Богородский р-н МО. Расчёт выполнен автоматически, возможны погрешности ±5%.
</div>
</body>
</html>"""

CAT_NAMES = {
    "main": "Основной материал",
    "elem": "Элементы и комплектующие",
    "wood": "Деревянные конструкции",
    "fastener": "Крепёж",
    "seal": "Уплотнители",
    "insulation_elem": "Дополнительные материалы",
}

CALC_TYPE_NAMES = {
    "roofing": "Кровля",
    "facade": "Фасад",
    "insulation": "Утепление",
}


def _fmt(n: float) -> str:
    return f"{int(round(n)):,}".replace(",", "\u00a0")


def build_rows(items: List[Dict], categories: List[str]) -> str:
    rows = ""
    shown_cats = []
    for cat in categories:
        group = [it for it in items if it.get("category") == cat]
        if not group:
            continue
        cat_label = CAT_NAMES.get(cat, cat)
        rows += f'<tr><td class="cat-header" colspan="5">{cat_label}</td></tr>'
        for it in group:
            subtotal = it["qty"] * it["price"]
            stock_badge = "" if it.get("in_stock", True) else " ⚠️"
            rows += (
                f"<tr>"
                f"<td>{it['name']}{stock_badge}</td>"
                f"<td class='c'>{it['qty']}</td>"
                f"<td class='r'>{it['unit']}</td>"
                f"<td class='r'>{_fmt(it['price'])} ₽</td>"
                f"<td class='r'>{_fmt(subtotal)} ₽</td>"
                f"</tr>"
            )
    return rows


def generate_pdf(
    quote_number: str,
    calc_type: str,
    supplier_name: str,
    delivery_days: int,
    phone: str,
    items: List[Dict],
    total: float,
) -> str | None:
    """
    Генерирует PDF и возвращает путь к файлу.
    Если WeasyPrint не установлен — возвращает None.
    """
    if not WEASY_AVAILABLE:
        return None

    categories = ["main", "elem", "wood", "fastener", "seal", "insulation_elem"]
    rows = build_rows(items, categories)
    delivery_str = "Самовывоз" if delivery_days == 0 else f"{delivery_days} дн."

    html = HTML_TEMPLATE.format(
        number=quote_number,
        date=date.today().strftime("%d.%m.%Y"),
        calc_type=CALC_TYPE_NAMES.get(calc_type, calc_type),
        supplier_name=supplier_name,
        delivery=delivery_str,
        phone=phone or "",
        rows=rows,
        total=_fmt(total),
    )

    pdf_path = os.path.join(PDF_DIR, f"{quote_number}.pdf")
    WeasyHTML(string=html).write_pdf(pdf_path)
    return pdf_path
