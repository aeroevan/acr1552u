from enum import IntEnum, IntFlag


class RFStatus(IntEnum):
    OFF = 0x00
    ON_WITH_POLLING = 0x01
    ON_WITHOUT_POLLING = 0x02


class PICCStatus(IntEnum):
    RF_OFF = 0x00
    NO_PICC = 0x01
    PICC_READY = 0x02
    PICC_SELECTED = 0x03
    ERROR = 0xFF


class PICCType(IntEnum):
    NO_PICC = 0xCC
    TOPAZ = 0x04
    MIFARE = 0x10
    FELICA = 0x11
    TYPE_A_PART4 = 0x20
    TYPE_B_PART4 = 0x23
    INNOVATRON = 0x25
    SRIX = 0x28
    PICOPASS = 0x30
    OTHER = 0xFF


class AutoPPSSpeed(IntEnum):
    """106 kbps (no auto PPS) through 848 kbps."""
    SPEED_106_KBPS = 0x00
    SPEED_212_KBPS = 0x01
    SPEED_424_KBPS = 0x02
    SPEED_848_KBPS = 0x03


class RFPower(IntEnum):
    DISABLE = 0x00
    PERCENT_20 = 0x01
    PERCENT_40 = 0x02
    PERCENT_60 = 0x03
    PERCENT_80 = 0x04
    PERCENT_100 = 0x05


class PollingATROption(IntFlag):
    """Bitmask for the Polling/ATR Option byte (section 6.1.4)."""
    ENABLE_POLLING = 0x01
    ENABLE_RF_OFF_INTERVAL = 0x02
    # Bit 2 = RFU
    ENABLE_EXTRA_MIFARE_ID_IN_ATR = 0x08
    # Bits 4-5 = RF Off Interval (00=no interval, 01=250ms, 10=1000ms, 11=2500ms when bit1=1)
    RF_OFF_INTERVAL_LOW = 0x10
    RF_OFF_INTERVAL_HIGH = 0x20
    # Bit 6 = RFU
    ENABLE_PART4_ATR_FOR_SMARTMX = 0x80


class PICCPollingTypeByte1(IntFlag):
    """Byte 1 bitmask for Set/Get PICC Polling Type (section 6.1.6)."""
    ISO14443A = 0x01
    ISO14443B = 0x02
    FELICA = 0x04
    # Bit 3 = RFU
    TOPAZ = 0x10
    INNOVATRON = 0x20
    SRI_SRIX = 0x40
    # Bit 7 = RFU


class PICCPollingTypeByte0(IntFlag):
    """Byte 0 bitmask for Set/Get PICC Polling Type (section 6.1.6)."""
    PICOPASS_ISO14443B = 0x01
    PICOPASS_ISO15693 = 0x02
    ISO15693 = 0x04
    CTS = 0x08
    # Bits 4-7 = RFU


class SelectiveSuspend(IntEnum):
    DISABLE = 0x00
    ENABLE = 0x01


class NFCMode(IntEnum):
    """NFC device mode for card emulation commands."""
    CARD_READ_WRITE = 0x00
    NFC_FORUM_TYPE2_TAG = 0x02
    FELICA = 0x03


class DiscoveryMode(IntEnum):
    CARD_READER = 0x00
    NFC_FORUM_TYPE2_TAG = 0x02
    FELICA = 0x03


class HostInterface(IntEnum):
    ONLY_HID_KEYBOARD = 0x00
    ONLY_CCID_READER = 0x01
    HID_KEYBOARD_AND_CCID = 0x02


class KeyboardLanguage(IntEnum):
    ENGLISH = 0x00
    FRENCH = 0x01
    RESERVED = 0x02
    LITHUANIAN = 0x03


class OutputFormat(IntEnum):
    """Lower nibble = Display Mode, upper nibble = Letter Case (section 6.1.14.2)."""
    # Display modes (lower 4 bits)
    HEX = 0x00
    DEC_BYTE_BY_BYTE = 0x01
    DEC = 0x02
    # Letter cases (upper 4 bits, shift left 4 to combine)
    CASE_LOWERCASE = 0x00
    CASE_UPPERCASE = 0x10


class OutputOrder(IntEnum):
    DEFAULT = 0x00
    REVERSE_ALL = 0x01
    REVERSE_ISO14443_AND_FELICA = 0x02
    REVERSE_ISO15693 = 0x04


class LEDStatus(IntFlag):
    """Bitmask for Set/Get LED Control (section 6.2.7)."""
    BLUE = 0x01
    GREEN = 0x02


class EmulationLock(IntFlag):
    """Lock bits for Set Card Emulation Lock Data (section 6.1.15.7)."""
    NFC_FORUM_TYPE2_TAG = 0x01
    FELICA = 0x02


class CardEmulationStatus(IntFlag):
    """Status bits returned by Get Card Emulation Status (section 6.1.15.9)."""
    CARD_DETECTING = 0x01
    CARD_WRITTEN = 0x02
    CARD_READ = 0x04
    CARD_READ_ALL = 0x08
    CARD_REMOVED = 0x10
    CARD_ACTIVATED = 0x20


class UIBehaviour(IntFlag):
    """Bitmask for Get/Set UI Behaviour (section 6.2.10)."""
    ACCESSING_LED_FAST_BLINK = 0x01
    PICC_POLLING_STATUS_LED = 0x02
    PICC_ACTIVATION_STATUS_LED = 0x04
    PRESENCE_EVENT_BEEP = 0x08
    CARD_REMOVAL_EVENT_BEEP = 0x10
    POWER_UP_EVENT_BEEP = 0x20


class SNInUSBDescriptor(IntEnum):
    DISABLE = 0x00
    ENABLE = 0x01
