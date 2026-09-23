"""Provider-neutral optional S3-compatible object storage adapter."""

from __future__ import annotations

from dataclasses import dataclass

from config import get_settings


class StorageUnavailable(RuntimeError):
    """Raised when an optional external storage backend is not configured."""


@dataclass(frozen=True)
class StorageObject:
    path: str
    size: int
    content_type: str


def is_configured() -> bool:
    settings = get_settings()
    return settings.object_storage_backend.lower() == "s3" and bool(
        settings.object_storage_bucket
        and settings.object_storage_access_key_id
        and settings.object_storage_secret_access_key
    )


def _client():
    settings = get_settings()
    if settings.object_storage_backend.lower() != "s3" or not is_configured():
        raise StorageUnavailable("S3-compatible storage is not configured")
    import boto3

    kwargs = {
        "service_name": "s3",
        "region_name": settings.object_storage_region or None,
        "endpoint_url": settings.object_storage_endpoint_url or None,
        "aws_access_key_id": settings.object_storage_access_key_id,
        "aws_secret_access_key": settings.object_storage_secret_access_key,
    }
    return boto3.client(**kwargs)


def put_object(path: str, data: bytes, content_type: str) -> dict:
    settings = get_settings()
    client = _client()
    client.put_object(
        Bucket=settings.object_storage_bucket,
        Key=path,
        Body=data,
        ContentType=content_type,
    )
    return {"path": path, "size": len(data), "content_type": content_type}


def get_object(path: str) -> tuple[bytes, str]:
    settings = get_settings()
    response = _client().get_object(Bucket=settings.object_storage_bucket, Key=path)
    body = response["Body"].read()
    return body, response.get("ContentType", "application/octet-stream")


def delete_object(path: str) -> None:
    settings = get_settings()
    _client().delete_object(Bucket=settings.object_storage_bucket, Key=path)
