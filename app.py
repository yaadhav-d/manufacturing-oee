import streamlit as st
import pandas as pd
import numpy as np
import time
import random
from datetime import datetime, timedelta
import plotly.graph_objects as go

# ==================================================
# PAGE CONFIG
# ==================================================
st.set_page_config(
    page_title="Manufacturing OEE – Live Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🏭 Manufacturing OEE – Live Monitoring Dashboard")

# ==================================================
# SIDEBAR CONTROLS
# ==================================================
st.sidebar.title("🔧 Controls")

MACHINES = ["M-1", "M-2", "M-3", "M-4", "M-5"]
machine_options = ["ALL"] + MACHINES

selected_machine = st.sidebar.selectbox(
    "Select Machine",
    machine_options,
    key="machine_selector"
)

refresh_rate = st.sidebar.slider(
    "Refresh rate (seconds)",
    min_value=2,
    max_value=10,
    value=5,
    key="refresh_rate"
)

# ==================================================
# REALISTIC BASELINES
# ==================================================
BASELINES = {
    "M-1": {"temp": 68, "vib": 2.5},
    "M-2": {"temp": 70, "vib": 3.0},
    "M-3": {"temp": 66, "vib": 2.2},
    "M-4": {"temp": 72, "vib": 3.5},
    "M-5": {"temp": 69, "vib": 2.8},
}

ANOMALY_PROBABILITY = 0.07  # 7% chance

# ==================================================
# SESSION STATE INIT
# ==================================================
if "data" not in st.session_state:
    st.session_state.data = pd.DataFrame(
        columns=["timestamp", "machine_id", "temperature", "vibration", "units", "anomaly"]
    )

# ==================================================
# DATA GENERATOR (ANOMALY BASED)
# ==================================================
def generate_live_data():
    rows = []
    now = datetime.now()

    for m in MACHINES:
        base = BASELINES[m]

        # Normal operation
        temp = np.random.normal(base["temp"], 1.2)
        vib = np.random.normal(base["vib"], 0.3)
        units = random.randint(12, 18)
        anomaly = 0

        # Rare anomaly
        if random.random() < ANOMALY_PROBABILITY:
            anomaly = 1
            temp += random.uniform(15, 25)
            vib += random.uniform(3, 5)
            units = random.randint(5, 10)

        rows.append({
            "timestamp": now,
            "machine_id": m,
            "temperature": round(temp, 2),
            "vibration": round(vib, 2),
            "units": units,
            "anomaly": anomaly
        })

    return pd.DataFrame(rows)

# ==================================================
# TEMPERATURE GAUGE
# ==================================================
def temperature_gauge(temp):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=temp,
        title={"text": "Temperature (°C)"},
        gauge={
            "axis": {"range": [0, 100]},
            "bar": {"color": "darkred"},
            "steps": [
                {"range": [0, 75], "color": "#4CAF50"},
                {"range": [75, 85], "color": "#FFC107"},
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

# ==================================================
# MAIN LOOP
# ==================================================
placeholder = st.empty()

while True:
    # Generate data
    new_data = generate_live_data()
    st.session_state.data = pd.concat(
        [st.session_state.data, new_data],
        ignore_index=True
    )

    df = st.session_state.data.copy()

    # Apply machine filter
    if selected_machine != "ALL":
        filtered_df = df[df["machine_id"] == selected_machine]
    else:
        filtered_df = df.copy()

    # Today filter
    filtered_df["date"] = filtered_df["timestamp"].dt.date
    today = datetime.now().date()
    today_df = filtered_df[filtered_df["date"] == today]

    with placeholder.container():

        # ==============================================
        # LIVE STATUS
        # ==============================================
        st.subheader("📊 Live Machine Status")

        latest = filtered_df.iloc[-1]

        col1, col2, col3 = st.columns([2, 1, 1])

        with col1:
            st.plotly_chart(
                temperature_gauge(latest["temperature"]),
                use_container_width=True,
                key="temp_gauge"
            )

        with col2:
            st.metric("Units Produced", int(latest["units"]), key="units_metric")
            st.metric("Machine", latest["machine_id"], key="machine_metric")

        with col3:
            st.metric("Vibration (mm/s)", f"{latest['vibration']:.2f}", key="vibration_metric")
            if latest["anomaly"] == 1:
                st.error("🚨 Anomaly Detected")
            else:
                st.success("✅ Normal")

        st.divider()

        # ==============================================
        # VIBRATION TREND
        # ==============================================
        st.subheader("📈 Vibration Trend (mm/s)")
        st.line_chart(
            filtered_df.set_index("timestamp")[["vibration"]],
            key="vibration_trend"
        )

        st.divider()

        # ==============================================
        # DAILY PEAK TEMPERATURE ANALYSIS
        # ==============================================
        if not today_df.empty:
            peak_row = today_df.loc[today_df["temperature"].idxmax()]

            st.subheader("🔥 Today’s Peak Temperature (Root Cause View)")

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Machine", peak_row["machine_id"], key="peak_machine")
            c2.metric("Max Temp (°C)", peak_row["temperature"], key="peak_temp")
            c3.metric("Units at that time", peak_row["units"], key="peak_units")
            c4.metric("Vibration at that time", peak_row["vibration"], key="peak_vib")

            if peak_row["anomaly"] == 1:
                st.error("🚨 Confirmed anomaly – investigate bearing/load/cooling")
            else:
                st.success("✅ Peak within expected operating range")

            # Context window
            window_df = today_df[
                (today_df["timestamp"] >= peak_row["timestamp"] - timedelta(minutes=10)) &
                (today_df["timestamp"] <= peak_row["timestamp"] + timedelta(minutes=10))
            ]

            st.subheader("🕒 Context Around Peak Event")
            st.line_chart(
                window_df.set_index("timestamp")[["temperature", "vibration"]],
                key="anomaly_context"
            )

        st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")

    time.sleep(refresh_rate)
