import numpy as np

CITIES = [
    ("Lahore", "Pakistan", 31.55, 74.34),
    ("Faisalabad", "Pakistan", 31.42, 73.08),
    ("Rawalpindi", "Pakistan", 33.60, 73.05),
    ("Islamabad", "Pakistan", 33.69, 73.05),
    ("Multan", "Pakistan", 30.20, 71.47),
    ("Gujranwala", "Pakistan", 32.16, 74.19),
    ("Sialkot", "Pakistan", 32.49, 74.53),
    ("Sargodha", "Pakistan", 32.08, 72.67),
    ("Bahawalpur", "Pakistan", 29.40, 71.68),
    ("Sahiwal", "Pakistan", 30.66, 73.11),
    ("Sheikhupura", "Pakistan", 31.71, 73.99),
    ("Jhelum", "Pakistan", 32.93, 73.73),
    ("Gujrat", "Pakistan", 32.57, 74.08),
    ("Okara", "Pakistan", 30.81, 73.45),
    ("Kasur", "Pakistan", 31.12, 74.45),
    ("Rahim Yar Khan", "Pakistan", 28.42, 70.30),
    ("Dera Ghazi Khan", "Pakistan", 30.05, 70.63),
    ("Jhang", "Pakistan", 31.27, 72.32),
    ("Mianwali", "Pakistan", 32.58, 71.54),
    ("Bahawalnagar", "Pakistan", 29.99, 73.25),
    ("Vehari", "Pakistan", 30.04, 72.35),
    ("Hafizabad", "Pakistan", 32.07, 73.69),
    ("Narowal", "Pakistan", 32.10, 74.87),
    ("Pakpattan", "Pakistan", 30.34, 73.39),
    ("Khanewal", "Pakistan", 30.30, 71.93),
    ("Karachi", "Pakistan", 24.86, 67.01),
    ("Hyderabad", "Pakistan", 25.39, 68.37),
    ("Sukkur", "Pakistan", 27.71, 68.86),
    ("Larkana", "Pakistan", 27.56, 68.21),
    ("Nawabshah", "Pakistan", 26.24, 68.41),
    ("Peshawar", "Pakistan", 34.01, 71.58),
    ("Mardan", "Pakistan", 34.20, 72.05),
    ("Quetta", "Pakistan", 30.18, 66.98),
    ("Amritsar", "India", 31.63, 74.87),
    ("Ludhiana", "India", 30.90, 75.85),
    ("Jalandhar", "India", 31.33, 75.58),
    ("Patiala", "India", 30.34, 76.39),
    ("Bathinda", "India", 30.21, 74.95),
    ("Sangrur", "India", 30.25, 75.84),
    ("Firozpur", "India", 30.93, 74.61),
    ("Moga", "India", 30.82, 75.17),
    ("Barnala", "India", 30.38, 75.55),
    ("Mansa", "India", 29.99, 75.40),
    ("Muktsar", "India", 30.47, 74.52),
    ("Fazilka", "India", 30.40, 74.03),
    ("Gurdaspur", "India", 32.04, 75.40),
    ("Hoshiarpur", "India", 31.53, 75.91),
    ("Chandigarh", "India", 30.73, 76.78),
    ("Ambala", "India", 30.38, 76.78),
    ("Karnal", "India", 29.69, 76.99),
    ("Kurukshetra", "India", 29.97, 76.88),
    ("Kaithal", "India", 29.80, 76.40),
    ("Sirsa", "India", 29.53, 75.03),
    ("Hisar", "India", 29.15, 75.72),
    ("Jind", "India", 29.32, 76.31),
    ("Fatehabad", "India", 29.52, 75.45),
    ("Panipat", "India", 29.39, 76.97),
    ("Delhi", "India", 28.61, 77.21),
    ("Meerut", "India", 28.98, 77.71),
    ("Dehradun", "India", 30.32, 78.03),
    ("Srinagar", "India", 34.08, 74.80),
    ("Sri Ganganagar", "India", 29.90, 73.88),
    ("Bikaner", "India", 28.02, 73.31),
    ("Jodhpur", "India", 26.24, 73.02),
    ("Jaipur", "India", 26.91, 75.79),
    ("Udaipur", "India", 24.58, 73.71),
    ("Agra", "India", 27.18, 78.01),
    ("Gwalior", "India", 26.22, 78.18),
    ("Kanpur", "India", 26.45, 80.33),
    ("Lucknow", "India", 26.85, 80.95),
    ("Varanasi", "India", 25.32, 82.99),
    ("Patna", "India", 25.59, 85.14),
    ("Ranchi", "India", 23.34, 85.31),
    ("Kolkata", "India", 22.57, 88.36),
    ("Guwahati", "India", 26.14, 91.74),
    ("Shillong", "India", 25.58, 91.89),
    ("Kohima", "India", 25.67, 94.11),
    ("Imphal", "India", 24.82, 93.94),
    ("Aizawl", "India", 23.73, 92.72),
    ("Agartala", "India", 23.83, 91.29),
    ("Bhubaneswar", "India", 20.30, 85.82),
    ("Raipur", "India", 21.25, 81.63),
    ("Nagpur", "India", 21.15, 79.09),
    ("Jabalpur", "India", 23.18, 79.99),
    ("Bhopal", "India", 23.26, 77.41),
    ("Indore", "India", 22.72, 75.86),
    ("Ahmedabad", "India", 23.02, 72.57),
    ("Surat", "India", 21.17, 72.83),
    ("Mumbai", "India", 19.08, 72.88),
    ("Pune", "India", 18.52, 73.86),
    ("Hyderabad (IN)", "India", 17.39, 78.49),
    ("Visakhapatnam", "India", 17.69, 83.22),
    ("Vijayawada", "India", 16.51, 80.65),
    ("Bengaluru", "India", 12.97, 77.59),
    ("Chennai", "India", 13.08, 80.27),
    ("Coimbatore", "India", 11.02, 76.96),
    ("Madurai", "India", 9.93, 78.12),
    ("Kochi", "India", 9.93, 76.27),
    ("Thiruvananthapuram", "India", 8.52, 76.94),
    ("Port Blair", "India", 11.62, 92.73),
]

