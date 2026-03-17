"""PayNow QR code generator implementing the SGQR (EMVCo) standard.

Generates PayNow QR codes for employee reimbursements and ad-hoc payments.
Pure client-side implementation -- no external API calls.

SGQR specification: EMVCo QR Code Specification for Payment Systems (CPS)
Merchant Account ID for PayNow: 26 (PayNow proxy type + value)
"""

from __future__ import annotations

import io
import logging
import struct
import zlib
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)

PROVIDER_NAME = "paynow"

# EMVCo TLV tag constants
TAG_PAYLOAD_FORMAT = "00"
TAG_POI_METHOD = "01"
TAG_MERCHANT_ACCOUNT_PAYNOW = "26"
TAG_TRANSACTION_CURRENCY = "53"
TAG_TRANSACTION_AMOUNT = "54"
TAG_COUNTRY_CODE = "58"
TAG_MERCHANT_NAME = "59"
TAG_MERCHANT_CITY = "60"
TAG_ADDITIONAL_DATA = "62"
TAG_CRC = "63"

# PayNow sub-tags (within tag 26)
SUBTAG_GUID = "00"  # Globally Unique Identifier
SUBTAG_PROXY_TYPE = "01"  # 0=mobile, 2=UEN
SUBTAG_PROXY_VALUE = "02"  # Phone number / NRIC / UEN
SUBTAG_EDITABLE = "03"  # 0=not editable, 1=editable
SUBTAG_EXPIRY = "04"  # YYYYMMDD

# Additional data sub-tags (within tag 62)
SUBTAG_BILL_NUMBER = "01"
SUBTAG_REFERENCE = "05"

# PayNow constants
PAYNOW_GUID = "SG.PAYNOW"
CURRENCY_SGD = "702"
COUNTRY_SG = "SG"
DEFAULT_CITY = "Singapore"


class ProxyType(str, Enum):
    """PayNow proxy types."""

    MOBILE = "0"  # +65XXXXXXXX
    NRIC = "1"  # Not commonly used for QR
    UEN = "2"  # Company UEN


class PayNowQRError(Exception):
    """Raised when QR generation fails."""

    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(f"PayNow QR error: {detail}")


