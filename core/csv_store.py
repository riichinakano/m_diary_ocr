"""visits.csv / sales.csv の読み書き（アトミック更新）"""

import os
from datetime import datetime
from pathlib import Path

import pandas as pd

VISITS_COLS = ["date", "exhibition", "code", "category", "discount",
               "count", "created_at", "updated_at"]
SALES_COLS  = ["date", "exhibition", "code", "name",
               "count", "created_at", "updated_at"]


def _visits_path(data_dir: Path) -> Path:
    return data_dir / "visits.csv"


def _sales_path(data_dir: Path) -> Path:
    return data_dir / "sales.csv"


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _ensure_csv(path: Path, cols: list[str]) -> None:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(columns=cols).to_csv(path, index=False, encoding="utf-8-sig")


def _write_atomic(path: Path, df: pd.DataFrame, cols: list[str]) -> None:
    tmp = path.with_suffix(".tmp")
    df[cols].to_csv(tmp, index=False, encoding="utf-8-sig")
    os.replace(tmp, path)


# ──────────────────────── 読み込み ────────────────────────

def read_visits(data_dir: Path) -> pd.DataFrame:
    p = _visits_path(data_dir)
    _ensure_csv(p, VISITS_COLS)
    df = pd.read_csv(p, dtype=str, encoding="utf-8-sig").fillna("")
    return df


def read_sales(data_dir: Path) -> pd.DataFrame:
    p = _sales_path(data_dir)
    _ensure_csv(p, SALES_COLS)
    df = pd.read_csv(p, dtype=str, encoding="utf-8-sig").fillna("")
    return df


# ──────────────────────── 重複チェック ────────────────────────

def find_visit_duplicates(data_dir: Path, rows: list[dict]) -> list[dict]:
    """rowsのうち既存CSVと一意キー (date, code, category, discount) が重複するものを返す"""
    df = read_visits(data_dir)
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


def find_sale_duplicates(data_dir: Path, rows: list[dict]) -> list[dict]:
    """rowsのうち既存CSVと一意キー (date, code, name) が重複するものを返す"""
    df = read_sales(data_dir)
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

def upsert_visits(data_dir: Path, rows: list[dict]) -> None:
    """一意キーが存在すれば count/updated_at を更新、なければ追記"""
    p = _visits_path(data_dir)
    _ensure_csv(p, VISITS_COLS)
    df = pd.read_csv(p, dtype=str, encoding="utf-8-sig").fillna("")
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
        df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)

    _write_atomic(p, df, VISITS_COLS)


def upsert_sales(data_dir: Path, rows: list[dict]) -> None:
    """一意キーが存在すれば count/updated_at を更新、なければ追記"""
    p = _sales_path(data_dir)
    _ensure_csv(p, SALES_COLS)
    df = pd.read_csv(p, dtype=str, encoding="utf-8-sig").fillna("")
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
        df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)

    _write_atomic(p, df, SALES_COLS)


# ──────────────────────── 削除 ────────────────────────

def delete_visit(data_dir: Path, date: str, code: str,
                 category: str, discount: str) -> None:
    p = _visits_path(data_dir)
    df = read_visits(data_dir)
    mask = (
        (df["date"]     == date) &
        (df["code"]     == code) &
        (df["category"] == category) &
        (df["discount"] == (discount or ""))
    )
    _write_atomic(p, df[~mask].reset_index(drop=True), VISITS_COLS)


def delete_sale(data_dir: Path, date: str, code: str, name: str) -> None:
    p = _sales_path(data_dir)
    df = read_sales(data_dir)
    mask = (
        (df["date"] == date) &
        (df["code"] == code) &
        (df["name"] == name)
    )
    _write_atomic(p, df[~mask].reset_index(drop=True), SALES_COLS)
