"""Integration tests for the PayNow QR code adapter (SGQR/EMVCo).

Tests:
- QR data string generation for mobile number
- QR data string generation for UEN
- SGQR TLV format verification
- CRC-16/CCITT-FALSE checksum validation
- Amount encoding in QR payload
- Merchant name and reference fields
- Proxy type encoding (mobile=0, UEN=2)
- Validation errors (invalid mobile, missing amount, limit exceeded)
"""

from __future__ import annotations

import re

import pytest

from hr_advisory.mcp_servers.adapters.paynow import (
    COUNTRY_SG,
    CURRENCY_SGD,
    DEFAULT_CITY,
    PAYNOW_GUID,
    TAG_CRC,
    TAG_MERCHANT_ACCOUNT_PAYNOW,
    TAG_PAYLOAD_FORMAT,
    TAG_TRANSACTION_AMOUNT,
    TAG_TRANSACTION_CURRENCY,
    PayNowAdapter,
    PayNowQRError,
    ProxyType,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def adapter() -> PayNowAdapter:
    return PayNowAdapter()


# ---------------------------------------------------------------------------
# TLV Helpers
# ---------------------------------------------------------------------------


def _extract_tlv(qr_data: str, tag: str) -> str | None:
    """Extract the value for a given TLV tag from the QR data string.

    EMVCo TLV format: Tag(2) + Length(2) + Value(Length).
    """
    idx = 0
    while idx < len(qr_data) - 4:
        t = qr_data[idx : idx + 2]
        length = int(qr_data[idx + 2 : idx + 4])
        value = qr_data[idx + 4 : idx + 4 + length]
        if t == tag:
            return value
        idx += 4 + length
    return None


def _compute_crc16(data: str) -> str:
    """Compute CRC-16/CCITT-FALSE (polynomial 0x1021, init 0xFFFF)."""
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


# ---------------------------------------------------------------------------
# Mobile Number QR Tests
# ---------------------------------------------------------------------------


class TestMobileNumberQR:
    """QR generation for mobile number recipients."""

    def test_qr_data_is_nonempty_string(self, adapter):
        qr_data = adapter.generate_qr_data_only(
            recipient_type=ProxyType.MOBILE,
            recipient_id="+6591234567",
            amount=150.00,
        )
        assert isinstance(qr_data, str)
        assert len(qr_data) > 20

    def test_payload_format_indicator_is_01(self, adapter):
        qr_data = adapter.generate_qr_data_only(
            recipient_type=ProxyType.MOBILE,
            recipient_id="+6591234567",
            amount=150.00,
        )
        pfi = _extract_tlv(qr_data, TAG_PAYLOAD_FORMAT)
        assert pfi == "01"

    def test_paynow_block_contains_guid(self, adapter):
        qr_data = adapter.generate_qr_data_only(
            recipient_type=ProxyType.MOBILE,
            recipient_id="+6591234567",
            amount=150.00,
        )
        paynow_block = _extract_tlv(qr_data, TAG_MERCHANT_ACCOUNT_PAYNOW)
        assert paynow_block is not None
        # GUID is sub-tag 00 within the PayNow block
        assert PAYNOW_GUID in paynow_block

    def test_proxy_type_is_zero_for_mobile(self, adapter):
        qr_data = adapter.generate_qr_data_only(
            recipient_type=ProxyType.MOBILE,
            recipient_id="+6591234567",
            amount=150.00,
        )
        paynow_block = _extract_tlv(qr_data, TAG_MERCHANT_ACCOUNT_PAYNOW)
        # Parse sub-tags to find proxy type (tag 01)
        proxy_type = _extract_tlv(paynow_block, "01")
        assert proxy_type == "0"

    def test_mobile_number_in_payload(self, adapter):
        qr_data = adapter.generate_qr_data_only(
            recipient_type=ProxyType.MOBILE,
            recipient_id="+6591234567",
            amount=150.00,
        )
        assert "+6591234567" in qr_data

    def test_amount_encoded_correctly(self, adapter):
        qr_data = adapter.generate_qr_data_only(
            recipient_type=ProxyType.MOBILE,
            recipient_id="+6591234567",
            amount=150.00,
        )
        amount_val = _extract_tlv(qr_data, TAG_TRANSACTION_AMOUNT)
        assert amount_val == "150.00"

    def test_currency_is_702_sgd(self, adapter):
        qr_data = adapter.generate_qr_data_only(
            recipient_type=ProxyType.MOBILE,
            recipient_id="+6591234567",
            amount=150.00,
        )
        currency = _extract_tlv(qr_data, TAG_TRANSACTION_CURRENCY)
        assert currency == CURRENCY_SGD

    def test_qr_returns_png_bytes(self, adapter):
        qr_data, png_bytes = adapter.generate_qr(
            recipient_type=ProxyType.MOBILE,
            recipient_id="+6591234567",
            amount=150.00,
        )
        assert isinstance(png_bytes, bytes)
        assert len(png_bytes) > 0
        # PNG magic bytes
        assert png_bytes[:4] == b"\x89PNG"


# ---------------------------------------------------------------------------
# UEN QR Tests
# ---------------------------------------------------------------------------


class TestUENQR:
    """QR generation for UEN (company) recipients."""

    def test_proxy_type_is_two_for_uen(self, adapter):
        qr_data = adapter.generate_qr_data_only(
            recipient_type=ProxyType.UEN,
            recipient_id="201234567K",
            amount=5000.00,
        )
        paynow_block = _extract_tlv(qr_data, TAG_MERCHANT_ACCOUNT_PAYNOW)
        # Parse sub-tags to find proxy type (tag 01)
        proxy_type = _extract_tlv(paynow_block, "01")
        assert proxy_type == "2"

    def test_uen_in_payload(self, adapter):
        qr_data = adapter.generate_qr_data_only(
            recipient_type=ProxyType.UEN,
            recipient_id="201234567K",
            amount=5000.00,
        )
        assert "201234567K" in qr_data

    def test_uen_amount_encoded(self, adapter):
        qr_data = adapter.generate_qr_data_only(
            recipient_type=ProxyType.UEN,
            recipient_id="201234567K",
            amount=5000.00,
        )
        amount_val = _extract_tlv(qr_data, TAG_TRANSACTION_AMOUNT)
        assert amount_val == "5000.00"


# ---------------------------------------------------------------------------
# CRC-16 Checksum
# ---------------------------------------------------------------------------


class TestCRCChecksum:
    """CRC-16/CCITT-FALSE checksum verification."""

    def test_crc_present_at_end(self, adapter):
        qr_data = adapter.generate_qr_data_only(
            recipient_type=ProxyType.MOBILE,
            recipient_id="+6591234567",
            amount=100.00,
        )
        # CRC tag "63" should be at the end with 4-char hex value
        assert qr_data[-8:-4] == "6304"

    def test_crc_is_valid(self, adapter):
        qr_data = adapter.generate_qr_data_only(
            recipient_type=ProxyType.MOBILE,
            recipient_id="+6591234567",
            amount=100.00,
        )
        # CRC is the last 4 hex characters
        payload_without_crc_value = qr_data[:-4]
        expected_crc = _compute_crc16(payload_without_crc_value)
        actual_crc = qr_data[-4:]
        assert actual_crc == expected_crc

    def test_crc_changes_with_different_amount(self, adapter):
        qr1 = adapter.generate_qr_data_only(
            recipient_type=ProxyType.MOBILE,
            recipient_id="+6591234567",
            amount=100.00,
        )
        qr2 = adapter.generate_qr_data_only(
            recipient_type=ProxyType.MOBILE,
            recipient_id="+6591234567",
            amount=200.00,
        )
        crc1 = qr1[-4:]
        crc2 = qr2[-4:]
        assert crc1 != crc2


# ---------------------------------------------------------------------------
# Merchant Name and Reference
# ---------------------------------------------------------------------------


class TestMerchantAndReference:
    """Verify merchant name and reference encoding."""

    def test_default_merchant_name(self, adapter):
        qr_data = adapter.generate_qr_data_only(
            recipient_type=ProxyType.MOBILE,
            recipient_id="+6591234567",
            amount=100.00,
        )
        # Tag 59 = merchant name; default is "PAYNOW"
        assert "PAYNOW" in qr_data

    def test_custom_merchant_name(self, adapter):
        qr_data = adapter.generate_qr_data_only(
            recipient_type=ProxyType.MOBILE,
            recipient_id="+6591234567",
            amount=100.00,
            merchant_name="ACME PTE LTD",
        )
        assert "ACME PTE LTD" in qr_data

    def test_reference_in_additional_data(self, adapter):
        qr_data = adapter.generate_qr_data_only(
            recipient_type=ProxyType.MOBILE,
            recipient_id="+6591234567",
            amount=100.00,
            reference="CLAIM-2026-001",
        )
        assert "CLAIM-2026-001" in qr_data

    def test_country_code_is_sg(self, adapter):
        qr_data = adapter.generate_qr_data_only(
            recipient_type=ProxyType.MOBILE,
            recipient_id="+6591234567",
            amount=100.00,
        )
        # Tag 58 = country code
        assert "5802SG" in qr_data

    def test_city_is_singapore(self, adapter):
        qr_data = adapter.generate_qr_data_only(
            recipient_type=ProxyType.MOBILE,
            recipient_id="+6591234567",
            amount=100.00,
        )
        assert DEFAULT_CITY in qr_data


# ---------------------------------------------------------------------------
# Point of Initiation
# ---------------------------------------------------------------------------


class TestPointOfInitiation:
    """POI method: 11=static (reusable), 12=dynamic (one-time)."""

    def test_dynamic_when_amount_specified(self, adapter):
        qr_data = adapter.generate_qr_data_only(
            recipient_type=ProxyType.MOBILE,
            recipient_id="+6591234567",
            amount=100.00,
        )
        # Tag 01 = POI method, value "12" = dynamic
        assert "010212" in qr_data

    def test_static_when_no_amount(self, adapter):
        qr_data = adapter.generate_qr_data_only(
            recipient_type=ProxyType.MOBILE,
            recipient_id="+6591234567",
        )
        # Tag 01 = POI method, value "11" = static
        assert "010211" in qr_data

    def test_no_amount_tag_when_amount_is_none(self, adapter):
        qr_data = adapter.generate_qr_data_only(
            recipient_type=ProxyType.MOBILE,
            recipient_id="+6591234567",
        )
        amount_val = _extract_tlv(qr_data, TAG_TRANSACTION_AMOUNT)
        assert amount_val is None


# ---------------------------------------------------------------------------
# Validation Errors
# ---------------------------------------------------------------------------


class TestPayNowValidation:
    """Verify validation errors for invalid inputs."""

    def test_empty_recipient_id_raises(self, adapter):
        with pytest.raises(PayNowQRError, match="recipient_id is required"):
            adapter.generate_qr_data_only(
                recipient_type=ProxyType.MOBILE,
                recipient_id="",
            )

    def test_invalid_mobile_format_raises(self, adapter):
        with pytest.raises(PayNowQRError, match="Mobile number must be in"):
            adapter.generate_qr_data_only(
                recipient_type=ProxyType.MOBILE,
                recipient_id="91234567",  # Missing +65 prefix
            )

    def test_short_mobile_raises(self, adapter):
        with pytest.raises(PayNowQRError, match="Mobile number must be in"):
            adapter.generate_qr_data_only(
                recipient_type=ProxyType.MOBILE,
                recipient_id="+659123",  # Too short
            )

    def test_uen_too_short_raises(self, adapter):
        with pytest.raises(PayNowQRError, match="UEN must be 8-10 characters"):
            adapter.generate_qr_data_only(
                recipient_type=ProxyType.UEN,
                recipient_id="1234567",  # 7 chars, needs at least 8
            )

    def test_uen_too_long_raises(self, adapter):
        with pytest.raises(PayNowQRError, match="UEN must be 8-10 characters"):
            adapter.generate_qr_data_only(
                recipient_type=ProxyType.UEN,
                recipient_id="12345678901",  # 11 chars, max 10
            )

    def test_negative_amount_raises(self, adapter):
        with pytest.raises(PayNowQRError, match="Amount must be positive"):
            adapter.generate_qr_data_only(
                recipient_type=ProxyType.MOBILE,
                recipient_id="+6591234567",
                amount=-50.00,
            )

    def test_zero_amount_raises(self, adapter):
        with pytest.raises(PayNowQRError, match="Amount must be positive"):
            adapter.generate_qr_data_only(
                recipient_type=ProxyType.MOBILE,
                recipient_id="+6591234567",
                amount=0,
            )

    def test_amount_over_limit_raises(self, adapter):
        with pytest.raises(PayNowQRError, match="exceeds PayNow limit"):
            adapter.generate_qr_data_only(
                recipient_type=ProxyType.MOBILE,
                recipient_id="+6591234567",
                amount=200001.00,
            )

    def test_amount_at_limit_is_accepted(self, adapter):
        # $200,000 is the limit -- should NOT raise
        qr_data = adapter.generate_qr_data_only(
            recipient_type=ProxyType.MOBILE,
            recipient_id="+6591234567",
            amount=200000.00,
        )
        assert isinstance(qr_data, str)


# ---------------------------------------------------------------------------
# Editable Flag and Expiry
# ---------------------------------------------------------------------------


class TestEditableAndExpiry:
    """Verify editable flag and expiry encoding in PayNow sub-block."""

    def test_not_editable_by_default(self, adapter):
        qr_data = adapter.generate_qr_data_only(
            recipient_type=ProxyType.MOBILE,
            recipient_id="+6591234567",
            amount=100.00,
        )
        paynow_block = _extract_tlv(qr_data, TAG_MERCHANT_ACCOUNT_PAYNOW)
        # Parse sub-tag 03 (editable flag)
        editable_flag = _extract_tlv(paynow_block, "03")
        assert editable_flag == "0"

    def test_editable_when_flag_set(self, adapter):
        qr_data = adapter.generate_qr_data_only(
            recipient_type=ProxyType.MOBILE,
            recipient_id="+6591234567",
            amount=100.00,
            editable=True,
        )
        paynow_block = _extract_tlv(qr_data, TAG_MERCHANT_ACCOUNT_PAYNOW)
        # Parse sub-tag 03 (editable flag)
        editable_flag = _extract_tlv(paynow_block, "03")
        assert editable_flag == "1"

    def test_expiry_date_encoded(self, adapter):
        qr_data = adapter.generate_qr_data_only(
            recipient_type=ProxyType.MOBILE,
            recipient_id="+6591234567",
            amount=100.00,
            expiry_date="20260401",
        )
        assert "20260401" in qr_data
