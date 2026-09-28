import datetime

from camera_stream import CameraError, LatestFrameCamera
from geometry import GeometryError, image_point_to_servo_angle
from modal_client import ModalVLMError, classify_frame
from pico_link import PicoLink, PicoLinkError
from run_logger import RunLogger
from vision import VisionError, detect_layout, layouts_consistent


def stop_for_fault(pico, logger, reason, **fields):
    print("STOP:", reason)
    logger.write("system_stop", reason=reason, **fields)

    try:
        ack = pico.stop_pwm()
        print("Pico:", ack)
        logger.write("pwm_stop_ack", ack=ack)
    except PicoLinkError as exc:
        print("STOP WARNING: could not disable PWM:", exc)
        logger.write(
            "pwm_stop_failed",
            error=str(exc),
        )


def main():
    logger = RunLogger()
    print("LOG:", logger.path)

    with LatestFrameCamera() as camera, PicoLink() as pico:
        print("READY")
        ping = pico.ping()
        print("Pico:", ping)
        logger.write("startup", pico_ping=ping)

        while True:
            instruction = input("\n指示（qで終了）: ").strip()

            if instruction.lower() == "q":
                logger.write("user_exit")
                break

            if not instruction:
                print("STOP: empty instruction")
                logger.write("semantic_stop", reason="empty_instruction")
                continue

            try:
                before = camera.snapshot()
                before_layout = detect_layout(before.frame)
            except (CameraError, VisionError) as exc:
                stop_for_fault(
                    pico,
                    logger,
                    f"pre-inference observation invalid: {exc}",
                    instruction=instruction,
                )
                continue

            captured_at = datetime.datetime.fromtimestamp(
                before.captured_wall_time
            ).isoformat(timespec="milliseconds")

            logger.write(
                "observation_frozen",
                instruction=instruction,
                captured_at=captured_at,
                layout={
                    color: {
                        "center": list(det.center),
                        "area": det.area,
                    }
                    for color, det in before_layout.items()
                },
            )

            try:
                vlm_result = classify_frame(
                    before.frame,
                    instruction,
                )
            except ModalVLMError as exc:
                stop_for_fault(
                    pico,
                    logger,
                    f"VLM unavailable: {exc}",
                    instruction=instruction,
                    captured_at=captured_at,
                )
                continue

            target = vlm_result["target"]

            print("Captured:", captured_at)
            print("VLM target:", target)
            print("Modal RTT ms:", vlm_result.get("round_trip_ms"))
            print("Model inference ms:", vlm_result.get("inference_ms"))
            print("Model revision:", vlm_result.get("model_revision"))

            logger.write(
                "vlm_result",
                instruction=instruction,
                captured_at=captured_at,
                request_id=vlm_result.get("request_id"),
                target=target,
                raw_output=vlm_result.get("raw_output"),
                model=vlm_result.get("model"),
                model_revision=vlm_result.get("model_revision"),
                inference_ms=vlm_result.get("inference_ms"),
                round_trip_ms=vlm_result.get("round_trip_ms"),
            )

            if target == "NONE":
                print("NO ACTION: VLM selected NONE")
                logger.write(
                    "semantic_stop",
                    reason="target_none",
                    instruction=instruction,
                )
                continue

            try:
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
                stop_for_fault(
                    pico,
                    logger,
                    str(exc),
                    instruction=instruction,
                    target=target,
                )
                continue

            try:
                ack = pico.send_angle(angle)
            except PicoLinkError as exc:
                stop_for_fault(
                    pico,
                    logger,
                    f"Pico command failed: {exc}",
                    instruction=instruction,
                    target=target,
                    angle=angle,
                )
                continue

            print("Target center:", target_detection.center)
            print("Command angle:", round(angle, 2))
            print("Pico ACK:", ack)

            logger.write(
                "actuation_success",
                instruction=instruction,
                target=target,
                target_center=list(target_detection.center),
                target_area=target_detection.area,
                command_angle=angle,
                pico_ack=ack,
            )


if __name__ == "__main__":
    main()
