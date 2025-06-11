import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

with st.spinner("⏳ Waking up the app, please wait..."):
    time.sleep(2)  # Simulate loading time

# === Load Data ===
@st.cache_data
def load_data():
    df = pd.read_excel("Data.xlsx")
    columns_to_drop = ["Previous_Month_Price", "Price_Change", "Fact_ID"]
    df = df.drop(columns=columns_to_drop)
    df = df[df['Group_Name_x'] != "APPLE_BB"]
    df = df[df['Product_ID'].isin(df['Product_ID'].value_counts()[lambda x: x > 2].index)]

    # Manual override for main group categories
    def map_main_group(name):
        if isinstance(name, str):
            name_upper = name.upper()
            if name_upper.startswith("PC_"):
                return "PC"
            elif name_upper.startswith("BB_"):
                return "BB"
            elif "SMARTPHONE" in name_upper:
                return "SMARTPHONE"
            elif "TABLET" in name_upper:
                return "TABLET"
            else:
                return name.split()[0]
        return name

    df["Main_Group"] = df["Group_Name_x"].apply(map_main_group)
    return df

assets = load_data()

# === Sidebar UI ===
st.sidebar.header("📂 Asset Filter")

main_group = st.sidebar.selectbox("Main Group", sorted(assets['Main_Group'].dropna().unique()))

# Subcategory (with 'All' option)
subcategory_options = sorted(assets[assets["Main_Group"] == main_group]["Group_Name_x"].dropna().unique())
subcategory_options = ["All"] + subcategory_options
group = st.sidebar.selectbox("Subcategory", subcategory_options)

# Filter by Main Group and optionally Subcategory
if group != "All":
    group_filtered_assets = assets[assets["Group_Name_x"] == group]
else:
    group_filtered_assets = assets[assets["Main_Group"] == main_group]

# Brand dropdown even if Subcategory is 'All'
brand_options = sorted(group_filtered_assets["Brand_x"].dropna().unique())
brand = st.sidebar.selectbox("Brand", brand_options)

# Filter by Brand
filtered_assets = group_filtered_assets[group_filtered_assets["Brand_x"] == brand]

# Filter by year
start_year = st.sidebar.number_input("Start Year", min_value=2000, max_value=2100, value=2019)
end_year = st.sidebar.number_input("End Year", min_value=2000, max_value=2100, value=2025)
filtered_assets = filtered_assets[filtered_assets['Year_Available'].between(start_year, end_year)]

# Product dropdown comes first
product_options = sorted(filtered_assets["Product_Name_x"].dropna().unique())
product = st.sidebar.selectbox("Product", product_options) if product_options else None

# Narrow to selected product
if product:
    matching_assets = filtered_assets[filtered_assets["Product_Name_x"] == product]
else:
    matching_assets = pd.DataFrame()

# Optional specification filters after product selection
screen = class_ = generation = 'All'
if not matching_assets.empty and main_group in ["SMARTPHONE", "TABLET", "PC", "BB", "Laptop"]:
    screen_options = matching_assets['Screen_Size'].dropna().unique()
    if len(screen_options) > 0:
        screen = st.sidebar.selectbox("Screen Size (Optional)", ['All'] + sorted(screen_options))

    class_options = matching_assets['Class'].dropna().unique()
    if len(class_options) > 0:
        class_ = st.sidebar.selectbox("Class (Optional)", ['All'] + sorted(class_options))

    gen_options = matching_assets['Gen'].dropna().unique()
    if len(gen_options) > 0:
        generation = st.sidebar.selectbox("Generation (Optional)", ['All'] + sorted(gen_options))

    storage_options = matching_assets['Storage'].dropna().unique()
    if len(storage_options) > 0:
        storage = st.sidebar.selectbox("Storage", ['All'] + sorted(storage_options))
    else:
        storage = 'N/A'
else:
    storage = 'N/A'

# Apply filters to matching_assets
if screen != "All":
    matching_assets = matching_assets[matching_assets["Screen_Size"] == screen]
if class_ != "All":
    matching_assets = matching_assets[matching_assets["Class"] == class_]
if generation != "All":
    matching_assets = matching_assets[matching_assets["Gen"] == generation]
if storage != "All" and storage != "N/A":
    matching_assets = matching_assets[matching_assets["Storage"] == storage]

# === Main Section ===
st.title("\U0001F4C8 Long Term Asset Depreciation")

orig_price = st.number_input("Original Price (NOK)", value=10000.0)
release_date_str = st.text_input("Release Date (YYYY-MM)", value="2021-01")

# Risk Analysis Inputs
st.subheader("\U0001F4CA Historical Customer Category Returns")
risk_analysis_a = st.number_input("Grade A %", value=0.25)
risk_analysis_b = st.number_input("Grade B %", value=0.25)
risk_analysis_c = st.number_input("Grade C %", value=0.25)
risk_analysis_d = st.number_input("Grade D %", value=0.25)

