"""visits / sales の読み書き
- USE_LOCAL_CSV=1 の環境変数が設定されている場合はローカル CSV（data/）
- それ以外は Google Sheets（Streamlit Secrets 連携）
"""

import os
import re
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

VISITS_COLS = ["date", "exhibition", "code", "category", "discount",
               "count", "created_at", "updated_at"]
SALES_COLS  = ["date", "exhibition", "code", "name",
               "count", "created_at", "updated_at"]

ROOT     = Path(__file__).parents[1]
DATA_DIR = ROOT / "data"


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _normalize_date(v: str) -> str:
    """2026/5/1 や 5/1/2026 など各種形式を YYYY-MM-DD に統一"""
    v = str(v).strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}$", v):
        return v
    m = re.match(r"^(\d{4})[/.](\d{1,2})[/.](\d{1,2})$", v)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    try:
        return pd.to_datetime(v).strftime("%Y-%m-%d")
    except Exception:
        return v


def _use_local() -> bool:
    if os.environ.get("USE_LOCAL_CSV", "").lower() in ("1", "true", "yes"):
        return True
    try:
        _ = st.secrets["gcp_service_account"]
        return False
    except Exception:
        return True


# ──────────────────── ローカル CSV ───────────────────────────

def _local_path(name: str) -> Path:
    return DATA_DIR / f"{name}.csv"


def _read_local(name: str, cols: list[str]) -> pd.DataFrame:
    path = _local_path(name)
    if not path.exists():
        return pd.DataFrame(columns=cols)
    try:
        df = pd.read_csv(path, dtype=str).fillna("")
        for col in cols:
            if col not in df.columns:
                df[col] = ""
        df = df[cols]
        if "date" in df.columns:
            df["date"] = df["date"].apply(_normalize_date)
        return df
    except Exception:
        return pd.DataFrame(columns=cols)


def _write_local(name: str, df: pd.DataFrame, cols: list[str]) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    df[cols].to_csv(_local_path(name), index=False, encoding="utf-8-sig")


# ──────────────────── Google Sheets ──────────────────────────

def _get_worksheet(sheet_name: str):
    import gspread
    from google.oauth2.service_account import Credentials

    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(
        creds_dict,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ],
    )
    client = gspread.Client(auth=creds)
    doc = client.open_by_url(st.secrets["spreadsheet_url"])
    try:
        return doc.worksheet(sheet_name)
    except gspread.exceptions.WorksheetNotFound:
        return doc.add_worksheet(title=sheet_name, rows="1000", cols="20")


def _read_gsheet(sheet_name: str, cols: list[str]) -> pd.DataFrame:
    try:
        sheet   = _get_worksheet(sheet_name)
        records = sheet.get_all_records()
        if not records:
            return pd.DataFrame(columns=cols)
        df = pd.DataFrame(records, dtype=str).fillna("")
        for col in cols:
            if col not in df.columns:
                df[col] = ""
        df = df[cols]
        if "date" in df.columns:
            df["date"] = df["date"].apply(_normalize_date)
        return df
    except Exception as e:
        st.error(f"スプレッドシートの読み込みに失敗しました: {e}")
        return pd.DataFrame(columns=cols)


def _write_gsheet(sheet_name: str, df: pd.DataFrame, cols: list[str]) -> None:
    try:
        sheet = _get_worksheet(sheet_name)
        sheet.clear()
        if df.empty:
            sheet.update(values=[cols], range_name="A1")
        else:
            data = [cols] + df[cols].astype(str).fillna("").values.tolist()
            sheet.update(values=data, range_name="A1")
    except Exception as e:
        st.exception(e)
        st.error(f"スプレッドシートへの書き込みに失敗しました。エラー: {e}")


# ──────────────────── 統合ルーター ───────────────────────────

def _read(name: str, cols: list[str]) -> pd.DataFrame:
    return _read_local(name, cols) if _use_local() else _read_gsheet(name, cols)


