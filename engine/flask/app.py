import asyncio
import socket
import uuid
import cv2

from flask import Flask, render_template, Response,url_for, jsonify
import logging
from concurrent.futures import ThreadPoolExecutor
from package.postgres import Postgres
from detection.process_ai import process_video_stream
from query.postgres_query import get_data

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
tasks = []
initial_coordinates = None

## DEBUG
frame_count = 0

def get_analytics_type(geojson_data):
    data = geojson_data
    return data["properties"]["type"]

@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response

def get_detection_coordinates():
    pg = Postgres()
    return pg.get_data_executor(query=get_data()) 

def update_logs_status(record_id):
    pg = Postgres()
    query = f"""
        update video_logs
        set status = 'U'
        where id = {record_id}
    """
    pg.update_logs(query)
    logging.info(f'Table Has Been Updated for record_id {record_id}')

def generate_frames(video_source, geojson_file, stream_id, location, longitude, latitude, analytics_type):
    frame_iterator = process_video_stream(video_source, geojson_file, stream_id, location, longitude, latitude, analytics_type)
    global frame_count
    for frame in frame_iterator:
        frame_count += 1
        logging.info(f"Frame ke-{frame_count} dikirim.")
        if frame is not None:
            yield frame
        else:
            logging.warning(f"Frame ke-{frame_count} kosong!")
        # await asyncio.sleep(0.033)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed/<string:stream_id>')
def video_feed(stream_id):
    global initial_coordinates
    record_id, db_stream_id, gjson_coordinates, longitude, latitude, location, url_stream = initial_coordinates[0]
    
    if stream_id != db_stream_id:
        return jsonify({"error": "Stream ID tidak valid"}), 400

    update_logs_status(record_id)
    
    try:
        return Response(generate_frames(
            video_source=url_stream,
            geojson_file=gjson_coordinates,
            stream_id=stream_id,
            location=location,
            longitude=longitude,
            latitude=latitude,
            analytics_type=get_analytics_type(gjson_coordinates)
        ), mimetype='multipart/x-mixed-replace; boundary=frame')
    except Exception as e:
        logging.error(f"Error in video feed generation: {e}")
        return jsonify({"error": "Unable to process video feed"}), 500

@app.route('/api/get-video-feed-url', methods=['GET'])
def get_video_feed_url():
    global initial_coordinates  
    record_id, stream_id, _, longitude, latitude, location, url_stream = initial_coordinates[0]
    
    video_feed_url = url_for('video_feed', stream_id=stream_id, _external=True)
    return jsonify({"video_feed_url": video_feed_url})

def poll_for_new_coordinates():
    global initial_coordinates  
    try:
        geojson_data = get_detection_coordinates()
        if geojson_data:
            initial_coordinates = geojson_data  
            logging.info("Initial coordinates fetched successfully.")
        else:
            logging.warning("No coordinates found at startup.")
    except Exception as e:
        logging.error(f"Error polling coordinates: {e}")

def find_available_port(start_port=8501, end_port=8600):
    for port in range(start_port, end_port + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('localhost', port)) != 0: 
                return port
    raise RuntimeError("No available ports found in the specified range.")

if __name__ == '__main__':
    app.config['KEEP_ALIVE_TIMEOUT'] = 120

    try:
        poll_for_new_coordinates()
        port = find_available_port()
        logging.info(f"Running app on available port: {port}")
        app.run(debug=True, port=port)
    except RuntimeError as e:
        logging.error(str(e))