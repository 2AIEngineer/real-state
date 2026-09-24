import pytest

from apps.accounts.enums import PropertyRole
from apps.common.exceptions import BusinessRuleViolation, InvalidInput, NotFound
from apps.library.models import Folder
from apps.library.policies import DocumentPolicy
from apps.library.services import DocumentService, FolderService
from tests import factories as f

pytestmark = pytest.mark.django_db


def folder(world, name="Rules", parent=None):
    return FolderService.create(
        actor=world.manager, prop=world.prop, en_name=name, fr_name=f"{name} FR", parent=parent
    )


def test_default_folders_exist_for_every_new_property(world):
    FolderService.create_default_folders(prop=world.prop)
    assert Folder.objects.filter(property=world.prop, is_system=True).count() == 6


def test_names_are_unique_per_parent(world):
    root = folder(world)
    folder(world, "Sub", parent=root)
    folder(world, "Sub")  # same name at root level is fine
    with pytest.raises(InvalidInput):
        folder(world, "sub", parent=root)


def test_folder_cannot_move_inside_itself(world):
    root = folder(world)
    child = folder(world, "Child", parent=root)
    with pytest.raises(InvalidInput):
        FolderService.update(actor=world.manager, folder=root, changes={"parent_folder": child})


def test_only_empty_non_system_folders_can_be_deleted(world):
    root = folder(world)
    DocumentService.publish(
        actor=world.manager,
        folder=root,
        title="Bylaws",
        target_roles=[PropertyRole.OWNER],
        upload=f.pdf(),
    )
    with pytest.raises(BusinessRuleViolation):
        FolderService.delete(actor=world.manager, folder=root)


def test_documents_are_visible_to_their_target_roles_only(world):
    document = DocumentService.publish(
        actor=world.manager,
        folder=folder(world),
        title="AGM minutes",
        target_roles=[PropertyRole.OWNER],
        upload=f.pdf(),
    )
    assert DocumentService.get_visible(actor=world.owner, document_id=document.pk) == document
    with pytest.raises(NotFound):
        DocumentService.get_visible(actor=world.tenant, document_id=document.pk)
    assert DocumentPolicy.can_view(world.tenant, document) is False
