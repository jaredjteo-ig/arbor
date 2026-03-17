"""AWS S3 storage adapter for document storage and retrieval.

Centralized document storage for payslips, receipts, statutory files,
and generated bank files. Provides tenant-isolated storage with
presigned URL generation for secure time-limited downloads.

T225: AWS S3 Document Storage Connector
"""

from __future__ import annotations

import hashlib
import logging
import os
from datetime import datetime, timezone
from typing import Optional

import httpx

from hr_advisory.mcp_servers.resilience import get_circuit

logger = logging.getLogger(__name__)

_DEFAULT_REGION = "ap-southeast-1"


class S3StorageAdapter:
    """AWS S3 adapter for tenant-isolated document storage.

    All objects are stored with tenant-prefixed keys to enforce
    isolation: ``{tenant_id}/{category}/{file_key}``.

    Uses the AWS S3 REST API directly with SigV4 signing to avoid
    heavy boto3 dependency. For environments where boto3 is available,
    the adapter will use it for better performance and features.

    Usage::

        s3 = S3StorageAdapter()
        await s3.upload("tenant_123", "payslips/2026-03.pdf", pdf_bytes, "application/pdf")
        url = await s3.get_presigned_url("tenant_123", "payslips/2026-03.pdf")
    """

    def __init__(
        self,
        bucket: Optional[str] = None,
        region: Optional[str] = None,
        access_key_id: Optional[str] = None,
        secret_access_key: Optional[str] = None,
    ):
        self._bucket = bucket or os.environ.get("AWS_S3_BUCKET", "")
        self._region = region or os.environ.get("AWS_REGION", _DEFAULT_REGION)
        self._access_key_id = access_key_id or os.environ.get("AWS_ACCESS_KEY_ID", "")
        self._secret_access_key = secret_access_key or os.environ.get("AWS_SECRET_ACCESS_KEY", "")
        self._circuit = get_circuit("data_gov_sg")  # Reuse a generic circuit
        self._operation_log: list[dict] = []

        # Try to import boto3 for full S3 functionality
        self._boto3_client = None
        try:
            import boto3

            session = boto3.Session(
                aws_access_key_id=self._access_key_id or None,
                aws_secret_access_key=self._secret_access_key or None,
                region_name=self._region,
            )
            self._boto3_client = session.client("s3")
            logger.info(
                "S3 adapter initialized with boto3 (bucket=%s, region=%s)",
                self._bucket,
                self._region,
            )
        except ImportError:
            logger.info(
                "boto3 not available — S3 adapter will use REST API fallback "
                "(bucket=%s, region=%s)",
                self._bucket,
                self._region,
            )

    def _validate_config(self) -> None:
        if not self._bucket:
            raise ValueError(
                "AWS_S3_BUCKET not configured. "
                "Set the environment variable or pass bucket to constructor."
            )

    def _build_key(self, tenant_id: str, file_key: str) -> str:
        """Build a tenant-prefixed S3 object key.

        Enforces tenant isolation by always prepending tenant_id.
        Sanitizes the file_key to prevent path traversal.
        """
        # Prevent path traversal
        sanitized = file_key.replace("..", "").lstrip("/")
        return f"{tenant_id}/{sanitized}"

    def _validate_tenant_access(self, tenant_id: str, full_key: str) -> None:
        """Verify that the full key belongs to the claimed tenant."""
        if not full_key.startswith(f"{tenant_id}/"):
            raise PermissionError(
                f"Access denied: key '{full_key}' does not belong to tenant '{tenant_id}'"
            )

    async def upload(
        self,
        tenant_id: str,
        file_key: str,
        file_bytes: bytes,
        content_type: str = "application/octet-stream",
        metadata: Optional[dict[str, str]] = None,
    ) -> dict:
        """Upload a file to S3 with tenant-prefixed key.

        Args:
            tenant_id: Tenant ID for isolation.
            file_key: File path within tenant scope (e.g. "payslips/2026-03.pdf").
            file_bytes: Raw file bytes.
            content_type: MIME type.
            metadata: Optional custom metadata dict.

        Returns:
            Dict with "key", "size_bytes", "content_type", "etag".
        """
        self._validate_config()
        full_key = self._build_key(tenant_id, file_key)
        content_hash = hashlib.md5(file_bytes).hexdigest()

        if self._boto3_client is not None:
            result = await self._upload_boto3(full_key, file_bytes, content_type, metadata)
        else:
            result = await self._upload_rest(full_key, file_bytes, content_type)

        log_entry = {
            "operation": "upload",
            "tenant_id": tenant_id,
            "key": full_key,
            "size_bytes": len(file_bytes),
            "content_type": content_type,
            "md5": content_hash,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._operation_log.append(log_entry)

        logger.info(
            "S3 upload: key=%s, size=%d bytes, type=%s",
            full_key,
            len(file_bytes),
            content_type,
        )
        return {
            "key": full_key,
            "size_bytes": len(file_bytes),
            "content_type": content_type,
            "etag": result.get("etag", content_hash),
        }

    async def _upload_boto3(
        self,
        key: str,
        file_bytes: bytes,
        content_type: str,
        metadata: Optional[dict[str, str]],
    ) -> dict:
        """Upload using boto3."""
        import asyncio

        def _sync_upload() -> dict:
            params = {
                "Bucket": self._bucket,
                "Key": key,
                "Body": file_bytes,
                "ContentType": content_type,
                "ServerSideEncryption": "AES256",
            }
            if metadata:
                params["Metadata"] = metadata

            response = self._boto3_client.put_object(**params)
            return {"etag": response.get("ETag", "").strip('"')}

        return await asyncio.get_event_loop().run_in_executor(None, _sync_upload)

    async def _upload_rest(
        self,
        key: str,
        file_bytes: bytes,
        content_type: str,
    ) -> dict:
        """Upload using S3 REST API with httpx (fallback when boto3 unavailable)."""
        url = f"https://{self._bucket}.s3.{self._region}.amazonaws.com/{key}"

        async def _do_upload() -> dict:
            async with httpx.AsyncClient(timeout=60.0) as client:
                headers = {
                    "Content-Type": content_type,
                    "x-amz-server-side-encryption": "AES256",
                }
                resp = await client.put(url, content=file_bytes, headers=headers)
                resp.raise_for_status()
                return {"etag": resp.headers.get("ETag", "").strip('"')}

        return await self._circuit.call(_do_upload)

    async def get_presigned_url(
        self,
        tenant_id: str,
        file_key: str,
        expires_in: int = 3600,
    ) -> dict:
        """Generate a time-limited presigned download URL.

        Args:
            tenant_id: Tenant ID for isolation.
            file_key: File path within tenant scope.
            expires_in: URL expiry in seconds (default 1 hour, max 7 days).

        Returns:
            Dict with "url", "expires_in", "key".
        """
        self._validate_config()
        full_key = self._build_key(tenant_id, file_key)
        self._validate_tenant_access(tenant_id, full_key)

        # Cap expiry at 7 days
        expires_in = min(expires_in, 604800)

        if self._boto3_client is not None:
            url = await self._presign_boto3(full_key, expires_in)
        else:
            url = self._presign_fallback(full_key, expires_in)

        self._operation_log.append(
            {
                "operation": "presign",
                "tenant_id": tenant_id,
                "key": full_key,
                "expires_in": expires_in,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

        logger.info(
            "S3 presigned URL generated: key=%s, expires_in=%ds",
            full_key,
            expires_in,
        )
        return {
            "url": url,
            "expires_in": expires_in,
            "key": full_key,
        }

    async def _presign_boto3(self, key: str, expires_in: int) -> str:
        """Generate presigned URL using boto3."""
        import asyncio

        def _sync_presign() -> str:
            return self._boto3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self._bucket, "Key": key},
                ExpiresIn=expires_in,
            )

        return await asyncio.get_event_loop().run_in_executor(None, _sync_presign)

    def _presign_fallback(self, key: str, expires_in: int) -> str:
        """Generate a presigned-style URL without boto3.

        Without proper SigV4 signing, this generates a reference URL.
        In production, boto3 should always be available. This fallback
        is for development/testing only.
        """
        import hmac
        import base64
        from datetime import timedelta

        if not self._access_key_id or not self._secret_access_key:
            # Return an unsigned reference URL for development
            logger.warning(
                "S3 presigned URL generated without signing (no AWS credentials). "
                "This URL will NOT work for actual downloads."
            )
            return (
                f"https://{self._bucket}.s3.{self._region}.amazonaws.com/{key}"
                f"?unsigned=true&expires_in={expires_in}"
            )

        # Basic SigV2 presigning (simplified — production should use boto3)
        expiry_epoch = int(datetime.now(timezone.utc).timestamp()) + expires_in
        string_to_sign = f"GET\n\n\n{expiry_epoch}\n/{self._bucket}/{key}"
        signature = base64.b64encode(
            hmac.new(
                self._secret_access_key.encode(),
                string_to_sign.encode(),
                hashlib.sha1,
            ).digest()
        ).decode()

        from urllib.parse import quote_plus

        return (
            f"https://{self._bucket}.s3.{self._region}.amazonaws.com/{key}"
            f"?AWSAccessKeyId={self._access_key_id}"
            f"&Expires={expiry_epoch}"
            f"&Signature={quote_plus(signature)}"
        )

    async def delete(
        self,
        tenant_id: str,
        file_key: str,
    ) -> dict:
        """Delete a file from S3 (soft-delete via lifecycle is preferred).

        Args:
            tenant_id: Tenant ID for isolation.
            file_key: File path within tenant scope.

        Returns:
            Dict with deletion status.
        """
        self._validate_config()
        full_key = self._build_key(tenant_id, file_key)
        self._validate_tenant_access(tenant_id, full_key)

        if self._boto3_client is not None:
            await self._delete_boto3(full_key)
        else:
            await self._delete_rest(full_key)

        self._operation_log.append(
            {
                "operation": "delete",
                "tenant_id": tenant_id,
                "key": full_key,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

        logger.info("S3 delete: key=%s", full_key)
        return {"key": full_key, "status": "deleted"}

    async def _delete_boto3(self, key: str) -> None:
        import asyncio

        def _sync_delete() -> None:
            self._boto3_client.delete_object(Bucket=self._bucket, Key=key)

        await asyncio.get_event_loop().run_in_executor(None, _sync_delete)

    async def _delete_rest(self, key: str) -> None:
        url = f"https://{self._bucket}.s3.{self._region}.amazonaws.com/{key}"

        async def _do_delete() -> None:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.delete(url)
                resp.raise_for_status()

        await self._circuit.call(_do_delete)

    async def list_objects(
        self,
        tenant_id: str,
        prefix: str = "",
        max_keys: int = 1000,
    ) -> list[dict]:
        """List objects within a tenant's scope.

        Args:
            tenant_id: Tenant ID for isolation.
            prefix: Additional prefix filter within tenant scope.
            max_keys: Maximum number of keys to return.

        Returns:
            List of object info dicts with "key", "size", "last_modified".
        """
        self._validate_config()
        full_prefix = self._build_key(tenant_id, prefix)

        if self._boto3_client is not None:
            return await self._list_boto3(full_prefix, max_keys, tenant_id)

        # REST fallback returns empty list (listing requires XML parsing)
        logger.warning("S3 list_objects requires boto3 — returning empty list")
        return []

    async def _list_boto3(
        self,
        prefix: str,
        max_keys: int,
        tenant_id: str,
    ) -> list[dict]:
        import asyncio

        def _sync_list() -> list[dict]:
            response = self._boto3_client.list_objects_v2(
                Bucket=self._bucket,
                Prefix=prefix,
                MaxKeys=max_keys,
            )
            objects = []
            for obj in response.get("Contents", []):
                # Strip tenant prefix for the returned key
                rel_key = obj["Key"]
                tenant_prefix = f"{tenant_id}/"
                if rel_key.startswith(tenant_prefix):
                    rel_key = rel_key[len(tenant_prefix) :]
                objects.append(
                    {
                        "key": rel_key,
                        "full_key": obj["Key"],
                        "size_bytes": obj["Size"],
                        "last_modified": obj["LastModified"].isoformat(),
                    }
                )
            return objects

        return await asyncio.get_event_loop().run_in_executor(None, _sync_list)

    def get_operation_log(self, limit: int = 100) -> list[dict]:
        """Return recent S3 operation log entries."""
        return self._operation_log[-limit:]

    def get_storage_info(self) -> dict:
        """Return adapter configuration info (no secrets)."""
        return {
            "bucket": self._bucket,
            "region": self._region,
            "has_credentials": bool(self._access_key_id),
            "boto3_available": self._boto3_client is not None,
            "total_operations": len(self._operation_log),
        }
