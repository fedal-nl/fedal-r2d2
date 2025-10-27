from enum import Enum


class EmailStatus(str, Enum):
    SENDING = "SENDING"
    SENT = "SENT"
    FAILED = "FAILED"
    QUEUED = "QUEUED"
