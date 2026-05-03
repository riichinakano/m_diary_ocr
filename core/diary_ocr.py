#!/usr/bin/env python3
"""受付日誌PNG画像をGemini APIでOCRしてMarkdownに変換する"""

import argparse
import os
import re
import time
from pathlib import Path

import google.generativeai as genai
from dotenv import load_dotenv
from PIL import Image

GEMINI_MODEL = "gemini-2.5-flash"

PROMPT_MD_TEMPLATE = """\
あなたは日本語手書き文書の読み取り専門家です。
この画像は美術館の受付日誌1ページです。
画像の内容を以下のMarkdown形式で正確に出力してください。
**Markdownのみを出力**し、説明文・コードブロック（```）は不要です。

【展覧会名】{exhibition}

【出力フォーマット】

## YYYY-MM-DD (曜) 天気

スタッフ: 氏名1、氏名2

【AM】午前の連絡事項テキスト
【PM】午後の連絡事項テキスト

### 入館者
| コード | 分類 | 割引 | 人数 |
|--------|------|------|------|
| A：一般 | 一般 | HP | 5 |

合計: 8人　累計(有料): 100人　累計(全体): 102人

### 物販
| コード | 品名 | 販売数 |
|--------|------|--------|
| P：絵葉書 | 絵葉書（@100円） | 3 |

【スタッフマスター（最も近い名前を選ぶ）】
館長, 副館長, 吉田, 御堂, 中垣, 文, 向井

【入館者コード】
A：一般 / B：シニア / C：学生 / D：小中学生 / E：身障者 / F：招待券

【ルール】
- 日付はISO 8601形式（YYYY-MM-DD）で出力する
- 連絡事項がない場合は【AM】【PM】行を省略する
- 人数・販売数が0のエントリは省略する
- 割引がない場合は割引列に「-」を記入する
- 物販がない場合は「### 物販」セクションを省略する
- 数値が読み取れない場合は「?」と記載する
- Markdownのみを出力すること（前置き・後書き不要）
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="受付日誌PNG画像をOCRしてMarkdownに変換")
    parser.add_argument("--dir", required=True, help="画像ディレクトリパス")
    parser.add_argument("--exhibition", required=True, help="展覧会名（例: 8_春季展_前期）")
    parser.add_argument("--output", help="出力先ディレクトリ（デフォルト: --dir と同じ）")
    parser.add_argument("--overwrite", action="store_true", help="既存MDファイルを上書きする")
    return parser.parse_args()


def collect_images(dir_path: str) -> list[Path]:
    """ディレクトリ内のPNGを _NN 番号順でソートして返す"""
    pattern = re.compile(r"_(\d+)\.png$", re.IGNORECASE)
    images = []
    for p in Path(dir_path).iterdir():
        if p.suffix.lower() != ".png":
            continue
        m = pattern.search(p.name)
        if m:
            images.append((int(m.group(1)), p))
        else:
            print(f"[WARN] 命名規則外スキップ: {p.name}")
    images.sort(key=lambda x: x[0])
    return [p for _, p in images]


def extract_year_month(image_path: Path) -> str:
    """ファイル名 '2026年4月日誌_01.png' から '202604' を抽出する"""
    m = re.search(r"(\d{4})年(\d{1,2})月", image_path.name)
    if m:
        return f"{m.group(1)}{int(m.group(2)):02d}"
    from datetime import datetime
    return datetime.now().strftime("%Y%m")


def ocr_image(image_path: Path, exhibition: str, model, retries: int = 2) -> str | None:
    """Gemini APIでPNG画像をOCRしてMarkdownテキストを返す。失敗時はNone。"""
    prompt = PROMPT_MD_TEMPLATE.format(exhibition=exhibition)
    img = Image.open(image_path)

    for attempt in range(retries + 1):
        try:
            response = model.generate_content([img, prompt])
            return response.text.strip()
        except Exception as e:
            if attempt == retries:
                print(f"[ERROR] {image_path.name}: API失敗 ({e})")
                return None
            wait = 2 ** attempt
            print(f"[RETRY] {image_path.name}: {attempt + 1}回目失敗、{wait}秒後リトライ")
            time.sleep(wait)

    return None


def run(
    dir_path: str,
    exhibition: str,
    output_dir: str | None = None,
    overwrite: bool = False,
) -> Path | None:
    """GUIやスクリプトから直接呼び出せるエントリポイント。出力MDパスを返す。"""
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError(".env に GOOGLE_API_KEY が設定されていません")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(GEMINI_MODEL)

    images = collect_images(dir_path)
    if not images:
        print("[ERROR] PNG画像が見つかりません")
        return None

    out = Path(output_dir or dir_path)
    out.mkdir(parents=True, exist_ok=True)

    year_month = extract_year_month(images[0])
    md_path = out / f"{year_month}note.md"

    # 既存MDから処理済み画像ファイル名を収集
    processed: set[str] = set()
    existing_content = ""
    if md_path.exists() and not overwrite:
        existing_content = md_path.read_text(encoding="utf-8")
        for m in re.finditer(r"<!-- src: (.+?) -->", existing_content):
            processed.add(m.group(1))
        print(f"[INFO] 既存MD読込: 処理済み {len(processed)}ページ")

    # ヘッダー（新規 or 上書き時のみ）
    if overwrite or not md_path.exists():
        header = (
            f"# {year_month[:4]}年{int(year_month[4:]):d}月 受付日誌\n"
            f"展覧会: {exhibition}\n\n---\n\n"
        )
        sections = [header]
    else:
        sections = [existing_content] if existing_content else []

    new_count = 0
    for img in images:
        if img.name in processed and not overwrite:
            print(f"[SKIP] {img.name}: 処理済み")
            continue

        print(f"[OCR] {img.name} ...", end=" ", flush=True)
        md_text = ocr_image(img, exhibition, model)
        if md_text is None:
            print("スキップ")
            continue

        # コードブロックが含まれている場合は除去
        md_text = re.sub(r"^```(?:markdown)?\s*", "", md_text, flags=re.MULTILINE)
        md_text = re.sub(r"\s*```$", "", md_text, flags=re.MULTILINE)
        md_text = md_text.strip()

        date_match = re.search(r"^## (\d{4}-\d{2}-\d{2})", md_text, re.MULTILINE)
        date_str = date_match.group(1) if date_match else "日付不明"

        section = f"{md_text}\n\n<!-- src: {img.name} -->\n\n---\n\n"
        sections.append(section)
        new_count += 1
        print(f"→ {date_str} OK")

    if new_count > 0 or overwrite:
        md_path.write_text("".join(sections), encoding="utf-8")
        print(f"[SAVED] {md_path}  ({new_count}ページ追記)")
    else:
        print("[INFO] 新規追記なし")

    return md_path


def main() -> None:
    load_dotenv()
    args = parse_args()
    run(args.dir, args.exhibition, args.output, args.overwrite)


if __name__ == "__main__":
    main()
