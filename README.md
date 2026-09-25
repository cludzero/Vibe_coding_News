# 每日 Vibe Coding 情報：v4.2 → v4.3 修改說明

## 1. 問題診斷（依 2026-09-23、09-24 兩份報告）

| 現象 | 數據 | 原因 |
|---|---|---|
| 滿 5 則的類別很少 | 兩天都只有 1/13（08 類） | 預算平均分給 13 類，已滿的 08 類仍持續搜尋；缺額類別沒拿到額外預算 |
| 三個類別兩天都是 0 則 | 03 ChatGPT 辦公、09 圖像、10 NotebookLM | ① 分類綁死單一工具（09-24 的 Gemini Excel 案例因「不是 ChatGPT」被排除）；② 這三類原本靠 Reddit 補，但 Reddit 兩天都被 web_fetch 封鎖；③ Qiita NotebookLM 標籤最新文停在 09-07，開發者社群的熱度已經降低 |
| 來源太集中在日文 | 兩天 19 則 NEW 中有 15 則（79%）來自 Qiita／Zenn，英文只有 Show HN／GitHub 零星幾則 | 提示詞列出的英文入口只有 HN、DEV（兩個 tag）和 Reddit；DEV 幾乎沒用到，Reddit 被擋 |
| 查詢浪費在中文 | 每類都有一組中文種子 | 與「外國文章為主」的需求衝突，中文查詢又常回傳通用教學 |
| 業務場域兩天都沒命中 | 優先場域 6/7/8、9/10/11 都沒有新案例 | 場域案例很少出現在 Claude Code 的 feed；而且 168h 對特定場域來說太短，13 類只好用開發流程自動化補位 |
| 翻譯漏掉日文漢字 | 「仕様照合」「拒否」「掲載版」「未試行」「實行錯誤」直接出現在摘要 | 提示詞沒有翻譯規範 |

## 2. v4.3 修改重點

| 項目 | v4.2 | v4.3 |
|---|---|---|
| 語言 | 中、英、日交錯 | **英文優先，日文其次**，不查中文；輸出統一為台灣繁中，並附日→繁、簡→繁對照表；原文標題寫進 evidence note |
| 03 類 | ChatGPT 辦公研究資料 | **AI 辦公與研究交付物（不限工具）**：ChatGPT、Claude、Gemini、Copilot、Excel／Sheets 內建 AI、Deep Research |
| 04 類 | Codex 開發測試部署 | **Codex 與其他 Coding Agent**：加入 Cursor、Copilot agent、Gemini CLI、Jules、Cline、OpenCode、Aider 等 |
| 09 類 | 圖像圖文視覺 | **視覺與多媒體生成**：加入影片、配音、ComfyUI workflow |
| 10 類 | NotebookLM／Gemini Notebook | **NotebookLM 與 AI 研讀學習**：NotebookLM 仍優先，另收 Deep Research、學習模式、Obsidian＋AI、個人知識庫 |
| 11／12 類 | MCP／瀏覽器；Skills／Plugins | 11 加入電腦操作 Agent；12 加入 hooks、slash commands、GPTs／Gems |
| 13 類 | 真實任務自動化，最多 5 則，每天輪 3 個優先場域 | **業務場域實作：12 場域各 1 則，最多 12 則**；場域窗口 30 天；空場域優先，每天輪 4 個；12 場域的範圍放寬（例如財報加入發票、醫療加入健康資料）；種子改成英文＋日文 |
| 來源 | 約 10 個入口 | **76 個啟用入口（英文 55、日文 21）**：HN Algolia 主題查詢、DEV 16 個 tag、Medium 7 個 tag、Cursor 論壇、n8n「Built with n8n」、Streamlit、Lobsters、Simon Willison 等個人部落格、XDA／MakeUseOf／How-To Geek 第一人稱實測、GitHub topic、Zenn／Qiita 擴充 |
| 採集方式 | 逐個 web_fetch | **`scan_feeds_v43.py` 一次掃完**（日期初篩＋成果訊號打分＋類別與場域線索），只把前 40 名交給模型判斷；Python 不能連網時才改用 web_fetch 讀「核心 15 來源」 |
| 預算 | 13 類平均分 | 已滿 5 則的類別停止搜尋；來源連續兩輪受阻就略過，每三天重試一次；Reddit 預設停用 |
| 來源類型 | 未規範 | 媒體第一人稱實測可收；廠商示範要有實際輸入和輸出；SEO 清單文一律排除；Medium 付費牆文章列候選 |

## 3. 檔案

```
vibe_v4修復包/
  每日Vibe_Coding情報_v4.3_排程提示詞.md    ← 排程提示詞全文（取代 v4.2）
  Vibe情報_v4.3_近期來源與搜尋操作.md       ← 各類來源、查詢寫法、核心 15 來源、翻譯對照
  sources_v4.3.json                        ← 掃描器用的來源、成果訊號、類別與場域關鍵字
  scan_feeds_v43.py                        ← 批次掃描器（只用 Python 標準庫）
tests/                                     ← 掃描器離線測試（file:// fixtures）
```

## 4. 部署步驟

1. 把 `vibe_v4修復包/` 裡的 4 個檔案複製到 `D:\Claude Project\Vibe coding 情報\vibe_v4修復包\`（和 `render_vibe_v4.py` 放在同一層）。
2. 把排程任務的提示詞整段換成 `每日Vibe_Coding情報_v4.3_排程提示詞.md` 的內容。
3. 第一次執行會做 §2.1 的 renderer 相容性檢查：備份 `render_vibe_v4.py` 後，只修改類別名稱、13 類上限（12）和 13 類窗口（720h）。若修改失敗，就用舊名稱輸出，並在回報中註明。
4. 第一次執行後，打開 `scan_v43_YYYY-MM-DD.json` 的 `sources`，檢查每個來源的 status：
   - 除了 v4.2 已成功的 Qiita／Zenn／HN，其餘新來源都還沒在你的排程環境實測過。
   - 失敗的來源依 `fix_hint` 修正網址，或把 `enabled` 改成 false。

## 5. 驗證

```
python -m unittest discover -s tests
```

11 項測試涵蓋：RSS／Atom／HN／Qiita API／Discourse 解析、168h 與 720h 窗口、HTML 外殼偵測、URL 去重、字邊界比對（retrieval 不會誤中 eval）、正式來源設定檔的結構。

## 6. 仍需留意

- 這個雲端環境的網路擋掉了所有 feed 主機，所以新來源的網址是依各平台公開格式寫的，還沒實際連線驗證；Cursor 論壇和 Streamlit 的分類網址是用搜尋確認過的。
- 我手上沒有 `render_vibe_v4.py`。如果 §2.1 的自動升級失敗，把腳本傳給我，我可以直接修改並附上測試。
- 01–12 類仍維持 168h。如果 03、09、10 類在 v4.3 跑幾天後仍常常是 0，可以考慮把這三類的窗口也放寬到 14 天。
