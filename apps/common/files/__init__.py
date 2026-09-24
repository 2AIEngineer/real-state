"""Files attached to records: rules, storage, signed links.

| Module          | Role                                                                  |
|-----------------|-----------------------------------------------------------------------|
| `rules.py`      | Each kind of file: formats, count, size, public or private            |
| `formats.py`    | What a file really is, from its bytes                                 |
| `service.py`    | `AttachmentService`: storing, listing, deleting                       |
| `links.py`      | Signed URLs the client uses as they are (`<img src>`, download)       |
| `delivery.py`   | Answering a link: stream the file, or redirect to the storage         |
| `storage.py`    | Azure Blob in a private container, read through short SAS URLs        |
| `serializers.py`| `AttachmentSerializer`, `AttachmentsField`                            |
| `views.py`      | `GET /files/<token>/`                                                 |
"""
