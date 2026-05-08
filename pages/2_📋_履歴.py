"""履歴ページ：月別入館者・物販データの閲覧・削除・CSVダウンロード"""

import datetime
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))

from core import csv_store, master_loader  # noqa: E402

import pandas as pd        # noqa: E402
import streamlit as st     # noqa: E402

DATA_DIR   = ROOT / "data"
CONFIG_DIR = ROOT / "config"

# ══════════════════════════════════════════════════════════════
st.header("📋 入力履歴")
# ══════════════════════════════════════════════════════════════

# ── 月選択・表示オプション ────────────────────────────────────
today = datetime.date.today()
months: list[str] = []
d = today.replace(day=1)
for _ in range(13):
    months.append(d.strftime("%Y-%m"))
    d = (d - datetime.timedelta(days=1)).replace(day=1)

sel_month = st.selectbox("表示月", months, index=0)

col_opt1, col_opt2 = st.columns(2)
with col_opt1:
    data_type = st.radio("データ種別", ["入館者", "物販", "両方"], horizontal=True)
with col_opt2:
    sort_asc = st.radio("並び順", ["日付昇順", "日付降順"], horizontal=True) == "日付昇順"

st.divider()

# ── 料金マスター読み込み ──────────────────────────────────────
master = master_loader.load(CONFIG_DIR)
v_price_map = {
    (vc["code"], vc["category"]): int(vc.get("price", 0))
    for vc in master.get("visitor_categories", [])
}
s_price_map = {
    (m["code"], m["name"]): int(m.get("price", 0))
    for m in master.get("merchandise", [])
}

# ── CSV読み込み・月フィルタ・ソート ──────────────────────────
df_v = csv_store.read_visits(DATA_DIR)
df_s = csv_store.read_sales(DATA_DIR)

def _filter_month(df: pd.DataFrame, month: str) -> pd.DataFrame:
    return df[df["date"].str.startswith(month)].sort_values("date", ascending=sort_asc).reset_index(drop=True)

df_v_m = (
    _filter_month(df_v, sel_month)
    if not df_v.empty else pd.DataFrame(columns=csv_store.VISITS_COLS)
)
df_s_m = (
    _filter_month(df_s, sel_month)
    if not df_s.empty else pd.DataFrame(columns=csv_store.SALES_COLS)
)

# ── 月次集計 ──────────────────────────────────────────────────
st.subheader(f"📊 {sel_month} 月次集計")

if not df_v_m.empty:
    dv = df_v_m.copy()
    dv["count"] = pd.to_numeric(dv["count"], errors="coerce").fillna(0).astype(int)
    dv["unit_price"] = dv.apply(lambda r: v_price_map.get((r["code"], r["category"]), 0), axis=1)
    total_visitors  = int(dv["count"].sum())
    paid_visitors   = int(dv[dv["unit_price"] > 0]["count"].sum())
    admission_rev   = int((dv["count"] * dv["unit_price"]).sum())
else:
    total_visitors = paid_visitors = admission_rev = 0

if not df_s_m.empty:
    ds = df_s_m.copy()
    ds["count"] = pd.to_numeric(ds["count"], errors="coerce").fillna(0).astype(int)
    ds["unit_price"] = ds.apply(lambda r: s_price_map.get((r["code"], r["name"]), 0), axis=1)
    postcard_count = int(ds[ds["code"] == "P：絵葉書"]["count"].sum())
    catalog_count  = int(ds[ds["code"] == "Q：図録"]["count"].sum())
    merch_rev      = int((ds["count"] * ds["unit_price"]).sum())
else:
    postcard_count = catalog_count = merch_rev = 0

grand_rev = admission_rev + merch_rev

c1, c2, c3 = st.columns(3)
c1.metric("有料入場者",           f"{paid_visitors:,} 人")
c2.metric("入場者合計（無料含む）", f"{total_visitors:,} 人")
c3.metric("入館料売上",           f"¥{admission_rev:,}")

c4, c5, c6 = st.columns(3)
c4.metric("絵葉書販売数",  f"{postcard_count:,} 枚")
c5.metric("図録販売数",    f"{catalog_count:,} 冊")
c6.metric("物販売上",      f"¥{merch_rev:,}")

st.info(f"**{sel_month} 売上合計：¥{grand_rev:,}**　（入館料 ¥{admission_rev:,} ＋ 物販 ¥{merch_rev:,}）")

