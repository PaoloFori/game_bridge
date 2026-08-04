"""Wire protocol for the Cortical Peaks Challenge 2026 BCI/game server.

Ported from `cortical-peaks-challenge-2026/shared/connection/protocol.py` and
`PROTOCOL.md`, trimmed to the message types a BCI client actually sends and
receives: a BCI client never gets STATE or SESSIONS frames (those are
spectator-only), so those branches are intentionally not implemented here.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from enum import IntEnum

TOKEN_SIZE = 8  # bytes on wire
UID_SIZE = 16  # bytes on wire
CMD_SIZE = 8  # bytes on wire


class MessageType(IntEnum):
    REGISTER = 1
    ACK = 2
    PING = 3
    PONG = 4
    CMD = 5


class DeviceType(IntEnum):
    BCI = 0
    SPECTATOR = 1


@dataclass
class RegisterMessage:
    display_name: str
    device: DeviceType


@dataclass
class PingMessage:
    """Client-initiated heartbeat; server responds with ServerPongMessage."""

    session_token: str
    device: DeviceType


@dataclass
class PongMessage:
    """Client response to a server-initiated ServerPingMessage."""

    session_token: str
    device: DeviceType


@dataclass
class CmdMessage:
    """Game command from BCI client to server."""

    session_token: str
    device: DeviceType
    content: str


ClientMessage = RegisterMessage | PingMessage | PongMessage | CmdMessage


@dataclass
class AckMessage:
    """Successful registration response carrying this device's session token."""

    session_token: str


@dataclass
class ServerPingMessage:
    """Server-initiated heartbeat; client responds with PongMessage."""


@dataclass
class ServerPongMessage:
    """Server response to a client-initiated PingMessage."""


ServerMessage = AckMessage | ServerPingMessage | ServerPongMessage


def _enc_token(token: str) -> bytes:
    return bytes.fromhex(token)


def _enc_uid(uid: str) -> bytes:
    encoded = uid.encode("utf-8")
    if len(encoded) > UID_SIZE:
        encoded = encoded[:UID_SIZE]
        while encoded:
            try:
                encoded.decode("utf-8")
                break
            except UnicodeDecodeError:
                encoded = encoded[:-1]
    return encoded.ljust(UID_SIZE, b"\x00")


def _enc_cmd(content: str) -> bytes:
    return content.encode("utf-8")[:CMD_SIZE].ljust(CMD_SIZE, b"\x00")


def to_bytes(msg: ClientMessage) -> bytes:
    """Serialize a client-originated (BCI to server) message to bytes."""
    match msg:
        case RegisterMessage(display_name=display_name, device=device):
            return struct.pack("!BB16s", MessageType.REGISTER, int(device), _enc_uid(display_name))
        case PingMessage(session_token=token, device=device):
            return struct.pack("!BB8s", MessageType.PING, int(device), _enc_token(token))
        case PongMessage(session_token=token, device=device):
            return struct.pack("!BB8s", MessageType.PONG, int(device), _enc_token(token))
        case CmdMessage(session_token=token, device=device, content=content):
            return struct.pack("!BB8s8s", MessageType.CMD, int(device), _enc_token(token), _enc_cmd(content))
        case _:
            err = f"Unsupported client message: {msg!r}"
            raise ValueError(err)


def parse_server_message(data: bytes) -> ServerMessage:
    """
    Deserialize raw UDP bytes into a typed server message.

    Raises
    ------
    ValueError
        If the data is empty, the type byte is unknown or not one a BCI
        client should ever receive, or the frame is the wrong size.

    """
    if not data:
        err = "Empty datagram"
        raise ValueError(err)
    try:
        msg_type = MessageType(data[0])
        match msg_type:
            case MessageType.ACK:
                _, token_bytes = struct.unpack("!B8s", data)
                return AckMessage(session_token=token_bytes.hex())
            case MessageType.PING:
                if len(data) != 1:
                    err = f"Server PING frame must be 1 byte, got {len(data)}"
                    raise ValueError(err)
                return ServerPingMessage()
            case MessageType.PONG:
                if len(data) != 1:
                    err = f"Server PONG frame must be 1 byte, got {len(data)}"
                    raise ValueError(err)
                return ServerPongMessage()
            case _:
                err = f"Unexpected server message type for a BCI client: {msg_type!r}"
                raise ValueError(err)
    except (struct.error, ValueError) as exc:
        err = f"Malformed server message: {exc}"
        raise ValueError(err) from exc
