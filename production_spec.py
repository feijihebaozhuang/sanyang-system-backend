# -*- coding: utf-8 -*-
"""SKU 属性（platformSpec / display / spec）→ 生产规格解析与展示。"""
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
_HEIGHT_TAG_ONLY_RE = re.compile(
    r"【\s*高\s*】\s*(\d+(?:\.\d+)?)\s*(?:cm|CM|厘米|mm|MM|毫米)?",
    re.I,
)
_PLATFORM_LABEL_RE = re.compile(
    r"(?:规格|尺寸|材质硬度等级|颜色分类|材质|颜色|硬度等级|硬度)[:：]\s*",
    re.I,
)
_LW_IN_BRACKET_RE = re.compile(
    r"长\s*x?\s*宽\s*【\s*(\d+(?:\.\d+)?)\s*[*×xX]\s*(\d+(?:\.\d+)?)\s*(?:cm|CM|厘米|mm|MM|毫米)?\s*】",
    re.I,
)
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
_BUNDLE_RE = re.compile(
    r"""[-/／\-]?\s*【?\s*(\d+)\s*个\s*[/／]?(?:一)?(捆|组|袋|包)\s*】?""",
    re.I,
)
_QTY_BRACKET_RE = re.compile(r"【\s*数量\s*(\d+)\s*个\s*】", re.I)
_INNER_MARK_RE = re.compile(r"【\s*内\s*】|内径|内尺寸|\(内\)|（内）", re.I)
_OUTER_MARK_RE = re.compile(r"【\s*外\s*】|外径|外尺寸|\(外\)|（外）", re.I)
_COLOR_LABEL_RE = re.compile(r"颜色\s*[:：]\s*([^\s;；,，]+)", re.I)
_COLOR_WORDS = ("白色", "黑色", "红色", "黄色", "牛皮", "原色", "金色", "银色")

_AIRBOX_MATERIAL_PRIORITY: list[tuple[int, str, tuple[str, ...]]] = [
    (1, "台湾", ("台湾", "进口")),
    (2, "白色", ("白色", "双白", "白卡")),
    (3, "黑色", ("黑色", "黑卡")),
    (4, "红色", ("红色", "红卡")),
    (5, "P6D", ("P6D",)),
    (6, "特硬", ("D6D", "特硬")),
    (7, "EB", ("五层EB", "EB")),
    (8, "BC", ("五层BC", "BC")),
    (9, "E坑", ("E坑", "E瓦", "三层", "五层")),
]

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


def platform_spec_raw(attrs: str) -> str:
    """完整保留 platformSpec 原文（display/spec），不做删减。"""
    return (attrs or "").strip()


def sanitize_sku_attrs(text: str) -> str:
    """仅用于辅助匹配材料/颜色时去掉平台字段名前缀；展示与尺寸解析用原文。"""
    if not text:
        return ""
    t = _PLATFORM_LABEL_RE.sub("", text)
    t = re.sub(r"[;；]+\s*", " ", t)
    return re.sub(r"\s{2,}", " ", t).strip()


def parse_dimensions_cm(text: str) -> dict[str, float]:
    """仅从 SKU 属性文本解析长宽高（厘米）。"""
    return _parse_dimensions(platform_spec_raw(text))