st.divider()

# ── 入館者 ────────────────────────────────────────────────────
if data_type in ("入館者", "両方"):
    st.subheader("👤 入館者")
    if not df_v_m.empty:
        hc = st.columns([2, 3, 2, 1, 2, 1])
        for col, label in zip(hc, ["日付", "分類", "割引", "人数", "金額", ""]):
            col.markdown(f"**{label}**")
        st.markdown("---")
        for _, row in df_v_m.iterrows():
            cnt        = int(row["count"]) if str(row["count"]).isdigit() else 0
            unit_price = v_price_map.get((row["code"], row["category"]), 0)
            subtotal   = cnt * unit_price
            c1, c2, c3, c4, c5, c6 = st.columns([2, 3, 2, 1, 2, 1])
            c1.write(row["date"])
            c2.write(row["category"])
            c3.write(row["discount"] if row["discount"] else "—")
            c4.write(f"{row['count']} 人")
            c5.write(f"¥{subtotal:,}")
            btn_key = f"del_hv_{row['date']}_{row['code']}_{row['category']}_{row['discount']}"
            if c6.button("削除", key=btn_key):
                csv_store.delete_visit(
                    DATA_DIR, row["date"], row["code"], row["category"], row["discount"]
                )
                st.rerun()
    else:
        st.info(f"{sel_month} の入館者データはありません")

# ── 物販 ──────────────────────────────────────────────────────
if data_type in ("物販", "両方"):
    st.subheader("🛍️ 物販")
    if not df_s_m.empty:
        hc = st.columns([2, 4, 1, 2, 1])
        for col, label in zip(hc, ["日付", "商品名", "販売数", "金額", ""]):
            col.markdown(f"**{label}**")
        st.markdown("---")
        for _, row in df_s_m.iterrows():
            cnt        = int(row["count"]) if str(row["count"]).isdigit() else 0
            unit_price = s_price_map.get((row["code"], row["name"]), 0)
            subtotal   = cnt * unit_price
            c1, c2, c3, c4, c5 = st.columns([2, 4, 1, 2, 1])
            c1.write(row["date"])
            c2.write(row["name"])
            c3.write(f"{row['count']} 個")
            c4.write(f"¥{subtotal:,}")
            btn_key = f"del_hs_{row['date']}_{row['code']}_{row['name']}"
            if c5.button("削除", key=btn_key):
                csv_store.delete_sale(DATA_DIR, row["date"], row["code"], row["name"])
                st.rerun()
    else:
        st.info(f"{sel_month} の物販データはありません")

st.divider()

# ── CSVダウンロード ───────────────────────────────────────────
st.subheader("💾 CSVダウンロード")
month_tag = sel_month.replace("-", "")

st.caption("当月")
col1, col2 = st.columns(2)
with col1:
    if not df_v_m.empty:
        st.download_button(
            f"📥 {sel_month} 入館者",
            df_v_m.to_csv(index=False).encode("utf-8-sig"),
            f"{month_tag}_visits.csv", "text/csv",
            use_container_width=True,
        )
    else:
        st.button(f"📥 {sel_month} 入館者", disabled=True, use_container_width=True)

with col2:
    if not df_s_m.empty:
        st.download_button(
            f"📥 {sel_month} 物販",
            df_s_m.to_csv(index=False).encode("utf-8-sig"),
            f"{month_tag}_sales.csv", "text/csv",
            use_container_width=True,
        )
    else:
        st.button(f"📥 {sel_month} 物販", disabled=True, use_container_width=True)

st.caption("全期間")
col3, col4 = st.columns(2)
with col3:
    if not df_v.empty:
        st.download_button(
            "📥 visits.csv（全期間）",
            df_v.to_csv(index=False).encode("utf-8-sig"),
            "visits.csv", "text/csv",
            use_container_width=True,
        )
    else:
        st.button("📥 visits.csv", disabled=True, use_container_width=True)

with col4:
    if not df_s.empty:
        st.download_button(
            "📥 sales.csv（全期間）",
            df_s.to_csv(index=False).encode("utf-8-sig"),
            "sales.csv", "text/csv",
            use_container_width=True,
        )
    else:
        st.button("📥 sales.csv", disabled=True, use_container_width=True)
