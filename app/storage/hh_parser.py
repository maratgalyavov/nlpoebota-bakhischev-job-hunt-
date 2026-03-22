"""
Parse IT vacancies from hh.ru HTML (search + vacancy pages).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from html import unescape
from typing import Any
from urllib.parse import parse_qs, urljoin, urlparse

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


def _extract_vacancy_id_from_card(card: BeautifulSoup) -> str | None:
    for tag in card.find_all(True, id=True):
        tid = tag.get("id", "")
        if tid.isdigit():
            return tid
    resp = card.select_one('a[data-qa="vacancy-serp__vacancy_response"]')
    if resp and resp.get("href"):
        q = parse_qs(urlparse(resp["href"]).query)
        vid = q.get("vacancyId", [None])[0]
        if vid and vid.isdigit():
            return vid
    return None


def _normalize_vacancy_url(href: str | None, vacancy_id: str) -> str:
    if href:
        if "/vacancy/" in href:
            return href if href.startswith("http") else urljoin(BASE, href)
        if "adsrv.hh.ru" in href or "click" in (href or ""):
            return f"{BASE}/vacancy/{vacancy_id}"
    return f"{BASE}/vacancy/{vacancy_id}"


def parse_search_page(html: str) -> list[ListingItem]:
    soup = BeautifulSoup(html, "lxml")
    out: list[ListingItem] = []
    cards = soup.select('[data-qa="vacancy-serp__vacancy vacancy-serp-item_clickme"]')
    if not cards:
        cards = soup.select('[data-qa^="vacancy-serp__vacancy"]')

    for card in cards:
        vid = _extract_vacancy_id_from_card(card)
        if not vid:
            continue

        title_el = card.select_one('[data-qa="serp-item__title-text"]')
        title = title_el.get_text(strip=True) if title_el else ""

        link_el = card.select_one('a[data-qa="serp-item__title"]')
        href = link_el.get("href") if link_el else None
        url = _normalize_vacancy_url(href, vid)

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
        except Exception as e:
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


def vacancy_id_from_url(url: str) -> str | None:
    m = re.search(r"/vacancy/(\d+)", url)
    return m.group(1) if m else None


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
    for idx, item in enumerate(listing_order, start=1):
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

        results.append({"id": f"vac_{idx:03d}", **detail})

    results.sort(
        key=lambda r: (_parse_iso_date(r.get("posted_date")) or date.min),
        reverse=True,
    )
    for i, row in enumerate(results, start=1):
        row["id"] = f"vac_{i:03d}"

    return results


def vacancy_ids_from_rows(rows: list[Any]) -> set[str]:
    ids: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        u = row.get("url")
        if isinstance(u, str):
            vid = vacancy_id_from_url(u)
            if vid:
                ids.add(vid)
    return ids


def merge_append(
    new_rows: list[dict[str, Any]],
    existing_path: str,
) -> list[dict[str, Any]]:
    try:
        with open(existing_path, encoding="utf-8") as f:
            existing = json.load(f)
    except FileNotFoundError:
        existing = []
    if not isinstance(existing, list):
        existing = []
    known = vacancy_ids_from_rows(existing)
    fresh: list[dict[str, Any]] = []
    for row in new_rows:
        u = row.get("url")
        if not isinstance(u, str):
            continue
        vid = vacancy_id_from_url(u)
        if vid and vid not in known:
            fresh.append(row)
            known.add(vid)
    combined = list(existing) + fresh
    combined.sort(
        key=lambda r: (_parse_iso_date(r.get("posted_date")) or date.min),
        reverse=True,
    )
    for i, row in enumerate(combined, start=1):
        row["id"] = f"vac_{i:03d}"
    return combined


def main() -> None:
    p = argparse.ArgumentParser(description="Parse hh.ru IT vacancies (HTML only, no API).")
    p.add_argument(
        "--queries",
        "-q",
        default=",".join(DEFAULT_QUERIES),
        help="Comma-separated search text queries (default: IT-related bundle).",
    )
    p.add_argument(
        "--area",
        "-a",
        default="1",
        help="hh.ru area id (1=Moscow, 113=Russia, 2=SPb). Default: 1.",
    )
    p.add_argument(
        "--pages",
        "-p",
        type=int,
        default=1,
        help="Pages per query (0-based page index). Default: 1.",
    )
    p.add_argument(
        "--delay",
        type=float,
        default=0.6,
        help="Seconds between HTTP requests. Default: 0.6.",
    )
    p.add_argument(
        "--max",
        type=int,
        default=None,
        help="Max vacancies to scrape (after deduplication).",
    )
    p.add_argument(
        "--order-by",
        default="publication_time",
        help='Сортировка выдачи на hh.ru (по умолчанию publication_time — сначала свежие). Пустая строка — без параметра.',
    )
    p.add_argument(
        "--search-period",
        type=int,
        default=None,
        metavar="DAYS",
        help="Показывать вакансии не старше N дней (параметр search_period на сайте). Например 1 — за последние сутки.",
    )
    p.add_argument(
        "--since",
        metavar="YYYY-MM-DD",
        default=None,
        help="Оставить только вакансии с posted_date не раньше этой даты (после загрузки страницы вакансии).",
    )
    p.add_argument(
        "--recent-days",
        type=int,
        default=None,
        metavar="N",
        help="Удобный вариант --since: последние N календарных дней включая сегодня (N=1 — только сегодня).",
    )
    p.add_argument(
        "--include-unknown-date",
        action="store_true",
        help="При фильтре по дате не отбрасывать вакансии без posted_date (по умолчанию отбрасываются).",
    )
    p.add_argument(
        "--merge-with",
        metavar="FILE",
        default=None,
        help="Дописать только новые id вакансий к существующему JSON (дедупликация по URL).",
    )
    p.add_argument(
        "--output",
        "-o",
        default=None,
        help="Write JSON to file instead of stdout.",
    )
    args = p.parse_args()
    queries = [x.strip() for x in args.queries.split(",") if x.strip()]

    posted_since: date | None = None
    if args.since:
        try:
            posted_since = datetime.strptime(args.since.strip(), "%Y-%m-%d").date()
        except ValueError:
            print("Invalid --since, expected YYYY-MM-DD", file=sys.stderr)
            sys.exit(2)
    elif args.recent_days is not None:
        if args.recent_days < 1:
            print("--recent-days must be >= 1", file=sys.stderr)
            sys.exit(2)
        posted_since = date.today() - timedelta(days=args.recent_days - 1)

    order_by = (args.order_by or "").strip() or None

    try:
        data = run(
            queries=queries,
            area=args.area,
            pages_per_query=args.pages,
            delay=args.delay,
            max_vacancies=args.max,
            order_by=order_by,
            search_period=args.search_period,
            posted_since=posted_since,
            skip_if_no_posted_date=bool(posted_since) and not args.include_unknown_date,
        )
    except requests.RequestException as e:
        print(f"Network error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.merge_with:
        data = merge_append(data, args.merge_with)

    text = json.dumps(data, ensure_ascii=False, indent=2)
    out_path = args.output
    if args.merge_with and not out_path:
        out_path = args.merge_with
    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(text)
    else:
        print(text)


if __name__ == "__main__":
    main()