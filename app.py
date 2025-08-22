import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import gspread
from google.oauth2.service_account import Credentials
from datetime import date
import json

# --- CONFIG ---
st.set_page_config(page_title="BP Tracker", layout="wide")
st.title("🩺 Blood Pressure Tracker")

# --- GOOGLE SHEETS API SETUP ---
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

# Load service account info from Streamlit secrets
service_account_info = st.secrets["gcp_service_account"]

# Create credentials object
creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPES)

# Authorize gspread client
client = gspread.authorize(creds)

# Your private Google Sheet URL or ID
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1Fi-PN4lOhd10G7fbnhMZntog11PnXWx-LSWsDBK9UbU"

@st.cache_data(show_spinner=False)
def load_data():
    # Open sheet by URL
    sheet = client.open_by_url(SPREADSHEET_URL)
    worksheet = sheet.get_worksheet(0)  # first sheet (you can change index if needed)
    
    # Fetch all data as list of dicts
    data = worksheet.get_all_records()
    
    # Convert to DataFrame
    df = pd.DataFrame(data)
    df.columns = df.columns.str.strip()
    df['Timestamp'] = pd.to_datetime(df['Timestamp'])  # assumed IST already
    df['Date'] = df['Timestamp'].dt.date
    return df

df = load_data()

# --- Variables as in Google Sheets ---
variables = [
    "Systolic Pressure (mmHg)",
    "Diastolic Pressure (mmHg)",
    "Pulse (bpm)"
]

# --- Emergency ranges ---
emergency_ranges = {
    "Systolic Pressure (mmHg)": (90, 129),
    "Diastolic Pressure (mmHg)": (60, 79),
    "Pulse (bpm)": (60, 100),
}

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
            # Plot line with markers on all points
            ax.plot(filtered_df['Timestamp'], filtered_df[metric], 
                    label=metric, color=color_map.get(metric, None), marker='o')

            # Identify emergency points outside safe ranges
            low, high = emergency_ranges[metric]
            emergency_mask = (filtered_df[metric] < low) | (filtered_df[metric] > high)
            emergency_points = filtered_df.loc[emergency_mask]

            # Plot emergency points with red star marker, bigger size
            if not emergency_points.empty:
                ax.scatter(emergency_points['Timestamp'], emergency_points[metric],
                           color='red', marker='*', s=150, label=f'{metric} - Emergency')

    ax.set_xlabel("Timestamp (IST)")
    ax.set_ylabel("Measurement")
    ax.set_title("Vitals Over Time")
    
    # Handle duplicate labels in legend
    handles, labels = ax.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    ax.legend(by_label.values(), by_label.keys())

    ax.grid(True)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d %b, %I:%M %p'))
    fig.autofmt_xdate()

    st.pyplot(fig)

# --- RAW DATA ---
with st.expander("📄 View Raw Data"):
    cols_to_show = ["Timestamp"] + [m for m in selected_metrics if m in filtered_df.columns]
    st.dataframe(filtered_df[cols_to_show], use_container_width=True)
