import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import os

def run():
    # App Title
    st.markdown(
        "<h1 style='text-align: center; color: #06e3fd;'>RV Investment Analyzer</h1>",
        unsafe_allow_html=True,
    )
    uploaded_file_unicorns = st.file_uploader(
        "Upload a VC Portfolio CSV for Unicorn Analysis", type=["csv"], key="unicorns"
    )
    uploaded_file_stages = st.file_uploader(
        "Upload a VC Investment Rounds CSV", type=["csv"], key="stages"
    )

    # -----------------------------------------------
    # 🦄 Unicorn Hit Rate Analyzer
    # -----------------------------------------------
    st.markdown("## 🦄 Unicorn Investment Overlap Analyzer")

    if uploaded_file_unicorns is not None:
        @st.cache_data
        def load_static_csv():
            df_unicorns = pd.read_csv(
                "/Users/octavianpievu/Desktop/python/Dashboard/data/June 25 - All Unicorns.csv",
                on_bad_lines="skip",
            )
            df_emerging = pd.read_csv(
                "/Users/octavianpievu/Desktop/python/Dashboard/data/Emerging_Unicorn_List-June_3rd_2025.csv",
                on_bad_lines="skip",
            )

            df_unicorns.columns = df_unicorns.columns.str.lower().str.strip()
            df_emerging.columns = df_emerging.columns.str.lower().str.strip()
            return df_unicorns, df_emerging

        # ✅ Load the static unicorn datasets
        df_unicorns, df_emerging = load_static_csv()

        # ✅ Read and normalize the uploaded file
        df_uploaded = pd.read_csv(uploaded_file_unicorns)
        df_uploaded.columns = df_uploaded.columns.str.lower().str.strip()

        # Normalize static datasets (though load_static_csv already did this)
        df_unicorns.columns = df_unicorns.columns.str.lower().str.strip()
        df_emerging.columns = df_emerging.columns.str.lower().str.strip()

        # Find relevant columns
        possible_columns = ["organization name", "company", "startup name", "name"]
        column_uploaded_name = next(
            (col for col in df_uploaded.columns if col in possible_columns), None
        )
        column_unicorns_name = next(
            (col for col in df_unicorns.columns if col in possible_columns), None
        )
        column_emerging_name = next(
            (col for col in df_emerging.columns if col in possible_columns), None
        )

        if not column_uploaded_name or not column_unicorns_name:
            st.error("🚨 Missing required columns in the uploaded file.")
            st.stop()

        # Extract company names
        column_uploaded = df_uploaded[column_uploaded_name]
        column_unicorns = df_unicorns[column_unicorns_name]
        column_emerging = (
            df_emerging[column_emerging_name] if column_emerging_name else pd.Series([])
        )

        # Find overlaps
        overlaps_unicorns = set(column_unicorns).intersection(set(column_uploaded))
        overlaps_emerging = set(column_emerging).intersection(set(column_uploaded))

        # ✅ Calculate Metrics
        total_uploaded_companies = len(df_uploaded[column_uploaded_name].dropna())
        unicorn_percentage = (
            (len(overlaps_unicorns) / total_uploaded_companies) * 100
            if total_uploaded_companies > 0
            else 0
        )
        # ✅ Display Metrics
        col1, col2 = st.columns(2)
        with col1:
            st.metric(label="No. of Portfolio Companies", value=f"{total_uploaded_companies}")
        with col2:
            st.metric(label="Unicorn Hit Rate", value=f"{unicorn_percentage:.2f}%")

                        # ✅ Extract and display 🦄 Unicorn Overlaps with Valuation + Follow-On Data
        valuation_column = "post_money_valuation_(in b)"
        if valuation_column in df_unicorns.columns:
            df_unicorns_filtered = df_unicorns[df_unicorns[column_unicorns_name].isin(overlaps_unicorns)]
            df_unicorns_filtered = df_unicorns_filtered[[column_unicorns_name, valuation_column]]

            # ✅ Convert valuation column to numeric:
            df_unicorns_filtered[valuation_column] = (
                df_unicorns_filtered[valuation_column]
                .astype(str)
                .str.replace(" B", "", regex=False)
                .astype(float)
            )

            # --- Merge Follow-On Data from Investment Rounds CSV ---
            # Use the investment rounds CSV uploaded via 'uploaded_file_stages'
            if 'uploaded_file_stages' in globals() and uploaded_file_stages is not None:
                df_investment = pd.read_csv(uploaded_file_stages)
                df_investment.columns = df_investment.columns.str.lower().str.strip()
                if "organization name" in df_investment.columns and "funding round" in df_investment.columns:
                    # Clean "Funding Round" column (remove text after "-")
                    df_investment["funding round"] = df_investment["funding round"].astype(str).str.split(" - ").str[0].str.strip()
                    # Aggregate data: count and list unique funding rounds per organization
                    follow_on_data = df_investment.groupby("organization name")["funding round"].agg(
                        ["count", lambda x: ", ".join(sorted(x.unique()))]
                    )
                    follow_on_data.columns = ["Investment Count", "Investment Stages"]
                else:
                    follow_on_data = pd.DataFrame(columns=["Investment Count", "Investment Stages"])
            else:
                follow_on_data = pd.DataFrame(columns=["Investment Count", "Investment Stages"])
            # --- End of Follow-On Data Merge ---

            # Merge unicorn overlap data with follow-on data
            df_unicorns_filtered = df_unicorns_filtered.merge(follow_on_data, how="left", left_on=column_unicorns_name, right_index=True)

            # Fill missing follow-on data with defaults
            df_unicorns_filtered["Investment Count"] = df_unicorns_filtered["Investment Count"].fillna(0).astype(int)
            df_unicorns_filtered["Investment Stages"] = df_unicorns_filtered["Investment Stages"].fillna("No Follow-On Investments")

            # ✅ Sort by highest valuation
            df_unicorns_filtered = df_unicorns_filtered.sort_values(by=valuation_column, ascending=False)

            # ✅ Convert valuation back to display format
            df_unicorns_filtered[valuation_column] = df_unicorns_filtered[valuation_column].astype(str) + " B"

            # ✅ Display the combined results
            st.markdown(f"### 🦄 Unicorn Overlaps Sorted by Valuation ({len(df_unicorns_filtered)})")
            st.dataframe(df_unicorns_filtered, height=400, width=800)

        else:
            st.error("🚨 The 'Post_Money_Valuation_(in B)' column is missing.")


        # ✅ Display Emerging Unicorn Overlaps
        def display_overlap_table(overlaps, title, color):
            if overlaps:
                df_display = pd.DataFrame({"Company Name": list(overlaps)})
                st.markdown(f"<h3 style='color: {color};'>{title}: {len(overlaps)}</h3>", unsafe_allow_html=True)
                st.dataframe(df_display, height=300, width=700)
            else:
                st.markdown(f"<h3 style='color: {color};'>{title}: 0</h3>", unsafe_allow_html=True)
                st.info("No overlaps found.")

        display_overlap_table(overlaps_emerging, "🚀 Emerging Unicorn Overlaps", "#2196F3")

    # -----------------------------------------------
    # 📊 Investment Stages & Lead % Analyzer
    # -----------------------------------------------
    st.markdown("## 📊 Investment Stages & Lead % Analyzer")

    if uploaded_file_stages is not None:
        try:
            # Reset file pointer and read the file contents
            uploaded_file_stages.seek(0)
            file_data = uploaded_file_stages.getvalue()
            if len(file_data) == 0:
                st.error("🚨 The uploaded investment file is empty. Please upload a valid CSV.")
            else:
                # Read the CSV file
                uploaded_file_stages.seek(0)  # Ensure the pointer is reset before reading
                df_uploaded = pd.read_csv(uploaded_file_stages)

                # ✅ Normalize column names
                df_uploaded.columns = df_uploaded.columns.str.lower().str.strip()

                # ✅ Ensure necessary columns exist
                required_columns = ["announced date", "organization name", "funding round", "lead investor"]
                if not all(col in df_uploaded.columns for col in required_columns):
                    st.error("🚨 Missing required columns in the uploaded file (e.g., 'Announced Date').")
                    st.stop()

                # ✅ Convert "Announced Date" to datetime & extract year
                df_uploaded["announced date"] = pd.to_datetime(df_uploaded["announced date"], errors="coerce")
                df_uploaded["year"] = df_uploaded["announced date"].dt.year  # Extract only the year

                # ✅ Get min/max years for slider
                min_year = int(df_uploaded["year"].min())
                max_year = int(df_uploaded["year"].max())

                # ✅ Add Date Slider
                selected_year_range = st.slider("📅 Select Year Range", min_year, max_year, (min_year, max_year))
                
                # ✅ Filter dataset based on selected years
                df_uploaded = df_uploaded[(df_uploaded["year"] >= selected_year_range[0]) & 
                                        (df_uploaded["year"] <= selected_year_range[1])]

                # ✅ Clean "Funding Round" column (Remove text after " - ")
                df_uploaded["funding round"] = df_uploaded["funding round"].astype(str).str.split(" - ").str[0].str.strip()

                # ✅ Calculate Metrics
                total_companies = df_uploaded["organization name"].nunique()
                lead_count = df_uploaded["lead investor"].str.lower().eq("yes").sum()
                lead_percentage = (lead_count / len(df_uploaded)) * 100 if len(df_uploaded) > 0 else 0

                # ✅ Display Metrics (Move to top)
                col1, col2 = st.columns(2)
                with col1:
                    st.metric(label="Total Investments", value=f"{len(df_uploaded)}")
                with col2:
                    st.metric(label="Lead Investment %", value=f"{lead_percentage:.2f}%")

                # ✅ Count investments per stage
                stage_counts = df_uploaded["funding round"].value_counts()

                # ✅ Calculate Investment Stage Percentage
                stage_percentages = (stage_counts / len(df_uploaded)) * 100

                # ✅ Flip bar chart: Investment Stage on Y-axis
                st.markdown("### 📊 Investment Stages Breakdown")
                fig, ax = plt.subplots(figsize=(8, 6))
                bars = ax.barh(stage_counts.index, stage_counts.values, color="navy")

                # ✅ Add data labels at the end of each bar
                for bar in bars:
                    ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height() / 2,
                            f"{int(bar.get_width())}", va="center", ha="left", color="black", fontsize=12, fontweight='bold')

                ax.set_xlabel("Number of Investments")
                ax.set_ylabel("Investment Stage")
                ax.set_title(f"Investment Stages Distribution ({selected_year_range[0]} - {selected_year_range[1]})")
                ax.invert_yaxis()  # Flip the order of Y-axis labels
                st.pyplot(fig)

                # ✅ Display Investment Stage Percentages
                st.markdown("### 📊 Investment Stage Percentages (deal by deal basis)")
                
            # ✅ Calculate Early and Growth Stage Exposure
                # Define early-stage funding rounds
                early_stage_rounds = ["pre-seed round", "seed round", "series a", "series b"]

                # Count early-stage investments (match funding rounds in a case-insensitive manner)
                early_stage_count = df_uploaded["funding round"].str.lower().isin(early_stage_rounds).sum()

                # Calculate total investments
                total_investments = len(df_uploaded)

                # Calculate early-stage and growth-stage percentages
                if total_investments > 0:
                    early_stage_percentage = (early_stage_count / total_investments) * 100
                    growth_stage_percentage = 100 - early_stage_percentage
                else:
                    early_stage_percentage = 0
                    growth_stage_percentage = 0

                # ✅ Display Early/Growth % Metrics
                col3, col4 = st.columns(2)
                with col3:
                    st.metric(
                        label="Early Stage Exposure %",
                        value=f"{early_stage_percentage:.2f}%",
                        help="Percentage of investments made in pre-seed round, seed round, series a, and series b rounds."
                    )
                with col4:
                    st.metric(
                        label="Growth Stage Exposure %",
                        value=f"{growth_stage_percentage:.2f}%",
                        help="Percentage of investments made in later stages beyond Series B."
                    )

                
            stage_percent_df = pd.DataFrame({
                "Investment Stage": stage_counts.index,
                "Total Count": stage_counts.values,
                "Percentage": stage_percentages.values
            })

            # ✅ Convert percentage column to readable format
            stage_percent_df["Percentage"] = stage_percent_df["Percentage"].apply(lambda x: f"{x:.2f}%")

            # ✅ Display table
            st.dataframe(stage_percent_df, height=300, width=700)

            # -----------------------------------------------
            # ✅ Follow-On Investment Analysis
            # -----------------------------------------------
            st.markdown("### 🔄 Follow-On Investment Analysis")

            # ✅ Count occurrences of each company
            company_counts = df_uploaded.groupby("organization name")["funding round"].agg(
                ["count", lambda x: ", ".join(sorted(x.unique()))]
            )
            company_counts.columns = ["Investment Count", "Investment Stages"]

            # ✅ Filter to show only companies with more than 1 investment
            follow_on_companies = company_counts[company_counts["Investment Count"] > 1].reset_index()

            # ✅ Calculate Follow-On Rate (percentage of companies with >1 investment)
            follow_on_rate = (len(follow_on_companies) / total_companies) * 100 if total_companies > 0 else 0

            # ✅ Display Follow-On Rate Metric
            st.metric(label="Follow-On Investment Rate", value=f"{follow_on_rate:.2f}%")

            # ✅ Display Follow-On Companies Table
            if not follow_on_companies.empty:
                st.markdown("### 🔁 Companies with Follow-On Investments")
                st.dataframe(follow_on_companies, height=400, width=700)
            else:
                st.info("No companies received multiple investments in this timeframe.")
        except pd.errors.EmptyDataError:
            st.error("🚨 The uploaded investment file is empty. Please upload a valid CSV.")

