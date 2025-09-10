import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import time

# === Spinner to simulate loading ===
with st.spinner("Waking up the app, please wait..."):
    time.sleep(2)

# === Load and clean data ===
@st.cache_data
def load_data():
    df = pd.read_excel("Data.xlsx")
    df.columns = df.columns.str.strip()

    # Drop optional columns if they exist
    columns_to_drop = ["Previous_Month_Price", "Price_Change", "Fact_ID"]
    df = df.drop(columns=[col for col in columns_to_drop if col in df.columns], errors="ignore")

    # Ensure required columns exist
    required_cols = ["Group_Name", "Brand", "Product_ID"]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        st.error(f"❌ Missing required columns in Data.xlsx: {missing}")
        st.stop()

    # Filter unwanted records
    df = df[df["Group_Name"] != "APPLE_BB"]
    df = df[df["Product_ID"].isin(df["Product_ID"].value_counts()[lambda x: x > 2].index)]

    # Add Main_Group column
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
            elif "LAPTOP" in name_upper:
                return "Laptop"
            else:
                return name.split()[0]
        return name

    df["Main_Group"] = df["Group_Name"].apply(map_main_group)
    return df

assets = load_data()

# === Sidebar Filters ===
st.sidebar.header("📂 Asset Filter")

main_group = st.sidebar.selectbox("Main Group", sorted(assets['Main_Group'].dropna().unique()))

# Subcategory
subcategory_options = sorted(assets[assets["Main_Group"] == main_group]["Group_Name"].dropna().unique())
subcategory_options = ["All"] + subcategory_options
group = st.sidebar.selectbox("Subcategory", subcategory_options)

if group != "All":
    group_filtered_assets = assets[assets["Group_Name"] == group]
else:
    group_filtered_assets = assets[assets["Main_Group"] == main_group]

# Brand
brand_options = sorted(group_filtered_assets["Brand"].dropna().unique())
brand = st.sidebar.selectbox("Brand", brand_options)
filtered_assets = group_filtered_assets[group_filtered_assets["Brand"] == brand]

# Year filter
start_year = st.sidebar.number_input("Start Year", min_value=2000, max_value=2100, value=2019)
end_year = st.sidebar.number_input("End Year", min_value=2000, max_value=2100, value=2025)
filtered_assets = filtered_assets[filtered_assets['Year Available'].between(start_year, end_year)]

# Product selection
product_options = sorted(filtered_assets["Product_Name"].dropna().unique())
product = st.sidebar.selectbox("Product", product_options) if product_options else None

if product:
    matching_assets = filtered_assets[filtered_assets["Product_Name"] == product]
else:
    matching_assets = pd.DataFrame()

# Optional filters (Screen size, Class, Gen, Storage)
screen = class_ = generation = storage = 'All'
if not matching_assets.empty and main_group in ["SMARTPHONE", "TABLET", "PC", "BB", "Laptop"]:
    if "Screen_Size" in matching_assets.columns:
        options = matching_assets["Screen_Size"].dropna().unique()
        if len(options) > 0:
            screen = st.sidebar.selectbox("Screen Size", ["All"] + sorted(options.astype(str)))

    if "Class" in matching_assets.columns:
        options = matching_assets["Class"].dropna().unique()
        if len(options) > 0:
            class_ = st.sidebar.selectbox("Class", ["All"] + sorted(options.astype(str)))

    if "Gen" in matching_assets.columns:
        options = matching_assets["Gen"].dropna().unique()
        if len(options) > 0:
            generation = st.sidebar.selectbox("Generation", ["All"] + sorted(options.astype(str)))

    if "Storage" in matching_assets.columns:
        options = matching_assets["Storage"].dropna().unique()
        if len(options) > 0:
            storage = st.sidebar.selectbox("Storage", ["All"] + sorted(options.astype(str)))

# Apply filters
if screen != "All":
    matching_assets = matching_assets[matching_assets["Screen_Size"].astype(str) == screen]
if class_ != "All":
    matching_assets = matching_assets[matching_assets["Class"].astype(str) == class_]
if generation != "All":
    matching_assets = matching_assets[matching_assets["Gen"].astype(str) == generation]
if storage != "All":
    matching_assets = matching_assets[matching_assets["Storage"].astype(str) == storage]

# === Main Content ===
st.title("📉 Long Term Asset Depreciation Forecast")

orig_price = st.number_input("Original Price (NOK)", value=10000.0)
release_date_str = st.text_input("Release Date (YYYY-MM)", value="2025-04")

st.subheader("📊 Historical Risk Weighting")
risk_a = st.number_input("Grade A %", value=0.25)
risk_b = st.number_input("Grade B %", value=0.25)
risk_c = st.number_input("Grade C %", value=0.25)
risk_d = st.number_input("Grade D %", value=0.25)

if st.button("Run Forecast"):
    try:
        release_date = datetime.strptime(release_date_str, "%Y-%m")
        df = matching_assets.copy()
        df["Date"] = pd.to_datetime(df[["Year", "Month"]].assign(DAY=1))
        df = df[df["Date"] >= release_date].sort_values("Date")

        if df.empty:
            st.warning("No records found after the release date.")
        else:
            df["Original_Price"] = orig_price
            df["Depreciation_NOK"] = orig_price - df["Current_Month_Price"]
            df["Depreciation_%"] = 100 * df["Depreciation_NOK"] / orig_price
            df["Months_Since_Release"] = (
                (df["Date"].dt.year - release_date.year) * 12 +
                (df["Date"].dt.month - release_date.month)
            )

            # Normalize risk weights
            total = risk_a + risk_b + risk_c + risk_d
            a, b, c, d = [x / total for x in [risk_a, risk_b, risk_c, risk_d]]
            factors = {'A': 0.90, 'B': 0.75, 'C': 0.60, 'D': 0.0}

            # Expected case
            df["Expected"] = df["Current_Month_Price"] * (a*factors['A'] + b*factors['B'] + c*factors['C'] + d*factors['D'])

            # Visualization
            st.subheader("📉 Depreciation Table")
            st.dataframe(df[["Date", "Current_Month_Price", "Depreciation_%", "Expected"]].round(2))

            fig = px.line(df, x="Months_Since_Release", y=["Current_Month_Price", "Expected"], markers=True)
            st.plotly_chart(fig)

    except ValueError:
        st.error("Invalid date format. Use YYYY-MM.")
