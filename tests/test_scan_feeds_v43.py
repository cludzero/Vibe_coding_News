"""scan_feeds_v43.py 的離線測試：用 file:// fixtures，不需網路。

執行：python -m unittest discover -s tests
"""
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIX = Path(__file__).resolve().parent / "fixtures"
sys.path.insert(0, str(ROOT / "vibe_v4修復包"))

import scan_feeds_v43 as scan  # noqa: E402

REFERENCE = "2026-09-25T09:00:00+08:00"


def fixture_url(name):
    return FIX.joinpath(name).as_uri()


class ScanFeedsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        real = json.loads((ROOT / "vibe_v4修復包" / "sources_v4.3.json").read_text(encoding="utf-8"))
        cls.real_config = real
        cfg = {k: real[k] for k in ("signals", "category_keywords", "domain_keywords")}
        cfg["sources"] = [
            {"id": "zenn", "kind": "rss", "lang": "ja", "cats": ["02"], "url": fixture_url("zenn.rss")},
            {"id": "qiita", "kind": "atom", "lang": "ja", "cats": ["11"], "url": fixture_url("qiita.atom")},
            {"id": "hn", "kind": "hn_algolia", "lang": "en", "cats": ["05"], "url": fixture_url("hn.json")},
            {"id": "hn_dup", "kind": "hn_algolia", "lang": "en", "cats": ["05"], "url": fixture_url("hn_dup.json")},
            {"id": "n8n", "kind": "discourse", "lang": "en", "cats": ["13"], "url": fixture_url("discourse.json")},
            {"id": "qiita_api", "kind": "qiita_api", "lang": "ja", "cats": ["13"], "url": fixture_url("qiita_api.json")},
            {"id": "shell", "kind": "rss", "lang": "en", "cats": ["03"], "url": fixture_url("shell.html")},
            {"id": "missing", "kind": "rss", "lang": "en", "cats": ["03"], "url": fixture_url("nope.rss")},
            {"id": "off", "kind": "rss", "lang": "en", "cats": ["03"], "url": fixture_url("zenn.rss"), "enabled": False},
        ]
        cls.tmp = tempfile.TemporaryDirectory()
        src = Path(cls.tmp.name) / "sources.json"
        src.write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
        cls.out_path = Path(cls.tmp.name) / "scan.json"
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            cls.exit_code = scan.main(["--sources", str(src), "--out", str(cls.out_path),
                                       "--reference", REFERENCE])
        cls.stdout = buf.getvalue()
        cls.out = json.loads(cls.out_path.read_text(encoding="utf-8"))
        cls.by_url = {c["url"]: c for c in cls.out["candidates"]}
        cls.sources = {s["id"]: s for s in cls.out["sources"]}

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_exit_code_and_disabled_source(self):
        self.assertEqual(self.exit_code, 0)
        self.assertNotIn("off", self.sources)

    def test_source_status(self):
        self.assertEqual(self.sources["zenn"]["status"], "ok")
        self.assertEqual(self.sources["shell"]["status"], "html_shell")
        self.assertIn(self.sources["missing"]["status"], ("fetch_error", "http_404"))
        self.assertEqual(self.sources["qiita"]["undated_items"], 1)

    def test_main_window_and_domain_window(self):
        # 09-23 的請求書文章在 168h 內
        c = self.by_url["https://zenn.dev/a/articles/invoice?utm_source=rss"]
        self.assertTrue(c["in_main_window"])
        self.assertIn("1", c["domain_hints"])  # 経理／請求書 → 財報會計
        # 09-04 的在庫文章超過 168h，但有場域線索、在 720h 內 → 保留給 13 類
        old = self.by_url["https://zenn.dev/c/articles/old"]
        self.assertFalse(old["in_main_window"])
        self.assertIn("6", old["domain_hints"])
        # 08-03 超過 720h → 丟棄
        self.assertNotIn("https://zenn.dev/d/articles/tooold", self.by_url)
        # n8n 09-10 發票流程在場域窗口內；2024 的 about 文被丟棄
        self.assertTrue(any("invoice-workflow" in u for u in self.by_url))
        self.assertFalse(any(u.endswith("/about/1") for u in self.by_url))

    def test_scoring(self):
        good = self.by_url["https://github.com/u/resume-matcher/"]
        spam = self.by_url["https://spam.example.com/top10?utm_medium=x"]
        self.assertGreater(good["score"], spam["score"])
        self.assertIn("8", good["domain_hints"])
        self.assertTrue(spam["negative_signals"])
        intro = self.by_url["https://zenn.dev/b/articles/intro"]
        self.assertIn("まとめ", intro["negative_signals"])

    def test_word_boundary(self):
        # "retrieval" 不應命中 08 類的 "eval"
        mcp = self.by_url["https://qiita.com/x/items/1"]
        self.assertIn("11", mcp["cat_hints"])
        self.assertNotIn("08", mcp["cat_hints"])

    def test_dedupe_by_normalized_url(self):
        matches = [c for c in self.out["candidates"] if "resume-matcher" in c["url"]]
        self.assertEqual(len(matches), 1)
        self.assertEqual(sorted(matches[0]["found_in"]), ["hn", "hn_dup"])

    def test_hn_without_url_uses_discussion(self):
        self.assertIn("https://news.ycombinator.com/item?id=3", self.by_url)

    def test_stdout_summary(self):
        self.assertIn("sources:", self.stdout)
        self.assertIn("top 40:", self.stdout)

    def test_placeholders_and_iri(self):
        from datetime import datetime
        since = datetime.fromisoformat("2026-09-18T09:00:00+08:00")
        dom = datetime.fromisoformat("2026-08-26T09:00:00+08:00")
        url = scan.iri_to_uri(scan.fill_placeholders(
            "https://qiita.com/tags/画像生成/feed?a={since_date}&b={domain_since_epoch}", since, dom))
        self.assertIn("%E7%94%BB%E5%83%8F", url)
        self.assertIn("a=2026-09-17", url)
        self.assertIn(f"b={int(dom.timestamp())}", url)

    def test_parse_date(self):
        dt, p = scan.parse_date("Tue, 22 Sep 2026 09:46:20 GMT")
        self.assertEqual((dt.isoformat(), p), ("2026-09-22T09:46:20+00:00", "datetime"))
        dt, p = scan.parse_date("2026-09-20")
        self.assertEqual(p, "date")
        self.assertEqual(scan.parse_date("not a date"), (None, "none"))

    def test_real_config_is_valid(self):
        ids = [s["id"] for s in self.real_config["sources"]]
        self.assertEqual(len(ids), len(set(ids)), "來源 id 重複")
        for s in self.real_config["sources"]:
            self.assertIn(s["kind"], ("rss", "atom", *scan.JSON_PARSERS), s["id"])
            self.assertTrue(s["url"].startswith("https://"), s["id"])
        self.assertEqual(sorted(self.real_config["category_keywords"]), [f"{i:02d}" for i in range(1, 13)])
        self.assertEqual(sorted(self.real_config["domain_keywords"], key=int), [str(i) for i in range(12)])


if __name__ == "__main__":
    unittest.main()
