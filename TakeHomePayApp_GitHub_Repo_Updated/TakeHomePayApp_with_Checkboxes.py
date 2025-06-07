
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
from geopy.geocoders import Nominatim
from geopy.distance import geodesic

# App Title
st.title("Take Home Pay App")

# About Button
with st.sidebar.expander("About"):
    st.markdown("**Take Home Pay App**  
June, 2025  
By Micah Forstein")

# Sidebar inputs
salary = st.sidebar.slider("Annual Salary ($)", 1, 500000, 85000, step=500)
gas_price = st.sidebar.slider("Gas Price per Gallon ($)", 1.0, 30.0, 3.75, step=0.25)
car_payment = st.sidebar.number_input("Monthly Car Payment ($)", 0, 2000, 300)
car_insurance = st.sidebar.number_input("Monthly Car Insurance ($)", 0, 1000, 100)
healthcare = st.sidebar.number_input("Monthly Healthcare Cost ($)", 0, 2000, 500)
federal_tax = st.sidebar.slider("Federal Tax Rate (%)", 0, 50, 20)
state_tax = st.sidebar.slider("State Tax Rate (%)", 0, 15, 5)
max_distance = st.sidebar.slider("Maximum Distance from Home (miles)", 3, 300, 150, step=5)

# Weekly commute days checkboxes
st.sidebar.markdown("**Weekly Commute Days**")
commute_days = {
    "Monday": st.sidebar.checkbox("Monday", value=True),
    "Tuesday": st.sidebar.checkbox("Tuesday", value=True),
    "Wednesday": st.sidebar.checkbox("Wednesday", value=True),
    "Thursday": st.sidebar.checkbox("Thursday", value=True),
    "Friday": st.sidebar.checkbox("Friday", value=True)
}
selected_days = sum(commute_days.values())

# Load data
df = pd.read_csv("us_cities_cleaned_reduced_formatted.csv")

# Home location (e.g., Washington, DC)
home_coords = (38.8977, -77.0365)

# Calculate distances
def get_distance(city_coords):
    return round(geodesic(home_coords, city_coords).miles, 2)

df["Distance"] = df.apply(lambda row: get_distance((row["Latitude"], row["Longitude"])), axis=1)

# Filter cities
df_filtered = df[df["Distance"] <= max_distance].copy()

# Financial calculations
mpg = 25
weeks_per_year = 48
days_per_week = 5
annual_multiplier = 2 * weeks_per_year * (selected_days / days_per_week)

def calculate_financials(row):
    is_remote = row["City"] == "Remote"
    commute_miles = 0 if is_remote else row["Distance"] * annual_multiplier
    gas_cost = 0 if is_remote else (commute_miles / mpg) * gas_price
    car = 0 if is_remote else car_payment
    insurance = 0 if is_remote else car_insurance
    fica = 0.062 * salary + 0.0145 * salary
    total_deductions = (salary * (federal_tax + state_tax) / 100) + fica + gas_cost + car + insurance + healthcare
    net_pay = salary - total_deductions

    return pd.Series({
        "Commute Miles": round(commute_miles),
        "Gas Cost": round(gas_cost, 2),
        "Federal Tax": round(salary * federal_tax / 100, 2),
        "State Tax": round(salary * state_tax / 100, 2),
        "FICA": round(fica, 2),
        "Car Payment": car,
        "Car Insurance": insurance,
        "Healthcare": healthcare,
        "Net Pay": round(net_pay, 2)
    })

df_financials = df_filtered.apply(calculate_financials, axis=1)
df_final = pd.concat([df_filtered.reset_index(drop=True), df_financials], axis=1)

# Display chart
st.subheader("Top Cities by Net Pay")
st.dataframe(df_final[["City", "Distance", "Net Pay", "Commute Miles", "Gas Cost"]].sort_values("Net Pay", ascending=False).reset_index(drop=True))

# Map
st.subheader("City Locations Map")
m = folium.Map(location=home_coords, zoom_start=6)
for _, row in df_final.iterrows():
    folium.Marker(
        location=[row["Latitude"], row["Longitude"]],
        popup=f"{row['City']}: ${row['Net Pay']}",
        icon=folium.Icon(color="green" if row["Net Pay"] > 60000 else "red")
    ).add_to(m)
folium_static(m)
