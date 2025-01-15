import os
import cv2
import torch
import math
import numpy as np
import pytz
import cvzone
import json
from datetime import datetime, timedelta
from ultralytics import YOLO
from utils.sort import Sort
import threading
import asyncio
import websocket

from package.tracker_utils import draw_object_count, is_hitting_line
from package.geojson_utils import load_lines_from_geojson
from websocket.websocket_client import send_to_websocket
from package.connections import Connections

CURRENT_FOLDER = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = f"{CURRENT_FOLDER}/model/yolov8m.pt"
model = YOLO(MODEL_PATH)
tracker = Sort(max_age=20, min_hits=3, iou_threshold=0.3)
WIB_TIMEZONE = pytz.timezone('Asia/Jakarta')

conn = Connections(postgres_database="vidan",
        postgres_host="47.128.219.203",
        # postgres_host = 'localhost',
        postgres_password="nfvisionaire123",
        postgres_username='postgres',
        postgres_port=5432)

class_names = [
    "person", "bicycle", "car", "motorbike", "aeroplane", "bus", "train", "truck", "boat", "traffic light",
    "fire hydrant", "stop sign", "parking meter", "bench", "bird", "cat", "dog", "horse", "sheep", "cow", 
    "elephant", "bear", "zebra", "giraffe", "backpack", "umbrella", "handbag", "tie", "suitcase", "frisbee", 
    "skis", "snowboard", "sports ball", "kite", "baseball bat", "baseball glove", "skateboard", "surfboard", 
    "tennis racket", "bottle", "wine glass", "cup", "fork", "knife", "spoon", "bowl", "banana", "apple", 
    "sandwich", "orange", "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair", "sofa", 
    "pottedplant", "bed", "diningtable", "toilet", "tvmonitor", "laptop", "mouse", "remote", "keyboard", 
    "cell phone", "microwave", "oven", "toaster", "sink", "refrigerator", "book", "clock", "vase", "scissors", 
    "teddy bear", "hair drier", "toothbrush"
]

def send_to_websocket(message):
    async def async_send():
        try:
            uri = "ws://localhost:8765" 
            async with websocket.connect(uri) as websocket:
                await websocket.send(message)
                print("Message sent to WebSocket")
        except Exception as e:
            print(f"Failed to send to WebSocket: {e}")

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError: 
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    loop.run_until_complete(async_send())


def get_data_query():
    return """
        SELECT id, stream_id, pixel_coordinates, latitude, longitude, stream_url 
        FROM video_logs
        WHERE status = 'A'
        ORDER BY id DESC
        LIMIT 1
    """

def fetch_latest_video_data():
    pg_conn = conn.postgres_connection()
    with pg_conn.cursor() as cursor:
        cursor.execute(get_data_query())
        return cursor.fetchall()

def load_polygon_coordinates(geojson_data):
    return geojson_data["geometry"]["coordinates"]["AREA"]

def calculate_duration(enter_times, obj_id):
    enter_time = enter_times.get(obj_id)
    if enter_time:
        return (datetime.now().astimezone(WIB_TIMEZONE) - enter_time).total_seconds()
    return 0

def draw_parallelogram(frame, vertices):
    color = (0, 255, 0)
    thickness = 2
    is_closed = True
    cv2.polylines(frame, [vertices], is_closed, color, thickness)