SMOG_CITIES = ["Lahore", "Delhi", "Amritsar", "Ludhiana", "Faisalabad", "Islamabad", "Multan", "Chandigarh"]

REGIONS = {
    "punjab_region": {"label": "Punjab region (both sides)", "bbox": [28.0, 34.0, 69.5, 77.5]},
    "pakistan_punjab": {"label": "Punjab, Pakistan (approx.)", "bbox": [27.7, 34.1, 69.3, 75.4], "country": "Pakistan"},
    "indian_punjab": {"label": "Punjab, India (approx.)", "bbox": [29.5, 32.6, 73.8, 77.0], "country": "India"},
    "haryana": {"label": "Haryana, India (approx.)", "bbox": [27.6, 31.0, 74.4, 77.6], "country": "India"},
    "pakistan": {"label": "Pakistan", "country": "Pakistan"},
    "india": {"label": "India", "country": "India"},
    "all": {"label": "Pakistan + India"},
}

_C_LAT = np.radians(np.array([c[2] for c in CITIES]))
_C_LON = np.radians(np.array([c[3] for c in CITIES]))


def haversine_km(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 6371.0 * 2 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def bearing_deg(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    y = np.sin(lon2 - lon1) * np.cos(lat2)
    x = np.cos(lat1) * np.sin(lat2) - np.sin(lat1) * np.cos(lat2) * np.cos(lon2 - lon1)
    return (np.degrees(np.arctan2(y, x)) + 360) % 360


def nearest_cities(lats, lons):
    la = np.radians(np.asarray(lats, dtype="float64"))[:, None]
    lo = np.radians(np.asarray(lons, dtype="float64"))[:, None]
    a = np.sin((_C_LAT - la) / 2) ** 2 + np.cos(la) * np.cos(_C_LAT) * np.sin((_C_LON - lo) / 2) ** 2
    d = 6371.0 * 2 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))
    idx = d.argmin(axis=1)
    names = [CITIES[i][0] for i in idx]
    return names, d[np.arange(len(idx)), idx]


def find_city(name):
    for c in CITIES:
        if c[0].lower() == name.lower():
            return {"name": c[0], "country": c[1], "lat": c[2], "lon": c[3]}
    return None
