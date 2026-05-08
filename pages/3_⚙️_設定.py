"""設定ページ：展覧会・物販・割引リストのマスター編集"""

import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))

from core import master_loader  # noqa: E402

import streamlit as st  # noqa: E402

CONFIG_DIR = ROOT / "config"

# ══════════════════════════════════════════════════════════════
st.header("⚙️ マスター設定")
st.caption("変更後は各セクションの「保存」ボタンを押してください")
# ══════════════════════════════════════════════════════════════

master = master_loader.load(CONFIG_DIR)


def _save(data: dict) -> None:
    master_loader.save(CONFIG_DIR, data)
    st.success("✅ 保存しました")


# ── 展覧会リスト ──────────────────────────────────────────────
with st.expander("🎨 展覧会リスト", expanded=True):
    exhibitions: list[str] = list(master.get("exhibitions", []))
    updated_exh: list[str] = []

    for i, exh in enumerate(exhibitions):
        c1, c2 = st.columns([6, 1])
        val = c1.text_input(
            f"展覧会 {i + 1}", value=exh,
            label_visibility="collapsed", key=f"exh_val_{i}",
        )
        updated_exh.append(val)
        if c2.button("削除", key=f"del_exh_{i}"):
            exhibitions.pop(i)
            master["exhibitions"] = exhibitions
            _save(master)
            st.rerun()

    st.markdown("---")
    c_new, c_add = st.columns([6, 1])
    new_exh = c_new.text_input(
        "新規展覧会名", placeholder="例: 9_夏季展_前期",
        label_visibility="collapsed", key="new_exh_input",
    )
    if c_add.button("追加", key="btn_add_exh"):
        trimmed = new_exh.strip()
        if trimmed and trimmed not in exhibitions:
            exhibitions.append(trimmed)
            master["exhibitions"] = exhibitions
            _save(master)
            st.rerun()
        elif trimmed in exhibitions:
            st.warning("既に登録されています")

    if st.button("展覧会リストを保存", key="save_exh_btn"):
        master["exhibitions"] = [e.strip() for e in updated_exh if e.strip()]
        _save(master)

# ── 物販リスト ────────────────────────────────────────────────
with st.expander("🛍️ 物販リスト"):
    st.caption("コード・品名・単価（円）を編集できます")
    merch_list: list[dict] = list(master.get("merchandise", []))
    updated_merch: list[dict] = []

    for i, m in enumerate(merch_list):
        c1, c2, c3, c4 = st.columns([2, 3, 1, 1])
        code_val = c1.text_input(
            f"コード {i}", value=m["code"],
            label_visibility="collapsed", key=f"m_code_{i}",
        )
        name_val = c2.text_input(
            f"品名 {i}", value=m["name"],
            label_visibility="collapsed", key=f"m_name_{i}",
        )
        price_val = c3.number_input(
            f"単価 {i}", value=int(m.get("price", 0)),
            min_value=0, step=10, format="%d",
            label_visibility="collapsed", key=f"m_price_{i}",
        )
        updated_merch.append({"code": code_val, "name": name_val, "price": int(price_val)})
        if c4.button("削除", key=f"del_merch_{i}"):
            merch_list.pop(i)
            master["merchandise"] = merch_list
            _save(master)
            st.rerun()

    st.markdown("---")
    c1, c2, c3, c4 = st.columns([2, 3, 1, 1])
    new_m_code = c1.text_input(
        "新コード", placeholder="P：絵葉書",
        label_visibility="collapsed", key="new_m_code",
    )
    new_m_name = c2.text_input(
        "新品名", placeholder="絵葉書（＠100円）",
        label_visibility="collapsed", key="new_m_name",
    )
    new_m_price = c3.number_input(
        "新単価", value=0, min_value=0, step=10, format="%d",
        label_visibility="collapsed", key="new_m_price",
    )
    if c4.button("追加", key="btn_add_merch"):
        if new_m_code.strip() and new_m_name.strip():
            merch_list.append({"code": new_m_code.strip(), "name": new_m_name.strip(), "price": int(new_m_price)})
            master["merchandise"] = merch_list
            _save(master)
            st.rerun()
        else:
            st.warning("コードと品名を両方入力してください")

    if st.button("物販リストを保存", key="save_merch_btn"):
        master["merchandise"] = [
            m for m in updated_merch if m["code"].strip() and m["name"].strip()
        ]
        _save(master)

