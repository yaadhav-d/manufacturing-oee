import streamlit as st
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta
import mysql.connector
import plotly.graph_objects as go

# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------
st.set_page_config(
    page_title="Manufacturing Live Dashboard",
    layout="wide"
)

st.title("🏭 Manufacturing Live Monitoring Dashboard")

# --------------------------------------------------
# DATABASE CONFIG
# --------------------------------------------------
DB_CONFIG = {
    "host": st.secrets["DB_HOST"],
    "user": st.secrets["DB_USER"],
    "password": st.secrets["DB_PASSWORD"],
    "database": st.secrets["DB_NAME"],
    "port": int(st.secrets["DB_PORT"]),
    "ssl_disabled": False,
    "connection_timeout": 10
}

def get_connection():
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except mysql.connector.Error:
        st.error("❌ Database connection failed")
        st.stop()

conn = get_connection()

# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------
st.sidebar.title("🔧 Controls")

MACHINES = ["M-1", "M-2", "M-3", "M-4", "M-5"]
selected_machine = st.sidebar.selectbox("Select Machine", MACHINES)

refresh_rate = st.sidebar.slider("Refresh rate (seconds)", 2, 10, 5)
pause_generation = st.sidebar.checkbox("⏸ Pause data generation")

# --------------------------------------------------
# INITIAL STATE
# --------------------------------------------------
if "machine_state" not in st.session_state:
    st.session_state.machine_state = {
        m: {
            "temperature": np.random.uniform(62, 68),
            "vibration": np.random.uniform(2.5, 3.2),
            "units": np.random.randint(13, 16)
        }
        for m in MACHINES
    }

# --------------------------------------------------
# DATA GENERATION
# --------------------------------------------------
def insert_live_data():
    cursor = conn.cursor()
    now = datetime.now()

    for m in MACHINES:
        s = st.session_state.machine_state[m]

        temp = max(58, min(s["temperature"] + np.random.uniform(-0.4, 0.4), 82))
        vib = max(2.0, min(s["vibration"] + np.random.uniform(-0.08, 0.08), 6.5))
        units = max(10, min(s["units"] + np.random.randint(-1, 2), 18))

        st.session_state.machine_state[m] = {
            "temperature": temp,
            "vibration": vib,
            "units": units
        }

        cursor.execute(
            """
            INSERT INTO machine_telemetry
            (timestamp, machine_id, temperature, vibration, units)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (now, m, round(temp, 2), round(vib, 2), units)
        )

    conn.commit()
    cursor.close()

# --------------------------------------------------
# MAIN EXECUTION
# --------------------------------------------------
if not pause_generation:
    insert_live_data()

df = pd.read_sql(
    """
    SELECT timestamp, temperature, vibration, units
    FROM machine_telemetry
    WHERE machine_id = %s
    ORDER BY timestamp
    """,
    conn,
    params=(selected_machine,)
)

df["timestamp"] = pd.to_datetime(df["timestamp"])
latest = df.iloc[-1]

# --------------------------------------------------
# TEMP TREND ARROW
# --------------------------------------------------
if "prev_temp" not in st.session_state:
    arrow = "➖"
else:
    arrow = "🔺" if latest["temperature"] > st.session_state.prev_temp else "🔻"

st.session_state.prev_temp = latest["temperature"]

# --------------------------------------------------
# STATUS
# --------------------------------------------------
TEMP_CRITICAL, VIB_CRITICAL = 85, 7.5
if latest["temperature"] >= TEMP_CRITICAL or latest["vibration"] >= VIB_CRITICAL:
    status = "🔴 CRITICAL"
else:
    status = "🟢 NORMAL"

# --------------------------------------------------
# LIVE STATUS
# --------------------------------------------------
st.subheader("📊 Live Machine Status")

c1, c2, c3 = st.columns(3)

c1.plotly_chart(
    go.Figure(go.Indicator(
        mode="gauge+number",
        value=latest["temperature"],
        title={"text": "Temperature (°C)"},
        gauge={"axis": {"range": [0, 100]}}
    )),
    use_container_width=True
)

c2.metric("Status", status)
c3.metric("Temperature", f"{arrow} {latest['temperature']:.1f} °C")

st.divider()

# --------------------------------------------------
# ✅ TEMPERATURE TREND (RESTORED)
# --------------------------------------------------
st.subheader("🌡️ LIVE Temperature Trend")
st.line_chart(df.set_index("timestamp")[["temperature"]])

st.divider()

# --------------------------------------------------
# VIBRATION TREND
# --------------------------------------------------
st.subheader("📈 LIVE Vibration Trend")
st.line_chart(df.set_index("timestamp")[["vibration"]])

# --------------------------------------------------
# FOOTER
# --------------------------------------------------
st.caption(
    "🟢 NORMAL = Safe | 🔴 CRITICAL = Unsafe | 🔺/🔻 show temperature direction"
)

time.sleep(refresh_rate)
st.rerun()
