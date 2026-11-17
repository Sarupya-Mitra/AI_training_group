from app.db import get_cursor

# Allowed status moves. Anything else is rejected.
ALLOWED_TRANSITIONS = {
    "New": {"In Progress"},
    "In Progress": {"Resolved"},
    "Resolved": set(),  # final
}


class InvalidTransition(Exception):
    """Raised when a status change is not allowed (API turns it into 409)."""


class NoSuggestion(Exception):
    """Raised when feedback is given but the ticket has no AI suggestion (409)."""

TICKET_SELECT = """
    SELECT t.ticket_id, t.title, t.description, t.category, t.priority,
           t.status, t.created_at,
           r.req_id, r.req_name, r.req_email
    FROM tickets t
    JOIN requesters r ON r.req_id = t.req_id
"""


# ---------------------------------------------------------------- helpers

def _next_id(cur, table, column, prefix):
    """Next ID like T111 / A1018 / R1011: highest existing number + 1.
    table/column/prefix are fixed values from this file, never user input."""
    cur.execute(
        f"""
        SELECT COALESCE(MAX(CAST(SUBSTRING({column} FROM 2) AS INTEGER)), 0) + 1 AS n
        FROM {table}
        WHERE {column} ~ %s
        """,
        (f"^{prefix}[0-9]+$",),
    )
    return f"{prefix}{cur.fetchone()['n']}"


def _lock_ids(cur):
    """Lock (until commit) so two requests at the same moment can't get the same new ID.
    Call this before _next_id() in any function that inserts rows."""
    cur.execute("SELECT pg_advisory_xact_lock(1001)")


# ---------------------------------------------------------------- read

def list_tickets(status=None, category=None, priority=None, req_email=None):
    """Tickets joined with requester details, with optional filters, newest first."""
    sql = TICKET_SELECT + " WHERE 1 = 1"
    params = []
    if status:
        sql += " AND t.status = %s"
        params.append(status)
    if category:
        sql += " AND t.category = %s"
        params.append(category)
    if priority:
        sql += " AND t.priority = %s"
        params.append(priority)
    if req_email:
        sql += " AND LOWER(r.req_email) = LOWER(%s)"
        params.append(req_email)
    sql += " ORDER BY t.created_at DESC"

    with get_cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def get_ticket(ticket_id):
    """One ticket with requester details, its AI suggestion and staff feedback.
    Returns None if the ticket does not exist."""
    with get_cursor() as cur:
        cur.execute(TICKET_SELECT + " WHERE t.ticket_id = %s", (ticket_id,))
        row = cur.fetchone()
        if row is None:
            return None
        ticket = dict(row)

        cur.execute("SELECT * FROM ai_suggestions WHERE ticket_id = %s", (ticket_id,))
        ticket["ai_suggestion"] = cur.fetchone()

        cur.execute("SELECT * FROM ai_feedback WHERE ticket_id = %s", (ticket_id,))
        ticket["ai_feedback"] = cur.fetchone()

        return ticket


def get_ticket_history(ticket_id):
    """All activity rows for a ticket, oldest first.
    Returns None if the ticket does not exist (so the API can send 404),
    or a list (possibly empty) if it does."""
    with get_cursor() as cur:
        cur.execute("SELECT 1 FROM tickets WHERE ticket_id = %s", (ticket_id,))
        if cur.fetchone() is None:
            return None

        cur.execute(
            """
            SELECT activity_id, ticket_id, note_action, old_status, new_status,
                   comments, updated_at
            FROM ticket_activity
            WHERE ticket_id = %s
            ORDER BY updated_at, activity_id
            """,
            (ticket_id,),
        )
        return cur.fetchall()


# ---------------------------------------------------------------- create

def create_ticket(title, description, req_name, req_email, category=None):
    """Create a ticket in ONE transaction:
    1. find requester by email (or create a new one)
    2. insert ticket with status 'New'
    3. insert 'Ticket created' activity row
    Returns the new ticket_id."""
    with get_cursor() as cur:
        _lock_ids(cur)

        # 1. requester
        cur.execute(
            "SELECT req_id FROM requesters WHERE LOWER(req_email) = LOWER(%s)",
            (req_email,),
        )
        row = cur.fetchone()
        if row:
            req_id = row["req_id"]
        else:
            req_id = _next_id(cur, "requesters", "req_id", "R")
            cur.execute(
                "INSERT INTO requesters (req_id, req_name, req_email) VALUES (%s, %s, %s)",
                (req_id, req_name, req_email),
            )

        # 2. ticket (priority stays empty: set later by staff / AI suggestion)
        ticket_id = _next_id(cur, "tickets", "ticket_id", "T")
        cur.execute(
            """
            INSERT INTO tickets (ticket_id, title, description, category, status, req_id)
            VALUES (%s, %s, %s, %s, 'New', %s)
            """,
            (ticket_id, title, description, category, req_id),
        )

        # 3. history
        activity_id = _next_id(cur, "ticket_activity", "activity_id", "A")
        cur.execute(
            """
            INSERT INTO ticket_activity (activity_id, ticket_id, note_action, old_status, new_status)
            VALUES (%s, %s, 'Ticket created', NULL, 'New')
            """,
            (activity_id, ticket_id),
        )

    return ticket_id


