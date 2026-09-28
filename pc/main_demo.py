import datetime

import config
from camera_stream import CameraError, LatestFrameCamera
from geometry import GeometryError, image_point_to_servo_angle
from modal_client import ModalVLMError, classify_frame
from pico_link import PicoLink, PicoLinkError
from vision import VisionError, detect_layout, layouts_consistent


def stop_for_fault(pico, reason):
    print("STOP:", reason)
    try:
        print("Pico:", pico.stop_pwm())
    except PicoLinkError as exc:
        print("STOP WARNING: could not disable PWM:", exc)


def main():
    with LatestFrameCamera() as camera, PicoLink() as pico:
        print("READY")
        print("Pico:", pico.ping())

        while True:
            instruction = input("\n指示（qで終了）: ").strip()

            if instruction.lower() == "q":
                break

            if not instruction:
                print("STOP: empty instruction")
                continue

            try:
                # Camera is continuously drained in a background thread.
                # Snapshot only after the user has finished entering the command.
                before = camera.snapshot()
                before_layout = detect_layout(before.frame)
            except (CameraError, VisionError) as exc:
                stop_for_fault(pico, f"pre-inference observation invalid: {exc}")
                continue

            captured_at = datetime.datetime.fromtimestamp(
                before.captured_wall_time
            ).isoformat(timespec="milliseconds")

            try:
                vlm_result = classify_frame(
                    before.frame,
                    instruction,
                )
            except ModalVLMError as exc:
                stop_for_fault(pico, f"VLM unavailable: {exc}")
                continue

            target = vlm_result["target"]

            print("Captured:", captured_at)
            print("VLM target:", target)
            print("Modal RTT ms:", vlm_result.get("round_trip_ms"))
            print("Model inference ms:", vlm_result.get("inference_ms"))
            print("Model revision:", vlm_result.get("model_revision"))

            if target == "NONE":
                # NONE is a valid semantic result, not a system fault.
                # Do not issue a new angle and do not silently recenter.
                print("NO ACTION: VLM selected NONE")
                continue

            try:
                # Re-observe immediately before actuation. If the layout moved
                # while Modal was reasoning, the old semantic decision is stale.
                current = camera.snapshot()
                current_layout = detect_layout(current.frame)

                consistent, reason = layouts_consistent(
                    before_layout,
                    current_layout,
                    current.frame.shape,
                )
                if not consistent:
                    raise VisionError(
                        "scene changed during inference: " + reason
                    )

                target_detection = current_layout[target]

                angle = image_point_to_servo_angle(
                    target_detection.center[0],
                    target_detection.center[1],
                    current.frame.shape,
                )

            except (CameraError, VisionError, GeometryError) as exc:
                stop_for_fault(pico, str(exc))
                continue

            try:
                ack = pico.send_angle(angle)
            except PicoLinkError as exc:
                stop_for_fault(pico, f"Pico command failed: {exc}")
                continue

            print("Target center:", target_detection.center)
            print("Command angle:", round(angle, 2))
            print("Pico ACK:", ack)


if __name__ == "__main__":
    main()
