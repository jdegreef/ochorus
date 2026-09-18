from django.urls import path

from .views import ResendWebhookView, UnsubscribeView

urlpatterns = [
    path("webhook/", ResendWebhookView.as_view(), name="emails-webhook"),
    path(
        "unsubscribe/<str:token>/",
        UnsubscribeView.as_view(),
        name="emails-unsubscribe",
    ),
]
