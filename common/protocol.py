"""Length-prefixed transport for monitoring metadata and JPEG frames."""

from __future__ import annotations

import json
import socket
import struct
from typing import Any, Optional, Tuple


HEADER = struct.Struct("!II")
MAX_METADATA_BYTES = 64 * 1024
MAX_IMAGE_BYTES = 16 * 1024 * 1024


class ConnectionClosed(ConnectionError):
    """Raised when a peer closes a connection between packet boundaries."""


def _recv_exact(sock: socket.socket, size: int, *, allow_clean_eof: bool = False) -> Optional[bytes]:
    data = bytearray()
    while len(data) < size:
        chunk = sock.recv(size - len(data))
        if not chunk:
            if allow_clean_eof and not data:
                return None
            raise ConnectionClosed("connection closed while receiving a packet")
        data.extend(chunk)
    return bytes(data)


def send_packet(sock: socket.socket, metadata: dict[str, Any], image: bytes = b"") -> None:
    metadata_bytes = json.dumps(metadata, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(metadata_bytes) > MAX_METADATA_BYTES:
        raise ValueError("metadata exceeds the protocol limit")
    if len(image) > MAX_IMAGE_BYTES:
        raise ValueError("image exceeds the protocol limit")
    sock.sendall(HEADER.pack(len(metadata_bytes), len(image)) + metadata_bytes + image)


def receive_packet(sock: socket.socket) -> Optional[Tuple[dict[str, Any], bytes]]:
    header = _recv_exact(sock, HEADER.size, allow_clean_eof=True)
    if header is None:
        return None

    metadata_size, image_size = HEADER.unpack(header)
    if metadata_size > MAX_METADATA_BYTES or image_size > MAX_IMAGE_BYTES:
        raise ValueError("received packet exceeds the protocol limit")

    metadata_bytes = _recv_exact(sock, metadata_size)
    image = _recv_exact(sock, image_size) if image_size else b""
    assert metadata_bytes is not None
    assert image is not None

    metadata = json.loads(metadata_bytes.decode("utf-8"))
    if not isinstance(metadata, dict):
        raise ValueError("metadata must be a JSON object")
    return metadata, image
