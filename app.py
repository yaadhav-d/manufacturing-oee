import streamlit as st
import pandas as pd
import numpy as np
import random
from datetime import datetime
import plotly.graph_objects as go
import pytz

# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------
st.set_page_config(
    page_title="Manufacturing OEE Dashboard",
    layout="wide"
)

st.title("🏭 Manufacturing OEE – Monitoring Dashboard")

# --------------------------------------------------
# TIMEZONE
# --------------------------------------------------
IST = pytz.timezone("Asia/Kolkata")

# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------
st.sidebar.header("Controls")

MACHINES = ["M-1", "M-2", "M-3", "M-4", "M-5"]
selected_machine = st.sidebar.selectbox("Select Machine", MACHINES)

# --------------------------------------------------
# BASELINES
# --------------------------------------------------
BASELINES = {
    "M-1": (68, 2.5),
    "M-2": (70, 3.0),
    "M-3": (66, 2.2),
    "M-4": (72, 3.5),
    "M-5": (69, 2.8),
}

# --------------------------------------------------
# DATA INIT (SAFE)
# --------------------------------------------------
if "data" not in st.session_state:
    rows = []
    now = datetime.now(pytz.utc)

    for m in MACHINES:
        temp, vib = BASELINES[m]
        rows.append({
            "timestamp": now,
            "machine": m,
            "temperature": round(np.random.normal(temp, 0.8), 2),
            "vibration": round(np.random.normal(vib, 0.15), 2),
            "units": random.randint(12, 18)
        })

    st.session_state.data = pd.DataFrame(rows)

# --------------------------------------------------
# ADD ONE NEW ROW PER INTERACTION (SAFE “LIVE”)
# --------------------------------------------------
now = datetime.now(pytz.utc)
new_rows = []

for m in MACHINES:
    last = st.session_state.data[st.session_state.data["machine"] == m].iloc[-1]

    temp = last["temperature"] + np.random.normal(0, 0.2)
    vib = last["vibration"] + np.random.normal(0, 0.05)

    temp = max(60, min(temp, 90))
    vib = max(1.5, min(vib, 7))

    new_rows.append({
        "timestamp": now,
        "machine": m,
        "temperature": round(temp, 2),
        "vibration": round(vib, 2),
        "units": random.randint(12, 18)
    })

st.session_state.data = pd.concat(
    [st.session_state.data, pd.DataFrame(new_rows)],
    ignore_index=True
)

df = st.session_state.data.copy()

# --------------------------------------------------
# TIME CONVERSION
# --------------------------------------------------
df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
df["timestamp_ist"] = df["timestamp"].dt.tz_convert(IST)
df["date"] = df["timestamp_ist"].dt.date

filtered_df = df[df["machine"] == selected_machine]
latest = filtered_df.iloc[-1]

# --------------------------------------------------
# TEMPERATURE GAUGE
# --------------------------------------------------
def temp_gauge(value):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        title={"text": "Temperature (°C)"},
        gauge={
            "axis": {"range": [0, 100]},
            "steps": [
                {"range": [0, 75], "color": "#4CAF50"},
                {"range": [75, 85], "color": "#FFC107"},
                {"range": [85, 100], "color": "#F44336"},
            ],
            "threshold": {"line": {"color": "black", "width": 4}, "value": 85}
        }
    ))
    fig.update_layout(height=300)
    return fig

# --------------------------------------------------
# LIVE STATUS
# --------------------------------------------------
st.subheader(f"Live Status – {selected_machine}")

c1, c2, c3 = st.columns([2, 1, 1])

with c1:
    st.plotly_chart(temp_gauge(latest["temperature"]), use_container_width=True)

with c2:
    st.metric("Units Produced", int(latest["units"]))
    st.metric("Temperature", f"{latest['temperature']} °C")

with c3:
    st.metric("Vibration", f"{latest['vibration']} mm/s")

st.divider()

# --------------------------------------------------
# VIBRATION TREND
# --------------------------------------------------
st.subheader("Vibration Trend")
st.line_chart(filtered_df.set_index("timestamp_ist")[["vibration"]])

st.divider()

# --------------------------------------------------
# TODAY PEAK (ROOT CAUSE VIEW)
# --------------------------------------------------
today = datetime.now(IST).date()
today_df = filtered_df[filtered_df["date"] == today]

if not today_df.empty:
    peak = today_df.loc[today_df["temperature"].idxmax()]

    st.subheader("🔥 Today’s Peak Temperature – Root Cause")

    a, b, c, d = st.columns(4)
    a.metric("Max Temp", peak["temperature"])
    b.metric("Units at that time", peak["units"])
    c.metric("Vibration", peak["vibration"])
    d.metric(
        "Incident Time",
        peak["timestamp_ist"].strftime("%I:%M:%S %p IST")
    )

# --------------------------------------------------
# FOOTER
# --------------------------------------------------
st.caption(
    f"Last updated: {datetime.now(IST).strftime('%I:%M:%S %p IST')}"
)
