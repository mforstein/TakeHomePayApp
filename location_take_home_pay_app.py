import streamlit as st
import pandas as pd
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import folium
from streamlit_folium import st_folium
from time import sleep

st.set_page_config(layout="wide")

# One-time refresh to fix initial spacing issues
if "page_reloaded" not in st.session_state:
    st.session_state["page_reloaded"] = True
    st.markdown(
        """
        <script>
        setTimeout(function() {
            window.location.reload();
        }, 1000);
        </script>
        """,
        unsafe_allow_html=True
    )

# Safe geocode wrapper
def safe_geocode(address, retries=3, delay=2):
    for _ in range(retries):
        try:
            return geolocator.geocode(address, timeout=10)
        except:
            sleep(delay)
    return None

# Load and clean data
df = pd.read_csv("us_cities_cleaned_reduced_formatted.csv")
df.dropna(subset=["Latitude", "Longitude", "AverageSalary"], inplace=True)

# Sidebar
st.sidebar.title("Settings")
salary = st.sidebar.slider("Annual Salary ($)", 10000, 600000, 100000, step=5000)
gas_price = st.sidebar.slider("Gas Price ($/gallon)", 1.00, 25.00, 3.00, step=0.1)
mpg = st.sidebar.slider("Vehicle Fuel Efficiency (MPG)", 10, 160, 30, step=1)
car_payment = st.sidebar.number_input("Car Payment (Annual)", 0, 300000, 5000, step=500)
car_insurance = st.sidebar.number_input("Car Insurance (Annual)", 0, 50000, 1500, step=100)
healthcare = st.sidebar.number_input("Healthcare Premiums (Annual)", 0, 90000, 9000, step=500)

st.sidebar.markdown("**Select Commute Days**")
commute_days = {
    "Monday": st.sidebar.checkbox("Monday", True),
    "Tuesday": st.sidebar.checkbox("Tuesday", True),
    "Wednesday": st.sidebar.checkbox("Wednesday", True),
    "Thursday": st.sidebar.checkbox("Thursday", True),
    "Friday": st.sidebar.checkbox("Friday", True),
}
selected_days = sum(commute_days.values())

federal_tax = st.sidebar.slider("Federal Tax", 0, 300000, 15500, step=500)
state_tax = st.sidebar.slider("State Tax", 0, 200000, 7750, step=250)

home_address = st.sidebar.text_input("Enter Home Address", "1600 Pennsylvania Ave NW, Washington, DC")
max_distance = st.sidebar.slider("Maximum Distance (miles)", 3, 300, 150, step=5)
custom_locations = st.sidebar.text_area("Add Custom Labeled Locations (Label,Address)", placeholder="My Job,123 Main St, City, State")
remove_city = st.sidebar.text_input("Remove City from List", "")
add_city = st.sidebar.text_input("Add City to List", "")

geolocator = Nominatim(user_agent="take_home_pay_app")
home_location = safe_geocode(home_address)
if not home_location:
    st.error("Home address could not be geocoded.")
    st.stop()
home_coords = (home_location.latitude, home_location.longitude)

# Add city
if add_city:
    result = safe_geocode(add_city)
    if result:
        city_distance = geodesic((result.latitude, result.longitude), home_coords).miles
        if city_distance > max_distance:
            st.warning(f"{add_city} is {city_distance:.1f} miles away, which exceeds the max distance of {max_distance} miles.")
            if st.sidebar.button("Update max distance to include this city"):
                max_distance = int(city_distance) + 10

# Recompute distances
df["Distance"] = df.apply(lambda row: geodesic((row["Latitude"], row["Longitude"]), home_coords).miles, axis=1)
df = df[df["Distance"] <= max_distance]
df_filtered = df.copy()

# Remove cities
if remove_city:
    df_filtered = df_filtered[df_filtered["City"] != remove_city]

# Add city again (to df_filtered)
if add_city and result:
    df_filtered = pd.concat([
        df_filtered,
        pd.DataFrame([{
            "City": add_city,
            "State": "",
            "Latitude": result.latitude,
            "Longitude": result.longitude,
            "AverageSalary": salary,
            "Distance": city_distance
        }])
    ])

# Add custom labeled addresses
custom_rows = []
if custom_locations.strip():
    for line in custom_locations.split("\n"):
        if "," in line:
            label, *address_parts = line.split(",")
            address = ",".join(address_parts).strip()
            result = safe_geocode(address)
            if result:
                distance = geodesic((result.latitude, result.longitude), home_coords).miles
                custom_rows.append({
                    "City": label.strip(),
                    "State": "",
                    "Latitude": result.latitude,
                    "Longitude": result.longitude,
                    "AverageSalary": salary,
                    "Distance": distance
                })
if custom_rows:
    df_filtered = pd.concat([pd.DataFrame(custom_rows), df_filtered], ignore_index=True)

# Add "Remote" row
df_filtered = pd.concat([
    pd.DataFrame([{
        "City": "Remote",
        "State": "",
        "Latitude": home_coords[0],
        "Longitude": home_coords[1],
        "AverageSalary": salary,
        "Distance": 0
    }]),
    df_filtered
], ignore_index=True)

# Financial calculations
def calculate_financials(row):
    is_remote = row["City"].lower() == "remote"
    commute_miles = 0 if is_remote else row["Distance"] * 2 * 48 * (selected_days / 5)
    gas_cost = 0 if is_remote else (commute_miles / mpg) * gas_price
    car = 0 if is_remote else car_payment
    insurance = 0 if is_remote else car_insurance
    fica = 0.062 * salary + 0.0145 * salary
    total_deductions = federal_tax + state_tax + fica + gas_cost + car + insurance + healthcare
    net_pay = salary - total_deductions
    return pd.Series({
        "Commute Miles": round(commute_miles, 2),
        "Gas Cost": round(gas_cost, 2),
        "Federal Tax": federal_tax,
        "State Tax": state_tax,
        "FICA": round(fica, 2),
        "Car Payment": car,
        "Car Insurance": insurance,
        "Healthcare": healthcare,
        "Net Pay": round(net_pay, 2)
    })

# Apply calculations
df_financials = df_filtered.apply(calculate_financials, axis=1)

# Clean duplicate columns
for col in df_financials.columns:
    if col in df_filtered.columns:
        df_filtered.drop(columns=col, inplace=True)

df_final = pd.concat([df_filtered.reset_index(drop=True), df_financials], axis=1)
df_final = df_final.loc[:, ~df_final.columns.duplicated()]

# Layout output in a container
with st.container():
    st.markdown("### Map of Cities")
    m = folium.Map(location=home_coords, zoom_start=8)
    for _, row in df_final.iterrows():
        net_pay_val = row['Net Pay']
        try:
            net_pay_float = float(net_pay_val)
        except Exception:
            net_pay_float = 0.0
        popup = f"{row['City']}<br>Net Pay: ${net_pay_float:,.2f}"
        folium.Marker(
            [row["Latitude"], row["Longitude"]],
            popup=popup,
            icon=folium.Icon(color="blue" if row["City"] != "Remote" else "green")
        ).add_to(m)
    st_folium(m, width=1200, height=600)

    st.markdown("### Take-Home Pay Comparison Table")
    st.dataframe(df_final[[
        "City", "Distance", "Commute Miles", "Gas Cost",
        "Federal Tax", "State Tax", "FICA",
        "Car Payment", "Car Insurance", "Healthcare", "Net Pay"
    ]], use_container_width=True)