# Copyright 2026 Terrene Foundation
# SPDX-License-Identifier: Apache-2.0

"""CLI command to rotate LLM_KEY_ENCRYPTION_KEY.

Decrypts all stored API keys with the old key and re-encrypts with the new key.

Usage:
    OLD_LLM_KEY=<old-key> NEW_LLM_KEY=<new-key> python -m hr_advisory.cli.rotate_llm_keys
"""

from __future__ import annotations

import logging
import os
import sys

logger = logging.getLogger(__name__)


def rotate_keys() -> None:
    """Rotate encryption key for all stored LLM API keys."""
    from cryptography.fernet import Fernet

    old_key_str = os.environ.get("OLD_LLM_KEY", "")
    new_key_str = os.environ.get("NEW_LLM_KEY", "")

    if not old_key_str or not new_key_str:
        print("ERROR: Set OLD_LLM_KEY and NEW_LLM_KEY environment variables.")
        print(
            "Usage: OLD_LLM_KEY=<old> NEW_LLM_KEY=<new> python -m hr_advisory.cli.rotate_llm_keys"
        )
        sys.exit(1)

    # Validate keys
    try:
        old_fernet = Fernet(old_key_str.encode())
        new_fernet = Fernet(new_key_str.encode())
    except Exception as e:
        print(f"ERROR: Invalid Fernet key: {e}")
        sys.exit(1)

    # Load .env for database access
    from pathlib import Path
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent.parent.parent / ".env")

    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder
    import hr_advisory.models  # noqa: F401 — register DataFlow models

    # Fetch all active configs with encrypted keys
    wf = WorkflowBuilder()
    wf.add_node(
        "CompanyLLMConfigListNode",
        "configs",
        {
            "filter": {"is_active": True},
            "limit": 10000,
            "enable_cache": False,
        },
    )
    runtime = LocalRuntime()
    results, _ = runtime.execute(wf.build())
    raw = results.get("configs", {})
    records = raw.get("records", []) if isinstance(raw, dict) else []

    rotated = 0
    failed = 0

    for record in records:
        encrypted_key = record.get("encrypted_key")
        if not encrypted_key:
            continue

        record_id = record.get("id")
        plaintext = None
        verify = None
        try:
            # Decrypt with old key
            plaintext = old_fernet.decrypt(encrypted_key.encode()).decode()

            # Re-encrypt with new key
            new_ciphertext = new_fernet.encrypt(plaintext.encode()).decode()

            # Verify the new ciphertext decrypts correctly
            verify = new_fernet.decrypt(new_ciphertext.encode()).decode()
            if verify != plaintext:
                raise ValueError("Re-encryption verification failed")

            # Update the record
            wf2 = WorkflowBuilder()
            wf2.add_node(
                "CompanyLLMConfigUpdateNode",
                "update",
                {
                    "filter": {"id": record_id},
                    "fields": {"encrypted_key": new_ciphertext},
                },
            )
            runtime.execute(wf2.build())
            rotated += 1
            print(
                f"  Rotated: CompanyLLMConfig id={record_id} (company_id={record.get('company_id')})"
            )
        except Exception as e:
            failed += 1
            print(f"  FAILED: CompanyLLMConfig id={record_id}: {e}")
        finally:
            del plaintext, verify  # Clear key material from memory

    # Also rotate UserLLMConfig keys
    wf3 = WorkflowBuilder()
    wf3.add_node(
        "UserLLMConfigListNode",
        "user_configs",
        {
            "filter": {"is_active": True},
            "limit": 10000,
            "enable_cache": False,
        },
    )
    results3, _ = runtime.execute(wf3.build())
    raw3 = results3.get("user_configs", {})
    user_records = raw3.get("records", []) if isinstance(raw3, dict) else []

    for record in user_records:
        encrypted_key = record.get("encrypted_key")
        if not encrypted_key:
            continue

        record_id = record.get("id")
        plaintext = None
        verify = None
        try:
            plaintext = old_fernet.decrypt(encrypted_key.encode()).decode()
            new_ciphertext = new_fernet.encrypt(plaintext.encode()).decode()
            verify = new_fernet.decrypt(new_ciphertext.encode()).decode()
            if verify != plaintext:
                raise ValueError("Re-encryption verification failed")

            wf4 = WorkflowBuilder()
            wf4.add_node(
                "UserLLMConfigUpdateNode",
                "update",
                {
                    "filter": {"id": record_id},
                    "fields": {"encrypted_key": new_ciphertext},
                },
            )
            runtime.execute(wf4.build())
            rotated += 1
            print(f"  Rotated: UserLLMConfig id={record_id} (user_id={record.get('user_id')})")
        except Exception as e:
            failed += 1
            print(f"  FAILED: UserLLMConfig id={record_id}: {e}")
        finally:
            del plaintext, verify  # Clear key material from memory

    print(f"\nRotation complete: {rotated} rotated, {failed} failed.")
    if failed > 0:
        print("WARNING: Some keys failed to rotate. Check the errors above.")
        print("The old key is still needed to decrypt those records.")
        sys.exit(1)
    else:
        print("All keys rotated successfully. Update LLM_KEY_ENCRYPTION_KEY to the new key.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    rotate_keys()
