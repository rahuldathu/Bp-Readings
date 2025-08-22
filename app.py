import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import date

# --- CONFIG ---
st.set_page_config(page_title="BP Tracker", layout="wide")
st.title("🩺 Blood Pressure Tracker")

# --- DATA SOURCE ---
csv_url = "https://docs.google.com/spreadsheets/d/1Fi-PN4lOhd10G7fbnhMZntog11PnXWx-LSWsDBK9UbU/export?format=csv&gid=491137158"

# --- LOAD DATA ---
@st.cache_data
def load_data(url):
    df = pd.read_csv(url)
    df.columns = df.columns.str.strip()
    df['Timestamp'] = pd.to_datetime(df['Timestamp'])  # assume IST already
    df['Date'] = df['Timestamp'].dt.date
    return df

df = load_data(csv_url)

# --- Variables as in Google Sheets ---
variables = [
    "Systolic Pressure (mmHg)",
    "Diastolic Pressure (mmHg)",
    "Pulse (bpm)"
]

# --- DEFAULT DATE RANGE ---
available_dates = df['Date'].unique()[::-1]
today = date.today()
if today in available_dates:
    default_start = default_end = today
else:
    default_start = default_end = available_dates[0]

# --- SIDEBAR: date range + toggles ---
with st.sidebar:
    st.header("Filter & Metrics")
    
    date_range = st.date_input(
        "Select date range:",
        value=[default_start, default_end],
        min_value=df['Date'].min(),
        max_value=df['Date'].max(),
        key="date_filter"
    )
    
    selected_metrics = st.multiselect(
        "Select metrics to show:",
        options=variables,
        default=variables,
        key="metric_filter"
    )

# --- FILTER DATA ---
if isinstance(date_range, list) and len(date_range) == 2:
    start_date, end_date = date_range
    mask = (df['Date'] >= start_date) & (df['Date'] <= end_date)
    filtered_df = df.loc[mask]
else:
    filtered_df = df.copy()

# --- PLOTTING ---
st.subheader("📈 Vitals Over Time")

if filtered_df.empty:
    st.warning("No data available for selected date range.")
elif not selected_metrics:
    st.info("Please select at least one metric to plot.")
else:
    fig, ax = plt.subplots(figsize=(12, 6))

    color_map = {
        "Systolic Pressure (mmHg)": "red",
        "Diastolic Pressure (mmHg)": "blue",
        "Pulse (bpm)": "green"
    }

    for metric in selected_metrics:
        if metric in filtered_df.columns:
            ax.plot(filtered_df['Timestamp'], filtered_df[metric], label=metric, color=color_map.get(metric, None))

    ax.set_xlabel("Timestamp (IST)")
    ax.set_ylabel("Measurement")
    ax.set_title("Vitals Over Time")
    ax.legend()
    ax.grid(True)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d %b, %I:%M %p'))
    fig.autofmt_xdate()

    st.pyplot(fig)

# --- RAW DATA ---
with st.expander("📄 View Raw Data"):
    cols_to_show = ["Timestamp"] + [m for m in selected_metrics if m in filtered_df.columns]
    st.dataframe(filtered_df[cols_to_show], use_container_width=True)
