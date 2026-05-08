"""入力ページ：1日分の入館者・物販をCSVに保存する"""

import datetime
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))

from core import csv_store, master_loader  # noqa: E402

import streamlit as st  # noqa: E402

DATA_DIR   = ROOT / "data"
CONFIG_DIR = ROOT / "config"

master       = master_loader.load(CONFIG_DIR)
visitor_cats = master.get("visitor_categories", [])
discounts_all = master.get("discounts", [])
merch_list   = master.get("merchandise", [])
exhibitions  = master.get("exhibitions", [])

# ── セッション初期化 ──────────────────────────────────────────
for _k, _v in [("visitors", []), ("sales", []), ("confirm_overwrite", False)]:
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ══════════════════════════════════════════════════════════════
st.header("📝 1日分入力")
# ══════════════════════════════════════════════════════════════

# ── 基本情報 ──────────────────────────────────────────────────
date_val = st.date_input("日付", datetime.date.today())
date_str = str(date_val)

if exhibitions:
    exhibition = st.selectbox("展覧会名", exhibitions)
else:
    st.warning("⚙️ 設定ページで展覧会名を登録してください")
    exhibition = st.text_input("展覧会名（直接入力）", key="exh_manual")

st.divider()

# ── 入館者 ────────────────────────────────────────────────────
st.subheader("👤 入館者")

if visitor_cats:
    cat_labels = [f"{vc['code']}  {vc['category']}" for vc in visitor_cats]
    disc_opts  = ["（なし）"] + discounts_all

    col_cat, col_disc, col_cnt, col_add = st.columns([3, 2, 1, 1])
    with col_cat:
        v_cat_idx = st.selectbox(
            "分類", range(len(cat_labels)),
            format_func=lambda i: cat_labels[i],
            label_visibility="collapsed", key="v_cat_sel",
        )
    with col_disc:
        v_disc_idx = st.selectbox(
            "割引", range(len(disc_opts)),
            format_func=lambda i: disc_opts[i],
            label_visibility="collapsed", key="v_disc_sel",
        )
    with col_cnt:
        v_count = st.number_input(
            "人数", min_value=1, step=1, value=1,
            label_visibility="collapsed", key="v_cnt_inp",
        )
    with col_add:
        if st.button("追加", key="btn_add_v", use_container_width=True):
            vc   = visitor_cats[v_cat_idx]
            disc = "" if v_disc_idx == 0 else discounts_all[v_disc_idx - 1]
            st.session_state.visitors.append({
                "code":     vc["code"],
                "category": vc["category"],
                "discount": disc,
                "count":    int(v_count),
            })
            st.rerun()

# 入館者リスト
v_price_map = {(vc["code"], vc["category"]): int(vc.get("price", 0)) for vc in visitor_cats}

if st.session_state.visitors:
    st.markdown("**本日の入館者**")
    for i, v in enumerate(st.session_state.visitors):
        c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
        c1.write(v["category"])
        c2.write(v["discount"] if v["discount"] else "—")
        c3.write(f"**{v['count']} 人**")
        if c4.button("×", key=f"del_v_{i}"):
            st.session_state.visitors.pop(i)
            st.rerun()

    total_people    = sum(v["count"] for v in st.session_state.visitors)
    total_admission = sum(v["count"] * v_price_map.get((v["code"], v["category"]), 0)
                         for v in st.session_state.visitors)
    st.info(f"入館者合計：**{total_people} 人** ／ **{total_admission:,} 円**")
else:
    st.caption("まだ入力がありません")
    total_people    = 0
    total_admission = 0

st.divider()

# ── 物販 ──────────────────────────────────────────────────────
st.subheader("🛍️ 物販")

if merch_list:
    m_labels = [f"{m['code']}  {m['name']}" for m in merch_list]

    col_m, col_mc, col_madd = st.columns([4, 1, 1])
    with col_m:
        m_idx = st.selectbox(
            "商品", range(len(m_labels)),
            format_func=lambda i: m_labels[i],
            label_visibility="collapsed", key="m_sel",
        )
    with col_mc:
        m_count = st.number_input(
            "販売数", min_value=1, step=1, value=1,
            label_visibility="collapsed", key="m_cnt_inp",
        )
    with col_madd:
        if st.button("追加", key="btn_add_m", use_container_width=True):
            m = merch_list[m_idx]
            st.session_state.sales.append({
                "code":  m["code"],
                "name":  m["name"],
                "count": int(m_count),
            })
            st.rerun()

