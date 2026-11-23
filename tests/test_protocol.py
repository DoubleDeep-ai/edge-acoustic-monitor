import socket
import unittest

from common.protocol import ConnectionClosed, receive_packet, send_packet


class ProtocolTests(unittest.TestCase):
    def test_metadata_and_image_round_trip(self):
        sender, receiver = socket.socketpair()
        self.addCleanup(sender.close)
        self.addCleanup(receiver.close)

        expected = {"device_id": "machine-1", "anomaly": True, "temperature": 23.4}
        send_packet(sender, expected, b"jpeg-bytes")

        self.assertEqual(receive_packet(receiver), (expected, b"jpeg-bytes"))

    def test_clean_disconnect_returns_none(self):
        sender, receiver = socket.socketpair()
        receiver.close()
        self.addCleanup(sender.close)

        self.assertIsNone(receive_packet(sender))

    def test_truncated_packet_raises(self):
        sender, receiver = socket.socketpair()
        self.addCleanup(sender.close)
        self.addCleanup(receiver.close)

        sender.sendall(b"\x00\x00\x00\x05\x00\x00\x00\x00{}")
        sender.shutdown(socket.SHUT_WR)

        with self.assertRaises(ConnectionClosed):
            receive_packet(receiver)


if __name__ == "__main__":
    unittest.main()
