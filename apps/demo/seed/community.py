"""Community life: announcements, events, surveys and the document library."""

from __future__ import annotations

import datetime as dt

from apps.accounts.enums import PropertyRole
from apps.announcements.models import Announcement
from apps.announcements.services import AnnouncementService
from apps.demo import content, media
from apps.demo.seed.base import Demo, Residence
from apps.events.models import Event
from apps.events.services import EventService
from apps.library.models import Folder
from apps.library.services import DocumentService, FolderService
from apps.surveys.models import Survey
from apps.surveys.services import ParticipationService, QuestionInput, SurveyService

EVERYONE = [PropertyRole.OWNER, PropertyRole.TENANT, PropertyRole.MANAGER, PropertyRole.SECURITY]


def seed(demo: Demo) -> None:
    for residence in demo.residences:
        _announcements(demo, residence)
        _events(demo, residence)
        _surveys(demo, residence)
        _library(demo, residence)
        demo.log(f"  {residence.prop.name}: annonces, événements, sondages, bibliothèque")


def _announcements(demo: Demo, residence: Residence) -> None:
    for index, (category, priority, title, body) in enumerate(content.ANNOUNCEMENTS):
        published = demo.days_ago(1, 120)
        building = demo.rng.choice(residence.buildings) if index % 4 == 1 else None
        announcement = AnnouncementService.publish(
            actor=demo.rng.choice([residence.manager, residence.syndic, demo.admin]),
            prop=residence.prop,
            title=title if building is None else f"{title} — {building.name}",
            body=body,
            target_roles=[PropertyRole.OWNER, PropertyRole.TENANT],
            category=category,
            priority=priority,
            building=building,
            files=[media.pdf("note-information.pdf", title, [body[:90]])] if index % 3 == 0 else [],
        )
        Announcement.objects.filter(pk=announcement.pk).update(
            published_at=published, created_at=published
        )
        if index == len(content.ANNOUNCEMENTS) - 1:
            AnnouncementService.archive(actor=residence.manager, announcement=announcement)


def _events(demo: Demo, residence: Residence) -> None:
    for index, (title, description, location) in enumerate(content.EVENTS):
        start = demo.now + dt.timedelta(days=demo.rng.randint(3, 60), hours=demo.rng.randint(0, 6))
        event = EventService.create(
            actor=residence.manager,
            prop=residence.prop,
            title=title,
            description=description,
            location=location,
            start_at=start,
            end_at=start + dt.timedelta(hours=demo.rng.choice([2, 3, 4])),
            target_roles=EVERYONE,
            files=[media.png("affiche.png", (200, 80 + index * 15, 60))] if index % 2 == 0 else [],
        )
        if index < 4:  # the first half already took place
            past = demo.now - dt.timedelta(days=demo.rng.randint(7, 150))
            Event.objects.filter(pk=event.pk).update(
                start_at=past,
                end_at=past + dt.timedelta(hours=3),
                created_at=past - dt.timedelta(days=20),
            )
        elif index == 6:
            EventService.cancel(actor=residence.manager, event=event, reason="Météo défavorable.")
    EventService.complete_past(prop=residence.prop)


def _surveys(demo: Demo, residence: Residence) -> None:
    voters = [p for p in residence.residents if demo.chance(0.35)]
    for index, (title, description, questions) in enumerate(content.SURVEYS):
        survey = SurveyService.create_draft(
            actor=residence.manager,
            prop=residence.prop,
            title=title,
            description=description,
            target_roles=[PropertyRole.OWNER, PropertyRole.TENANT],
            questions=[QuestionInput(text, options) for text, options in questions],
            closes_at=demo.now + dt.timedelta(days=demo.rng.randint(10, 30)),
        )
        if index == 3:
            continue  # a draft still being written
        SurveyService.publish(actor=residence.manager, survey=survey)
        survey.refresh_from_db()
        rows = list(survey.questions.prefetch_related("options"))
        for voter in voters:
            if not demo.chance(0.7):
                continue
            answers = {q.pk: demo.rng.choice(list(q.options.all())).pk for q in rows}
            ParticipationService.respond(actor=voter, survey=survey, answers=answers)
        if index in (1, 2):  # closed surveys, results available
            Survey.objects.filter(pk=survey.pk).update(
                closes_at=demo.now - dt.timedelta(days=index * 9)
            )
    SurveyService.close_expired(prop=residence.prop)


def _library(demo: Demo, residence: Residence) -> None:
    folders = {
        f.en_name: f for f in Folder.objects.filter(property=residence.prop, parent_folder=None)
    }
    works = FolderService.create(
        actor=residence.manager,
        prop=residence.prop,
        en_name="Facade works 2026",
        fr_name="Travaux de façade 2026",
        parent=folders["Notices and communication"],
        description="Devis, planning et comptes rendus de chantier.",
    )
    for folder_name, title, description in content.LIBRARY_DOCUMENTS:
        DocumentService.publish(
            actor=residence.manager,
            folder=folders[folder_name],
            title=title,
            description=description,
            target_roles=[PropertyRole.OWNER, PropertyRole.TENANT],
            upload=media.pdf(f"{title}.pdf", title, [description, residence.prop.name]),
        )
    DocumentService.publish(
        actor=residence.manager,
        folder=works,
        title="Devis ravalement de façade",
        description="Devis retenu en conseil syndical.",
        target_roles=[PropertyRole.OWNER],
        upload=media.pdf(
            "devis-facade.pdf", "Devis ravalement de façade", ["Montant TTC : 1 240 000 MAD"]
        ),
    )
