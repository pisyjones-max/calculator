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

    return [
        CalcItem(product_slug=mat["slug"],       name=mat["name"],                    qty=math.ceil(area),               unit="м²",    base_price=mat["price"], category="main"),
        CalcItem(product_slug="ridge_element_3m", name="Конёк (планка 3м)",           qty=math.ceil(ridge / 3),          unit="шт",    base_price=580,          category="elem"),
        CalcItem(product_slug="hydro_izospan_a",  name="Гидроизоляция Изоспан А",     qty=math.ceil(hydro / 15) * 15,    unit="м²",    base_price=45,           category="elem"),
        CalcItem(product_slug="batten_25x100",    name="Обрешётка (доска 25×100мм)",  qty=math.ceil(battens),            unit="пог.м", base_price=28,           category="wood"),
        CalcItem(product_slug="screw_roofing_250",name="Саморезы кровельные уп.250шт",qty=math.ceil(screws / 250),       unit="уп",    base_price=320,          category="fastener"),
        CalcItem(product_slug="wind_plank",       name="Ветровая планка",             qty=wind_planks,                   unit="шт",    base_price=290,          category="elem"),
        CalcItem(product_slug="ridge_seal",       name="Уплотнитель конька",          qty=math.ceil(ridge),              unit="пог.м", base_price=85,           category="seal"),
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
    panels = math.ceil(net_area / mat["area"] * 1.07)       # +7% запас
    outer_corners  = math.ceil(height / 3) * 4
    starter_strips = math.ceil(perimeter / 3.6)
    finish_strips  = math.ceil(perimeter / 3.6)
    j_profiles     = math.ceil((windows * 0.75 + doors * 0.9) * 2)
    screw_packs    = math.ceil(net_area * 1.5 / 250)

    return [
        CalcItem(product_slug=mat["slug"],        name=mat["name"],                      qty=panels,         unit="шт",  base_price=mat["price"], category="main"),
        CalcItem(product_slug="outer_corner_3m",  name="Внешний угол 3м",                qty=outer_corners,  unit="шт",  base_price=220,          category="elem"),
        CalcItem(product_slug="starter_strip",    name="Стартовая планка",               qty=starter_strips, unit="шт",  base_price=180,          category="elem"),
        CalcItem(product_slug="finish_strip",     name="Финишная планка",                qty=finish_strips,  unit="шт",  base_price=175,          category="elem"),
        CalcItem(product_slug="j_profile",        name="J-профиль оконный",              qty=j_profiles,     unit="шт",  base_price=160,          category="elem"),
        CalcItem(product_slug="screw_facade_250", name="Саморезы фасадные уп.250шт",    qty=screw_packs,    unit="уп",  base_price=280,          category="fastener"),
        CalcItem(product_slug="window_sill_150",  name="Подоконник 150мм",               qty=windows,        unit="шт",  base_price=320,          category="elem"),
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
    packs  = math.ceil(area * layers / 3 * 1.05)   # +5% запас; 1 уп = 3 м²

    return [
        CalcItem(product_slug=mat["slug"],             name=mat["name"],                       qty=packs,                      unit="уп",  base_price=mat["price"], category="main"),
        CalcItem(product_slug="dowel_umbrella",         name="Дюбель-зонтик",                  qty=math.ceil(area * 6),        unit="шт",  base_price=8,            category="fastener"),
        CalcItem(product_slug="armor_mesh_m2",          name="Армировочная сетка",              qty=math.ceil(area * 1.1),      unit="м²",  base_price=55,           category="elem"),
        CalcItem(product_slug="facade_glue_25kg",       name="Фасадный клей меш.25кг",         qty=math.ceil(area / 3),        unit="меш", base_price=480,          category="elem"),
        CalcItem(product_slug="vapor_barrier_m2",       name="Пароизоляция",                   qty=math.ceil(area * 1.1),      unit="м²",  base_price=38,           category="elem"),
    ]
