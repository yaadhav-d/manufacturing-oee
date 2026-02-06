import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
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
# SIDEBAR
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
# SESSION STATE INIT
# ==================================================
if "data" not in st.session_state:
    st.session_state.data = pd.DataFrame(
        columns=["timestamp", "machine_id", "temperature", "vibration", "units"]
    )

if "machine_state" not in st.session_state:
    st.session_state.machine_state = {
        m: {
            "temp": np.random.uniform(65, 75),
            "vib": np.random.uniform(2.5, 4.0)
        }
        for m in MACHINES
    }

if "last_update" not in st.session_state:
    st.session_state.last_update = datetime.now()

# ==================================================
# DATA GENERATION (REALISTIC, STABLE)
# ==================================================
def generate_live_data():
    now = datetime.now()
    rows = []

    for m in MACHINES:
        state = st.session_state.machine_state[m]

        # smooth industrial drift
        temp = state["temp"] + np.random.normal(0, 0.3)
        vib = state["vib"] + np.random.normal(0, 0.1)

        # clamp physical limits
        temp = max(60, min(temp, 90))
        vib = max(1.5, min(vib, 7))

        state["temp"] = temp
        state["vib"] = vib

        units = np.random.randint(12, 18)

        rows.append({
            "timestamp": now,
            "machine_id": m,
            "temperature": round(temp, 2),
            "vibration": round(vib, 2),
            "units": units
        })

    return pd.DataFrame(rows)

# ==================================================
# AUTO UPDATE (SAFE, STREAMLIT-NATIVE)
# ==================================================
if (datetime.now() - st.session_state.last_update).seconds >= refresh_rate:
    new_data = generate_live_data()
    st.session_state.data = pd.concat(
        [st.session_state.data, new_data],
        ignore_index=True
    )
    st.session_state.last_update = datetime.now()

df = st.session_state.data.copy()

if df.empty:
    st.info("Waiting for live data…")
    st.stop()

filtered_df = df[df["machine_id"] == selected_machine]
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
                {"range": [0, 70], "color": "#4CAF50"},
                {"range": [70, 85], "color": "#FFC107"},
                {"range": [85, 100], "color": "#F44336"}
            ],
            "threshold": {
                "line": {"color": "black", "width": 4},
                "value": 85
            }
        }
    ))
    fig.update_layout(height=300)
    return fig

# ==================================================
# LIVE STATUS
# ==================================================
st.subheader(f"📊 Live Machine Status – {selected_machine}")

c1, c2, c3 = st.columns([2, 1, 1])

with c1:
    st.plotly_chart(
        temperature_gauge(latest["temperature"]),
        use_container_width=True
    )

with c2:
    st.metric("Units Produced", int(latest["units"]))
    st.metric("Temperature", f"{latest['temperature']} °C")

with c3:
    st.metric("Vibration (mm/s)", f"{latest['vibration']:.2f}")

st.divider()

# ==================================================
# VIBRATION TREND
# ==================================================
st.subheader("📈 Vibration Trend")
st.line_chart(
    filtered_df.set_index("timestamp")[["vibration"]]
)

st.divider()

# ==================================================
# TODAY PEAK ANALYSIS
# ==================================================
df["date"] = df["timestamp"].dt.date
today = datetime.now().date()
today_df = filtered_df[filtered_df["date"] == today]

if not today_df.empty:
    peak = today_df.loc[today_df["temperature"].idxmax()]

    st.subheader("🔥 Today’s Peak Temperature Analysis")

    a, b, c, d = st.columns(4)
    a.metric("Max Temp (°C)", peak["temperature"])
    b.metric("Units at that time", int(peak["units"]))
    c.metric("Vibration", peak["vibration"])
    d.metric(
        "Incident Time",
        peak["timestamp"].astimezone(IST).strftime("%I:%M:%S %p IST")
    )

# ==================================================
# FOOTER
# ==================================================
st.caption(
    f"Last updated: {datetime.now(IST).strftime('%I:%M:%S %p IST')}"
)
