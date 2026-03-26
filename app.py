import streamlit as st
import pandas as pd
import os
from datetime import date

st.set_page_config(page_title="黄金库存与平均成本管理", layout="wide")

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
        except Exception:
            pass

    return pd.DataFrame(columns=[
        "id",
        "类型",            # 进货 / 销售
        "日期",
        "克重(g)",
        "单价(元/g)",
        "总金额(元)",
        "备注"
    ])


def save_data(df):
    df.to_csv(DATA_FILE, index=False, encoding="utf-8-sig")


# =========================
# 计算当前库存
# 规则：
# - 进货：增加库存克重与库存总成本
# - 销售：按销售当时的平均成本出库
# =========================
def calculate_inventory_summary(df):
    if df.empty:
        return {
            "current_weight": 0.0,
            "current_cost": 0.0,
            "avg_cost": 0.0,
            "processed_df": df.copy()
        }

    work_df = df.copy()
    work_df["日期_dt"] = pd.to_datetime(work_df["日期"])
    work_df = work_df.sort_values(["日期_dt", "id"]).reset_index(drop=True)

    current_weight = 0.0
    current_cost = 0.0

    inventory_weights = []
    inventory_costs = []
    avg_costs = []
    outbound_costs = []

    for _, row in work_df.iterrows():
        record_type = row["类型"]
        weight = float(row["克重(g)"])
        unit_price = float(row["单价(元/g)"])
        amount = float(row["总金额(元)"])

        if record_type == "进货":
            current_weight += weight
            current_cost += amount
            avg_cost = current_cost / current_weight if current_weight > 0 else 0.0
            outbound_cost = 0.0

        elif record_type == "销售":
            avg_cost_before_sale = current_cost / current_weight if current_weight > 0 else 0.0
            outbound_cost = weight * avg_cost_before_sale

            current_weight -= weight
            current_cost -= outbound_cost

            if current_weight < 1e-10:
                current_weight = 0.0
                current_cost = 0.0

            avg_cost = current_cost / current_weight if current_weight > 0 else 0.0

        else:
            avg_cost = current_cost / current_weight if current_weight > 0 else 0.0
            outbound_cost = 0.0

        inventory_weights.append(current_weight)
        inventory_costs.append(current_cost)
        avg_costs.append(avg_cost)
        outbound_costs.append(outbound_cost)

    work_df["库存克重(g)"] = inventory_weights
    work_df["库存总成本(元)"] = inventory_costs
    work_df["库存平均成本(元/g)"] = avg_costs
    work_df["销售出库成本(元)"] = outbound_costs

    return {
        "current_weight": current_weight,
        "current_cost": current_cost,
        "avg_cost": current_cost / current_weight if current_weight > 0 else 0.0,
        "processed_df": work_df
    }


# =========================
# 新增记录
# =========================
def add_purchase_record(df, purchase_date, weight, unit_price, remark=""):
    new_id = 1 if df.empty else int(df["id"].max()) + 1
    total_amount = float(weight) * float(unit_price)

    new_row = pd.DataFrame([{
        "id": new_id,
        "类型": "进货",
        "日期": str(purchase_date),
        "克重(g)": float(weight),
        "单价(元/g)": float(unit_price),
        "总金额(元)": float(total_amount),
        "备注": remark
    }])

    return pd.concat([df, new_row], ignore_index=True)


def add_sale_record(df, sale_date, sale_weight, sale_unit_price, remark=""):
    # 先算销售前库存
    summary = calculate_inventory_summary(df)
    current_weight = summary["current_weight"]

    if sale_weight > current_weight:
        return None, f"销售失败：当前库存只有 {current_weight:.4f} g，不能销售 {sale_weight:.4f} g。"

    new_id = 1 if df.empty else int(df["id"].max()) + 1
    total_amount = float(sale_weight) * float(sale_unit_price)

    new_row = pd.DataFrame([{
        "id": new_id,
        "类型": "销售",
        "日期": str(sale_date),
        "克重(g)": float(sale_weight),
        "单价(元/g)": float(sale_unit_price),   # 这里是销售单价
        "总金额(元)": float(total_amount),      # 这里是销售金额
        "备注": remark
    }])

    updated_df = pd.concat([df, new_row], ignore_index=True)
    return updated_df, "销售记录已保存"


