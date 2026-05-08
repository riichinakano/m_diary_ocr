# 要件定義書：美術館受付日誌 OCR・集計自動化システム

**バージョン** 1.0　**作成日** 2026-05-03

---

## 1. プロジェクト概要

美術館の受付日誌（手書きPNG画像）を自動でOCR解析し、Gemini Flash APIを用いて構造化JSONに変換。既存のExcel集計表（R7_入館者・R7_物販シート）への自動追記まで一貫して処理するCLIシステムを構築する。

**実装環境：** Claude Code（ターミナル実行）／GitHub管理  
**OCR API：** Google Gemini Flash（既存Streamlitアプリと統一）

---

## 2. 業務フロー

```
[Step 1] 撮影・保存
  Scanner Pro (iOS) で受付日誌を撮影
  → OneDrive の月別フォルダに手動リネームしてPNG保存
  例: MuseumWork/01_MuseumOffice/dailynote/2026/202604/
       2026年4月日誌_01.png, _02.png, ...

[Step 2] OCR変換（スクリプト実行のみ）
  Claude Code ターミナルで実行：
  python diary_ocr.py --dir ./202604 --exhibition "8_春季展_前期"
  → diary_2026_04.json（構造化データ）
  → notes_2026_04.txt（連絡事項まとめ）

[Step 3] Excel自動追記（スクリプト実行のみ）
  python json_to_excel.py \
    --json ./202604/diary_2026_04.json \
    --excel ./R7_2025年度入館者一覧_2604new.xlsx
  → R7_入館者シート に行追記
  → R7_物販シート に行追記

[Step 4] 目視確認
  Excel上でOCR結果を確認・修正
```

---

## 3. 入力仕様

### 3-1. 画像ファイル

| 項目 | 仕様 |
|------|------|
| 形式 | PNG |
| 命名規則 | `YYYY年M月日誌_NN.png`（手動リネーム） |
| 保存先 | OneDrive 月別フォルダ（例: `202604/`） |
| 枚数 | 1ファイル = 1開館日（月20〜26枚程度） |
| 処理単位 | ディレクトリ内の全PNGを一括処理（月途中の部分実行も可） |

### 3-2. CLIオプション

| オプション | 説明 | 必須 |
|-----------|------|------|
| `--dir` | 画像ディレクトリパス | ○ |
| `--exhibition` | 展覧会名（例: `8_春季展_前期`） | ○ |
| `--output` | 出力先ディレクトリ（デフォルト: `--dir` と同じ） | – |

> **展覧会名の管理：** 月の途中で展覧会が切り替わる場合は、切り替え後に再実行（`--exhibition` を変更）し、JSONをマージして使用する。または設定ファイルで日付範囲マッピングを定義する方式も検討。

---

## 4. 出力仕様

### 4-1. diary_YYYY_MM.json

1日1オブジェクトの配列。月全体を1ファイルに格納。

```json
[
  {
    "date": "2026-04-01",
    "day_of_week": "水",
    "weather": "晴",
    "staff": ["副館長", "吉田", "御堂"],
    "exhibition": "8_春季展_前期",
    "notes": {
      "am": "鍵開き済。10:00 来客対応。...",
      "pm": "鍵閉なし。..."
    },
    "visitors": [
      {"code": "A：一般",   "category": "一般",         "discount": null, "count": 5},
      {"code": "B：シニア", "category": "シニア（割引）","discount": "HP", "count": 3},
      {"code": "F：招待券", "category": "招待券",        "discount": null, "count": 2}
    ],
    "visitors_total": 10,
    "cumulative_excluding_free": 13,
    "cumulative_including_free": 14,
    "sales": [
      {"code": "P：絵葉書", "name": "絵葉書（＠100円）", "count": 3},
      {"code": "Q：図録",   "name": "作品選",           "count": 1}
    ]
  }
]
```

**フィールド詳細：**

| フィールド | 説明 |
|-----------|------|
| `staff` | 出勤者リスト（館長・副館長・吉田・御堂・中垣・文・向井） |
| `visitors[].code` | 入館者コード（A〜F、既存Excelの分類に準拠） |
| `visitors[].discount` | 割引種別（HP・JAF等、記載なければ null） |
| `cumulative_excluding_free` | 累計（無料含まず） |
| `cumulative_including_free` | 累計（無料含む） |
| OCR失敗値 | 読み取れない場合は `null`（後で手動修正） |

