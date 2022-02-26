"""
The device module provides a high-level abstraction over an Eques Elf device,
including commands for execution.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any


@dataclass
class Device:
    """
    Device represents an Eques Elf device.

    NB: Currently only smart plugs are supported, so implicitly the state is for
    the smart plug relay.
    """

    """IP address of the device."""
    ip: str

    """MAC address of the device."""
    mac: str

    """Password of the device for LAN commands."""
    password: str

    """State of the relay. When `None`, the state is unknown."""
    state: Optional[bool]

    def as_dict(self) -> Dict[str, Any]:
        """
        Serializes the Device as a dictionary.
        """
        return asdict(self)

    @staticmethod
    def from_dict(blob: Dict[str, Any]) -> Device:
        """
        Deserializes the Device as a dictionary.
        """
        return Device(
            ip=blob["ip"],
            mac=blob["mac"],
            password=blob["password"],
            state=blob.get("state"),
        )
