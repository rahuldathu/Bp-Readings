import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from zoneinfo import ZoneInfo
import datetime

# --- CONFIG ---
st.set_page_config(page_title="BP Tracker", layout="wide")
st.title("🩺 Blood Pressure Tracker")

# --- DATA SOURCE ---
csv_url = "https://docs.google.com/spreadsheets/d/1Fi-PN4lOhd10G7fbnhMZntog11PnXWx-LSWsDBK9UbU/export?format=csv&gid=491137158"

# --- LOAD DATA ---
@st.cache_data
def load_data(url):
    df = pd.read_csv(url)
    df.columns = df.columns.str.strip()  # Remove extra spaces
    df['Timestamp'] = pd.to_datetime(df['Timestamp'], utc=True)
    df['Timestamp'] = df['Timestamp'].dt.tz_convert(ZoneInfo("Asia/Kolkata"))
    
    # Rename columns to simpler names
    rename_map = {
        "Systolic Pressure (mmHg)": "Systolic",
        "Diastolic Pressure (mmHg)": "Diastolic",  # <-- Fixes typo
        "Pulse (bpm)": "Pulse"
    }
    df = df.rename(columns=rename_map)
    
    df = df.sort_values('Timestamp')
    df['Date'] = df['Timestamp'].dt.date
    return df

df = load_data(csv_url)

# --- DEFAULT DATE RANGE: today or latest available day ---
available_dates = df['Date'].unique()[::-1]
today = datetime.date.today()

if today in available_dates:
    default_start = default_end = today
else:
    default_start = default_end = available_dates[0]

# --- SIDEBAR FILTERS ---
st.sidebar.header("📅 Filter by Date Range")

date_range = st.sidebar.date_input(
    "Select date range:",
    value=[default_start, default_end],
    min_value=df['Date'].min(),
    max_value=df['Date'].max()
)

# --- FILTER DATA ---
if isinstance(date_range, list) and len(date_range) == 2:
    start_date, end_date = date_range
    mask = (df['Date'] >= start_date) & (df['Date'] <= end_date)
    filtered_df = df.loc[mask]
else:
    filtered_df = df.copy()

# --- TOGGLE METRICS ---
metrics = ["Systolic", "Diastolic", "Pulse"]
st.sidebar.header("📊 Select Metrics to Display")
selected_metrics = st.sidebar.multiselect(
    "Choose variables to plot:",
    options=metrics,
    default=metrics
)

# --- COLOR MAP ---
color_map = {
    "Systolic": "red",
    "Diastolic": "blue",
    "Pulse": "green"
}

# --- PLOTTING ---
if filtered_df.empty or not selected_metrics:
    st.warning("No data to display. Check your filters and selected metrics.")
else:
    st.subheader("📈 Vitals Over Time")
    fig, ax = plt.subplots(figsize=(12, 6))

    for metric in selected_metrics:
        if metric in filtered_df.columns:
            ax.plot(filtered_df['Timestamp'], filtered_df[metric], label=metric, color=color_map.get(metric))

    ax.set_xlabel("Timestamp (IST)")
    ax.set_ylabel("Measurement")
    ax.set_title("Vitals Over Time")
    ax.legend()
    ax.grid(True)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d %b, %I:%M %p', tz=ZoneInfo("Asia/Kolkata")))
    fig.autofmt_xdate()

    st.pyplot(fig)

    with st.expander("📄 View Raw Data"):
        st.dataframe(filtered_df[["Timestamp"] + selected_metrics], use_container_width=True)
