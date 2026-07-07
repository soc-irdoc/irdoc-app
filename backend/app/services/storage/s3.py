"""S3-compatible storage backend (AWS S3, MinIO, Cloudflare R2, Wasabi)."""
import asyncio
from functools import partial


class S3StorageBackend:
    backend_name = "s3"

    def __init__(self, config: dict):
        import boto3

        self.client = boto3.client(
            "s3",
            endpoint_url=config.get("endpoint_url") or None,
            aws_access_key_id=config["access_key_id"],
            aws_secret_access_key=config["secret_access_key"],
            region_name=config.get("region", "us-east-1"),
        )
        self.bucket = config["bucket"]

    async def store(self, data: bytes, path: str) -> str:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            partial(self.client.put_object, Bucket=self.bucket, Key=path, Body=data),
        )
        return path

    async def retrieve(self, path: str) -> bytes:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            partial(self.client.get_object, Bucket=self.bucket, Key=path),
        )
        return response["Body"].read()

    async def delete(self, path: str) -> None:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            partial(self.client.delete_object, Bucket=self.bucket, Key=path),
        )

    async def get_url(self, path: str, expires_in: int = 3600) -> str:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            partial(
                self.client.generate_presigned_url,
                "get_object",
                Params={"Bucket": self.bucket, "Key": path},
                ExpiresIn=expires_in,
            ),
        )

    async def test_connection(self) -> bool:
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                partial(self.client.head_bucket, Bucket=self.bucket),
            )
            return True
        except Exception:
            return False
