# acr1552u

Python library for the [ACS ACR1552U](https://www.acs.com.hk/en/products/419/acr1552u-usb-nfc-reader-iv/) NFC reader/writer. Communicates directly over USB via raw CCID escape commands — no PC/SC daemon or middleware required.

## Features

- Direct USB communication via `libusb1` (no `pcscd`)
- Full coverage of the vendor escape command set (reference manual section 6)
- RF control, PICC polling, card type detection
- Card emulation: NFC Forum Type 2 Tag and FeliCa
- Discovery mode
- LED (mono and RGB), buzzer, UI behaviour
- HID keyboard output configuration (output format, UID delimiters, keyboard language)
- Type-annotated API; enums for all command parameters and return values

## Requirements

- Python 3.11+
- [libusb1](https://pypi.org/project/libusb1/) (`pip install libusb1`)
- USB access to the device at `072F:2308`

### USB permissions (Linux)

Either run as root, or add a udev rule:

```
SUBSYSTEM=="usb", ATTRS{idVendor}=="072f", ATTRS{idProduct}=="2308", TAG+="uaccess"
```

Save to `/etc/udev/rules.d/99-acr1552u.rules` and run `udevadm control --reload-rules && udevadm trigger`.

## Installation

```bash
pip install acr1552u
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv add acr1552u
```

## Quickstart

```python
from acr1552u import ACR1552U, PICCStatus

with ACR1552U() as reader:
    print(reader.get_firmware_version())   # e.g. "ACR1552 R FW 5.00.01"

    status = reader.get_picc_status()
    if status == PICCStatus.PICC_READY:
        t = reader.read_picc_type()
        print(f"Card present: type={t.picc_type:#04x}")
```

## API Reference

All methods are on `ACR1552U`. Every parameter that corresponds to a vendor enum accepts either the enum member or a raw `int`.

### PICC / RF

| Method | Description |
|---|---|
| `rf_control(status)` | Turn RF on/off (see `RFStatus`) |
| `get_picc_status()` | Current PCD/PICC state (see `PICCStatus`) |
| `get_polling_atr_option()` / `set_polling_atr_option(option)` | Polling and ATR behaviour flags |
| `get_picc_polling_type()` / `set_picc_polling_type(byte1, byte0)` | Which card families to poll (ISO14443A/B, FeliCa, Topaz, ISO15693, …) |
| `get_auto_pps()` / `set_auto_pps(max_speed)` | Automatic Protocol and Parameter Selection speed |
| `read_picc_type()` | Type and status of card in field (see `PICCType`) |
| `get_rf_power()` / `set_rf_power(rf_power)` | RF field strength — **note: causes reader reset** |
| `get_selective_suspend()` / `set_selective_suspend(setting)` | USB selective suspend |

### Card Emulation

Before switching to an emulation mode, always call `enter_card_emulation_mode(NFCMode.CARD_READ_WRITE)` first.

| Method | Description |
|---|---|
| `enter_card_emulation_mode(nfc_mode)` | Switch to card read/write, NFC Forum Type 2, or FeliCa emulation |
| `read_emulation_data(nfc_mode, offset, length)` | Read from emulated card memory |
| `write_emulation_data(nfc_mode, offset, data)` | Write to emulated card memory |
| `read_emulation_data_extended(...)` / `write_emulation_data_extended(...)` | 16-bit offset variants for larger memory maps |
| `set_emulation_type2_tag_id(uid)` | Set 3-byte UID for emulated NFC Forum Type 2 Tag |
| `set_emulation_felica_idm(idm)` | Set 6-byte FeliCa IDm |
| `set_emulation_lock(lock)` | Prevent NFC-side writes (USB escape commands still work) |
| `get_emulation_status()` | Read/write/activation event flags (see `CardEmulationStatus`) |

### Discovery Mode

```python
from acr1552u import ACR1552U, DiscoveryMode

with ACR1552U() as reader:
    reader.enter_discovery_mode(DiscoveryMode.CARD_READER)
```

### LED and Buzzer

```python
from acr1552u import ACR1552U

with ACR1552U() as reader:
    # RGB LED (ACR1552U-A* variant)
    reader.set_rgb_led(red=0xFF, green=0x00, blue=0x00)

    # Buzzer: single beep (50 ms)
    reader.buzzer_single(duration=5)

    # Buzzer: repeating pattern
    reader.buzzer_repeatable(on_time=5, off_time=5, repeat_count=3)
```

| Method | Description |
|---|---|
| `get_led_status()` | Current LED state (1 byte standard, 3 bytes RGB on A* variant) |
| `set_led(led_status)` | Blue/Green LED on/off (see `LEDStatus`) |
| `set_rgb_led(red, green, blue)` | Full-colour LED (ACR1552U-A* only) |
| `buzzer_single(duration)` | One-shot buzzer in 10ms units |
| `buzzer_repeatable(on_time, off_time, repeat_count)` | Repeating buzzer pattern |
| `get_ui_behaviour()` / `set_ui_behaviour(behaviour)` | LED/beep event triggers (see `UIBehaviour`) |

### HID Keyboard Mode

| Method | Description |
|---|---|
| `get_host_interface()` / `set_host_interface(interface)` | CCID-only, HID-only, or both (see `HostInterface`) |
| `get_output_format()` / `set_output_format(fmt, order)` | Hex/decimal, case, byte order for keyboard output |
| `get_uid_chars()` / `set_uid_chars(between, end, start)` | Delimiter characters around UID output (USB HID usage codes) |
| `get_keyboard_language()` / `set_keyboard_language(lang)` | Keyboard layout (see `KeyboardLanguage`) |

### Device Info

| Method | Description |
|---|---|
| `get_firmware_version()` | Firmware version string |
| `get_serial_number()` | Raw serial number bytes |
| `set_sn_in_usb_descriptor(enable)` | Include/exclude S/N from USB descriptor |

## Architecture

Three-layer design:

**`transport.py` — `CCIDTransport`**  
Speaks raw USB via `libusb1`. Opens the CCID-class interface, detaches the kernel driver if needed, and sends/receives CCID bulk transfers. The one public method is `send_escape(cmd: bytes) -> bytes`, which wraps the command in a `PC_to_RDR_Escape` (0x6B) CCID frame and returns the payload from the `RDR_to_PC_Escape` (0x83) response with the 10-byte CCID header and 5-byte escape prefix stripped.

**`commands.py` — `ACR1552U`**  
High-level driver. Each method maps to one section of the vendor reference manual. `ACR1552U` accepts an optional pre-built `CCIDTransport` for testing or advanced use; otherwise it constructs and owns one.

**`constants.py`**  
`IntEnum` / `IntFlag` types for all command parameters and return values.

## Hardware Notes

- Confirmed firmware: `ACR1552 R FW 5.00.01` (ACR1552U-A* variant with RGB LED)
- `get_auto_pps()` times out on this firmware — the command is unsupported on the A* variant
- `get_led_status()` returns 3 bytes (R, G, B) on the A* variant rather than 1
- `set_rf_power()` causes the reader to reset

## Development

```bash
# Install dependencies
uv sync

# Type-check
uv run pyright src/

# Interactive use (requires USB access)
uv run python -c "from acr1552u import ACR1552U; r = ACR1552U(); print(r.get_firmware_version()); r.close()"
```

No automated test suite exists — tests require real hardware.
