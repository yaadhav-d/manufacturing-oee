import streamlit as st
import pandas as pd
import numpy as np
import time
from datetime import datetime

st.set_page_config(
    page_title="Live Operations Dashboard",
    layout="wide"
)

st.title("🔴 Live Operations Dashboard")

# Placeholder for live data
placeholder = st.empty()

def generate_data():
    return {
        "time": datetime.now().strftime("%H:%M:%S"),
        "temperature": np.random.uniform(60, 95),
        "vibration": np.random.uniform(2, 9),
        "units": np.random.randint(5, 20)
    }

data = []

while True:
    new_row = generate_data()
    data.append(new_row)

    df = pd.DataFrame(data[-30:])  # last 30 points

    with placeholder.container():
        col1, col2, col3 = st.columns(3)

        col1.metric("Temperature (°C)", f"{new_row['temperature']:.2f}")
        col2.metric("Vibration (mm/s)", f"{new_row['vibration']:.2f}")
        col3.metric("Units Produced", new_row["units"])

        st.line_chart(df.set_index("time")[["temperature", "vibration"]])

        # Alert
        if new_row["temperature"] > 85 or new_row["vibration"] > 7:
            st.error("🚨 CRITICAL ALERT: Machine Threshold Exceeded")

    time.sleep(5)
