import numpy as np
import cv2

def is_hitting_line(point, line_start, line_end, threshold=5):
    point = np.array(point)
    line_start = np.array(line_start)
    line_end = np.array(line_end)

    line_vector = line_end - line_start
    point_vector = point - line_start

    line_length = np.linalg.norm(line_vector)
    if line_length == 0:
        return False

    line_unit_vector = line_vector / line_length
    projection_length = np.dot(point_vector, line_unit_vector)
    projection_point = line_start + projection_length * line_unit_vector

    if (
        np.linalg.norm(projection_point - line_start) > line_length
        or np.linalg.norm(projection_point - line_end) > line_length
    ):
        return False

    perpendicular_distance = np.linalg.norm(point - projection_point)
    return perpendicular_distance <= threshold

def draw_object_count(img, line_counts, img_h):
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = img_h / 600
    thickness = 2
    color = (255, 255, 255)
    background_color = (0, 0, 0)

    text_lines = [f"{line_name}: {count}" for line_name, count in line_counts.items()]
    text = "\n".join(text_lines)

    # Calculate the size of the text block
    line_height = int(30 * font_scale)
    block_height = line_height * len(text_lines)
    block_width = max([cv2.getTextSize(line, font, font_scale, thickness)[0][0] for line in text_lines])

    x, y = img.shape[1] - block_width - 15, 50

    # Draw background rectangle
    cv2.rectangle(
        img,
        (x - 5, y - 30),
        (img.shape[1], y + block_height),
        background_color,
        -1,
    )

    for i, line in enumerate(text_lines):
        cv2.putText(
            img,
            line,
            (x, y + i * line_height),
            font,
            font_scale,
            color,
            thickness,
        )
