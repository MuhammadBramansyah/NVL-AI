import asyncio
import uuid
import cv2
import os 
from pyhocon import ConfigFactory

from package.draw_line import capture_image_for_drawing, draw_line, save_lines_to_db, draw_polyline
from detection.process_ai import process_ai
from query.postgres_query import get_data
from package.postgres import Postgres
# from config.config import url_stream, output_messages_json, location

# CURRENT_FOLDER = os.path.dirname(os.path.abspath(__file__))
# os.chdir(os.path.join(CURRENT_FOLDER, "."))
current_dir = os.getcwd()

readfile = f"{current_dir}/config/config.conf"
conf = ConfigFactory.parse_file(readfile)

url_stream = conf.get("CONF.STREAM_URL")
def handle_key_press():
    while True:
        key = cv2.waitKey(1) & 0xFF
        if key == 13:  # Enter key
            save_lines_to_db()
            break

def get_detection_coordinates():
    pg = Postgres()
    data = pg.get_data_executor(query=get_data())
    return data 

def generate_lines():
    img_for_draw = capture_image_for_drawing(url_stream)
    cv2.imshow("Draw Line", img_for_draw)
    cv2.setMouseCallback("Draw Line", draw_line, img_for_draw)

    # cv2.waitKey(0)
    handle_key_press()

    cv2.destroyAllWindows()

def generate_rectangle():
    img_for_draw = capture_image_for_drawing(url_stream)
    cv2.imshow("Draw Polyline", img_for_draw)  # Gunakan jendela ini untuk menggambar
    cv2.setMouseCallback("Draw Polyline", draw_polyline, img_for_draw)

    handle_key_press()  # Menunggu penekanan tombol 'Enter' untuk menyimpan
    cv2.destroyAllWindows()


def draw_shapes(mode):
    img_for_draw = capture_image_for_drawing(url_stream)
    # cv2.imshow("Draw Shapes", img_for_draw)
    
    if mode == "line":
        cv2.setMouseCallback("Draw Shapes", draw_line, img_for_draw)
    elif mode == "rectangle":
        cv2.setMouseCallback("Draw Shapes", draw_polyline, img_for_draw)
    
    handle_key_press()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    mode = input("Pilih mode gambar (line/polygon): ")
    if mode == "line":
        generate_lines()
    elif mode == "polygon":
        generate_rectangle()
    else:
        print("Mode tidak dikenal.")