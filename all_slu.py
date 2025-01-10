import typing as t
import datetime
import streamlit as st
import duckdb
import folium
from streamlit_folium import st_folium

last_date = datetime.date(2025, 1, 3)
start_date = last_date - datetime.timedelta(days=30)
downtown_seattle_lat_lon = (47.608013, -122.335167)
greenlake_lat_lon = (47.681568, -122.341133)
ship_canal_bridge_lat_lon = (47.65309, -122.32252)

categories = {
    "Encampment": ("data/csr-encampments.csv", "blue"),
    "Dumping": ("data/csr-dumping.csv", "green"),
    "Graffiti": ("data/csr-graffiti.csv", "red"),
    "Abandoned Vehicle": ("data/csr-abandoned-vehicle.csv", "darkorange"),
    "Public Litter": ("data/csr-public-litter.csv", "darkslateblue"),
}

all_csv_files = [filename for filename, _ in categories.values()]
read_all_csvs_clause = f"read_csv([{", ".join(f"'{file}'" for file in all_csv_files)}])"


conn = duckdb.connect()

st.set_page_config(page_title="All Fix-It Data In SLU")

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

st.title("All Fix-It Data In SLU, Last 30 Days")

color_guide = []
for category, (_, color) in categories.items():
    color_guide.append(f'<span style="color: {color}">{category}</span>')
color_html = ",&nbsp;".join(color_guide)
color_html = f"<span>{color_html}</span>"
st.html(color_html)


neighborhood_clause = "AND Neighborhood = 'SOUTH LAKE UNION'"

start_date_str = start_date.strftime("%Y-%m-%d")
end_date_str = last_date.strftime("%Y-%m-%d")


result = conn.execute(
    f"""
    SELECT \"Service Request Type\" as ServiceRequestType, Latitude, Longitude, Location, COUNT(*) AS ReportCount
    FROM {read_all_csvs_clause}
    WHERE \"Created Date\" >= '{start_date_str}' AND \"Created Date\" <= '{end_date_str}'
    {neighborhood_clause}
    GROUP BY \"Service Request Type\", Latitude, Longitude, Location
    """
)
df = result.fetchdf()

map = folium.Map(location=ship_canal_bridge_lat_lon, zoom_start=12)
pixel_size = 30

max_report_count = df["ReportCount"].max()

for row in df.itertuples():
    latitude = t.cast(float, row.Latitude)
    longitude = t.cast(float, row.Longitude)
    location = t.cast(str, row.Location)
    service_request_type = t.cast(str, row.ServiceRequestType)
    report_count = t.cast(int, row.ReportCount)
    category = next(
        category
        for category, (filename, _) in categories.items()
        if category.lower() in service_request_type.lower()
    )
    color = categories[category][1]
    details = f"{location} ({report_count} {category} reports)"
    marker = folium.CircleMarker(
        location=[latitude, longitude],
        popup=details,
        color=color,
        fill=color,
        radius=(report_count / max_report_count) * pixel_size,
    )
    marker.add_to(map)


st_folium(map, returned_objects=[], height=700, width=700)
