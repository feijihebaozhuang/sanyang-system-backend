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
# 长度---240mm（标签在方括号外，横线连接数字）
_LENGTH_DASH_RE = re.compile(
    r"(?:长度|长)\s*[-—－]+\s*(\d+(?:\.\d+)?)\s*(?:cm|CM|厘米|mm|MM|毫米)?",
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
# 长度【28cm】、宽【15cm】、高【6cm】（标签在方括号外）
_OUTER_LABEL_BRACKET_RE = re.compile(
    r"(长度|宽度|高度|长|宽|高)\s*【\s*(\d+(?:\.\d+)?)\s*(?:cm|CM|厘米|mm|MM|毫米)?\s*】",
    re.I,
)
_PLATFORM_LABEL_RE = re.compile(
    r"(?:规格|尺寸|材质硬度等级|颜色分类|材质|颜色|硬度等级|硬度)[:：]\s*",
    re.I,
)
_LW_SEP = r"[x\*×]"
_LW_IN_BRACKET_RE = re.compile(
    rf"长\s*{_LW_SEP}?\s*宽\s*【\s*(\d+(?:\.\d+)?)\s*[*×xX\*]\s*(\d+(?:\.\d+)?)\s*(cm|CM|厘米|mm|MM|毫米)?\s*】",
    re.I,
)
_LW_SPLIT_BRACKET_RE = re.compile(
    rf"长\s*{_LW_SEP}?\s*宽\s*【\s*(\d+(?:\.\d+)?)\s*[*×xX\*]\s*(\d+(?:\.\d+)?)\s*】",
    re.I,
)
_LW_REV_BRACKET_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*[*×xX\*]\s*(\d+(?:\.\d+)?)\s*【\s*长\s*宽\s*】\s*(cm|CM|厘米|mm|MM|毫米)?",
    re.I,
)
_HEIGHT_NUM_FIRST_RE = re.compile(
    r"【\s*(\d+(?:\.\d+)?)\s*(?:cm|CM|厘米|mm|MM|毫米)?\s*高\s*】",
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
_QTY_SIMPLE_BRACKET_RE = re.compile(r"【\s*(\d+)\s*个\s*】", re.I)
_INNER_MARK_RE = re.compile(r"【\s*内\s*】|内径|内尺寸|\(内\)|（内）", re.I)
_OUTER_MARK_RE = re.compile(r"【\s*外\s*】|外径|外尺寸|\(外\)|（外）", re.I)
_COLOR_LABEL_RE = re.compile(r"颜色\s*[:：]\s*([^\s;；,，]+)", re.I)
_COLOR_WORDS = ("白色", "黑色", "红色", "黄色", "牛皮", "原色", "金色", "银色")

_AIRBOX_MATERIAL_PRIORITY: list[tuple[int, str, tuple[str, ...]]] = [
    (1, "台湾", ("台湾", "进口")),
    # 裸「白色/黑色/红色」多为颜色词，材料须命中 白卡/黑卡 等
    (2, "白色", ("双白", "白卡")),
    (3, "黑色", ("黑卡",)),
    (4, "红色", ("红卡",)),
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


def _val_to_cm(val: float, unit: str | None) -> float:
    """mm/毫米 → cm（÷10）；cm/厘米 或 无单位则按厘米。"""
    u = (unit or "").strip().lower()
    if u in ("mm", "毫米"):
        return val / 10.0
    return val


def _fmt_dim_cm(n: float) -> str:
    return f"{_fmt_num(n)}cm"


def _fmt_dim_cm_or_missing(key: str, dims: dict[str, float]) -> str:
    if dims.get(key) is not None:
        return _fmt_dim_cm(float(dims[key]))
    return "缺" + {"l": "长", "w": "宽", "h": "高"}.get(key, key)


def format_size_display_cm(dims: dict[str, float]) -> str:
    """第二行尺寸：统一 cm；缺维度显示「缺长/缺宽/缺高」。"""
    if not dims:
        return ""
    has_any = any(dims.get(k) is not None for k in ("l", "w", "h"))
    if not has_any:
        return ""
    return "x".join(
        [
            _fmt_dim_cm_or_missing("l", dims),
            _fmt_dim_cm_or_missing("w", dims),
            _fmt_dim_cm_or_missing("h", dims),
        ]
    )


def format_size_compact(dims: dict[str, float]) -> str:
    """打单/报价展示：19×19×6（三维齐全）；不全则返回空串，由上层回退原文。"""
    if not dims:
        return ""
    if all(dims.get(k) is not None for k in ("l", "w", "h")):
        return "×".join(_fmt_num(float(dims[k])) for k in ("l", "w", "h"))
    return ""


def missing_dimension_labels(dims: dict[str, float]) -> list[str]:
    labels = {"l": "长", "w": "宽", "h": "高"}
    return [labels[k] for k in ("l", "w", "h") if dims.get(k) is None]


def dimensions_ready_for_calc(dims: dict[str, float]) -> bool:
    return all(dims.get(k) is not None for k in ("l", "w", "h"))


def _normalize_parsed_dims_units(dims: dict[str, float], text: str) -> dict[str, float]:
    """按原文单位把已解析的长宽高统一为厘米数值。"""
    if not dims or not text:
        return dims
    out = dict(dims)
    unit_cap = r"(?P<unit>cm|CM|厘米|mm|MM|毫米)?"
    scans: list[tuple[str, list[str]]] = [
        (
            "l",
            [
                rf"【\s*(?:长度|长)\s*(\d+(?:\.\d+)?)\s*{unit_cap}\s*】",
                rf"(?:长度|长)\s*[-—－]+\s*(\d+(?:\.\d+)?)\s*{unit_cap}",
                rf"(?:长度|长)\s*【?\s*(\d+(?:\.\d+)?)\s*{unit_cap}\s*】?",
            ],
        ),
        (
            "w",
            [
                rf"【\s*(?:宽度|(?<![*×xX])宽)\s*(\d+(?:\.\d+)?)\s*{unit_cap}\s*】",
                rf"(?:宽度|(?<![*×xX])宽)\s*【\s*(\d+(?:\.\d+)?)\s*{unit_cap}\s*】",
                rf"(?:宽度|(?<![*×xX])宽)\s*【?\s*(\d+(?:\.\d+)?)\s*{unit_cap}\s*】?",
            ],
        ),
        (
            "h",
            [
                rf"【\s*(?:高度|高)\s*(\d+(?:\.\d+)?)\s*{unit_cap}\s*】",
                rf"(?:高度|高)\s*【\s*(\d+(?:\.\d+)?)\s*{unit_cap}\s*】",
                rf"(?:高度|高)\s*(\d+(?:\.\d+)?)\s*{unit_cap}\s*【",
                rf"(?:高度|高)\s*(\d+(?:\.\d+)?)(?:\s*-\s*\d+(?:\.\d+)?)?\s*(?P<unit>cm|CM|厘米|mm|MM|毫米)(?!\s*个)",
                rf"【\s*(\d+(?:\.\d+)?)\s*{unit_cap}\s*高\s*】",
            ],
        ),
    ]
    for key, patterns in scans:
        if key not in out:
            continue
        for pat in patterns:
            m = re.search(pat, text, re.I)
            if m:
                out[key] = _val_to_cm(float(m.group(1)), m.groupdict().get("unit"))
                break
    m3 = _NUM3_RE.search(text)
    if m3 and len(out) < 3:
        suffix = text[m3.end() : m3.end() + 12]
        um = re.search(r"(mm|MM|毫米|cm|CM|厘米)", suffix, re.I)
        unit = um.group(1) if um else None
        if "l" not in out:
            out["l"] = _val_to_cm(float(m3.group(1)), unit)
        if "w" not in out:
            out["w"] = _val_to_cm(float(m3.group(2)), unit)
        if "h" not in out:
            out["h"] = _val_to_cm(float(m3.group(3)), unit)
    return out


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


def parse_dimensions_cm(text: str, *, title: str = "") -> dict[str, float]:
    """从 SKU 属性 + 可选商品标题解析长宽高（厘米）。"""
    blob = platform_spec_raw(text)
    t = (title or "").strip()
    if t and t not in blob:
        blob = f"{t} {blob}".strip()
    return _parse_dimensions(blob)


def parse_dimensions_for_item(attrs: str, title: str = "") -> dict[str, float]:
    """打单/算料统一入口：合并标题后再解析。"""
    return parse_dimensions_cm(attrs, title=title)


def _apply_merged_dimension_tags(dims: dict[str, float], text: str) -> None:
    """长宽/宽高/长高 合并标签：长宽13x13、宽高10cm、长高25cm 等。"""
    unit = r"(?P<unit>cm|CM|厘米|mm|MM|毫米)?"
    for label, k1, k2 in (
        ("长宽", "l", "w"),
        ("宽高", "w", "h"),
        ("长高", "l", "h"),
    ):
        m_pair = re.search(
            rf"{label}\s*(\d+(?:\.\d+)?)\s*[*×xX]\s*(\d+(?:\.\d+)?)\s*{unit}",
            text,
            re.I,
        )
        if m_pair:
            u = m_pair.groupdict().get("unit")
            dims[k1] = _val_to_cm(float(m_pair.group(1)), u)
            dims[k2] = _val_to_cm(float(m_pair.group(2)), u)
            continue
        m_pair2 = re.search(
            rf"{label}\s*(\d+(?:\.\d+)?)\s*[*×xX]\s*(\d+(?:\.\d+)?)",
            text,
            re.I,
        )
        if m_pair2:
            dims[k1] = float(m_pair2.group(1))
            dims[k2] = float(m_pair2.group(2))
            continue
        m_same = re.search(
            rf"{label}\s*(\d+(?:\.\d+)?)\s*{unit}(?!\s*[*×xX])",
            text,
            re.I,
        )
        if m_same:
            v = _val_to_cm(float(m_same.group(1)), m_same.groupdict().get("unit"))
            dims[k1] = v
            dims[k2] = v


def _extract_lwh_triple_early(text: str) -> dict[str, float]:
    """首轮：L×W×H 三连（13×24×4、7*14*7 等），避免后续规则误删「长」。"""
    out: dict[str, float] = {}
    if not text:
        return out
    for pat in (
        r"(?:^|[\s;；、])(\d+(?:\.\d+)?)\s*[*×xX]\s*(\d+(?:\.\d+)?)\s*[*×xX]\s*(\d+(?:\.\d+)?)\s*(mm|MM|毫米|cm|CM|厘米)?",
        r"(\d+(?:\.\d+)?)\s*[*×xX]\s*(\d+(?:\.\d+)?)\s*[*×xX]\s*(\d+(?:\.\d+)?)\s*(mm|MM|毫米|cm|CM|厘米)?",
    ):
        m = re.search(pat, text, re.I)
        if not m:
            continue
        u = m.group(4) if m.lastindex and m.lastindex >= 4 else None
        out["l"] = _val_to_cm(float(m.group(1)), u)
        out["w"] = _val_to_cm(float(m.group(2)), u)
        out["h"] = _val_to_cm(float(m.group(3)), u)
        break
    return out


def _parse_dimensions(text: str) -> dict[str, float]:
    dims: dict[str, float] = {}
    if not text:
        return dims

    dims.update(_extract_lwh_triple_early(text))

    _apply_merged_dimension_tags(dims, text)

    # 宽*高【13*2】、宽高【13*2】：优先于散落的 n*n，避免把 13 当成宽、2 当成高以外的维度
    m_wh_br = re.search(
        r"宽\s*[*×xX]?\s*高\s*【\s*(\d+(?:\.\d+)?)\s*[*×xX]\s*(\d+(?:\.\d+)?)\s*】",
        text,
        re.I,
    )
    if m_wh_br:
        dims["w"] = float(m_wh_br.group(1))
        dims["h"] = float(m_wh_br.group(2))

    m_lw_in = _LW_IN_BRACKET_RE.search(text)
    m_lw_split = _LW_SPLIT_BRACKET_RE.search(text) if not m_lw_in else None
    m_lw_pair = m_lw_in or m_lw_split
    if m_lw_pair:
        u = m_lw_pair.group(3) if m_lw_pair.lastindex and m_lw_pair.lastindex >= 3 else None
        dims.setdefault("l", _val_to_cm(float(m_lw_pair.group(1)), u))
        dims.setdefault("w", _val_to_cm(float(m_lw_pair.group(2)), u))

    m_lw_spec = re.search(
        r"长\s*[*×xX]?\s*宽\s*【\s*(\d+(?:\.\d+)?)\s*[*×xX]\s*(\d+(?:\.\d+)?)\s*】\s*(mm|MM|毫米|cm|CM|厘米)?",
        text,
        re.I,
    )
    if m_lw_spec:
        u = m_lw_spec.group(3)
        dims.setdefault("l", _val_to_cm(float(m_lw_spec.group(1)), u))
        dims.setdefault("w", _val_to_cm(float(m_lw_spec.group(2)), u))

    if "l" not in dims or "w" not in dims:
        m_lw_rev = _LW_REV_BRACKET_RE.search(text)
        if m_lw_rev:
            u = m_lw_rev.group(3) if m_lw_rev.lastindex and m_lw_rev.lastindex >= 3 else None
            dims.setdefault("l", _val_to_cm(float(m_lw_rev.group(1)), u))
            dims.setdefault("w", _val_to_cm(float(m_lw_rev.group(2)), u))
    if ("l" not in dims or "w" not in dims) and re.search(
        r"【\s*长\s*宽\s*】", text, re.I
    ):
        m_lw_rev2 = re.search(
            r"(\d+(?:\.\d+)?)\s*[*×xX\*]\s*(\d+(?:\.\d+)?)\s*【\s*长\s*宽\s*】\s*(cm|CM|厘米|mm|MM|毫米)?",
            text,
            re.I,
        )
        if m_lw_rev2:
            u2 = m_lw_rev2.group(3) if m_lw_rev2.lastindex and m_lw_rev2.lastindex >= 3 else None
            dims.setdefault("l", _val_to_cm(float(m_lw_rev2.group(1)), u2))
            dims.setdefault("w", _val_to_cm(float(m_lw_rev2.group(2)), u2))

    m_wh_paren = re.search(
        r"[（(]\s*宽\s*x?\s*高\s*[）)]\s*(\d+(?:\.\d+)?)\s*[*×xX]\s*(\d+(?:\.\d+)?)\s*(?:cm|CM|厘米|mm|MM|毫米)?",
        text,
        re.I,
    )
    if m_wh_paren:
        dims.setdefault("w", float(m_wh_paren.group(1)))
        dims.setdefault("h", float(m_wh_paren.group(2)))

    for m in _BRACKET_DIM_RE.finditer(text):
        label, val = m.group(1), float(m.group(2))
        key = _LABEL_TO_KEY.get(label) or _LABEL_TO_KEY.get(label[:1])
        if key:
            dims[key] = val

    for m in _OUTER_LABEL_BRACKET_RE.finditer(text):
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
        _HEIGHT_NUM_FIRST_RE.search(text),
        re.search(
            r"(\d+(?:\.\d+)?)\s*(?:mm|MM|毫米)\s*【\s*高\s*】",
            text,
            re.I,
        ),
        re.search(
            r"(\d+(?:\.\d+)?)\s*(?:cm|CM|厘米)\s*高(?!\s*个)",
            text,
            re.I,
        ),
    ):
        if hm:
            g0 = hm.group(0) or ""
            u = "mm" if re.search(r"mm|毫米", g0, re.I) else None
            if not u and re.search(r"cm|厘米", g0, re.I):
                u = "cm"
            dims["h"] = _val_to_cm(float(hm.group(1)), u)
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
        m = _HEIGHT_NUM_FIRST_RE.search(text)
        if m:
            g0 = m.group(0) or ""
            u = "mm" if re.search(r"mm|毫米", g0, re.I) else None
            dims["h"] = _val_to_cm(float(m.group(1)), u)
    if "h" not in dims:
        m = re.search(
            r"(?:高度|高)\s*[:：]\s*(\d+(?:\.\d+)?)\s*(?:cm|CM|厘米|mm|MM|毫米)?",
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
    if "w" not in dims:
        m = re.search(
            r"(?:宽度|宽)\s*[:：]\s*(\d+(?:\.\d+)?)\s*(?:cm|CM|厘米|mm|MM|毫米)?",
            text,
            re.I,
        )
        if m:
            dims["w"] = float(m.group(1))
    if "l" not in dims:
        for pat in (
            r"(?:长度|长)\s*【?\s*(\d+(?:\.\d+)?)\s*(?:cm|CM|厘米|mm|MM|毫米)?\s*】?",
            r"(?:长度|长)\s+(\d+(?:\.\d+)?)\s*(?:cm|CM|厘米|mm|MM|毫米)(?!\s*个)",
        ):
            m = re.search(pat, text, re.I)
            if m:
                dims["l"] = _val_to_cm(float(m.group(1)), m.group(0))
                break
    if "l" not in dims:
        m = re.search(
            r"(?:长度|长)\s*[:：]\s*(\d+(?:\.\d+)?)\s*(?:cm|CM|厘米|mm|MM|毫米)?",
            text,
            re.I,
        )
        if m:
            dims["l"] = float(m.group(1))
    if "l" not in dims:
        m = _LENGTH_DASH_RE.search(text)
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
    if ("l" not in dims or "w" not in dims) and not (
        dims.get("w") is not None and dims.get("h") is not None
    ):
        for m in re.finditer(
            r"(\d+(?:\.\d+)?)\s*[*×xX]\s*(\d+(?:\.\d+)?)\s*(?:cm|CM|厘米|mm|MM|毫米)?",
            text,
            re.I,
        ):
            prefix = text[max(0, m.start() - 4) : m.start()]
            if re.search(r"(?:长宽|宽高|长高)$", prefix):
                continue
            dims.setdefault("l", float(m.group(1)))
            dims.setdefault("w", float(m.group(2)))
            break

    if len(dims) < 3:
        m3 = _NUM3_RE.search(text)
        if m3:
            suffix = text[m3.end() : m3.end() + 12]
            um = re.search(r"(mm|MM|毫米|cm|CM|厘米)", suffix, re.I)
            unit = um.group(1) if um else None
            dims.setdefault("l", _val_to_cm(float(m3.group(1)), unit))
            dims.setdefault("w", _val_to_cm(float(m3.group(2)), unit))
            dims.setdefault("h", _val_to_cm(float(m3.group(3)), unit))

    if len(dims) < 2:
        m2 = _NUM2_RE.search(text)
        if m2:
            dims.setdefault("l", float(m2.group(1)))
            dims.setdefault("w", float(m2.group(2)))

    # 宽×高（如 7*3cm）：仅缺「高」且尚无完整三维时，才按宽高压掉「长」
    if (
        dims.get("h") is None
        and dims.get("l") is not None
        and dims.get("w") is not None
        and not all(dims.get(k) is not None for k in ("l", "w", "h"))
    ):
        m_wh = re.search(
            r"(\d+(?:\.\d+)?)\s*[*×xX]\s*(\d+(?:\.\d+)?)\s*(?:cm|CM|厘米)(?!\s*[*×xX])",
            text,
            re.I,
        )
        if m_wh:
            has_long = bool(
                re.search(
                    r"(?:长度|长)\s*[:：【\d]|【\s*(?:长度|长)",
                    text,
                    re.I,
                )
            )
            has_wh = bool(re.search(r"宽|高", text, re.I))
            if has_wh or not has_long:
                dims["w"] = _val_to_cm(float(m_wh.group(1)), "cm")
                dims["h"] = _val_to_cm(float(m_wh.group(2)), "cm")
                dims.pop("l", None)

    return _normalize_parsed_dims_units(dims, text)


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
    m_simple = _QTY_SIMPLE_BRACKET_RE.search(raw)
    if m_qty:
        n = int(m_qty.group(1))
        return {
            "total_qty": n,
            "order_qty": n,
            "per_group_qty": 0,
            "qty_label": f"{n}个",
            "qty_source": "bracket",
        }
    if m_simple:
        n = int(m_simple.group(1))
        return {
            "total_qty": n,
            "order_qty": n,
            "per_group_qty": 0,
            "qty_label": f"{n}个",
            "qty_source": "bracket_qty",
        }

    per_group, bundle_label = parse_group_info(raw)
    plat = int(platform_qty or 0)
    if per_group > 0:
        groups = plat if plat > 0 else 1
        total = groups * per_group
        label = bundle_label
        if plat > 1:
            label = f"×{total}个（{total}={per_group}个×{groups}组）"
        else:
            label = f"×{total}个" if total else bundle_label
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
    """飞机盒：按优先级取材料；无关键词时由 match_production_material 默认「特硬」。"""
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


def match_production_material(text: str, mapping: list[dict] | None = None) -> str:
    """仅从 SKU 属性解析材料；飞机盒走优先级表（无关键词默认特硬），纸箱走硬编码规则。"""
    import hardcoded_config as hc

    raw = platform_spec_raw(text)
    parse_text = sanitize_sku_attrs(raw) or raw
    if is_airbox_product(raw):
        return match_airbox_material(parse_text) or "特硬"
    return hc.match_carton_material(parse_text)


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
    """打单主行：19×19×6 特硬 内径 ×300个（可带颜色，不含平台零售噪声）。"""
    parts: list[str] = []
    if size:
        parts.append(size.replace("cm", "").replace("x", "×"))
    if material:
        parts.append(material)
    if diameter_type:
        parts.append(diameter_type)
    if qty_label:
        q = qty_label if qty_label.startswith("×") else f"×{qty_label}"
        parts.append(q)
    if color:
        parts.append(color)
    return "  ".join(parts)


def build_production_spec(
    attrs: str,
    qty: int = 0,
    *,
    title: str = "",
    material_mapping: list[dict] | None = None,  # 已废弃，仅保留参数兼容
) -> dict[str, Any]:
    """
    四层展示（C）之解析数据：
    line1 — 快麦 platformSpec 原文；line2 — 外径|内径  长x宽x高  数量  材料  颜色；
    line3/4 — 刀模库存、算料由前端 + production_dashboard_cache 渲染。
    """
    raw = platform_spec_raw(attrs)
    line1 = raw
    parse_text = raw
    t = (title or "").strip()
    if t and t not in parse_text:
        parse_text = f"{t} {parse_text}".strip()

    dims = _parse_dimensions(parse_text)
    dim_missing = missing_dimension_labels(dims)
    dims_ok = dimensions_ready_for_calc(dims)

    qinfo = parse_quantity_info(parse_text, qty)
    diam = _parse_diameter_type(parse_text)
    material = match_production_material(parse_text)
    color = _parse_color(parse_text, material)

    if not dims_ok:
        formatted = (
            raw.strip()
            or line1.strip()
            or parse_text.strip()
            or t
            or ""
        )
        line2 = formatted
        size = ""
    else:
        size = format_size_compact(dims)
        formatted = _build_formatted_line(
            diameter_type=diam,
            size=size,
            qty_label=qinfo.get("qty_label") or "",
            material=material,
            color=color,
        )
        line2 = formatted or ""

    per_group = int(qinfo.get("per_group_qty") or 0)
    order_qty = int(qinfo.get("order_qty") or 0)
    real_qty = int(qinfo.get("total_qty") or 0)

    return {
        "line": line2,
        "line1": line1,
        "line2": line2,
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
        "dimensions_ok": dims_ok,
        "dimensions_missing": dim_missing,
        "is_placeholder": _is_placeholder_spec(raw),
    }


# 兼容旧调用名
parse_dimensions_with_fallback = parse_dimensions_cm
