# Vibe 情報 v4.3｜近期來源與搜尋操作

排程每輪只讀需要的段落。機器可讀版本在 `sources_v4.3.json`，由 `scan_feeds_v43.py` 批次掃描；這份文件給人和 web_fetch 備援時使用。

> 標「v4.2 已成功」的來源在 2026-09-23／24 的報告中確實讀到過。其餘來源是 v4.3 新增的，還沒在排程環境實測；第一次執行後，請以 scan 輸出的 status 為準，失敗的來源依 §4.3 的規則處理。

## A. 核心 15 來源（Python 不能連網時用 web_fetch 逐一讀）

| # | 來源 | 網址 | 主要類別 |
|---|---|---|---|
| 1 | HN Show HN（依日期） | `https://hn.algolia.com/api/v1/search_by_date?tags=show_hn&hitsPerPage=200&numericFilters=created_at_i>{168h前epoch}` | 05 01 11 12 13（v4.2 已成功） |
| 2 | HN 主題查詢（依缺額換關鍵字） | `https://hn.algolia.com/api/v1/search_by_date?tags=story&query=<關鍵字>&numericFilters=created_at_i>{epoch},points>=2` | 依關鍵字 |
| 3 | DEV #showdev | `https://dev.to/feed/tag/showdev` | 05 |
| 4 | DEV #claudecode | `https://dev.to/feed/tag/claudecode` | 02 12 |
| 5 | DEV #agents | `https://dev.to/feed/tag/agents` | 08 13 |
| 6 | Medium claude-code | `https://medium.com/feed/tag/claude-code` | 02 |
| 7 | HN Gemini Notebook（新名）＋ Medium notebooklm（舊名標籤） | `https://hn.algolia.com/api/v1/search_by_date?tags=story&query=Gemini%20Notebook&numericFilters=created_at_i>{epoch}`；`https://medium.com/feed/tag/notebooklm` | 10 |
| 8 | Simon Willison | `https://simonwillison.net/atom/everything/` | 01 02 06 09 11 12 |
| 9 | Cursor 論壇 Built with Cursor | `https://forum.cursor.com/c/showcase/built-with-cursor/18/l/latest.json` | 04 05 |
| 10 | n8n 社群 Built with n8n | `https://community.n8n.io/c/built-with-n8n/l/latest.json` | 13 |
| 11 | XDA Developers | `https://www.xda-developers.com/feed/` | 03 10 01 09 |
| 12 | Zenn claudecode | `https://zenn.dev/topics/claudecode/feed` | 02 08 12（v4.2 已成功） |
| 13 | Qiita ClaudeCode | `https://qiita.com/tags/claudecode/feed` | 02 12（v4.2 已成功） |
| 14 | Qiita 業務効率化 | `https://qiita.com/tags/業務効率化/feed` | 03 13（v4.2 已成功） |
| 15 | Zenn codex | `https://zenn.dev/topics/codex/feed` | 04 |

epoch 用 Python 算：`int((reference_time - timedelta(hours=168)).timestamp())`。

## B. 各類來源與 site: 查詢網域

| 類別 | 英文來源（優先） | 日文來源 | site: 補查網域 |
|---|---|---|---|
| 01 開源／本地 AI | HN `local LLM`、DEV #ollama #selfhosted、Simon Willison、Hugging Face Blog | Zenn／Qiita `ローカルLLM` | `simonwillison.net`、`dev.to`、`huggingface.co/blog`、`xda-developers.com` |
| 02 Claude Code | HN `Claude Code`、DEV #claudecode #claude、Medium claude-code、Simon Willison、Armin Ronacher、Harper Reed、Lobsters #ai | Zenn claudecode、Qiita ClaudeCode | `dev.to`、`medium.com`、`substack.com`、`github.com` |
| 03 AI 辦公交付物 | XDA、MakeUseOf、How-To Geek（第一人稱實測）、One Useful Thing、Medium chatgpt、DEV #chatgpt #automation | Zenn chatgpt／gemini、Qiita ChatGPT、業務効率化、`note.com` | `xda-developers.com`、`makeuseof.com`、`howtogeek.com`、`medium.com`、`substack.com`、`note.com` |
| 04 Codex 等 Coding Agent | HN `Codex`／`Cursor`、Cursor 論壇 Built with Cursor、DEV #codex #cursor、Addy Osmani | Zenn codex／cursor、Qiita codex | `forum.cursor.com`、`dev.to`、`medium.com`、`github.com` |
| 05 成品建置 | Show HN、DEV #showdev #vibecoding、Medium vibe-coding、Lobsters #vibecoding、Cursor 論壇、Streamlit Show the Community | Zenn 個人開発 | `indiehackers.com`、`dev.to`、`medium.com` |
| 06 提示詞／規格 | HN `vibe coding`、DEV #promptengineering、Simon Willison、Addy Osmani | Zenn／Qiita `プロンプト` `仕様駆動` | `dev.to`、`medium.com`、`substack.com` |
| 07 資料分析／教材 | Towards Data Science、Streamlit Show the Community、DEV #datascience | Zenn／Qiita `データ分析` | `towardsdatascience.com`、`discuss.streamlit.io`、`kaggle.com`、`medium.com` |
| 08 Agent 可靠性 | HN `agent`、DEV #agents、Medium ai-agents、Armin Ronacher、Lobsters #ai | Zenn aiagent、Qiita AIエージェント | `dev.to`、`medium.com`、`github.com` |
| 09 視覺與多媒體 | HN `image generation`、Medium comfyui、Hugging Face Blog、XDA／MakeUseOf、Simon Willison | Qiita 画像生成、Zenn、`note.com` | `civitai.com/articles`、`medium.com`、`dev.to`、`note.com` |
| 10 Gemini Notebook（原 NotebookLM）／研讀學習 | HN `Gemini Notebook`＋`NotebookLM`、XDA、MakeUseOf、How-To Geek、Medium gemini-notebook／notebooklm、One Useful Thing、DEV #gemininotebook／#notebooklm | Zenn gemininotebook／notebooklm／gemini、Qiita GeminiNotebook／NotebookLM、`note.com` | `xda-developers.com`、`makeuseof.com`、`medium.com`、`substack.com`、`note.com`（查詢寫 `"Gemini Notebook" OR NotebookLM`） |
| 11 MCP／瀏覽器 | HN `MCP`、DEV #mcp、Cursor 論壇 Built for Cursor、GitHub topic:mcp-server | Qiita MCP（v4.2 已成功）、Zenn mcp | `dev.to`、`github.com`、`medium.com` |
| 12 Skills／Plugins | GitHub topic:claude-skills、HN `Claude Code`、DEV #claudecode、Cursor 論壇 Built for Cursor | Zenn claudecode、Qiita ClaudeCode | `github.com`、`dev.to` |
| 13 業務場域 | n8n Built with n8n、Show HN（30 天）、DEV #n8n #automation #agents、Medium n8n ai-agents、Towards Data Science、GitHub topic:ai-agent | Qiita 業務効率化／n8n／AIエージェント、Zenn n8n／dify／aiagent、Qiita API | `community.n8n.io`、`dev.to`、`medium.com`、`github.com`、`zenn.dev`、`qiita.com` |