def draw_parallelogram_with_divider(frame,vertices):
    color = (0, 255, 0)
    divider_color = (255, 0, 0)
    thickness = 2

    isClosed = True
    cv2.polylines(frame, [vertices], isClosed, color, thickness)

    x1, y1 = vertices[0] 
    x2, y2 = vertices[1]  
    x3, y3 = vertices[2]  
    x4, y4 = vertices[3]  

    # global divider_start, divider_end
    global divider_start, divider_end
    divider_start = ((x1 + x4) // 2, (y1 + y4) // 2)
    divider_end = ((x2 + x3) // 2, (y2 + y3) // 2)

    red_box = np.array([vertices[0], divider_start, divider_end, vertices[1]], np.int32)
    yellow_box = np.array([divider_start, vertices[3], vertices[2], divider_end], np.int32)

    cv2.polylines(frame, [red_box], isClosed, (0, 0, 255), thickness)  
    cv2.polylines(frame, [yellow_box], isClosed, (0, 255, 255), thickness)

## Engine Generator
def process_video_stream(video_source, geojson_file, stream_id, location, longitude, latitude, analytics_type):
    img_w, img_h = 1280, 720
    lines = load_lines_from_geojson(geojson_file)
    line_counts = {line_name: 0 for line_name, _, _ in lines}
    cap = cv2.VideoCapture(video_source)

    if not cap.isOpened():
        raise RuntimeError("Error opening video source.")

    prev_objects = {}
    
    if analytics_type == "VC":
        for frame in process_vehicle_counting(cap, img_w, img_h, lines, line_counts, stream_id, location, longitude, latitude):
            yield frame
    elif analytics_type == "TC":
        limits_jajargenjang = np.array(load_polygon_coordinates(geojson_file), np.int32)
        for frame in process_traffic_control(cap, img_w, img_h, limits_jajargenjang, stream_id, location, longitude, latitude):
            yield frame

    cap.release()

## Vehicle Counting
def process_vehicle_counting(cap, img_w, img_h, lines, line_counts, stream_id, location, longitude, latitude):
    prev_objects = {}
    
    while True:
        success, img = cap.read()
        if not success:
            break

        img = cv2.resize(img, (img_w, img_h))
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        results = model(img, stream=True, device=device)

        detections = np.empty((0, 5))
        for r in results:
            boxes = r.boxes
            for box in boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                conf = math.ceil((box.conf[0] * 100)) / 100
                cls = int(box.cls[0])
                current_class = class_names[cls]

                if current_class in ["car", "truck", "motorbike", "bus"] and conf > 0.3:
                    detections = np.vstack((detections, [x1, y1, x2, y2, conf]))
                    # Bounding Box
                    w, h = x2 - x1, y2 - y1
                    cvzone.cornerRect(img, (x1, y1, w, h), l=9, rt=2, colorR=(255, 0, 0))
                    cvzone.putTextRect(
                        img,
                        f"{current_class} {conf}",
                        (max(0, x1), max(35, y1)),
                        scale=1,
                        thickness=2,
                        offset=5,
                        colorR=(255, 255, 255),
                        colorT=(0, 0, 0)
                    )

        results_tracker = tracker.update(detections)
        
        for line_name, start, end in lines:
            color = (0, 255, 0) if "IN" in line_name else (0, 0, 255)
            cv2.line(img, start, end, color, 3)

        for result in results_tracker:
            x1, y1, x2, y2, obj_id = map(int, result)
            w, h = x2 - x1, y2 - y1
            cx, cy = x1 + w // 2, y1 + h // 2
            cv2.circle(img, (cx, cy), 5, (255, 0, 0), cv2.FILLED)

            for line_name, line_start, line_end in lines:
                if is_hitting_line((cx, cy), line_start, line_end):
                    if obj_id not in prev_objects:
                        prev_objects[obj_id] = (cx, cy)
                        line_counts[line_name] += 1
                        direction = "IN" if "IN" in line_name else "OUT"
                        vehicle_counts = {"car": 0, "bus": 0, "motorbike": 0, "truck": 0}
                        vehicle_counts[current_class] = 1
                        
                        now_wib = datetime.now().astimezone(WIB_TIMEZONE)
                        timestamp = now_wib.strftime("%Y-%m-%d %H:%M:%S%z")
                        message = {
                            "timestamp": timestamp,
                            "stream_id": stream_id,
                            "location": location,
                            **vehicle_counts,
                            "longitude": longitude,
                            "latitude": latitude,
                            "direction": direction,
                            "type": "VC"
                        }

                        send_to_websocket(json.dumps(message))
                        # send_websocket_message(json.dumps(message))

                    else:
                        prev_objects[obj_id] = (cx, cy)

        draw_object_count(img, line_counts, img_h)
        ret, jpeg = cv2.imencode('.jpg', img)
        if not ret:
            continue

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')

## Vehicle Congjungtion
def process_traffic_control(cap, img_w, img_h, limits_jajargenjang, stream_id, location, longitude, latitude):
    prev_objects = {}
    total_displacement, total_objects = 0, 0
    prev_timestamp = None
    next_save_time = datetime.now() + timedelta(minutes=1)

    while True:
        now_wib = datetime.now().astimezone(WIB_TIMEZONE)
        success, img = cap.read()
        img = cv2.resize(img, (img_w, img_h))
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        results = model(img, stream=True, device=device)
        detections = np.empty((0, 5))

        for r in results:
            boxes = r.boxes
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0]
                x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                w, h = x2 - x1, y2 - y1

                conf = math.ceil((box.conf[0] * 100)) / 100

                cls = int(box.cls[0])
                current_class = class_names[cls]

                if current_class in ["car", "truck", "motorbike", "bus"] and conf > 0.3:
                    current_arrays = np.array([x1, y1, x2, y2, conf])
                    detections = np.vstack((detections, current_arrays))
                    cvzone.cornerRect(img, (x1, y1, w, h), l=9, rt=2, colorR=(255, 0, 0))
                    cvzone.putTextRect(
                        img,
                        f"{current_class} {conf}",
                        (max(0, x1), max(35, y1)),
                        scale=1,
                        thickness=2,
                        offset=5,
                        colorR=(255, 255, 255),
                        colorT=(0, 0, 0)
                    )

        results_tracker = tracker.update(detections)
        draw_parallelogram_with_divider(img, limits_jajargenjang)

        yellow_box_count, red_box_count = 0, 0
        red_box = np.array([limits_jajargenjang[0], divider_start, divider_end, limits_jajargenjang[1]], np.int32)
        yellow_box = np.array([divider_start, limits_jajargenjang[3], limits_jajargenjang[2], divider_end], np.int32)

        for result in results_tracker:
            x1, y1, x2, y2, id = result
            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
            w, h = x2 - x1, y2 - y1
            cx, cy = x1 + w // 2, y1 + h // 2

            if cv2.pointPolygonTest(yellow_box, (cx, cy), False) >= 0:
                yellow_box_count += 1
            elif cv2.pointPolygonTest(red_box, (cx, cy), False) >= 0:
                red_box_count += 1

            cv2.circle(img, (cx, cy), 5, (255, 0, 0), cv2.FILLED)

        label = ""
        total_count = yellow_box_count + red_box_count
        if yellow_box_count < 0.4 * total_count and red_box_count < 0.4 * total_count: 
            label = "Macet"
        else:
            label = "Normal"
        cvzone.putTextRect(img, f"yellow Count = {yellow_box_count}", (50, 100))
        cvzone.putTextRect(img, f"red Count = {red_box_count}", (50, 150))
        cvzone.putTextRect(img, f"Traffic Label = {label}", (50, 200))
        
        if datetime.now() >= next_save_time:
            message = {
                "timestamp": now_wib.strftime("%Y-%m-%d %H:%M:%S%z"),
                "stream_id": stream_id,
                "location": location,
                "longitude": longitude,
                "latitude": latitude,
                "numbers_of_cars": len(results_tracker),
                "label":label,
                "type": "TC"
            }
            print(message)
            send_to_websocket(json.dumps(message))
            next_save_time = datetime.now() + timedelta(minutes=1)

        ret, jpeg = cv2.imencode('.jpg', img)
        if not ret:
            continue

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