# ---------------------------------------------------------------- update

UPDATABLE_FIELDS = ("title", "description", "category", "priority")


def update_ticket(ticket_id, changes):
    """Update some of: title, description, category, priority.
    Only fields that actually change are written, and one history row
    records what changed. Status is NOT changed here (separate endpoint).
    Returns None if the ticket does not exist, else the list of changed fields."""
    with get_cursor() as cur:
        # FOR UPDATE: lock this ticket row until we commit
        cur.execute(
            "SELECT title, description, category, priority, status FROM tickets "
            "WHERE ticket_id = %s FOR UPDATE",
            (ticket_id,),
        )
        row = cur.fetchone()
        if row is None:
            return None
        current = dict(row)

        changed = {k: v for k, v in changes.items()
                   if k in UPDATABLE_FIELDS and current[k] != v}
        if not changed:
            return []

        _lock_ids(cur)
        # Column names come from UPDATABLE_FIELDS (fixed), values are parameters
        set_sql = ", ".join(f"{col} = %s" for col in changed)
        cur.execute(
            f"UPDATE tickets SET {set_sql} WHERE ticket_id = %s",
            (*changed.values(), ticket_id),
        )

        # History: "Updated priority: Low -> High; title"
        parts = []
        for col in changed:
            if col in ("category", "priority"):
                parts.append(f"{col}: {current[col] or '-'} -> {changed[col]}")
            else:
                parts.append(col)
        note = ("Updated " + "; ".join(parts))[:255]

        activity_id = _next_id(cur, "ticket_activity", "activity_id", "A")
        cur.execute(
            """
            INSERT INTO ticket_activity (activity_id, ticket_id, note_action, old_status, new_status)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (activity_id, ticket_id, note, current["status"], current["status"]),
        )

    return list(changed)


# ---------------------------------------------------------------- AI suggestion

def save_ai_suggestion(ticket_id, category, priority, troubleshooting, tokens_used):
    """Insert or replace the AI suggestion for a ticket (one per ticket).
    Touches ONLY ai_suggestions — never the ticket's own category/priority/status."""
    with get_cursor() as cur:
        cur.execute(
            """
            INSERT INTO ai_suggestions
                (ticket_id, sugg_category, sugg_priority, troubleshooting, tokens_used, analyzed_at)
            VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (ticket_id) DO UPDATE SET
                sugg_category   = EXCLUDED.sugg_category,
                sugg_priority   = EXCLUDED.sugg_priority,
                troubleshooting = EXCLUDED.troubleshooting,
                tokens_used     = EXCLUDED.tokens_used,
                analyzed_at     = EXCLUDED.analyzed_at
            RETURNING sugg_category, sugg_priority, troubleshooting, tokens_used, analyzed_at
            """,
            (ticket_id, category, priority, troubleshooting, tokens_used),
        )
        return cur.fetchone()


# ---------------------------------------------------------------- AI feedback

def save_feedback(ticket_id, action, is_useful, final_category=None,
                  final_priority=None, note=None):
    """Staff accept or correct the AI suggestion, in ONE transaction:
    1. tickets         <- final category/priority (AI's if accepted, staff's if corrected)
    2. ai_feedback     <- useful/not useful + corrected values (one row per ticket)
    3. ticket_activity <- history row describing the decision
    Status is never changed here.
    Returns None if the ticket does not exist. Raises NoSuggestion if not analysed yet."""
    with get_cursor() as cur:
        cur.execute(
            "SELECT category, priority, status FROM tickets WHERE ticket_id = %s FOR UPDATE",
            (ticket_id,),
        )
        row = cur.fetchone()
        if row is None:
            return None
        ticket = dict(row)

        cur.execute(
            "SELECT sugg_category, sugg_priority FROM ai_suggestions WHERE ticket_id = %s",
            (ticket_id,),
        )
        sugg = cur.fetchone()
        if sugg is None:
            raise NoSuggestion(f"Ticket {ticket_id} has no AI suggestion yet. Run analyze first.")
        sugg = dict(sugg)

        # Final values: accept = AI's; correct = staff's (missing field keeps AI's)
        if action == "accept":
            final_cat, final_pri = sugg["sugg_category"], sugg["sugg_priority"]
            corrected_value = None
        else:
            final_cat = final_category or sugg["sugg_category"]
            final_pri = final_priority or sugg["sugg_priority"]
            corrected_value = f"Category: {final_cat}, Priority: {final_pri}"

        # 1. ticket
        cur.execute(
            "UPDATE tickets SET category = %s, priority = %s WHERE ticket_id = %s",
            (final_cat, final_pri, ticket_id),
        )

        # 2. feedback (replace earlier feedback for this ticket, if any)
        cur.execute(
            """
            INSERT INTO ai_feedback (ticket_id, is_useful, corrected_value, created_at)
            VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (ticket_id) DO UPDATE SET
                is_useful       = EXCLUDED.is_useful,
                corrected_value = EXCLUDED.corrected_value,
                created_at      = EXCLUDED.created_at
            """,
            (ticket_id, is_useful, corrected_value),
        )

        # 3. history: "AI suggestion corrected (category: Software -> Network; priority: Low -> Medium)"
        changes = []
        if ticket["category"] != final_cat:
            changes.append(f"category: {ticket['category'] or '-'} -> {final_cat}")
        if ticket["priority"] != final_pri:
            changes.append(f"priority: {ticket['priority'] or '-'} -> {final_pri}")
        note_action = f"AI suggestion {'accepted' if action == 'accept' else 'corrected'}"
        note_action += f" ({'; '.join(changes)})" if changes else " (no change)"

        _lock_ids(cur)
        activity_id = _next_id(cur, "ticket_activity", "activity_id", "A")
        cur.execute(
            """
            INSERT INTO ticket_activity
                (activity_id, ticket_id, note_action, old_status, new_status, comments)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (activity_id, ticket_id, note_action[:255], ticket["status"], ticket["status"], note),
        )

    return True


# ---------------------------------------------------------------- dashboard

def dashboard_summary():
    """Ticket counts for the support dashboard. Every known value is listed,
    even with count 0, so charts always have the same bars.
    Tickets with no priority/category yet are counted as 'Unassigned'."""
    def counts(cur, column, values):
        cur.execute(
            f"SELECT COALESCE({column}, 'Unassigned') AS k, COUNT(*) AS n "
            f"FROM tickets GROUP BY 1"
        )
        found = {r["k"]: r["n"] for r in cur.fetchall()}
        result = {v: found.pop(v, 0) for v in values}
        result.update(found)  # e.g. 'Unassigned' if present
        return result

    with get_cursor() as cur:
        cur.execute("SELECT COUNT(*) AS n FROM tickets")
        total = cur.fetchone()["n"]
        return {
            "total": total,
            "by_status": counts(cur, "status", ["New", "In Progress", "Resolved"]),
            "by_priority": counts(cur, "priority", ["High", "Medium", "Low"]),
            "by_category": counts(cur, "category", ["Hardware", "Software", "Network", "Access", "Other"]),
        }


# ---------------------------------------------------------------- activity

def add_activity(ticket_id, comment=None, new_status=None):
    """Support action on a ticket: add a comment, change status, or both.
    Writes one ticket_activity row (and updates tickets.status if changed).
    Returns None if the ticket does not exist.
    Raises InvalidTransition if the status move is not allowed."""
    with get_cursor() as cur:
        cur.execute(
            "SELECT status FROM tickets WHERE ticket_id = %s FOR UPDATE",
            (ticket_id,),
        )
        row = cur.fetchone()
        if row is None:
            return None
        old_status = dict(row)["status"]

        if new_status:
            if new_status not in ALLOWED_TRANSITIONS[old_status]:
                allowed = ", ".join(sorted(ALLOWED_TRANSITIONS[old_status])) or "none (ticket is closed)"
                raise InvalidTransition(
                    f"Cannot change status from '{old_status}' to '{new_status}'. "
                    f"Allowed next status: {allowed}"
                )
            cur.execute(
                "UPDATE tickets SET status = %s WHERE ticket_id = %s",
                (new_status, ticket_id),
            )
            note_action = f"Status changed to {new_status}"
        else:
            new_status = old_status
            note_action = "Support comment added"

        _lock_ids(cur)
        activity_id = _next_id(cur, "ticket_activity", "activity_id", "A")
        cur.execute(
            """
            INSERT INTO ticket_activity
                (activity_id, ticket_id, note_action, old_status, new_status, comments)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING activity_id, ticket_id, note_action, old_status, new_status,
                      comments, updated_at
            """,
            (activity_id, ticket_id, note_action, old_status, new_status, comment),
        )
        return cur.fetchone()
