"""
Parse IT vacancies from hh.ru HTML (search + vacancy pages).
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from datetime import date, datetime
from html import unescape
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE = "https://hh.ru"

DEFAULT_QUERIES = [
    "Python developer",
    "Java developer",
    "аналитик данных",
    "системный аналитик",
    "QA engineer",
    "тестировщик",
    "DevOps",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.5",
}

DEFAULT_POS_LEFT = 13
DEFAULT_POS_RIGHT = 31


@dataclass
class ListingItem:
    vacancy_id: str
    title: str
    company: str
    location: str
    url: str


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update(HEADERS)
    return s


def _normalize_vacancy_url(href: str | None) -> str:
    if href:
        if "/vacancy/" in href:
            return href if href.startswith("http") else urljoin(BASE, href)
    return ''

def parse_search_page(html: str) -> list[ListingItem]:
    soup = BeautifulSoup(html, "lxml")
    out: list[ListingItem] = []
    cards = soup.select('[data-qa="vacancy-serp__vacancy vacancy-serp-item_clickme"]')
    if not cards:
        cards = soup.select('[data-qa^="vacancy-serp__vacancy"]')

    for card in cards:
        title_el = card.select_one('[data-qa="serp-item__title-text"]')
        title = title_el.get_text(strip=True) if title_el else ""

        link_el = card.select_one('a[data-qa="serp-item__title"]')
        href = link_el.get("href") if link_el else None
        if href is None:
            continue
        url = _normalize_vacancy_url(href)
        pos_left = url.find('/vacancy/')
        pos_right = url.find('?')
        if pos_left == -1:
            pos_left = DEFAULT_POS_LEFT
        if pos_right == -1:
            pos_right = DEFAULT_POS_RIGHT
        pos_left += 9
        vid = url[pos_left:pos_right]
        if not vid.isdigit():
            continue

        company_el = card.select_one('[data-qa="vacancy-serp__vacancy-employer-text"]')
        company = company_el.get_text(strip=True) if company_el else ""

        loc_el = card.select_one('[data-qa="vacancy-serp__vacancy-address"]')
        location = loc_el.get_text(strip=True) if loc_el else ""

        out.append(
            ListingItem(
                vacancy_id=vid,
                title=title,
                company=company,
                location=location,
                url=url,
            )
        )
    return out


def _digits_from_ru_salary(text: str) -> list[int]:
    """Extract integer ruble amounts from Russian salary strings."""
    cleaned = text.replace("\xa0", " ").replace("\u00a0", " ")
    cleaned = re.sub(r"[\u2009\u202f]", " ", cleaned)
    parts = re.findall(r"(\d[\d\s]*)\s*(?:₽|руб)", cleaned, flags=re.IGNORECASE)
    if not parts:
        parts = re.findall(r"\b(\d[\d\s]{2,})\b", cleaned)
    nums: list[int] = []
    for p in parts:
        try:
            n = int(re.sub(r"\s+", "", p))
        except Exception:
            continue
        if n > 1000000:
            continue
        nums.append(n)
    return nums


def parse_salary_line(text: str) -> tuple[int | None, int | None]:
    if not text:
        return None, None
    low = text.lower()
    if "не указан" in low or "по договор" in low:
        return None, None
    nums = _digits_from_ru_salary(text)
    if not nums:
        return None, None
    if len(nums) >= 2:
        return min(nums[0], nums[1]), max(nums[0], nums[1])
    if "от" in low and "до" not in low:
        return nums[0], None
    if "до" in low and "от" not in low:
        return None, nums[0]
    return nums[0], nums[0]


def _parse_meta_date(html: str) -> str | None:
    m = re.search(
        r"Дата публикации:\s*(\d{2})\.(\d{2})\.(\d{4})",
        html,
    )
    if m:
        d, mo, y = m.groups()
        return f"{y}-{mo}-{d}"
    return None


def _parse_active_flag(html: str) -> bool:
    # Do not match UI i18n strings (e.g. "Вакансия в архиве"); only structured flags.
    if re.search(r'"archived"\s*:\s*"true"', html):
        return False
    if re.search(r'"archived"\s*:\s*true\b', html):
        return False
    return True


def parse_vacancy_page(html: str, listing: ListingItem) -> dict[str, Any]:
    soup = BeautifulSoup(html, "lxml")

    title_el = soup.select_one('[data-qa="vacancy-title"]')
    title = title_el.get_text(strip=True) if title_el else listing.title

    company_el = soup.select_one('[data-qa="vacancy-company-name"]')
    company = company_el.get_text(strip=True) if company_el else listing.company

    desc_el = soup.select_one('[data-qa="vacancy-description"]')
    if desc_el:
        description = unescape(desc_el.get_text(separator="\n", strip=True))
    else:
        description = ""

    skills: list[str] = []
    for li in soup.select('[data-qa="skills-element"]'):
        label = li.select_one('[class*="magritte-tag__label"]')
        t = label.get_text(strip=True) if label else li.get_text(strip=True)
        if t:
            skills.append(t)

    salary_line = ""
    vacancy_title_block = soup.select_one(".vacancy-title")
    if vacancy_title_block:
        for span in vacancy_title_block.find_all("span", class_=True):
            txt = span.get_text(strip=True)
            if txt and (
                "Уровень дохода" in txt
                or "₽" in txt
                or "руб" in txt.lower()
            ):
                salary_line = txt
                break
        if not salary_line:
            spans = vacancy_title_block.find_all("span", class_=re.compile(r"magritte-text"))
            for sp in spans:
                txt = sp.get_text(strip=True)
                if not txt:
                    continue
                if any(
                    x in txt.lower()
                    for x in ("доход", "₽", "руб", "не указан")
                ):
                    salary_line = txt
                    break

    salary_from, salary_to = parse_salary_line(salary_line)

    posted = _parse_meta_date(html)
    if not posted:
        og = soup.find("meta", property="og:description")
        if og and og.get("content"):
            posted = _parse_meta_date(og["content"])

    active = _parse_active_flag(html)

    loc = listing.location
    fmt_el = soup.select_one('[data-qa="work-formats-text"]')
    if fmt_el:
        fmt_txt = fmt_el.get_text(" ", strip=True)
        if "Формат работы" in fmt_txt:
            loc = f"{loc} / {fmt_txt.split(':', 1)[-1].strip()}" if loc else fmt_txt

    return {
        "title": title,
        "company": company,
        "description": description,
        "skills": skills,
        "salary_from": salary_from,
        "salary_to": salary_to,
        "location": loc,
        "url": listing.url,
        "posted_date": posted,
        "active_flg": active,
    }


def fetch_search(
    sess: requests.Session,
    text: str,
    area: str,
    page: int,
    *,
    order_by: str | None = None,
    search_period: int | None = None,
) -> str:
    params: dict[str, str | int] = {
        "text": text,
        "area": area,
        "page": page,
        "items_on_page": 20,
        "ored_clusters": "true",
    }
    # Сначала свежие: publication_time. Период: search_period (дней), 0 — за всё время.
    if order_by:
        params["order_by"] = order_by
    if search_period is not None:
        params["search_period"] = search_period
    r = sess.get(f"{BASE}/search/vacancy", params=params, timeout=30)
    r.raise_for_status()
    return r.text


def fetch_vacancy(sess: requests.Session, vacancy_id: str) -> str:
    r = sess.get(f"{BASE}/vacancy/{vacancy_id}", timeout=30)
    r.raise_for_status()
    return r.text


def _parse_iso_date(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


def run(
    queries: list[str],
    area: str,
    pages_per_query: int,
    delay: float,
    max_vacancies: int | None,
    *,
    order_by: str | None = "publication_time",
    search_period: int | None = None,
    posted_since: date | None = None,
    skip_if_no_posted_date: bool = False,
) -> list[dict[str, Any]]:
    sess = _session()
    seen: set[str] = set()
    listing_order: list[ListingItem] = []

    for q in queries:
        for page in range(pages_per_query):
            html = fetch_search(
                sess,
                q,
                area,
                page,
                order_by=order_by,
                search_period=search_period,
            )
            batch = parse_search_page(html)
            if not batch:
                break
            for it in batch:
                if it.vacancy_id in seen:
                    continue
                seen.add(it.vacancy_id)
                listing_order.append(it)
            time.sleep(delay)

    if max_vacancies is not None:
        listing_order = listing_order[: max_vacancies]

    results: list[dict[str, Any]] = []
    for _idx, item in enumerate(listing_order, start=1):
        try:
            vhtml = fetch_vacancy(sess, item.vacancy_id)
        except requests.HTTPError:
            continue
        time.sleep(delay)
        detail = parse_vacancy_page(vhtml, item)
        posted = _parse_iso_date(detail.get("posted_date"))

        if posted_since is not None:
            if posted is None:
                if skip_if_no_posted_date:
                    continue
            elif posted < posted_since:
                continue

        results.append({"id": f"vac_{int(item.vacancy_id)}", **detail})

    results.sort(
        key=lambda r: (_parse_iso_date(r.get("posted_date")) or date.min),
        reverse=True,
    )

    return results