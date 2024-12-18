import typing as t
import datetime
import streamlit as st
import duckdb
import folium
from streamlit_folium import st_folium


last_date = datetime.date(2024, 12, 16)
downtown_seattle_lat_lon = (47.608013, -122.335167)
greenlake_lat_lon = (47.681568, -122.341133)
ship_canal_bridge_lat_lon = (47.65309, -122.32252)

file_path = "data/encampments.csv"
conn = duckdb.connect()

st.set_page_config(page_title="Encampments in Seattle")

st.markdown(
    """
    <style>
        .reportview-container {
            margin-top: -2em;
        }
        #MainMenu {visibility: hidden;}
        .stDeployButton {display:none;}
        .stAppDeployButton {display:none;}
        footer {visibility: hidden;}
        #stDecoration {display:none;}
    </style>
""",
    unsafe_allow_html=True,
)

st.title("Encampments in Seattle")

# Set it to wide mode

# Make a selector for the date range, allowing the following options:
# - All dates
# - Calendar Year 2024
# - Last 90 days
# - Last 30 days

date_range = st.segmented_control(
    "Select Date Range",
    ["All Dates", "CY2024", "Most Recent 90 Days", "Most Recent 30 Days"],
    default="All Dates",
)

if date_range == "All Dates":
    start_date = datetime.date(2020, 1, 1)
    end_date = last_date
elif date_range == "CY2024":
    start_date = datetime.date(2024, 1, 1)
    end_date = last_date
elif date_range == "Most Recent 90 Days":
    end_date = last_date
    start_date = end_date - datetime.timedelta(days=90)
elif date_range == "Most Recent 30 Days":
    end_date = last_date
    start_date = end_date - datetime.timedelta(days=30)


start_date_str = start_date.strftime("%Y-%m-%d")
end_date_str = end_date.strftime("%Y-%m-%d")

limit = 15

# Load the data
result = conn.execute(
    f"SELECT Location, Latitude, Longitude, COUNT(*) as ReportCount FROM read_csv('{file_path}') WHERE \"Created Date\" >= '{start_date_str}' AND \"Created Date\" <= '{end_date_str}' GROUP BY Location, Latitude, Longitude ORDER BY COUNT(*) DESC LIMIT {limit}"
)

df = result.fetchdf()

# Display the data
st.write(df)

# Create a map
map = folium.Map(location=ship_canal_bridge_lat_lon, zoom_start=12)

max_reports = float(df["ReportCount"].max())

pixel_size = 25

for row in df.itertuples():
    latitude = t.cast(float, row.Latitude)
    longitude = t.cast(float, row.Longitude)
    location = t.cast(str, row.Location)
    report_count = t.cast(int, row.ReportCount)
    details = f"{location} ({report_count} reports)"
    marker = folium.CircleMarker(
        location=[latitude, longitude],
        popup=details,
        radius=(report_count / max_reports) * pixel_size,
    )
    marker.add_to(map)

st_folium(map, returned_objects=[], height=700, width=700)
