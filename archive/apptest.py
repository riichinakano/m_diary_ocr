import json
import datetime
import pandas as pd
import streamlit as st

st.set_page_config(page_title="美術館 受付システム", page_icon="🏛️", layout="centered")

# ==========================================
# マスターデータ定義（ご提示いただいたリストを正確に反映）
# ==========================================
VISITOR_CATEGORIES = {
    "一般": "A：一般",
    "一般（割引）": "A：一般",
    "一般（特別優待）": "A：一般",
    "シニア": "B：シニア",
    "シニア（割引）": "B：シニア",
    "シニア（特別優待）": "B：シニア",
    "学生": "C：学生",
    "学生（割引）": "C：学生",
    "学生（特別優待）": "C：学生",
    "学生（無料）": "C：学生",
    "小中学生": "D：小中学生",
    "小中学生（割引）": "D：小中学生",
    "小中学生（無料）": "D：小中学生",
    "身障者": "E：身障者",
    "招待券": "F：招待券",
    "その他": "Z：その他"
}

DISCOUNT_LIST = [
    "-", "HP", "優待割引", "特別優待割引", "JAF", "朝日友の会", 
    "リロクラブ", "奈良ファンクラブ", "アートフェスタ", "団体", 
    "その他", "コンサート", "まほろばパス"
]

GOODS_LIST = {
    "作品選": "Q：図録",
    "長谷川潔・駒井哲郎": "Q：図録",
    "村上華岳展": "Q：図録",
    "須田国太郎・鳥海青児展": "Q：図録",
    "入江波光展": "Q：図録",
    "村上華岳・須田国太郎展": "Q：図録",
    "絵葉書（＠100円）": "P：絵葉書",
    "絵葉書（＠50円）": "P：絵葉書"
}

# ==========================================
# セッションステートの初期化
# ==========================================
if 'visitors' not in st.session_state:
    st.session_state.visitors = []
if 'sales' not in st.session_state:
    st.session_state.sales = []
# 展覧会名のリストを保持（自分で追加可能に）
if 'exhibitions' not in st.session_state:
    st.session_state.exhibitions = ["1_春季展"]

st.title("🏛️ 美術館 受付システム")

# ==========================================
# 🌟 ここでタブを作成します
# ==========================================
tab_input, tab_summary = st.tabs(["📝 データ入力", "📊 月次集計表"])

