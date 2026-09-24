"""Vocabularies of the property referential."""

from django.db import models


class Feature(models.TextChoices):
    """Per-property activable modules (SaaS plan gating)."""

    SERVICE_REQUEST = "service_request", "Service requests"
    ANNOUNCEMENTS = "announcements", "Announcements"
    EVENTS = "events", "Events"
    AMENITIES = "amenities", "Amenities"
    STORE = "store", "Residential store"
    LIBRARY = "library", "Library"
    SHORT_TERM_RENTAL = "short_term_rental", "Short-term rentals"
    SURVEYS = "surveys", "Surveys"
    MARKETPLACE = "marketplace", "Marketplace"
    VISITOR = "visitor", "Visitors"
    CHAT = "chat", "Chat"
