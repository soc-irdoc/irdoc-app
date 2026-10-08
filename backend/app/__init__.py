import os

# Same resolution as Settings.VERSION, without importing (and validating) the
# whole settings object — upgrade.sh prints this to confirm what is running.
__version__ = os.environ.get("APP_VERSION") or os.environ.get("VERSION") or "dev"
