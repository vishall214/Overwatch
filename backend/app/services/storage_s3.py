"""S3 storage helper for OVERWATCH

Provides simple upload/download helpers that the application
can use when `Settings.use_s3` is enabled. Uses boto3 and
reads credentials from the configured Settings instance.
"""
from typing import BinaryIO, Optional
import io
import logging

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.core.dependencies import get_cached_settings

logger = logging.getLogger(__name__)


class S3Storage:
    def __init__(self):
        settings = get_cached_settings()
        self.enabled = bool(settings.use_s3 and settings.s3_bucket)
        if not self.enabled:
            return

        session = boto3.session.Session(
            aws_access_key_id=settings.s3_access_key_id or None,
            aws_secret_access_key=settings.s3_secret_access_key or None,
            region_name=settings.s3_region or None,
        )
        client_kwargs = {}
        if settings.s3_endpoint_url:
            client_kwargs["endpoint_url"] = settings.s3_endpoint_url

        self.client = session.client("s3", **client_kwargs)
        self.bucket = settings.s3_bucket

    def upload_fileobj(self, file_obj: BinaryIO, key: str, content_type: Optional[str] = None) -> bool:
        if not self.enabled:
            raise RuntimeError("S3Storage is not enabled - check configuration")

        extra_args = {}
        if content_type:
            extra_args["ContentType"] = content_type

        try:
            self.client.upload_fileobj(file_obj, self.bucket, key, ExtraArgs=extra_args or None)
            return True
        except (BotoCoreError, ClientError) as exc:
            logger.exception("Failed to upload to S3: %s", exc)
            return False

    def download_to_bytes(self, key: str) -> Optional[bytes]:
        if not self.enabled:
            raise RuntimeError("S3Storage is not enabled - check configuration")
        try:
            buff = io.BytesIO()
            self.client.download_fileobj(self.bucket, key, buff)
            buff.seek(0)
            return buff.read()
        except (BotoCoreError, ClientError) as exc:
            logger.exception("Failed to download from S3: %s", exc)
            return None


s3 = S3Storage()