# 物販リスト
s_price_map = {(m["code"], m["name"]): int(m.get("price", 0)) for m in merch_list}

if st.session_state.sales:
    st.markdown("**本日の物販**")
    for i, s in enumerate(st.session_state.sales):
        c1, c2, c3 = st.columns([4, 2, 1])
        c1.write(s["name"])
        c2.write(f"**{s['count']} 個**")
        if c3.button("×", key=f"del_s_{i}"):
            st.session_state.sales.pop(i)
            st.rerun()

    total_items = sum(s["count"] for s in st.session_state.sales)
    total_sales = sum(s["count"] * s_price_map.get((s["code"], s["name"]), 0)
                      for s in st.session_state.sales)
    st.info(f"物販合計：**{total_items} 点** ／ **{total_sales:,} 円**")
else:
    st.caption("まだ入力がありません")
    total_items = 0
    total_sales = 0

# ── 合計サマリー ──────────────────────────────────────────────
if st.session_state.visitors or st.session_state.sales:
    grand_total = total_admission + total_sales
    cols = st.columns(4)
    cols[0].metric("入館者合計", f"{total_people} 人")
    cols[1].metric("入館料売上", f"¥{total_admission:,}")
    cols[2].metric("物販点数", f"{total_items} 点")
    cols[3].metric("物販売上", f"¥{total_sales:,}")
    st.success(f"**本日の売上合計：¥{grand_total:,}**")

st.divider()

# ── 保存処理 ──────────────────────────────────────────────────

def _do_save(v_rows: list, s_rows: list) -> None:
    if v_rows:
        csv_store.upsert_visits(DATA_DIR, v_rows)
    if s_rows:
        csv_store.upsert_sales(DATA_DIR, s_rows)
    st.session_state.visitors.clear()
    st.session_state.sales.clear()
    for _k in ("confirm_overwrite", "_pending_v", "_pending_s", "_dups_v", "_dups_s"):
        st.session_state.pop(_k, None)


if not st.session_state.get("confirm_overwrite"):
    if st.button("💾 この日付で保存", type="primary", use_container_width=True):
        if not st.session_state.visitors and not st.session_state.sales:
            st.warning("入力データがありません")
        else:
            v_rows = [{**v, "date": date_str, "exhibition": exhibition}
                      for v in st.session_state.visitors]
            s_rows = [{**s, "date": date_str, "exhibition": exhibition}
                      for s in st.session_state.sales]

            v_dups = csv_store.find_visit_duplicates(DATA_DIR, v_rows)
            s_dups = csv_store.find_sale_duplicates(DATA_DIR, s_rows)

            if v_dups or s_dups:
                st.session_state.confirm_overwrite = True
                st.session_state._pending_v = v_rows
                st.session_state._pending_s = s_rows
                st.session_state._dups_v    = v_dups
                st.session_state._dups_s    = s_dups
                st.rerun()
            else:
                _do_save(v_rows, s_rows)
                st.success(f"✅ {date_str} のデータを保存しました")
                st.rerun()
else:
    # ── 重複確認UI ──
    st.warning("⚠️ 以下のデータが既に存在します。上書きしますか？")

    if st.session_state.get("_dups_v"):
        st.markdown("**入館者（上書き対象）**")
        for d in st.session_state._dups_v:
            disc = d.get("discount") or "—"
            st.write(f"・{d['category']} / {disc} / {d['count']} 人")

    if st.session_state.get("_dups_s"):
        st.markdown("**物販（上書き対象）**")
        for d in st.session_state._dups_s:
            st.write(f"・{d['name']} / {d['count']} 個")

    col_ok, col_ng = st.columns(2)
    if col_ok.button("上書きして保存", type="primary", use_container_width=True):
        _do_save(st.session_state._pending_v, st.session_state._pending_s)
        st.success("✅ 上書き保存しました")
        st.rerun()
    if col_ng.button("キャンセル", use_container_width=True):
        for _k in ("confirm_overwrite", "_pending_v", "_pending_s", "_dups_v", "_dups_s"):
            st.session_state.pop(_k, None)
        st.rerun()
