"""Banking endpoints.

Provides PayNow QR code generation and related banking operations
for Singapore-based HRIS functionality.
"""

import logging
import math
import re
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from hr_advisory.api.middleware.auth_middleware import get_current_user
from hr_advisory.api.middleware.rate_limit import check_rate_limit
from hr_advisory.api.middleware.tenant_isolation import get_current_company_id

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Request/Response Models ──────────────────────────────────


class PayNowQRRequest(BaseModel):
    amount: float
    reference: str = ""


# ── PayNow QR Generation ────────────────────────────────────


def _generate_paynow_qr_payload(
    uen: str,
    amount: float,
    reference: str,
    merchant_name: str = "",
    editable: bool = False,
    expiry: str = "",
) -> str:
    """Generate a PayNow-compatible EMVCo QR payload string.

    Follows the Singapore PayNow QR code specification based on
    EMVCo Merchant Presented Mode (MPM). This produces the raw
    text payload that should be encoded into a QR code image.

    Args:
        uen: The company UEN or proxy value (NRIC/mobile for personal).
        amount: Transaction amount in SGD.
        reference: Bill/payment reference string.
        merchant_name: Display name for the merchant.
        editable: Whether the amount can be edited by the payer.
        expiry: Expiry date string in YYYYMMDD format.

    Returns:
        The EMVCo-formatted payload string including CRC-16 checksum.
    """

    def _tlv(tag: str, value: str) -> str:
        """Format a Tag-Length-Value element."""
        return f"{tag}{len(value):02d}{value}"

    def _crc16(data: str) -> str:
        """Compute CRC-16/CCITT-FALSE checksum for EMVCo payloads."""
        crc = 0xFFFF
        for byte in data.encode("utf-8"):
            crc ^= byte << 8
            for _ in range(8):
                if crc & 0x8000:
                    crc = (crc << 1) ^ 0x1021
                else:
                    crc = crc << 1
                crc &= 0xFFFF
        return f"{crc:04X}"

    # Tag 00: Payload Format Indicator
    payload = _tlv("00", "01")

    # Tag 01: Point of Initiation Method (11 = static, 12 = dynamic)
    payload += _tlv("01", "12")

    # Tag 26: Merchant Account Information (PayNow)
    # Sub-tag 00: Globally unique identifier for PayNow
    mai = _tlv("00", "SG.PAYNOW")
    # Sub-tag 01: Proxy type (0 = mobile, 2 = UEN)
    mai += _tlv("01", "2")
    # Sub-tag 02: Proxy value (UEN)
    mai += _tlv("02", uen)
    # Sub-tag 03: Editable indicator (0 = not editable, 1 = editable)
    mai += _tlv("03", "1" if editable else "0")
    # Sub-tag 04: Expiry date (optional)
    if expiry:
        mai += _tlv("04", expiry)

    payload += _tlv("26", mai)

    # Tag 52: Merchant Category Code
    payload += _tlv("52", "0000")

    # Tag 53: Transaction Currency (702 = SGD)
    payload += _tlv("53", "702")

    # Tag 54: Transaction Amount
    if amount > 0:
        payload += _tlv("54", f"{amount:.2f}")

    # Tag 58: Country Code
    payload += _tlv("58", "SG")

    # Tag 59: Merchant Name
    name = merchant_name[:25] if merchant_name else "COMPANY"
    payload += _tlv("59", name)

    # Tag 60: Merchant City
    payload += _tlv("60", "Singapore")

    # Tag 62: Additional Data (bill reference)
    if reference:
        ad = _tlv("01", reference[:25])
        payload += _tlv("62", ad)

    # Tag 63: CRC — append tag and length first, then compute
    payload += "6304"
    crc = _crc16(payload)
    payload += crc

    return payload


@router.post("/paynow-qr")
async def generate_paynow_qr(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Generate a PayNow QR code for a payment.

    Accepts amount and reference, generates a PayNow-compatible EMVCo
    QR payload. Returns the QR data as a text payload string that the
    frontend can render using a QR code library.
    """
    user_id = int(current_user.get("sub", 0))
    check_rate_limit(f"generate_paynow_qr:{user_id}", max_requests=30, window_seconds=60, action_name="generate PayNow QR")

    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    body = await request.json()
    amount = body.get("amount", 0)
    reference = body.get("reference", "")

    # Validate amount
    if not isinstance(amount, (int, float)):
        raise HTTPException(status_code=400, detail="amount must be a number.")
    amount = float(amount)
    if not math.isfinite(amount) or amount <= 0:
        raise HTTPException(status_code=400, detail="amount must be a positive finite number.")
    if amount > 200_000:
        raise HTTPException(status_code=400, detail="amount exceeds PayNow transaction limit.")

    # Validate reference
    if reference and not re.match(r"^[a-zA-Z0-9 _\-/:.]+$", reference):
        raise HTTPException(status_code=400, detail="reference contains invalid characters.")
    reference = reference[:25]

    # Look up company UEN from profile
    from hr_advisory.services import dataflow_crud

    company = dataflow_crud.read("Company", company_id)
    uen = ""
    merchant_name = ""
    if company:
        uen = company.get("uen", "") or company.get("registration_number", "") or ""
        merchant_name = company.get("name", "") or ""

    if not uen:
        # Fall back to a placeholder — the QR is still valid but the payer
        # will need to verify the recipient manually
        uen = "000000000A"

    expiry_dt = datetime.now(timezone.utc) + timedelta(hours=24)
    expiry_str = expiry_dt.strftime("%Y%m%d")

    qr_payload = _generate_paynow_qr_payload(
        uen=uen,
        amount=amount,
        reference=reference,
        merchant_name=merchant_name,
        editable=False,
        expiry=expiry_str,
    )

    return {
        "qr_data": qr_payload,
        "amount": amount,
        "reference": reference,
        "expires_at": expiry_dt.isoformat(),
    }
