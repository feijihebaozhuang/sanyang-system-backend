# -*- coding: utf-8 -*-
"""买家下单属性 → 生产规格（长x宽x高、捆数、数量、材料简称）。"""
from __future__ import annotations

import re
from typing import Any

# 【长度18CM】【宽度14CM】【高度5CM】
_BRACKET_DIM_RE = re.compile(
    r"【\s*(长度|宽度|高度|长|宽|高)\s*(\d+(?:\.\d+)?)\s*(?:cm|CM|厘米|mm|MM|毫米)?\s*】",
    re.I,
)
_LABELED_DIM_RE = re.compile(
    r"(长度|宽度|高度)\s*【\s*(\d+(?:\.\d+)?)\s*(?:cm|CM|厘米|mm|MM|毫米)?\s*】",
    re.I,
)
_HEIGHT_BRACKET_RE = re.compile(
    r"(?:高度|高)\s*【\s*(\d+(?:\.\d+)?)\s*(?:cm|CM|厘米|mm|MM|毫米)?\s*】",
    re.I,
)
# 【高】25cm / 【高】25（无「高度」二字）
_HEIGHT_TAG_ONLY_RE = re.compile(
    r"【\s*高\s*】\s*(\d+(?:\.\d+)?)\s*(?:cm|CM|厘米|mm|MM|毫米)?",
    re.I,
)
_PLATFORM_LABEL_RE = re.compile(
    r"(?:规格|尺寸|材质硬度等级|颜色分类|材质|颜色|硬度等级|硬度)[:：]\s*",
    re.I,
)
# 长x宽【20x20cm】 / 长x宽【20*20】
_LW_IN_BRACKET_RE = re.compile(
    r"长\s*x?\s*宽\s*【\s*(\d+(?:\.\d+)?)\s*[*×xX]\s*(\d+(?:\.\d+)?)\s*(?:cm|CM|厘米|mm|MM|毫米)?\s*】",
    re.I,
)
# 长x宽【16x16】旧格式（括号内无 cm）
_LW_SPLIT_BRACKET_RE = re.compile(
    r"长\s*x?\s*宽\s*【\s*(\d+(?:\.\d+)?)\s*[*×xX]\s*(\d+(?:\.\d+)?)\s*】",
    re.I,
)
_NUM3_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*[*×xX]\s*(\d+(?:\.\d+)?)\s*[*×xX]\s*(\d+(?:\.\d+)?)"
    r"\s*(?:cm|CM|厘米|mm|MM|毫米)?",
    re.I,
)
_NUM2_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*[*×xX]\s*(\d+(?:\.\d+)?)\s*(?:cm|CM|厘米|mm|MM|毫米)?",
    re.I,
)
# N个/捆、N个/组、N个一组、-/10个一组 等
_BUNDLE_RE = re.compile(
    r"""[-/／\-]?\s*【?\s*(\d+)\s*个\s*[/／]?(?:一)?(捆|组|袋|包)\s*】?""",
    re.I,
)
# 仅明确写法，不用【内/【外（会误伤【高度】等）
_OUTER_DIAM_RE = re.compile(r"外径|外尺寸|\(外\)|（外）", re.I)
_INNER_DIAM_RE = re.compile(r"内径|内尺寸|\(内\)|（内）", re.I)
_COLOR_LABEL_RE = re.compile(r"颜色\s*[:：]\s*([^\s;；,，]+)", re.I)
_COLOR_WORDS = ("白色", "黑色", "红色", "黄色", "牛皮", "原色", "金色", "银色")
_MATERIAL_FALLBACK_RE = re.compile(
    r"(特硬|优质|台湾|三层|加硬|E瓦|瓦楞|进口)",
    re.I,
)

# 飞机盒类目材料优先级（数字越小优先级越高，仅匹配 SKU 属性值）
_AIRBOX_MATERIAL_PRIORITY: list[tuple[int, str, tuple[str, ...]]] = [
    (1, "台湾", ("台湾", "进口")),
    (2, "白色", ("白色", "双白", "白卡")),
    (3, "黑色", ("黑色", "黑卡")),
    (4, "红色", ("红色", "红卡")),
    (5, "P6D", ("P6D",)),
    (6, "特硬", ("D6D", "特硬")),
    (7, "EB", ("五层EB", "EB")),  # 五层EB 先于单独「五层」
    (8, "BC", ("五层BC", "BC")),
    (9, "E坑", ("E坑", "E瓦", "三层", "五层")),
]
_AIRBOX_DEFAULT_MATERIAL = "特硬"

_LABEL_TO_KEY = {
    "长度": "l",
    "长": "l",
    "宽度": "w",
    "宽": "w",
    "高度": "h",
    "高": "h",
}


