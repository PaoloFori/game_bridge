"""ROS2 node that speaks the Cortical Peaks Challenge 2026 wire protocol.

Subscribes to a topic of already-decided game commands (published by a
separate controller node) and forwards them to the game server as CMD
messages, while handling registration and heartbeat on its own. Which
server it talks to (local vs. the competition server) is purely a matter
of the `server_host`/`server_port` parameters -- see config/local.yaml and
config/host.yaml.
"""

from __future__ import annotations

import socket
import threading
import time
from datetime import timedelta

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

from game_bridge.protocol import (
    AckMessage,
    CmdMessage,
    DeviceType,
    PingMessage,
    PongMessage,
    RegisterMessage,
    ServerMessage,
    ServerPingMessage,
    ServerPongMessage,
    parse_server_message,
    to_bytes,
)

BUFFER_SIZE = 65535
HEARTBEAT_PERIOD = timedelta(seconds=1)
SERVER_TIMEOUT = timedelta(seconds=3)
SOCKET_TIMEOUT = timedelta(seconds=2)
REGISTER_RETRY_PERIOD = timedelta(seconds=1)

VALID_COMMANDS = {"INPUT_A", "INPUT_B", "INPUT_C", "INPUT_D"}


class GameBridgeNode(Node):
    def __init__(self) -> None:
        super().__init__("game_bridge")

        self.declare_parameter("server_host", "127.0.0.1")
        self.declare_parameter("server_port", 5000)
        self.declare_parameter("display_name", f"game_bridge-{socket.gethostname()}")
        self.declare_parameter("command_topic", "/game/command")

        self._server_address = (
            self.get_parameter("server_host").get_parameter_value().string_value,
            self.get_parameter("server_port").get_parameter_value().integer_value,
        )
        self._display_name = self.get_parameter("display_name").get_parameter_value().string_value
        command_topic = self.get_parameter("command_topic").get_parameter_value().string_value

        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.settimeout(SOCKET_TIMEOUT.total_seconds())

        self._connected = False
        self._session_token = ""
        self._last_received_time = time.monotonic()
        self._running = True

        self._status_pub = self.create_publisher(String, "~/status", 10)
        self.create_subscription(String, command_topic, self._on_command, 10)

        self._listener_thread = threading.Thread(target=self._network_listener, daemon=True)
        self._heartbeat_thread = threading.Thread(target=self._heartbeat_worker, daemon=True)
        self._listener_thread.start()
        self._heartbeat_thread.start()

        self.get_logger().info(
            f"game_bridge targeting {self._server_address[0]}:{self._server_address[1]} "
            f"(display_name={self._display_name}, command_topic={command_topic})"
        )

    def _on_command(self, msg: String) -> None:
        if msg.data not in VALID_COMMANDS:
            self.get_logger().warning(f"Ignoring unrecognised command {msg.data!r}")
            return
        if not self._connected:
            self.get_logger().warning(f"Dropping command {msg.data!r}: not connected to game server")
            return
        cmd = CmdMessage(session_token=self._session_token, device=DeviceType.BCI, content=msg.data)
        self._sock.sendto(to_bytes(cmd), self._server_address)
        self.get_logger().debug(f"Sent CMD {msg.data} to {self._server_address}")

    def _network_listener(self) -> None:
        while self._running:
            if not self._connected:
                reg = RegisterMessage(display_name=self._display_name, device=DeviceType.BCI)
                self._sock.sendto(to_bytes(reg), self._server_address)
                time.sleep(REGISTER_RETRY_PERIOD.total_seconds())

            try:
                data, _ = self._sock.recvfrom(BUFFER_SIZE)
                msg = parse_server_message(data)
                self._handle_server_message(msg)
            except TimeoutError:
                pass
            except ValueError:
                self.get_logger().debug("Dropped malformed server packet")
            except OSError:
                if self._running:
                    time.sleep(0.1)

    def _handle_server_message(self, msg: ServerMessage) -> None:
        match msg:
            case AckMessage(session_token=token):
                was_connected = self._connected
                self._session_token = token
                self._connected = True
                self._last_received_time = time.monotonic()
                if not was_connected:
                    self.get_logger().info(f"Registered with game server, session {token}")
                    self._publish_status("connected")

            case ServerPingMessage():
                self._last_received_time = time.monotonic()
                pong = PongMessage(session_token=self._session_token, device=DeviceType.BCI)
                self._sock.sendto(to_bytes(pong), self._server_address)

            case ServerPongMessage():
                self._last_received_time = time.monotonic()

    def _heartbeat_worker(self) -> None:
        while self._running:
            if self._connected:
                ping = PingMessage(session_token=self._session_token, device=DeviceType.BCI)
                self._sock.sendto(to_bytes(ping), self._server_address)

                if time.monotonic() - self._last_received_time > SERVER_TIMEOUT.total_seconds():
                    self.get_logger().warning("Game server timed out, will re-register")
                    self._connected = False
                    self._session_token = ""
                    self._publish_status("disconnected")

            time.sleep(HEARTBEAT_PERIOD.total_seconds())

    def _publish_status(self, status: str) -> None:
        self._status_pub.publish(String(data=status))

    def destroy_node(self) -> None:
        self._running = False
        self._sock.close()
        super().destroy_node()


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = GameBridgeNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
