from flask import Flask, request, jsonify, render_template
import sqlite3
import math
import requests

app = Flask(__name__)
DB_PATH = "surf_spots.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

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
            headers={"User-Agent": "WannaSurf-Finder/1.0"},
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

    conn = get_db()
    spots = conn.execute(
        "SELECT * FROM surf_spots WHERE latitude IS NOT NULL AND longitude IS NOT NULL"
    ).fetchall()
    conn.close()

    results = []
    for spot in spots:
        dist = haversine_miles(lat, lon, spot["latitude"], spot["longitude"])
        if dist > radius:
            continue

        if experience and spot["experience"]:
            if experience.lower() not in spot["experience"].lower():
                continue

        if wave_type and spot["wave_type"]:
            if wave_type.lower() not in spot["wave_type"].lower():
                continue

        if direction and spot["wave_direction"]:
            if direction.lower() not in spot["wave_direction"].lower():
                continue

        if crowd and spot["weekend_crowd"]:
            if crowd.lower() not in spot["weekend_crowd"].lower():
                continue

        results.append({
            "id":                 spot["id"],
            "name":               spot["name"],
            "alternative_name":   spot["alternative_name"],
            "zone":               spot["zone"],
            "country":            spot["country"],
            "latitude":           spot["latitude"],
            "longitude":          spot["longitude"],
            "distance_miles":     round(dist, 1),
            "wave_quality":       spot["wave_quality"],
            "experience":         spot["experience"],
            "frequency":          spot["frequency"],
            "wave_type":          spot["wave_type"],
            "wave_direction":     spot["wave_direction"],
            "bottom":             spot["bottom"],
            "power":              spot["power"],
            "normal_length":      spot["normal_length"],
            "good_day_length":    spot["good_day_length"],
            "good_swell_dir":     spot["good_swell_dir"],
            "good_wind_dir":      spot["good_wind_dir"],
            "swell_size":         spot["swell_size"],
            "best_tide_position": spot["best_tide_position"],
            "best_tide_movement": spot["best_tide_movement"],
            "week_crowd":         spot["week_crowd"],
            "weekend_crowd":      spot["weekend_crowd"],
            "dangers":            spot["dangers"],
            "access_distance":    spot["access_distance"],
            "access_walk":        spot["access_walk"],
            "access_description": spot["access_description"],
            "description":        spot["description"],
            "atmosphere":         spot["atmosphere"],
            "url":                spot["url"],
        })

    results.sort(key=lambda x: x["distance_miles"])

    return jsonify({
        "center": {"lat": lat, "lon": lon},
        "count": len(results),
        "spots": results,
    })

@app.route("/filters")
def filters():
    """Return distinct filter values from the DB for dynamic dropdowns."""
    conn = get_db()
    experience_vals = [r[0] for r in conn.execute(
        "SELECT DISTINCT experience FROM surf_spots WHERE experience IS NOT NULL ORDER BY experience"
    ).fetchall()]
    wave_type_vals = [r[0] for r in conn.execute(
        "SELECT DISTINCT wave_type FROM surf_spots WHERE wave_type IS NOT NULL ORDER BY wave_type"
    ).fetchall()]
    crowd_vals = [r[0] for r in conn.execute(
        "SELECT DISTINCT weekend_crowd FROM surf_spots WHERE weekend_crowd IS NOT NULL ORDER BY weekend_crowd"
    ).fetchall()]
    conn.close()
    return jsonify({
        "experience": experience_vals,
        "wave_type":  wave_type_vals,
        "crowd":      crowd_vals,
    })

if __name__ == "__main__":
    app.run(debug=True, port=5000)
