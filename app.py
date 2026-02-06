import streamlit as st
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta
import plotly.graph_objects as go

# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------
st.set_page_config(
    page_title="Manufacturing OEE – Live Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🏭 Manufacturing OEE – Live Monitoring Dashboard")

# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------
st.sidebar.title("🔧 Controls")

MACHINES = ["M-1", "M-2", "M-3", "M-4", "M-5"]

selected_machine = st.sidebar.selectbox(
    "Select Machine",
    MACHINES
)

refresh_rate = st.sidebar.slider(
    "Refresh rate (seconds)",
    min_value=2,
    max_value=10,
    value=5
)

# --------------------------------------------------
# SESSION STATE INIT
# --------------------------------------------------
if "data" not in st.session_state:
    st.session_state.data = pd.DataFrame(
        columns=["timestamp", "machine_id", "temperature", "vibration", "units"]
    )

# --------------------------------------------------
# DATA GENERATOR (SIMULATED LIVE DATA)
# --------------------------------------------------
def generate_live_data():
    rows = []
    now = datetime.now()

    for m in MACHINES:
        temp = np.random.uniform(60, 95)
        vib = np.random.uniform(2, 9)
        units = np.random.randint(5, 20)

        rows.append({
            "timestamp": now,
            "machine_id": m,
            "temperature": round(temp, 2),
            "vibration": round(vib, 2),
            "units": units
        })

    return pd.DataFrame(rows)

# --------------------------------------------------
# TEMPERATURE GAUGE
# --------------------------------------------------
def temperature_gauge(temp):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=temp,
        title={"text": "Temperature (°C)"},
        gauge={
            "axis": {"range": [0, 100]},
            "bar": {"color": "darkred"},
            "steps": [
                {"range": [0, 70], "color": "#4CAF50"},
                {"range": [70, 85], "color": "#FFC107"},
                {"range": [85, 100], "color": "#F44336"}
            ],
            "threshold": {
                "line": {"color": "black", "width": 4},
                "thickness": 0.75,
                "value": 85
            }
        }
    ))

    fig.update_layout(height=300, margin=dict(t=40, b=0))
    return fig

# --------------------------------------------------
# MAIN LOOP
# --------------------------------------------------
placeholder = st.empty()

while True:
    # Generate and append new data
    new_data = generate_live_data()
    st.session_state.data = pd.concat(
        [st.session_state.data, new_data],
        ignore_index=True
    )

    df = st.session_state.data.copy()

    # --------------------------------------------------
    # APPLY MACHINE FILTER (NO ALL OPTION)
    # --------------------------------------------------
    filtered_df = df[df["machine_id"] == selected_machine]

    # --------------------------------------------------
    # TODAY FILTER
    # --------------------------------------------------
    filtered_df["date"] = filtered_df["timestamp"].dt.date
    today = datetime.now().date()
    today_df = filtered_df[filtered_df["date"] == today]

    with placeholder.container():

        # --------------------------------------------------
        # LIVE STATUS
        # --------------------------------------------------
        st.subheader("📊 Live Machine Status")

        latest = filtered_df.iloc[-1]

        col1, col2, col3 = st.columns([2, 1, 1])

        with col1:
            st.plotly_chart(
                temperature_gauge(latest["temperature"]),
                use_container_width=True
            )

        with col2:
            st.metric("Units Produced", int(latest["units"]))
            st.metric("Machine", latest["machine_id"])

        with col3:
            st.metric("Vibration (mm/s)", f"{latest['vibration']:.2f}")
            if latest["vibration"] > 7:
                st.warning("⚠️ High vibration")

        st.divider()

        # --------------------------------------------------
        # VIBRATION TREND
        # --------------------------------------------------
        st.subheader("📈 Vibration Trend (mm/s)")

        st.line_chart(
            filtered_df.set_index("timestamp")[["vibration"]]
        )

        st.divider()

        # --------------------------------------------------
        # DAILY PEAK TEMPERATURE ANALYSIS
        # --------------------------------------------------
        if not today_df.empty:
            peak_row = today_df.loc[today_df["temperature"].idxmax()]

            peak_time = peak_row["timestamp"]
            peak_temp = peak_row["temperature"]
            peak_units = peak_row["units"]
            peak_vibration = peak_row["vibration"]
            peak_machine = peak_row["machine_id"]

            st.subheader("🔥 Today’s Peak Temperature Analysis")

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Machine", peak_machine)
            c2.metric("Max Temp (°C)", f"{peak_temp}")
            c3.metric("Units at that time", int(peak_units))
            c4.metric("Vibration at that time", f"{peak_vibration}")

            if peak_temp > 85:
                st.error("🚨 High temperature event – possible overload or friction issue")
            else:
                st.success("✅ Temperature within safe range")

            # --------------------------------------------------
            # ROOT CAUSE CONTEXT WINDOW
            # --------------------------------------------------
            st.subheader("🕒 10-Minute Window Around Temperature Spike")

            window_df = today_df[
                (today_df["timestamp"] >= peak_time - timedelta(minutes=10)) &
                (today_df["timestamp"] <= peak_time + timedelta(minutes=10))
            ]

            st.line_chart(
                window_df.set_index("timestamp")[["temperature", "vibration"]]
            )

        st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")

    time.sleep(refresh_rate)
