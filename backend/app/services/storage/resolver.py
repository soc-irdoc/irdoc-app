"""
StorageBackend resolver.
Priority: active storage_config row in DB → STORAGE_BACKEND env var.
lru_cache is used but must be cleared when config changes (call get_storage_backend.cache_clear()).
"""
from functools import lru_cache

from app.core.config import settings


@lru_cache(maxsize=1)
def get_storage_backend():
    """
    Returns the active storage backend based on the STORAGE_BACKEND env var.
    For cloud backends (s3/azure_blob/gcs), the config must come from the DB
    storage_configs row via get_storage_backend_from_config().
    """
    backend_name = settings.STORAGE_BACKEND
    if backend_name == "s3":
        from app.services.storage.s3 import S3StorageBackend  # noqa: F401
        raise ValueError(
            "S3 backend requires config from DB storage_configs table — "
            "use get_storage_backend_from_config() with the active StorageConfig row."
        )
    elif backend_name == "azure_blob":
        from app.services.storage.azure_blob import AzureBlobStorageBackend  # noqa: F401
        raise ValueError(
            "Azure Blob backend requires config from DB storage_configs table — "
            "use get_storage_backend_from_config() with the active StorageConfig row."
        )
    elif backend_name == "gcs":
        from app.services.storage.gcs import GCSStorageBackend  # noqa: F401
        raise ValueError(
            "GCS backend requires config from DB storage_configs table — "
            "use get_storage_backend_from_config() with the active StorageConfig row."
        )
    else:
        from app.services.storage.local import LocalStorageBackend
        return LocalStorageBackend(settings.STORAGE_PATH)


def get_storage_backend_from_config(config_row) -> object:
    """
    Instantiate a backend from a StorageConfig DB row.
    config_row.config must already be decrypted (plain dict) before calling this.
    """
    backend = config_row.backend
    cfg = config_row.config  # pre-decrypted dict

    if backend == "s3":
        from app.services.storage.s3 import S3StorageBackend
        return S3StorageBackend(cfg)
    elif backend == "azure_blob":
        from app.services.storage.azure_blob import AzureBlobStorageBackend
        return AzureBlobStorageBackend(cfg)
    elif backend == "gcs":
        from app.services.storage.gcs import GCSStorageBackend
        return GCSStorageBackend(cfg)
    else:
        from app.services.storage.local import LocalStorageBackend
        return LocalStorageBackend(settings.STORAGE_PATH)
