import typing as t
import datetime
import streamlit as st
import duckdb
import folium
from streamlit_folium import st_folium

last_date = datetime.date(2025, 1, 3)
downtown_seattle_lat_lon = (47.608013, -122.335167)
greenlake_lat_lon = (47.681568, -122.341133)
ship_canal_bridge_lat_lon = (47.65309, -122.32252)

categories = {
    "Encampments": "data/csr-encampments.csv",
    "Dumping": "data/csr-dumping.csv",
    "Graffiti": "data/csr-graffiti.csv",
    "Abandoned Vehicles": "data/csr-abandoned-vehicle.csv",
    "Public Litter": "data/csr-public-litter.csv",
    "911 Pri 1 & 2": "data/911-pri1-pri2.csv",
}

supports_neighborhoods = set(
    category for category in categories.keys() if category != "911 Pri 1 & 2"
)

conn = duckdb.connect()

st.set_page_config(page_title="Seattle Find It Fix It")

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

st.title("Seattle Find It Fix It")

# Set it to wide mode

# Make a selector for the date range, allowing the following options:
# - All dates
# - Calendar Year 2024
# - Last 90 days
# - Last 30 days

show_kind = st.segmented_control(
    "Display",
    ["Top 15", "Everything"],
    default="Top 15",
)
if show_kind == "Everything":
    limit = None
    limit_clause = ""
else:
    show_kind = "Top 15"
    limit = 15
    limit_clause = f"LIMIT {limit}"

show_table = st.segmented_control(
    "Show Table",
    list(categories.keys()),
    default=list(categories.keys())[0],
)
if show_table is None:
    show_table = list(categories.keys())[0]

date_range = st.segmented_control(
    "Select Date Range",
    ["All Dates", "CY2024+", "Most Recent 90 Days", "Most Recent 30 Days"],
    default="Most Recent 30 Days",
)
if date_range is None:
    date_range = "Most Recent 30 Days"

smoothing = st.segmented_control(
    "Location Smoothing",
    ["None", "A Little", "More"],
    default="None",
)
if smoothing is None:
    smoothing = "None"

if show_table in supports_neighborhoods:
    neighborhoods_result = conn.execute(
        f"SELECT DISTINCT Neighborhood FROM read_csv('{categories[show_table]}')"
    )
    neighborhoods_df = neighborhoods_result.fetchdf()
    # Get just the values from the "Neighborhood" column of the df
    neighborhoods = neighborhoods_df["Neighborhood"].values
    sorted_neighborhoods = list(sorted(n.title() for n in neighborhoods if n))
    sorted_neighborhoods = ["(all)"] + sorted_neighborhoods
    neighborhood = st.selectbox("Select Neighborhood", sorted_neighborhoods, index=0)
else:
    neighborhood = "(all)"

neighborhood_clause = (
    f"AND Neighborhood = '{neighborhood.upper()}'"
    if neighborhood and neighborhood != "(all)"
    else ""
)

st.html(f"<p>Data ends on {last_date}</p>")


if date_range == "All Dates":
    start_date = datetime.date(2020, 1, 1)
    end_date = last_date
elif date_range == "CY2024+":
    start_date = datetime.date(2024, 1, 1)
    end_date = last_date
elif date_range == "Most Recent 90 Days":
    end_date = last_date
    start_date = end_date - datetime.timedelta(days=90)
elif date_range == "Most Recent 30 Days":
    end_date = last_date
    start_date = end_date - datetime.timedelta(days=30)

if smoothing == "None":
    round_places = None
elif smoothing == "A Little":
    round_places = 3
elif smoothing == "More":
    round_places = 2


start_date_str = start_date.strftime("%Y-%m-%d")
end_date_str = end_date.strftime("%Y-%m-%d")

# Count rows in the table matching dates
assert isinstance(show_table, str)
total_result = conn.execute(
    f"SELECT COUNT(*) as TotalReports FROM read_csv('{categories[show_table]}') WHERE \"Created Date\" >= '{start_date_str}' AND \"Created Date\" <= '{end_date_str}' {neighborhood_clause}"
)
total_df = total_result.fetchdf()
total_reports = int(total_df.iloc[0]["TotalReports"])

# Load the data
if round_places is None:
    result = conn.execute(
        f"SELECT Location, Latitude, Longitude, COUNT(*) as ReportCount FROM read_csv('{categories[show_table]}') WHERE \"Created Date\" >= '{start_date_str}' AND \"Created Date\" <= '{end_date_str}' {neighborhood_clause} AND Latitude IS NOT NULL AND Longitude IS NOT NULL AND Latitude != 0 AND Longitude != 0 AND Latitude != -1 AND Longitude != -1 GROUP BY Location, Latitude, Longitude ORDER BY COUNT(*) DESC {limit_clause}"
    )
else:
    result = conn.execute(
        f"SELECT ANY_VALUE(Location) as Location, AVG(Latitude) as Latitude, AVG(Longitude) as Longitude, COUNT(*) as ReportCount FROM read_csv('{categories[show_table]}') WHERE \"Created Date\" >= '{start_date_str}' AND \"Created Date\" <= '{end_date_str}' {neighborhood_clause} AND Latitude IS NOT NULL AND Longitude IS NOT NULL AND Latitude != 0 AND Longitude != 0 AND Latitude != -1 AND Longitude != -1 GROUP BY ROUND(Latitude, {round_places}), ROUND(Longitude, {round_places}) ORDER BY COUNT(*) DESC {limit_clause}"
    )

# Get basic dataset
df = result.fetchdf()
try:
    max_reports = int(df["ReportCount"].max())
except ValueError:
    max_reports = 1


assert isinstance(show_kind, str)
st.html(
    f"<h3>{show_table} ({show_kind.lower()} from {total_reports:,d} reports in timeframe)</h3>"
)
st.write(df)

# Create a map
map = folium.Map(location=ship_canal_bridge_lat_lon, zoom_start=12)


pixel_size = 30


for row in df.itertuples():
    latitude = t.cast(float, row.Latitude)
    longitude = t.cast(float, row.Longitude)
    location = t.cast(str, row.Location)
    report_count = t.cast(int, row.ReportCount)
    details = f"{location} ({report_count} {show_table} reports)"
    marker = folium.CircleMarker(
        location=[latitude, longitude],
        popup=details,
        color="#0000ff",
        fill="#0000ff",
        radius=(report_count / max_reports) * pixel_size,
    )
    marker.add_to(map)

# Create cluster markers that show the number of reports in the cluster, and
# when zoomed in, show the individual reports
marker_cluster = folium.plugins.MarkerCluster().add_to(map)
for row in df.itertuples():
    latitude = t.cast(float, row.Latitude)
    longitude = t.cast(float, row.Longitude)
    location = t.cast(str, row.Location)
    report_count = t.cast(int, row.ReportCount)
    details = f"{location} ({report_count} {show_table} reports)"
    marker = folium.Marker(location=[latitude, longitude], popup=details)
    marker.add_to(marker_cluster)

st_folium(map, returned_objects=[], height=700, width=700)
