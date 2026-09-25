#!/usr/bin/env python3
"""Vibe 情報 v4.3 來源批次掃描：只做「發現＋日期初篩＋粗排序」，不做核實。

一次讀完 sources_v4.3.json 裡的 RSS／Atom／JSON API，抽出 title、URL、作者、
發表時間與短摘要，依時間窗過濾、依成果線索打分，輸出候選 JSON 與精簡摘要。
只用 Python 標準庫；Python 不能連網時，排程改用 web_fetch 逐一讀核心來源。

用法：
  python scan_feeds_v43.py --sources sources_v4.3.json --out scan_v43_2026-09-25.json
  python scan_feeds_v43.py --sources sources_v4.3.json --out x.json --only-cats 03,09,10
  python scan_feeds_v43.py --sources sources_v4.3.json --out x.json --skip reddit_claudeai
"""
import argparse
import html
import json
import re
import sys
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

TPE = timezone(timedelta(hours=8))
UA = "Mozilla/5.0 (compatible; VibeScan/4.3; +daily-digest)"
MAX_BYTES = 3_000_000
SUMMARY_CHARS = 280


# ---------- 基本工具 ----------

def iri_to_uri(url):
    """把網址中的非 ASCII 字元（例如 Qiita 日文標籤）做百分比編碼。"""
    return re.sub(r"[^\x00-\x7f]", lambda m: quote(m.group(0)), url)


def clean_text(s, limit=SUMMARY_CHARS):
    if not s:
        return ""
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:limit]


def parse_date(value):
    """回傳 (datetime|None, precision)。precision: datetime / date / none。"""
    if value is None or value == "":
        return None, "none"
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, timezone.utc), "datetime"
    s = str(value).strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        d = datetime.fromisoformat(s).replace(tzinfo=TPE)
        return d, "date"
    try:
        dt = parsedate_to_datetime(s)
        if dt is not None:
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt, "datetime"
    except (TypeError, ValueError, IndexError):
        pass
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            return dt.replace(tzinfo=TPE), "date"
        return dt, "datetime"
    except ValueError:
        return None, "none"


def normalize_url(url):
    try:
        p = urlsplit(url.strip())
    except ValueError:
        return url
    query = [(k, v) for k, v in parse_qsl(p.query) if not k.lower().startswith("utm_")]
    path = p.path.rstrip("/") or "/"
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), path, urlencode(query), ""))


def local(tag):
    return tag.rsplit("}", 1)[-1] if isinstance(tag, str) else ""


def child_text(el, *names):
    for c in el:
        if local(c.tag) in names and (c.text or "").strip():
            return c.text.strip()
    return ""


# ---------- 各類來源解析 ----------

def parse_xml_feed(body):
    root = ET.fromstring(body)
    items = []
    for el in root.iter():
        name = local(el.tag)
        if name == "item":  # RSS 2.0 / RSS 1.0
            items.append({
                "title": child_text(el, "title"),
                "url": child_text(el, "link") or child_text(el, "guid"),
                "published": child_text(el, "pubDate", "date", "published", "updated"),
                "author": child_text(el, "creator", "author"),
                "summary": child_text(el, "description", "encoded"),
            })
        elif name == "entry":  # Atom
            link = ""
            for c in el:
                if local(c.tag) == "link" and c.get("rel", "alternate") == "alternate":
                    link = c.get("href", "")
                    break
            author = ""
            for c in el:
                if local(c.tag) == "author":
                    author = child_text(c, "name")
            items.append({
                "title": child_text(el, "title"),
                "url": link,
                "published": child_text(el, "published", "updated"),
                "author": author,
                "summary": child_text(el, "summary", "content"),
            })
    return items


def parse_hn_algolia(data, base):
    out = []
    for h in data.get("hits", []):
        hn_url = f"https://news.ycombinator.com/item?id={h.get('objectID')}"
        out.append({
            "title": h.get("title") or h.get("story_title") or "",
            "url": h.get("url") or h.get("story_url") or hn_url,
            "discussion_url": hn_url,
            "published": h.get("created_at_i") or h.get("created_at"),
            "author": h.get("author", ""),
            "summary": h.get("story_text") or "",
            "points": h.get("points"),
        })
    return out


