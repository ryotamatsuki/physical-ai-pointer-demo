# Machine-specific settings.
# Update these values only after the corresponding experiment establishes them.

CAMERA_INDEX = 0
SERIAL_PORT = "COM5"
SERIAL_BAUD = 115200

# Temporary Gradio share URL printed by the Colab notebook.
# This usually changes whenever the Colab runtime is restarted.
COLAB_GRADIO_URL = "https://REPLACE-ME.gradio.live"
VLM_MODEL_NAME = "Qwen/Qwen3-VL-2B-Instruct"

# Image coordinates of the servo rotation axis.
PIVOT_X = 640
PIVOT_Y = 600

# Servo calibration.
SERVO_CENTER = 90.0
SERVO_MIN = 30.0
SERVO_MAX = 150.0
ANGLE_SIGN = 1.0
ANGLE_SCALE = 1.0
ANGLE_OFFSET = 0.0

# HSV defaults: starting points only. Calibrate in EXP-005.
HSV_RED_1_LOW = (0, 100, 80)
HSV_RED_1_HIGH = (10, 255, 255)
HSV_RED_2_LOW = (170, 100, 80)
HSV_RED_2_HIGH = (179, 255, 255)

HSV_BLUE_LOW = (90, 80, 60)
HSV_BLUE_HIGH = (135, 255, 255)

HSV_GREEN_LOW = (35, 60, 50)
HSV_GREEN_HIGH = (85, 255, 255)

MIN_CONTOUR_AREA = 500
