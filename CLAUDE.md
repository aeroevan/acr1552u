# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

This project uses [uv](https://docs.astral.sh/uv/) for dependency management and Python 3.11.

```bash
# Install dependencies and activate venv
uv sync

# Run the library interactively (requires USB access)
uv run python -c "from acr1552u import ACR1552U; ..."

# Type-check
uv run pyright src/

# No test suite exists yet — tests would require real hardware
```

USB access: the device at `072F:2308` requires either root or a udev rule granting the user ACL access (e.g. `/dev/bus/usb/001/NNN`). `pcscd` is not needed.

## Architecture

Three-layer design:

**`transport.py` — `CCIDTransport`**
Speaks raw USB via `libusb1`. Opens the CCID-class interface, claims it (detaching the kernel driver if needed), and sends/receives CCID bulk transfers. The only public method is `send_escape(cmd: bytes) -> bytes`, which wraps `cmd` in a `PC_to_RDR_Escape` (0x6B) CCID message and returns the payload from the `RDR_to_PC_Escape` (0x83) response, stripping the 10-byte CCID header and the 5-byte escape prefix `[E1 00 00 00 Le]`.

On `close()`, the kernel driver is re-attached so the device remains usable by the OS afterward.

**Initialization / recovery (`_ccid_init`)**
After claiming the interface, the transport sends `PC_to_RDR_Abort` (0x72) over bulk-OUT before any escape commands. This is the only reliable way to flush the device's CCID state machine after a USB reset or incomplete transaction — the CCID control-level ABORT request returns `LIBUSB_ERROR_PIPE` on this hardware. After draining the abort response, a `GetSlotStatus` exchange confirms the device is live.

**`commands.py` — `ACR1552U`**
High-level driver. Each method corresponds to one section of the vendor reference manual (REF-ACR1552U-Series-1.08.pdf, section 6). Every escape command follows the wire format `[E0 00 P1 P2 Lc_or_Le data...]`; responses arrive as plain bytes after the transport strips the prefix. The shorthand `self._esc(*args)` converts positional ints to bytes and calls `send_escape`.

`ACR1552U` accepts an optional pre-built `CCIDTransport` for testing or advanced use; otherwise it constructs and owns one.

**`constants.py`**
All enums (`IntEnum` / `IntFlag`) for command parameters and return values. All `ACR1552U` methods accept either the enum or a raw `int`.

## Hardware notes

- Confirmed firmware: `ACR1552 R FW 5.00.01` (ACR1552U-A* variant with RGB LED)
- `get_auto_pps()` times out on this firmware — it is unsupported
- `get_led_status()` returns 3 bytes (R, G, B) on the A* variant, not 1
- `set_rf_power()` causes the reader to reset
- Card emulation: must call `enter_card_emulation_mode()` with `CARD_READ_WRITE` before switching to another emulation mode
