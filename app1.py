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
# DATABASE CONFIG (Railway + Streamlit Cloud)
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
# SIDEBAR CONTROLS
# --------------------------------------------------
st.sidebar.title("🔧 Controls")

MACHINES = ["M-1", "M-2", "M-3", "M-4", "M-5"]
selected_machine = st.sidebar.selectbox("Select Machine", MACHINES)

refresh_rate = st.sidebar.slider(
    "Refresh rate (seconds)", 2, 10, 5
)

pause_generation = st.sidebar.checkbox("⏸ Pause data generation")

st.sidebar.divider()
st.sidebar.subheader("🧪 Demo Controls")
inject_critical = st.sidebar.button("🚨 Add 1 Critical Sample (Reference)")

# --------------------------------------------------
# INITIALIZE MACHINE STATE (CALM BASELINE)
# --------------------------------------------------
if "machine_state" not in st.session_state:
    st.session_state.machine_state = {}
    for m in MACHINES:
        st.session_state.machine_state[m] = {
            "temperature": np.random.uniform(62, 68),
            "vibration": np.random.uniform(2.5, 3.2),
            "units": np.random.randint(13, 16)
        }

# --------------------------------------------------
# DATA GENERATION (TONED DOWN)
# --------------------------------------------------
def insert_live_data():
    cursor = conn.cursor()
    now = datetime.now()

    for m in MACHINES:
        state = st.session_state.machine_state[m]

        temp_change = np.random.uniform(-0.4, 0.4)
        if np.random.rand() < 0.05:
            temp_change += np.random.uniform(0.6, 1.2)

        temperature = max(58, min(state["temperature"] + temp_change, 82))

        vib_change = np.random.uniform(-0.08, 0.08)
        if temperature > 75:
            vib_change += np.random.uniform(0.05, 0.15)

        vibration = max(2.0, min(state["vibration"] + vib_change, 6.5))

        units = max(10, min(state["units"] + np.random.randint(-1, 2), 18))

        st.session_state.machine_state[m] = {
            "temperature": temperature,
            "vibration": vibration,
            "units": units
        }

        cursor.execute(
            """
            INSERT INTO machine_telemetry
            (timestamp, machine_id, temperature, vibration, units)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (now, m, round(temperature, 2), round(vibration, 2), units)
        )

    conn.commit()
    cursor.close()

# --------------------------------------------------
# MANUAL CRITICAL SAMPLE (REFERENCE)
# --------------------------------------------------
def insert_critical_sample(machine_id="M-4"):
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO machine_telemetry
        (timestamp, machine_id, temperature, vibration, units)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (datetime.now(), machine_id, 88.5, 7.8, 10)
    )
    conn.commit()
    cursor.close()

# --------------------------------------------------
# MAIN EXECUTION
# --------------------------------------------------
if inject_critical:
    insert_critical_sample()
    st.sidebar.success("✅ Critical reference data added (M-4)")

if not pause_generation:
    insert_live_data()

df = pd.read_sql(
    """
    SELECT timestamp, machine_id, temperature, vibration, units
    FROM machine_telemetry
    WHERE machine_id = %s
    ORDER BY timestamp DESC
    LIMIT 500
    """,
    conn,
    params=(selected_machine,)
)

if df.empty:
    st.warning("Waiting for live data...")
    time.sleep(refresh_rate)
    st.rerun()

df["timestamp"] = pd.to_datetime(df["timestamp"])
df = df.sort_values("timestamp")
latest = df.iloc[-1]

# --------------------------------------------------
# KPI LOGIC
# --------------------------------------------------
TEMP_WARNING, TEMP_CRITICAL = 80, 85
VIB_WARNING, VIB_CRITICAL = 6.5, 7.5

if latest["temperature"] >= TEMP_CRITICAL or latest["vibration"] >= VIB_CRITICAL:
    machine_status = "CRITICAL"
elif latest["temperature"] >= TEMP_WARNING or latest["vibration"] >= VIB_WARNING:
    machine_status = "WARNING"
else:
    machine_status = "NORMAL"

if "critical_cycles" not in st.session_state:
    st.session_state.critical_cycles = 0

if machine_status == "CRITICAL":
    st.session_state.critical_cycles += 1

estimated_downtime_minutes = round(
    (st.session_state.critical_cycles * refresh_rate) / 60, 2
)

estimated_units_per_hour = round(
    (latest["units"] / refresh_rate) * 3600, 2
)

# --------------------------------------------------
# PRIMARY LIVE KPIs
# --------------------------------------------------
st.subheader("📌 Primary Live KPIs")

k1, k2, k3 = st.columns(3)

k1.metric("Estimated Downtime (mins)", estimated_downtime_minutes)
k2.metric(
    "LIVE Vibration / Temperature",
    f"{latest['vibration']:.2f} mm/s | {latest['temperature']:.1f} °C"
)
k3.metric("Estimated Units / Hour", estimated_units_per_hour)

st.divider()

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
            "steps": [
                {"range": [0, 70], "color": "#4CAF50"},
                {"range": [70, 85], "color": "#FFC107"},
                {"range": [85, 100], "color": "#F44336"}
            ],
            "threshold": {"line": {"color": "black", "width": 4}, "value": 85}
        }
    ))
    fig.update_layout(height=300)
    return fig

# --------------------------------------------------
# LIVE STATUS
# --------------------------------------------------
st.subheader("📊 Live Machine Status")

c1, c2, c3 = st.columns([2, 1, 1])

c1.plotly_chart(temperature_gauge(latest["temperature"]), use_container_width=True)
c2.metric("Machine", latest["machine_id"])
c2.metric("Status", machine_status)
c3.metric("Vibration (mm/s)", f"{latest['vibration']:.2f}")

st.divider()

# --------------------------------------------------
# VIBRATION TREND
# --------------------------------------------------
st.subheader("📈 LIVE Vibration Trend")
st.line_chart(df.set_index("timestamp")[["vibration"]])

st.divider()

# --------------------------------------------------
# DAILY PEAK TEMPERATURE
# --------------------------------------------------
today_df = df[df["timestamp"].dt.date == datetime.now().date()]

if not today_df.empty:
    peak = today_df.loc[today_df["temperature"].idxmax()]
    st.subheader("🔥 Today’s Peak Temperature")

    a, b, c = st.columns(3)
    a.metric("Peak Temp (°C)", peak["temperature"])
    b.metric("Units at Peak", int(peak["units"]))
    c.metric("Vibration at Peak", peak["vibration"])

    window_df = today_df[
        (today_df["timestamp"] >= peak["timestamp"] - timedelta(minutes=10)) &
        (today_df["timestamp"] <= peak["timestamp"] + timedelta(minutes=10))
    ]

    st.subheader("🕒 10-Minute Window Around Peak")
    st.line_chart(window_df.set_index("timestamp")[["temperature", "vibration"]])

# --------------------------------------------------
# CRITICAL ALERT NOTES
# --------------------------------------------------
st.divider()
st.caption(
    "🔴 **Critical Alert Notes**  \n"
    "• Critical Alert is triggered when **Temperature ≥ 85 °C** or "
    "**Vibration ≥ 7.5 mm/s**.  \n"
    "• These indicate unsafe operating conditions requiring immediate attention.  \n"
    "• **Estimated Downtime** represents sustained time spent in critical state.  \n"
    "• Alerts are sensor-based and updated in real time."
)

st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")

# --------------------------------------------------
# AUTO REFRESH
# --------------------------------------------------
time.sleep(refresh_rate)
st.rerun()
