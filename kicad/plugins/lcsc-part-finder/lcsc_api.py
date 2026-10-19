"""Client for the JSON endpoints that www.lcsc.com itself uses.

These are not a published API: LCSC can change them at any time. Everything
LCSC-specific lives in this module so a breakage only needs fixing here.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field

BASE_URL = "https://wmsc.lcsc.com"
USER_AGENT = "KiCad-LCSC-Part-Finder/1.0 (+https://www.kicad.org)"
PAGE_SIZE = 100


class LcscError(Exception):
    pass


@dataclass
class Category:
    id: int
    name: str
    count: int

    def label(self) -> str:
        return f"{self.name} ({self.count})"


@dataclass
class SearchPlan:
    """What LCSC's search engine made of a keyword."""
    keyword: str
    scene: str                  # FULL_MATCH, PARTIAL_MATCH or NO_RESULT
    categories: list[Category]
    total: int
    understood_as: str
    understood_package: bool


@dataclass
class Part:
    code: str
    mpn: str
    manufacturer: str
    package: str
    description: str
    stock: int
    min_order: int
    order_multiple: int
    price_breaks: list[tuple[int, float]]
    datasheet: str
    url: str
    category: str
    params: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_api(cls, p: dict) -> "Part":
        breaks = []
        for tier in p.get("productPriceList") or []:
            price = tier.get("usdPrice")
            if price is None:
                try:
                    price = float(tier.get("productPrice"))
                except (TypeError, ValueError):
                    continue
            try:
                breaks.append((int(tier["ladder"]), float(price)))
            except (KeyError, TypeError, ValueError):
                continue
        code = p.get("productCode") or ""
        return cls(
            code=code,
            mpn=p.get("productModel") or "",
            manufacturer=p.get("brandNameEn") or "",
            package=p.get("encapStandard") or "",
            description=(p.get("productIntroEn") or p.get("productDescEn")
                         or p.get("productNameEn") or ""),
            stock=int(p.get("stockNumber") or 0),
            min_order=max(int(p.get("minBuyNumber") or 1), 1),
            order_multiple=max(int(p.get("split") or 1), 1),
            price_breaks=sorted(breaks),
            datasheet=p.get("pdfUrl") or "",
            url=p.get("url") or f"https://www.lcsc.com/product-detail/{code}.html",
            category=p.get("catalogName") or p.get("catalogNameEn") or "",
            params={x["paramNameEn"]: x.get("paramValueEn") or ""
                    for x in p.get("paramVOList") or [] if x.get("paramNameEn")},
        )

    def order_for(self, quantity: int) -> tuple[int, float | None, float | None]:
        """(quantity you'd actually buy, unit price, total) for needing ``quantity``."""
        buy = max(quantity, self.min_order)
        if self.order_multiple > 1:
            buy = -(-buy // self.order_multiple) * self.order_multiple
        unit = None
        for ladder, price in self.price_breaks:
            if buy >= ladder:
                unit = price
        if unit is None and self.price_breaks:
            unit = self.price_breaks[0][1]
        return buy, unit, (unit * buy if unit is not None else None)


def _request(path: str, body: dict | None = None, timeout: float = 20, retries: int = 3):
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    last_error: Exception | None = None
    for attempt in range(retries):
        if attempt:
            time.sleep(1.5 * attempt)
        try:
            req = urllib.request.Request(BASE_URL + path, data=data, headers=headers,
                                         method="POST" if data is not None else "GET")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                payload = json.load(resp)
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code in (400, 401, 403, 404):
                break
            continue
        except (urllib.error.URLError, TimeoutError, ConnectionError, ValueError) as exc:
            last_error = exc
            continue
        if payload.get("code") != 200:
            raise LcscError(f"LCSC refused the request: {payload.get('msg') or payload.get('code')}")
        return payload.get("result")
    raise LcscError(f"Could not reach LCSC ({last_error})")


def _leaf_categories(nodes, out: list[Category]) -> list[Category]:
    for node in nodes or []:
        children = node.get("childCatelogs") or []
        if node.get("isLeaf") or not children:
            out.append(Category(int(node["catalogId"]), node.get("catalogNameEn") or "?",
                                int(node.get("productNum") or 0)))
        else:
            _leaf_categories(children, out)
    return out


def plan_search(keyword: str) -> SearchPlan:
    result = _request("/ftps/wm/search/v3/global", {"keyword": keyword, "isStock": True}) or {}
    engine = result.get("searchEngineProcess") or {}
    judged = engine.get("judgeProcess") or ""
    categories = _leaf_categories(result.get("catalogVOS"), [])
    categories.sort(key=lambda c: -c.count)
    return SearchPlan(
        keyword=keyword,
        scene=result.get("scene") or "NO_RESULT",
        categories=categories,
        total=int(result.get("totalCount") or 0),
        understood_as=engine.get("searchValidWord") or "",
        # The engine tags each recognised word; "封装" means "package".
        understood_package="封装" in judged,
    )


def _category_ids(category_ids: int | list[int]) -> list[int]:
    return [category_ids] if isinstance(category_ids, int) else list(category_ids)


def param_values(plan: SearchPlan, category_ids: int | list[int]) -> dict[str, list[str]]:
    """The values each filterable parameter takes among the plan's in-stock parts, e.g.
    {"Pitch": ["2mm", "2.54mm", ...], "Gender": ["Female", "Male"]} (the site's filter panel)."""
    body = {"globalKeyword": plan.keyword, "scene": plan.scene,
            "catalogIdList": _category_ids(category_ids), "isStock": True}
    result = _request("/ftps/wm/product/query/param/group", body) or {}
    return {name: [d["name"] for d in (info or {}).get("paramDetailList") or [] if d.get("name")]
            for name, info in (result.get("paramNameValueMap") or {}).items()}


def list_parts(plan: SearchPlan, category_ids: int | list[int], page: int = 1,
               page_size: int = PAGE_SIZE,
               params: dict[str, list[str]] | None = None) -> tuple[list[Part], int, int]:
    """One page of in-stock parts in the categories matching the plan, cheapest first.
    `params` keeps only parts whose parameters take one of the given values (exact
    strings from param_values)."""
    body = {
        "globalKeyword": plan.keyword,
        "scene": plan.scene,
        "catalogIdList": _category_ids(category_ids),
        "isStock": True,
        "currentPage": page,
        "pageSize": page_size,
        "sortField": "price",
        "sortType": "asc",
    }
    if params:
        body["paramNameValueMap"] = params
    result = _request("/ftps/wm/product/query/list", body) or {}
    parts = [Part.from_api(p) for p in result.get("dataList") or []]
    return parts, int(result.get("totalRow") or 0), int(result.get("totalPage") or 0)


def get_part(code: str) -> Part | None:
    query = urllib.parse.urlencode({"productCode": code.strip().upper()})
    result = _request(f"/ftps/wm/product/detail?{query}")
    return Part.from_api(result) if result else None
