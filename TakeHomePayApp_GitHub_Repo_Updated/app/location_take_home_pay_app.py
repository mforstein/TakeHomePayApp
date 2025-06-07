
import streamlit as st
import pandas as pd
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import folium
from streamlit_folium import st_folium

st.set_page_config(layout="wide")

# Sidebar inputs
st.sidebar.title("Settings")

if st.sidebar.button("About"):
    st.sidebar.info("Take Home Pay App\nJune, 2025\nBy Micah Forstein")

salary = st.sidebar.slider("Annual Salary ($)", 1, 500000, 100000, step=5000)
gas_price = st.sidebar.slider("Gas Price ($/gallon)", 1.00, 30.00, 3.00, step=0.1)
mpg = st.sidebar.slider("Vehicle Fuel Efficiency (MPG)", 10, 60, 30, step=1)
car_payment = st.sidebar.number_input("Car Payment (Annual)", 0, 60000, 5000, step=500)
car_insurance = st.sidebar.number_input("Car Insurance (Annual)", 0, 10000, 1500, step=100)
healthcare = st.sidebar.number_input("Healthcare Premiums (Annual)", 0, 20000, 9000, step=500)
home_address = st.sidebar.text_input("Enter Home Address", "1600 Pennsylvania Ave NW, Washington, DC 20500")
max_distance = st.sidebar.slider("Maximum Distance from Home (miles)", 3, 300, 150, step=10)

# Commute days
st.sidebar.markdown("### Commute Days")
commute_days = {
    "Monday": st.sidebar.checkbox("Monday", value=True),
    "Tuesday": st.sidebar.checkbox("Tuesday", value=True),
    "Wednesday": st.sidebar.checkbox("Wednesday", value=True),
    "Thursday": st.sidebar.checkbox("Thursday", value=True),
    "Friday": st.sidebar.checkbox("Friday", value=True),
}
selected_days = sum(commute_days.values())

# City coordinates
df_cities = pd.DataFrame({
    "City": ["Washington, DC", "Baltimore, MD", "Richmond, VA", "Philadelphia, PA", "Remote"],
    "Latitude": [38.9072, 39.2904, 37.5407, 39.9526, None],
    "Longitude": [-77.0369, -76.6122, -77.4360, -75.1652, None]
})

# Get home coordinates
geolocator = Nominatim(user_agent="take_home_pay_app")
home_location = geolocator.geocode(home_address)
if not home_location:
    st.error("Could not geocode home address.")
    st.stop()
home_coords = (home_location.latitude, home_location.longitude)

# Compute distances
def compute_distance(row):
    if pd.notna(row["Latitude"]) and pd.notna(row["Longitude"]):
        return round(geodesic(home_coords, (row["Latitude"], row["Longitude"])).miles, 1)
    return 0

df_cities["Distance"] = df_cities.apply(compute_distance, axis=1)

# Filter by distance
df_filtered = df_cities[df_cities["City"] == "Remote"]
if selected_days > 0:
    df_filtered = pd.concat([
        df_filtered,
        df_cities[(df_cities["City"] != "Remote") & (df_cities["Distance"] <= max_distance)]
    ], ignore_index=True)

# Calculate financials
def calculate_financials(row):
    is_remote = row["City"] == "Remote" or selected_days == 0
    commute_miles = 0 if is_remote else row["Distance"] * 2 * 48 * (selected_days / 5)
    gas_cost = 0 if is_remote else (commute_miles / mpg) * gas_price
    car = 0 if is_remote else car_payment
    insurance = 0 if is_remote else car_insurance
    federal = max(0.1 * salary - 1000, 0)
    state = max(0.05 * salary - 500, 0)
    fica = 0.062 * salary + 0.0145 * salary
    total_deductions = gas_cost + federal + state + fica + car + insurance + healthcare
    net_pay = salary - total_deductions
    return pd.Series({
        "Commute Miles": round(commute_miles, 1),
        "Gas Cost": round(gas_cost, 2),
        "Federal Tax": round(federal, 2),
        "State Tax": round(state, 2),
        "FICA": round(fica, 2),
        "Car Payment": round(car, 2),
        "Car Insurance": round(insurance, 2),
        "Healthcare": round(healthcare, 2),
        "Net Pay": round(net_pay, 2)
    })

df_financials = df_filtered.apply(calculate_financials, axis=1)
df_final = pd.concat([df_filtered[["City", "Latitude", "Longitude", "Distance"]], df_financials], axis=1)
df_final = df_final.dropna(subset=['Latitude', 'Longitude'])  # Ensure valid coordinates

# Display map
st.header("Map of Cities")
import folium
from streamlit_folium import st_folium
m = folium.Map(location=home_coords, zoom_start=8)
for _, row in df_final.iterrows():
    popup = f"{row['City']}<br>Net Pay: ${row['Net Pay']:,.2f}"
    color = "green" if row["City"] == "Remote" else "blue"
    folium.Marker([row["Latitude"], row["Longitude"]], popup=popup, icon=folium.Icon(color=color)).add_to(m)
st_folium(m, width=800, height=500)

# Display data table
st.header("Take-Home Pay Comparison Table")
st.dataframe(df_final[[
    "City", "Distance", "Commute Miles", "Gas Cost",
    "Federal Tax", "State Tax", "FICA",
    "Car Payment", "Car Insurance", "Healthcare", "Net Pay"
]])
