import hashlib
import io
from typing import TYPE_CHECKING

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

if TYPE_CHECKING:
    from config import Settings


def get_storage_client(settings: "Settings"):
    """Returns a boto3 S3 client pointed at MinIO."""
    return boto3.client(
        "s3",
        endpoint_url=settings.minio_endpoint_url,
        aws_access_key_id=settings.minio_access_key,
        aws_secret_access_key=settings.minio_secret_key,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )


def create_bucket_if_missing(settings: "Settings") -> None:
    client = get_storage_client(settings)
    try:
        client.head_bucket(Bucket=settings.minio_bucket)
    except ClientError as e:
        if e.response["Error"]["Code"] == "404":
            client.create_bucket(Bucket=settings.minio_bucket)
        else:
            raise


def upload_file(settings: "Settings", key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
    """Upload bytes to MinIO. Returns the object key."""
    client = get_storage_client(settings)
    client.put_object(
        Bucket=settings.minio_bucket,
        Key=key,
        Body=data,
        ContentType=content_type,
    )
    return key


def download_file(settings: "Settings", key: str) -> bytes:
    """Download object from MinIO and return bytes."""
    client = get_storage_client(settings)
    response = client.get_object(Bucket=settings.minio_bucket, Key=key)
    return response["Body"].read()


def get_presigned_url(settings: "Settings", key: str, expires_in: int = 3600) -> str:
    """Generate a presigned download URL valid for `expires_in` seconds."""
    client = get_storage_client(settings)
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.minio_bucket, "Key": key},
        ExpiresIn=expires_in,
    )


def sha256_of_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
