"""Google Cloud Storage backend."""
import asyncio
import json
from datetime import timedelta
from functools import partial


class GCSStorageBackend:
    backend_name = "gcs"

    def __init__(self, config: dict):
        from google.cloud import storage as gcs
        from google.oauth2 import service_account

        service_account_json = config.get("service_account_json", "")
        if service_account_json:
            sa_info = json.loads(service_account_json)
            credentials = service_account.Credentials.from_service_account_info(
                sa_info,
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )
            self.client = gcs.Client(
                project=sa_info.get("project_id"),
                credentials=credentials,
            )
        else:
            # Fall back to ADC (Application Default Credentials)
            self.client = gcs.Client(project=config.get("project_id"))

        self.bucket_name = config["bucket"]

    def _get_bucket(self):
        return self.client.bucket(self.bucket_name)

    async def store(self, data: bytes, path: str) -> str:
        loop = asyncio.get_event_loop()
        bucket = self._get_bucket()
        blob = bucket.blob(path)
        await loop.run_in_executor(
            None, partial(blob.upload_from_string, data)
        )
        return path

    async def retrieve(self, path: str) -> bytes:
        loop = asyncio.get_event_loop()
        bucket = self._get_bucket()
        blob = bucket.blob(path)
        return await loop.run_in_executor(None, blob.download_as_bytes)

    async def delete(self, path: str) -> None:
        loop = asyncio.get_event_loop()
        bucket = self._get_bucket()
        blob = bucket.blob(path)
        await loop.run_in_executor(None, blob.delete)

    async def get_url(self, path: str, expires_in: int = 3600) -> str:
        loop = asyncio.get_event_loop()
        bucket = self._get_bucket()
        blob = bucket.blob(path)

        def _sign() -> str:
            return blob.generate_signed_url(
                expiration=timedelta(seconds=expires_in),
                method="GET",
                version="v4",
            )

        return await loop.run_in_executor(None, _sign)

    async def test_connection(self) -> bool:
        try:
            loop = asyncio.get_event_loop()
            bucket = self._get_bucket()
            await loop.run_in_executor(None, bucket.reload)
            return True
        except Exception:
            return False
