import cv2
import mediapipe as mp
import os
import sys
import ctypes
import time
from contextlib import ExitStack

from calibration import calibrate_monitor_mapping
from cursor_control import CursorController, trigger_mouse_click
from directx9_preview import DirectX9Preview
from eye_3d import draw_eye_monitor_model
from gesture_control import GestureController, draw_hand
from gaze_utils import (
    average_points,
    get_blink_ratio,
    get_gaze,
    landmark_to_pixel,
)
import settings

# =========================
# Settings
# =========================

settings.configure(sys.argv[1:])
CALIBRATION_SAMPLES = []
cursor_controller = CursorController(
    settings.CURSOR_SENSITIVITY,
    settings.CURSOR_SMOOTHING,
    settings.MOUSE_OVERRIDE_SECONDS
)
gesture_controller = GestureController()
directx_preview = None
try:
    directx_preview = DirectX9Preview()
    print("DirectX 9 eye model preview enabled.")
except Exception as error:
    print(f"DirectX 9 preview unavailable: {error}")

# =========================
# MediaPipe setup
# =========================

BaseOptions = mp.tasks.BaseOptions
FaceLandmarker = mp.tasks.vision.FaceLandmarker
FaceLandmarkerOptions = mp.tasks.vision.FaceLandmarkerOptions
HandLandmarker = mp.tasks.vision.HandLandmarker
HandLandmarkerOptions = mp.tasks.vision.HandLandmarkerOptions
VisionRunningMode = mp.tasks.vision.RunningMode

if not os.path.exists(settings.MODEL_PATH):
    print(f"ERROR: Could not find {settings.MODEL_PATH}")
    print("Put face_landmarker.task in the same folder as main.py")
    input("Press Enter to exit...")
    raise SystemExit

options = FaceLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=settings.MODEL_PATH),
    running_mode=VisionRunningMode.IMAGE,
    num_faces=1,
    min_face_detection_confidence=0.5,
    min_face_presence_confidence=0.5,
    min_tracking_confidence=0.5
)

# =========================
# Helper functions
# =========================

def debug_print(message):
    if settings.VERBOSE:
        print(message)


# =========================
# Camera
# =========================

camera = cv2.VideoCapture(settings.CAMERA_INDEX)

if not camera.isOpened():
    print("ERROR: Could not open webcam.")
    input("Press Enter to exit...")
    raise SystemExit

camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

print("Eye tracking started.")
print("Press Q to quit.")
if os.path.exists(settings.HAND_MODEL_PATH):
    print("Gestures enabled: point, two fingers, pinch, fist.")
else:
    print("Gestures disabled: hand_landmarker.task was not found.")
debug_print("Verbose mode enabled.")

# =========================
# Main loop
# =========================