# ==========================================
# タブ1：データ入力（今までのコードをここに入れます）
# ==========================================
with tab_input:
    # ==========================================
    # 基本情報エリア ＆ 展覧会名の編集機能
    # ==========================================
    date_input = st.date_input("📅 日付", datetime.date.today())

    st.markdown("**🎨 展覧会名**")
    # 既存リストからの選択
    exhibition = st.selectbox("展覧会を選択", st.session_state.exhibitions, label_visibility="collapsed")

    # 新規展覧会名の追加フォーム（折りたたみ）
    with st.expander("＋ 新しい展覧会名を作成・追加する"):
        new_exhibition = st.text_input("新しい展覧会名")
        if st.button("リストに追加"):
            if new_exhibition and new_exhibition not in st.session_state.exhibitions:
                st.session_state.exhibitions.append(new_exhibition)
                st.success(f"「{new_exhibition}」を追加しました。上のリストから選択してください。")
                st.rerun()
            elif new_exhibition in st.session_state.exhibitions:
                st.warning("既に登録されています。")

    st.divider()

    # ==========================================
    # 入館者の追加フォーム
    # ==========================================
    with st.expander("▼ 👤 入館者を追加", expanded=True):
        # UI上は「一般（割引）」などを表示し、裏で「A：一般」を紐付ける
        v_category = st.selectbox("分類", list(VISITOR_CATEGORIES.keys()))
        discount = st.selectbox("割引", DISCOUNT_LIST)
        v_count = st.number_input("人数", min_value=1, step=1, key="v_count")
        
        if st.button("＋ 入館者リストに追加", type="secondary", use_container_width=True):
            st.session_state.visitors.append({
                "code": VISITOR_CATEGORIES[v_category],
                "category": v_category,
                "discount": None if discount == "-" else discount,
                "count": v_count
            })
            st.success(f"{v_category} {v_count}人 を追加しました！")

    # ==========================================
    # 物販の追加フォーム
    # ==========================================
    with st.expander("▼ 🛍️ 物販を追加"):
        s_name = st.selectbox("品名", list(GOODS_LIST.keys()))
        s_count = st.number_input("販売数", min_value=1, step=1, key="s_count")
        
        if st.button("＋ 物販リストに追加", type="secondary", use_container_width=True):
            st.session_state.sales.append({
                "code": GOODS_LIST[s_name],
                "name": s_name,
                "count": s_count
            })
            st.success(f"{s_name} {s_count}個 を追加しました！")

    st.divider()

    # ==========================================
    # 本日の入力内容（確認・削除エリア）
    # ==========================================
    st.subheader("📋 本日の入力リスト")

    # 入館者リストの表示
    st.markdown("**👤 入館者**")
    if st.session_state.visitors:
        for i, v in enumerate(st.session_state.visitors):
            col_text, col_btn = st.columns([4, 1])
            with col_text:
                disc_text = v['discount'] if v['discount'] else "-"
                st.write(f"・{v['category']} | 割引: {disc_text} | **{v['count']}人**")
            with col_btn:
                if st.button("❌", key=f"del_v_{i}"):
                    st.session_state.visitors.pop(i)
                    st.rerun()
    else:
        st.info("まだ入力されていません")

    # 物販リストの表示
    st.markdown("**🛍️ 物販**")
    if st.session_state.sales:
        for i, s in enumerate(st.session_state.sales):
            col_text, col_btn = st.columns([4, 1])
            with col_text:
                st.write(f"・{s['name']} | **{s['count']}個**")
            with col_btn:
                if st.button("❌", key=f"del_s_{i}"):
                    st.session_state.sales.pop(i)
                    st.rerun()
    else:
        st.info("まだ入力されていません")

    st.divider()

    # ==========================================
    # 送信（JSONとして保存）
    # ==========================================
    if st.button("📥 1日分のデータを確定して送信", type="primary", use_container_width=True):
        if not st.session_state.visitors and not st.session_state.sales:
            st.warning("送信するデータがありません。")
        else:
            output_data = {
                "date": str(date_input),
                "exhibition": exhibition,
                "visitors": st.session_state.visitors,
                "sales": st.session_state.sales
            }
            
            st.success(f"{date_input} のデータを保存しました！")
            st.json(output_data)

    # ==========================================
    # ダウンロード機能（JSON ＆ CSV の両方を出力）
    # ==========================================
    if not st.session_state.visitors and not st.session_state.sales:
        st.warning("ダウンロードするデータがありません。")
    else:
        st.markdown("### 💾 データのダウンロード")
        st.write("用途に合わせてお好きな形式でダウンロードしてください。")
        
        # 横に3つボタンを並べるためのカラム
        col1, col2, col3 = st.columns(3)

        # ----------------------------------
        # 1. JSONデータの準備（既存の自動化スクリプト用）
        # ----------------------------------
        output_data = [{
            "date": str(date_input),
            "day_of_week": ["月", "火", "水", "木", "金", "土", "日"][date_input.weekday()],
            "weather": "", 
            "staff": [],   
            "exhibition": exhibition,
            "notes": {"am": None, "pm": None},
            "visitors": st.session_state.visitors,
            "visitors_total": sum(v['count'] for v in st.session_state.visitors),
            "cumulative_excluding_free": 0, 
            "cumulative_including_free": 0, 
            "sales": st.session_state.sales
        }]
        json_str = json.dumps(output_data, ensure_ascii=False, indent=2)
        filename_json = f"manual_{date_input.strftime('%Y%m%d')}.json"

        with col1:
            st.download_button(
                label=" JSONをダウンロード\n(自動化スクリプト用)",
                data=json_str,
                file_name=filename_json,
                mime="application/json",
                type="primary",
                use_container_width=True
            )

        # ----------------------------------
        # 2. 入館者CSVの準備（Excel手動確認用）
        # ----------------------------------
        if st.session_state.visitors:
            df_v = pd.DataFrame(st.session_state.visitors)
            # Excelの列構成に合わせてデータを整形
            df_v.insert(0, "日付", str(date_input))
            df_v.insert(1, "展覧会名", exhibition)
            df_v = df_v.rename(columns={
                "code": "入館者コード", 
                "category": "分類", 
                "discount": "割引リスト", 
                "count": "入場者数"
            })
            # Excelで文字化けしないように utf-8-sig を使用
            csv_v = df_v.to_csv(index=False).encode('utf-8-sig')
            filename_csv_v = f"visitors_{date_input.strftime('%Y%m%d')}.csv"
            
            with col2:
                st.download_button(
                    label="📊 入館者CSV\n(Excel確認・手動用)",
                    data=csv_v,
                    file_name=filename_csv_v,
                    mime="text/csv",
                    use_container_width=True
                )
        else:
            with col2:
                st.button("📊 入館者CSV\n(データなし)", disabled=True, use_container_width=True)

        # ----------------------------------
        # 3. 物販CSVの準備（Excel手動確認用）
        # ----------------------------------
        if st.session_state.sales:
            df_s = pd.DataFrame(st.session_state.sales)
            # Excelの列構成に合わせてデータを整形
            df_s.insert(0, "日付", str(date_input))
            df_s.insert(1, "展覧会名", exhibition)
            df_s = df_s.rename(columns={
                "code": "図版コード", 
                "name": "図録・絵葉書", 
                "count": "販売数"
            })
            csv_s = df_s.to_csv(index=False).encode('utf-8-sig')
            filename_csv_s = f"sales_{date_input.strftime('%Y%m%d')}.csv"
            
            with col3:
                st.download_button(
                    label="🛍️ 物販CSV\n(Excel確認・手動用)",
                    data=csv_s,
                    file_name=filename_csv_s,
                    mime="text/csv",
                    use_container_width=True
                )
        else:
            with col3:
                st.button("🛍️ 物販CSV\n(データなし)", disabled=True, use_container_width=True)


