from flask import Flask, request, jsonify, render_template
from supabase import create_client
import math
import requests
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_ANON_KEY")
)

def haversine_miles(lat1, lon1, lat2, lon2):
    R = 3958.8
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat/2)**2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2)
    return R * 2 * math.asin(math.sqrt(a))

def geocode(location):
    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": location, "format": "json", "limit": 1},
            headers={"User-Agent": "SurfFind/1.0"},
            timeout=5,
        )
        results = resp.json()
        if results:
            return float(results[0]["lat"]), float(results[0]["lon"])
    except Exception:
        pass
    return None, None

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/search")
def search():
    location   = request.args.get("location", "").strip()
    radius     = float(request.args.get("radius", 5))
    experience = request.args.get("experience", "").strip()
    wave_type  = request.args.get("wave_type", "").strip()
    direction  = request.args.get("direction", "").strip()
    crowd      = request.args.get("crowd", "").strip()

    if not location:
        return jsonify({"error": "No location provided"}), 400

    lat, lon = geocode(location)
    if lat is None:
        return jsonify({"error": f"Could not find location: {location}"}), 404

    print(f"Geocoded: {lat}, {lon}")

    all_spots = []
    page = 0
    page_size = 1000
    while True:
        response = supabase.table("surf_spots") \
            .select("*") \
            .not_.is_("latitude", "null") \
            .not_.is_("longitude", "null") \
            .range(page * page_size, (page + 1) * page_size - 1) \
            .execute()
        all_spots.extend(response.data)
        if len(response.data) < page_size:
            break
        page += 1

    spots = all_spots

    results = []
    for spot in spots:
        dist = haversine_miles(lat, lon, spot["latitude"], spot["longitude"])
        if dist > radius:
            continue

        if experience and spot.get("experience"):
            if experience.lower() not in spot["experience"].lower():
                continue

        if wave_type and spot.get("wave_type"):
            if wave_type.lower() not in spot["wave_type"].lower():
                continue

        if direction and spot.get("wave_direction"):
            if direction.lower() not in spot["wave_direction"].lower():
                continue

        if crowd and spot.get("weekend_crowd"):
            if crowd.lower() not in spot["weekend_crowd"].lower():
                continue

        results.append({
            "id":                 spot["id"],
            "name":               spot["name"],
            "alternative_name":   spot.get("alternative_name"),
            "zone":               spot.get("zone"),
            "country":            spot.get("country"),
            "latitude":           spot["latitude"],
            "longitude":          spot["longitude"],
            "distance_miles":     round(dist, 1),
            "wave_quality":       spot.get("wave_quality"),
            "experience":         spot.get("experience"),
            "frequency":          spot.get("frequency"),
            "wave_type":          spot.get("wave_type"),
            "wave_direction":     spot.get("wave_direction"),
            "bottom":             spot.get("bottom"),
            "power":              spot.get("power"),
            "normal_length":      spot.get("normal_length"),
            "good_day_length":    spot.get("good_day_length"),
            "good_swell_dir":     spot.get("good_swell_dir"),
            "good_wind_dir":      spot.get("good_wind_dir"),
            "swell_size":         spot.get("swell_size"),
            "best_tide_position": spot.get("best_tide_position"),
            "best_tide_movement": spot.get("best_tide_movement"),
            "week_crowd":         spot.get("week_crowd"),
            "weekend_crowd":      spot.get("weekend_crowd"),
            "dangers":            spot.get("dangers"),
            "access_distance":    spot.get("access_distance"),
            "access_walk":        spot.get("access_walk"),
            "access_description": spot.get("access_description"),
            "description":        spot.get("description"),
            "atmosphere":         spot.get("atmosphere"),
            "url":                spot.get("url"),
        })

    results.sort(key=lambda x: x["distance_miles"])

    return jsonify({
        "center": {"lat": lat, "lon": lon},
        "count": len(results),
        "spots": results,
    })

@app.route("/filters")
def filters():
    all_spots = []
    page = 0
    page_size = 1000
    while True:
        response = supabase.table("surf_spots") \
            .select("experience, wave_type, weekend_crowd") \
            .range(page * page_size, (page + 1) * page_size - 1) \
            .execute()
        all_spots.extend(response.data)
        if len(response.data) < page_size:
            break
        page += 1

    spots = all_spots
    
    experience_vals = sorted(set(s["experience"] for s in spots if s.get("experience")))
    wave_type_vals  = sorted(set(s["wave_type"]  for s in spots if s.get("wave_type")))
    crowd_vals      = sorted(set(s["weekend_crowd"] for s in spots if s.get("weekend_crowd")))

    return jsonify({
        "experience": experience_vals,
        "wave_type":  wave_type_vals,
        "crowd":      crowd_vals,
    })

if __name__ == "__main__":
    app.run(debug=True, port=5000)