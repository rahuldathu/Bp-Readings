import streamlit as st
import pandas as pd
import plotly.graph_objs as go
from datetime import date
import gspread
from google.oauth2 import service_account

# --- PAGE CONFIG ---
st.set_page_config(page_title="BP Tracker", layout="wide")
st.title("🩺 Blood Pressure Tracker")

# --- GOOGLE SHEETS AUTH ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=scope
)

client = gspread.authorize(credentials)
sheet = client.open_by_key("1Fi-PN4lOhd10G7fbnhMZntog11PnXWx-LSWsDBK9UbU")

try:
    worksheet = sheet.worksheet("Form Responses 1")
except gspread.exceptions.WorksheetNotFound:
    st.error("The worksheet 'Form Responses 1' was not found in the spreadsheet.")
    st.stop()

data = worksheet.get_all_records()

# --- LOAD DATA ---
df = pd.DataFrame(data)
df.columns = df.columns.str.strip()

# Rename columns for shorter display
column_rename_map = {
    "Systolic Pressure (mmHg)": "Systolic (mmHg)",
    "Diastolic Pressure (mmHg)": "Diastolic (mmHg)",
    "Pulse (bpm)": "Pulse (bpm)"
}
df.rename(columns=column_rename_map, inplace=True)

# Parse timestamp
df['Timestamp'] = pd.to_datetime(df['Timestamp'])
df['Date'] = df['Timestamp'].dt.date

# --- METRIC SETTINGS ---
variables = list(column_rename_map.values())

emergency_ranges = {
    "Systolic (mmHg)": (90, 129),
    "Diastolic (mmHg)": (60, 80),
    "Pulse (bpm)": (60, 100),
}

# --- COLOR MAP ---
color_map = {
    "Systolic (mmHg)": "red",
    "Diastolic (mmHg)": "blue",
    "Pulse (bpm)": "green"
}

# --- DEFAULT DATE RANGE ---
available_dates = df['Date'].unique()[::-1]
today = date.today()
default_start = default_end = today if today in available_dates else available_dates[0]

# --- SIDEBAR ---
with st.sidebar:
    st.header("Filters")

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
if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
    start_date, end_date = date_range
    start_datetime = pd.to_datetime(start_date)
    end_datetime = pd.to_datetime(end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
    mask = (df['Timestamp'] >= start_datetime) & (df['Timestamp'] <= end_datetime)
    filtered_df = df.loc[mask]
else:
    filtered_df = df.copy()

# --- GRAPH ---
st.subheader("📈 Vitals Over Time")

if filtered_df.empty:
    st.warning("No data available for selected date range.")
elif not selected_metrics:
    st.info("Please select at least one metric to plot.")
else:
    fig = go.Figure()

    for metric in selected_metrics:
        fig.add_trace(go.Scatter(
            x=filtered_df['Timestamp'],
            y=filtered_df[metric],
            mode='lines+markers',
            name=metric,
            marker=dict(size=8, color=color_map.get(metric, 'black')),
            line=dict(color=color_map.get(metric, 'black')),
            hovertemplate=f'%{{x|%d %b, %I:%M %p}}<br>{metric}: %{{y}}<extra></extra>',
        ))

        # Emergency points in red stars
        low, high = emergency_ranges[metric]
        emergency_mask = (filtered_df[metric] < low) | (filtered_df[metric] > high)
        emergencies = filtered_df[emergency_mask]

        if not emergencies.empty:
            fig.add_trace(go.Scatter(
                x=emergencies['Timestamp'],
                y=emergencies[metric],
                mode='markers',
                marker=dict(color='red', symbol='star', size=14),
                showlegend=False,
                hovertemplate=f'🚨 {metric}: %{{y}}<br>%{{x|%d %b, %I:%M %p}}<extra></extra>',
            ))

    fig.update_layout(
        xaxis_title="Timestamp (IST)",
        yaxis_title="Measurement",
        hovermode="closest",
        margin=dict(t=50, r=10, l=10, b=40),
        height=500,
    )

    st.plotly_chart(fig, use_container_width=True)

# --- HIGHLIGHT EMERGENCIES IN RAW DATA ---
cols_to_show = ["Timestamp"] + [m for m in selected_metrics if m in filtered_df.columns]

def highlight_emergencies(row):
    styles = []
    for col in cols_to_show:
        if col in emergency_ranges:
            low, high = emergency_ranges[col]
            value = row[col]
            if pd.notnull(value) and (value < low or value > high):
                styles.append("background-color: #FFCCCC")
            else:
                styles.append("")
        else:
            styles.append("")  # No style for non-metric columns like Timestamp
    return styles

with st.expander("📄 View Raw Data"):
    styled_df = filtered_df[cols_to_show].style.apply(highlight_emergencies, axis=1)
    st.dataframe(styled_df, use_container_width=True)
