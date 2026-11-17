from datetime import datetime
from enum import Enum
from typing import Literal

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class Category(str, Enum):
    hardware = "Hardware"
    software = "Software"
    network = "Network"
    access = "Access"
    other = "Other"


class Priority(str, Enum):
    low = "Low"
    medium = "Medium"
    high = "High"


class Status(str, Enum):
    new = "New"
    in_progress = "In Progress"
    resolved = "Resolved"


class LoginRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"example": {"email": "ravi.kumar@company.com", "password": "staff123"}}
    )
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    name: str
    email: str
    role: str  # "employee" or "staff"


class TicketCreate(BaseModel):
    """What is sent to raise a ticket.
    Employee: req_name/req_email are taken from the login token (can be left out).
    Staff raising a ticket for someone: req_name and req_email are required."""
    model_config = ConfigDict(
        str_strip_whitespace=True,  # "   " counts as empty
        json_schema_extra={
            "example": {
                "title": "Wireless keyboard not responding",
                "description": "Keyboard stopped working this morning. Replaced batteries, still no response.",
                "req_name": "Amit Sharma",
                "req_email": "amit.sharma@company.com",
                "category": "Hardware",
            }
        },
    )

    title: str = Field(min_length=5, max_length=200)
    description: str = Field(min_length=10)
    req_name: str | None = Field(default=None, min_length=2, max_length=100)
    req_email: str | None = Field(default=None, max_length=150)
    category: Category | None = None

    @field_validator("req_email")
    @classmethod
    def check_email(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not EMAIL_RE.match(v):
            raise ValueError("must be a valid email address, e.g. name@company.com")
        return v.lower()


class TicketUpdate(BaseModel):
    """Fields staff may change. Send only the ones you want to change.
    Status is changed through its own endpoint."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",  # e.g. sending "status" here gives a clear 422
        json_schema_extra={"example": {"priority": "High", "category": "Network"}},
    )

    title: str | None = Field(default=None, min_length=5, max_length=200)
    description: str | None = Field(default=None, min_length=10)
    category: Category | None = None
    priority: Priority | None = None

    @model_validator(mode="after")
    def at_least_one_field(self):
        if not self.model_dump(exclude_none=True):
            raise ValueError("send at least one of: title, description, category, priority")
        return self


class TicketOut(BaseModel):
    ticket_id: str
    title: str
    description: str
    category: Category | None
    priority: Priority | None
    status: Status
    req_id: str
    req_name: str
    req_email: str
    created_at: datetime


class ActivityCreate(BaseModel):
    """Support action: a comment, a status change, or both."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
        json_schema_extra={
            "example": {"comment": "Checked AP channels on 3rd floor", "new_status": "In Progress"}
        },
    )

    comment: str | None = Field(default=None, min_length=1, max_length=2000)
    new_status: Status | None = None

    @model_validator(mode="after")
    def at_least_one_field(self):
        if self.comment is None and self.new_status is None:
            raise ValueError("send a comment, a new_status, or both")
        return self


class ActivityOut(BaseModel):
    """One row of ticket history: an action/note and the status change (if any)."""
    activity_id: str
    ticket_id: str
    note_action: str
    old_status: str | None
    new_status: str
    comments: str | None
    updated_at: datetime


class FeedbackCreate(BaseModel):
    """Staff decision on the AI suggestion.
    accept  -> AI's category/priority become the ticket's values
    correct -> staff's final_category/final_priority become the ticket's values
              (a field left out keeps the AI's value)"""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
        json_schema_extra={
            "examples": [
                {"action": "accept", "is_useful": True},
                {"action": "correct", "is_useful": False,
                 "final_category": "Network", "final_priority": "Medium",
                 "note": "VPN auth issue, not a client install problem"},
            ]
        },
    )

    action: Literal["accept", "correct"]
    is_useful: bool | None = None  # default: accept=True, correct=False
    final_category: Category | None = None
    final_priority: Priority | None = None
    note: str | None = Field(default=None, min_length=1, max_length=2000)

    @model_validator(mode="after")
    def check_action(self):
        has_values = self.final_category is not None or self.final_priority is not None
        if self.action == "correct" and not has_values:
            raise ValueError("action 'correct' needs final_category and/or final_priority")
        if self.action == "accept" and has_values:
            raise ValueError("action 'accept' uses the AI's values; use action 'correct' to give your own")
        if self.is_useful is None:
            self.is_useful = self.action == "accept"
        return self


class DashboardSummary(BaseModel):
    total: int
    by_status: dict[str, int]
    by_priority: dict[str, int]
    by_category: dict[str, int]


class AISuggestionOut(BaseModel):
    sugg_category: str | None
    sugg_priority: str | None
    troubleshooting: str | None
    tokens_used: int | None
    analyzed_at: datetime


class AIFeedbackOut(BaseModel):
    is_useful: bool
    corrected_value: str | None
    created_at: datetime


class TicketDetailOut(TicketOut):
    """Ticket plus AI suggestion and staff feedback (null if not present yet).
    AI values are kept separate from the human-confirmed category/priority."""
    ai_suggestion: AISuggestionOut | None
    ai_feedback: AIFeedbackOut | None
