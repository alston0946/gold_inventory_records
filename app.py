import streamlit as st
import pandas as pd
import os
from datetime import date

st.set_page_config(page_title="黄金平均成本计算", layout="wide")

DATA_FILE = "gold_inventory_records.csv"

# =========================
# 数据读写
# =========================
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            df = pd.read_csv(DATA_FILE)
            if not df.empty:
                return df
        except:
            pass
    return pd.DataFrame(columns=["id", "进货日期", "克重(g)", "单价(元/g)", "总成本(元)"])


def save_data(df):
    df.to_csv(DATA_FILE, index=False, encoding="utf-8-sig")


# =========================
# 初始化 session_state
# =========================
if "df" not in st.session_state:
    st.session_state.df = load_data()

df = st.session_state.df

# =========================
# 标题
# =========================
st.title("黄金平均成本计算工具")
st.caption("按每次进货记录自动计算当前所有黄金的加权平均成本")

# =========================
# 添加记录区域
# =========================
with st.form("add_record_form", clear_on_submit=True):
    st.subheader("新增进货记录")

    col1, col2, col3 = st.columns(3)

    with col1:
        purchase_date = st.date_input("进货日期", value=date.today())

    with col2:
        weight = st.number_input("克重 (g)", min_value=0.0001, value=20.0, step=0.1, format="%.4f")

    with col3:
        unit_price = st.number_input("单价 (元/g)", min_value=0.0001, value=1000.0, step=1.0, format="%.4f")

    submitted = st.form_submit_button("保存记录")

    if submitted:
        total_cost = weight * unit_price

        new_id = 1 if df.empty else int(df["id"].max()) + 1

        new_row = pd.DataFrame([{
            "id": new_id,
            "进货日期": str(purchase_date),
            "克重(g)": float(weight),
            "单价(元/g)": float(unit_price),
            "总成本(元)": float(total_cost)
        }])

        st.session_state.df = pd.concat([df, new_row], ignore_index=True)
        save_data(st.session_state.df)
        st.success("记录已保存")
        st.rerun()

# 重新取最新 df
df = st.session_state.df

# =========================
# 汇总计算
# =========================
st.subheader("当前库存平均成本")

if not df.empty:
    total_weight = df["克重(g)"].sum()
    total_cost = df["总成本(元)"].sum()
    avg_price = total_cost / total_weight if total_weight > 0 else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("总克重", f"{total_weight:,.4f} g")
    c2.metric("总成本", f"¥ {total_cost:,.2f}")
    c3.metric("平均成本", f"¥ {avg_price:,.4f} /g")

    with st.expander("查看计算过程", expanded=False):
        st.write("平均成本 = 所有进货总成本 ÷ 所有进货总克重")
        st.write(f"总成本 = ¥ {total_cost:,.2f}")
        st.write(f"总克重 = {total_weight:,.4f} g")
        st.write(f"平均成本 = {total_cost:,.2f} ÷ {total_weight:,.4f} = ¥ {avg_price:,.4f} /g")
else:
    st.info("当前还没有任何进货记录，请先添加。")

# =========================
# 历史记录展示
# =========================
st.subheader("进货记录")

if not df.empty:
    show_df = df.copy()
    show_df["克重(g)"] = show_df["克重(g)"].map(lambda x: f"{x:,.4f}")
    show_df["单价(元/g)"] = show_df["单价(元/g)"].map(lambda x: f"{x:,.4f}")
    show_df["总成本(元)"] = show_df["总成本(元)"].map(lambda x: f"{x:,.2f}")

    st.dataframe(show_df, use_container_width=True)

    st.markdown("---")
    st.subheader("删除单条记录")

    raw_df = st.session_state.df.copy()
    options = [
        f"ID {row['id']} | 日期: {row['进货日期']} | 克重: {row['克重(g)']:.4f}g | 单价: ¥{row['单价(元/g)']:.4f}/g"
        for _, row in raw_df.iterrows()
    ]

    selected_option = st.selectbox("选择要删除的记录", options)

    if st.button("删除选中记录"):
        selected_id = int(selected_option.split("|")[0].replace("ID", "").strip())
        st.session_state.df = raw_df[raw_df["id"] != selected_id].reset_index(drop=True)
        save_data(st.session_state.df)
        st.success(f"已删除 ID {selected_id} 的记录")
        st.rerun()

    st.markdown("---")
    col_a, col_b = st.columns(2)

    with col_a:
        csv = st.session_state.df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button(
            label="导出 CSV",
            data=csv,
            file_name="gold_inventory_records.csv",
            mime="text/csv"
        )

    with col_b:
        if st.button("清空全部记录"):
            st.session_state.df = pd.DataFrame(columns=["id", "进货日期", "克重(g)", "单价(元/g)", "总成本(元)"])
            save_data(st.session_state.df)
            st.warning("全部记录已清空")
            st.rerun()
else:
    st.info("暂无历史记录。")