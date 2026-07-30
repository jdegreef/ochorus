from django.apps import AppConfig


class LibraryConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "library"

    def ready(self):
        # Connects the Language cache's invalidation signals. Without this the
        # per-process display cache would only refresh on a restart, so an admin
        # renaming a language would see the old name until one.
        from . import languages  # noqa: F401
