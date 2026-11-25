from django.apps import AppConfig


class LibraryConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "library"

    def ready(self):
        # Connects the Language signals: `languages` refreshes the per-process
        # display cache (else an admin renaming a language would see the old
        # name until a restart), and `admin_cache` drops the dashboard stats
        # memo, which a language write doesn't move the content revision for.
        from . import admin_cache, languages  # noqa: F401
