"""S3-compatible object storage (RustFS / MinIO / AWS S3).

Two clients are kept on purpose:

* ``_client`` talks to the container-internal endpoint and is what the
  ingestion worker uses.
* ``_presign_client`` talks to the browser-reachable endpoint. SigV4 signs the
  ``Host`` header, so a URL signed against ``http://minio:9000`` would fail
  signature validation (and DNS resolution) in the user's browser.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import aioboto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.core.config import Settings
from app.core.errors import UpstreamError


class StorageClient:
    """Thin async wrapper over aioboto3 for the application's object needs."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.bucket = settings.minio_bucket
        self._session = aioboto3.Session()

    # ------------------------------------------------------------- internals
    def _make_client(self, presign: bool = False) -> Any:
        """Build a fresh client context.

        aioboto3 returns a *single-use* context manager from
        ``session.client(...)``, so a new one is required per operation rather
        than one long-lived client.
        """
        cfg = self.settings
        endpoint = cfg.minio_public_endpoint if presign else cfg.minio_endpoint
        return self._session.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=cfg.minio_access_key,
            aws_secret_access_key=cfg.minio_secret_key,
            region_name=cfg.minio_region,
            use_ssl=cfg.minio_secure,
            config=Config(
                signature_version="s3v4",
                s3={"addressing_style": "path"},
                retries={"max_attempts": 3, "mode": "standard"},
                connect_timeout=10,
                read_timeout=60,
            ),
        )

    @asynccontextmanager
    async def _ctx(self, presign: bool = False) -> AsyncIterator[Any]:
        async with self._make_client(presign) as s3:
            yield s3

    def _key(self, document_id: Any, filename: str) -> str:
        return f"documents/{document_id}/{filename}"

    # ---------------------------------------------------------------- public
    async def ensure_bucket(self) -> None:
        """Create the bucket when missing. Safe to call on every startup."""
        for attempt in range(1, 31):
            try:
                async with self._ctx() as s3:
                    try:
                        await s3.head_bucket(Bucket=self.bucket)
                    except ClientError:
                        await s3.create_bucket(Bucket=self.bucket)
                return
            except Exception as exc:  # retry while the store boots
                if attempt == 30:
                    raise UpstreamError(f"object storage unavailable: {exc}") from exc
                await asyncio.sleep(1)

    async def bucket_exists(self) -> bool:
        try:
            async with self._ctx() as s3:
                await s3.head_bucket(Bucket=self.bucket)
            return True
        except ClientError:
            return False

    async def upload_fileobj(
        self,
        fileobj: Any,
        key: str,
        *,
        content_type: str = "application/pdf",
    ) -> int:
        """Stream a file-like object to the bucket; returns the byte count."""
        async with self._ctx() as s3:
            await s3.upload_fileobj(
                fileobj,
                self.bucket,
                key,
                ExtraArgs={"ContentType": content_type},
            )
        return await self.size(key)

    async def upload_bytes(
        self, data: bytes, key: str, *, content_type: str = "application/pdf"
    ) -> int:
        import io

        return await self.upload_fileobj(io.BytesIO(data), key, content_type=content_type)

    async def download_bytes(self, key: str) -> bytes:
        async with self._ctx() as s3:
            response = await s3.get_object(Bucket=self.bucket, Key=key)
            async with response["Body"] as stream:
                return await stream.read()

    async def presigned_get(self, key: str, *, expires: int | None = None) -> str:
        """Return a browser-usable, signed GET URL for `key`."""
        ttl = expires or self.settings.minio_presign_expires
        async with self._ctx(presign=True) as s3:
            return await s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=ttl,
            )

    async def delete(self, key: str) -> None:
        async with self._ctx() as s3:
            await s3.delete_object(Bucket=self.bucket, Key=key)

    async def exists(self, key: str) -> bool:
        try:
            async with self._ctx() as s3:
                await s3.head_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError:
            return False

    async def size(self, key: str) -> int:
        async with self._ctx() as s3:
            response = await s3.head_object(Bucket=self.bucket, Key=key)
        return int(response["ContentLength"])

    def document_key(self, document_id: Any, filename: str) -> str:
        return self._key(document_id, filename)
