"""Azure Blob Storage backend."""
import asyncio
from datetime import datetime, timezone, timedelta
from functools import partial


class AzureBlobStorageBackend:
    backend_name = "azure_blob"

    def __init__(self, config: dict):
        from azure.storage.blob import BlobServiceClient

        connection_string = config.get("connection_string")
        if connection_string:
            self.service_client = BlobServiceClient.from_connection_string(
                connection_string
            )
        else:
            account_url = (
                f"https://{config['account_name']}.blob.core.windows.net"
            )
            self.service_client = BlobServiceClient(
                account_url=account_url,
                credential=config["account_key"],
            )
        self.container = config["container"]
        self._account_name: str = config.get("account_name", "")
        self._account_key: str = config.get("account_key", "")

    def _get_blob_client(self, path: str):
        return self.service_client.get_blob_client(
            container=self.container, blob=path
        )

    async def store(self, data: bytes, path: str) -> str:
        loop = asyncio.get_event_loop()
        blob_client = self._get_blob_client(path)
        await loop.run_in_executor(
            None, partial(blob_client.upload_blob, data, overwrite=True)
        )
        return path

    async def retrieve(self, path: str) -> bytes:
        loop = asyncio.get_event_loop()
        blob_client = self._get_blob_client(path)
        download = await loop.run_in_executor(None, blob_client.download_blob)
        return await loop.run_in_executor(None, download.readall)

    async def delete(self, path: str) -> None:
        loop = asyncio.get_event_loop()
        blob_client = self._get_blob_client(path)
        await loop.run_in_executor(None, blob_client.delete_blob)

    async def get_url(self, path: str, expires_in: int = 3600) -> str:
        from azure.storage.blob import generate_blob_sas, BlobSasPermissions

        loop = asyncio.get_event_loop()

        def _generate() -> str:
            sas_token = generate_blob_sas(
                account_name=self._account_name,
                container_name=self.container,
                blob_name=path,
                account_key=self._account_key,
                permission=BlobSasPermissions(read=True),
                expiry=datetime.now(timezone.utc) + timedelta(seconds=expires_in),
            )
            return (
                f"https://{self._account_name}.blob.core.windows.net"
                f"/{self.container}/{path}?{sas_token}"
            )

        return await loop.run_in_executor(None, _generate)

    async def test_connection(self) -> bool:
        try:
            loop = asyncio.get_event_loop()
            container_client = self.service_client.get_container_client(
                self.container
            )
            await loop.run_in_executor(None, container_client.get_container_properties)
            return True
        except Exception:
            return False
