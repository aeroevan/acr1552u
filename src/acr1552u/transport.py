import struct
from typing import Optional

import usb1

CCID_CLASS = 0x0B
CCID_PC_TO_RDR_ESCAPE = 0x6B
CCID_PC_TO_RDR_ABORT = 0x72
CCID_PC_TO_RDR_GET_SLOT_STATUS = 0x65
CCID_RDR_TO_PC_SLOT_STATUS = 0x81
CCID_RDR_TO_PC_ESCAPE = 0x83

# 10-byte CCID message header, 5-byte escape response prefix [E1 00 00 00 Le]
_CCID_HDR_SIZE = 10
_ESC_RESP_PREFIX_SIZE = 5

_TIMEOUT_MS = 5000
_INIT_TIMEOUT_MS = 2000
_DRAIN_TIMEOUT_MS = 200


class CCIDError(Exception):
    def __init__(self, status: int, error: int) -> None:
        self.status = status
        self.error = error
        super().__init__(f"CCID error: status=0x{status:02X} error=0x{error:02X}")


class CCIDTransport:
    """
    Sends CCID PC_to_RDR_Escape messages (0x6B) directly via libusb1 bulk
    transfers and returns the abData payload from RDR_to_PC_Escape (0x83).

    Escape command wire format (abData sent in Bulk-OUT):
        [E0, 00, P1, P2, Lc_or_Le, data...]

    Escape response wire format (abData from Bulk-IN):
        [E1, 00, 00, 00, Le, data[Le]...]

    The transport sends a PC_to_RDR_GetSlotStatus exchange at startup so the
    device is in a known CCID state before the first escape command, and
    re-attaches the kernel driver on close so the device stays usable between
    sessions.
    """

    def __init__(
        self,
        vendor_id: int = 0x072F,
        product_id: int = 0x2308,
        interface_index: int = 0,
        slot: int = 0,
        timeout_ms: int = _TIMEOUT_MS,
    ) -> None:
        self._slot = slot
        self._seq = 0
        self._timeout = timeout_ms
        self._interface_num: Optional[int] = None
        self._bulk_out: Optional[int] = None
        self._bulk_in: Optional[int] = None
        self._had_kernel_driver = False

        self._ctx = usb1.USBContext()
        self._handle = self._ctx.openByVendorIDAndProductID(vendor_id, product_id)
        if self._handle is None:
            raise RuntimeError(
                f"USB device {vendor_id:04X}:{product_id:04X} not found; "
                "try running as root or adding a udev rule"
            )
        self._setup_interface(interface_index)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _setup_interface(self, index: int) -> None:
        device = self._handle.getDevice()
        ccid_seen = 0
        for config in device.iterConfigurations():
            for interface in config.iterInterfaces():
                for setting in interface.iterSettings():
                    if setting.getClass() != CCID_CLASS:
                        continue
                    if ccid_seen < index:
                        ccid_seen += 1
                        continue
                    bulk_in = bulk_out = None
                    for ep in setting.iterEndpoints():
                        addr = ep.getAddress()
                        if (ep.getAttributes() & 0x03) == 0x02:  # Bulk
                            if addr & 0x80:
                                bulk_in = addr
                            else:
                                bulk_out = addr
                    if bulk_in is None or bulk_out is None:
                        raise RuntimeError(
                            f"CCID interface {setting.getNumber()} is missing bulk endpoints"
                        )
                    iface_num = setting.getNumber()
                    self._had_kernel_driver = self._handle.kernelDriverActive(iface_num)
                    if self._had_kernel_driver:
                        self._handle.detachKernelDriver(iface_num)
                    self._handle.claimInterface(iface_num)
                    # Clear any endpoint stall from a previous incomplete transaction.
                    for ep in (bulk_out, bulk_in):
                        try:
                            self._handle.clearHalt(ep)
                        except Exception:
                            pass
                    self._interface_num = iface_num
                    self._bulk_out = bulk_out
                    self._bulk_in = bulk_in
                    self._ccid_init()
                    return
        raise RuntimeError(f"CCID interface index {index} not found on this device")

    def _ccid_init(self) -> None:
        """
        Reset the device's CCID state machine, drain stale data, then confirm
        the device responds to GetSlotStatus before the first escape command.

        PC_to_RDR_Abort (0x72) sent over bulk-OUT causes the device to flush
        any in-progress command and reply with RDR_to_PC_SlotStatus, recovering
        from states where the device accepts writes but sends no responses (e.g.
        after a USB reset or a previous bulkRead timeout).
        """
        # Send PC_to_RDR_Abort to flush any stuck command state.
        abort = struct.pack(
            "<BIBBBBB",
            CCID_PC_TO_RDR_ABORT,
            0,
            self._slot,
            0xFE,   # sentinel sequence for abort probe
            0x00, 0x00, 0x00,
        )
        try:
            self._handle.bulkWrite(self._bulk_out, abort, _INIT_TIMEOUT_MS)
        except usb1.USBErrorTimeout:
            pass

        # Drain all pending IN data (including the abort SlotStatus response).
        while True:
            try:
                self._handle.bulkRead(self._bulk_in, 64, _DRAIN_TIMEOUT_MS)
            except usb1.USBErrorTimeout:
                break

        # GetSlotStatus: bMsgType=0x65, dwLen=0, bSlot, bSeq, bRFU x3
        hdr = struct.pack(
            "<BIBBBBB",
            CCID_PC_TO_RDR_GET_SLOT_STATUS,
            0,
            self._slot,
            0xFF,   # sequence 0xFF for init probe
            0x00, 0x00, 0x00,
        )
        try:
            self._handle.bulkWrite(self._bulk_out, hdr, _INIT_TIMEOUT_MS)
            raw = bytes(self._handle.bulkRead(self._bulk_in, 64, _INIT_TIMEOUT_MS))
            if len(raw) >= _CCID_HDR_SIZE and raw[0] == CCID_RDR_TO_PC_SLOT_STATUS:
                pass  # device is alive and responding
        except usb1.USBErrorTimeout:
            # Device didn't respond to slot status; it may still accept escapes.
            pass

    def _next_seq(self) -> int:
        seq = self._seq
        self._seq = (self._seq + 1) & 0xFF
        return seq

    def _ccid_header(self, msg_type: int, data_len: int, seq: int) -> bytes:
        return struct.pack(
            "<BIBBBBB",
            msg_type,
            data_len,
            self._slot,
            seq,
            0x00, 0x00, 0x00,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def send_escape(self, cmd: bytes) -> bytes:
        """
        Send *cmd* as a CCID escape command and return the response payload.

        *cmd* should be the raw escape bytes, e.g. b'\\xE0\\x00\\x00\\x18\\x00'
        for Get Firmware Version.

        Returns the data portion of the escape response (everything after the
        5-byte [E1 00 00 00 Le] prefix).
        """
        seq = self._next_seq()
        msg = self._ccid_header(CCID_PC_TO_RDR_ESCAPE, len(cmd), seq) + cmd
        self._handle.bulkWrite(self._bulk_out, msg, self._timeout)

        raw = bytes(self._handle.bulkRead(self._bulk_in, 65536, self._timeout))
        if len(raw) < _CCID_HDR_SIZE:
            raise RuntimeError(f"CCID response too short: {len(raw)} bytes")

        msg_type, ab_len, _slot, _seq, status, error, _rfu = struct.unpack_from(
            "<BIBBBBB", raw
        )
        if msg_type != CCID_RDR_TO_PC_ESCAPE:
            raise RuntimeError(
                f"Unexpected CCID message type: 0x{msg_type:02X} (expected 0x83)"
            )
        if status & 0x40:
            raise CCIDError(status, error)

        abdata = raw[_CCID_HDR_SIZE : _CCID_HDR_SIZE + ab_len]
        if len(abdata) < _ESC_RESP_PREFIX_SIZE:
            raise RuntimeError(
                f"Escape response abData too short: {len(abdata)} bytes"
            )
        # abdata layout: [E1, 00, 00, 00, Le, payload...]
        data_len = abdata[4]
        return bytes(abdata[_ESC_RESP_PREFIX_SIZE : _ESC_RESP_PREFIX_SIZE + data_len])

    def close(self) -> None:
        if self._interface_num is not None:
            iface = self._interface_num
            self._interface_num = None
            try:
                self._handle.releaseInterface(iface)
            except Exception:
                pass
            # Re-attach the kernel driver so the device is usable by pcscd/OS
            # after this session ends.
            if self._had_kernel_driver:
                try:
                    self._handle.attachKernelDriver(iface)
                except Exception:
                    pass
        if self._handle is not None:
            self._handle.close()
            self._handle = None
        if self._ctx is not None:
            self._ctx.close()
            self._ctx = None

    def __enter__(self) -> "CCIDTransport":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