def parse_qiita_api(data, base):
    return [{
        "title": it.get("title", ""),
        "url": it.get("url", ""),
        "published": it.get("created_at"),
        "author": (it.get("user") or {}).get("id", ""),
        "summary": (it.get("body") or "")[:1200],
        "tags": [t.get("name") for t in it.get("tags", [])],
    } for it in data]


def parse_devto_api(data, base):
    return [{
        "title": it.get("title", ""),
        "url": it.get("url", ""),
        "published": it.get("published_at") or it.get("published_timestamp"),
        "author": (it.get("user") or {}).get("name", ""),
        "summary": it.get("description", ""),
        "tags": it.get("tag_list", []),
    } for it in data]


def parse_discourse(data, base):
    topics = (data.get("topic_list") or {}).get("topics", [])
    return [{
        "title": t.get("title", ""),
        "url": f"{base}/t/{t.get('slug')}/{t.get('id')}",
        "published": t.get("created_at"),
        "author": "",
        "summary": t.get("excerpt", ""),
    } for t in topics]


def parse_github_repos(data, base):
    return [{
        "title": f"{it.get('full_name')}: {it.get('description') or ''}",
        "url": it.get("html_url", ""),
        "published": it.get("pushed_at") or it.get("created_at"),
        "author": (it.get("owner") or {}).get("login", ""),
        "summary": it.get("description") or "",
        "date_kind": "repo_pushed_at（僅供篩選，正式卡需指向具體 commit／PR／案例）",
    } for it in data.get("items", [])]


JSON_PARSERS = {
    "hn_algolia": parse_hn_algolia,
    "qiita_api": parse_qiita_api,
    "devto_api": parse_devto_api,
    "discourse": parse_discourse,
    "github_repos": parse_github_repos,
}


# ---------- 抓取 ----------

def fill_placeholders(url, since, dom_since):
    """{since_*} 用 01–12 類窗口，{domain_since_*} 用 13 類場域窗口；日期多退一天以免時區差漏抓。"""
    return (url.replace("{since_epoch}", str(int(since.timestamp())))
               .replace("{since_date}", (since - timedelta(days=1)).strftime("%Y-%m-%d"))
               .replace("{domain_since_epoch}", str(int(dom_since.timestamp())))
               .replace("{domain_since_date}", (dom_since - timedelta(days=1)).strftime("%Y-%m-%d")))


def fetch_source(src, since, dom_since, timeout):
    url = iri_to_uri(fill_placeholders(src["url"], since, dom_since))
    result = {"id": src["id"], "url": url, "kind": src["kind"], "status": "ok",
              "http_code": None, "items_total": 0, "error": "", "items": []}
    try:
        req = Request(url, headers={"User-Agent": UA,
                                    "Accept": "application/json, application/xml, text/xml, */*"})
        with urlopen(req, timeout=timeout) as r:
            result["http_code"] = getattr(r, "status", None) or r.getcode() or 200
            body = r.read(MAX_BYTES)
    except Exception as e:  # noqa: BLE001 — 任何失敗都只記錄，不中斷整批
        code = getattr(e, "code", None)
        result["status"] = f"http_{code}" if code else "fetch_error"
        result["http_code"] = code
        result["error"] = f"{type(e).__name__}: {str(e)[:160]}"
        return result

    head = body[:600].lstrip().lower()
    try:
        if src["kind"] in ("rss", "atom"):
            if head.startswith(b"<!doctype html") or head.startswith(b"<html"):
                result["status"] = "html_shell"
                result["error"] = "回傳 HTML 頁面而非 feed（可能只是外殼或被導向）"
                return result
            items = parse_xml_feed(body)
        else:
            data = json.loads(body.decode("utf-8", "replace"))
            parts = urlsplit(url)
            items = JSON_PARSERS[src["kind"]](data, f"{parts.scheme}://{parts.netloc}")
    except (ET.ParseError, json.JSONDecodeError, KeyError, AttributeError, TypeError) as e:
        result["status"] = "parse_error"
        result["error"] = f"{type(e).__name__}: {str(e)[:160]}"
        return result

    result["items_total"] = len(items)
    result["items"] = items
    if not items:
        result["status"] = "empty"
    return result


