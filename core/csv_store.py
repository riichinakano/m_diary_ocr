"""スプレッドシート（visits / sales）の読み書き（Streamlit Secrets連携）"""

import os
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

VISITS_COLS = ["date", "exhibition", "code", "category", "discount",
               "count", "created_at", "updated_at"]
SALES_COLS  = ["date", "exhibition", "code", "name",
               "count", "created_at", "updated_at"]

def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")

def _get_worksheet(sheet_name: str):
    """Streamlit secretsから認証してワークシートを取得"""
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(
        creds_dict,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
    )
    client = gspread.authorize(creds)
    spreadsheet_url = st.secrets["spreadsheet_url"]
    doc = client.open_by_url(spreadsheet_url)
    
    try:
        return doc.worksheet(sheet_name)
    except gspread.exceptions.WorksheetNotFound:
        # シートが存在しない場合は新規作成する
        return doc.add_worksheet(title=sheet_name, rows="1000", cols="20")

def _read_gsheet(sheet_name: str, cols: list[str]) -> pd.DataFrame:
    try:
        sheet = _get_worksheet(sheet_name)
        records = sheet.get_all_records()
        if not records:
            return pd.DataFrame(columns=cols)
        df = pd.DataFrame(records, dtype=str).fillna("")
        for col in cols:
            if col not in df.columns:
                df[col] = ""
        return df[cols]
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
        st.error(f"スプレッドシートへの書き込みに失敗しました。エラー内容を開発者に連絡してください。エラー: {e}")


# ──────────────────────── 読み込み ────────────────────────

def read_visits() -> pd.DataFrame:
    return _read_gsheet("visits", VISITS_COLS)


def read_sales() -> pd.DataFrame:
    return _read_gsheet("sales", SALES_COLS)


# ──────────────────────── 重複チェック ────────────────────────

def find_visit_duplicates(rows: list[dict]) -> list[dict]:
    """rowsのうち既存CSVと一意キー (date, code, category, discount) が重複するものを返す"""
    df = read_visits()
    if df.empty:
        return []
    dups = []
    for row in rows:
        disc = row.get("discount") or ""
        mask = (
            (df["date"]     == row["date"]) &
            (df["code"]     == row["code"]) &
            (df["category"] == row["category"]) &
            (df["discount"] == disc)
        )
        if mask.any():
            dups.append(row)
    return dups


def find_sale_duplicates(rows: list[dict]) -> list[dict]:
    """rowsのうち既存CSVと一意キー (date, code, name) が重複するものを返す"""
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


# ──────────────────────── 書き込み（upsert） ────────────────────────

def upsert_visits(rows: list[dict]) -> None:
    """一意キーが存在すれば count/updated_at を更新、なければ追記"""
    df = read_visits()
    now = _now_iso()

    new_rows = []
    for row in rows:
        disc = row.get("discount") or ""
        mask = (
            (df["date"]     == row["date"]) &
            (df["code"]     == row["code"]) &
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

    _write_gsheet("visits", df, VISITS_COLS)


def upsert_sales(rows: list[dict]) -> None:
    """一意キーが存在すれば count/updated_at を更新、なければ追記"""
    df = read_sales()
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

    _write_gsheet("sales", df, SALES_COLS)


# ──────────────────────── 削除 ────────────────────────

def delete_visit(date: str, code: str, category: str, discount: str) -> None:
    df = read_visits()
    mask = (
        (df["date"]     == date) &
        (df["code"]     == code) &
        (df["category"] == category) &
        (df["discount"] == (discount or ""))
    )
    _write_gsheet("visits", df[~mask].reset_index(drop=True), VISITS_COLS)


def delete_sale(date: str, code: str, name: str) -> None:
    df = read_sales()
    mask = (
        (df["date"] == date) &
        (df["code"] == code) &
        (df["name"] == name)
    )
    _write_gsheet("sales", df[~mask].reset_index(drop=True), SALES_COLS)
