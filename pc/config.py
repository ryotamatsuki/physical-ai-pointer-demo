# Machine-specific settings.
# Replace placeholder values only after the corresponding experiment PASS.

CAMERA_INDEX = 0

# Expected capture geometry. Set these from EXP-004/EXP-006.
CAMERA_WIDTH = None
CAMERA_HEIGHT = None
MAX_FRAME_AGE_SECONDS = 0.75

# Dedicated 3.3V TTL USB-UART adapter COM port.
SERIAL_PORT = "COM5"
SERIAL_BAUD = 115200
SERIAL_ACK_TIMEOUT_SECONDS = 1.5

# Modal endpoint.
MODAL_CLASSIFY_URL = "https://REPLACE-WITH-MODAL-ENDPOINT"

# Public-demo request timeout. Cold-start validation uses a longer value.
MODAL_REQUEST_TIMEOUT_SECONDS = 30
MODAL_COLD_START_TIMEOUT_SECONDS = 120

# Resize by the longest image side before upload.
MAX_VLM_IMAGE_SIDE = 1280
JPEG_QUALITY = 85

# Calibration must be recorded from the actual fixed camera setup.
CALIBRATION_FRAME_WIDTH = None
CALIBRATION_FRAME_HEIGHT = None
PIVOT_X = None
PIVOT_Y = None

# Geometry / mechanical safety.
SERVO_CENTER = 90.0
SERVO_MIN = 30.0
SERVO_MAX = 150.0
ANGLE_SIGN = 1.0
ANGLE_SCALE = 1.0
ANGLE_OFFSET = 0.0
MIN_TARGET_RADIUS_PX = 60.0

# Stage/board ROI as fractions of full image.
# Adjust in EXP-005 so audience/clothes/cables are outside whenever possible.
ROI_LEFT = 0.05
ROI_TOP = 0.05
ROI_RIGHT = 0.95
ROI_BOTTOM = 0.85

# Card-shape validation within the ROI.
MIN_CARD_AREA_FRACTION = 0.002
MAX_CARD_AREA_FRACTION = 0.12
MIN_CARD_ASPECT_RATIO = 0.45
MAX_CARD_ASPECT_RATIO = 2.2
MIN_CARD_EXTENT = 0.55

# Scene freshness: if any card moves more than this fraction of image diagonal
# while Modal is reasoning, do not actuate. Require a new instruction.
MAX_LAYOUT_SHIFT_FRACTION = 0.015
MAX_CARD_AREA_CHANGE_FRACTION = 0.30

# HSV starting points only. Calibrate in EXP-005.
HSV_RED_1_LOW = (0, 100, 80)
HSV_RED_1_HIGH = (10, 255, 255)
HSV_RED_2_LOW = (170, 100, 80)
HSV_RED_2_HIGH = (179, 255, 255)

HSV_BLUE_LOW = (90, 80, 60)
HSV_BLUE_HIGH = (135, 255, 255)

HSV_GREEN_LOW = (35, 60, 50)
HSV_GREEN_HIGH = (85, 255, 255)

# Morphology kernel. Keep small to avoid joining separate objects.
MORPH_KERNEL_SIZE = 3
