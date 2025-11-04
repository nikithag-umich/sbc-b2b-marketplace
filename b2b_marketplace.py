import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from math import radians, cos, sin, asin, sqrt

# -----------------------------
# Helper function for distance
# -----------------------------
def haversine_distance(lat1, lon1, lat2, lon2):
    R = 3958.8  # miles
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlon, dlat = lon2 - lon1, lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * R * asin(sqrt(a))

# -----------------------------
# Streamlit app setup
# -----------------------------
st.set_page_config(page_title="Local B2B Marketplace", layout="wide")
st.title("🌾 Local B2B Marketplace: Buyers & Producers")
st.markdown("A prototype to connect **regional food producers** with **local buyers** based on product needs and distance.")

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
    selected_company = st.sidebar.selectbox("Select your business", buyer_names, key="buyer_select")
    if selected_company:
        selected_buyer = buyers.loc[buyers["company_name"] == selected_company].iloc[0]
        buyer_lat, buyer_lon = selected_buyer["latitude"], selected_buyer["longitude"]

        # Handle keyword or multi-item produce_needed
        if search_keyword.strip():
            need_list = [search_keyword.strip().lower()]
        else:
            raw_needs = str(selected_buyer["produce_needed"]).strip().lower()
            need_list = [n.strip() for n in raw_needs.split(",") if n.strip()]

        st.subheader(f"🌱 Producers matching **{', '.join(need_list) if need_list else '—'}** near {selected_buyer['city']}")

        # Matching logic
        if "all" in need_list:
            matches = producers.copy()
        else:
            mask = producers["type_produced"].astype(str).str.lower().apply(
                lambda text: any(need in text for need in need_list)
            )
            matches = producers[mask].copy()

        # Compute distance
        matches["distance_miles"] = matches.apply(
            lambda r: haversine_distance(buyer_lat, buyer_lon, r["latitude"], r["longitude"]), axis=1
        )
        matches = matches[matches["distance_miles"] <= max_distance].sort_values("distance_miles")

        # Display
        if matches.empty:
            st.info("No producers found within the selected range.")
        else:
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
                    unsafe_allow_html=True,
                )

# =====================================================
# PRODUCER MODE
# =====================================================
else:
    producer_names = producers["company_name"].dropna().unique().tolist()
    selected_company = st.sidebar.selectbox("Select your business", producer_names, key="producer_select")
    if selected_company:
        selected_producer = producers.loc[producers["company_name"] == selected_company].iloc[0]
        prod_lat, prod_lon = selected_producer["latitude"], selected_producer["longitude"]

        supply_raw = (search_keyword if search_keyword else str(selected_producer.get("type_produced", ""))).strip().lower()
        supply_list = [s.strip() for s in supply_raw.split(",") if s.strip()]
        st.subheader(f"🛒 Buyers needing **{', '.join(supply_list) if supply_list else '—'}** near {selected_producer['city']}")

        buyers_copy = buyers.copy()
        buyers_copy["produce_needed"] = buyers_copy["produce_needed"].astype(str).str.lower()

        # --- FIXED FILTER LOGIC ---
        if not supply_list:
            # If producer has no defined products or no keyword, show only "all" buyers
            mask = buyers_copy["produce_needed"].apply(lambda text: text.strip() == "all")
        else:
            # Match if buyer has "all" or shares any product word with the producer
            mask = buyers_copy["produce_needed"].apply(
                lambda text: text.strip() == "all" or any(supply in text for supply in supply_list)
            )

        matches = buyers_copy[mask].copy()

        # Compute distance
        matches["distance_miles"] = matches.apply(
            lambda r: haversine_distance(prod_lat, prod_lon, r["latitude"], r["longitude"]), axis=1
        )
        matches = matches[matches["distance_miles"] <= max_distance].sort_values("distance_miles")

        # Display
        if matches.empty:
            st.info("No buyers found within the selected range.")
        else:
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
                    unsafe_allow_html=True,
                )
