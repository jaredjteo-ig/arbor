# Copyright 2026 Terrene Foundation
# SPDX-License-Identifier: Apache-2.0

"""BYOK / LLM configuration endpoints.

Allows company admins to:
- Save an API key for a cloud provider (OpenAI, Anthropic, etc.)
- Configure an Ollama / custom endpoint
- Validate that the key or endpoint works
- View current-month token usage and budget status
- Delete (revoke) a stored configuration

All endpoints enforce authentication, tenant isolation, and admin role.
Encrypted keys are never returned — only a masked preview.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request

from hr_advisory.api.middleware.auth_middleware import require_role
from hr_advisory.api.middleware.tenant_isolation import validate_company_access
from hr_advisory.security.llm_encryption import encrypt_api_key
from hr_advisory.services.audit_log import AuditAction, log_audit_event
from hr_advisory.services.llm_config import (
    VALID_PROVIDERS,
    delete_llm_config,
    get_active_llm_config,
    save_llm_config,
)
from hr_advisory.services.llm_budget import get_usage_summary

logger = logging.getLogger(__name__)

router = APIRouter()

_MAX_KEY_LENGTH = 512
_MAX_URL_LENGTH = 2048
_MAX_MODEL_LENGTH = 256


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _config_to_response(config: dict) -> dict:
    """Convert a raw DB config dict to a safe API response (key masked)."""
    encrypted = config.get("encrypted_key")
    has_key = bool(encrypted)
    masked = ""
    if has_key:
        # We cannot mask the encrypted ciphertext — it would be meaningless.
        # Instead, indicate that a key is stored.
        masked = "***stored***"

    return {
        "id": config.get("id"),
        "company_id": config.get("company_id"),
        "provider": config.get("provider", ""),
        "has_key": has_key,
        "masked_key": masked,
        "model_pref": config.get("model_pref"),
        "base_url": config.get("base_url"),
        "status": config.get("status", "active"),
        "updated_by": config.get("updated_by"),
        "is_active": config.get("is_active", True),
        "created_at": config.get("created_at", ""),
        "updated_at": config.get("updated_at", ""),
    }


def _validate_provider(provider: str) -> None:
    """Validate provider name."""
    if provider not in VALID_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid provider. Must be one of: {', '.join(sorted(VALID_PROVIDERS))}",
        )


def _validate_base_url(base_url: str, provider: str) -> None:
    """Validate base_url format and requirement.

    Note: Private/internal IPs are intentionally ALLOWED because the Ollama
    endpoint is often on a private network (e.g., institution DGX server).
    Only cloud metadata endpoints are blocked (SSRF via 169.254.169.254).
    """
    if provider in ("ollama", "custom") and not base_url:
        raise HTTPException(
            status_code=400,
            detail=f"base_url is required for {provider} provider.",
        )
    if base_url and len(base_url) > _MAX_URL_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"base_url exceeds maximum length of {_MAX_URL_LENGTH} characters.",
        )
    if base_url and not (base_url.startswith("http://") or base_url.startswith("https://")):
        raise HTTPException(
            status_code=400,
            detail="base_url must start with http:// or https://",
        )
    # Block cloud metadata endpoints (SSRF protection)
    if base_url:
        from urllib.parse import urlparse

        parsed = urlparse(base_url)
        host = parsed.hostname or ""
        _blocked = {"169.254.169.254", "metadata.google.internal", "100.100.100.200"}
        if host in _blocked:
            raise HTTPException(
                status_code=400,
                detail="This endpoint address is not allowed.",
            )


# ---------------------------------------------------------------------------
# POST /companies/{company_id}/llm-config — Save BYOK key or Ollama config
# ---------------------------------------------------------------------------


@router.post("/{company_id}/llm-config")
async def save_company_llm_config(
    company_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager", "platform_admin")),
) -> dict:
    """Save or update the company's LLM provider configuration.

    Accepts an API key (which is encrypted before storage), a provider
    name, and optional model preference / base URL.

    For Ollama: no API key needed, but base_url is required.

    Status codes:
        200: Config saved successfully
        400: Invalid input
        401: Not authenticated
        403: Not authorized (wrong company or non-admin role)
        500: Server error
    """
    validate_company_access(current_user, requested_company_id=company_id)

    body = await request.json()

    provider = (body.get("provider") or "").strip().lower()
    api_key = (body.get("api_key") or "").strip()
    model_pref = (body.get("model_pref") or "").strip() or None
    base_url = (body.get("base_url") or "").strip() or None

    # Validate provider
    _validate_provider(provider)

    # Validate API key
    if provider != "ollama" and not api_key:
        raise HTTPException(
            status_code=400,
            detail="api_key is required for cloud providers.",
        )
    if api_key and len(api_key) > _MAX_KEY_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"api_key exceeds maximum length of {_MAX_KEY_LENGTH} characters.",
        )

    # Validate base_url
    if base_url:
        _validate_base_url(base_url, provider)
    elif provider in ("ollama", "custom"):
        raise HTTPException(
            status_code=400,
            detail=f"base_url is required for {provider} provider.",
        )

    # Validate model_pref
    if model_pref and len(model_pref) > _MAX_MODEL_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"model_pref exceeds maximum length of {_MAX_MODEL_LENGTH} characters.",
        )

    # Encrypt the key if provided
    encrypted_key = None
    if api_key:
        try:
            encrypted_key = encrypt_api_key(api_key)
        except Exception as exc:
            logger.error("Failed to encrypt API key for company_id=%s: %s", company_id, exc)
            raise HTTPException(
                status_code=500,
                detail="Failed to secure the API key. Please try again or contact support.",
            ) from exc

    user_id = current_user.get("sub")

    try:
        config = save_llm_config(
            company_id=company_id,
            provider=provider,
            encrypted_key=encrypted_key,
            model_pref=model_pref,
            base_url=base_url,
            updated_by=user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Failed to save LLM config for company_id=%s: %s", company_id, exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to save configuration. Please try again later.",
        ) from exc

    logger.info(
        "LLM config saved: company_id=%s, provider=%s, by user_id=%s",
        company_id,
        provider,
        user_id,
    )
    log_audit_event(
        action=AuditAction.LLM_KEY_CREATED,
        actor_user_id=user_id,
        company_id=company_id,
        target_entity="CompanyLLMConfig",
        details={"provider": provider},
    )

    return {
        "message": "LLM configuration saved successfully.",
        "config": _config_to_response(config),
    }


# ---------------------------------------------------------------------------
# GET /companies/{company_id}/llm-config — Get config with masked key
# ---------------------------------------------------------------------------


@router.get("/{company_id}/llm-config")
async def get_company_llm_config(
    company_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager", "platform_admin")),
) -> dict:
    """Get the company's active LLM configuration.

    Returns the configuration with the API key masked (never in plaintext).

    Status codes:
        200: Config found
        401: Not authenticated
        403: Not authorized
        404: No active config
    """
    validate_company_access(current_user, requested_company_id=company_id)

    config = get_active_llm_config(company_id=company_id)
    if config is None:
        return {
            "config": None,
            "message": "No LLM configuration found. Using server defaults.",
            "source": "server_env",
        }

    log_audit_event(
        action=AuditAction.LLM_KEY_VIEWED,
        actor_user_id=current_user.get("sub"),
        company_id=company_id,
        target_entity="CompanyLLMConfig",
    )

    return {
        "config": _config_to_response(config),
        "source": "byok",
    }


# ---------------------------------------------------------------------------
# DELETE /companies/{company_id}/llm-config — Remove config
# ---------------------------------------------------------------------------


@router.delete("/{company_id}/llm-config")
async def delete_company_llm_config(
    company_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager", "platform_admin")),
) -> dict:
    """Delete the company's LLM configuration.

    Hard-deletes the encrypted key from the database and soft-deletes
    the config row.  The company reverts to server .env defaults.

    Status codes:
        200: Config deleted
        401: Not authenticated
        403: Not authorized
        404: No active config to delete
    """
    validate_company_access(current_user, requested_company_id=company_id)

    deleted = delete_llm_config(company_id=company_id)
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="No active LLM configuration found for this company.",
        )

    user_id = current_user.get("sub")
    logger.info("LLM config deleted: company_id=%s, by user_id=%s", company_id, user_id)
    log_audit_event(
        action=AuditAction.LLM_KEY_DELETED,
        actor_user_id=user_id,
        company_id=company_id,
        target_entity="CompanyLLMConfig",
    )

    return {
        "message": "LLM configuration removed. Reverting to server defaults.",
    }


# ---------------------------------------------------------------------------
# POST /companies/{company_id}/llm-config/validate — Test key/endpoint
# ---------------------------------------------------------------------------


@router.post("/{company_id}/llm-config/validate")
async def validate_company_llm_config(
    company_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager", "platform_admin")),
) -> dict:
    """Validate a BYOK key or Ollama endpoint before saving.

    For cloud providers: makes a minimal API call (max_tokens=1).
    For Ollama: hits {base_url}/api/tags to verify reachability.

    Can validate either:
    - A new key/url passed in the request body (pre-save validation)
    - The currently stored config (no body needed)

    Status codes:
        200: Validation result (may be valid=True or valid=False)
        400: Invalid input
        401: Not authenticated
        403: Not authorized
    """
    validate_company_access(current_user, requested_company_id=company_id)

    body = await request.json() if request.headers.get("content-type") else {}

    provider = (body.get("provider") or "").strip().lower()
    api_key = (body.get("api_key") or "").strip()
    base_url = (body.get("base_url") or "").strip()
    model_pref = (body.get("model_pref") or "").strip()

    # If no body params, validate the stored config
    if not provider and not api_key and not base_url:
        config = get_active_llm_config(company_id=company_id)
        if config is None:
            return {
                "valid": False,
                "message": "No LLM configuration found to validate.",
            }
        provider = config.get("provider", "")
        base_url = config.get("base_url", "")
        model_pref = config.get("model_pref", "")
        # Decrypt stored key for validation
        encrypted = config.get("encrypted_key")
        if encrypted:
            from hr_advisory.security.llm_encryption import decrypt_api_key

            try:
                api_key = decrypt_api_key(encrypted)
            except Exception:
                return {
                    "valid": False,
                    "message": "Stored API key could not be decrypted. Please re-save your configuration.",
                }

    if not provider:
        raise HTTPException(status_code=400, detail="provider is required for validation.")

    _validate_provider(provider)

    # Validate based on provider type
    if provider == "ollama":
        return await _validate_ollama(base_url)
    else:
        return await _validate_cloud_provider(provider, api_key, base_url, model_pref)


async def _validate_ollama(base_url: str) -> dict:
    """Validate Ollama endpoint by hitting /api/tags."""
    if not base_url:
        return {"valid": False, "message": "base_url is required for Ollama."}

    import httpx

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            url = base_url.rstrip("/") + "/api/tags"
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                models = data.get("models", [])
                model_names = [m.get("name", "") for m in models[:10]]
                return {
                    "valid": True,
                    "message": f"Ollama endpoint is reachable. {len(models)} model(s) available.",
                    "available_models": model_names,
                }
            else:
                return {
                    "valid": False,
                    "message": f"Ollama endpoint returned status {resp.status_code}.",
                }
    except httpx.ConnectError:
        return {
            "valid": False,
            "message": "Cannot connect to Ollama endpoint. Is Ollama running?",
        }
    except httpx.TimeoutException:
        return {
            "valid": False,
            "message": "Ollama endpoint timed out. Check the URL and network.",
        }
    except Exception as exc:
        logger.warning("Ollama validation failed: %s", exc)
        return {
            "valid": False,
            "message": "Failed to validate Ollama endpoint. Check the URL.",
        }


async def _validate_cloud_provider(
    provider: str,
    api_key: str,
    base_url: str,
    model_pref: str,
) -> dict:
    """Validate a cloud provider API key with a minimal request."""
    if not api_key:
        return {"valid": False, "message": "API key is required for cloud providers."}

    try:
        if provider in ("openai", "deepseek", "mistral", "custom"):
            return await _validate_openai_compatible(provider, api_key, base_url, model_pref)
        elif provider == "anthropic":
            return await _validate_anthropic(api_key, model_pref)
        elif provider == "gemini":
            return await _validate_gemini(api_key, model_pref)
        else:
            return {"valid": False, "message": f"Validation not supported for provider: {provider}"}
    except Exception as exc:
        logger.warning("Cloud provider validation failed for %s: %s", provider, exc)
        return {
            "valid": False,
            "message": "Failed to validate API key. Please check the key and try again.",
        }


async def _validate_openai_compatible(
    provider: str,
    api_key: str,
    base_url: str,
    model_pref: str,
) -> dict:
    """Validate OpenAI-compatible API (OpenAI, DeepSeek, Mistral, custom)."""
    import httpx

    default_urls = {
        "openai": "https://api.openai.com/v1",
        "deepseek": "https://api.deepseek.com/v1",
        "mistral": "https://api.mistral.ai/v1",
    }
    url = (base_url or default_urls.get(provider, "")).rstrip("/")
    if not url:
        return {"valid": False, "message": "base_url is required for custom providers."}

    default_models = {
        "openai": "gpt-4o-mini",
        "deepseek": "deepseek-chat",
        "mistral": "mistral-small-latest",
    }
    model = model_pref or default_models.get(provider, "gpt-4o-mini")

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 1,
            },
        )

    if resp.status_code == 200:
        return {"valid": True, "message": f"API key validated successfully for {provider}."}
    elif resp.status_code == 401:
        return {"valid": False, "message": "Invalid API key. Please check and try again."}
    elif resp.status_code == 429:
        # Rate limited but key is valid
        return {
            "valid": True,
            "message": f"API key is valid for {provider} (rate limited during test).",
        }
    elif resp.status_code == 404:
        return {
            "valid": False,
            "message": f"Model '{model}' not found. Check the model name or base URL.",
        }
    else:
        return {
            "valid": False,
            "message": f"API returned status {resp.status_code}. Please check your configuration.",
        }


async def _validate_anthropic(api_key: str, model_pref: str) -> dict:
    """Validate Anthropic API key."""
    import httpx

    model = model_pref or "claude-haiku-4-5-20251001"

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "max_tokens": 1,
                "messages": [{"role": "user", "content": "Hi"}],
            },
        )

    if resp.status_code == 200:
        return {"valid": True, "message": "Anthropic API key validated successfully."}
    elif resp.status_code == 401:
        return {"valid": False, "message": "Invalid Anthropic API key."}
    elif resp.status_code == 429:
        return {"valid": True, "message": "Anthropic API key is valid (rate limited during test)."}
    elif resp.status_code == 404:
        return {
            "valid": False,
            "message": f"Model '{model}' not found. Check the model name.",
        }
    else:
        return {
            "valid": False,
            "message": f"Anthropic API returned status {resp.status_code}. Check your key.",
        }


async def _validate_gemini(api_key: str, model_pref: str) -> dict:
    """Validate Google Gemini API key."""
    import httpx

    model = model_pref or "gemini-2.5-flash"

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            params={"key": api_key},
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{"parts": [{"text": "Hi"}]}],
                "generationConfig": {"maxOutputTokens": 1},
            },
        )

    if resp.status_code == 200:
        return {"valid": True, "message": "Gemini API key validated successfully."}
    elif resp.status_code in (401, 403):
        return {"valid": False, "message": "Invalid Gemini API key."}
    elif resp.status_code == 429:
        return {"valid": True, "message": "Gemini API key is valid (rate limited during test)."}
    elif resp.status_code == 404:
        return {
            "valid": False,
            "message": f"Model '{model}' not found. Check the model name.",
        }
    else:
        return {
            "valid": False,
            "message": f"Gemini API returned status {resp.status_code}. Check your key.",
        }


# ---------------------------------------------------------------------------
# GET /companies/{company_id}/llm-usage — Current month usage
# ---------------------------------------------------------------------------


@router.get("/{company_id}/llm-usage")
async def get_company_llm_usage(
    company_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager", "platform_admin")),
) -> dict:
    """Get the current month's LLM usage and budget status for a company.

    Status codes:
        200: Usage summary
        401: Not authenticated
        403: Not authorized
    """
    validate_company_access(current_user, requested_company_id=company_id)

    try:
        summary = get_usage_summary(company_id)
    except Exception as exc:
        logger.error("Failed to get LLM usage for company_id=%s: %s", company_id, exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve usage data. Please try again later.",
        ) from exc

    return summary


# ---------------------------------------------------------------------------
# PUT /companies/{company_id}/llm-budget — Adjust monthly budget cap
# ---------------------------------------------------------------------------


@router.put("/{company_id}/llm-budget")
async def update_company_llm_budget(
    company_id: int,
    request: Request,
    current_user: dict = Depends(require_role("owner", "platform_admin")),
) -> dict:
    """Update the company's monthly LLM budget cap.

    Only owners and platform admins can change the budget.
    Minimum: $1.00, Maximum: $100.00.

    Status codes:
        200: Budget updated
        400: Invalid amount
        401: Not authenticated
        403: Not authorized
    """
    validate_company_access(current_user, requested_company_id=company_id)

    body = await request.json()
    budget = body.get("monthly_budget_usd")

    if budget is None:
        raise HTTPException(status_code=400, detail="monthly_budget_usd is required.")

    import math

    try:
        budget = float(budget)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="monthly_budget_usd must be a number.")

    if not math.isfinite(budget):
        raise HTTPException(status_code=400, detail="monthly_budget_usd must be a finite number.")

    if budget < 1.0:
        raise HTTPException(status_code=400, detail="Minimum budget is $1.00.")
    if budget > 100.0:
        raise HTTPException(status_code=400, detail="Maximum budget is $100.00.")

    # Update company record
    try:
        from kailash.runtime import LocalRuntime
        from kailash.workflow.builder import WorkflowBuilder
        import hr_advisory.models  # noqa: F401

        wf = WorkflowBuilder()
        wf.add_node(
            "CompanyUpdateNode",
            "update",
            {
                "filter": {"id": company_id},
                "fields": {"monthly_llm_budget_usd": budget},
            },
        )
        runtime = LocalRuntime()
        runtime.execute(wf.build())
    except Exception as exc:
        logger.error("Failed to update budget for company_id=%s: %s", company_id, exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to update budget. Please try again later.",
        ) from exc

    user_id = current_user.get("sub")
    logger.info(
        "LLM budget updated: company_id=%s, budget=$%.2f, by user_id=%s",
        company_id,
        budget,
        user_id,
    )
    log_audit_event(
        action=AuditAction.LLM_BUDGET_CHANGED,
        actor_user_id=user_id,
        company_id=company_id,
        target_entity="Company",
        details={"monthly_budget_usd": budget},
    )

    return {
        "message": f"Monthly AI budget updated to ${budget:.2f}.",
        "monthly_budget_usd": budget,
    }


# ---------------------------------------------------------------------------
# Per-user LLM config endpoints (T442)
# ---------------------------------------------------------------------------

from hr_advisory.api.middleware.auth_middleware import get_current_user
from hr_advisory.services.llm_config import save_user_llm_config, delete_user_llm_config

# Create a separate router for user-level endpoints (prefix=/users)
user_llm_router = APIRouter()


@user_llm_router.get("/me/llm-config")
async def get_user_llm_config(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Get the current user's personal LLM config (if any)."""
    user_id = current_user.get("sub")
    company_id = current_user.get("company_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required.")

    # Query user config directly (not the combined resolver which may return company config)
    try:
        from hr_advisory.services.llm_config import _execute_node, _extract_records

        result = _execute_node(
            "UserLLMConfigListNode",
            "find_user",
            {
                "filter": {"user_id": user_id, "is_active": True},
                "limit": 1,
                "enable_cache": False,
            },
        )
        records = _extract_records(result)
        if records and records[0].get("status") == "active":
            return {"config": _config_to_response(records[0]), "source": "user"}
    except Exception:
        logger.warning("Failed to load user LLM config", exc_info=True)
    return {"config": None, "source": "none"}