# ---------- 打分與分類線索 ----------

def compile_words(words):
    """英數關鍵字用字邊界比對（避免 retrieval 命中 eval），日文等非 ASCII 用子字串比對。"""
    out = []
    for w in words:
        w = w.lower().strip()
        if w.isascii():
            out.append((w, re.compile(r"(?<![a-z0-9])" + re.escape(w) + r"(?![a-z0-9])")))
        else:
            out.append((w, None))
    return out


def compile_keywords(mapping):
    return {k: compile_words(words) for k, words in mapping.items()}


def hits(text, words):
    return [w for w, rx in words if (rx.search(text) if rx else w in text)]


def score_item(item, cfg, cat_kw, dom_kw, reference):
    text = f"{item['title']} {clean_text(item.get('summary'), 1200)} {' '.join(item.get('tags') or [])}".lower()
    title = item["title"].lower()
    pos = hits(text, cfg["signals"]["positive"])
    neg = hits(title, cfg["signals"]["negative"])
    cats = [c for c, words in cat_kw.items() if hits(text, words)]
    doms = [d for d, words in dom_kw.items() if hits(text, words)]
    score = min(len(pos), 3) * 2 - len(neg) * 3
    score += 1 if cats else 0
    score += 1 if doms else 0
    if item.get("_dt") and reference - item["_dt"] < timedelta(hours=48):
        score += 1
    if item.get("points") and item["points"] >= 20:
        score += 1
    return score, pos, neg, cats, doms