if st.button("Run Depreciation Forecast"):
    try:
        release_date = datetime.strptime(release_date_str, "%Y-%m")
        df = matching_assets.copy()
        if storage != "N/A":
            df = df[df["Storage"] == storage]

        df["Date"] = pd.to_datetime(df[["Year", "Month"]].assign(DAY=1))
        df = df[df["Date"] >= release_date].sort_values("Date")

        if df.empty:
            st.warning("⚠️ No records after selected release date.")
        else:
            df["Original_Price"] = orig_price
            df["Depreciation_NOK"] = orig_price - df["Current_Month_Price"]
            df["Depreciation_%"] = 100 * df["Depreciation_NOK"] / orig_price
            df["Months_Since_Release"] = (
                (df["Date"].dt.year - release_date.year) * 12 +
                (df["Date"].dt.month - release_date.month)
            )

            # Normalize weights
            total_weight = risk_analysis_a + risk_analysis_b + risk_analysis_c + risk_analysis_d
            a = risk_analysis_a / total_weight
            b = risk_analysis_b / total_weight
            c = risk_analysis_c / total_weight
            d = risk_analysis_d / total_weight

            # Scenario multipliers
            a_factor = 0.90
            b_factor = 0.75
            c_factor = 0.60
            d_factor = 0.0

            # Expected Case
            df["Expected_Residual"] = df["Current_Month_Price"] * (a * a_factor + b * b_factor + c * c_factor + d * d_factor)

            # Best Case (favor A/B more)
            a_b = a + 0.1
            b_b = b + 0.05
            c_b = max(c - 0.075, 0)
            d_b = max(d - 0.075, 0)
            total_b = a_b + b_b + c_b + d_b
            a_b /= total_b
            b_b /= total_b
            c_b /= total_b
            d_b /= total_b
            df["Best_Case"] = df["Current_Month_Price"] * (a_b * a_factor + b_b * b_factor + c_b * c_factor + d_b * d_factor)

            # Worst Case (favor C/D more)
            a_w = max(a - 0.075, 0)
            b_w = max(b - 0.075, 0)
            c_w = c + 0.05
            d_w = d + 0.1
            total_w = a_w + b_w + c_w + d_w
            a_w /= total_w
            b_w /= total_w
            c_w /= total_w
            d_w /= total_w
            df["Worst_Case"] = df["Current_Month_Price"] * (a_w * a_factor + b_w * b_factor + c_w * c_factor + d_w * d_factor)

            # Residual Percent
            df["Expected_%"] = 100 * (df["Expected_Residual"] / orig_price)
            df["Best_%"] = 100 * (df["Best_Case"] / orig_price)
            df["Worst_%"] = 100 * (df["Worst_Case"] / orig_price)

            st.subheader("📄 Depreciation Table")
            df["Year-Month"] = df["Date"].dt.strftime("%Y-%m")
            depreciation_table = df[["Year-Month", "Months_Since_Release", "Current_Month_Price", "Depreciation_%", "Depreciation_NOK"]].round(2)
            st.dataframe(depreciation_table)

            st.subheader("📊 Residual Scenarios Table")
            scenario_df = df[[
                "Months_Since_Release",
                "Current_Month_Price",
                "Expected_%",
                "Best_%",
                "Worst_%"
            ]].rename(columns={
                "Current_Month_Price": "Actual Asset Value (INREGO)",
                "Expected_%": "Expected Risk",
                "Best_%": "Full Damage Billing",
                "Worst_%": "Medium Damage Billing"
            }).round(2)
            st.dataframe(scenario_df)

            # Scenario Forecasts Graph
            st.subheader("📈 Residual Recommendations by Month")
            fig3 = px.line(df, x="Months_Since_Release", y=["Expected_%", "Best_%", "Worst_%"],
                           title="Residual Scenario Forecasts (%)", markers=True)
            fig3.update_layout(xaxis_title="Months Since Release", yaxis_title="Residual %")
            st.plotly_chart(fig3)

            # Lorenz-style Depreciation Curve
            st.subheader("📉 Marginal Cumulative Rate of Depreciation (Lorenz-style)")
            df_lorenz = df.sort_values("Months_Since_Release").copy()
            df_lorenz["Cumulative_Depreciation"] = df_lorenz["Depreciation_NOK"].cumsum()
            df_lorenz["Cumulative_Depreciation_%"] = 100 * df_lorenz["Cumulative_Depreciation"] / df_lorenz["Depreciation_NOK"].sum()
            df_lorenz["Cumulative_Months_%"] = 100 * (
                df_lorenz["Months_Since_Release"] - df_lorenz["Months_Since_Release"].min()
            ) / (df_lorenz["Months_Since_Release"].max() - df_lorenz["Months_Since_Release"].min())

            fig_lorenz = px.line(df_lorenz, x="Cumulative_Months_%", y="Cumulative_Depreciation_%",
                                 title="Lorenz-Style Curve of Depreciation",
                                 labels={
                                     "Cumulative_Months_%": "Cumulative Time (%)",
                                     "Cumulative_Depreciation_%": "Cumulative Depreciation (%)"
                                 },
                                 markers=True)
            fig_lorenz.add_shape(
                type='line', x0=0, y0=0, x1=100, y1=100,
                line=dict(dash='dash', color='gray'),
            )
            fig_lorenz.update_layout(xaxis=dict(ticksuffix="%"), yaxis=dict(ticksuffix="%"))
            st.plotly_chart(fig_lorenz)

    except ValueError:
        st.error("❌ Invalid date format. Please use YYYY-MM.")



