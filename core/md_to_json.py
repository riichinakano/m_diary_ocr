#!/usr/bin/env python3
"""受付日誌MarkdownをGeminiで構造化JSONに変換する"""

import argparse
import json
import os
import re
from pathlib import Path

import google.generativeai as genai
from dotenv import load_dotenv

GEMINI_MODEL = "gemini-2.5-flash"

PROMPT_PARSE_TEMPLATE = """\
以下は美術館の受付日誌のMarkdownテキストです。
このMarkdownを解析し、**1日1オブジェクトのJSON配列**を出力してください。
**JSONのみを出力**し、説明文・コードブロック（```）は不要です。

【JSONスキーマ（1日分のオブジェクト）】
{{
  "date": "YYYY-MM-DD",
  "day_of_week": "月/火/水/木/金/土/日 のいずれか",
  "weather": "晴/曇/雨/雪など簡潔に",
  "staff": ["スタッフ名"],
  "exhibition": "展覧会名",
  "notes": {{
    "am": "午前の連絡事項テキスト（なければ null）",
    "pm": "午後の連絡事項テキスト（なければ null）"
  }},
  "visitors": [
    {{
      "code": "A：一般",
      "category": "一般（割引）",
      "discount": "HP",
      "count": 5
    }}
  ],
  "visitors_total": 10,
  "cumulative_excluding_free": 13,
  "cumulative_including_free": 14,
  "sales": [
    {{
      "code": "P：絵葉書",
      "name": "絵葉書（＠100円）",
      "count": 3
    }}
  ]
}}

【入館者カテゴリマスター（category は完全一致必須）】
一般, 一般（割引）, 一般（特別優待）,
シニア, シニア（割引）, シニア（特別優待）,
学生, 学生（割引）, 学生（特別優待）, 学生（無料）,
小中学生, 小中学生（割引）, 小中学生（無料）,
身障者, 招待券, その他

【ルール】
- discount は「HP」「JAF」など記載があれば設定、「-」やなければ null
- 数値が「?」の場合は null
- 物販がない場合は "sales": [] とする
- 日付順に並べること

【Markdownテキスト】
{content}
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="受付日誌MarkdownをJSONに変換")
    parser.add_argument("--md", required=True, help="入力Markdownファイルのパス")
    parser.add_argument("--output", help="出力JSONパス（デフォルト: 同フォルダに YYYYMM.json）")
    return parser.parse_args()


def infer_json_path(md_path: str) -> Path:
    """202604note.md → 202604.json"""
    p = Path(md_path)
    stem = re.sub(r"note$", "", p.stem)
    return p.parent / f"{stem}.json"


def parse_md_to_json(content: str, model) -> list[dict]:
    """MarkdownテキストをGeminiでJSON配列に変換する"""
    prompt = PROMPT_PARSE_TEMPLATE.format(content=content)
    # API側にJSONでの返却を強制する設定を追加
    response = model.generate_content(
        prompt,
        generation_config=genai.GenerationConfig(response_mime_type="application/json")
    )
    text = response.text.strip()

    # コードブロック除去
    m = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", text, re.DOTALL)
    if m:
        text = m.group(1)
    else:
        m = re.search(r"\[.*\]", text, re.DOTALL)
        if m:
            text = m.group(0)

    return json.loads(text)


def run(md_path: str, output_path: str | None = None) -> Path | None:
    """GUIやスクリプトから直接呼び出せるエントリポイント。出力JSONパスを返す。"""
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError(".env に GOOGLE_API_KEY が設定されていません")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(GEMINI_MODEL)

    content = Path(md_path).read_text(encoding="utf-8")
    print(f"[INFO] Markdown読込: {Path(md_path).name}  ({len(content)}文字)")
    print("[INFO] Gemini解析中...")

    try:
        data = parse_md_to_json(content, model)
    except (json.JSONDecodeError, ValueError) as e:
        print(f"[ERROR] JSONパース失敗: {e}")
        return None

    out_path = Path(output_path) if output_path else infer_json_path(md_path)
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[SAVED] {out_path}  ({len(data)}日分)")
    return out_path


def main() -> None:
    load_dotenv()
    args = parse_args()
    run(args.md, args.output)


if __name__ == "__main__":
    main()
