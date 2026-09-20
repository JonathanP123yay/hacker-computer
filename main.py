import cv2
import os
import sys
import ctypes
from contextlib import ExitStack

# Lightweight imports that are always needed
from calibration import calibrate_monitor_mapping
from consent import request_consent
from cursor_control import CursorController
from directx9_preview import DirectX9Preview
from eye_3d import draw_eye_monitor_model
from gesture_control import GestureController, draw_hand
import settings
import os

# Detect if a controller should be used for cursor control.
use_controller = os.getenv("USE_CONTROLLER", "0") == "1"
if use_controller:
    try:
        import pygame
        pygame.init()
        if pygame.joystick.get_count() > 0:
            controller = pygame.joystick.Joystick(0)
            controller.init()
        else:
            controller = None
    except Exception as e:
        print(f"Controller support unavailable: {e}")
        controller = None
from gaze_utils import average_points, get_gaze, landmark_to_pixel

# Import Mediapipe only if eye tracking is enabled to avoid unnecessary startup cost.
# Import Mediapipe only if eye tracking or hand gestures are enabled.
if settings.EYE_TRACKING_ENABLED or os.path.exists(settings.HAND_MODEL_PATH):
    import mediapipe as mp
    BaseOptions = mp.tasks.BaseOptions
    FaceLandmarker = mp.tasks.vision.FaceLandmarker
    FaceLandmarkerOptions = mp.tasks.vision.FaceLandmarkerOptions
    HandLandmarker = mp.tasks.vision.HandLandmarker
    HandLandmarkerOptions = mp.tasks.vision.HandLandmarkerOptions
    VisionRunningMode = mp.tasks.vision.RunningMode

    # Detect if a CUDA-capable GPU is available for Mediapipe delegation.
    try:
        import cv2.cuda as cuda
        gpu_available = cuda.getCudaEnabledDeviceCount() > 0
    except Exception:
        gpu_available = False

# =========================
# Settings
# =========================

settings.configure(sys.argv[1:])

if not request_consent():
    print("Consent was not provided. Eye tracking stopped.")
    raise SystemExit

if not settings.request_settings():
    print("Settings were not confirmed. Eye tracking stopped.")
    raise SystemExit

CALIBRATION_SAMPLES = []
cursor_controller = CursorController(
    settings.CURSOR_SENSITIVITY,
    settings.CURSOR_SMOOTHING,
    settings.MOUSE_OVERRIDE_SECONDS
)
# Load addons after initializing core components.
import importlib.util

def load_addons():
    addon_dir = os.path.join(os.getcwd(), "addons")
    if not os.path.isdir(addon_dir):
        return
    for filename in os.listdir(addon_dir):
        if filename.endswith(".py") and not filename.startswith("_"):
            path = os.path.join(addon_dir, filename)
            spec = importlib.util.spec_from_file_location(filename[:-3], path)
            mod = importlib.util.module_from_spec(spec)
            try:
                spec.loader.exec_module(mod)
                if hasattr(mod, "register"):
                    mod.register(settings, cursor_controller)
            except Exception as e:
                print(f"Failed to load addon {filename}: {e}")

load_addons()
gesture_controller = GestureController()
directx_preview = None
if settings.EYE_TRACKING_ENABLED:
    try:
        directx_preview = DirectX9Preview()
        print("DirectX 9 eye model preview enabled.")
    except Exception as error:
        print(f"DirectX 9 preview unavailable: {error}")


if settings.EYE_TRACKING_ENABLED and not os.path.exists(settings.MODEL_PATH):
    print(f"ERROR: Could not find {settings.MODEL_PATH}")
    print("Put face_landmarker.task in the same folder as main.py")
    input("Press Enter to exit...")
    raise SystemExit

options = None
if settings.EYE_TRACKING_ENABLED:
    delegate = mp.tasks.BaseOptions.Delegate.GPU if gpu_available else mp.tasks.BaseOptions.Delegate.CPU
    options = FaceLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=settings.MODEL_PATH, delegate=delegate),
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
print(
    "Eye tracking: enabled."
    if settings.EYE_TRACKING_ENABLED
    else "Eye tracking: disabled. Gesture-only mode."
)
if os.path.exists(settings.HAND_MODEL_PATH):
    print("Gestures: thumb-index tap = left click; hold pinch = drag.")
    print("Two fingers = right click; fist = pause eye tracking.")
else:
    print("Gestures disabled: hand_landmarker.task was not found.")
debug_print("Verbose mode enabled.")

# =========================
# Main loop
# =========================

with ExitStack() as resources:
    landmarker = None
    if settings.EYE_TRACKING_ENABLED:
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

    calibration = []
    if settings.EYE_TRACKING_ENABLED:
        calibration = calibrate_monitor_mapping(
            camera,
            landmarker,
            settings.VERBOSE
        )
    CALIBRATION_SAMPLES = calibration

    while True:
        success, frame = camera.read()

        if not success:
            print("Could not read webcam frame.")
            break

        # Mirror webcam
        frame = cv2.flip(frame, 1)

        height, width, _ = frame.shape

        # Handle controller input if enabled.
        if use_controller and controller is not None:
            pygame.event.pump()
            try:
                x = controller.get_axis(0)
                y = controller.get_axis(1)
                norm_x = (x + 1) / 2
                norm_y = (y + 1) / 2
                cursor_controller.move_from_gaze(norm_x, norm_y, CALIBRATION_SAMPLES)
            except Exception as e:
                print(f"Controller input error: {e}")

        # Only perform MediaPipe processing when a detector exists.
        if landmarker is not None or hand_landmarker is not None:
            # Convert BGR -> RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Create MediaPipe image
            mp_image = mp.Image(
                image_format=mp.ImageFormat.SRGB,
                data=rgb_frame
            )

            # Detect face landmarks
            result = None
            if landmarker is not None:
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

            if result is not None and result.face_landmarks:
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

            if settings.VERBOSE:
                debug_print(f"Gaze: x={gaze_x:.3f} y={gaze_y:.3f}")

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

            nose = landmark_to_pixel(landmarks[1],width,height)

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