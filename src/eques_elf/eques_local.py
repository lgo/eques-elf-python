"""
eques_local provides local network commands for the Eques Elf smart plug.

Support commands include:
- Discovery broadcast
- Status query
- Toggle on or off

Original author: iamckn
Source code adapted from https://github.com/iamckn/eques/blob/master/exploit/equeslocal.go
"""
from __future__ import annotations

import binascii
from datetime import datetime, timedelta
import select
import socket
from typing import List, Tuple
from Crypto.Cipher import AES
import logging
import json

from .device import Device

logger = logging.getLogger(__name__)

AES_KEY = binascii.unhexlify(
    b"6664736c3b6d6577726a6f706534353666647334666276666e6a77617567666f"
)
CIPHER = AES.new(AES_KEY, AES.MODE_ECB)
DEVICE_PORT = 27431

# Broadcast across the whole subet.
BROADCAST_ADDRESS = "255.255.255.255"
# Listen for to all IPs for responses.
LISTEN_ADDRESS = "0.0.0.0"
# Use an arbitrary port assigned by the OS.
LISTEN_PORT = 0

# Broadcast srv.
BROADCAST_SOCKET = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
# Enable port reusage.
BROADCAST_SOCKET.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
# Enable broadcasting mode
BROADCAST_SOCKET.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

# ... srv.
COMMAND_SOCKET = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
# Enable port reusage.
COMMAND_SOCKET.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
COMMAND_SOCKET.bind((LISTEN_ADDRESS, LISTEN_PORT))


def _unpad(text: bytes) -> bytes:
    return text.rstrip(b"\x00")


def _pad(text: bytes, size: int) -> bytes:
    if len(text) % size == 0:
        return text
    padded_len = len(text) + size - len(text) % size
    return text.ljust(padded_len, b"\x00")


def _decrypt(ciphertext: bytes) -> str:
    """
    Decrypts ciphertext for Eques devices.
    """
    return _unpad(CIPHER.decrypt(ciphertext)).decode()


def _encrypt(plaintext: str) -> bytes:
    """
    Encrypts plaintext for Eques devices.
    """
    return CIPHER.encrypt(_pad(plaintext.encode(), AES.block_size))


def _send_command(
    device: Device, command: str, timeout_sec: float = 0.2
) -> List[Tuple[bytes, str]]:
    """
    Sends a command to a Eques device.
    """
    responses: List[Tuple[bytes, str]] = []
    # Bind for listening to responses.
    # COMMAND_SOCKET.bind((LISTEN_ADDRESS, LISTEN_PORT))
    assigned_port = COMMAND_SOCKET.getsockname()[1]
    logger.info(f"listening on port={assigned_port}")

    # Send the broadcast to devices.
    logger.debug(f"sent command: {command}")
    message = _encrypt(command)
    COMMAND_SOCKET.sendto(message, (device.ip, DEVICE_PORT))

    before = datetime.now()

    # Listen for responses.
    while _socket_has_message(COMMAND_SOCKET, timeout_sec):
        after = datetime.now()
        delay_ms = (after - before) / timedelta(milliseconds=1)
        logger.debug(f"got response in {delay_ms}ms")
        data, addr = COMMAND_SOCKET.recvfrom(1024)
        responses.append((data, addr))
        before = datetime.now()

    # COMMAND_SOCKET.close()

    return responses


def _broadcast_command(
    command: str, timeout_sec: float = 0.5
) -> List[Tuple[bytes, str]]:
    """
    Broadcasts a command to Eques devices and listens for responses.

    Waits for :timeout (sec) to collect responses before returning.
    """
    responses: List[Tuple[bytes, str]] = []
    # Bind for listening to responses.
    BROADCAST_SOCKET.bind((LISTEN_ADDRESS, LISTEN_PORT))
    assigned_port = BROADCAST_SOCKET.getsockname()[1]
    logger.info(f"listening on port={assigned_port}")

    # Send the broadcast to devices.
    message = _encrypt(command)
    BROADCAST_SOCKET.sendto(message, (BROADCAST_ADDRESS, DEVICE_PORT))

    before = datetime.now()

    # Listen for responses.
    while _socket_has_message(BROADCAST_SOCKET, timeout_sec):
        after = datetime.now()
        delay_ms = (after - before) / timedelta(milliseconds=1)
        logger.debug(f"got response in {delay_ms}ms")
        data, addr = BROADCAST_SOCKET.recvfrom(1024)
        ip, _port = addr
        responses.append((data, ip))
        before = datetime.now()

    BROADCAST_SOCKET.close()

    return responses


def _socket_has_message(sock: socket.socket, timeout_sec: float) -> bool:
    ready, _, _ = select.select([sock], [], [], timeout_sec)
    return len(ready) > 0


def _formatted(dt: datetime) -> str:
    """Using in discovery commands"""
    return dt.strftime("%Y-%m-%d-%H:%M:%S")


def discover_command() -> List[Device]:
    formatted_dt = _formatted(datetime.now())
    command = f"lan_phone%mac%nopassword%{formatted_dt}%heart"
    logger.debug(f"sending: {command}")
    responses = _broadcast_command(command)
    logger.debug(f"response size={len(responses)}")
    devices = [unwrap_heartbeat_resp(ip, _decrypt(data)) for data, ip in responses]
    return devices


def parse_status(status_blob: str) -> bool:
    status, *_ = status_blob.split("#")
    if status == "open":
        return True
    elif status == "close":
        return False
    else:
        raise Exception(f"unexpected status: {status}")


def unwrap_heartbeat_resp(ip: str, resp: str) -> Device:
    logger.debug(f"response: {resp}")

    split = resp.split("%")
    if len(split) != 5:
        logger.warn(f"unexpected heartbeat response size (not 5): {resp}")

    _mode, mac, password, status_blob, _msg_type = split
    state = parse_status(status_blob)
    return Device(ip=ip, mac=mac, password=password, state=state)


def unwrap_command_resp(device: Device, resp_ip: str, resp: str) -> Device:
    logger.debug(f"response: {resp}")

    split = resp.split("%")
    if len(split) != 5:
        logger.warn(f"unexpected response size (not 5): {resp}")

    _mode, _mac, _password, status_blob, _msg_type = split
    # TODO(joey): Possibly verify mac and address match the device data?
    device.state = parse_status(status_blob)
    return device


def status_command(device: Device) -> List[Device]:
    command = f"lan_phone%{device.mac}%{device.password}%check%relay"
    responses = _send_command(device, command)
    devices = [
        unwrap_command_resp(device, resp_ip, _decrypt(data))
        for data, resp_ip in responses
    ]
    return devices


def off_command(device: Device) -> List[Device]:
    command = f"lan_phone%{device.mac}%{device.password}%close%relay"
    responses = _send_command(device, command)
    devices = [
        unwrap_command_resp(device, resp_ip, _decrypt(data))
        for data, resp_ip in responses
    ]
    return devices


def on_command(device: Device) -> List[Device]:
    command = f"lan_phone%{device.mac}%{device.password}%open%relay"
    responses = _send_command(device, command)
    devices = [
        unwrap_command_resp(device, resp_ip, _decrypt(data))
        for data, resp_ip in responses
    ]
    return devices