def _parse_dimensions(text: str) -> dict[str, float]:
    dims: dict[str, float] = {}
    if not text:
        return dims

    m = _LW_IN_BRACKET_RE.search(text) or _LW_SPLIT_BRACKET_RE.search(text)
    if m:
        dims["l"] = float(m.group(1))
        dims["w"] = float(m.group(2))

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

    for hm in (_HEIGHT_BRACKET_RE.search(text), _HEIGHT_TAG_ONLY_RE.search(text)):
        if hm:
            dims["h"] = float(hm.group(1))
            break

    if "h" not in dims:
        m = re.search(
            r"(?:高度|高)\s*(\d+(?:\.\d+)?)\s*(?:-\s*\d+(?:\.\d+)?)?\s*(?:cm|CM|厘米|mm|MM|毫米)?\s*【",
            text,
            re.I,
        )
        if m:
            dims["h"] = float(m.group(1))
    if "h" not in dims:
        for pat in (
            r"(?:高度|高)\s*(\d+(?:\.\d+)?)(?:\s*-\s*\d+(?:\.\d+)?)?\s*(?:cm|CM|厘米|mm|MM|毫米)(?!\s*个)",
            r"(\d+(?:\.\d+)?)(?:\s*-\s*\d+(?:\.\d+)?)?\s*(?:cm|CM|厘米|mm|MM|毫米)\s*高(?!\s*个)",
        ):
            m = re.search(pat, text, re.I)
            if m:
                dims["h"] = float(m.group(1))
                break
    if "h" not in dims:
        m = re.search(
            r"【\s*(\d+(?:\.\d+)?)\s*(?:cm|CM|厘米|mm|MM|毫米)?\s*高\s*】",
            text,
            re.I,
        )
        if m:
            dims["h"] = float(m.group(1))

    if "w" not in dims:
        m = re.search(
            r"(?:宽度|宽)\s*【?\s*(\d+(?:\.\d+)?)\s*(?:cm|CM|厘米|mm|MM|毫米)?\s*】?",
            text,
            re.I,
        )
        if m:
            dims["w"] = float(m.group(1))
    if "l" not in dims:
        m = re.search(
            r"(?:长度|长)\s*【?\s*(\d+(?:\.\d+)?)\s*(?:cm|CM|厘米|mm|MM|毫米)?\s*】?",
            text,
            re.I,
        )
        if m:
            dims["l"] = float(m.group(1))

    if "l" not in dims or "w" not in dims:
        m = re.search(
            r"长\s*宽\s*【\s*(\d+(?:\.\d+)?)\s*[*×xX]\s*(\d+(?:\.\d+)?)",
            text,
            re.I,
        )
        if m:
            dims.setdefault("l", float(m.group(1)))
            dims.setdefault("w", float(m.group(2)))
    if "l" not in dims or "w" not in dims:
        m = re.search(
            r"(\d+(?:\.\d+)?)\s*[*×xX]\s*(\d+(?:\.\d+)?)\s*(?:cm|CM|厘米|mm|MM|毫米)?",
            text,
            re.I,
        )
        if m:
            dims.setdefault("l", float(m.group(1)))
            dims.setdefault("w", float(m.group(2)))

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


def _has_size_digits(text: str) -> bool:
    t = text or ""
    return bool(
        re.search(
            r"\d+(?:\.\d+)?\s*[*×xX]\s*\d+|\d+\s*(?:cm|CM|厘米)|【\s*\d|(?:长|宽|高|长度|宽度|高度)",
            t,
            re.I,
        )
    )


def _parse_diameter_type(text: str) -> str:
    """内外径：无标注时默认为外径。"""
    t = text or ""
    has_inner = bool(_INNER_MARK_RE.search(t))
    has_outer = bool(_OUTER_MARK_RE.search(t))
    if has_inner and not has_outer:
        return "内径"
    if has_outer and not has_inner:
        return "外径"
    if has_inner and has_outer:
        im = _INNER_MARK_RE.search(t)
        om = _OUTER_MARK_RE.search(t)
        if im and om and im.start() < om.start():
            return "内径"
        return "外径"
    return "外径"


def parse_group_info(text: str) -> tuple[int, str]:
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


def parse_quantity_info(text: str, platform_qty: int = 0) -> dict[str, Any]:
    """
    数量：优先 【数量N个】、N个/组 等；否则用平台 item.qty。
    返回 total_qty（算料用）、order_qty（组数）、qty_label（展示用）。
    """
    raw = text or ""
    m_qty = _QTY_BRACKET_RE.search(raw)
    if m_qty:
        n = int(m_qty.group(1))
        return {
            "total_qty": n,
            "order_qty": n,
            "per_group_qty": 0,
            "qty_label": f"{n}个",
            "qty_source": "bracket",
        }

    per_group, bundle_label = parse_group_info(raw)
    plat = int(platform_qty or 0)
    if per_group > 0:
        groups = plat if plat > 0 else 1
        total = groups * per_group
        label = bundle_label
        if plat > 1:
            label = f"{bundle_label} ×{plat}"
        return {
            "total_qty": total,
            "order_qty": groups,
            "per_group_qty": per_group,
            "qty_label": label,
            "qty_source": "bundle",
        }

    n = plat
    return {
        "total_qty": n,
        "order_qty": n,
        "per_group_qty": 0,
        "qty_label": f"{n}个" if n else "",
        "qty_source": "platform",
    }


def _parse_color(text: str, material: str = "") -> str:
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
    t = platform_spec_raw(attrs)
    if not t:
        return True
    if "纸箱" in t and "飞机盒" not in t:
        return False
    return True