# ---------- 主流程 ----------

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sources", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--hours", type=float, default=168, help="01–12 類時間窗（預設 168h）")
    ap.add_argument("--domain-hours", type=float, default=720, help="13 類業務場域時間窗（預設 720h）")
    ap.add_argument("--reference", help="參考時間 ISO 8601（預設現在，+08:00）")
    ap.add_argument("--only-cats", help="只掃描涵蓋這些類別的來源，例如 03,09,10")
    ap.add_argument("--skip", help="略過的來源 id，逗號分隔（例如前兩輪受阻的來源）")
    ap.add_argument("--top", type=int, default=40, help="stdout 顯示的候選數")
    ap.add_argument("--timeout", type=float, default=20)
    args = ap.parse_args(argv)

    with open(args.sources, encoding="utf-8") as f:
        cfg = json.load(f)
    cfg["signals"] = compile_keywords(cfg["signals"])
    cat_kw = compile_keywords(cfg["category_keywords"])
    dom_kw = compile_keywords(cfg["domain_keywords"])

    reference = (datetime.fromisoformat(args.reference.replace("Z", "+00:00"))
                 if args.reference else datetime.now(TPE)).astimezone(TPE)
    main_since = reference - timedelta(hours=args.hours)
    dom_since = reference - timedelta(hours=max(args.hours, args.domain_hours))

    only = set(args.only_cats.split(",")) if args.only_cats else None
    skip = set(args.skip.split(",")) if args.skip else set()
    sources = [s for s in cfg["sources"]
               if s.get("enabled", True) and s["id"] not in skip
               and (only is None or only & set(s.get("cats", [])))]

    with ThreadPoolExecutor(max_workers=8) as ex:
        results = list(ex.map(lambda s: fetch_source(s, main_since, dom_since, args.timeout), sources))

    by_url = {}
    source_report = []
    for src, res in zip(sources, results):
        in_main = in_dom = undated = 0
        dates = []
        for it in res.pop("items"):
            if not it.get("title") or not it.get("url"):
                continue
            dt, precision = parse_date(it.get("published"))
            if dt is None:
                undated += 1
                continue
            dt = dt.astimezone(TPE)
            dates.append(dt)
            # 只有日期精度時用當日結束時間比較下界，避免把窗內文章誤刪；定稿仍由排程依保守判準重篩。
            cmp_dt = dt + timedelta(days=1) if precision == "date" else dt
            if cmp_dt < dom_since or dt > reference + timedelta(hours=1):
                continue
            it["_dt"] = dt
            score, pos, neg, cats, doms = score_item(it, cfg, cat_kw, dom_kw, reference)
            main_window = cmp_dt >= main_since
            if not main_window and not doms:
                continue  # 超過 168h 只留給 13 類業務場域
            in_main += main_window
            in_dom += 1
            key = normalize_url(it["url"])
            cand = by_url.get(key)
            if cand:
                cand["found_in"].append(src["id"])
                cand["cat_hints"] = sorted(set(cand["cat_hints"]) | set(cats))
                continue
            by_url[key] = {
                "title": clean_text(it["title"], 200),
                "url": it["url"],
                "discussion_url": it.get("discussion_url", ""),
                "published": dt.isoformat(timespec="seconds"),
                "date_precision": precision,
                "date_kind": it.get("date_kind", "source_published"),
                "in_main_window": main_window,
                "lang": src.get("lang", ""),
                "author": clean_text(it.get("author"), 80),
                "summary": clean_text(it.get("summary")),
                "score": score,
                "positive_signals": pos,
                "negative_signals": neg,
                "cat_hints": cats or [c for c in src.get("cats", []) if c != "13"],
                "domain_hints": doms,
                "found_in": [src["id"]],
            }
        source_report.append({
            **res,
            "lang": src.get("lang", ""),
            "cats": src.get("cats", []),
            "items_in_main_window": in_main,
            "items_in_domain_window": in_dom,
            "undated_items": undated,
            "date_min": min(dates).isoformat(timespec="seconds") if dates else "",
            "date_max": max(dates).isoformat(timespec="seconds") if dates else "",
            "pages_read": 1,
        })

    candidates = sorted(by_url.values(), key=lambda c: (c["score"], c["published"]), reverse=True)

    out = {
        "scanner": "scan_feeds_v43",
        "generated_at": datetime.now(TPE).isoformat(timespec="seconds"),
        "reference_time": reference.isoformat(timespec="seconds"),
        "main_window": {"since": main_since.isoformat(timespec="seconds"), "hours": args.hours},
        "domain_window": {"since": dom_since.isoformat(timespec="seconds"), "hours": args.domain_hours},
        "note": "只做發現與日期初篩；分數與類別只是排序線索，正式收錄前必須開原文核對日期、方法與成果。",
        "sources": source_report,
        "candidates": candidates,
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    # 精簡摘要：讓排程只讀這段，不必把整份 JSON 放進對話
    ok = [s for s in source_report if s["status"] == "ok"]
    print(f"reference_time={out['reference_time']}  main_since={out['main_window']['since']}  "
          f"domain_since={out['domain_window']['since']}")
    print(f"sources: {len(ok)}/{len(source_report)} ok")
    for s in source_report:
        print(f"  [{s['status']:<11}] {s['id']:<26} total={s['items_total']:<4} "
              f"main={s['items_in_main_window']:<3} dom={s['items_in_domain_window']:<3} "
              f"range={s['date_min'][:10]}~{s['date_max'][:10]} {s['error'][:60]}")
    counts = {}
    for c in candidates:
        if c["in_main_window"] and c["score"] > 0:
            for h in c["cat_hints"]:
                counts[h] = counts.get(h, 0) + 1
    print("candidates(score>0, 168h) by category hint: "
          + ", ".join(f"{k}={counts[k]}" for k in sorted(counts)))
    dom_counts = {}
    for c in candidates:
        for d in c["domain_hints"]:
            dom_counts[d] = dom_counts.get(d, 0) + 1
    print("candidates by domain hint (720h): "
          + (", ".join(f"{k}={dom_counts[k]}" for k in sorted(dom_counts, key=int)) or "none"))
    print(f"top {args.top}:")
    for c in candidates[: args.top]:
        print(f"  {c['score']:>2} {c['published'][:16]} {c['lang']:<2} cat={','.join(c['cat_hints']) or '-':<8} "
              f"dom={','.join(c['domain_hints']) or '-':<5} {c['title'][:70]} | {c['url']}")
    print(f"full output: {args.out}  (candidates={len(candidates)})")
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
