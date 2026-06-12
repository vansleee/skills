---
name: pytest-failure-triage
description: >
  Triage failed automation tests from a pytest report — JUnit XML, pytest console output,
  or pytest-html — typically produced by a Jenkins (or any CI) run: parse the failures,
  group them by owner, create or update the corresponding JIRA tickets (one per owner),
  then delegate root-cause analysis to the pytest-selenium-failure-analysis skill.
  Always use this skill when the user provides a pytest report path/URL or CI test output
  and wants tickets created, failures triaged, owners notified, or asks things like
  「幫我 triage 這份 report」、「根據 owner 開 JIRA ticket」、「分析這個 run 的失敗」、/triage-report.
---

# Pytest Failure Triage

Usage: `/triage-report <report_path_or_url>`

接受的輸入（擇一，優先序由上而下）:

1. **JUnit XML**（`--junitxml` 產物）— 結構最完整，優先使用。
2. **pytest console output**（CI console log 或本地輸出的文字檔）。
3. **pytest-html report**（`--html` 產物）。

輸入可以是本地路徑或 URL。URL 用 `curl -s` 下載到 `/tmp/triage/` 再解析 — 不要用 WebFetch 抓內網 HTTP server（會被強制升級 HTTPS 而失敗）。

## Configuration

讀取 skill 目錄下的 `config.yaml`（若存在），否則使用 `config.example.yaml` 的預設值。第一次執行若缺少必要設定，先向使用者確認再繼續：

```yaml
jira:
  base_url: "https://jira.example.com"
  project_key: "PROJ"
  issue_type: "Bug"
  auth: "env:JIRA_API_TOKEN"   # Bearer token from env var; never ask the user to paste it in chat
  labels: ["pytest-triage", "auto-created"]
ownership:
  # 測試路徑 pattern（glob）→ owner 名稱；越前面優先
  owner_map: {}
  # owner 名稱 → JIRA username / accountId（查不到時 ticket 留 unassigned 並在描述註明）
  jira_account_map: {}
  # owner_map 查不到時是否用 git blame 推測（取該測試檔案多數作者）
  fallback_git_blame: true
dedupe:
  jql_template: 'project = {project_key} AND labels = pytest-triage AND summary ~ "{test_file}" AND statusCategory != Done'
```

## What to do

### Step 1 — Collect the report

- 本地路徑直接讀；URL 用 `curl -s <url> -o /tmp/triage/report.<ext>`。
- 自動判斷格式：XML 以 `<testsuite` 開頭 → JUnit；HTML → pytest-html；其餘當 console output。
- 先 `head` 看實際結構再寫解析，不要假設欄位。

### Step 2 — Parse failures

寫一個小腳本到 `/tmp/triage/parse_report.py`，輸出 JSON 到 `/tmp/triage/failures.json`，後續步驟都吃這份 JSON。每筆 failure 至少取得：

| Field | Source |
|-------|--------|
| nodeid | `file::class::test` 完整路徑 |
| test_file | nodeid 的檔案部分（owner 對應與查重的 key） |
| outcome | failed / error / skipped（error 含 collection error）|
| error_type | exception class（如 `TimeoutException`、`AssertionError`）|
| message | 失敗訊息第一行 |
| traceback | 完整 traceback（餵給 RCA 用）|
| duration | 秒數（若有）|

統計欄（total / passed / failed / error / skipped）一併輸出。collection error（total 計不到的檔案）標 WARNING。

### Step 3 — Resolve owners

對每個 failed/error 的 test_file 決定 owner，依序：

1. `ownership.owner_map` 的 glob pattern 比對（第一個命中為準）。
2. 若 `fallback_git_blame: true` 且該檔案在 git repo 內：`git log --format=%an -- <file>` 取近一年 commit 數最多的作者。
3. 都查不到 → owner = `unassigned`，並在 ticket 與最終報告標註「⚠ owner mapping missing: <file>」。

### Step 4 — Root cause analysis（delegate）

