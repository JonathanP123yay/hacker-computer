import math

import cv2
import numpy as np


WINDOW_NAME = "3D Eye Model"


def _project(point, width, height):
    x, y, z = point
    camera_distance = 4.0
    scale = 260.0
    perspective = scale / max(0.5, z + camera_distance)
    center_x = width * 0.5
    center_y = height * 0.56
    return (
        int(center_x + x * perspective),
        int(center_y - y * perspective)
    )


def _line(canvas, first, second, color, thickness=2):
    cv2.line(canvas, first, second, color, thickness, cv2.LINE_AA)


def draw_eye_monitor_model(gaze_x, gaze_y, average_eye_position):
    width, height = 720, 520
    canvas = np.full((height, width, 3), (24, 27, 32), dtype=np.uint8)

    eye_origin = (0.0, 0.0, 0.0)
    monitor_z = 2.0
    monitor_half_width = 1.35
    monitor_half_height = 0.82

    direction_x = (gaze_x - 0.5) * 2.0
    direction_y = -(gaze_y - 0.5) * 2.0
    direction_z = 1.0
    ray_scale = monitor_z / direction_z
    hit_x = direction_x * ray_scale
    hit_y = direction_y * ray_scale
    monitor_hit = (hit_x, hit_y, monitor_z)

    monitor_corners = [
        (-monitor_half_width, monitor_half_height, monitor_z),
        (monitor_half_width, monitor_half_height, monitor_z),
        (monitor_half_width, -monitor_half_height, monitor_z),
        (-monitor_half_width, -monitor_half_height, monitor_z),
    ]
    projected_monitor = [
        _project(corner, width, height) for corner in monitor_corners
    ]

    for index in range(4):
        _line(
            canvas,
            projected_monitor[index],
            projected_monitor[(index + 1) % 4],
            (115, 145, 170),
            3
        )

    monitor_center = _project((0.0, 0.0, monitor_z), width, height)
    stand_top = _project((0.0, -monitor_half_height, monitor_z), width, height)
    stand_bottom = _project((0.0, -1.15, monitor_z + 0.1), width, height)
    _line(canvas, stand_top, stand_bottom, (115, 145, 170), 3)
    _line(
        canvas,
        (stand_bottom[0] - 55, stand_bottom[1]),
        (stand_bottom[0] + 55, stand_bottom[1]),
        (115, 145, 170),
        3
    )

    left_eye = (-0.22, 0.0, 0.0)
    right_eye = (0.22, 0.0, 0.0)
    for eye in (left_eye, right_eye):
        center = _project(eye, width, height)
        cv2.circle(canvas, center, 22, (70, 190, 235), 2, cv2.LINE_AA)
        cv2.circle(canvas, center, 7, (70, 220, 255), -1, cv2.LINE_AA)

    origin = _project(eye_origin, width, height)
    hit = _project(monitor_hit, width, height)
    _line(canvas, origin, hit, (75, 230, 110), 4)
    cv2.circle(canvas, hit, 11, (0, 220, 255), -1, cv2.LINE_AA)
    cv2.circle(canvas, hit, 18, (0, 220, 255), 2, cv2.LINE_AA)

    cv2.putText(
        canvas,
        "3D EYE -> MONITOR RAY",
        (22, 32),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.72,
        (235, 240, 245),
        2,
        cv2.LINE_AA
    )
    cv2.putText(
        canvas,
        f"Average eye: ({average_eye_position[0]}, {average_eye_position[1]})",
        (22, height - 52),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (190, 205, 215),
        1,
        cv2.LINE_AA
    )
    cv2.putText(
        canvas,
        f"Gaze: X={gaze_x:.2f} Y={gaze_y:.2f}",
        (22, height - 24),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (190, 205, 215),
        1,
        cv2.LINE_AA
    )

    cv2.imshow(WINDOW_NAME, canvas)
