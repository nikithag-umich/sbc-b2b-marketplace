import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from math import radians, cos, sin, asin, sqrt

# -----------------------------
# Helper: distance calculator
# -----------------------------
def haversine_distance(lat1, lon1, lat2, lon2):
    R = 3958.8  # miles
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlon, dlat = lon2 - lon1, lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * R * asin(sqrt(a))

# -----------------------------
# App layout
# -----------------------------
st.set_page_config(page_title="Local B2B Marketplace", layout="wide")
st.title("🌾 Local B2B Marketplace: Buyers & Producers")
st.markdown("Find **local buyers and producers** based on product and distance.")

# -----------------------------
# Load data
# -----------------------------
buyers = pd.read_csv("sbc_buyers.csv").dropna(subset=["latitude", "longitude"])
producers = pd.read_csv("sbc_producers.csv").dropna(subset=["latitude", "longitude"])

# -----------------------------
# Sidebar filters
# -----------------------------
st.sidebar.header("🔍 Filters")
user_type = st.sidebar.radio("You are a...", ["Buyer", "Producer"])
max_distance = st.sidebar.slider("Maximum distance (miles)", 10, 500, 100)
search_keyword = st.sidebar.text_input("Optional: product keyword (overrides preset)")

# =====================================================
# BUYER MODE
# =====================================================
if user_type == "Buyer":
    buyer_names = buyers["company_name"].dropna().unique().tolist()
    selected_company = st.sidebar.selectbox("Select your business", buyer_names)
    if selected_company:
        selected_buyer = buyers.loc[buyers["company_name"] == selected_company].iloc[0]
        buyer_lat, buyer_lon = selected_buyer["latitude"], selected_buyer["longitude"]

        # Need: keyword override > produce_needed column
        need = (search_keyword if search_keyword else str(selected_buyer.get("produce_needed", ""))).strip().lower()
        st.subheader(f"🌱 Producers matching **{need if need else '—'}** near {selected_buyer['city']}")

        # --- Matching logic ---
        if need and need != "all":
            # Filter producers by product text
            matches = producers[
                producers["type_produced"].astype(str).str.lower().str.contains(need, na=False)
            ].copy()
        else:
            # If need is 'all' or empty: consider all producers
            matches = producers.copy()

        # Compute distance & filter
        matches["distance_miles"] = matches.apply(
            lambda r: haversine_distance(buyer_lat, buyer_lon, r["latitude"], r["longitude"]), axis=1
        )
        matches = matches[matches["distance_miles"] <= max_distance].sort_values("distance_miles")

        if matches.empty:
            st.info("No producers found within the selected range.")
        else:
            # Map
            m = folium.Map(location=[buyer_lat, buyer_lon], zoom_start=8)
            folium.Marker(
                [buyer_lat, buyer_lon],
                popup=f"Buyer: {selected_company}",
                icon=folium.Icon(color="blue", icon="shopping-cart"),
            ).add_to(m)
            for _, r in matches.iterrows():
                folium.Marker(
                    [r["latitude"], r["longitude"]],
                    popup=f"{r['company_name']} ({r['city']})<br>{r['type_produced']}<br>{r['distance_miles']:.1f} mi",
                    icon=folium.Icon(color="green", icon="leaf"),
                ).add_to(m)
            st_folium(m, width=750, height=500)

            # Compact listings
            st.markdown("---")
            for _, r in matches.iterrows():
                st.markdown(
                    f"""
                    <div style="font-size:15px; line-height:1.5; margin-bottom:18px;">
                        <b style="font-size:17px; color:#2e7d32;">🌿 {r['company_name']}</b> — {r['city']}<br>
                        <span style="color:#444;"><b>Produces:</b> {r['type_produced']}</span><br>
                        <span style="color:#666;"><b>Distance:</b> {r['distance_miles']:.1f} miles</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

# =====================================================
# PRODUCER MODE
# =====================================================
else:
    producer_names = producers["company_name"].dropna().unique().tolist()
    selected_company = st.sidebar.selectbox("Select your business", producer_names)
    if selected_company:
        selected_producer = producers.loc[producers["company_name"] == selected_company].iloc[0]
        prod_lat, prod_lon = selected_producer["latitude"], selected_producer["longitude"]

        # Supply: keyword override > type_produced column
        supply = (search_keyword if search_keyword else str(selected_producer.get("type_produced", ""))).strip().lower()
        st.subheader(f"🛒 Buyers needing **{supply if supply else '—'}** near {selected_producer['city']}")

        # --- Matching logic ---
        buyers_copy = buyers.copy()
        # Normalize text columns for safe matching
        buyers_copy["produce_needed"] = buyers_copy["produce_needed"].astype(str).str.lower()

        if supply:
            # Match buyers whose need contains the supply OR who are 'all'
            matches = buyers_copy[
                (buyers_copy["produce_needed"] == "all") |
                (buyers_copy["produce_needed"].str.contains(supply, na=False))
            ].copy()
        else:
            # If no supply text, just include buyers who are 'all'
            matches = buyers_copy[buyers_copy["produce_needed"] == "all"].copy()

        # Compute distance & filter
        matches["distance_miles"] = matches.apply(
            lambda r: haversine_distance(prod_lat, prod_lon, r["latitude"], r["longitude"]), axis=1
        )
        matches = matches[matches["distance_miles"] <= max_distance].sort_values("distance_miles")

        if matches.empty:
            st.info("No buyers found within the selected range.")
        else:
            # Map
            m = folium.Map(location=[prod_lat, prod_lon], zoom_start=8)
            folium.Marker(
                [prod_lat, prod_lon],
                popup=f"Producer: {selected_company}",
                icon=folium.Icon(color="green", icon="leaf"),
            ).add_to(m)
            for _, r in matches.iterrows():
                folium.Marker(
                    [r["latitude"], r["longitude"]],
                    popup=f"{r['company_name']} ({r['city']})<br>{r['produce_needed']}<br>{r['distance_miles']:.1f} mi",
                    icon=folium.Icon(color="blue", icon="shopping-cart"),
                ).add_to(m)
            st_folium(m, width=750, height=500)

            # Compact listings
            st.markdown("---")
            for _, r in matches.iterrows():
                st.markdown(
                    f"""
                    <div style="font-size:15px; line-height:1.5; margin-bottom:18px;">
                        <b style="font-size:17px; color:#1565c0;">🏪 {r['company_name']}</b> — {r['city']}<br>
                        <span style="color:#444;"><b>Needs:</b> {r['produce_needed']}</span><br>
                        <span style="color:#666;"><b>Distance:</b> {r['distance_miles']:.1f} miles</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