# =========================
# Session State 初始化
# =========================
if "df" not in st.session_state:
    st.session_state.df = load_data()

df = st.session_state.df

# =========================
# 标题
# =========================
st.title("黄金库存与平均成本管理工具")
st.caption("支持进货、销售出库、日期筛选、删除记录、导出 CSV")

# =========================
# 当前库存汇总
# =========================
summary = calculate_inventory_summary(df)
current_weight = summary["current_weight"]
current_cost = summary["current_cost"]
avg_cost = summary["avg_cost"]
processed_df = summary["processed_df"]

st.subheader("当前库存汇总")
m1, m2, m3 = st.columns(3)
m1.metric("当前库存克重", f"{current_weight:,.4f} g")
m2.metric("当前库存总成本", f"¥ {current_cost:,.2f}")
m3.metric("当前平均成本", f"¥ {avg_cost:,.4f} /g")

with st.expander("查看当前平均成本计算过程", expanded=False):
    st.write("当前平均成本 = 当前库存总成本 ÷ 当前库存克重")
    st.write(f"当前库存总成本 = ¥ {current_cost:,.2f}")
    st.write(f"当前库存克重 = {current_weight:,.4f} g")
    if current_weight > 0:
        st.write(f"当前平均成本 = {current_cost:,.2f} ÷ {current_weight:,.4f} = ¥ {avg_cost:,.4f} /g")
    else:
        st.write("当前没有库存，所以平均成本为 0。")

# =========================
# 录入区域
# =========================
tab1, tab2 = st.tabs(["新增进货", "销售出库"])

with tab1:
    with st.form("purchase_form", clear_on_submit=True):
        st.subheader("新增进货记录")
        c1, c2, c3, c4 = st.columns(4)

        with c1:
            purchase_date = st.date_input("进货日期", value=date.today(), key="purchase_date")

        with c2:
            purchase_weight = st.number_input(
                "进货克重 (g)", min_value=0.0001, value=20.0, step=0.1, format="%.4f", key="purchase_weight"
            )

        with c3:
            purchase_price = st.number_input(
                "进货单价 (元/g)", min_value=0.0001, value=1000.0, step=1.0, format="%.4f", key="purchase_price"
            )

        with c4:
            purchase_remark = st.text_input("备注", value="", key="purchase_remark")

        submit_purchase = st.form_submit_button("保存进货记录")

        if submit_purchase:
            st.session_state.df = add_purchase_record(
                st.session_state.df,
                purchase_date,
                purchase_weight,
                purchase_price,
                purchase_remark
            )
            save_data(st.session_state.df)
            st.success("进货记录已保存")
            st.rerun()

with tab2:
    with st.form("sale_form", clear_on_submit=True):
        st.subheader("新增销售出库记录")
        s1, s2, s3, s4 = st.columns(4)

        with s1:
            sale_date = st.date_input("销售日期", value=date.today(), key="sale_date")

        with s2:
            sale_weight = st.number_input(
                "销售克重 (g)", min_value=0.0001, value=1.0, step=0.1, format="%.4f", key="sale_weight"
            )

        with s3:
            sale_price = st.number_input(
                "销售单价 (元/g)", min_value=0.0001, value=1100.0, step=1.0, format="%.4f", key="sale_price"
            )

        with s4:
            sale_remark = st.text_input("备注", value="", key="sale_remark")

        st.info(f"当前可销售库存：{current_weight:,.4f} g")
        submit_sale = st.form_submit_button("保存销售记录")

        if submit_sale:
            updated_df, msg = add_sale_record(
                st.session_state.df,
                sale_date,
                sale_weight,
                sale_price,
                sale_remark
            )

            if updated_df is None:
                st.error(msg)
            else:
                st.session_state.df = updated_df
                save_data(st.session_state.df)
                st.success(msg)
                st.rerun()

# 重新计算
df = st.session_state.df
summary = calculate_inventory_summary(df)
processed_df = summary["processed_df"]

