# 受付日誌 入力システム v2.2.1

美術館受付日誌の入力・集計・OCR処理を行う Streamlit Webアプリ。  
**スマートフォン対応。Google Sheets をデータストアとして Streamlit Community Cloud で稼働中。**

## 公開URL

https://mdiaryocr.streamlit.app/

---

## 起動方法

### ローカル開発（ローカルCSVを使用）

```powershell
$env:USE_LOCAL_CSV = "1"
streamlit run app.py
```

`data/visits.csv` / `data/sales.csv` が読み書き先になります（ファイルがなければ自動生成）。

### 本番環境相当（Google Sheets を使用）

`.streamlit/secrets.toml` に以下を設定して起動：

```toml
spreadsheet_url = "https://docs.google.com/spreadsheets/d/..."

[gcp_service_account]
type = "service_account"
project_id = "..."
# ... (サービスアカウントJSONの内容)
```

```bash
streamlit run app.py
```

---

## ディレクトリ構成

```
app.py                      # Streamlitエントリ（st.navigation）
pages/
  1_📝_入力.py              # 入館者・物販入力、バリデーション、重複確認
  2_📋_履歴.py              # 月次集計・履歴閲覧・削除・CSVダウンロード
  3_⚙️_設定.py              # マスターデータ編集（展覧会/分類/割引/物販）
core/
  csv_store.py              # デュアルモード：Google Sheets（本番）/ ローカルCSV（開発）
  master_loader.py          # config/master.json 読み書き
config/
  master.json               # マスターデータ（展覧会・入館者分類・割引・物販）
ocr/
  diary_ocr_gui.py          # Tkinter + Gemini OCR GUI（日誌手書き読み取り）
docs/                       # 要件定義書・実装記録
archive/                    # 旧コード
```

> `data/` および `.streamlit/secrets.toml` は `.gitignore` 対象（コミットされません）

---

## 画面構成

### 📝 入力
- 日付・展覧会名を選択
- 入館者分類・割引種別・人数を追加してリスト化
- 物販（図録・絵葉書等）を追加してリスト化
- 入館者合計人数・入館料売上、物販点数・物販売上をリアルタイム表示
- 保存時に重複チェック → 既存データは上書き確認UI
- **バリデーション**：「（割引）」「（特別優待）」を含む分類は割引種別の選択が必須

### 📋 履歴
- 月単位で入館者・物販の一覧をテーブル表示（スマホ横スクロール対応）
- 月次集計（有料入場者・入場者合計・入館料売上・物販コード別販売数・物販売上・合計）
- 物販集計はマスターデータに連動して自動生成（ハードコーディングなし）
- 日付昇順/降順の切替
- 行削除（Expander 内セレクトボックス）
- 当月・全期間 CSV ダウンロード

### ⚙️ 設定
- 展覧会リスト（追加・編集・削除）
- 入館者分類リスト（コード・分類名・料金の追加・編集・削除）
- 物販リスト（コード・品名・単価の追加・編集・削除）
- 割引種別リスト（追加・編集・削除）

---

## データ仕様

### Google Sheets（本番）

スプレッドシート内に `visits` / `sales` の2シートを使用。  
シート名はタブ名と完全一致が必要。日付フォーマットは `YYYY-MM-DD` 推奨（スラッシュ形式も自動正規化）。

### visits

| カラム | 内容 |
|--------|------|
| date | YYYY-MM-DD |
| exhibition | 展覧会名（master.json 参照）|
| code | 入館者コード（A：一般 など）|
| category | 分類名（一般、シニア など）|
| discount | 割引種別（なし時は空文字）|
| count | 人数 |
| created_at / updated_at | ISO8601 タイムスタンプ |

一意キー：`(date, code, category, discount)`

### sales

| カラム | 内容 |
|--------|------|
| date | YYYY-MM-DD |
| exhibition | 展覧会名 |
| code | 物販コード（P：絵葉書 など）|
| name | 商品名 |
| count | 販売数 |
| created_at / updated_at | ISO8601 タイムスタンプ |

一意キー：`(date, code, name)`

---

## config/master.json 構造

```json
{
  "exhibitions": ["1_春季展_前期", "..."],
  "visitor_categories": [
    { "code": "A：一般", "category": "一般", "price": 600 }
  ],
  "discounts": ["HP", "優待割引", "..."],
  "merchandise": [
    { "code": "Q：図録", "name": "作品選", "price": 2000 }
  ]
}
```

---

## OCR（Tkinter）

```bash
python ocr/diary_ocr_gui.py
```

Gemini 2.5 Flash を使用。日誌画像を読み込み Markdown で出力。  
`.env` に `GEMINI_API_KEY=...` が必要。

---

## 依存パッケージ

```
streamlit>=1.36.0
pandas>=2.0.0
gspread>=6.0.0
google-auth>=2.28.0
google-generativeai
python-dotenv
pillow
```

---

## クラウドデプロイ（Streamlit Community Cloud）

1. GitHub にプッシュ
2. [share.streamlit.io](https://share.streamlit.io) でリポジトリを選択してデプロイ
3. Settings → Secrets に `secrets.toml` の内容を貼り付け

コードをプッシュすると自動で再デプロイされます。

---

## 今後の予定

- Phase 3: OCR プロンプト簡素化（全文 Markdown 書き起こしへ変更）
- Phase 4: 過去データの一括 CSV インポート機能
