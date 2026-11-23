"""Thread-safe PyAudio input stream used by the Raspberry Pi client."""

from __future__ import annotations

from queue import Empty, Queue
from typing import Iterator, Optional

import pyaudio


class MicrophoneStream:
    def __init__(self, rate: int, chunk: int):
        self.rate = rate
        self.chunk = chunk
        self.buffer: Queue[Optional[bytes]] = Queue()
        self.closed = True

    def __enter__(self) -> "MicrophoneStream":
        self.audio_interface = pyaudio.PyAudio()
        self.audio_stream = self.audio_interface.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.rate,
            input=True,
            frames_per_buffer=self.chunk,
            stream_callback=self._fill_buffer,
        )
        self.closed = False
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.audio_stream.stop_stream()
        self.audio_stream.close()
        self.closed = True
        self.buffer.put(None)
        self.audio_interface.terminate()

    def _fill_buffer(self, data, frame_count, time_info, status_flags):
        self.buffer.put(data)
        return None, pyaudio.paContinue

    def generator(self) -> Iterator[bytes]:
        while not self.closed:
            chunk = self.buffer.get()
            if chunk is None:
                return
            chunks = [chunk]
            while True:
                try:
                    chunk = self.buffer.get_nowait()
                    if chunk is None:
                        return
                    chunks.append(chunk)
                except Empty:
                    break
            yield b"".join(chunks)
