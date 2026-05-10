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
_hcol1, _hcol2 = st.columns([4, 1])
_hcol1.header("📋 入力履歴")
if _hcol2.button("🔄 更新", use_container_width=True):
    csv_store.read_visits.clear()
    csv_store.read_sales.clear()
    st.rerun()
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
try:
    df_v = csv_store.read_visits()
    df_s = csv_store.read_sales()
except Exception as _e:
    st.error(f"スプレッドシートの読み込みに失敗しました: {_e}")
    st.info("しばらく待ってから「🔄 更新」ボタンを押してください。Google Sheets API が一時的に不安定な場合があります。")
    st.stop()

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
    merch_rev      = int((ds["count"] * ds["unit_price"]).sum())

    # codeごとの販売数集計（動的）
    by_code: dict[str, int] = (
        ds.groupby("code")["count"].sum().astype(int).to_dict()
    )
else:
    by_code = {}
    merch_rev = 0

grand_rev = admission_rev + merch_rev

c1, c2, c3 = st.columns(3)
c1.metric("有料入場者",           f"{paid_visitors:,} 人")
c2.metric("入場者合計（無料含む）", f"{total_visitors:,} 人")
c3.metric("入館料売上",           f"¥{admission_rev:,}")

if by_code:
    cols_m = st.columns(min(len(by_code) + 1, 4))  # 最大4カラム
    for idx, (code, cnt) in enumerate(by_code.items()):
        cols_m[idx % len(cols_m)].metric(f"{code} 販売数", f"{cnt:,}")
    # 最後に物販売上
    cols_m[-1].metric("物販売上", f"¥{merch_rev:,}")
else:
    st.metric("物販売上", f"¥{merch_rev:,}")

st.info(f"**{sel_month} 売上合計：¥{grand_rev:,}**　（入館料 ¥{admission_rev:,} ＋ 物販 ¥{merch_rev:,}）")

st.divider()

# ── 入館者 ────────────────────────────────────────────────────
if data_type in ("入館者", "両方"):
    st.subheader("👤 入館者")
    if not df_v_m.empty:
        # 表示用データフレームの作成
        disp_v = df_v_m.copy()
        disp_v["人数"] = pd.to_numeric(disp_v["count"], errors="coerce").fillna(0).astype(int)
        disp_v["単価"] = disp_v.apply(lambda r: v_price_map.get((r["code"], r["category"]), 0), axis=1)
        disp_v["金額"] = disp_v["人数"] * disp_v["単価"]
        disp_v["割引"] = disp_v["discount"].fillna("").apply(lambda x: x if x else "—")
        
        disp_v = disp_v.rename(columns={"date": "日付", "category": "分類"})
        
        st.dataframe(
            disp_v[["日付", "分類", "割引", "人数", "金額"]],
            use_container_width=True,
            hide_index=True,
            column_config={
                "金額": st.column_config.NumberColumn("金額", format="¥%d")
            }
        )

        with st.expander("🗑️ 入館者データの削除"):
            opts_v = [
                f"{row['date']} | {row['category']} | {row['discount'] if row['discount'] else '—'} | {row['count']}人"
                for _, row in df_v_m.iterrows()
            ]
            del_sel_v = st.selectbox("削除するデータを選択", opts_v, key="del_v_sel")
            if st.button("削除実行", key="del_v_btn"):
                idx = opts_v.index(del_sel_v)
                row = df_v_m.iloc[idx]
                csv_store.delete_visit(
                    row["date"], row["code"], row["category"], row["discount"]
                )
                st.rerun()
    else:
        st.info(f"{sel_month} の入館者データはありません")

# ── 物販 ──────────────────────────────────────────────────────
if data_type in ("物販", "両方"):
    st.subheader("🛍️ 物販")
    if not df_s_m.empty:
        disp_s = df_s_m.copy()
        disp_s["販売数"] = pd.to_numeric(disp_s["count"], errors="coerce").fillna(0).astype(int)
        disp_s["単価"] = disp_s.apply(lambda r: s_price_map.get((r["code"], r["name"]), 0), axis=1)
        disp_s["金額"] = disp_s["販売数"] * disp_s["単価"]
        
        disp_s = disp_s.rename(columns={"date": "日付", "name": "商品名"})
        
        st.dataframe(
            disp_s[["日付", "商品名", "販売数", "金額"]],
            use_container_width=True,
            hide_index=True,
            column_config={
                "金額": st.column_config.NumberColumn("金額", format="¥%d")
            }
        )

        with st.expander("🗑️ 物販データの削除"):
            opts_s = [
                f"{row['date']} | {row['name']} | {row['count']}個"
                for _, row in df_s_m.iterrows()
            ]
            del_sel_s = st.selectbox("削除するデータを選択", opts_s, key="del_s_sel")
            if st.button("削除実行", key="del_s_btn"):
                idx = opts_s.index(del_sel_s)
                row = df_s_m.iloc[idx]
                csv_store.delete_sale(row["date"], row["code"], row["name"])
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
