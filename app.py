# UNIVERSAL SPATIAL INTERSECTION EQUATION
# Fetches any record where: Distance_To_Source <= (Search_Radius + Influence_Radius)

def fetch_intersecting_layer(table_name, target_lat, target_lon, search_radius_miles):
    # 1. Fetch regional records within extended boundary buffer
    extended_buffer_deg = (search_radius_miles + 100.0) / 69.0
    records = supabase.table(table_name).select("*") \
        .gte("latitude", target_lat - extended_buffer_deg) \
        .lte("latitude", target_lat + extended_buffer_deg) \
        .gte("longitude", target_lon - extended_buffer_deg) \
        .lte("longitude", target_lon + extended_buffer_deg) \
        .execute().data or []
    
    active_features = []
    for r in records:
        source_lat, source_lon = float(r["latitude"]), float(r["longitude"])
        dist_to_target = haversine_miles(target_lat, target_lon, source_lat, source_lon)
        
        # Get feature influence envelope (e.g., 80 mi for Niagara, 40 mi for Watershed/Lore)
        influence_radius = r.get("influence_radius_miles", 40.0)
        
        # INTERSECTION CRITERIA: Wave/Envelope touches the search zone
        if dist_to_target <= (search_radius_miles + influence_radius):
            r["dist_to_target"] = dist_to_target
            r["coverage_percent"] = calculate_overlap_coverage(dist_to_target, search_radius_miles, influence_radius)
            active_features.append(r)
            
    return active_features