def _fmt_num(n: float) -> str:
    if n == int(n):
        return str(int(n))
    s = f"{n:.2f}".rstrip("0").rstrip(".")
    return s


def sanitize_sku_attrs(text: str) -> str:
    """去掉平台字段名前缀，只保留属性值供解析/展示。"""
    if not text:
        return ""
    t = _PLATFORM_LABEL_RE.sub("", text)
    t = re.sub(r"[;；]+\s*", " ", t)
    return re.sub(r"\s{2,}", " ", t).strip()


def parse_dimensions_cm(text: str) -> dict[str, float]:
    """解析长/宽/高（厘米）。"""
    return _parse_dimensions(sanitize_sku_attrs(text) or text)


def _parse_dimensions(text: str) -> dict[str, float]:
    dims: dict[str, float] = {}
    if not text:
        return dims

    m = _LW_IN_BRACKET_RE.search(text) or _LW_SPLIT_BRACKET_RE.search(text)
    if m:
        dims["l"] = float(m.group(1))
        dims["w"] = float(m.group(2))

    m2_early = re.search(
        r"(\d+(?:\.\d+)?)\s*[*×xX]\s*(\d+(?:\.\d+)?)\s*(?:cm|CM|厘米)?",
        text,
        re.I,
    )
    if m2_early and "l" not in dims:
        dims["l"] = float(m2_early.group(1))
        dims["w"] = float(m2_early.group(2))

    for m in _BRACKET_DIM_RE.finditer(text):
        label, val = m.group(1), float(m.group(2))
        key = _LABEL_TO_KEY.get(label) or _LABEL_TO_KEY.get(label[:1])
        if key:
            dims[key] = val

    for m in _LABELED_DIM_RE.finditer(text):
        label, val = m.group(1), float(m.group(2))
        key = _LABEL_TO_KEY.get(label)
        if key:
            dims[key] = val

    for hm in (
        _HEIGHT_BRACKET_RE.search(text),
        _HEIGHT_TAG_ONLY_RE.search(text),
    ):
        if hm:
            dims["h"] = float(hm.group(1))
            break

    if len(dims) < 3:
        m3 = _NUM3_RE.search(text)
        if m3:
            dims.setdefault("l", float(m3.group(1)))
            dims.setdefault("w", float(m3.group(2)))
            dims.setdefault("h", float(m3.group(3)))

    if len(dims) < 2:
        m2 = _NUM2_RE.search(text)
        if m2:
            dims.setdefault("l", float(m2.group(1)))
            dims.setdefault("w", float(m2.group(2)))

    return dims


def _parse_diameter_type(text: str) -> str:
    """外径/内径：只看买家属性原文，不看商品标题（避免标题「内径现货」误判）。"""
    t = text or ""
    if not t:
        return ""
    has_outer = bool(_OUTER_DIAM_RE.search(t))
    has_inner = bool(_INNER_DIAM_RE.search(t))
    if has_outer and not has_inner:
        return "外径"
    if has_inner and not has_outer:
        return "内径"
    if has_outer and has_inner:
        om = _OUTER_DIAM_RE.search(t)
        im = _INNER_DIAM_RE.search(t)
        if om and (not im or om.start() <= im.start()):
            return "外径"
        return "内径"
    return ""


def parse_group_info(text: str) -> tuple[int, str]:
    """解析每捆/组数量，返回 (每组个数, 展示文本) 如 (10, '10个/组')。"""
    if not text:
        return 0, ""
    m = _BUNDLE_RE.search(text)
    if m:
        n = int(m.group(1))
        unit = (m.group(2) or "组").strip()
        return n, f"{n}个/{unit}"
    m_legacy = re.search(r"【?\s*(\d+)\s*个一捆\s*】?", text, re.I)
    if m_legacy:
        n = int(m_legacy.group(1))
        return n, f"{n}个/捆"
    return 0, ""


def _parse_bundle(text: str) -> str:
    _, label = parse_group_info(text)
    return label


def _parse_color(text: str, material: str = "") -> str:
    """从买家属性解析颜色（与材料分开展示）。"""
    if not text:
        return ""
    m = _COLOR_LABEL_RE.search(text)
    if m:
        c = m.group(1).strip()
        return c if c and c != material else ""
    for word in _COLOR_WORDS:
        if word in text and word != material:
            return word
    return ""


def is_airbox_product(attrs: str) -> bool:
    """飞机盒类目（正方形/长方形/带扣/扣底/双插等），纸箱走独立逻辑。"""
    t = sanitize_sku_attrs(attrs) or (attrs or "").strip()
    if not t:
        return True
    if "纸箱" in t and "飞机盒" not in t:
        return False
    if any(k in t for k in ("扣底", "双插", "带扣", "飞机盒", "正方形", "长方形")):
        return True
    if re.search(r"3层|5层|五层", t) and "飞机盒" not in t:
        if not any(k in t for k in ("扣底", "双插")):
            return False
    return True


