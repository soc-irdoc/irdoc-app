"""
Plugin registry. New integrations = new plugin file + @register_plugin decorator.
No core code changes needed.
"""
from typing import Type

PLUGINS: dict[str, Type] = {}


def register_plugin(cls: Type) -> Type:
    """Class decorator that registers a plugin in the global registry."""
    PLUGINS[cls.name] = cls
    return cls


def get_plugin(name: str) -> Type | None:
    """Return the plugin class for the given name, or None."""
    return PLUGINS.get(name)


def list_plugins() -> list[dict]:
    """Return metadata for all registered plugins (used by the integrations API)."""
    result = []
    for name, cls in PLUGINS.items():
        result.append({
            "name": name,
            "display_name": getattr(cls, "display_name", name),
            "category": getattr(cls, "category", ""),
            "is_premium": getattr(cls, "is_premium", False),
            "config_schema": getattr(cls, "config_schema", {}),
            "description": getattr(cls, "description", ""),
            "icon": getattr(cls, "icon", "electric_plug_color.svg"),
        })
    return sorted(result, key=lambda x: (x["category"], x["display_name"]))
