import streamlit as st
def run():
    # Continue with your usual imports
    import locale
    import pandas as pd
    import numpy as np
    from streamlit_extras.metric_cards import style_metric_cards

    # Add custom styling right after page config
    st.markdown("""
        <style>
            body {
                background-color: #f9f9f9;
            }

            .stMetric {
                background-color: #eefaff;
                padding: 1em;
                border-radius: 15px;
                margin: 5px 0;
            }

            .stMetric label {
                color: #090854 !important;
                font-weight: bold;
            }

            /* Make metric numbers navy */
            .stMetric div[data-testid="stMetricValue"] {
                color: #090854 !important;
                font-weight: bold;
            }

            /* Make delta navy as well */
            .stMetric div[data-testid="stMetricDelta"] {
                color: #090854 !important;
            }

            h1, h2, h3 {
                color: #090854;
            }

            .stButton>button {
                background-color: #06e3fd;
                color: #090854;
                border-radius: 10px;
                padding: 0.5em 1em;
                font-weight: bold;
            }
        </style>
    """, unsafe_allow_html=True)

    # Stages & Dilution Factors
    stages = ["Pre-seed", "Seed", "Series A", "Series B", "Series C", "Series D", "Series E+"]
    exit_dilution_factors = {
        "Pre-seed": 0.30, "Seed": 0.39, "Series A": 0.52,
        "Series B": 0.67, "Series C": 0.79, "Series D": 0.92, "Series E+": 1.00
    }
    # Typical exit valuations (in dollars) used to seed non-unicorn outcomes
    base_valuation_by_stage = {
        "Pre-seed":  50e6,
        "Seed":     150e6,
        "Series A": 300e6,
        "Series B": 600e6,
        "Series C": 1_200e6,
        "Series D": 3_000e6,
        "Series E+": 10_000e6,
    }

    # Default Ticket Sizes
    default_ticket_sizes = {
        "Pre-seed": 2_500_000, "Seed": 5_000_000, "Series A": 15_000_000,
        "Series B": 25_000_000, "Series C": 35_000_000,
        "Series D": 50_000_000, "Series E+": 75_000_000
    }

    # Nested Follow-On Multiplier Ranges
    follow_on_multipliers = {
        "Pre-seed": {
            "Seed":     (1.5, 3.0), "Series A": (1.2, 2.5),
            "Series B": (1.0, 2.0), "Series C": (0.8, 1.5)
        },
        "Seed": {
            "Series A": (1.0, 3.0), "Series B": (0.8, 2.0),
            "Series C": (0.7, 1.5), "Series D": (0.5, 1.2)
        },
        "Series A": {
            "Series B": (1.0, 2.0), "Series C": (0.8, 1.5),
            "Series D": (0.7, 1.2)
        },
        "Series B": {
            "Series C": (0.8, 1.5), "Series D": (0.7, 1.2),
            "Series E+": (0.5, 1.0)
        },
        "Series C": {
            "Series D": (0.7, 1.2), "Series E+": (0.5, 1.0)
        },
        "Series D": {
            "Series E+": (0.5, 1.0)
        },
        "Series E+": {}
    }

    # — Sidebar Inputs —
    stage_inputs = {}
    with st.sidebar:
        st.header("Fund Assumptions")
        fund_size_dollars    = st.number_input("Fund Size ($)", value=100_000_000, step=1_000_000, format="%d")
        mgmt_fee_pct         = st.number_input("Management Fee (%)", value=2.0, step=0.1)
        duration_years       = st.number_input("Fund Duration (years)", value=10, step=1)
        carry_pct            = st.number_input("Carry (%)", value=28.0, step=0.5)
        target_net_tvpi      = st.number_input("Targeted Net Return (TVPI)", value=5.5, step=0.1)
        unicorn_capture_rate = st.number_input("Unicorn Capture Rate (%)", value=7.0, step=0.5) / 100
        # in your st.sidebar, after unicorn_capture_rate:
        if "power_law_strength" not in st.session_state:
            # initialize with a default
            st.session_state.power_law_strength = 0.5

        # green “Simulate” button
        if st.button("Simulate"):
            # pick a random multiple of 0.05 between 0 and 1
            choices = np.round(np.arange(0.0, 1.0001, 0.05), 2)
            st.session_state.power_law_strength = float(np.random.choice(choices))

        # show the current value
        power_law_strength = st.session_state.power_law_strength
        st.markdown(f"**Power Law Strength:** {power_law_strength:.2f}")
        st.header("Follow-On Settings")
        follow_on_reserve_pct = st.number_input("Follow-On Reserve (% of Fund Size)", value=20.0, step=1.0) / 100
        winner_follow_on_prob = st.slider("Follow-On Chance if Winner", 0.0, 1.0, 0.7, 0.05)
        loser_follow_on_prob  = 1.0 - winner_follow_on_prob
        st.slider("Follow-On Chance if Loser", 0.0, 1.0, loser_follow_on_prob, 0.05, disabled=True)


        st.header("Stage Breakdown")
        for stage in stages:
            with st.expander(f"{stage} Settings"):
                num_deals     = st.number_input(f"# {stage} Deals", value=0, step=1, format="%d", key=f"{stage}_deals")
                loss_ratio    = st.number_input(f"Loss Ratio (%) - {stage}", value=90.0, step=1.0, key=f"{stage}_loss") / 100
                ticket_size   = st.number_input(f"Initial Ticket Size ($) - {stage}",
                                                value=default_ticket_sizes[stage], step=1_000_000, format="%d", key=f"{stage}_ticket")
                ownership_min = st.number_input(f"Min Ownership (%) - {stage}", value=10.0, step=0.5, key=f"{stage}_own_min") / 100
                ownership_max = st.number_input(f"Max Ownership (%) - {stage}", value=25.0, step=0.5, key=f"{stage}_own_max") / 100

                stage_inputs[stage] = {
                    "deals":           num_deals,
                    "loss_ratio":      loss_ratio,
                    "ticket_size":     ticket_size,
                    "ownership_bounds": (ownership_min, ownership_max),
                    "exit_dilution":   exit_dilution_factors[stage]
                }
    total_portfolio_companies = sum(data["deals"] for data in stage_inputs.values())

    # — Rates & Pools —
    mgmt_fee_rate             = mgmt_fee_pct / 100
    carry_rate                = carry_pct / 100
    initial_investable_pool   = fund_size_dollars * (1 - follow_on_reserve_pct)
    follow_on_reserve_capital = fund_size_dollars * follow_on_reserve_pct

    # — Formatting Helpers —
    def label_large_number(num):
        if num >= 1_000_000_000_000: return f"{num/1_000_000_000_000:.1f}T"
        if num >=   1_000_000_000: return f"{num/1_000_000_000:.1f}B"
        if num >=       1_000_000: return f"{num/1_000_000:.1f}M"
        return f"{num:,.0f}"

    def format_large_dollar_amount(num):
        return f"${label_large_number(num)}"

    # — Core Fund Metrics —
    total_fees            = fund_size_dollars * mgmt_fee_rate * duration_years
    investable_capital    = fund_size_dollars    # full fund used for return math
    net_return            = fund_size_dollars * target_net_tvpi
    required_gross_return = (net_return - carry_rate * investable_capital + total_fees) / (1 - carry_rate)
    required_multiple     = required_gross_return / investable_capital if investable_capital else 0
    profit                = required_gross_return - investable_capital
    total_carry           = carry_rate * profit

    # — Build Stage Valuation Data —
    stage_valuation_data = {}
    for s, data in stage_inputs.items():
        d = data["deals"]
        if d > 0:
            stage_valuation_data[s] = {
                "deals":        d,
                "ticket":       data["ticket_size"],
                "loss_ratio":   data["loss_ratio"],
                "min_own":      data["ownership_bounds"][0],
                "max_own":      data["ownership_bounds"][1],
                "exit_dilution": data["exit_dilution"]
            }

    # — Simulate Entry Ownership & Dilution —
    all_scaled_ownerships  = []
    all_diluted_ownerships = []
    valuation_stage_map   = []
    for stage, d in stage_valuation_data.items():
        lo, hi   = d["min_own"], d["max_own"]
        uniforms = np.random.rand(d["deals"])
        scaled   = uniforms * (hi - lo) + lo
        diluted  = scaled * d["exit_dilution"]

        winners = int(d["deals"] * (1 - d["loss_ratio"]))
        valuation_stage_map += [(stage, i, True)  for i in range(winners)]
        valuation_stage_map += [(stage, i, False) for i in range(winners, d["deals"])]

        all_scaled_ownerships.extend(scaled)
        all_diluted_ownerships.extend(diluted)

    num_entries    = len(valuation_stage_map)
    winner_indices = [i for i, (_,_,w) in enumerate(valuation_stage_map) if w]

    # — Unicorn & Non-Unicorn Valuations —
    raw_valuations  = np.zeros(num_entries)
    num_uni_desired = max(1, int(unicorn_capture_rate * num_entries))
    num_uni_allowed = min(num_uni_desired, len(winner_indices))
    uni_idx         = np.random.choice(winner_indices, num_uni_allowed, replace=False)
    non_uni_idx     = list(set(winner_indices) - set(uni_idx))

    if num_uni_allowed > 0:
        a         = 2.0 - 1.5 * power_law_strength
        base      = np.random.pareto(a, size=num_uni_allowed) + 1
        scaled    = base / base.sum()
        minV = base_valuation_by_stage[stage] * 3   # unicorn = 3× typical non-uni base
        maxV = base_valuation_by_stage[stage] * 10
        vals      = np.clip(scaled * (maxV - minV) + minV, minV, maxV)
        raw_valuations[uni_idx] = vals

    if non_uni_idx:
        weights = np.random.dirichlet(np.ones(len(non_uni_idx)))
        for j, idx in enumerate(non_uni_idx):
            stage = valuation_stage_map[idx][0]
            base  = base_valuation_by_stage.get(stage, 1e9)
            raw_valuations[idx] = weights[j] * base

    raw_exit_ownerships = np.array(all_diluted_ownerships)
    raw_fair = raw_valuations * raw_exit_ownerships

    # Cap MOIC at 150x
    for i in winner_indices:
        tix = stage_inputs[valuation_stage_map[i][0]]["ticket_size"]
        moic = raw_fair[i] / tix if tix else 0
        if moic > 150:
            raw_fair[i]       = 150 * tix
            raw_valuations[i] = raw_fair[i] / raw_exit_ownerships[i]

    # Scale to hit fund targets
    scaleA = required_gross_return / raw_fair[winner_indices].sum()
    raw_valuations[winner_indices] *= scaleA
    all_valuations = raw_valuations.copy()

    # — Follow-On Simulation & Deal Table (fixed) —
    max_follow_ons = 3
    order = stages[:]

    initial_check_invested   = 0
    follow_on_check_invested = 0
    rows = []

    for idx, (entry_stage, _, is_winner) in enumerate(valuation_stage_map):
        ticket    = stage_inputs[entry_stage]["ticket_size"]
        entry_own = all_scaled_ownerships[idx]
        exit_own  = entry_own
        seq       = [entry_stage]
        initial_check_invested += ticket

        company_follow_on_spent = 0
        cur     = order.index(entry_stage)
        follows = 0

        while follows < max_follow_ons and cur + 1 < len(order):
            nxt  = order[cur + 1]
            prob = winner_follow_on_prob if is_winner else loser_follow_on_prob

            if np.random.rand() < prob:
                # TRY to follow-on
                lo, hi = follow_on_multipliers.get(entry_stage, {}).get(nxt, (1.0, 1.5))
                amt    = ticket * np.random.uniform(lo, hi)

                if follow_on_reserve_capital >= amt:
                    # SPEND the money and record the stage
                    follow_on_reserve_capital  -= amt
                    follow_on_check_invested   += amt
                    company_follow_on_spent    += amt
                    seq.append(nxt)
                    # pro-rata → no dilution
                else:
                    # reserve EMPTY: treat as skip
                    dilution_factor = (
                        exit_dilution_factors[order[cur]]
                        / exit_dilution_factors[nxt]
                    )
                    exit_own *= dilution_factor

            else:
                # SKIP follow-on → apply dilution
                dilution_factor = (
                    exit_dilution_factors[order[cur]]
                    / exit_dilution_factors[nxt]
                )
                exit_own *= dilution_factor

            cur     += 1
            follows += 1

        # cap at pro-rata
        exit_own = min(exit_own, entry_own)

        # compute final metrics
        if is_winner:
            val  = all_valuations[idx]
            fair = val * exit_own
            total_invested = ticket + company_follow_on_spent
            moic = fair / total_invested if total_invested > 0 else 0
        else:
            val = fair = moic = 0.0


        rows.append([
            " > ".join(seq),
            ticket,
            company_follow_on_spent,
            fair,
            val,
            entry_own,
            exit_own,
            moic
        ])


    # — Render Outputs —
    st.header("Key Fund Metrics")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Fund Size", format_large_dollar_amount(investable_capital))
        st.metric("Required Gross Return", format_large_dollar_amount(required_gross_return))
        st.metric("Total Portfolio Companies", f"{total_portfolio_companies}")

    with col2:
        st.metric("Total Management Fees", format_large_dollar_amount(total_fees))
        st.metric("Gross Return Multiple", f"{required_multiple:.2f}x")
        st.metric("Follow-On Reserve", format_large_dollar_amount(follow_on_reserve_pct * fund_size_dollars))

    with col3:
        st.metric("Total Carry", format_large_dollar_amount(total_carry))
        st.metric("Net Return", format_large_dollar_amount(net_return))
        st.metric("Remaining Follow-On", format_large_dollar_amount(follow_on_reserve_capital))

    style_metric_cards(border_left_color="#06e3fd")

    st.header("Stage Contributions – Deal Table")
    df = pd.DataFrame(rows, columns=[
        "Stage Sequence", "Initial Ticket Size", "Follow-On Spent",
        "Fair Value at Exit", "Valuation",
        "Ownership at Entry", "Ownership at Exit", "MOIC"
    ])
    styled = df.style.format({
        "Initial Ticket Size": lambda x: format_large_dollar_amount(x),
        "Follow-On Spent":     lambda x: format_large_dollar_amount(x),
        "Fair Value at Exit":  lambda x: format_large_dollar_amount(x),
        "Valuation":           lambda x: format_large_dollar_amount(x),
        "Ownership at Entry":  lambda x: f"{x*100:.1f}%",
        "Ownership at Exit":   lambda x: f"{x*100:.1f}%",
        "MOIC":                lambda x: f"{x:.2f}x"
    })
    st.dataframe(styled, use_container_width=True)

    st.header("Dilution Reference Table")
    dilution_df = pd.DataFrame({
        "Entry Stage": list(exit_dilution_factors.keys()),
        "Retained % of Entry Ownership": list(exit_dilution_factors.values())
    }).set_index("Entry Stage")
    st.dataframe(dilution_df)
