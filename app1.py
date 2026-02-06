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
# DATABASE CONFIG (Railway + Streamlit Cloud SAFE)
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
    "Refresh rate (seconds)",
    min_value=2,
    max_value=10,
    value=5
)

# --------------------------------------------------
# INITIALIZE MACHINE STATE (STATEFUL + REALISTIC)
# --------------------------------------------------
if "machine_state" not in st.session_state:
    st.session_state.machine_state = {}
    for m in MACHINES:
        st.session_state.machine_state[m] = {
            "temperature": np.random.uniform(65, 72),
            "vibration": np.random.uniform(2.5, 3.5),
            "units": np.random.randint(12, 16)
        }

# --------------------------------------------------
# RATIONAL LIVE DATA GENERATION
# --------------------------------------------------
def insert_live_data():
    cursor = conn.cursor()
    now = datetime.now()

    for m in MACHINES:
        state = st.session_state.machine_state[m]

        # ---- Temperature: slow thermal drift ----
        temp_change = np.random.uniform(-0.3, 0.6)
        temperature = state["temperature"] + temp_change
        temperature = max(60, min(temperature, 92))

        # ---- Vibration: wear + thermal stress ----
        vib_change = np.random.uniform(-0.05, 0.12)
        if temperature > 80:
            vib_change += np.random.uniform(0.1, 0.25)

        vibration = state["vibration"] + vib_change
        vibration = max(1.5, min(vibration, 9))

        # ---- Units: stable output ----
        units = state["units"] + np.random.randint(-1, 2)
        units = max(8, min(units, 20))

        # ---- Persist state ----
        st.session_state.machine_state[m] = {
            "temperature": temperature,
            "vibration": vibration,
            "units": units
        }

        # ---- Insert into DB ----
        cursor.execute(
            """
            INSERT INTO machine_telemetry
            (timestamp, machine_id, temperature, vibration, units)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                now,
                m,
                round(temperature, 2),
                round(vibration, 2),
                units
            )
        )

    conn.commit()
    cursor.close()

# --------------------------------------------------
# FETCH DATA
# --------------------------------------------------
def fetch_data(machine_id):
    query = """
        SELECT timestamp, machine_id, temperature, vibration, units
        FROM machine_telemetry
        WHERE machine_id = %s
        ORDER BY timestamp DESC
        LIMIT 500
    """
    return pd.read_sql(query, conn, params=(machine_id,))

# --------------------------------------------------
# MAIN EXECUTION
# --------------------------------------------------
insert_live_data()
df = fetch_data(selected_machine)

if df.empty:
    st.warning("Waiting for live data...")
    time.sleep(refresh_rate)
    st.rerun()

df["timestamp"] = pd.to_datetime(df["timestamp"])
df = df.sort_values("timestamp")
latest = df.iloc[-1]

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
                "value": 85
            }
        }
    ))
    fig.update_layout(height=300, margin=dict(t=40, b=0))
    return fig

# --------------------------------------------------
# LIVE STATUS
# --------------------------------------------------
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
    if latest["vibration"] >= 7.5:
        st.error("🚨 Critical vibration")
    elif latest["vibration"] >= 6.5:
        st.warning("⚠️ High vibration")

st.divider()

# --------------------------------------------------
# VIBRATION TREND
# --------------------------------------------------
st.subheader("📈 Vibration Trend (mm/s)")
st.line_chart(df.set_index("timestamp")[["vibration"]])

st.divider()

# --------------------------------------------------
# TODAY PEAK TEMPERATURE ANALYSIS
# --------------------------------------------------
today = datetime.now().date()
today_df = df[df["timestamp"].dt.date == today]

if not today_df.empty:
    peak_row = today_df.loc[today_df["temperature"].idxmax()]

    st.subheader("🔥 Today’s Peak Temperature Analysis")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Machine", peak_row["machine_id"])
    c2.metric("Max Temp (°C)", peak_row["temperature"])
    c3.metric("Units", int(peak_row["units"]))
    c4.metric("Vibration", peak_row["vibration"])

    if peak_row["temperature"] >= 85:
        st.error("🚨 Critical temperature event")
    elif peak_row["temperature"] >= 80:
        st.warning("⚠️ High temperature")
    else:
        st.success("✅ Temperature normal")

    st.subheader("🕒 10-Minute Window Around Spike")

    peak_time = peak_row["timestamp"]
    window_df = today_df[
        (today_df["timestamp"] >= peak_time - timedelta(minutes=10)) &
        (today_df["timestamp"] <= peak_time + timedelta(minutes=10))
    ]

    st.line_chart(
        window_df.set_index("timestamp")[["temperature", "vibration"]]
    )

st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")

# --------------------------------------------------
# AUTO REFRESH (SAFE)
# --------------------------------------------------
time.sleep(refresh_rate)
st.rerun()
