import logging

from fastapi import Depends, FastAPI, HTTPException

from app.auth import authenticate, create_token, get_current_user, require_staff
from app.schemas import (
    ActivityCreate,
    ActivityOut,
    AISuggestionOut,
    Category,
    DashboardSummary,
    FeedbackCreate,
    LoginRequest,
    LoginResponse,
    Priority,
    Status,
    TicketCreate,
    TicketDetailOut,
    TicketOut,
    TicketUpdate,
)
from app.services import ai_service, ticket_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

app = FastAPI(
    title="AI-Powered Employee Helpdesk API",
    version="0.1.0",
)


# ---------------------------------------------------------------- Health

@app.get("/health", tags=["Health"], summary="[Public] Health check")
def health():
    return {"status": "ok"}


# ---------------------------------------------------------------- Login

@app.post("/auth/login", response_model=LoginResponse, tags=["Login"],
          summary="[Public] Log in (employee or staff)")
def login(body: LoginRequest):
    """Log in as employee or staff. Copy access_token into the Authorize button."""
    user = authenticate(body.email, body.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return {"access_token": create_token(user), **user}


@app.get("/auth/me", tags=["Login"], summary="[Employee + Staff] Who am I")
def me(user=Depends(get_current_user)):
    """Who is logged in (name, email, role)."""
    return user


def check_owner(ticket, user):
    """Employees may only see their own tickets; staff may see all."""
    if user["role"] == "employee" and ticket["req_email"].lower() != user["email"].lower():
        raise HTTPException(status_code=403, detail="You can only view your own tickets")


# ---------------------------------------------------------------- Tickets

@app.get("/tickets", response_model=list[TicketOut], tags=["Tickets"],
         summary="[Employee + Staff] List tickets (employee: own only)")
def list_tickets(
    status: Status | None = None,
    category: Category | None = None,
    priority: Priority | None = None,
    req_email: str | None = None,
    user=Depends(get_current_user),
):
    """Staff: all tickets (work queue), filters optional.
    Employee: always only their own tickets ("My tickets")."""
    if user["role"] == "employee":
        req_email = user["email"]
    return ticket_service.list_tickets(
        status=status.value if status else None,
        category=category.value if category else None,
        priority=priority.value if priority else None,
        req_email=req_email,
    )


@app.post("/tickets", response_model=TicketOut, status_code=201, tags=["Tickets"],
          summary="[Employee + Staff] Raise a new ticket")
def create_ticket(body: TicketCreate, user=Depends(get_current_user)):
    """Raise a new ticket. Status starts as 'New'; priority is set later by staff.
    Employee: requester = the logged-in employee. Staff: give req_name + req_email."""
    if user["role"] == "employee":
        req_name, req_email = user["name"], user["email"]
    else:
        if not body.req_name or not body.req_email:
            raise HTTPException(status_code=422, detail="req_name and req_email are required")
        req_name, req_email = body.req_name, body.req_email

    ticket_id = ticket_service.create_ticket(
        title=body.title,
        description=body.description,
        req_name=req_name,
        req_email=req_email,
        category=body.category.value if body.category else None,
    )
    return ticket_service.get_ticket(ticket_id)


@app.get(
    "/tickets/{ticket_id}",
    response_model=TicketDetailOut,
    responses={404: {"description": "Ticket not found"}},
    tags=["Tickets"],
    summary="[Employee + Staff] Ticket details (employee: own only)",
)
def get_ticket(ticket_id: str, user=Depends(get_current_user)):
    """One ticket with requester details, AI suggestion and staff feedback."""
    ticket = ticket_service.get_ticket(ticket_id.upper())
    if ticket is None:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")
    check_owner(ticket, user)
    return ticket


@app.patch(
    "/tickets/{ticket_id}",
    response_model=TicketDetailOut,
    responses={404: {"description": "Ticket not found"}},
    tags=["Tickets"],
    summary="[Staff only] Update title / description / category / priority",
)
def update_ticket(ticket_id: str, body: TicketUpdate, user=Depends(require_staff)):
    """Update title, description, category and/or priority (send only what changes).
    Each real change is recorded in the ticket history."""
    ticket_id = ticket_id.upper()
    changes = {k: (v.value if hasattr(v, "value") else v)
               for k, v in body.model_dump(exclude_none=True).items()}
    changed = ticket_service.update_ticket(ticket_id, changes)
    if changed is None:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")
    return ticket_service.get_ticket(ticket_id)


@app.get(
    "/tickets/{ticket_id}/history",
    response_model=list[ActivityOut],
    responses={404: {"description": "Ticket not found"}},
    tags=["Tickets"],
    summary="[Employee + Staff] Ticket history (employee: own only)",
)
def get_ticket_history(ticket_id: str, user=Depends(get_current_user)):
    """Progress history of a ticket: every action, note and status change, oldest first."""
    ticket = ticket_service.get_ticket(ticket_id.upper())
    if ticket is None:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")
    check_owner(ticket, user)
    return ticket_service.get_ticket_history(ticket_id.upper())


# ---------------------------------------------------------------- Support workflow

@app.post(
    "/tickets/{ticket_id}/activity",
    response_model=ActivityOut,
    status_code=201,
    responses={
        404: {"description": "Ticket not found"},
        409: {"description": "Status change not allowed"},
    },
    tags=["Support workflow"],
    summary="[Staff only] Add comment and/or change status",
)
def add_activity(ticket_id: str, body: ActivityCreate, user=Depends(require_staff)):
    """Add a support comment, change the status, or both.
    Allowed status moves: New → In Progress → Resolved.
    Every call is saved in the ticket history (old status → new status)."""
    ticket_id = ticket_id.upper()
    try:
        activity = ticket_service.add_activity(
            ticket_id,
            comment=body.comment,
            new_status=body.new_status.value if body.new_status else None,
        )
    except ticket_service.InvalidTransition as e:
        raise HTTPException(status_code=409, detail=str(e))
    if activity is None:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")
    return activity


# ---------------------------------------------------------------- AI

@app.post(
    "/tickets/{ticket_id}/analyze",
    response_model=AISuggestionOut,
    responses={
        404: {"description": "Ticket not found"},
        502: {"description": "AI answered in an invalid format (nothing saved)"},
        503: {"description": "AI unavailable or timed out (nothing saved)"},
    },
    tags=["AI"],
    summary="[Staff only] Run AI analysis on a ticket",
)
def analyze_ticket(ticket_id: str, user=Depends(require_staff)):
    """Ask the AI for a suggested category, priority (with reason) and troubleshooting steps.
    The suggestion is stored separately; the ticket itself is NOT changed.
    If the AI fails, nothing is saved and the ticket can still be managed normally."""
    ticket_id = ticket_id.upper()
    ticket = ticket_service.get_ticket(ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")

    try:
        result, tokens = ai_service.analyze_ticket(ticket_id, ticket["title"], ticket["description"])
    except ai_service.AIUnavailable as e:
        raise HTTPException(
            status_code=503,
            detail=f"AI analysis unavailable: {e}. The ticket was not changed; you can continue managing it manually.",
        )
    except ai_service.AIInvalidOutput as e:
        raise HTTPException(
            status_code=502,
            detail=f"AI returned an invalid answer ({e}). Nothing was saved; try again or continue manually.",
        )

    return ticket_service.save_ai_suggestion(
        ticket_id,
        category=result.category.value,
        priority=result.priority.value,
        troubleshooting=ai_service.format_troubleshooting(result),
        tokens_used=tokens,
    )


@app.post(
    "/tickets/{ticket_id}/feedback",
    response_model=TicketDetailOut,
    responses={
        404: {"description": "Ticket not found"},
        409: {"description": "Ticket has no AI suggestion yet"},
    },
    tags=["AI"],
    summary="[Staff only] Accept or correct the AI suggestion",
)
def give_feedback(ticket_id: str, body: FeedbackCreate, user=Depends(require_staff)):
    """Staff accept or correct the AI suggestion and mark it useful / not useful.
    The final values are applied to the ticket; the AI's original suggestion is kept
    for comparison. Status is never changed here."""
    ticket_id = ticket_id.upper()
    try:
        ok = ticket_service.save_feedback(
            ticket_id,
            action=body.action,
            is_useful=body.is_useful,
            final_category=body.final_category.value if body.final_category else None,
            final_priority=body.final_priority.value if body.final_priority else None,
            note=body.note,
        )
    except ticket_service.NoSuggestion as e:
        raise HTTPException(status_code=409, detail=str(e))
    if ok is None:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")
    return ticket_service.get_ticket(ticket_id)


# ---------------------------------------------------------------- Dashboard

@app.get("/dashboard/summary", response_model=DashboardSummary, tags=["Dashboard"],
         summary="[Staff only] Ticket counts for dashboard")
def dashboard_summary(user=Depends(require_staff)):
    """Ticket counts grouped by status, priority and category."""
    return ticket_service.dashboard_summary()
