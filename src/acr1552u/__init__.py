"""
acr1552u – Python library for the ACS ACR1552U NFC reader.

Communicates directly via libusb1 using raw CCID PC_to_RDR_Escape
messages (no PC/SC driver required).

Quickstart::

    from acr1552u import ACR1552U

    with ACR1552U() as reader:
        print(reader.get_firmware_version())
        print(reader.get_picc_status())
"""

from .commands import (
    ACR1552U,
    AutoPPS,
    BuzzerRepeatable,
    OutputFormatConfig,
    PICCPollingType,
    PICCTypeStatus,
    UIDChars,
)
from .constants import (
    AutoPPSSpeed,
    CardEmulationStatus,
    DiscoveryMode,
    EmulationLock,
    HostInterface,
    KeyboardLanguage,
    LEDStatus,
    NFCMode,
    PICCPollingTypeByte0,
    PICCPollingTypeByte1,
    PICCStatus,
    PICCType,
    PollingATROption,
    RFPower,
    RFStatus,
    SNInUSBDescriptor,
    SelectiveSuspend,
    UIBehaviour,
)
from .transport import CCIDError, CCIDTransport

__all__ = [
    # Main driver
    "ACR1552U",
    # Transport
    "CCIDTransport",
    "CCIDError",
    # Response dataclasses
    "AutoPPS",
    "BuzzerRepeatable",
    "OutputFormatConfig",
    "PICCPollingType",
    "PICCTypeStatus",
    "UIDChars",
    # Enums / constants
    "AutoPPSSpeed",
    "CardEmulationStatus",
    "DiscoveryMode",
    "EmulationLock",
    "HostInterface",
    "KeyboardLanguage",
    "LEDStatus",
    "NFCMode",
    "PICCPollingTypeByte0",
    "PICCPollingTypeByte1",
    "PICCStatus",
    "PICCType",
    "PollingATROption",
    "RFPower",
    "RFStatus",
    "SNInUSBDescriptor",
    "SelectiveSuspend",
    "UIBehaviour",
]
