from enum import Enum


class EmailStatus(str, Enum):
    SENDING = "SENDING"
    SENT = "SENT"
    FAILED = "FAILED"
    QUEUED = "QUEUED"

class FormStatus(str, Enum):
    NEW = "NEW"
    IN_PROGRESS = "IN_PROGRESS"
    VIEWED = "VIEWED"
    ARCHIVED = "ARCHIVED"