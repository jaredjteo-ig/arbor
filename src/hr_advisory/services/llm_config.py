# Copyright 2026 Terrene Foundation
# SPDX-License-Identifier: Apache-2.0

"""LLM configuration service — BYOK key management via DataFlow.

Provides CRUD operations for company and user LLM configs, resolves
the active LLM context per request (user override > company config >
server .env defaults), and handles key encryption/decryption.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from hr_advisory.agents.llm_context import LLMKeyContext

logger = logging.getLogger(__name__)

__all__ = [
    "get_active_llm_config",
    "save_llm_config",
    "save_user_llm_config",
    "delete_llm_config",
    "delete_user_llm_config",
    "build_llm_context",
]

# Valid provider names — validated before any DB write.
VALID_PROVIDERS = frozenset(
    {"openai", "anthropic", "gemini", "deepseek", "mistral", "ollama", "custom"}
)


# ---------------------------------------------------------------------------
# DataFlow helpers (same pattern used across the codebase)
# ---------------------------------------------------------------------------


def _execute_node(node_type: str, node_id: str, params: dict) -> dict:
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder

    import hr_advisory.models  # noqa: F401

    wf = WorkflowBuilder()
    wf.add_node(node_type, node_id, params)
    runtime = LocalRuntime()
    results, _ = runtime.execute(wf.build())
    return results[node_id]


def _extract_records(result) -> list[dict]:
    if isinstance(result, list):
        return result
    if isinstance(result, dict) and "records" in result:
        return result["records"]
    return []


# ---------------------------------------------------------------------------
# Company LLM Config
# ---------------------------------------------------------------------------


def get_active_llm_config(
    company_id: Optional[int] = None,
    user_id: Optional[int] = None,
) -> Optional[dict]:
    """Get the active LLM config for a company or user.

    Resolution order:
      1. User-level config (if user_id is given and one exists)
      2. Company-level config (if company_id is given)
      3. None (caller should fall back to server env)

    Returns the config dict (with encrypted_key still encrypted) or None.
    """
    # 1. Check user config first
    if user_id is not None and company_id is not None:
        try:
            result = _execute_node(
                "UserLLMConfigListNode",
                "find_user_config",
                {
                    "filter": {
                        "user_id": user_id,
                        "company_id": company_id,
                        "is_active": True,
                    },
                    "limit": 1,
                    "enable_cache": False,
                },
            )
            records = _extract_records(result)
            if records and records[0].get("status") == "active":
                return records[0]
        except Exception as exc:
            logger.warning("Failed to load user LLM config user_id=%s: %s", user_id, exc)

    # 2. Check company config
    if company_id is not None:
        try:
            result = _execute_node(
                "CompanyLLMConfigListNode",
                "find_company_config",
                {
                    "filter": {
                        "company_id": company_id,
                        "is_active": True,
                    },
                    "limit": 1,
                    "enable_cache": False,
                },
            )
            records = _extract_records(result)
            if records and records[0].get("status") == "active":
                return records[0]
        except Exception as exc:
            logger.warning(
                "Failed to load company LLM config company_id=%s: %s",
                company_id,
                exc,
            )

    return None


def save_llm_config(
    company_id: int,
    provider: str,
    encrypted_key: Optional[str] = None,
    model_pref: Optional[str] = None,
    base_url: Optional[str] = None,
    updated_by: Optional[int] = None,
) -> dict:
    """Save or update a company LLM config.

    If an active config for this company already exists, soft-deletes it
    first (sets is_active=False) and creates a new one.  This ensures a
    clean audit trail.

    Args:
        company_id: The company to configure.
        provider: One of VALID_PROVIDERS.
        encrypted_key: Already-encrypted API key (or None for Ollama).
        model_pref: Preferred model name (e.g. "gpt-5-chat-latest").
        base_url: Custom endpoint URL (required for Ollama/custom).
        updated_by: User ID of the admin making the change.

    Returns:
        The newly created config dict.
    """
    if provider not in VALID_PROVIDERS:
        raise ValueError(f"Invalid provider: {provider}")

    # Soft-delete any existing active config
    _deactivate_company_configs(company_id)

    create_params = {
        "company_id": company_id,
        "provider": provider,
        "encrypted_key": encrypted_key,
        "model_pref": model_pref,
        "base_url": base_url,
        "status": "active",
        "updated_by": updated_by,
        "is_active": True,
    }

    result = _execute_node("CompanyLLMConfigCreateNode", "create_config", create_params)

    # Fetch back the created record to get its ID
    config_id = result.get("id")
    if config_id is None:
        lookup = _execute_node(
            "CompanyLLMConfigListNode",
            "find_created",
            {
                "filter": {"company_id": company_id, "is_active": True},
                "limit": 1,
                "enable_cache": False,
            },
        )
        records = _extract_records(lookup)
        if records:
            return records[-1]

    logger.info(
        "Saved company LLM config: company_id=%s, provider=%s, updated_by=%s",
        company_id,
        provider,
        updated_by,
    )
    return result


def delete_llm_config(company_id: int, provider: Optional[str] = None) -> bool:
    """Delete company LLM config: hard-delete the encrypted key, soft-delete the row.

    Args:
        company_id: The company whose config to remove.
        provider: If given, only delete configs for this provider.

    Returns:
        True if at least one config was deactivated, False otherwise.
    """
    filter_params: dict = {"company_id": company_id, "is_active": True}
    if provider is not None:
        filter_params["provider"] = provider

    result = _execute_node(
        "CompanyLLMConfigListNode",
        "find_to_delete",
        {"filter": filter_params, "limit": 10000, "enable_cache": False},
    )
    records = _extract_records(result)
    if not records:
        return False

    for record in records:
        record_id = record.get("id")
        if record_id is None:
            continue
        # Clear the encrypted key and deactivate
        _execute_node(
            "CompanyLLMConfigUpdateNode",
            "soft_delete",
            {
                "filter": {"id": record_id},
                "fields": {
                    "encrypted_key": None,
                    "status": "revoked",
                    "is_active": False,
                },
            },
        )
    logger.info("Deleted %d company LLM config(s): company_id=%s", len(records), company_id)
    return True


# ---------------------------------------------------------------------------
# User LLM Config
# ---------------------------------------------------------------------------


def save_user_llm_config(
    user_id: int,
    company_id: int,
    provider: str,
    encrypted_key: Optional[str] = None,
    model_pref: Optional[str] = None,
    base_url: Optional[str] = None,
) -> dict:
    """Save or update a user-level LLM config override.

    Same pattern as save_llm_config but for per-user overrides.
    """
    if provider not in VALID_PROVIDERS:
        raise ValueError(f"Invalid provider: {provider}")

    # Soft-delete any existing active user config
    _deactivate_user_configs(user_id, company_id)

    create_params = {
        "user_id": user_id,
        "company_id": company_id,
        "provider": provider,
        "encrypted_key": encrypted_key,
        "model_pref": model_pref,
        "base_url": base_url,
        "status": "active",
        "is_active": True,
    }

    result = _execute_node("UserLLMConfigCreateNode", "create_user_config", create_params)

    config_id = result.get("id")
    if config_id is None:
        lookup = _execute_node(
            "UserLLMConfigListNode",
            "find_created_user",
            {
                "filter": {
                    "user_id": user_id,
                    "company_id": company_id,
                    "is_active": True,
                },
                "limit": 1,
                "enable_cache": False,
            },
        )
        records = _extract_records(lookup)
        if records:
            return records[-1]

    logger.info(
        "Saved user LLM config: user_id=%s, company_id=%s, provider=%s",
        user_id,
        company_id,
        provider,
    )
    return result


def delete_user_llm_config(user_id: int, company_id: int) -> bool:
    """Delete user LLM config: hard-delete key, soft-delete row."""
    result = _execute_node(
        "UserLLMConfigListNode",
        "find_user_to_delete",
        {
            "filter": {
                "user_id": user_id,
                "company_id": company_id,
                "is_active": True,
            },
            "limit": 10000,
            "enable_cache": False,
        },
    )
    records = _extract_records(result)
    if not records:
        return False

    for record in records:
        record_id = record.get("id")
        if record_id is None:
            continue
        _execute_node(
            "UserLLMConfigUpdateNode",
            "soft_delete_user",
            {
                "filter": {"id": record_id},
                "fields": {
                    "encrypted_key": None,
                    "status": "revoked",
                    "is_active": False,
                },
            },
        )
    logger.info(
        "Deleted %d user LLM config(s): user_id=%s, company_id=%s",
        len(records),
        user_id,
        company_id,
    )
    return True


# ---------------------------------------------------------------------------
# LLM Context Builder
# ---------------------------------------------------------------------------


def build_llm_context(
    company_id: int,
    user_id: Optional[int] = None,
) -> LLMKeyContext:
    """Build an LLMKeyContext from DB config, falling back to server env.

    Resolution order:
      1. User config (if user_id given)
      2. Company config
      3. Server .env defaults

    The returned context has the decrypted API key ready for use.
    """
    from hr_advisory.agents.llm_context import LLMKeyContext

    config = get_active_llm_config(company_id=company_id, user_id=user_id)
    if config is None:
        # No BYOK config — fall back to server env
        return LLMKeyContext.from_server_env(company_id=company_id)

    provider = config.get("provider", "openai")
    model = config.get("model_pref") or ""
    base_url = config.get("base_url")
    encrypted_key = config.get("encrypted_key")

    # Decrypt the key if present
    api_key: Optional[str] = None
    if encrypted_key:
        from hr_advisory.security.llm_encryption import decrypt_api_key

        try:
            api_key = decrypt_api_key(encrypted_key)
        except Exception as exc:
            logger.error(
                "Failed to decrypt BYOK key for company_id=%s: %s — " "falling back to server env",
                company_id,
                exc,
            )
            return LLMKeyContext.from_server_env(company_id=company_id)

    # Ollama: no key needed
    if provider == "ollama":
        return LLMKeyContext.for_ollama(
            base_url=base_url or "http://localhost:11434",
            model=model,
            company_id=company_id,
        )

    return LLMKeyContext(
        api_key=api_key,
        provider=provider,
        model=model,
        base_url=base_url,
        is_byok=True,
        company_id=company_id,
        user_id=user_id,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _deactivate_company_configs(company_id: int) -> None:
    """Soft-delete all active company LLM configs."""
    result = _execute_node(
        "CompanyLLMConfigListNode",
        "find_active",
        {
            "filter": {"company_id": company_id, "is_active": True},
            "limit": 10000,
            "enable_cache": False,
        },
    )
    for record in _extract_records(result):
        record_id = record.get("id")
        if record_id is None:
            continue
        _execute_node(
            "CompanyLLMConfigUpdateNode",
            "deactivate",
            {
                "filter": {"id": record_id},
                "fields": {"is_active": False, "encrypted_key": None},
            },
        )


def _deactivate_user_configs(user_id: int, company_id: int) -> None:
    """Soft-delete all active user LLM configs for a user/company pair."""
    result = _execute_node(
        "UserLLMConfigListNode",
        "find_active_user",
        {
            "filter": {
                "user_id": user_id,
                "company_id": company_id,
                "is_active": True,
            },
            "limit": 10000,
            "enable_cache": False,
        },
    )
    for record in _extract_records(result):
        record_id = record.get("id")
        if record_id is None:
            continue
        _execute_node(
            "UserLLMConfigUpdateNode",
            "deactivate_user",
            {
                "filter": {"id": record_id},
                "fields": {"is_active": False, "encrypted_key": None},
            },
        )
