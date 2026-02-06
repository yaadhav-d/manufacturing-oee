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
# TIMEZONES
# ==================================================
UTC = pytz.utc
IST = pytz.timezone("Asia/Kolkata")

# ==================================================
# SIDEBAR CONTROLS (NO ALL OPTION)
# ==================================================
st.sidebar.title("🔧 Controls")

MACHINES = ["M-1", "M-2", "M-3", "M-4", "M-5"]

selected_machine = st.sidebar.selectbox(
    "Select Machine",
    MACHINES
)

refresh_rate = st.sidebar.slider(
    "Refresh rate (seconds)",
    2, 10, 5
)

# ==================================================
# BASELINES (REALISTIC)
# ==================================================
BASELINES = {
    "M-1": {"temp": 68, "vib": 2.5},
    "M-2": {"temp": 70, "vib": 3.0},
    "M-3": {"temp": 66, "vib": 2.2},
    "M-4": {"temp": 72, "vib": 3.5},
    "M-5": {"temp": 69, "vib": 2.8},
}

ANOMALY_PROBABILITY = 0.03

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

if "next_refresh" not in st.session_state:
    st.session_state.next_refresh = datetime.now(UTC)

if "machine_state" not in st.session_state:
    st.session_state.machine_state = {
        m: {
            "temp": BASELINES[m]["temp"],
            "vib": BASELINES[m]["vib"],
            "anomaly_active": False,
            "anomaly_steps": 0
        }
        for m in MACHINES
    }

# ==================================================
# DATA GENERATOR (FACTORY-REALISTIC)
# ==================================================
def generate_live_data():
    now_utc = datetime.now(UTC)
    rows = []

    for m in MACHINES:
        state = st.session_state.machine_state[m]

        # natural drift
        state["temp"] += np.random.normal(0, 0.15)
        state["vib"] += np.random.normal(0, 0.04)

        # gradual anomaly
        if not state["anomaly_active"] and random.random() < ANOMALY_PROBABILITY:
            state["anomaly_active"] = True
            state["anomaly_steps"] = random.randint(4, 7)

        if state["anomaly_active"]:
            state["temp"] += np.random.uniform(0.8, 1.5)
            state["vib"] += np.random.uniform(0.2, 0.4)
            state["anomaly_steps"] -= 1
            anomaly = 1
            if state["anomaly_steps"] <= 0:
                state["anomaly_active"] = False
        else:
            anomaly = 0

        # clamp physical limits
        state["temp"] = max(60, min(state["temp"], 95))
        state["vib"] = max(1.5, min(state["vib"], 8))

        units = random.randint(12, 18) if anomaly == 0 else random.randint(6, 10)

        rows.append({
            "timestamp_utc": now_utc,
            "machine_id": m,
            "temperature": round(state["temp"], 2),
            "vibration": round(state["vib"], 2),
            "units": units,
            "anomaly": anomaly
        })

    return pd.DataFrame(rows)

# ==================================================
# AUTO-REFRESH (VERSION-SAFE)
# ==================================================
now_utc = datetime.now(UTC)

if now_utc >= st.session_state.next_refresh:
    new_data = generate_live_data()
    st.session_state.data = pd.concat(
        [st.session_state.data, new_data],
        ignore_index=True
    )
    st.session_state.next_refresh = now_utc + timedelta(seconds=refresh_rate)
    st.rerun()

# ==================================================
# DATA PREP (SAFE)
# ==================================================
df = st.session_state.data.copy()

if df.empty:
    st.info("Waiting for live data…")
    st.stop()

# force datetime dtype
df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True)
df["timestamp_ist"] = df["timestamp_utc"].dt.tz_convert(IST)
df["date_ist"] = df["timestamp_ist"].dt.date

filtered_df = df[df["machine_id"] == selected_machine]

if filtered_df.empty:
    st.warning("No data yet for selected machine.")
    st.stop()

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
            "threshold": {"line": {"color": "black", "width": 4}, "value": 85}
        }
    ))
    fig.update_layout(height=300)
    return fig

# ==================================================
# UI — LIVE STATUS
# ==================================================
st.subheader(f"📊 Live Status — {selected_machine}")

c1, c2, c3 = st.columns([2, 1, 1])

with c1:
    st.plotly_chart(
        temperature_gauge(latest["temperature"]),
        use_container_width=True
    )

with c2:
    st.metric("Units Produced", int(latest["units"]))
    st.metric("Machine", latest["machine_id"])

with c3:
    st.metric("Vibration (mm/s)", f"{latest['vibration']:.2f}")
    st.error("🚨 Anomaly Detected") if latest["anomaly"] else st.success("✅ Normal")

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
# TODAY’S PEAK TEMPERATURE
# ==================================================
today_df = filtered_df[filtered_df["date_ist"] == datetime.now(IST).date()]

if not today_df.empty:
    peak = today_df.loc[today_df["temperature"].idxmax()]
    incident_time = peak["timestamp_ist"].strftime("%I:%M:%S %p IST")

    st.subheader("🔥 Today’s Peak Temperature (Root Cause View)")

    a, b, c, d, e = st.columns(5)
    a.metric("Machine", peak["machine_id"])
    b.metric("Max Temp (°C)", peak["temperature"])
    c.metric("Units at that time", peak["units"])
    d.metric("Vibration at that time", peak["vibration"])
    e.metric("Incident Time", incident_time)

# ==================================================
# FOOTER
# ==================================================
st.caption(
    f"Last updated: {datetime.now(IST).strftime('%I:%M:%S %p IST')}"
)