對每筆 failure 呼叫 **`pytest-selenium-failure-analysis`** skill：餵入 nodeid、error_type、message、traceback（必要時附 screenshot / browser log 路徑），取回：

- 失敗分類（locator / wait-timing / assertion mismatch / test data / fixture isolation / environment / product regression / cascade / unknown）
- queue 分類（Autonomous / Needs owner / Ignored）
- likely root cause、confidence、建議的最小下一步

同一 error signature 的多筆 failure 可合併分析一次，避免重複工作。RCA 結果回填到 Step 5 的 ticket 描述。

### Step 5 — Create or update JIRA tickets

依 owner 分組，同一位 owner 的多個失敗收在**同一張** ticket（一個 owner 一張），避免洗版。

**先查重再建單。** 對每個 owner group：

1. 用 `dedupe.jql_template` 搜尋既有未關閉 ticket：
   ```
   curl -s -H "Authorization: Bearer $JIRA_API_TOKEN" \
     "<jira_base>/rest/api/2/search?jql=<urlencoded_jql>&fields=key,summary,status"
   ```
2. **找到既有 ticket → 更新**：add comment 附上本次 run 的失敗清單與 RCA（不要覆寫原描述）。留言前先檢查該 run 是否已留言過（冪等）。
3. **沒找到 → 建新單**：
   ```
   curl -s -X POST -H "Authorization: Bearer $JIRA_API_TOKEN" -H "Content-Type: application/json" \
     "<jira_base>/rest/api/2/issue" -d @/tmp/triage/issue_<owner>.json
   ```

Ticket 內容模板：

- **Summary**: `[Triage][<run_label>] <N> failed tests — <owner>`（run_label 取 CI build 名稱/編號，無則用日期）
- **Description**（JIRA wiki markup）：
  ```
  h3. Source
  * Report: <report path/URL>
  * Run: <CI run URL（若使用者有提供）>

  h3. Failed Tests
  || Test || Outcome || Error || Classification || Queue ||
  | <nodeid> | failed | <error_type>: <message> | <RCA 分類> | Autonomous/Needs owner |

  h3. RCA
  <pytest-selenium-failure-analysis 的 root cause、confidence、建議下一步>
  ```
- **Assignee**: `jira_account_map[<owner>]`（查無則略過 assignee 欄位）
- **Labels**: 套用 `jira.labels`

建單/留言**屬於對外副作用**：先把要建立的 ticket 清單（owner、summary、failed tests）列給使用者確認，得到同意後才呼叫 JIRA API。

### Step 6 — Final report

在對話中輸出 triage 總結（每張 ticket 印完整可點擊 URL，不准只寫 ticket key）：

| Owner | JIRA Ticket (full URL) | Action (created/updated) | Failed Tests | RCA Classification | Queue |
|-------|------------------------|--------------------------|---------------|--------------------|-------|

外加：

- ⚠ 無法 mapping 的 owner / 檔案
- ⚠ collection error 的檔案
- 同一 run 多筆 failure 出現相同 error signature（如同一個 timeout / 連線錯誤）→ 提醒可能是環境或 stack-wide event，建議合併成單一 infra ticket 而非分派給各 owner
- queue 為 **Autonomous** 的項目 → 提示可交給 `pytest-selenium-test-improvement` 修復（遵循 `agentic-sdet-governance` 的授權分層，未經授權不動手）

並把報告存檔：`<project-root>/triage-reports/<YYYY-MM-DD>_<run_label>_triage.md`（目錄不存在就建立）。

## Notes

- passed + failed + error + skipped 應等於 total；不相等時在報告標 WARNING。
- JIRA token 一律從環境變數讀；若未設定，提示使用者設定後重跑，不要在對話中要求貼上 token。
- 重跑同一份 report 必須是冪等的：查重邏輯保證不會重複開單，重複的 comment 也先檢查是否已存在。
- RCA 與修復分工：本 skill 只負責 triage 與開單；分析交給 `pytest-selenium-failure-analysis`，修復交給 `pytest-selenium-test-improvement`，全程受 `agentic-sdet-governance` 約束。
