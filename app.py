import streamlit as st
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta
import plotly.graph_objects as go
import pytz
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
# TIMEZONE
# --------------------------------------------------
IST = pytz.timezone("Asia/Kolkata")

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
# BASELINES (REALISTIC)
# --------------------------------------------------
BASELINES = {
    "M-1": {"temp": 68, "vib": 2.5},
    "M-2": {"temp": 70, "vib": 3.0},
    "M-3": {"temp": 66, "vib": 2.2},
    "M-4": {"temp": 72, "vib": 3.5},
    "M-5": {"temp": 69, "vib": 2.8},
}

# --------------------------------------------------
# SESSION STATE INIT
# --------------------------------------------------
if "data" not in st.session_state:
    st.session_state.data = pd.DataFrame(
        columns=["timestamp", "machine_id", "temperature", "vibration", "units"]
    )

if "machine_state" not in st.session_state:
    st.session_state.machine_state = {
        m: {
            "temp": BASELINES[m]["temp"],
            "vib": BASELINES[m]["vib"],
            "anomaly": False,
            "steps": 0
        }
        for m in MACHINES
    }

# --------------------------------------------------
# DATA GENERATOR (REALISTIC)
# --------------------------------------------------
def generate_live_data():
    rows = []
    now = datetime.now(IST)

    for m in MACHINES:
        state = st.session_state.machine_state[m]

        # natural drift
        state["temp"] += np.random.normal(0, 0.2)
        state["vib"] += np.random.normal(0, 0.05)

        # rare gradual anomaly
        if not state["anomaly"] and random.random() < 0.03:
            state["anomaly"] = True
            state["steps"] = random.randint(3, 6)

        if state["anomaly"]:
            state["temp"] += np.random.uniform(0.8, 1.5)
            state["vib"] += np.random.uniform(0.3, 0.6)
            state["steps"] -= 1
            if state["steps"] <= 0:
                state["anomaly"] = False

        # clamp
        state["temp"] = max(60, min(state["temp"], 95))
        state["vib"] = max(1.5, min(state["vib"], 9))

        units = random.randint(12, 18) if not state["anomaly"] else random.randint(6, 10)

        rows.append({
            "timestamp": now,
            "machine_id": m,
            "temperature": round(state["temp"], 2),
            "vibration": round(state["vib"], 2),
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
    new_data = generate_live_data()
    st.session_state.data = pd.concat(
        [st.session_state.data, new_data],
        ignore_index=True
    )

    df = st.session_state.data.copy()
    filtered_df = df[df["machine_id"] == selected_machine]

    filtered_df["date"] = pd.to_datetime(filtered_df["timestamp"]).dt.date
    today = datetime.now(IST).date()
    today_df = filtered_df[filtered_df["date"] == today]

    with placeholder.container():

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
            st.metric("Units Produced", int(latest["units"]))
            st.metric("Machine", latest["machine_id"])

        with col3:
            st.metric("Vibration (mm/s)", f"{latest['vibration']:.2f}")
            if latest["vibration"] > 7:
                st.warning("⚠️ High vibration")

        st.divider()

        st.subheader("📈 Vibration Trend (mm/s)")
        st.line_chart(
            filtered_df.set_index("timestamp")[["vibration"]]
        )

        st.divider()

        if not today_df.empty:
            peak_row = today_df.loc[today_df["temperature"].idxmax()]

            st.subheader("🔥 Today’s Peak Temperature Analysis")

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Machine", peak_row["machine_id"])
            c2.metric("Max Temp (°C)", peak_row["temperature"])
            c3.metric("Units at that time", int(peak_row["units"]))
            c4.metric("Vibration at that time", peak_row["vibration"])

            if peak_row["temperature"] > 85:
                st.error("🚨 High temperature event – possible overload or friction issue")
            else:
                st.success("✅ Temperature within safe range")

            st.subheader("🕒 10-Minute Window Around Temperature Spike")

            window_df = today_df[
                (today_df["timestamp"] >= peak_row["timestamp"] - timedelta(minutes=10)) &
                (today_df["timestamp"] <= peak_row["timestamp"] + timedelta(minutes=10))
            ]

            st.line_chart(
                window_df.set_index("timestamp")[["temperature", "vibration"]]
            )

        st.caption(
            f"Last updated: {datetime.now(IST).strftime('%I:%M:%S %p IST')}"
        )

    time.sleep(refresh_rate)
