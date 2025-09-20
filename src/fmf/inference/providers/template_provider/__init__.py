"""Reference provider template for new inference integrations."""

from typing import Any

from ....core.interfaces import ModelSpec
from ...registry import register_provider
from .provider import TemplateProvider


@register_provider("template")
def _build_template(_cfg: Any) -> TemplateProvider:
    spec = ModelSpec(provider="template", model="debug", modality="text")
    return TemplateProvider(spec)


__all__ = ["TemplateProvider"]
