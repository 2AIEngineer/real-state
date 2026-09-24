from drf_spectacular.utils import extend_schema_serializer
from rest_framework import serializers

from apps.accounts.enums import PropertyRole
from apps.common.files.rules import EntityType
from apps.common.files.serializers import AttachmentsField
from apps.common.serializers import UserSummarySerializer
from apps.library.models import Folder, LibraryDocument


class LibraryFolderSerializer(serializers.ModelSerializer):
    subfolders_count = serializers.SerializerMethodField()

    class Meta:
        model = Folder
        fields = [
            "id",
            "property",
            "parent_folder",
            "en_name",
            "fr_name",
            "description",
            "is_system",
            "subfolders_count",
            "created_at",
        ]
        read_only_fields = fields

    def get_subfolders_count(self, obj) -> int:
        # Lists annotate it in one query; single objects count on the spot.
        annotated = getattr(obj, "subfolders_count", None)
        return annotated if annotated is not None else obj.subfolders.count()


class LibraryDocumentSerializer(serializers.ModelSerializer):
    created_by = UserSummarySerializer(read_only=True)
    file = AttachmentsField(EntityType.LIBRARY_DOCUMENT, single=True)

    class Meta:
        model = LibraryDocument
        fields = [
            "id",
            "property",
            "folder",
            "title",
            "description",
            "target_roles",
            "file",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class LibraryFoldersQueryParamsSerializer(serializers.Serializer):
    parent_id = serializers.IntegerField(min_value=1, required=False)
    root_only = serializers.BooleanField(required=False, default=False)


class LibraryFolderCreateSerializer(serializers.Serializer):
    parent_folder_id = serializers.IntegerField(
        min_value=1, required=False, allow_null=True, default=None
    )
    en_name = serializers.CharField(max_length=160)
    fr_name = serializers.CharField(max_length=160)
    description = serializers.CharField(required=False, allow_blank=True, default="")


@extend_schema_serializer(component_name="LibraryFolder")
class LibraryFolderUpdateSerializer(serializers.Serializer):
    en_name = serializers.CharField(max_length=160, required=False)
    fr_name = serializers.CharField(max_length=160, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    parent_folder_id = serializers.IntegerField(min_value=1, required=False, allow_null=True)


class LibraryDocumentsQueryParamsSerializer(serializers.Serializer):
    folder_id = serializers.IntegerField(min_value=1, required=False)
    search = serializers.CharField(required=False, allow_blank=True, max_length=120)


class LibraryDocumentCreateSerializer(serializers.Serializer):
    folder_id = serializers.IntegerField(min_value=1)
    title = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    target_roles = serializers.ListField(
        child=serializers.ChoiceField(choices=PropertyRole.choices), allow_empty=False
    )
    file = serializers.FileField()


@extend_schema_serializer(component_name="LibraryDocument")
class LibraryDocumentUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    folder_id = serializers.IntegerField(min_value=1, required=False)
