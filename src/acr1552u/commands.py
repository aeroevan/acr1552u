"""
All ACR1552U escape commands (section 6 of REF-ACR1552U-Series-1.08).

Command wire format:  [E0, 00, P1, P2, Lc_or_Le, data...]
Response wire format: [E1, 00, 00, 00, Le, data...]  (transport strips prefix)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

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
    RFPower,
    RFStatus,
    SNInUSBDescriptor,
    SelectiveSuspend,
    UIBehaviour,
)
from .transport import CCIDTransport


@dataclass
class PICCPollingType:
    byte1: int  # ISO14443A/B, FeliCa, Topaz, Innovatron, SRI/SRIX flags
    byte0: int  # Picopass, ISO15693, CTS flags


@dataclass
class AutoPPS:
    max_speed: int
    current_speed: int


@dataclass
class PICCTypeStatus:
    picc_type: int
    status: int


@dataclass
class OutputFormatConfig:
    output_format: int
    output_order: int


@dataclass
class UIDChars:
    between: int
    end: int
    start: int


@dataclass
class BuzzerRepeatable:
    on_time: int   # 10ms units
    off_time: int  # 10ms units
    repeat_count: int


class ACR1552U:
    """
    High-level driver for all ACS ACR1552U escape commands.

    Usage::

        with ACR1552U() as reader:
            fw = reader.get_firmware_version()
            print(fw)
    """

    DEFAULT_VID = 0x072F
    DEFAULT_PID = 0x2308

    def __init__(
        self,
        transport: Optional[CCIDTransport] = None,
        vendor_id: int = DEFAULT_VID,
        product_id: int = DEFAULT_PID,
        interface_index: int = 0,
        slot: int = 0,
        timeout_ms: int = 5000,
    ) -> None:
        if transport is not None:
            self._t = transport
            self._owns_transport = False
        else:
            self._t = CCIDTransport(
                vendor_id=vendor_id,
                product_id=product_id,
                interface_index=interface_index,
                slot=slot,
                timeout_ms=timeout_ms,
            )
            self._owns_transport = True

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self) -> "ACR1552U":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        if self._owns_transport:
            self._t.close()

    # ------------------------------------------------------------------
    # Internal shorthand
    # ------------------------------------------------------------------

    def _esc(self, *args: int) -> bytes:
        return self._t.send_escape(bytes(args))

    # ==================================================================
    # 6.1  Escape Commands for PICC
    # ==================================================================

    # 6.1.1 ─ RF Control [E0 00 00 25 01 …]
    def rf_control(self, status: RFStatus | int) -> int:
        """Set RF control. Returns confirmed RF status byte."""
        resp = self._esc(0xE0, 0x00, 0x00, 0x25, 0x01, int(status))
        return resp[0]

    # 6.1.2 ─ Get PCD/PICC Status [E0 00 00 25 00]
    def get_picc_status(self) -> int:
        """Return PCD/PICC status byte (see PICCStatus enum)."""
        resp = self._esc(0xE0, 0x00, 0x00, 0x25, 0x00)
        return resp[0]

    # 6.1.3 ─ Get Polling/ATR Option [E0 00 00 23 00]
    def get_polling_atr_option(self) -> int:
        """Return the 1-byte Polling/ATR option bitmask."""
        resp = self._esc(0xE0, 0x00, 0x00, 0x23, 0x00)
        return resp[0]

    # 6.1.4 ─ Set Polling/ATR Option [E0 00 00 23 01 …]
    def set_polling_atr_option(self, option: int) -> int:
        """Set Polling/ATR option. Returns confirmed option byte."""
        resp = self._esc(0xE0, 0x00, 0x00, 0x23, 0x01, option & 0xFF)
        return resp[0]

    # 6.1.5 ─ Get PICC Polling Type [E0 00 01 20 00]
    def get_picc_polling_type(self) -> PICCPollingType:
        """Return current PICC polling type as a PICCPollingType(byte1, byte0)."""
        resp = self._esc(0xE0, 0x00, 0x01, 0x20, 0x00)
        # Response: [Byte1, Byte0]
        return PICCPollingType(byte1=resp[0], byte0=resp[1])

    # 6.1.6 ─ Set PICC Polling Type [E0 00 01 20 02 …]
    def set_picc_polling_type(self, byte1: int, byte0: int) -> PICCPollingType:
        """
        Set PICC polling type.

        *byte1* controls ISO14443A/B, FeliCa, Topaz, etc.
        *byte0* controls Picopass, ISO15693, CTS.
        Default: byte1=0x07 (ISO14443A, ISO14443B, FeliCa), byte0=0x05.
        """
        resp = self._esc(0xE0, 0x00, 0x01, 0x20, 0x02, byte1 & 0xFF, byte0 & 0xFF)
        return PICCPollingType(byte1=resp[0], byte0=resp[1])

    # 6.1.7 ─ Get Auto PPS [E0 00 00 24 00]
    def get_auto_pps(self) -> AutoPPS:
        """Return AutoPPS(max_speed, current_speed). See AutoPPSSpeed enum."""
        resp = self._esc(0xE0, 0x00, 0x00, 0x24, 0x00)
        return AutoPPS(max_speed=resp[0], current_speed=resp[1])

    # 6.1.8 ─ Set Auto PPS [E0 00 00 24 01 …]
    def set_auto_pps(self, max_speed: AutoPPSSpeed | int) -> AutoPPS:
        """Set maximum Auto PPS speed. Default: 0x02 (424 kbps)."""
        resp = self._esc(0xE0, 0x00, 0x00, 0x24, 0x01, int(max_speed))
        return AutoPPS(max_speed=resp[0], current_speed=resp[1])

    # 6.1.9 ─ Read PICC Type [E0 00 00 35 00]
    def read_picc_type(self) -> PICCTypeStatus:
        """Return PICCTypeStatus(picc_type, status). See PICCType/PICCStatus enums."""
        resp = self._esc(0xE0, 0x00, 0x00, 0x35, 0x00)
        return PICCTypeStatus(picc_type=resp[0], status=resp[1])

    # 6.1.10 ─ Get RF Power Setting [E0 00 00 50 00]
    def get_rf_power(self) -> int:
        """Return current RF power byte (see RFPower enum)."""
        resp = self._esc(0xE0, 0x00, 0x00, 0x50, 0x00)
        return resp[0]

    # 6.1.11 ─ Set RF Power Setting [E0 00 01 50 01 …]
    def set_rf_power(self, rf_power: RFPower | int) -> int:
        """
        Set RF power level. Note: reader resets after this command.
        Default: 0x00 (disable manual RF power, use firmware default).
        """
        resp = self._esc(0xE0, 0x00, 0x01, 0x50, 0x01, int(rf_power))
        return resp[0]

    # 6.1.12 ─ Get Selective Suspend Setting [E0 00 00 E5 00]
    def get_selective_suspend(self) -> int:
        """Return selective suspend setting byte (see SelectiveSuspend enum)."""
        resp = self._esc(0xE0, 0x00, 0x00, 0xE5, 0x00)
        return resp[0]

    # 6.1.13 ─ Set Selective Suspend Setting [E0 00 00 E5 01 …]
    def set_selective_suspend(self, setting: SelectiveSuspend | int) -> int:
        """Enable or disable selective suspend. Cannot be enabled in HID keyboard mode."""
        resp = self._esc(0xE0, 0x00, 0x00, 0xE5, 0x01, int(setting))
        return resp[0]

    # ==================================================================
    # 6.1.14  Escape Commands for PICC – HID Keyboard
    # ==================================================================

    # 6.1.14.1 ─ Get Output Format [E0 00 00 90 00]
    def get_output_format(self) -> OutputFormatConfig:
        """Return OutputFormatConfig(output_format, output_order)."""
        resp = self._esc(0xE0, 0x00, 0x00, 0x90, 0x00)
        return OutputFormatConfig(output_format=resp[0], output_order=resp[1])

    # 6.1.14.2 ─ Set Output Format [E0 00 00 90 02 …]
    def set_output_format(self, output_format: int, output_order: int) -> OutputFormatConfig:
        """
        Set HID keyboard output format and byte order.

        *output_format*: upper nibble = letter case, lower nibble = display mode.
        *output_order*: see OutputOrder enum.
        """
        resp = self._esc(
            0xE0, 0x00, 0x00, 0x90, 0x02,
            output_format & 0xFF,
            output_order & 0xFF,
        )
        return OutputFormatConfig(output_format=resp[0], output_order=resp[1])

    # 6.1.14.3 ─ Get Character at Start, Between, at End UID [E0 00 00 91 00]
    def get_uid_chars(self) -> UIDChars:
        """Return UIDChars(between, end, start). 0xFF = no character."""
        resp = self._esc(0xE0, 0x00, 0x00, 0x91, 0x00)
        return UIDChars(between=resp[0], end=resp[1], start=resp[2])

    # 6.1.14.4 ─ Set Character at Start, Between, at End UID [E0 00 00 91 03 …]
    def set_uid_chars(self, between: int, end: int, start: int) -> UIDChars:
        """
        Set HID keyboard UID delimiter characters.
        Values are USB HID usage codes; 0xFF = no character.
        """
        resp = self._esc(
            0xE0, 0x00, 0x00, 0x91, 0x03,
            between & 0xFF,
            end & 0xFF,
            start & 0xFF,
        )
        return UIDChars(between=resp[0], end=resp[1], start=resp[2])

    # 6.1.14.5 ─ Get Keyboard Layout Language [E0 00 00 92 00]
    def get_keyboard_language(self) -> int:
        """Return keyboard layout language byte (see KeyboardLanguage enum)."""
        resp = self._esc(0xE0, 0x00, 0x00, 0x92, 0x00)
        return resp[0]

    # 6.1.14.6 ─ Set Keyboard Layout Language [E0 00 00 92 01 …]
    def set_keyboard_language(self, language: KeyboardLanguage | int) -> int:
        """Set keyboard layout language. Default: 0x00 (English)."""
        resp = self._esc(0xE0, 0x00, 0x00, 0x92, 0x01, int(language))
        return resp[0]

    # 6.1.14.7 ─ Get Host Interface [E0 00 00 93 00]
    def get_host_interface(self) -> int:
        """Return host interface mode byte (see HostInterface enum)."""
        resp = self._esc(0xE0, 0x00, 0x00, 0x93, 0x00)
        return resp[0]

    # 6.1.14.8 ─ Set Host Interface [E0 00 00 93 01 …]
    def set_host_interface(self, interface: HostInterface | int) -> int:
        """Set host interface mode. Default: 0x01 (CCID reader only)."""
        resp = self._esc(0xE0, 0x00, 0x00, 0x93, 0x01, int(interface))
        return resp[0]

    # ==================================================================
    # 6.1.15  Escape Commands for PICC – Card Emulation
    # ==================================================================

    # 6.1.15.1 ─ Enter Card Emulation Mode [E0 00 00 40 03 …]
    def enter_card_emulation_mode(self, nfc_mode: NFCMode | int) -> bytes:
        """
        Enter card emulation mode.

        *nfc_mode*: 0x02 = NFC Forum Type 2 Tag, 0x03 = FeliCa.
        Note: enter card read/write mode first before switching emulation modes.
        Returns the 3-byte NFC mode echo.
        """
        resp = self._esc(0xE0, 0x00, 0x00, 0x40, 0x03, int(nfc_mode), 0x00, 0x00)
        return resp  # 3 bytes: NFC mode echo

    # 6.1.15.2 ─ Read Card Emulation Data (NFC Forum Type 2 Tag) [E0 00 00 60 04 …]
    def read_emulation_data(
        self, nfc_mode: NFCMode | int, start_offset: int, length: int
    ) -> bytes:
        """Read *length* bytes of emulated card data at *start_offset*."""
        resp = self._esc(
            0xE0, 0x00, 0x00, 0x60, 0x04,
            0x00,
            int(nfc_mode),
            start_offset & 0xFF,
            length & 0xFF,
        )
        return resp

    # 6.1.15.3 ─ Write Card Emulation Data (NFC Forum Type 2 Tag) [E0 00 00 60 …]
    def write_emulation_data(
        self, nfc_mode: NFCMode | int, start_offset: int, data: bytes
    ) -> bytes:
        """
        Write *data* to emulated card memory at *start_offset*.
        Returns [length, 0x90, 0x00] on success.
        """
        lc = len(data) + 4
        cmd = bytes([
            0xE0, 0x00, 0x00, 0x60, lc,
            0x01, int(nfc_mode), start_offset & 0xFF, len(data) & 0xFF,
        ]) + data
        return self._t.send_escape(cmd)

    # 6.1.15.4 ─ Read Card Emulation Data Extended [E0 00 01 60 05 …]
    def read_emulation_data_extended(
        self, nfc_mode: NFCMode | int, start_offset: int, length: int
    ) -> bytes:
        """Read *length* bytes at 16-bit *start_offset* (from SN0 in memory map)."""
        offset_hi = (start_offset >> 8) & 0xFF
        offset_lo = start_offset & 0xFF
        resp = self._esc(
            0xE0, 0x00, 0x01, 0x60, 0x05,
            0x00,
            int(nfc_mode),
            offset_hi,
            offset_lo,
            length & 0xFF,
        )
        return resp

    # 6.1.15.5 ─ Write Card Emulation Data Extended [E0 00 01 60 …]
    def write_emulation_data_extended(
        self, nfc_mode: NFCMode | int, start_offset: int, data: bytes
    ) -> bytes:
        """
        Write *data* to emulated card memory using 16-bit *start_offset*.
        Returns [length, 0x90, 0x00] on success.
        """
        offset_hi = (start_offset >> 8) & 0xFF
        offset_lo = start_offset & 0xFF
        lc = len(data) + 5
        cmd = bytes([
            0xE0, 0x00, 0x01, 0x60, lc,
            0x01, int(nfc_mode), offset_hi, offset_lo, len(data) & 0xFF,
        ]) + data
        return self._t.send_escape(cmd)

    # 6.1.15.6 ─ Set Card Emulation NFC Forum Type 2 Tag ID [E0 00 00 61 03 …]
    def set_emulation_type2_tag_id(self, uid: bytes) -> bytes:
        """
        Set 3-byte UID of the emulated NFC Forum Type 2 Tag.
        Returns [0x90, 0x00] on success.
        """
        if len(uid) != 3:
            raise ValueError("UID must be exactly 3 bytes")
        resp = self._esc(0xE0, 0x00, 0x00, 0x61, 0x03, uid[0], uid[1], uid[2])
        return resp

    # 6.1.15.7 ─ Set Card Emulation Lock Data [E0 00 00 65 01 …]
    def set_emulation_lock(self, lock: EmulationLock | int) -> int:
        """
        Set lock bits to prevent NFC-side writes.
        Bit 0 = NFC Forum Type 2 Tag lock, Bit 1 = FeliCa lock.
        USB escape commands can still write regardless.
        """
        resp = self._esc(0xE0, 0x00, 0x00, 0x65, 0x01, int(lock) & 0xFF)
        return resp[0]

    # 6.1.15.8 ─ Set Card Emulation FeliCa IDm [E0 00 00 64 06 …]
    def set_emulation_felica_idm(self, idm: bytes) -> bytes:
        """
        Set the 6-byte FeliCa Card Identification Number (IDm) for emulation.
        Manufacturer Code is fixed at 0x03 0x88.
        Returns the confirmed 6-byte IDm.
        """
        if len(idm) != 6:
            raise ValueError("IDm must be exactly 6 bytes")
        resp = self._esc(
            0xE0, 0x00, 0x00, 0x64, 0x06,
            idm[0], idm[1], idm[2], idm[3], idm[4], idm[5],
        )
        return resp

    # 6.1.15.9 ─ Get Card Emulation Status [E0 00 00 69 00]
    def get_emulation_status(self) -> int:
        """Return card emulation status bitmask (see CardEmulationStatus flags)."""
        resp = self._esc(0xE0, 0x00, 0x00, 0x69, 0x00)
        return resp[0]

    # ==================================================================
    # 6.1.16  Escape Commands for PICC – Discovery Mode
    # ==================================================================

    # 6.1.16.1 ─ Enter Discovery Mode [E0 00 00 6A 01 …]
    def enter_discovery_mode(self, mode: DiscoveryMode | int) -> int:
        """
        Enter discovery mode.

        *mode*: 0x00 = card reader, 0x02 = NFC Forum Type 2 Tag, 0x03 = FeliCa.
        Returns confirmed discovery mode byte.
        """
        resp = self._esc(0xE0, 0x00, 0x00, 0x6A, 0x01, int(mode))
        return resp[0]

    # ==================================================================
    # 6.2  Escape Commands for Peripheral Control and Other
    # ==================================================================

    # 6.2.1 ─ Get Firmware Version [E0 00 00 18 00]
    def get_firmware_version(self) -> str:
        """Return firmware version string, e.g. 'ACR1552 R FW 1.00.00'."""
        resp = self._esc(0xE0, 0x00, 0x00, 0x18, 0x00)
        return resp.decode("ascii", errors="replace")

    # 6.2.2 ─ Get Serial Number [E0 00 00 33 00]
    def get_serial_number(self) -> bytes:
        """Return raw serial number bytes."""
        return self._esc(0xE0, 0x00, 0x00, 0x33, 0x00)

    # 6.2.3 ─ Set S/N in USB Descriptor [E0 00 00 F0 …]
    def set_sn_in_usb_descriptor(self, enable: SNInUSBDescriptor | int) -> bytes:
        """
        Enable or disable serial number in USB descriptor.
        Returns [enable_byte, 0x90, 0x00] on success.
        Default: 0x01 (enabled).
        """
        resp = self._esc(0xE0, 0x00, 0x00, 0xF0, 0x02, 0x00, int(enable))
        return resp

    # 6.2.4 ─ Set Buzzer Control – Single Time [E0 00 00 28 01 …]
    def buzzer_single(self, duration: int) -> int:
        """
        Sound buzzer once.

        *duration*: 0x00 = off, 0x01–0xFF = on duration in 10ms units.
        Returns confirmed duration byte.
        """
        resp = self._esc(0xE0, 0x00, 0x00, 0x28, 0x01, duration & 0xFF)
        return resp[0]

    # 6.2.5 ─ Set Buzzer Control – Repeatable [E0 00 00 28 03 …]
    def buzzer_repeatable(
        self, on_time: int, off_time: int, repeat_count: int
    ) -> BuzzerRepeatable:
        """
        Set repeating buzzer pattern.

        All times in 10ms units; 0x01–0xFF range.
        *repeat_count*: number of on/off cycles.
        """
        resp = self._esc(
            0xE0, 0x00, 0x00, 0x28, 0x03,
            on_time & 0xFF,
            off_time & 0xFF,
            repeat_count & 0xFF,
        )
        return BuzzerRepeatable(
            on_time=resp[0], off_time=resp[1], repeat_count=resp[2]
        )

    # 6.2.6 ─ Get LED Status [E0 00 00 29 00]
    def get_led_status(self) -> bytes:
        """
        Return current LED status byte(s).
        Standard models return 1 byte; ACR1552U-A* (RGB) returns 3 bytes.
        """
        return self._esc(0xE0, 0x00, 0x00, 0x29, 0x00)

    # 6.2.7 ─ Set LED Control [E0 00 00 29 01 …]
    def set_led(self, led_status: LEDStatus | int) -> int:
        """
        Set LED state. Bit 0 = Blue, Bit 1 = Green (1 = on).
        Returns confirmed LED status byte.
        """
        resp = self._esc(0xE0, 0x00, 0x00, 0x29, 0x01, int(led_status) & 0xFF)
        return resp[0]

    # 6.2.8 ─ Set RGB LED Control (ACR1552U-A* only) [E0 00 00 29 03 …]
    def set_rgb_led(self, red: int, green: int, blue: int) -> bytes:
        """
        Set RGB LED colour (ACR1552U-A* only). Values 0x01–0xFF per channel.
        Returns confirmed [red, green, blue] bytes.
        """
        resp = self._esc(
            0xE0, 0x00, 0x00, 0x29, 0x03,
            red & 0xFF,
            green & 0xFF,
            blue & 0xFF,
        )
        return resp

    # 6.2.9 ─ Get UI Behaviour [E0 00 00 21 00]
    def get_ui_behaviour(self) -> int:
        """Return UI behaviour bitmask (see UIBehaviour flags). Default: 0x2F."""
        resp = self._esc(0xE0, 0x00, 0x00, 0x21, 0x00)
        return resp[0]

    # 6.2.10 ─ Set UI Behaviour [E0 00 00 21 01 …]
    def set_ui_behaviour(self, behaviour: UIBehaviour | int) -> int:
        """Set UI behaviour bitmask. Returns confirmed byte."""
        resp = self._esc(0xE0, 0x00, 0x00, 0x21, 0x01, int(behaviour) & 0xFF)
        return resp[0]
