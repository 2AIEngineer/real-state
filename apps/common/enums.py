"""Vocabulary shared across the whole API, not tied to one business domain."""

from django.db import models


class UIConfigStep(models.TextChoices):
    """How far the client is in configuring its session after login.

    The client announces it in the `X-UI-Config-Step` header. It is the path
    followed after every login: the syndicat page lists the syndicats the
    account may open, the property page lists the properties of the chosen
    syndicat, and the dashboard works inside the chosen pair (`X-Syndicat-Id`,
    `X-Property-Id`). Before the first step, right after login, the client
    sends no step header (the session reports `step: null`).
    """

    SYNDICAT = "syndicat", "Choosing a syndicat"
    PROPERTY = "property", "Choosing a property of the chosen syndicat"
    DASHBOARD = "dashboard", "Session configured"