def _kw_in_attrs(kw: str, text: str) -> bool:
    if not kw or not text:
        return False
    if kw.isascii():
        return kw.upper() in text.upper()
    return kw in text


def match_airbox_material(text: str) -> str:
    """飞机盒：按优先级取材料；找不到返回空（不猜默认值）。"""
    t = (text or "").strip()
    if not t:
        return ""
    raw: list[tuple[int, str, str]] = []
    for rank, label, kws in _AIRBOX_MATERIAL_PRIORITY:
        for kw in sorted(kws, key=len, reverse=True):
            if _kw_in_attrs(kw, t):
                raw.append((rank, label, kw))
                break
    if not raw:
        return ""
    kept: list[tuple[int, str, int]] = []
    for rank, label, kw in raw:
        if any(
            len(kw2) > len(kw) and kw in kw2 and _kw_in_attrs(kw2, t)
            for _, _, kw2 in raw
        ):
            continue
        kept.append((rank, label, len(kw)))
    if not kept:
        return ""
    kept.sort(key=lambda x: (x[0], -x[2]))
    return kept[0][1]


def _match_carton_material(text: str, mapping: list[dict]) -> str:
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
    """仅从 SKU 属性解析材料；飞机盒走优先级表，纸箱走 mapping。"""
    raw = platform_spec_raw(text)
    parse_text = sanitize_sku_attrs(raw) or raw
    if is_airbox_product(raw):
        return match_airbox_material(parse_text)
    return _match_carton_material(parse_text, mapping or [])


def _is_placeholder_spec(attrs: str) -> bool:
    raw = platform_spec_raw(attrs)
    if any(
        k in raw
        for k in ("定制拍单", "专拍", "联系客服", "1个起订", "无需刀模", "不接受退货")
    ):
        if not _has_size_digits(raw):
            return True
    return not _has_size_digits(raw)


def _build_formatted_line(
    *,
    diameter_type: str,
    size: str,
    qty_label: str,
    material: str,
    color: str,
) -> str:
    parts: list[str] = []
    if diameter_type:
        parts.append(diameter_type)
    if size:
        parts.append(size)
    if qty_label:
        parts.append(qty_label)
    if material:
        parts.append(material)
    if color:
        parts.append(color)
    return "  ".join(parts)


def build_production_spec(
    attrs: str,
    qty: int = 0,
    *,
    material_mapping: list[dict] | None = None,
) -> dict[str, Any]:
    """
    两步：① 完整保留 platformSpec 原文；② 逐项解析展示。
    展示格式：外径/内径  长x宽x高  数量  材料  颜色 ｜ 原文（只增不减）
    """
    raw = platform_spec_raw(attrs)
    dims = _parse_dimensions(raw)
    size = ""
    if dims.get("l") and dims.get("w") and dims.get("h"):
        size = f"{_fmt_num(dims['l'])}x{_fmt_num(dims['w'])}x{_fmt_num(dims['h'])}"
    elif dims.get("l") and dims.get("w"):
        size = f"{_fmt_num(dims['l'])}x{_fmt_num(dims['w'])}"

    qinfo = parse_quantity_info(raw, qty)
    diam = _parse_diameter_type(raw)
    material = match_production_material(raw, material_mapping or [])
    color = _parse_color(raw, material)

    formatted = _build_formatted_line(
        diameter_type=diam,
        size=size,
        qty_label=qinfo.get("qty_label") or "",
        material=material,
        color=color,
    )
    if formatted and raw:
        line = f"{formatted} ｜ {raw}"
    elif formatted:
        line = formatted
    else:
        line = raw

    per_group = int(qinfo.get("per_group_qty") or 0)
    order_qty = int(qinfo.get("order_qty") or 0)
    real_qty = int(qinfo.get("total_qty") or 0)

    return {
        "line": line,
        "formatted": formatted,
        "platform_spec_raw": raw,
        "size": size,
        "bundle": parse_group_info(raw)[1],
        "qty": real_qty,
        "order_qty": order_qty,
        "per_group_qty": per_group,
        "qty_label": qinfo.get("qty_label") or "",
        "qty_source": qinfo.get("qty_source") or "",
        "material": material,
        "color": color,
        "diameter_type": diam,
        "length": dims.get("l"),
        "width": dims.get("w"),
        "height": dims.get("h"),
        "is_placeholder": _is_placeholder_spec(raw),
    }


# 兼容旧调用名
parse_dimensions_with_fallback = parse_dimensions_cm
