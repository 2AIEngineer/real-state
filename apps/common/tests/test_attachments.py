import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.common.exceptions import InvalidInput
from apps.common.files.rules import RULES, EntityType
from apps.common.files.service import AttachmentService
from tests import factories as f

pytestmark = pytest.mark.django_db


def attach(world, entity_type, entity_id, files):
    return AttachmentService.attach(
        entity_type=entity_type, entity_id=entity_id, files=files, uploaded_by=world.admin
    )


def test_every_entity_type_has_a_rule():
    assert set(RULES) == set(EntityType.values)


def test_content_is_sniffed_not_trusted(world):
    with pytest.raises(InvalidInput):
        attach(world, EntityType.AMENITY, 1, [f.fake_exe()])


def test_metadata_is_recorded(world):
    (attachment,) = attach(world, EntityType.PROPERTY_LOGO, world.prop.pk, [f.png("façade.png")])
    assert attachment.mime_type == "image/png" and attachment.original_filename == "façade.png"
    assert len(attachment.checksum_sha256) == 64 and attachment.size == len(f.PNG_BYTES)
    assert attachment.file.name.startswith("attachments/property_logo/")
    assert "façade" not in attachment.file.name  # stored under a random name


def test_single_file_types_replace_the_current_file(world):
    attach(world, EntityType.PROPERTY_LOGO, world.prop.pk, [f.png()])
    attach(world, EntityType.PROPERTY_LOGO, world.prop.pk, [f.png()])
    assert AttachmentService.count(EntityType.PROPERTY_LOGO, world.prop.pk) == 1


def test_single_file_types_take_one_file_at_a_time(world):
    with pytest.raises(InvalidInput):
        attach(world, EntityType.CHAT_MESSAGE, 1, [f.png(), f.png()])


def test_maximum_number_of_files(world):
    limit = RULES[EntityType.AMENITY].max_files
    attach(world, EntityType.AMENITY, 1, [f.png() for _ in range(limit)])
    with pytest.raises(InvalidInput):
        attach(world, EntityType.AMENITY, 1, [f.png()])


def test_formats_follow_the_entity_type(world):
    webp = SimpleUploadedFile("x.webp", b"RIFF\x00\x00\x00\x00WEBPVP8 " + b"\x00" * 32)
    with pytest.raises(InvalidInput):
        AttachmentService.validate([webp], RULES[EntityType.CHAT_MESSAGE])
    assert AttachmentService.validate([f.pdf()], RULES[EntityType.CHAT_MESSAGE]) == [
        "application/pdf"
    ]
    with pytest.raises(InvalidInput):
        attach(world, EntityType.AMENITY, 1, [f.pdf()])  # images only


def test_the_stored_name_is_random_and_ends_with_the_detected_format(world):
    (attachment,) = attach(world, EntityType.PROPERTY_LOGO, world.prop.pk, [f.png("brand.html")])
    assert attachment.file.name.startswith("attachments/property_logo/")
    assert attachment.file.name.endswith(".png") and "brand" not in attachment.file.name


def test_every_entity_type_names_a_real_owner_model():
    from django.apps import apps

    for rule in RULES.values():
        assert apps.get_model(rule.owner)
