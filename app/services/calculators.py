import math
from typing import List
from pydantic import BaseModel


class CalcItem(BaseModel):
    product_slug: str
    name: str
    qty: int
    unit: str
    base_price: float
    category: str
    note: str = ""   # пояснение формулы расчёта количества — для тултипа на фронте


# ── ROOFING ─────────────────────────────────────────────────────────────────

MAT_ROOF = {
    "metal_tile_grand":     {"slug": "metal_tile_grand",     "name": "Металлочерепица Grand Line", "price": 650},
    "metal_tile_monterrey": {"slug": "metal_tile_monterrey", "name": "Металлочерепица Monterrey",   "price": 720},
    "profnastil_c20":       {"slug": "profnastil_c20",       "name": "Профнастил С-20",             "price": 420},
    "soft_roof_shinglas":   {"slug": "soft_roof_shinglas",   "name": "Мягкая кровля Shinglas",      "price": 480},
}


def calc_roofing(length: float, width: float, angle: float, material: str) -> List[CalcItem]:
    rad = math.radians(angle)
    slope_len = (width / 2) / math.cos(rad)
    area = length * slope_len * 2 * 1.10       # +10% нахлёст
    ridge = length + 0.3
    hydro = area * 1.15
    batten_rows = math.ceil(slope_len / 0.35)
    battens = batten_rows * length * 2
    screws = math.ceil(area / 2) * 8
    wind_planks = math.ceil(slope_len * 2 / 2)

    mat = MAT_ROOF.get(material, MAT_ROOF["metal_tile_grand"])

    area_qty = math.ceil(area)
    ridge_qty = math.ceil(ridge / 3)
    hydro_qty = math.ceil(hydro / 15) * 15
    battens_qty = math.ceil(battens)
    screws_qty = math.ceil(screws / 250)
    ridge_seal_qty = math.ceil(ridge)

    return [
        CalcItem(product_slug=mat["slug"],       name=mat["name"],                    qty=area_qty,       unit="м²",    base_price=mat["price"], category="main",
            note=f"Площадь ската: {length} × {slope_len:.2f} × 2 (два ската) + 10% на нахлёст = {area:.1f} м² → округлено вверх до {area_qty} м² (материал продают целыми листами)."),
        CalcItem(product_slug="ridge_element_3m", name="Конёк (планка 3м)",           qty=ridge_qty,      unit="шт",    base_price=580,          category="elem",
            note=f"Длина конька {ridge:.1f} м ÷ 3 м (длина одной планки) = {ridge/3:.2f} → округлено вверх до {ridge_qty} шт., частями планку не продают."),
        CalcItem(product_slug="hydro_izospan_a",  name="Гидроизоляция Изоспан А",     qty=hydro_qty,      unit="м²",    base_price=45,           category="elem",
            note=f"Площадь ската {area:.1f} м² + 15% запас на нахлёст полотен = {hydro:.1f} м². Рулон — 15 м², округлено вверх до кратного 15 = {hydro_qty} м²."),
        CalcItem(product_slug="batten_25x100",    name="Обрешётка (доска 25×100мм)",  qty=battens_qty,    unit="пог.м", base_price=28,           category="wood",
            note=f"{batten_rows} рядов обрешётки (шаг 0.35 м) × {length} м длины ската × 2 ската = {battens:.1f} пог.м, округлено вверх до {battens_qty}."),
        CalcItem(product_slug="screw_roofing_250",name="Саморезы кровельные уп.250шт",qty=screws_qty,     unit="уп",    base_price=320,          category="fastener",
            note=f"Норма ≈8 саморезов на м² × {area:.0f} м² = {screws} шт. Упаковка — 250 шт, поэтому берём {screws_qty} уп. (даже если по факту нужно чуть меньше)."),
        CalcItem(product_slug="wind_plank",       name="Ветровая планка",             qty=wind_planks,    unit="шт",    base_price=290,          category="elem",
            note=f"Длина торцов ската {slope_len*2:.1f} м ÷ 2 м (длина планки) = {wind_planks} шт."),
        CalcItem(product_slug="ridge_seal",       name="Уплотнитель конька",          qty=ridge_seal_qty, unit="пог.м", base_price=85,           category="seal",
            note=f"Длина конька {ridge:.1f} м, округлено вверх до {ridge_seal_qty} пог.м."),
    ]


# ── FACADE ──────────────────────────────────────────────────────────────────

MAT_FACADE = {
    "siding":        {"slug": "siding_vinyl_docke",  "name": "Сайдинг виниловый Döcke",  "price": 390, "area": 0.115},
    "facade_panel":  {"slug": "facade_panel_docke",  "name": "Фасадная панель Döcke",     "price": 550, "area": 0.24},
    "fiber":         {"slug": "fiber_cement_hbr",    "name": "Хаубер (фиброцемент)",      "price": 850, "area": 0.24},
}


