# Dashboard.py

import streamlit as st
import pandas as pd
import os

# Import your other two modules
import analyzer
import fund_model

# ─── 1) st.set_page_config must come first ─────────────────────────────────────
st.set_page_config(
    page_title="Formula Venture Dashboard",
    layout="wide",
)

# ─── 2) Sidebar + Navigation ─────────────────────────────────────────────────
st.sidebar.image("Formula Venture Logo.png", use_container_width=True)

st.sidebar.title("📂 Formula Venture Dashboard")

page = st.sidebar.radio(
    "Go to",
    ["🏠 Home", "🦄 Unicorn Analyzer", "📊 Fund Model Simulator"],
)

# ─── 3) Route your pages ───────────────────────────────────────────────────────
if page == "🏠 Home":
    # ————————— Home Page Header —————————
    st.markdown(
        "<h1 style='text-align: center;'>🏁 Welcome to Formula Venture Dashboard</h1>",
        unsafe_allow_html=True,
    )
    st.write("Use the sidebar to navigate between modules.")

    # ───────────── 3.1) Load & Merge Unicorn Data ──────────────────────────────
    SHEET_URL = (
        "https://docs.google.com/spreadsheets/d/e/"
        "2PACX-1vQZDRRKispN6WmiiOKW0G1TBVt21_I-6QbO-rSbiCJrT-rU_UnVohI87LzzTDSPfdUcomDVcb61mJhb/"
        "pub?gid=2128528272&single=true&output=csv"
    )
    ADDITIONAL_SHEET_URL = (
        "https://docs.google.com/spreadsheets/d/e/"
        "2PACX-1vQZDRRKispN6WmiiOKW0G1TBVt21_I-6QbO-rSbiCJrT-rU_UnVohI87LzzTDSPfdUcomDVcb61mJhb/"
        "pub?gid=1650893883&single=true&output=csv"
    )

    @st.cache_data
    def load_data(url):
        df = pd.read_csv(url)
        df["Post Money Value"] = pd.to_numeric(df["Post Money Value"], errors="coerce")
        df["Total Equity Funding"] = pd.to_numeric(df["Total Equity Funding"], errors="coerce")
        df["Quarter"] = df["Quarter"].astype(str)
        df["Company"] = df["Company"].astype(str)
        return df

    @st.cache_data
    def load_additional_data(url):
        df_extra = pd.read_csv(url)
        df_extra.rename(columns={"Organization Name": "Company"}, inplace=True)
        df_extra["Company"] = df_extra["Company"].astype(str)
        return df_extra

    df = load_data(SHEET_URL)
    df_extra = load_additional_data(ADDITIONAL_SHEET_URL)
    df_full = pd.merge(df, df_extra, on="Company", how="left")
    st.write("ℹ️ df_full shape:", df_full.shape)

    # ───────────── 3.2) Formatting helpers ──────────────────────────────────────
    def format_billions(val):
        if pd.isnull(val):
            return "—"
        return f"${val:.1f}B"

    def format_multiple(val):
        if pd.isnull(val) or val == float("inf") or val == 0:
            return "—"
        return f"{val:.2f}x"

    # ───────────── 3.3) Unicorn Tracker & Analyzer UI ──────────────────────────
    st.title("🦄 Unicorns Tracker & Analyzer")

    # --- Quarter Selection ---
    quarters = sorted(
        df_full["Quarter"].unique(),
        key=lambda x: (int(x.split()[1]), int(x.split()[0][1:])),
    )
    quarter = st.selectbox("Select Quarter", quarters, index=len(quarters) - 1)
    filtered = df_full[df_full["Quarter"] == quarter]

    # --- Summary Metrics ---
    st.header(f"Unicorns for {quarter}")
    col1, col2 = st.columns(2)
    col1.metric("Total Unicorns", len(filtered))
    col2.metric("Total Valuation", format_billions(filtered["Post Money Value"].sum()))

    # --- Main Unicorn Table (Expanded Columns) ---
    main_table = filtered[[
        "Company", "Post Money Value", "Total Funding Amount", "Last Equity Funding Type",
        "Top 5 Investors", "Industries", "Country", "Continent",
        "Headquarters Location", "Number of Employees", "Funding Status",
        "Number of Funding Rounds", "Monthly Visits"
    ]].copy()

    main_table = main_table.sort_values("Post Money Value", ascending=False)
    main_table["Post Money Value"] = main_table["Post Money Value"].apply(format_billions)
    main_table["Total Funding Amount"] = main_table["Total Funding Amount"].apply(
        lambda x: format_billions(x / 1e9) if pd.notnull(x) else "—"
    )
    main_table["Monthly Visits"] = main_table["Monthly Visits"].apply(
        lambda x: f"{int(str(x).replace(',', '')):,}" if pd.notnull(x) and str(x).replace(",", "").isdigit() else "—"
    )

    st.dataframe(main_table, height=400, width=1000)

    # --- Valuation Trend Chart ---
    st.header("Valuation Trend for a Unicorn (Q4 2024 → Q2 2025)")
    companies = sorted(df_full["Company"].drop_duplicates())
    company_choice = st.selectbox("Select Company", companies)

    desired_quarters = ["Q4 2024", "Q1 2025", "Q2 2025"]
    trend_df = df_full[
        (df_full["Company"] == company_choice) & (df_full["Quarter"].isin(desired_quarters))
    ].copy()
    trend_df["Quarter"] = pd.Categorical(trend_df["Quarter"], categories=desired_quarters, ordered=True)
    trend_df = trend_df.sort_values("Quarter")

    if trend_df.empty:
        st.info("No data available for this unicorn in Q4 2024 to Q2 2025.")
    else:
        chart_data = trend_df.set_index("Quarter")["Post Money Value"]
        st.line_chart(chart_data)

    # --- Risers & Fallers Between Quarters ---
    st.header("All Movers Between Quarters")
    q1, q2 = st.columns(2)
    quarter1 = q1.selectbox("Compare From", quarters, index=max(0, len(quarters) - 2), key="q1")
    quarter2 = q2.selectbox("Compare To", quarters, index=len(quarters) - 1, key="q2")

    from_df = df_full[df_full["Quarter"] == quarter1][["Company", "Post Money Value"]].rename(columns={"Post Money Value": "Value_From"})
    to_df = df_full[df_full["Quarter"] == quarter2][["Company", "Post Money Value"]].rename(columns={"Post Money Value": "Value_To"})
    comp = pd.merge(from_df, to_df, on="Company", how="outer")
    comp["Change_$B"] = comp["Value_To"] - comp["Value_From"]
    comp["Multiple"] = comp["Value_To"] / comp["Value_From"]

    risers = comp[comp["Change_$B"] > 0].sort_values("Change_$B", ascending=False).copy()
    fallers = comp[comp["Change_$B"] < 0].sort_values("Change_$B").copy()

    for group in [risers, fallers]:
        group["Value_From_fmt"] = group["Value_From"].apply(format_billions)
        group["Value_To_fmt"] = group["Value_To"].apply(format_billions)
        group["Change_$B_fmt"] = group["Change_$B"].apply(format_billions)
        group["Multiple_fmt"] = group["Multiple"].apply(format_multiple)

    if not risers.empty:
        st.subheader(f"All Risers ({quarter1} → {quarter2})")
        st.dataframe(
            risers[["Company", "Value_From_fmt", "Value_To_fmt", "Change_$B_fmt", "Multiple_fmt"]].rename(
                columns={
                    "Value_From_fmt": f"Valuation {quarter1}",
                    "Value_To_fmt": f"Valuation {quarter2}",
                    "Change_$B_fmt": "Change ($B)",
                    "Multiple_fmt": "Multiple",
                }
            ),
            height=400,
            width=1000,
        )
    else:
        st.info("No risers between selected quarters.")

    if not fallers.empty:
        st.subheader(f"All Fallers ({quarter1} → {quarter2})")
        st.dataframe(
            fallers[["Company", "Value_From_fmt", "Value_To_fmt", "Change_$B_fmt", "Multiple_fmt"]].rename(
                columns={
                    "Value_From_fmt": f"Valuation {quarter1}",
                    "Value_To_fmt": f"Valuation {quarter2}",
                    "Change_$B_fmt": "Change ($B)",
                    "Multiple_fmt": "Multiple",
                }
            ),
            height=400,
            width=1000,
        )
    else:
        st.info("No fallers between selected quarters.")

elif page == "🦄 Unicorn Analyzer":
    analyzer.run()
elif page == "📊 Fund Model Simulator":
    fund_model.run()