def _write(name: str, df: pd.DataFrame, cols: list[str]) -> None:
    if _use_local():
        _write_local(name, df, cols)
    else:
        _write_gsheet(name, df, cols)


# ──────────────────────── 読み込み ────────────────────────────

@st.cache_data(ttl=60)
def read_visits() -> pd.DataFrame:
    return _read("visits", VISITS_COLS)


@st.cache_data(ttl=60)
def read_sales() -> pd.DataFrame:
    return _read("sales", SALES_COLS)


# ──────────────────────── 重複チェック ───────────────────────

def find_visit_duplicates(rows: list[dict]) -> list[dict]:
    df = read_visits()
    if df.empty:
        return []
    dups = []
    for row in rows:
        disc = row.get("discount") or ""
        mask = (
            (df["date"]     == row["date"])     &
            (df["code"]     == row["code"])     &
            (df["category"] == row["category"]) &
            (df["discount"] == disc)
        )
        if mask.any():
            dups.append(row)
    return dups


def find_sale_duplicates(rows: list[dict]) -> list[dict]:
    df = read_sales()
    if df.empty:
        return []
    dups = []
    for row in rows:
        mask = (
            (df["date"] == row["date"]) &
            (df["code"] == row["code"]) &
            (df["name"] == row["name"])
        )
        if mask.any():
            dups.append(row)
    return dups


# ──────────────────────── 書き込み（upsert） ─────────────────

def upsert_visits(rows: list[dict]) -> None:
    df  = read_visits()
    now = _now_iso()

    new_rows = []
    for row in rows:
        disc = row.get("discount") or ""
        mask = (
            (df["date"]     == row["date"])     &
            (df["code"]     == row["code"])     &
            (df["category"] == row["category"]) &
            (df["discount"] == disc)
        )
        if mask.any():
            idx = df.index[mask][0]
            df.at[idx, "count"]      = str(row["count"])
            df.at[idx, "exhibition"] = row.get("exhibition", "")
            df.at[idx, "updated_at"] = now
        else:
            new_rows.append({
                "date":       row["date"],
                "exhibition": row.get("exhibition", ""),
                "code":       row["code"],
                "category":   row["category"],
                "discount":   disc,
                "count":      str(row["count"]),
                "created_at": now,
                "updated_at": now,
            })

    if new_rows:
        df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True).fillna("")

    _write("visits", df, VISITS_COLS)
    read_visits.clear()


def upsert_sales(rows: list[dict]) -> None:
    df  = read_sales()
    now = _now_iso()

    new_rows = []
    for row in rows:
        mask = (
            (df["date"] == row["date"]) &
            (df["code"] == row["code"]) &
            (df["name"] == row["name"])
        )
        if mask.any():
            idx = df.index[mask][0]
            df.at[idx, "count"]      = str(row["count"])
            df.at[idx, "exhibition"] = row.get("exhibition", "")
            df.at[idx, "updated_at"] = now
        else:
            new_rows.append({
                "date":       row["date"],
                "exhibition": row.get("exhibition", ""),
                "code":       row["code"],
                "name":       row["name"],
                "count":      str(row["count"]),
                "created_at": now,
                "updated_at": now,
            })

    if new_rows:
        df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True).fillna("")

    _write("sales", df, SALES_COLS)
    read_sales.clear()


# ──────────────────────── 削除 ────────────────────────────────

def delete_visit(date: str, code: str, category: str, discount: str) -> None:
    df = read_visits()
    mask = (
        (df["date"]     == date)           &
        (df["code"]     == code)           &
        (df["category"] == category)       &
        (df["discount"] == (discount or ""))
    )
    _write("visits", df[~mask].reset_index(drop=True), VISITS_COLS)
    read_visits.clear()


def delete_sale(date: str, code: str, name: str) -> None:
    df = read_sales()
    mask = (
        (df["date"] == date) &
        (df["code"] == code) &
        (df["name"] == name)
    )
    _write("sales", df[~mask].reset_index(drop=True), SALES_COLS)
    read_sales.clear()