with ExitStack() as resources:
    landmarker = resources.enter_context(
        FaceLandmarker.create_from_options(options)
    )
    hand_landmarker = None
    if os.path.exists(settings.HAND_MODEL_PATH):
        hand_options = HandLandmarkerOptions(
            base_options=BaseOptions(
                model_asset_path=settings.HAND_MODEL_PATH
            ),
            running_mode=VisionRunningMode.IMAGE,
            num_hands=1,
            min_hand_detection_confidence=0.5,
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5
        )
        hand_landmarker = resources.enter_context(
            HandLandmarker.create_from_options(hand_options)
        )

    calibration = calibrate_monitor_mapping(
        camera,
        landmarker,
        settings.VERBOSE
    )
    CALIBRATION_SAMPLES = calibration
    blink_cooldown = 0

    while True:
        success, frame = camera.read()

        if not success:
            print("Could not read webcam frame.")
            break

        # Mirror webcam
        frame = cv2.flip(frame, 1)

        height, width, _ = frame.shape

        # Convert BGR -> RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Create MediaPipe image
        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=rgb_frame
        )

        # Detect face landmarks
        result = landmarker.detect(mp_image)

        gesture = "DISABLED"
        if hand_landmarker is not None:
            hand_result = hand_landmarker.detect(mp_image)
            if hand_result.hand_landmarks:
                hand = hand_result.hand_landmarks[0]
                draw_hand(frame, hand)
                gesture = gesture_controller.update(hand)
            else:
                gesture_controller.reset()

        if result.face_landmarks:
            debug_print("Face detected.")

            landmarks = result.face_landmarks[0]

            # ==================================================
            # LEFT EYE
            # ==================================================

            left_iris_points = []

            for i in range(468, 473):
                point = landmark_to_pixel(
                    landmarks[i],
                    width,
                    height
                )
                left_iris_points.append(point)

            left_iris = average_points(left_iris_points)

            # Eye corners
            left_corner = landmark_to_pixel(
                landmarks[33],
                width,
                height
            )

            right_corner = landmark_to_pixel(
                landmarks[133],
                width,
                height
            )

            left_top = landmark_to_pixel(
                landmarks[159],
                width,
                height
            )

            left_bottom = landmark_to_pixel(
                landmarks[145],
                width,
                height
            )

            left_top2 = landmark_to_pixel(
                landmarks[160],
                width,
                height
            )

            left_bottom2 = landmark_to_pixel(
                landmarks[144],
                width,
                height
            )

            # ==================================================
            # RIGHT EYE
            # ==================================================

            right_iris_points = []

            for i in range(473, 478):
                point = landmark_to_pixel(
                    landmarks[i],
                    width,
                    height
                )
                right_iris_points.append(point)

            right_iris = average_points(right_iris_points)

            right_eye_left = landmark_to_pixel(
                landmarks[362],
                width,
                height
            )

            right_eye_right = landmark_to_pixel(
                landmarks[263],
                width,
                height
            )

            right_top = landmark_to_pixel(
                landmarks[386],
                width,
                height
            )

            right_bottom = landmark_to_pixel(
                landmarks[374],
                width,
                height
            )

            right_top2 = landmark_to_pixel(
                landmarks[387],
                width,
                height
            )

            right_bottom2 = landmark_to_pixel(
                landmarks[373],
                width,
                height
            )

            # ==================================================
            # GAZE
            # ==================================================

            left_gaze_x, left_gaze_y = get_gaze(
                left_iris,
                left_corner,
                right_corner,
                left_top,
                left_bottom
            )

            right_gaze_x, right_gaze_y = get_gaze(
                right_iris,
                right_eye_left,
                right_eye_right,
                right_top,
                right_bottom
            )

            average_eye_position = average_points([left_iris, right_iris])
            model_gaze_x = (left_gaze_x + right_gaze_x) / 2
            model_gaze_y = (left_gaze_y + right_gaze_y) / 2
            draw_eye_monitor_model(
                model_gaze_x,
                model_gaze_y,
                average_eye_position
            )
            if directx_preview is not None:
                directx_preview.update(
                    model_gaze_x,
                    model_gaze_y,
                    average_eye_position
                )

            gaze_x = right_gaze_x
            gaze_y = right_gaze_y

            if not gesture_controller.paused and not cursor_controller.manual_mouse_moved():
                cursor_controller.move_from_gaze(
                    gaze_x,
                    gaze_y,
                    CALIBRATION_SAMPLES
                )

            # ==================================================
            # BLINKING
            # ==================================================

            left_blink = get_blink_ratio(
                left_corner,
                right_corner,
                left_top,
                left_bottom,
                left_top2,
                left_bottom2
            )

            right_blink = get_blink_ratio(
                right_eye_left,
                right_eye_right,
                right_top,
                right_bottom,
                right_top2,
                right_bottom2
            )

            blink_ratio = (left_blink + right_blink) / 2

            if settings.VERBOSE:
                debug_print(f"Gaze: x={gaze_x:.3f} y={gaze_y:.3f} blink={blink_ratio:.3f}")

            # Approximate blink threshold
            blinking = blink_ratio < 0.18

            if blinking and blink_cooldown <= 0:
                trigger_mouse_click()
                blink_cooldown = 18
                debug_print("Blink detected: mouse click")
            elif blink_cooldown > 0:
                blink_cooldown -= 1

            # ==================================================
            # DRAW IRIS
            # ==================================================

            cv2.circle(
                frame,
                left_iris,
                7,
                (0, 255, 0),
                -1
            )

            cv2.circle(
                frame,
                right_iris,
                7,
                (0, 255, 0),
                -1
            )

            # ==================================================
            # DRAW EYE BOXES
            # ==================================================

            cv2.line(
                frame,
                left_corner,
                right_corner,
                (255, 0, 0),
                2
            )

            cv2.line(
                frame,
                left_top,
                left_bottom,
                (255, 0, 0),
                2
            )

            cv2.line(
                frame,
                right_eye_left,
                right_eye_right,
                (255, 0, 0),
                2
            )

            cv2.line(
                frame,
                right_top,
                right_bottom,
                (255, 0, 0),
                2
            )

            # ==================================================
            # FACE CENTER
            # ==================================================

            nose = landmark_to_pixel(
                landmarks[1],
                width,
                height
            )

            cv2.circle(
                frame,
                nose,
                5,
                (0, 0, 255),
                -1
            )

            # ==================================================
            # TEXT
            # ==================================================

            cv2.putText(
                frame,
                f"Left Iris: X={left_iris[0]} Y={left_iris[1]}",
                (20, 35),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (0, 255, 0),
                2
            )

            cv2.putText(
                frame,
                f"Right Iris: X={right_iris[0]} Y={right_iris[1]}",
                (20, 65),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (0, 255, 0),
                2
            )

            cv2.putText(
                frame,
                f"Gaze X: {gaze_x:.2f}",
                (20, 100),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (255, 255, 255),
                2
            )

            cv2.putText(
                frame,
                f"Gaze Y: {gaze_y:.2f}",
                (20, 130),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (255, 255, 255),
                2
            )

            if blinking:
                blink_text = "BLINKING"
            else:
                blink_text = "Eyes Open"

            cv2.putText(
                frame,
                blink_text,
                (20, 165),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.75,
                (0, 255, 255),
                2
            )

            cv2.putText(
                frame,
                f"Face Center: X={nose[0]} Y={nose[1]}",
                (20, 200),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (255, 255, 255),
                2
            )

        else:
            if settings.VERBOSE:
                debug_print("No face detected.")

            cv2.putText(
                frame,
                "No face detected",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 0, 255),
                2
            )

        cv2.putText(
            frame,
            f"Gesture: {gesture}",
            (20, 235),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (0, 255, 255),
            2
        )

        # Show camera
        cv2.imshow("Eye Tracking", frame)
        cv2.imshow("User Preview", frame)

        # Q = quit
        key = cv2.waitKey(1) & 0xFF

        if key == ord("q"):
            break

# =========================
# Cleanup
# =========================

camera.release()
if directx_preview is not None:
    directx_preview.close()
cv2.destroyAllWindows()

print("Eye tracking stopped.")