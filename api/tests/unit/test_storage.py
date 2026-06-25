import hashlib
from unittest.mock import MagicMock, patch

import pytest

from core.storage import (
    create_bucket_if_missing,
    download_file,
    get_presigned_url,
    get_storage_client,
    sha256_of_bytes,
    upload_file,
)


@pytest.fixture
def settings(mock_settings):
    return mock_settings


@pytest.fixture
def mock_s3(settings):
    with patch("core.storage.boto3.client") as mock_boto:
        mock_client = MagicMock()
        mock_boto.return_value = mock_client
        yield mock_client


class TestGetStorageClient:
    def test_returns_boto3_client(self, settings):
        with patch("core.storage.boto3.client") as mock_boto:
            mock_boto.return_value = MagicMock()
            client = get_storage_client(settings)
            assert client is not None
            mock_boto.assert_called_once()

    def test_uses_correct_endpoint(self, settings):
        with patch("core.storage.boto3.client") as mock_boto:
            mock_boto.return_value = MagicMock()
            get_storage_client(settings)
            call_kwargs = mock_boto.call_args.kwargs
            assert "endpoint_url" in call_kwargs
            assert settings.minio_endpoint in call_kwargs["endpoint_url"]


class TestCreateBucketIfMissing:
    def test_creates_bucket_when_not_exists(self, settings, mock_s3):
        from botocore.exceptions import ClientError
        mock_s3.head_bucket.side_effect = ClientError(
            {"Error": {"Code": "404", "Message": "Not Found"}}, "HeadBucket"
        )
        create_bucket_if_missing(settings)
        mock_s3.create_bucket.assert_called_once_with(Bucket=settings.minio_bucket)

    def test_skips_creation_when_bucket_exists(self, settings, mock_s3):
        mock_s3.head_bucket.return_value = {}
        create_bucket_if_missing(settings)
        mock_s3.create_bucket.assert_not_called()

    def test_raises_on_unexpected_error(self, settings, mock_s3):
        from botocore.exceptions import ClientError
        mock_s3.head_bucket.side_effect = ClientError(
            {"Error": {"Code": "403", "Message": "Forbidden"}}, "HeadBucket"
        )
        with pytest.raises(ClientError):
            create_bucket_if_missing(settings)


class TestUploadFile:
    def test_uploads_and_returns_key(self, settings, mock_s3):
        key = upload_file(settings, "test/file.csv", b"hello,world", "text/csv")
        assert key == "test/file.csv"
        mock_s3.put_object.assert_called_once_with(
            Bucket=settings.minio_bucket,
            Key="test/file.csv",
            Body=b"hello,world",
            ContentType="text/csv",
        )

    def test_default_content_type(self, settings, mock_s3):
        upload_file(settings, "test/file.bin", b"data")
        call_kwargs = mock_s3.put_object.call_args.kwargs
        assert call_kwargs["ContentType"] == "application/octet-stream"


class TestDownloadFile:
    def test_returns_bytes(self, settings, mock_s3):
        mock_s3.get_object.return_value = {"Body": MagicMock(read=lambda: b"csv content")}
        result = download_file(settings, "test/file.csv")
        assert result == b"csv content"
        mock_s3.get_object.assert_called_once_with(Bucket=settings.minio_bucket, Key="test/file.csv")


class TestGetPresignedUrl:
    def test_returns_url_string(self, settings, mock_s3):
        mock_s3.generate_presigned_url.return_value = "https://minio/test/file.csv?sig=abc"
        url = get_presigned_url(settings, "test/file.csv", expires_in=600)
        assert url == "https://minio/test/file.csv?sig=abc"
        mock_s3.generate_presigned_url.assert_called_once_with(
            "get_object",
            Params={"Bucket": settings.minio_bucket, "Key": "test/file.csv"},
            ExpiresIn=600,
        )


class TestSha256OfBytes:
    def test_correct_hash(self):
        data = b"hello"
        expected = hashlib.sha256(b"hello").hexdigest()
        assert sha256_of_bytes(data) == expected

    def test_empty_bytes(self):
        result = sha256_of_bytes(b"")
        assert len(result) == 64

    def test_different_data_different_hash(self):
        assert sha256_of_bytes(b"a") != sha256_of_bytes(b"b")
