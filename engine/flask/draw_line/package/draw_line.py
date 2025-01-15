import os 
import cv2
import json
from package.geojson_utils import save_geojson, geojson_data
from package.connections import Connections
import uuid 
import pytz
from datetime import datetime

conn = Connections(postgres_database=os.getenv('POSTGRES_DB_NAME'),
                    postgres_host=os.getenv('POSTGRES_DB_HOST'),
                    postgres_password=os.getenv('POSTGRES_DB_PASSWORD'),
                    postgres_username=os.getenv('POSTGRES_DB_USERNAME'),
                    postgres_port=os.getenv('POSTGRES_DB_PORT'))

drawing = False
lines = []
lines_id = 0
ix, iy = -1, -1

lines_geojson = {
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

def capture_image_for_drawing(video_source):
    img_w, img_h = 1280, 720
    cap = cv2.VideoCapture(video_source)
    success, img = cap.read()
    img = cv2.resize(img, (img_w, img_h))
    cap.release()

    if success:
        return img
    else:
        raise Exception("Failed to capture image from video.")

def save_lines_to_db():
    global lines, lines_geojson
    if lines:
        stream_id = str(uuid.uuid4())
        wib_timezone = pytz.timezone('Asia/Jakarta')
        now_wib = datetime.now().astimezone(wib_timezone)
        created_at = now_wib.strftime("%Y-%m-%d %H:%M:%S%z")

        pg_conn = conn.postgres_connection()
        pg_curr = pg_conn.cursor()

        sql_query = """
            INSERT INTO video_logs_2 (created_at, stream_id, pixel_coordinates, status)
            VALUES (%s, %s, %s, 'A')
        """
        record_to_insert = (created_at, stream_id, json.dumps(lines_geojson))

        pg_curr.execute(sql_query, record_to_insert)
        pg_conn.commit()
        pg_conn.close()

        print("Lines inserted into the database in GeoJSON format.")
        save_geojson('./json/border/line.json')

    else:
        print("No lines to save.")

def draw_line(event, x, y, flags, param):
    global ix, iy, drawing, lines, lines_id

    if event == cv2.EVENT_LBUTTONDOWN:
        drawing = True
        ix, iy = x, y

    elif event == cv2.EVENT_MOUSEMOVE:
        if drawing:
            img_copy = param.copy()
            cv2.line(img_copy, (ix, iy), (x, y), (0, 255, 0), 2)
            cv2.imshow("Draw Line", img_copy)

    elif event == cv2.EVENT_LBUTTONUP:
        drawing = False
        cv2.line(param, (ix, iy), (x, y), (0, 255, 0), 2)
        cv2.imshow("Draw Line", param)

        # Determine line direction (IN or OUT)
        label = "IN" if ix < x else "OUT"

        lines_id += 1
        lines.append((f"{label}-line-{lines_id}", (ix, iy), (x, y)))

        print(f"Koordinat garis: (({ix}, {iy}), ({x}, {y})) Label: {label}")
        lines_geojson["geometry"]["coordinates"][label].append([ix, iy, x, y])

        # save_geojson('./json/border/line.json')
        if not drawing:
            save_lines_to_db(lines)