@user_llm_router.post("/me/llm-config")
async def save_user_personal_config(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Save a personal LLM API key (any authenticated user)."""
    user_id = current_user.get("sub")
    company_id = current_user.get("company_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required.")

    if not company_id:
        raise HTTPException(status_code=400, detail="No company associated with your account.")

    body = await request.json()
    provider = body.get("provider", "openai")
    api_key = body.get("api_key", "")
    model_pref = body.get("model_pref", "")
    base_url = body.get("base_url", "")

    _validate_provider(provider)
    if api_key and len(api_key) > _MAX_KEY_LENGTH:
        raise HTTPException(status_code=400, detail="API key is too long.")

    encrypted_key = encrypt_api_key(api_key) if api_key else None

    try:
        config = save_user_llm_config(
            user_id=int(user_id),
            company_id=int(company_id),
            provider=provider,
            encrypted_key=encrypted_key,
            model_pref=model_pref or None,
            base_url=base_url or None,
        )
    except Exception as exc:
        logger.error("Failed to save user LLM config: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to save configuration.") from exc

    log_audit_event(
        action=AuditAction.USER_LLM_KEY_CREATED,
        actor_user_id=user_id,
        company_id=company_id,
        target_entity="UserLLMConfig",
        details={"provider": provider},
    )
    return {"message": "Personal AI configuration saved.", "config": _config_to_response(config)}


@user_llm_router.delete("/me/llm-config")
async def delete_user_personal_config(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Delete the current user's personal LLM config."""
    user_id = current_user.get("sub")
    company_id = current_user.get("company_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required.")

    _cid = int(company_id) if company_id else 0
    deleted = delete_user_llm_config(user_id=int(user_id), company_id=_cid)
    if not deleted:
        raise HTTPException(status_code=404, detail="No personal AI configuration found.")

    log_audit_event(
        action=AuditAction.USER_LLM_KEY_DELETED,
        actor_user_id=user_id,
        company_id=company_id,
        target_entity="UserLLMConfig",
    )
    return {"message": "Personal AI configuration removed."}
