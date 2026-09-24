from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response

from apps.common.serializers import UploadFileSerializer
from apps.common.views import BaseAPIView
from apps.library import serializers as s
from apps.library.services import DocumentService, FolderService


@extend_schema(tags=["Library"])
class FolderListView(BaseAPIView):
    @extend_schema(
        parameters=[s.LibraryFoldersQueryParamsSerializer],
        responses=s.LibraryFolderSerializer(many=True),
    )
    def get(self, request):
        query = self.parse_query_params(s.LibraryFoldersQueryParamsSerializer)
        qs = FolderService.list_for_property(
            actor=request.user,
            prop=self.property,
            parent_id=query.get("parent_id"),
            root_only=query["root_only"],
        )
        return self.render_page(s.LibraryFolderSerializer, qs)

    @extend_schema(
        request=s.LibraryFolderCreateSerializer, responses={201: s.LibraryFolderSerializer}
    )
    def post(self, request):
        data = dict(self.parse(s.LibraryFolderCreateSerializer))
        parent_id = data.pop("parent_folder_id")
        parent = (
            FolderService.get_visible(actor=request.user, prop=self.property, folder_id=parent_id)
            if parent_id
            else None
        )
        folder = FolderService.create(actor=request.user, prop=self.property, parent=parent, **data)
        return self.render(s.LibraryFolderSerializer, folder, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Library"])
class FolderDetailView(BaseAPIView):
    @extend_schema(responses=s.LibraryFolderSerializer)
    def get(self, request, folder_id: int):
        return self.render(
            s.LibraryFolderSerializer,
            FolderService.get_visible(actor=request.user, prop=self.property, folder_id=folder_id),
        )

    @extend_schema(request=s.LibraryFolderUpdateSerializer, responses=s.LibraryFolderSerializer)
    def patch(self, request, folder_id: int):
        folder = FolderService.get_visible(
            actor=request.user, prop=self.property, folder_id=folder_id
        )
        data = dict(self.parse(s.LibraryFolderUpdateSerializer))
        if "parent_folder_id" in data:
            parent_id = data.pop("parent_folder_id")
            data["parent_folder"] = (
                FolderService.get_visible(
                    actor=request.user, prop=self.property, folder_id=parent_id
                )
                if parent_id
                else None
            )
        return self.render(
            s.LibraryFolderSerializer,
            FolderService.update(actor=request.user, folder=folder, changes=data),
        )

    @extend_schema(responses={204: None})
    def delete(self, request, folder_id: int):
        folder = FolderService.get_visible(
            actor=request.user, prop=self.property, folder_id=folder_id
        )
        FolderService.delete(actor=request.user, folder=folder)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["Library"])
class DocumentListView(BaseAPIView):
    @extend_schema(
        parameters=[s.LibraryDocumentsQueryParamsSerializer],
        responses=s.LibraryDocumentSerializer(many=True),
    )
    def get(self, request):
        query = self.parse_query_params(s.LibraryDocumentsQueryParamsSerializer)
        qs = DocumentService.list_visible(
            actor=request.user,
            prop=self.property,
            folder_id=query.get("folder_id"),
            search=query.get("search"),
        )
        return self.render_page(s.LibraryDocumentSerializer, qs)

    @extend_schema(
        request=s.LibraryDocumentCreateSerializer, responses={201: s.LibraryDocumentSerializer}
    )
    def post(self, request):
        data = dict(self.parse(s.LibraryDocumentCreateSerializer))
        folder = FolderService.get_visible(
            actor=request.user, prop=self.property, folder_id=data.pop("folder_id")
        )
        upload = data.pop("file")
        document = DocumentService.publish(actor=request.user, folder=folder, upload=upload, **data)
        return self.render(s.LibraryDocumentSerializer, document, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Library"])
class DocumentDetailView(BaseAPIView):
    @extend_schema(responses=s.LibraryDocumentSerializer)
    def get(self, request, document_id: int):
        return self.render(
            s.LibraryDocumentSerializer,
            DocumentService.get_visible(
                actor=request.user, prop=self.property, document_id=document_id
            ),
        )

    @extend_schema(request=s.LibraryDocumentUpdateSerializer, responses=s.LibraryDocumentSerializer)
    def patch(self, request, document_id: int):
        document = DocumentService.get_visible(
            actor=request.user, prop=self.property, document_id=document_id
        )
        data = dict(self.parse(s.LibraryDocumentUpdateSerializer))
        if "folder_id" in data:
            data["folder"] = FolderService.get_visible(
                actor=request.user, prop=self.property, folder_id=data.pop("folder_id")
            )
        return self.render(
            s.LibraryDocumentSerializer,
            DocumentService.update(actor=request.user, document=document, changes=data),
        )

    @extend_schema(responses={204: None})
    def delete(self, request, document_id: int):
        document = DocumentService.get_visible(
            actor=request.user, prop=self.property, document_id=document_id
        )
        DocumentService.delete(actor=request.user, document=document)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["Library"])
class DocumentFileView(BaseAPIView):
    @extend_schema(request=UploadFileSerializer, responses=s.LibraryDocumentSerializer)
    def patch(self, request, document_id: int):
        document = DocumentService.get_visible(
            actor=request.user, prop=self.property, document_id=document_id
        )
        data = self.parse(UploadFileSerializer)
        DocumentService.replace_file(actor=request.user, document=document, upload=data["file"])
        return self.render(s.LibraryDocumentSerializer, document)