class PayNowAdapter:
    """PayNow QR code generator implementing SGQR/EMVCo standard.

    Generates QR code data strings and PNG images for PayNow payments.
    Entirely client-side -- no external API dependencies.

    Usage::

        adapter = PayNowAdapter()

        # Generate QR for mobile number
        qr_data, png_bytes = adapter.generate_qr(
            recipient_type=ProxyType.MOBILE,
            recipient_id="+6591234567",
            amount=150.00,
            reference="CLAIM-2026-001",
        )

        # Generate QR for company UEN
        qr_data, png_bytes = adapter.generate_qr(
            recipient_type=ProxyType.UEN,
            recipient_id="201234567K",
            amount=5000.00,
            reference="SALARY-MAR-2026",
        )
    """

    def generate_qr(
        self,
        recipient_type: ProxyType,
        recipient_id: str,
        amount: Optional[float] = None,
        reference: str = "",
        merchant_name: str = "",
        editable: bool = False,
        expiry_date: Optional[str] = None,
    ) -> tuple[str, bytes]:
        """Generate PayNow QR code data string and PNG image.

        Args:
            recipient_type: ProxyType.MOBILE or ProxyType.UEN.
            recipient_id: Phone number (with +65) or UEN.
            amount: Payment amount in SGD. None = open amount.
            reference: Payment reference / bill number.
            merchant_name: Recipient name for display on QR.
            editable: Whether amount is editable by payer.
            expiry_date: QR expiry date in YYYYMMDD format.

        Returns:
            Tuple of (qr_data_string, png_bytes).
            qr_data_string can be encoded into any QR library.
            png_bytes is a minimal QR code PNG image.

        Raises:
            PayNowQRError: If inputs are invalid.
        """
        # Validate inputs
        self._validate_inputs(recipient_type, recipient_id, amount)

        # Build EMVCo TLV payload
        qr_data = self._build_payload(
            recipient_type=recipient_type,
            recipient_id=recipient_id,
            amount=amount,
            reference=reference,
            merchant_name=merchant_name,
            editable=editable,
            expiry_date=expiry_date,
        )

        # Generate PNG QR code
        png_bytes = self._generate_qr_png(qr_data)

        logger.info(
            "Generated PayNow QR: type=%s, id=%s, amount=%s, ref=%s",
            recipient_type.value,
            self._mask_id(recipient_id),
            f"${amount:.2f}" if amount else "open",
            reference,
        )

        return qr_data, png_bytes

    def generate_qr_data_only(
        self,
        recipient_type: ProxyType,
        recipient_id: str,
        amount: Optional[float] = None,
        reference: str = "",
        merchant_name: str = "",
        editable: bool = False,
        expiry_date: Optional[str] = None,
    ) -> str:
        """Generate only the QR data string (no image).

        Useful when the caller will render the QR code themselves
        (e.g., in a frontend component).

        Returns:
            SGQR-compliant data string.
        """
        self._validate_inputs(recipient_type, recipient_id, amount)

        return self._build_payload(
            recipient_type=recipient_type,
            recipient_id=recipient_id,
            amount=amount,
            reference=reference,
            merchant_name=merchant_name,
            editable=editable,
            expiry_date=expiry_date,
        )

    # ------------------------------------------------------------------
    # EMVCo TLV payload construction
    # ------------------------------------------------------------------

    def _build_payload(
        self,
        recipient_type: ProxyType,
        recipient_id: str,
        amount: Optional[float],
        reference: str,
        merchant_name: str,
        editable: bool,
        expiry_date: Optional[str],
    ) -> str:
        """Build the EMVCo QR Code TLV payload string."""
        parts: list[str] = []

        # Payload Format Indicator (mandatory, always "01")
        parts.append(self._tlv(TAG_PAYLOAD_FORMAT, "01"))

        # Point of Initiation Method
        # "11" = static (reusable QR), "12" = dynamic (one-time)
        poi = "12" if amount else "11"
        parts.append(self._tlv(TAG_POI_METHOD, poi))

        # Merchant Account Information (PayNow)
        paynow_data = self._build_paynow_block(recipient_type, recipient_id, editable, expiry_date)
        parts.append(self._tlv(TAG_MERCHANT_ACCOUNT_PAYNOW, paynow_data))

        # Transaction Currency (SGD = 702)
        parts.append(self._tlv(TAG_TRANSACTION_CURRENCY, CURRENCY_SGD))

        # Transaction Amount (if specified)
        if amount is not None:
            parts.append(self._tlv(TAG_TRANSACTION_AMOUNT, f"{amount:.2f}"))

        # Country Code
        parts.append(self._tlv(TAG_COUNTRY_CODE, COUNTRY_SG))

        # Merchant Name
        name = merchant_name or "PAYNOW"
        parts.append(self._tlv(TAG_MERCHANT_NAME, name[:25]))

        # Merchant City
        parts.append(self._tlv(TAG_MERCHANT_CITY, DEFAULT_CITY))

        # Additional Data (reference / bill number)
        if reference:
            additional = self._tlv(SUBTAG_REFERENCE, reference[:25])
            parts.append(self._tlv(TAG_ADDITIONAL_DATA, additional))

        # CRC placeholder -- will be replaced with actual CRC
        payload_without_crc = "".join(parts) + f"{TAG_CRC}04"
        crc = self._crc16(payload_without_crc)
        parts.append(self._tlv(TAG_CRC, crc))

        return "".join(parts)

    def _build_paynow_block(
        self,
        recipient_type: ProxyType,
        recipient_id: str,
        editable: bool,
        expiry_date: Optional[str],
    ) -> str:
        """Build the PayNow merchant account TLV sub-block."""
        sub_parts: list[str] = []

        # GUID
        sub_parts.append(self._tlv(SUBTAG_GUID, PAYNOW_GUID))

        # Proxy Type
        sub_parts.append(self._tlv(SUBTAG_PROXY_TYPE, recipient_type.value))

        # Proxy Value
        sub_parts.append(self._tlv(SUBTAG_PROXY_VALUE, recipient_id))

        # Editable flag
        edit_flag = "1" if editable else "0"
        sub_parts.append(self._tlv(SUBTAG_EDITABLE, edit_flag))

        # Expiry date (optional)
        if expiry_date:
            sub_parts.append(self._tlv(SUBTAG_EXPIRY, expiry_date))

        return "".join(sub_parts)

    @staticmethod
    def _tlv(tag: str, value: str) -> str:
        """Build a TLV (Tag-Length-Value) string.

        Tag: 2 characters
        Length: 2 characters (zero-padded)
        Value: variable
        """
        length = f"{len(value):02d}"
        return f"{tag}{length}{value}"

    @staticmethod
    def _crc16(data: str) -> str:
        """Calculate CRC-16/CCITT-FALSE checksum per EMVCo spec.

        Polynomial: 0x1021, Init: 0xFFFF
        """
        crc = 0xFFFF
        for byte in data.encode("utf-8"):
            crc ^= byte << 8
            for _ in range(8):
                if crc & 0x8000:
                    crc = (crc << 1) ^ 0x1021
                else:
                    crc <<= 1
                crc &= 0xFFFF
        return f"{crc:04X}"

    # ------------------------------------------------------------------
    # QR Code PNG generation (minimal, no external library)
    # ------------------------------------------------------------------

    def _generate_qr_png(self, data: str) -> bytes:
        """Generate a minimal QR code PNG from data string.

        Uses a pure-Python QR code generator for portability.
        If `qrcode` library is available, uses it for better quality.
        Otherwise returns an empty PNG placeholder.
        """
        try:
            import qrcode
            from qrcode.image.pure import PyPNGImage

            qr = qrcode.QRCode(
                version=None,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=10,
                border=4,
            )
            qr.add_data(data)
            qr.make(fit=True)

            img = qr.make_image(image_factory=PyPNGImage)
            buffer = io.BytesIO()
            img.save(buffer)
            return buffer.getvalue()

        except ImportError:
            # Fallback: generate a 1x1 transparent PNG placeholder
            # The QR data string is still valid and can be used with
            # any frontend QR rendering library
            logger.warning(
                "qrcode library not installed. Returning placeholder PNG. "
                "Install with: pip install qrcode[pil]"
            )
            return self._placeholder_png()

    @staticmethod
    def _placeholder_png() -> bytes:
        """Generate a minimal 1x1 pixel PNG as placeholder.

        The real QR rendering should happen in the frontend using
        the data string returned alongside this placeholder.
        """

        # Minimal valid PNG: 1x1 white pixel
        def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
            chunk = chunk_type + data
            crc = zlib.crc32(chunk) & 0xFFFFFFFF
            return struct.pack(">I", len(data)) + chunk + struct.pack(">I", crc)

        signature = b"\x89PNG\r\n\x1a\n"
        ihdr_data = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
        ihdr = _png_chunk(b"IHDR", ihdr_data)
        raw_data = b"\x00\xff\xff\xff"  # filter byte + RGB white
        idat_data = zlib.compress(raw_data)
        idat = _png_chunk(b"IDAT", idat_data)
        iend = _png_chunk(b"IEND", b"")

        return signature + ihdr + idat + iend

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate_inputs(
        self,
        recipient_type: ProxyType,
        recipient_id: str,
        amount: Optional[float],
    ) -> None:
        """Validate QR generation inputs."""
        if not recipient_id:
            raise PayNowQRError("recipient_id is required")

        if recipient_type == ProxyType.MOBILE:
            # Must be +65XXXXXXXX format
            cleaned = recipient_id.replace(" ", "").replace("-", "")
            if not cleaned.startswith("+65") or len(cleaned) != 11:
                raise PayNowQRError(
                    f"Mobile number must be in +65XXXXXXXX format. Got: {recipient_id}"
                )

        elif recipient_type == ProxyType.UEN:
            # UEN: 8-10 characters (digits + optional letter suffix)
            if len(recipient_id) < 8 or len(recipient_id) > 10:
                raise PayNowQRError(f"UEN must be 8-10 characters. Got: {recipient_id}")

        if amount is not None:
            if amount <= 0:
                raise PayNowQRError(f"Amount must be positive. Got: {amount}")
            if amount > 200000:
                raise PayNowQRError(f"Amount exceeds PayNow limit ($200,000). Got: ${amount:.2f}")

    @staticmethod
    def _mask_id(recipient_id: str) -> str:
        """Mask recipient ID for logging (PII protection)."""
        if len(recipient_id) <= 4:
            return "****"
        return recipient_id[:3] + "*" * (len(recipient_id) - 5) + recipient_id[-2:]


# Module-level singleton
_adapter: Optional[PayNowAdapter] = None


def get_paynow_adapter() -> PayNowAdapter:
    """Get or create the PayNow adapter singleton."""
    global _adapter
    if _adapter is None:
        _adapter = PayNowAdapter()
    return _adapter
