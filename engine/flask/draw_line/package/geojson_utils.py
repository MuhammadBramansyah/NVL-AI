import json
from package.postgres import Postgres

geojson_data = {
    "type": "Feature",
    "geometry": {
        "type": "LineString",
        "coordinates": {
            "IN": [],
            "OUT": []
        }
    },
    "properties": {
        "name": "Dinagat Islands"
    }
}

ploygon_geojson = {
    "type":"Feature",
    "geometry": {
        "type": "Polygon",
        "coordinates": {
            "AREA":[]
        }
    },
    "properties": {
        "type":"VC"
    }
}

def save_geojson(geojson_file):
    with open(geojson_file, 'w') as f:
        json.dump(geojson_data, f, indent=4)


def save_polygon(geojson_file, polygon_data):
    with open(geojson_file, 'w') as f:
        json.dump(polygon_data, f, indent=4)

# def load_lines_from_geojson(geojson_file="/Users/mac/Documents/computer_vision/video_engines/json/border/line.json"):
#     with open(geojson_file, 'r') as f:
#         data = json.load(f)
    
#     lines = []
#     coordinates = data["geometry"]["coordinates"]
#     for label in ["IN", "OUT"]:
#         for idx, coord in enumerate(coordinates.get(label, []), start=1):
#             line_name = f"{label}-line-{idx}"
#             start_point = (coord[0], coord[1])
#             end_point = (coord[2], coord[3])
#             lines.append((line_name, start_point, end_point))
#     print('ini lines = ', lines)
#     return lines

def load_lines_from_geojson(geojson_data):
    data = geojson_data
    lines = []
    coordinates = data["geometry"]["coordinates"]
    for label in ["IN", "OUT"]:
        for idx, coord in enumerate(coordinates.get(label, []), start=1):
            line_name = f"{label}-line-{idx}"
            start_point = (coord[0], coord[1])
            end_point = (coord[2], coord[3])
            lines.append((line_name, start_point, end_point))
    print('ini lines = ', lines)
    return lines