# ── 割引リスト ────────────────────────────────────────────────
with st.expander("💰 割引種別リスト"):
    discounts: list[str] = list(master.get("discounts", []))
    updated_disc: list[str] = []

    for i, d in enumerate(discounts):
        c1, c2 = st.columns([6, 1])
        val = c1.text_input(
            f"割引 {i}", value=d,
            label_visibility="collapsed", key=f"disc_val_{i}",
        )
        updated_disc.append(val)
        if c2.button("削除", key=f"del_disc_{i}"):
            discounts.pop(i)
            master["discounts"] = discounts
            _save(master)
            st.rerun()

    st.markdown("---")
    c_new, c_add = st.columns([6, 1])
    new_disc = c_new.text_input(
        "新規割引", placeholder="例: たんぽぽカード",
        label_visibility="collapsed", key="new_disc_input",
    )
    if c_add.button("追加", key="btn_add_disc"):
        trimmed = new_disc.strip()
        if trimmed and trimmed not in discounts:
            discounts.append(trimmed)
            master["discounts"] = discounts
            _save(master)
            st.rerun()
        elif trimmed in discounts:
            st.warning("既に登録されています")

    if st.button("割引リストを保存", key="save_disc_btn"):
        master["discounts"] = [d.strip() for d in updated_disc if d.strip()]
        _save(master)

# ── 入館者分類・料金リスト ────────────────────────────────────
with st.expander("👤 入館者分類・料金リスト"):
    st.caption("コード・分類名・料金（円）を編集できます")
    cats: list[dict] = list(master.get("visitor_categories", []))
    updated_cats: list[dict] = []

    for i, vc in enumerate(cats):
        c1, c2, c3, c4 = st.columns([2, 3, 1, 1])
        code_val = c1.text_input(
            f"コード {i}", value=vc["code"],
            label_visibility="collapsed", key=f"vc_code_{i}",
        )
        cat_val = c2.text_input(
            f"分類 {i}", value=vc["category"],
            label_visibility="collapsed", key=f"vc_cat_{i}",
        )
        price_val = c3.number_input(
            f"料金 {i}", value=int(vc.get("price", 0)),
            min_value=0, step=10, format="%d",
            label_visibility="collapsed", key=f"vc_price_{i}",
        )
        updated_cats.append({"code": code_val, "category": cat_val, "price": int(price_val)})
        if c4.button("削除", key=f"del_vc_{i}"):
            cats.pop(i)
            master["visitor_categories"] = cats
            _save(master)
            st.rerun()

    st.markdown("---")
    c1, c2, c3, c4 = st.columns([2, 3, 1, 1])
    new_vc_code = c1.text_input(
        "新コード", placeholder="A：一般",
        label_visibility="collapsed", key="new_vc_code",
    )
    new_vc_cat = c2.text_input(
        "新分類", placeholder="一般（障がい者割引）",
        label_visibility="collapsed", key="new_vc_cat",
    )
    new_vc_price = c3.number_input(
        "新料金", value=0, min_value=0, step=10, format="%d",
        label_visibility="collapsed", key="new_vc_price",
    )
    if c4.button("追加", key="btn_add_vc"):
        if new_vc_code.strip() and new_vc_cat.strip():
            cats.append({"code": new_vc_code.strip(), "category": new_vc_cat.strip(), "price": int(new_vc_price)})
            master["visitor_categories"] = cats
            _save(master)
            st.rerun()
        else:
            st.warning("コードと分類名を両方入力してください")

    if st.button("入館者分類リストを保存", key="save_vc_btn"):
        master["visitor_categories"] = [
            vc for vc in updated_cats if vc["code"].strip() and vc["category"].strip()
        ]
        _save(master)