def calc_facade(length: float, width: float, height: float,
                windows: int, doors: int, material: str) -> List[CalcItem]:
    perimeter = 2 * (length + width)
    wall_area = perimeter * height
    openings  = windows * 1.5 + doors * 2.1
    net_area  = wall_area - openings

    mat = MAT_FACADE.get(material, MAT_FACADE["siding"])
    panels_raw = net_area / mat["area"] * 1.07               # +7% запас
    panels = math.ceil(panels_raw)
    outer_corners  = math.ceil(height / 3) * 4
    starter_strips = math.ceil(perimeter / 3.6)
    finish_strips  = math.ceil(perimeter / 3.6)
    j_profiles     = math.ceil((windows * 0.75 + doors * 0.9) * 2)
    screw_packs    = math.ceil(net_area * 1.5 / 250)

    return [
        CalcItem(product_slug=mat["slug"],        name=mat["name"],                      qty=panels,         unit="шт",  base_price=mat["price"], category="main",
            note=f"Чистая площадь стен {net_area:.1f} м² ÷ {mat['area']} м² (площадь 1 панели) × 1.07 (запас 7% на подрезку) = {panels_raw:.2f} → округлено вверх до {panels} шт."),
        CalcItem(product_slug="outer_corner_3m",  name="Внешний угол 3м",                qty=outer_corners,  unit="шт",  base_price=220,          category="elem",
            note=f"Высота стен {height} м ÷ 3 м (длина угла) = {math.ceil(height/3)} шт. на 1 угол × 4 угла дома = {outer_corners} шт."),
        CalcItem(product_slug="starter_strip",    name="Стартовая планка",               qty=starter_strips, unit="шт",  base_price=180,          category="elem",
            note=f"Периметр {perimeter:.1f} м ÷ 3.6 м (длина планки) = {perimeter/3.6:.2f} → округлено вверх до {starter_strips} шт."),
        CalcItem(product_slug="finish_strip",     name="Финишная планка",                qty=finish_strips,  unit="шт",  base_price=175,          category="elem",
            note=f"Периметр {perimeter:.1f} м ÷ 3.6 м (длина планки) = {perimeter/3.6:.2f} → округлено вверх до {finish_strips} шт."),
        CalcItem(product_slug="j_profile",        name="J-профиль оконный",              qty=j_profiles,     unit="шт",  base_price=160,          category="elem",
            note=f"(Окна {windows} × 0.75 м + двери {doors} × 0.9 м) × 2 стороны периметра проёма = {j_profiles} шт."),
        CalcItem(product_slug="screw_facade_250", name="Саморезы фасадные уп.250шт",    qty=screw_packs,    unit="уп",  base_price=280,          category="fastener",
            note=f"Норма ≈1.5 самореза на м² × {net_area:.1f} м² = {net_area*1.5:.0f} шт. Упаковка — 250 шт, округлено вверх до {screw_packs} уп."),
        CalcItem(product_slug="window_sill_150",  name="Подоконник 150мм",               qty=windows,        unit="шт",  base_price=320,          category="elem",
            note=f"По одному подоконнику на каждое окно: {windows} шт."),
    ]


# ── INSULATION ───────────────────────────────────────────────────────────────

MAT_INSULATION = {
    "mineral": {"slug": "mineral_wool_knauf_3m2", "name": "Минвата КНАУФ уп.3м²",       "price": 1850, "slab_m": 0.05},
    "foam":    {"slug": "foam_psb25_3m2",         "name": "Пенопласт ПСБ-25 уп.3м²",    "price": 1200, "slab_m": 0.05},
    "epp":     {"slug": "xps_penoplex_3m2",       "name": "Пенополистирол XPS уп.3м²",  "price": 2100, "slab_m": 0.05},
}


def calc_insulation(area: float, thickness: float, material: str) -> List[CalcItem]:
    mat = MAT_INSULATION.get(material, MAT_INSULATION["mineral"])
    layers = math.ceil(thickness / mat["slab_m"])
    packs_raw = area * layers / 3 * 1.05   # +5% запас; 1 уп = 3 м²
    packs = math.ceil(packs_raw)
    dowels = math.ceil(area * 6)
    mesh = math.ceil(area * 1.1)
    glue = math.ceil(area / 3)
    vapor = math.ceil(area * 1.1)

    return [
        CalcItem(product_slug=mat["slug"],             name=mat["name"],                       qty=packs,  unit="уп",  base_price=mat["price"], category="main",
            note=f"Толщина {thickness*1000:.0f} мм ÷ {mat['slab_m']*1000:.0f} мм (толщина 1 плиты в упаковке) = {layers} слоя. Площадь {area} м² × {layers} слоя ÷ 3 м² (в упаковке) × 1.05 (запас 5%) = {packs_raw:.2f} → округлено вверх до {packs} уп."),
        CalcItem(product_slug="dowel_umbrella",         name="Дюбель-зонтик",                  qty=dowels, unit="шт",  base_price=8,            category="fastener",
            note=f"Норма 6 дюбелей на м² × {area} м² = {dowels} шт."),
        CalcItem(product_slug="armor_mesh_m2",          name="Армировочная сетка",              qty=mesh,   unit="м²",  base_price=55,           category="elem",
            note=f"Площадь {area} м² × 1.1 (нахлёст полотен) = {area*1.1:.1f} → округлено вверх до {mesh} м²."),
        CalcItem(product_slug="facade_glue_25kg",       name="Фасадный клей меш.25кг",         qty=glue,   unit="меш", base_price=480,          category="elem",
            note=f"Расход клея ≈1 мешок (25 кг) на 3 м²: {area} м² ÷ 3 = {area/3:.2f} → округлено вверх до {glue} меш."),
        CalcItem(product_slug="vapor_barrier_m2",       name="Пароизоляция",                   qty=vapor,  unit="м²",  base_price=38,           category="elem",
            note=f"Площадь {area} м² × 1.1 (нахлёст полотен) = {area*1.1:.1f} → округлено вверх до {vapor} м²."),
    ]