## C. 常用查詢寫法

**HN Algolia（英文發現主力）**
- Show HN（168h）：`https://hn.algolia.com/api/v1/search_by_date?tags=show_hn&hitsPerPage=200&numericFilters=created_at_i>{epoch}`
- 主題（168h）：`https://hn.algolia.com/api/v1/search_by_date?tags=story&query=Gemini%20Notebook&numericFilters=created_at_i>{epoch}`（舊名 `NotebookLM` 另查一次）
- 關鍵字要短（1–2 個詞）；多個詞之間是 AND。hit 沒有 `url` 時就是 HN 自己的文章，用 `https://news.ycombinator.com/item?id=<objectID>`。

**Qiita API（日文，可帶日期條件）**
- `https://qiita.com/api/v2/items?per_page=100&query=tag:生成AI+created:>=YYYY-MM-DD+自動化`
- 未登入每小時 60 次，只在補查時使用；平常讀 tag feed 就夠了。

**GitHub 搜尋（找 Skills／MCP／場域專案的線索）**
- `https://api.github.com/search/repositories?q=topic:claude-skills+pushed:>YYYY-MM-DD&sort=updated&order=desc`
- Repo 的日期只供篩選；正式卡要指向具體的 commit、PR、release 或案例文章。

**Discourse 論壇（Cursor／n8n／Streamlit）**
- 分類最新：`<分類網址>/l/latest.json`；RSS：`<分類網址>.rss`。
- 用 topic 的 `created_at` 判斷日期，不用 `bumped_at`。
- 分類網址 404 時，先讀 `<站台>/categories.json` 找正確的 slug 與 id。

**一般搜尋（缺額補查）**
- 格式：`site:<網域> <工具> <任務> <成果詞>`，例如 `site:xda-developers.com "Gemini Notebook" "I used"`、`site:community.n8n.io invoice workflow built`。
- 加上 `-"top 10" -"best prompts" -"ultimate guide"` 排除清單文。
- 日期用工具的篩選參數，不寫在查詢字串裡。

## D. 已知限制

- **Reddit**：v4.2 兩輪都在 web_fetch 封鎖清單上，`sources_v4.3.json` 預設停用；不繞過封鎖。
- **Medium**：會員限定文章常常只有前幾段；全文讀不到就列候選並標「付費牆」。
- **XDA／MakeUseOf／How-To Geek**：總 feed 量很大，大多是硬體或新聞；靠 scan 的關鍵字篩選，只打開第一人稱實測文。
- **NotebookLM 已改名 Gemini Notebook（2026-07-16）**：v4.2 只查舊名，這是 10 類一直 0 則的主因之一（Qiita NotebookLM 標籤最新文停在 09-07）。現在新、舊名稱都查；新名稱的 Zenn／Qiita／DEV／Medium 標籤網址是推測的，第一次執行請看 scan 的 status，404 就停用。改名說明文很多，已列為負面訊號，不會排到前面。
- **X／LinkedIn／YouTube／Discord**：只有在實際讀得到正文、日期與畫面時才使用。

## E. 翻譯對照（常見漏譯）

| 原文 | 台灣繁中 |
|---|---|
| 実行／実行エラー | 執行／執行錯誤 |
| 仕様／仕様照合 | 規格／規格比對 |
| 拒否 | 拒絕 |
| 掲載 | 刊載 |
| 削減 | 精簡、刪減 |
| 差し戻し | 退回 |
| 検証 | 驗證 |
| 運用 | 維運、使用 |
| 未試行 | 未嘗試 |
| 画面 | 畫面 |
| 情報 | 資訊 |
| 数据／代码／项目 | 資料／程式碼／專案 |
| 服务器／默认／支持 | 伺服器／預設／支援 |
| 视频／网络／软件／优化 | 影片／網路／軟體／最佳化 |
