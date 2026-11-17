# 投稿審查系統

使用 FastAPI、Jinja2、PostgreSQL 與 Adminer 的簡單投稿審查範例。Python 套件由 `uv` 管理。

## 需要安裝

- Python 3.12 以上與 [uv](https://docs.astral.sh/uv/)
- Docker Desktop（啟動後才能執行 Docker 指令）

## 啟動

在本專案資料夾開啟終端機：

```bash
# 1. 安裝 Python 套件
uv sync

# 2. 啟動 PostgreSQL 和 Adminer
# 第一次啟動會自動執行 schema.sql，建立資料表和示範帳號
docker compose up -d

# 3. 啟動 FastAPI
uv run fastapi dev main.py
```

如果資料庫尚未啟動完成，FastAPI 可能會連線失敗；稍等幾秒後重新執行第 3 步。

- 投稿審查系統：http://127.0.0.1:8000
- Adminer：http://127.0.0.1:8080

## 示範帳號

| 角色 | 帳號 | 密碼 |
| --- | --- | --- |
| 作者 | author | pass1234 |
| 編輯 | editor | pass1234 |

先以作者身分登入並新增稿件，按「送出審查」；登出後以編輯身分登入，即可查看、通過或退回稿件。

## Adminer 連線

在 Adminer 登入頁填入：

- 系統：PostgreSQL
- 伺服器：`db`
- 使用者：`postgres`
- 密碼：`postgres`
- 資料庫：`submissions`

`db` 是 Docker Compose 中 PostgreSQL 服務的名稱；FastAPI 執行在電腦上，因此預設使用 `localhost:5433`。

## 停止與資料

按 `Ctrl+C` 停止 FastAPI；在專案資料夾執行 `docker compose down` 可停止資料庫及 Adminer，資料仍保留在 Docker volume。`schema.sql` 只會在建立全新的資料庫時自動執行，修改該檔不會自動更新已有的資料庫。

## 自訂連線

預設連線為 `postgresql://postgres:postgres@localhost:5433/submissions`，可在啟動前設定 `DATABASE_URL` 環境變數來更改。`SESSION_SECRET` 可用於設定 session 簽章金鑰；示範帳號、密碼與預設金鑰僅供本機教學使用。

## 執行測試

```bash
uv run python -m unittest discover -s tests -v
```

測試以記憶體中的 SQLite 模擬資料庫，檢查網頁操作及權限；實際部署仍使用 PostgreSQL。
