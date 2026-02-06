import streamlit as st
import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta
import plotly.graph_objects as go
import pytz

# ==================================================
# PAGE CONFIG
# ==================================================
st.set_page_config(
    page_title="Manufacturing OEE – Live Dashboard",
    layout="wide"
)

st.title("🏭 Manufacturing OEE – Live Monitoring Dashboard")

# ==================================================
# TIMEZONE
# ==================================================
IST = pytz.timezone("Asia/Kolkata")

# ==================================================
# SIDEBAR CONTROLS
# ==================================================
st.sidebar.title("🔧 Controls")

MACHINES = ["M-1", "M-2", "M-3", "M-4", "M-5"]
machine_options = ["ALL"] + MACHINES

selected_machine = st.sidebar.selectbox(
    "Select Machine",
    machine_options
)

refresh_rate = st.sidebar.slider(
    "Refresh rate (seconds)",
    2, 10, 5
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

ANOMALY_PROBABILITY = 0.07

# ==================================================
# SESSION STATE INIT
# ==================================================
if "data" not in st.session_state:
    st.session_state.data = pd.DataFrame(
        columns=[
            "timestamp_utc",
            "machine_id",
            "temperature",
            "vibration",
            "units",
            "anomaly",
        ]
    )

if "last_generated" not in st.session_state:
    st.session_state.last_generated = None

# ==================================================
# DATA GENERATOR
# ==================================================
def generate_live_data():
    rows = []
    now_utc = datetime.now(pytz.utc)

    for m in MACHINES:
        base = BASELINES[m]

        temp = np.random.normal(base["temp"], 1.2)
        vib = np.random.normal(base["vib"], 0.3)
        units = random.randint(12, 18)
        anomaly = 0

        if random.random() < ANOMALY_PROBABILITY:
            anomaly = 1
            temp += random.uniform(15, 25)
            vib += random.uniform(3, 5)
            units = random.randint(5, 10)

        rows.append({
            "timestamp_utc": now_utc,
            "machine_id": m,
            "temperature": round(temp, 2),
            "vibration": round(vib, 2),
            "units": units,
            "anomaly": anomaly
        })

    return pd.DataFrame(rows)

# ==================================================
# CONTROLLED DATA GENERATION (TIME-GUARDED)
# ==================================================
now_utc = datetime.now(pytz.utc)

if (
    st.session_state.last_generated is None
    or (now_utc - st.session_state.last_generated).seconds >= refresh_rate
):
    new_data = generate_live_data()
    st.session_state.data = pd.concat(
        [st.session_state.data, new_data],
        ignore_index=True
    )
    st.session_state.last_generated = now_utc

df = st.session_state.data.copy()

# ==================================================
# TIME CONVERSION (ONCE, CONSISTENTLY)
# ==================================================
df["timestamp_ist"] = df["timestamp_utc"].dt.tz_convert(IST)
df["date_ist"] = df["timestamp_ist"].dt.date

# ==================================================
# APPLY MACHINE FILTER
# ==================================================
if selected_machine != "ALL":
    filtered_df = df[df["machine_id"] == selected_machine]
else:
    filtered_df = df.copy()

latest = filtered_df.iloc[-1]

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
            "steps": [
                {"range": [0, 75], "color": "#4CAF50"},
                {"range": [75, 85], "color": "#FFC107"},
                {"range": [85, 100], "color": "#F44336"}
            ],
            "threshold": {
                "line": {"color": "black", "width": 4},
                "value": 85
            }
        }
    ))
    fig.update_layout(height=300, margin=dict(t=40, b=0))
    return fig

# ==================================================
# UI — LIVE STATUS
# ==================================================
st.subheader("📊 Live Machine Status")

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
    else:
        st.success("✅ Normal")

st.divider()

# ==================================================
# VIBRATION TREND
# ==================================================
st.subheader("📈 Vibration Trend (mm/s)")
st.line_chart(
    filtered_df.set_index("timestamp_ist")[["vibration"]]
)

st.divider()

# ==================================================
# TODAY’S PEAK TEMPERATURE (IST-CORRECT)
# ==================================================
today_ist = datetime.now(IST).date()
today_df = filtered_df[filtered_df["date_ist"] == today_ist]

if not today_df.empty:
    peak = today_df.loc[today_df["temperature"].idxmax()]
    incident_time_str = peak["timestamp_ist"].strftime("%I:%M:%S %p IST")

    st.subheader("🔥 Today’s Peak Temperature (Root Cause View)")

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Machine", peak["machine_id"])
    c2.metric("Max Temp (°C)", peak["temperature"])
    c3.metric("Units at that time", peak["units"])
    c4.metric("Vibration at that time", peak["vibration"])
    c5.metric("Incident Time", incident_time_str)

    if peak["anomaly"] == 1:
        st.error("🚨 Confirmed anomaly – investigate load / bearing / cooling")
    else:
        st.success("✅ Peak within normal operating range")

    window_df = today_df[
        (today_df["timestamp_ist"] >= peak["timestamp_ist"] - timedelta(minutes=10)) &
        (today_df["timestamp_ist"] <= peak["timestamp_ist"] + timedelta(minutes=10))
    ]

    st.subheader("🕒 Context Around Peak Event")
    st.line_chart(
        window_df.set_index("timestamp_ist")[["temperature", "vibration"]]
    )

# ==================================================
# FOOTER (TRUTHFUL)
# ==================================================
st.caption(
    f"Last updated: {datetime.now(IST).strftime('%I:%M:%S %p IST')}"
)

# ==================================================
# RERUN (STREAMLIT-NATIVE)
# ==================================================
st.rerun()
