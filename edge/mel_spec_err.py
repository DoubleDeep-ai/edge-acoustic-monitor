"""Raspberry Pi acoustic monitor and TCP client.

Run with ``--simulate`` to exercise the complete data path without a microphone
or camera. Real mode uses PyAudio for the microphone and OpenCV for the camera.
"""

from __future__ import annotations

import argparse
from collections import deque
from datetime import datetime, timezone
from io import BytesIO
import math
import random
import socket
import time
from typing import Any, Iterator, Optional

import numpy as np
from PIL import Image, ImageDraw

from common.protocol import send_packet


SAMPLE_RATE = 16_000
CHUNK_SAMPLES = SAMPLE_RATE // 10
WINDOW_SAMPLES = 10_240


def read_temperature() -> float:
    """Return a demonstration value; replace this function for a DHT11 sensor."""
    return round(random.uniform(20.0, 25.0), 1)


def synthetic_audio() -> Iterator[np.ndarray]:
    """Yield normal and high-amplitude periods for the hardware-free demo."""
    rng = np.random.default_rng(42)
    while True:
        phase = time.monotonic() % 10
        scale = 8_000 if 6 <= phase < 8 else 900
        yield rng.normal(0, scale, CHUNK_SAMPLES).clip(-32_768, 32_767).astype(np.int16)
        time.sleep(CHUNK_SAMPLES / SAMPLE_RATE)


def microphone_audio() -> Iterator[np.ndarray]:
    from edge.micro_Stream import MicrophoneStream

    with MicrophoneStream(SAMPLE_RATE, CHUNK_SAMPLES) as stream:
        for chunk in stream.generator():
            yield np.frombuffer(chunk, dtype=np.int16)


class AudioDetector:
    def __init__(self, amplitude_threshold: int, exceedance_count: int):
        chunk_count = math.ceil(WINDOW_SAMPLES / CHUNK_SAMPLES)
        self.chunks: deque[np.ndarray] = deque(maxlen=chunk_count)
        self.amplitude_threshold = amplitude_threshold
        self.exceedance_count = exceedance_count

    def update(self, chunk: np.ndarray) -> tuple[bool, int, float]:
        self.chunks.append(chunk)
        window = np.concatenate(tuple(self.chunks))[-WINDOW_SAMPLES:]
        exceedances = int(np.count_nonzero(np.abs(window.astype(np.int32)) > self.amplitude_threshold))
        rms = float(np.sqrt(np.mean(window.astype(np.float64) ** 2)))
        return exceedances >= self.exceedance_count, exceedances, round(rms, 1)


class FrameSource:
    def __init__(self, camera_index: int, simulate: bool):
        self.capture: Optional[Any] = None
        self.cv2: Optional[Any] = None
        if not simulate:
            import cv2

            self.cv2 = cv2
            self.capture = cv2.VideoCapture(camera_index)
            if not self.capture.isOpened():
                raise RuntimeError(f"could not open camera index {camera_index}")

    def read(self, device_id: str, anomaly: bool, temperature: float, rms: float) -> Image.Image:
        if self.capture is not None:
            ok, frame = self.capture.read()
            if not ok or frame is None:
                raise RuntimeError("camera frame could not be read")
            assert self.cv2 is not None
            image = Image.fromarray(self.cv2.cvtColor(frame, self.cv2.COLOR_BGR2RGB))
        else:
            image = Image.new("RGB", (640, 360), (28, 33, 43))

        status = "ANOMALY" if anomaly else "NORMAL"
        color = (230, 70, 70) if anomaly else (65, 190, 90)
        draw = ImageDraw.Draw(image)
        if self.capture is None:
            draw.text((34, 45), "SIMULATED EDGE CAMERA", fill=(235, 235, 235))
        draw.rectangle((24, image.height - 110, image.width - 24, image.height - 20), fill=(18, 18, 18))
        draw.text((42, image.height - 82), f"{device_id}  {status}", fill=color)
        draw.text((42, image.height - 48), f"Temperature {temperature:.1f} C   Audio RMS {rms:.0f}", fill=(230, 230, 230))
        return image

    def close(self) -> None:
        if self.capture is not None:
            self.capture.release()


def encode_jpeg(frame: Image.Image, quality: int) -> bytes:
    output = BytesIO()
    frame.save(output, format="JPEG", quality=quality)
    return output.getvalue()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Edge acoustic monitoring client")
    parser.add_argument("--host", default="127.0.0.1", help="monitoring server address")
    parser.add_argument("--port", type=int, default=8089, help="monitoring server port")
    parser.add_argument("--device-id", default="machine-1", help="device label shown on the dashboard")
    parser.add_argument("--camera", type=int, default=0, help="OpenCV camera index")
    parser.add_argument("--threshold", type=int, default=5_000, help="absolute audio amplitude threshold")
    parser.add_argument("--exceedance-count", type=int, default=1_000, help="samples above threshold required for an alert")
    parser.add_argument("--jpeg-quality", type=int, default=75, choices=range(30, 96), metavar="30-95")
    parser.add_argument("--simulate", action="store_true", help="use generated audio and video")
    return parser.parse_args()


def run(args: argparse.Namespace) -> None:
    detector = AudioDetector(args.threshold, args.exceedance_count)
    frames = FrameSource(args.camera, args.simulate)
    audio = synthetic_audio() if args.simulate else microphone_audio()

    print(f"Connecting {args.device_id} to {args.host}:{args.port}")
    try:
        with socket.create_connection((args.host, args.port), timeout=10) as client:
            client.settimeout(None)
            for chunk in audio:
                anomaly, exceedances, rms = detector.update(chunk)
                temperature = read_temperature()
                frame = frames.read(args.device_id, anomaly, temperature, rms)
                metadata = {
                    "device_id": args.device_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "anomaly": anomaly,
                    "exceedances": exceedances,
                    "audio_rms": rms,
                    "temperature": temperature,
                    "simulated": args.simulate,
                }
                send_packet(client, metadata, encode_jpeg(frame, args.jpeg_quality))
    finally:
        frames.close()


if __name__ == "__main__":
    try:
        run(parse_args())
    except KeyboardInterrupt:
        print("\nEdge client stopped")
    except (ConnectionError, OSError, RuntimeError, ValueError) as error:
        raise SystemExit(f"Edge client error: {error}") from error