def _kw_in_attrs(kw: str, text: str) -> bool:
    if not kw or not text:
        return False
    if kw.isascii():
        return kw.upper() in text.upper()
    return kw in text


def match_airbox_material(text: str) -> str:
    """飞机盒：按优先级取 SKU 属性中最高档材料；无匹配则特硬。"""
    t = (text or "").strip()
    if not t:
        return _AIRBOX_DEFAULT_MATERIAL
    raw: list[tuple[int, str, str]] = []
    for rank, label, kws in _AIRBOX_MATERIAL_PRIORITY:
        for kw in sorted(kws, key=len, reverse=True):
            if _kw_in_attrs(kw, t):
                raw.append((rank, label, kw))
                break
    if not raw:
        return _AIRBOX_DEFAULT_MATERIAL
    # 去掉被更长关键词覆盖的短词（如「五层」被「五层BC」覆盖）
    kept: list[tuple[int, str, int]] = []
    for rank, label, kw in raw:
        if any(
            len(kw2) > len(kw) and kw in kw2 and _kw_in_attrs(kw2, t)
            for _, _, kw2 in raw
        ):
            continue
        kept.append((rank, label, len(kw)))
    if not kept:
        return _AIRBOX_DEFAULT_MATERIAL
    kept.sort(key=lambda x: (x[0], -x[2]))
    return kept[0][1]


def _match_carton_material(text: str, mapping: list[dict]) -> str:
    """纸箱等：沿用后台关键词映射。"""
    low = (text or "").lower()
    best = ""
    best_len = 0
    for row in mapping or []:
        label = (row.get("label") or row.get("production_label") or "").strip()
        if not label:
            continue
        kws = [
            k.strip().lower()
            for k in (row.get("keywords") or "").split(",")
            if k.strip()
        ]
        for kw in kws:
            if kw and kw in low and len(kw) > best_len:
                best = label
                best_len = len(kw)
    return best


def match_production_material(text: str, mapping: list[dict] | None = None) -> str:
    """
    从 SKU 属性值解析生产材料（不看商品标题）。
    飞机盒类目按固定优先级；纸箱等走 mapping 配置。
    """
    t = sanitize_sku_attrs(text) or (text or "").strip()
    if is_airbox_product(t):
        return match_airbox_material(t)
    material = _match_carton_material(t, mapping or [])
    if not material:
        hm = _MATERIAL_FALLBACK_RE.search(t)
        if hm:
            material = hm.group(1)
            if material == "进口":
                material = "特硬"
    return material


def build_production_spec(
    attrs: str,
    qty: int = 0,
    *,
    material_mapping: list[dict] | None = None,
) -> dict[str, Any]:
    """
    返回 production_spec 字段供打单管理展示（仅解析买家下单 SKU 属性，不用商品标题）。
    line 示例: 外径 18x14x5   50个/捆   特硬   ×1（数量在材料/颜色后）
    """
    text = sanitize_sku_attrs(attrs) or (attrs or "").strip()
    diam_type = _parse_diameter_type(text)

    dims = _parse_dimensions(text)
    size = ""
    if dims.get("l") and dims.get("w") and dims.get("h"):
        size = f"{_fmt_num(dims['l'])}x{_fmt_num(dims['w'])}x{_fmt_num(dims['h'])}"
    elif dims.get("l") and dims.get("w"):
        size = f"{_fmt_num(dims['l'])}x{_fmt_num(dims['w'])}"

    order_qty = int(qty or 0)
    per_group, bundle = parse_group_info(text)
    if per_group > 0 and order_qty > 0:
        real_qty = order_qty * per_group
    else:
        real_qty = order_qty

    airbox = is_airbox_product(text)
    material = match_production_material(text, material_mapping or [])
    if airbox and not material:
        material = _AIRBOX_DEFAULT_MATERIAL
    color = _parse_color(text, material)

    parts: list[str] = []
    if diam_type:
        parts.append(diam_type)
    if size:
        parts.append(size)
    if bundle:
        parts.append(bundle)
    if material:
        parts.append(material)
    if color:
        parts.append(color)
    if order_qty:
        parts.append(f"×{order_qty}")

    line = "   ".join(parts) if parts else (text if text and text != "—" else "")

    return {
        "line": line,
        "size": size,
        "bundle": bundle,
        "qty": real_qty,
        "order_qty": order_qty,
        "per_group_qty": per_group,
        "material": material,
        "color": color,
        "diameter_type": diam_type,
        "length": dims.get("l"),
        "width": dims.get("w"),
        "height": dims.get("h"),
    }
