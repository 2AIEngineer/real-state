"""Files attached to records.

| Module           | Role                                                            |
|------------------|-----------------------------------------------------------------|
| `rules.py`       | Each kind of file: formats, count, size, owning model           |
| `formats.py`     | What a file really is, from its bytes                           |
| `service.py`     | `AttachmentService`: storing, listing, deleting                 |
| `serializers.py` | `AttachmentSerializer` (with the file URL), `AttachmentsField`  |

The table itself is `apps.common.models.Attachment`.
"""
