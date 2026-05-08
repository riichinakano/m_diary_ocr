# 受付日誌 入力システム v2.2

美術館受付日誌の入力・集計・OCR処理を行う Streamlit Webアプリ。

## 起動方法

```bash
streamlit run app.py
```

## ディレクトリ構成

```
app.py                      # Streamlitエントリ（st.navigation）
pages/
  1_📝_入力.py              # 入館者・物販入力、重複確認、合計表示
  2_📋_履歴.py              # 月次集計・履歴閲覧・削除・CSVダウンロード
  3_⚙️_設定.py              # 展覧会/入館者分類/物販/割引リスト編集
core/
  csv_store.py              # visits/sales CRUD（アトミック書き込み）
  master_loader.py          # config/master.json 読み書き
config/
  master.json               # マスターデータ（展覧会・入館者分類・割引・物販・スタッフ）
data/
  visits.csv                # 入館者CSV
  sales.csv                 # 物販CSV
  ocr_notes/                # Tkinter OCR の出力先（Markdown）
ocr/
  diary_ocr_gui.py          # Tkinter + Gemini OCR GUI（日誌手書き読み取り）
docs/                       # 要件定義書・参考資料
archive/                    # 旧コード
```

## 画面構成

### 📝 入力
- 日付・展覧会名を選択
- 入館者分類・割引種別・人数を追加してリスト化
- 物販（図録・絵葉書等）を追加してリスト化
- 入館者合計人数・入館料売上、物販点数・物販売上をリアルタイム表示
- 「保存」でCSVに書き込み。重複行は上書き確認UI

### 📋 履歴
- 月単位で入館者・物販の一覧を表示
- 月次集計（有料入場者、入場者合計、入館料売上、絵葉書/図録販売数、物販売上、合計売上）
- 日付昇順/降順の切替
- 行ごとに金額を表示
- 行削除ボタン
- 当月・全期間CSVダウンロード

### ⚙️ 設定
- 展覧会リスト（追加・編集・削除）
- 入館者分類リスト（コード・分類名・料金の追加・編集・削除）
- 物販リスト（コード・品名・単価の追加・編集・削除）
- 割引種別リスト（追加・編集・削除）

## データ仕様

### visits.csv

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

### sales.csv

| カラム | 内容 |
|--------|------|
| date | YYYY-MM-DD |
| exhibition | 展覧会名 |
| code | 物販コード（P：絵葉書 など）|
| name | 商品名 |
| count | 販売数 |
| created_at / updated_at | ISO8601 タイムスタンプ |

一意キー：`(date, code, name)`

## config/master.json 構造

```json
{
  "exhibitions": ["1_春季展_前期", ...],
  "visitor_categories": [
    { "code": "A：一般", "category": "一般", "price": 600 }, ...
  ],
  "discounts": ["HP", "優待割引", ...],
  "merchandise": [
    { "code": "Q：図録", "name": "作品選", "price": 2000 }, ...
  ],
  "staff": ["館長", ...]
}
```

## OCR（Tkinter）

```bash
python ocr/diary_ocr_gui.py
```

Gemini 2.5 Flash を使用。日誌画像を読み込み Markdown で `data/ocr_notes/` に出力。  
`.env` に `GEMINI_API_KEY=...` が必要。

## 依存パッケージ

```
streamlit>=1.36.0
pandas>=2.0.0
google-generativeai
python-dotenv
pillow
```

## 今後の予定（Phase 2〜）

- Phase 2: 天気・スタッフ・備考入力（daily_meta.csv）
- Phase 3: OCR プロンプト簡素化（全文 Markdown 化）
- Phase 4: 過去データ CSV 移行
