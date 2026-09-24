from django.apps import AppConfig


class CommonConfig(AppConfig):
    name = "apps.common"
    label = "common"
    verbose_name = "Shared kernel"

    def ready(self) -> None:
        from apps.common import schema  # noqa: F401  (registers the OpenAPI extension)
