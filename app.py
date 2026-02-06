import streamlit as st
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta
import plotly.graph_objects as go
import random

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
machine_options = ["ALL"] + MACHINES

selected_machine = st.sidebar.selectbox(
    "Select Machine",
    machine_options
)

refresh_rate = st.sidebar.slider(
    "Refresh rate (seconds)",
    min_value=2,
    max_value=10,
    value=5
)

# --------------------------------------------------
# BASELINES (REALISTIC)
# --------------------------------------------------
BASELINES = {
    "M-1": {"temp": 68, "vib": 2.5},
    "M-2": {"temp": 70, "vib": 3.0},
    "M-3": {"temp": 66, "vib": 2.2},
    "M-4": {"temp": 72, "vib": 3.5},
    "M-5": {"temp": 69, "vib": 2.8},
}

ANOMALY_PROBABILITY = 0.07  # 7% chance per cycle per machine

# --------------------------------------------------
# SESSION STATE INIT
# --------------------------------------------------
if "data" not in st.session_state:
    st.session_state.data = pd.DataFrame(
        columns=["timestamp", "machine_id", "temperature", "vibration", "units", "anomaly"]
    )

# --------------------------------------------------
# DATA GENERATOR (ANOMALY-BASED)
# --------------------------------------------------
def generate_live_data():
    rows = []
    now = datetime.now()

    for m in MACHINES:
        baseline_temp = BASELINES[m]["temp"]
        baseline_vib = BASELINES[m]["vib"]

        # Normal fluctuations
        temp = np.random.normal(baseline_temp, 1.2)
        vib = np.random.normal(baseline_vib, 0.3)
        units = random.randint(12, 18)

        anomaly = 0

        # Inject rare anomaly
        if random.random() < ANOMALY_PROBABILITY:
            anomaly = 1
            temp += random.uniform(15, 25)      # spike
            vib += random.uniform(3, 5)
            units = random.randint(5, 10)       # production drops

        rows.append({
            "timestamp": now,
            "machine_id": m,
            "temperature": round(temp, 2),
            "vibration": round(vib, 2),
            "units": units,
            "anomaly": anomaly
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

# --------------------------------------------------
# MAIN LOOP
# --------------------------------------------------
placeholder = st.empty()

while True:
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

    filtered_df["date"] = filtered_df["timestamp"].dt.date
    today = datetime.now().date()
    today_df = filtered_df[filtered_df["date"] == today]

    with placeholder.container():

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
            if latest["anomaly"] == 1:
                st.error("🚨 Anomaly Detected")

        st.divider()

        st.subheader("📈 Vibration Trend (mm/s)")
        st.line_chart(
            filtered_df.set_index("timestamp")[["vibration"]]
        )

        st.divider()

        # Peak temperature analysis (now meaningful)
        if not today_df.empty:
            peak_row = today_df.loc[today_df["temperature"].idxmax()]

            st.subheader("🔥 Today’s Peak Temperature (Anomaly Context)")

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Machine", peak_row["machine_id"])
            c2.metric("Max Temp (°C)", peak_row["temperature"])
            c3.metric("Units at that time", peak_row["units"])
            c4.metric("Vibration at that time", peak_row["vibration"])

            if peak_row["anomaly"] == 1:
                st.error("🚨 Confirmed anomaly event – investigate machine condition")
            else:
                st.success("✅ Peak within expected operational range")

            window_df = today_df[
                (today_df["timestamp"] >= peak_row["timestamp"] - timedelta(minutes=10)) &
                (today_df["timestamp"] <= peak_row["timestamp"] + timedelta(minutes=10))
            ]

            st.subheader("🕒 Context Around Anomaly")
            st.line_chart(
                window_df.set_index("timestamp")[["temperature", "vibration"]]
            )

        st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")

    time.sleep(refresh_rate)
