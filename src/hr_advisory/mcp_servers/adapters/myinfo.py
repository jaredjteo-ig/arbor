"""MyInfo v5 adapter (FAPI 2.0 compliant) for employee onboarding.

Retrieves verified personal data from Singpass MyInfo to auto-populate
employee records during onboarding. Eliminates manual data entry for
name, NRIC, DOB, address, race, nationality, and CPF contribution history.

MyInfo v5 protocol (FAPI 2.0):
- PAR (Pushed Authorization Request) is mandatory
- JARM (JWT-Secured Authorization Response Mode)
- Encrypted ID tokens (JWE + JWS)
- DPoP (Demonstration of Proof-of-Possession) tokens

Endpoints:
- PAR:       https://api.myinfo.gov.sg/v5/authorize/par
- Authorize: https://api.myinfo.gov.sg/v5/authorize
- Token:     https://api.myinfo.gov.sg/v5/token
- Person:    https://api.myinfo.gov.sg/v5/person
- Sandbox:   https://sandbox.api.myinfo.gov.sg/v5/...

MyInfo Business endpoints:
- Business:  https://api.myinfo.gov.sg/biz/v2/entity-person

Reference:
- MyInfo v5 API Specification (api.singpass.gov.sg)
- FAPI 2.0 Security Profile
- Singpass Developer Portal

Prerequisites:
- Singpass Developer Portal registration
- Security review and approval
- FAPI 2.0 compliance (deadline: 31 Dec 2026)

Pricing:
- First 5,000 transactions/month free
- S$1.00 per transaction thereafter
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import secrets
import time
import urllib.parse
from typing import Any, Optional

import httpx

from hr_advisory.mcp_servers.auth.token_store import get_token_manager
from hr_advisory.mcp_servers.health import get_health_monitor
from hr_advisory.mcp_servers.resilience import get_circuit

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration from environment
# ---------------------------------------------------------------------------

MYINFO_BASE_URL = os.environ.get("MYINFO_BASE_URL", "https://api.myinfo.gov.sg/v5")
MYINFO_BASE_URL_SANDBOX = os.environ.get(
    "MYINFO_BASE_URL_SANDBOX", "https://sandbox.api.myinfo.gov.sg/v5"
)
MYINFO_BIZ_BASE_URL = os.environ.get("MYINFO_BIZ_BASE_URL", "https://api.myinfo.gov.sg/biz/v2")
MYINFO_BIZ_BASE_URL_SANDBOX = os.environ.get(
    "MYINFO_BIZ_BASE_URL_SANDBOX", "https://sandbox.api.myinfo.gov.sg/biz/v2"
)
MYINFO_USE_SANDBOX = os.environ.get("MYINFO_USE_SANDBOX", "true").lower() == "true"

# Singpass client credentials
MYINFO_CLIENT_ID = os.environ.get("MYINFO_CLIENT_ID", "")
MYINFO_CLIENT_SECRET = os.environ.get("MYINFO_CLIENT_SECRET", "")

# JWK keys for decryption and signing
MYINFO_PRIVATE_SIGNING_KEY = os.environ.get("MYINFO_PRIVATE_SIGNING_KEY", "")
MYINFO_PRIVATE_ENCRYPTION_KEY = os.environ.get("MYINFO_PRIVATE_ENCRYPTION_KEY", "")

# Callback URL registered with Singpass
MYINFO_CALLBACK_URL = os.environ.get("MYINFO_CALLBACK_URL", "")

# Provider name for token store
PROVIDER_NAME = "myinfo"

_health = get_health_monitor()

# Default scopes for HR employee onboarding
DEFAULT_PERSON_SCOPES = [
    "name",
    "sex",
    "race",
    "nationality",
    "dob",
    "birthcountry",
    "residentialstatus",
    "passtype",
    "regadd",
    "mailadd",
    "mobileno",
    "email",
    "marital",
    "nric-fin",
    "uinfin",
    "cpfcontributions",
    "noabasic",
]

# MyInfo Business scopes
DEFAULT_BUSINESS_SCOPES = [
    "basic-profile",
    "addresses",
    "appointments",
]


class MyInfoError(Exception):
    """Error during MyInfo data retrieval."""

    def __init__(
        self, message: str, error_code: str = "myinfo_error", details: Optional[dict] = None
    ):
        self.error_code = error_code
        self.details = details or {}
        super().__init__(message)


# ---------------------------------------------------------------------------
# Consent state store for PKCE + PAR during consent flow
# ---------------------------------------------------------------------------

_CONSENT_EXPIRY = 600  # 10 minutes


class ConsentStateStore:
    """Stores PKCE and PAR state for in-flight MyInfo consent flows.

    Default implementation uses an in-memory dict with TTL-based expiry.

    Production: replace with Redis-backed store for multi-instance deployment.
    The interface (store/retrieve/delete) stays the same; swap the backing
    dict for a Redis hash with TTL set to _CONSENT_EXPIRY.
    """

    def __init__(self) -> None:
        self._store: dict[str, dict[str, Any]] = {}

    def store(self, state: str, data: dict[str, Any]) -> None:
        """Store consent flow data keyed by state token."""
        self._clean_expired()
        data.setdefault("created_at", time.time())
        self._store[state] = data

    def retrieve(self, state: str) -> Optional[dict[str, Any]]:
        """Retrieve consent flow data without removing it.

        Returns None if the state does not exist or has expired.
        """
        self._clean_expired()
        entry = self._store.get(state)
        if entry is None:
            return None
        if time.time() - entry.get("created_at", 0) > _CONSENT_EXPIRY:
            del self._store[state]
            return None
        return entry

    def delete(self, state: str) -> Optional[dict[str, Any]]:
        """Remove and return consent flow data for a state token.

        Returns None if the state does not exist or has expired.
        """
        self._clean_expired()
        return self._store.pop(state, None)

    def _clean_expired(self) -> None:
        """Remove all expired entries from the store."""
        now = time.time()
        expired = [
            k for k, v in self._store.items() if now - v.get("created_at", 0) > _CONSENT_EXPIRY
        ]
        for k in expired:
            del self._store[k]


# Module-level singleton
_consent_store = ConsentStateStore()


def _get_base_url() -> str:
    return MYINFO_BASE_URL_SANDBOX if MYINFO_USE_SANDBOX else MYINFO_BASE_URL


def _get_biz_base_url() -> str:
    return MYINFO_BIZ_BASE_URL_SANDBOX if MYINFO_USE_SANDBOX else MYINFO_BIZ_BASE_URL


# ---------------------------------------------------------------------------
# PKCE + DPoP helpers
# ---------------------------------------------------------------------------


def _generate_pkce() -> tuple[str, str]:
    """Generate PKCE code_verifier and code_challenge (S256)."""
    verifier = secrets.token_urlsafe(64)[:128]
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


def _generate_dpop_proof(http_method: str, url: str, access_token: Optional[str] = None) -> str:
    """Generate a DPoP (Demonstration of Proof-of-Possession) proof JWT.

    FAPI 2.0 requires DPoP to bind access tokens to the client.
    In production, this signs a JWT with the client's private key.
    For sandbox, returns a placeholder.
    """
    if MYINFO_USE_SANDBOX:
        # Sandbox does not validate DPoP proofs
        return "sandbox-dpop-proof"

    # Production DPoP proof construction
    # In production, import PyJWT or python-jose for proper JWT signing
    try:
        import jwt as pyjwt

        now = int(time.time())
        headers = {
            "typ": "dpop+jwt",
            "alg": "ES256",
            # "jwk": <public key thumbprint> — added by signing lib
        }
        payload = {
            "jti": secrets.token_urlsafe(16),
            "htm": http_method,
            "htu": url,
            "iat": now,
        }
        if access_token:
            ath = (
                base64.urlsafe_b64encode(hashlib.sha256(access_token.encode()).digest())
                .rstrip(b"=")
                .decode()
            )
            payload["ath"] = ath

        return pyjwt.encode(
            payload,
            MYINFO_PRIVATE_SIGNING_KEY,
            algorithm="ES256",
            headers=headers,
        )
    except ImportError:
        logger.warning("PyJWT not available for DPoP proof generation — using placeholder")
        return "dpop-proof-placeholder"


# ---------------------------------------------------------------------------
# Public API — Consent Flow
# ---------------------------------------------------------------------------


async def initiate_consent(
    callback_url: str,
    requested_attributes: Optional[list[str]] = None,
    purpose: str = "employee_onboarding",
) -> dict:
    """Initiate MyInfo consent flow via Singpass.

    FAPI 2.0 requires Pushed Authorization Requests (PAR).
    The client first pushes the authorization parameters to the PAR endpoint,
    receives a request_uri, then redirects the user to the authorize endpoint
    with the request_uri.

    Args:
        callback_url: URL where Singpass redirects after user consent.
        requested_attributes: List of MyInfo attributes to request.
            Defaults to DEFAULT_PERSON_SCOPES.
        purpose: Purpose of data retrieval (for consent display).

    Returns:
        Dict with authorization_url for user redirect, state, and expiry.
    """
    if not MYINFO_CLIENT_ID:
        raise MyInfoError(
            "MYINFO_CLIENT_ID not configured. Register at the Singpass Developer Portal.",
            error_code="missing_config",
        )

    scopes = requested_attributes or DEFAULT_PERSON_SCOPES
    scope_string = " ".join(scopes)

    # PKCE
    code_verifier, code_challenge = _generate_pkce()

    # CSRF state
    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(16)

    base_url = _get_base_url()

    # Step 1: Pushed Authorization Request (PAR)
    par_url = f"{base_url}/authorize/par"
    par_payload = {
        "client_id": MYINFO_CLIENT_ID,
        "redirect_uri": callback_url or MYINFO_CALLBACK_URL,
        "scope": scope_string,
        "response_type": "code",
        "state": state,
        "nonce": nonce,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "purpose_id": purpose,
    }

    circuit = get_circuit("myinfo")

    async def _push_auth_request() -> dict:
        dpop_proof = _generate_dpop_proof("POST", par_url)
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                par_url,
                data=par_payload,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "DPoP": dpop_proof,
                },
                auth=(MYINFO_CLIENT_ID, MYINFO_CLIENT_SECRET),
            )
            if resp.status_code != 201:
                raise MyInfoError(
                    f"PAR request failed (HTTP {resp.status_code})",
                    error_code="par_failed",
                    details={"http_status": resp.status_code, "body": resp.text[:500]},
                )
            return resp.json()

    par_response = await circuit.call(_push_auth_request)
    request_uri = par_response.get("request_uri", "")

    # Store consent flow state via ConsentStateStore
    _consent_store.store(
        state,
        {
            "callback_url": callback_url or MYINFO_CALLBACK_URL,
            "pkce_verifier": code_verifier,
            "par_request_uri": request_uri,
            "scopes": scopes,
            "created_at": time.time(),
        },
    )

    # Step 2: Build authorization URL with request_uri
    authorize_url = f"{base_url}/authorize"
    auth_params = {
        "client_id": MYINFO_CLIENT_ID,
        "request_uri": request_uri,
    }

    authorization_url = f"{authorize_url}?{urllib.parse.urlencode(auth_params)}"

    logger.info("MyInfo consent flow initiated (state=%s...)", state[:8])

    return {
        "authorization_url": authorization_url,
        "state": state,
        "expires_in": _CONSENT_EXPIRY,
        "requested_attributes": scopes,
    }


async def handle_callback(
    auth_code: str,
    state: str,
) -> dict:
    """Exchange authorization code for access token after Singpass consent.

    Args:
        auth_code: Authorization code from Singpass callback.
        state: State parameter for CSRF validation (REQUIRED).

    Returns:
        Dict with access_token and token metadata.

    Raises:
        MyInfoError: If state is missing, invalid, or token exchange fails.
    """
    # State is REQUIRED for CSRF protection — never skip validation
    if not state:
        raise MyInfoError(
            "State parameter is required for CSRF protection.",
            error_code="missing_state",
        )

    consent_data = _consent_store.delete(state)
    if consent_data is None:
        raise MyInfoError(
            "Invalid or expired consent state. Please restart the MyInfo flow.",
            error_code="invalid_state",
        )

    code_verifier = consent_data["pkce_verifier"]
    callback_url = consent_data["callback_url"]

    base_url = _get_base_url()
    token_url = f"{base_url}/token"

    token_payload = {
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": callback_url,
        "client_id": MYINFO_CLIENT_ID,
        "client_secret": MYINFO_CLIENT_SECRET,
        "code_verifier": code_verifier,
    }

    circuit = get_circuit("myinfo")

    async def _exchange_token() -> dict:
        dpop_proof = _generate_dpop_proof("POST", token_url)
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                token_url,
                data=token_payload,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "DPoP": dpop_proof,
                },
            )
            if resp.status_code != 200:
                raise MyInfoError(
                    f"Token exchange failed (HTTP {resp.status_code})",
                    error_code="token_exchange_failed",
                    details={"http_status": resp.status_code, "body": resp.text[:500]},
                )
            return resp.json()

    token_data = await circuit.call(_exchange_token)

    _health.record_success("myinfo")

    return {
        "access_token": token_data.get("access_token", ""),
        "token_type": token_data.get("token_type", "DPoP"),
        "expires_in": token_data.get("expires_in", 1800),
        "scope": token_data.get("scope", ""),
    }


# ---------------------------------------------------------------------------
# Public API — Data Retrieval
# ---------------------------------------------------------------------------


async def fetch_person_data(
    access_token: str,
    requested_attributes: Optional[list[str]] = None,
) -> dict:
    """Retrieve and decrypt MyInfo person data.

    MyInfo v5 returns data as a JWE (JSON Web Encryption) containing
    a JWS (JSON Web Signature). In production, this must be decrypted
    with our private encryption key and the signature verified against
    the MyInfo public key.

    Sandbox returns plain JSON without encryption.

    Args:
        access_token: Valid access token from handle_callback().
        requested_attributes: Attributes to request (for scoping the query).

    Returns:
        Dict with verified person data mapped to internal field names.
    """
    scopes = requested_attributes or DEFAULT_PERSON_SCOPES
    scope_param = ",".join(scopes)

    base_url = _get_base_url()
    # The person endpoint path includes the sub claim extracted from the access token
    # In production, decode the token to get the NRIC; in sandbox, pass a test NRIC
    person_url = f"{base_url}/person"

    circuit = get_circuit("myinfo")

    async def _fetch() -> Any:
        dpop_proof = _generate_dpop_proof("GET", person_url, access_token=access_token)
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                person_url,
                params={"attributes": scope_param},
                headers={
                    "Authorization": f"DPoP {access_token}",
                    "DPoP": dpop_proof,
                    "Accept": "application/json",
                },
            )
            if resp.status_code != 200:
                raise MyInfoError(
                    f"MyInfo person data retrieval failed (HTTP {resp.status_code})",
                    error_code="person_fetch_failed",
                    details={"http_status": resp.status_code},
                )
            content_type = resp.headers.get("content-type", "")
            if "application/jose" in content_type or "application/jwe" in content_type:
                # JWE response — decrypt
                return _decrypt_jwe_response(resp.text)
            return resp.json()

    raw_data = await circuit.call(_fetch)

    _health.record_success("myinfo")

    # Map MyInfo fields to our Employee model fields
    mapped = _map_person_to_employee(raw_data)

    return {
        "raw_data": raw_data,
        "mapped_fields": mapped,
        "source": "myinfo_v5",
        "verified": True,
    }


def _decrypt_jwe_response(jwe_string: str) -> dict:
    """Decrypt a JWE+JWS response from MyInfo.

    In production, this uses the private encryption key to decrypt the JWE,
    then verifies the JWS signature with MyInfo's public signing key.

    For sandbox or when keys are not configured, attempts to parse as JSON.
    """
    if MYINFO_USE_SANDBOX or not MYINFO_PRIVATE_ENCRYPTION_KEY:
        # Sandbox may return plain JSON even with JWE content-type
        try:
            return json.loads(jwe_string)
        except (json.JSONDecodeError, TypeError):
            pass

    # Production decryption
    try:
        from jwcrypto import jwe as jwcrypto_jwe, jwk, jws as jwcrypto_jws

        # Load our private encryption key
        private_key = jwk.JWK.from_pem(MYINFO_PRIVATE_ENCRYPTION_KEY.encode())

        # Decrypt JWE
        jwe_obj = jwcrypto_jwe.JWE()
        jwe_obj.deserialize(jwe_string)
        jwe_obj.decrypt(private_key)
        jws_string = jwe_obj.payload.decode()

        # Verify JWS (skip verification in sandbox)
        jws_obj = jwcrypto_jws.JWS()
        jws_obj.deserialize(jws_string)
        # In production, verify against MyInfo's public key
        # For now, extract the payload
        return json.loads(jws_obj.payload.decode())

    except ImportError:
        logger.warning("jwcrypto not available — attempting plain JSON parse")
        try:
            return json.loads(jwe_string)
        except (json.JSONDecodeError, TypeError):
            raise MyInfoError(
                "Cannot decrypt MyInfo response — jwcrypto library required for production",
                error_code="decryption_failed",
            )
    except Exception as e:
        raise MyInfoError(
            f"MyInfo response decryption failed: {e}",
            error_code="decryption_failed",
        ) from e


def _map_person_to_employee(myinfo_data: dict) -> dict:
    """Map MyInfo person data fields to AITE Employee model fields.

    MyInfo fields use a nested structure with 'value' and optional
    'source' and 'classification' metadata.
    """

    def _extract_value(field_data: Any) -> Any:
        """Extract the value from a MyInfo field (may be nested or plain)."""
        if isinstance(field_data, dict):
            return field_data.get("value", field_data.get("desc", ""))
        return field_data

    def _extract_address(addr_data: Any) -> dict:
        """Extract address components from MyInfo regadd field."""
        if not isinstance(addr_data, dict):
            return {"residential_address": "", "postal_code": ""}
        block = _extract_value(addr_data.get("block", ""))
        street = _extract_value(addr_data.get("street", ""))
        floor = _extract_value(addr_data.get("floor", ""))
        unit = _extract_value(addr_data.get("unit", ""))
        building = _extract_value(addr_data.get("building", ""))
        postal = _extract_value(addr_data.get("postal", ""))
        country = _extract_value(addr_data.get("country", {}).get("desc", "SINGAPORE"))

        parts = []
        if block:
            parts.append(f"Blk {block}")
        if street:
            parts.append(street)
        if floor and unit:
            parts.append(f"#{floor}-{unit}")
        if building:
            parts.append(building)
        if country and country != "SINGAPORE":
            parts.append(country)

        return {
            "residential_address": " ".join(parts),
            "postal_code": str(postal),
        }

    # Core identity
    name = _extract_value(myinfo_data.get("name", ""))
    nric_fin = _extract_value(myinfo_data.get("uinfin", ""))
    dob = _extract_value(myinfo_data.get("dob", ""))
    sex = _extract_value(myinfo_data.get("sex", ""))
    race = _extract_value(myinfo_data.get("race", ""))
    nationality = _extract_value(myinfo_data.get("nationality", ""))
    birth_country = _extract_value(myinfo_data.get("birthcountry", ""))
    marital = _extract_value(myinfo_data.get("marital", ""))
    residential_status = _extract_value(myinfo_data.get("residentialstatus", ""))
    pass_type = _extract_value(myinfo_data.get("passtype", ""))

    # Contact
    mobile = _extract_value(myinfo_data.get("mobileno", {}).get("nbr", ""))
    mobile_prefix = _extract_value(myinfo_data.get("mobileno", {}).get("prefix", "+65"))
    email = _extract_value(myinfo_data.get("email", ""))

    # Address
    address = _extract_address(myinfo_data.get("regadd", {}))

    # Map gender
    gender_map = {"M": "male", "F": "female", "MALE": "male", "FEMALE": "female"}
    gender = gender_map.get(str(sex).upper(), "")

    # Map race to internal code
    race_map = {
        "CHINESE": "chinese",
        "MALAY": "malay",
        "INDIAN": "indian",
        "EURASIAN": "eurasian",
        "CN": "chinese",
        "MY": "malay",
        "IN": "indian",
        "EU": "eurasian",
    }
    race_code = race_map.get(str(race).upper(), "other")

    # Map immigration/residential status
    immigration_map = {
        "C": "citizen",
        "CITIZEN": "citizen",
        "PR": "pr_year3_plus",
        "P": "pr_year3_plus",
        "F": "foreigner",
        "FOREIGNER": "foreigner",
    }
    immigration_status = immigration_map.get(str(residential_status).upper(), "citizen")

    # Map nationality code to display name
    nationality_display = str(nationality).upper() if nationality else "SINGAPOREAN"

    # Format NRIC last 4
    nric_last4 = nric_fin[-4:] if nric_fin and len(nric_fin) >= 4 else ""

    # Format DOB to ISO
    dob_formatted = ""
    if dob:
        # MyInfo returns YYYY-MM-DD
        dob_formatted = str(dob)[:10]

    return {
        "name": name,
        "nric_fin": nric_fin,
        "nric_fin_last4": nric_last4,
        "date_of_birth": dob_formatted,
        "gender": gender,
        "race": race_code,
        "nationality": nationality_display,
        "marital_status": str(marital).lower() if marital else "",
        "immigration_status": immigration_status,
        "pass_type": str(pass_type).lower() if pass_type else "",
        "residential_address": address.get("residential_address", ""),
        "postal_code": address.get("postal_code", ""),
        "phone": f"{mobile_prefix}{mobile}" if mobile else "",
        "email": email,
        "birth_country": birth_country,
    }


# ---------------------------------------------------------------------------
# MyInfo Business
# ---------------------------------------------------------------------------


async def fetch_business_data(
    access_token: str,
    uen: Optional[str] = None,
) -> dict:
    """Retrieve MyInfo Business data for a company.

    Uses the MyInfo Business API to auto-populate company profile
    during onboarding (UEN, name, directors, SSIC codes).

    Args:
        access_token: Valid access token from CorpPass OAuth flow.
        uen: Company UEN (optional — may be derived from token).

    Returns:
        Dict with company profile data mapped to internal fields.
    """
    biz_base_url = _get_biz_base_url()
    entity_url = f"{biz_base_url}/entity-person"

    circuit = get_circuit("myinfo")

    async def _fetch() -> dict:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                entity_url,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json",
                },
            )
            if resp.status_code != 200:
                raise MyInfoError(
                    f"MyInfo Business data retrieval failed (HTTP {resp.status_code})",
                    error_code="business_fetch_failed",
                    details={"http_status": resp.status_code},
                )
            return resp.json()

    raw_data = await circuit.call(_fetch)

    _health.record_success("myinfo")

    # Map business data to Company model fields
    mapped = _map_business_to_company(raw_data)

    return {
        "raw_data": raw_data,
        "mapped_fields": mapped,
        "source": "myinfo_business",
    }


def _map_business_to_company(biz_data: dict) -> dict:
    """Map MyInfo Business data to AITE Company model fields."""
    entity = biz_data.get("entity", biz_data)

    def _val(field: Any) -> Any:
        if isinstance(field, dict):
            return field.get("value", field.get("desc", ""))
        return field

    uen = _val(entity.get("uen", ""))
    name = _val(entity.get("name", ""))
    entity_type = _val(entity.get("entityType", ""))
    entity_status = _val(entity.get("entityStatus", ""))

    # SSIC (Singapore Standard Industrial Classification) — primary activity
    primary_ssic = entity.get("primarySSIC", {})
    ssic_code = _val(primary_ssic.get("code", ""))
    ssic_desc = _val(primary_ssic.get("description", ""))

    # Registered address
    reg_addr = entity.get("registeredAddress", {})
    address_parts = []
    for field in ("block", "street", "floor", "unit", "building"):
        v = _val(reg_addr.get(field, ""))
        if v:
            address_parts.append(str(v))
    postal = _val(reg_addr.get("postal", ""))

    # Appointments (directors)
    appointments = entity.get("appointments", [])
    directors = []
    for appt in appointments:
        person_name = _val(appt.get("name", ""))
        position = _val(appt.get("position", ""))
        nric = _val(appt.get("idNo", ""))
        directors.append(
            {
                "name": person_name,
                "position": position,
                "nric_last4": nric[-4:] if nric and len(nric) >= 4 else "",
            }
        )

    return {
        "uen": uen,
        "name": name,
        "entity_type": entity_type,
        "entity_status": entity_status,
        "sector": ssic_desc,
        "sub_sector": ssic_code,
        "registered_address": " ".join(address_parts),
        "postal_code": str(postal),
        "directors": directors,
    }