### 4-2. notes_YYYY_MM.txt

```
=== 2026-04-01 (水) ===
【AM】鍵開き済。10:00 来客対応。...
【PM】鍵閉なし。...

=== 2026-04-02 (木) ===
...
```

---

## 5. Excelマッピング仕様

### 5-1. R7_入館者シート

JSON `visitors` 配列の各要素 → 1行追記

| Excelカラム | JSONソース | 補完方法 |
|------------|-----------|---------|
| 日付 | `date` | そのまま |
| 入館者コード | `visitors[].code` | そのまま |
| 入館者分類 | `visitors[].category` | そのまま |
| 割引リスト | `visitors[].discount` | そのまま（nullなら空白） |
| 入場者数 | `visitors[].count` | そのまま |
| 入館料単価 | — | `リスト`シートから自動参照 |
| 入館料合計 | — | 単価 × 人数で自動計算 |
| 展覧会名 | `exhibition` | そのまま |

### 5-2. R7_物販シート

JSON `sales` 配列の各要素 → 1行追記

| Excelカラム | JSONソース | 補完方法 |
|------------|-----------|---------|
| 日付 | `date` | そのまま |
| 図版コード | `sales[].code` | そのまま |
| 図録・絵葉書 | `sales[].name` | そのまま |
| 販売数 | `sales[].count` | そのまま |
| 物販単価 | — | `図録リスト`シートから自動参照 |
| 物販合計 | — | 単価 × 販売数で自動計算 |
| 展覧会名 | `exhibition` | そのまま |

---

## 6. 入館者コード マスター

Excelの「リスト」シートに準拠。

| コード | 主分類 | 備考 |
|-------|-------|------|
| A：一般 | 一般・一般（割引）・一般（特別優待） | 割引25種類 |
| B：シニア | シニア・シニア（割引）・シニア（特別優待） | |
| C：学生 | 学生・学生（割引）・学生（無料） | |
| D：小中学生 | 小中学生・小中学生（割引）・小中学生（無料） | |
| E：身障者 | 身障者 | |
| F：招待券 | 招待券 | 無料 |

---

## 7. エラーハンドリング

| ケース | 対応 |
|-------|------|
| OCR読み取り失敗（数値） | `null` で出力 → 手動修正 |
| OCR読み取り失敗（文字列） | `null` or 空文字 → 手動修正 |
| 不明な入館者コード | `"code": "UNKNOWN"` で保存・警告ログ出力 |
| 不明な図録名 | `"name"` に読み取り文字列をそのまま格納 |
| API呼び出し失敗 | リトライ2回後、エラーログ出力・スキップ |
| 処理済みファイルの重複実行 | 日付キーで重複チェック → 上書きか追記かを選択 |

---

## 8. 実装スコープ

### Phase 1（初期実装）

| ファイル | 役割 |
|---------|------|
| `diary_ocr.py` | PNG → JSON変換メインスクリプト |
| `json_to_excel.py` | JSON → Excel自動追記スクリプト |
| `.env` | APIキー管理（`GOOGLE_API_KEY`） |
| `requirements.txt` | 依存ライブラリ |
| `README.md` | 実行手順 |

### Phase 2（将来検討）

- 展覧会名の日付範囲設定ファイル（`exhibitions.json`）
- OCR精度の検証・Gemini Flash Lite比較テスト
- 処理ログの保存

---

## 9. 技術スタック

| 項目 | 採用技術 | 理由 |
|------|---------|------|
| 実行環境 | Python 3.10+ | 既存アプリと統一 |
| バージョン管理 | GitHub | 再現性・変更履歴 |
| OCR API | Gemini 2.5 Flash | 既存アプリと統一・コスト安定・自動化対応 |
| Excel操作 | openpyxl | 既存シートへの追記 |
| 設定管理 | python-dotenv | APIキーをコードから分離 |
| CLI | argparse（標準ライブラリ） | 追加依存なし |

---

## 10. ディレクトリ構成（想定）

```
diary-ocr/
├── diary_ocr.py          # メインOCRスクリプト
├── json_to_excel.py      # Excel追記スクリプト
├── requirements.txt
├── .env                  # GOOGLE_API_KEY=xxxx（.gitignore対象）
├── .gitignore
├── README.md
└── output/               # 出力JSON・TXT（.gitignore対象）
```

OneDrive側（月別フォルダ）への直接出力も可（`--output` オプションで指定）。