# ==========================================
# タブ2：月次集計表（R8様式 完全再現）
# ==========================================
with tab_summary:
    st.markdown("### 📊 月次集計表（R8様式）")
    st.write("ダウンロードした「入館者CSV」や、マスターの「visitors.xlsx」をアップロードしてください。")
    
    # ファイルアップロード
    uploaded_file = st.file_uploader("入館者データをアップロード", type=["csv", "xlsx"])
    
    if uploaded_file is not None:
        try:
            # CSVかExcelかで読み込み方を変える
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            
            # --- R8入力シートの形式に変換する処理 ---
            # 「入館者コード」（例：A：一般）から、「一般」などの文字だけを取り出す
            target_col = "入館者コード" if "入館者コード" in df.columns else "分類"
            
            if target_col in df.columns and "入場者数" in df.columns and "日付" in df.columns:
                if "展覧会名" not in df.columns:
                    df["展覧会名"] = "-"
                    
                # 「A：一般」を「一般」に分割
                df['主分類'] = df[target_col].astype(str).str.split('：').str[-1]
                
                # Excelの列名にマッピング（要件定義書のマスターデータに準拠）
                col_map = {
                    '一般': '一般',
                    'シニア': 'シニア',
                    '身障者': '身障',
                    '招待券': '招待',
                    '学生': '高・大生',
                    '小中学生': '小・中生'
                }
                df['列名'] = df['主分類'].map(col_map).fillna('その他')
                
                # 日付 × 列名 でクロス集計（ピボットテーブル）
                pivot_df = pd.pivot_table(
                    df,
                    index=['日付', '展覧会名'], 
                    columns='列名', 
                    values='入場者数', 
                    aggfunc='sum'
                ).reset_index()
                
                # 誰も来なかった分類の列も表示されるように確保
                for c in ['一般', 'シニア', '身障', '招待', '高・大生', '小・中生']:
                    if c not in pivot_df.columns:
                        pivot_df[c] = float('nan')
                        
                # 小計と合計の計算
                pivot_df['一般　　小計'] = pivot_df[['一般', 'シニア', '身障', '招待']].sum(axis=1)
                pivot_df['計'] = pivot_df[['一般　　小計', '高・大生', '小・中生']].sum(axis=1)
                
                # 日付順に並び替え
                pivot_df = pivot_df.sort_values('日付')
                
                # 累計の計算
                pivot_df['累計'] = pivot_df['計'].cumsum()
                
                # 日数の計算（データがある行を1日としてカウント）
                pivot_df['日数'] = 1
                
                # 列の並び替え（アップロードいただいたR8入力シートと完全に一致させます）
                final_cols = ['日付', '展覧会名', '一般', 'シニア', '身障', '招待', '一般　　小計', '高・大生', '小・中生', '計', '累計', '日数']
                
                # 存在する列だけを抽出（万が一「その他」などがあれば除外）
                pivot_df = pivot_df[[c for c in final_cols if c in pivot_df.columns]]
                
                st.success("✨ R8形式の集計表を作成しました！")
                
                # DataFrameの表示（NaNは空白にして、小数点以下を非表示にするとExcelそっくりになります）
                st.dataframe(
                    pivot_df.style.format(na_rep="", precision=0), 
                    use_container_width=True, 
                    hide_index=True
                )
                
                # 折れ線グラフで累計推移を表示するオマケ
                st.markdown("#### 📈 累計入館者数の推移")
                st.line_chart(pivot_df, x="日付", y="累計")
                
            else:
                st.error("アップロードされたファイルに「日付」「入場者数」「入館者コード（または分類）」の列が見つかりません。")
                
        except Exception as e:
            st.error(f"ファイルの読み込みに失敗しました: {e}")