# =========================
# 日期筛选
# =========================
st.subheader("记录筛选")

f1, f2, f3 = st.columns(3)

if not df.empty:
    min_date = pd.to_datetime(df["日期"]).min().date()
    max_date = pd.to_datetime(df["日期"]).max().date()
else:
    min_date = date.today()
    max_date = date.today()

with f1:
    filter_start = st.date_input("开始日期", value=min_date, key="filter_start")

with f2:
    filter_end = st.date_input("结束日期", value=max_date, key="filter_end")

with f3:
    record_type_filter = st.multiselect(
        "记录类型",
        options=["进货", "销售"],
        default=["进货", "销售"]
    )

filtered_df = processed_df.copy()

if not filtered_df.empty:
    filtered_df["日期_dt"] = pd.to_datetime(filtered_df["日期"])
    filtered_df = filtered_df[
        (filtered_df["日期_dt"].dt.date >= filter_start) &
        (filtered_df["日期_dt"].dt.date <= filter_end) &
        (filtered_df["类型"].isin(record_type_filter))
    ].copy()

# =========================
# 记录表
# =========================
st.subheader("记录明细")

if not filtered_df.empty:
    display_df = filtered_df[[
        "id", "类型", "日期", "克重(g)", "单价(元/g)", "总金额(元)",
        "销售出库成本(元)", "库存克重(g)", "库存总成本(元)", "库存平均成本(元/g)", "备注"
    ]].copy()

    for col in ["克重(g)", "单价(元/g)", "总金额(元)", "销售出库成本(元)", "库存克重(g)", "库存总成本(元)", "库存平均成本(元/g)"]:
        display_df[col] = display_df[col].astype(float)

    st.dataframe(display_df, use_container_width=True)

    with st.expander("筛选结果统计", expanded=False):
        st.write(f"筛选后记录数：{len(display_df)} 条")
        purchase_df = filtered_df[filtered_df["类型"] == "进货"]
        sale_df = filtered_df[filtered_df["类型"] == "销售"]

        st.write(f"筛选后进货笔数：{len(purchase_df)}")
        st.write(f"筛选后销售笔数：{len(sale_df)}")
        st.write(f"筛选后进货总克重：{purchase_df['克重(g)'].sum():,.4f} g")
        st.write(f"筛选后销售总克重：{sale_df['克重(g)'].sum():,.4f} g")
else:
    st.info("当前筛选条件下没有记录。")

# =========================
# 删除记录
# =========================
st.subheader("删除单条记录")

if not df.empty:
    raw_processed = processed_df.sort_values(["日期_dt", "id"]).copy()

    delete_options = [
        f"ID {row['id']} | {row['类型']} | 日期: {row['日期']} | 克重: {row['克重(g)']:.4f}g | 单价: ¥{row['单价(元/g)']:.4f}/g"
        for _, row in raw_processed.iterrows()
    ]

    selected_option = st.selectbox("选择要删除的记录", delete_options)

    if st.button("删除选中记录"):
        selected_id = int(selected_option.split("|")[0].replace("ID", "").strip())
        st.session_state.df = st.session_state.df[st.session_state.df["id"] != selected_id].reset_index(drop=True)
        save_data(st.session_state.df)
        st.success(f"已删除 ID {selected_id} 的记录")
        st.rerun()
else:
    st.info("暂无可删除记录。")

# =========================
# 导出与清空
# =========================
st.subheader("数据管理")

c1, c2 = st.columns(2)

with c1:
    export_df = processed_df.drop(columns=["日期_dt"], errors="ignore").copy()
    csv_data = export_df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
    st.download_button(
        label="导出 CSV",
        data=csv_data,
        file_name="gold_inventory_records.csv",
        mime="text/csv"
    )

with c2:
    if st.button("清空全部记录"):
        st.session_state.df = pd.DataFrame(columns=[
            "id", "类型", "日期", "克重(g)", "单价(元/g)", "总金额(元)", "备注"
        ])
        save_data(st.session_state.df)
        st.warning("全部记录已清空")
        st.rerun()
