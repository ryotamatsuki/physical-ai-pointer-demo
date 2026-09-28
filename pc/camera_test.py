import cv2

MAX_INDEX = 9

for index in range(MAX_INDEX + 1):
    print(f"Testing camera index {index}...")
    cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)

    if not cap.isOpened():
        print("  cannot open")
        cap.release()
        continue

    ok, frame = cap.read()
    if ok:
        print(f"  SUCCESS shape={frame.shape}")
        cv2.imshow(f"Camera {index} - press any key", frame)
        cv2.waitKey(1500)
        cv2.destroyAllWindows()
    else:
        print("  opened but frame read failed")

    cap.release()
