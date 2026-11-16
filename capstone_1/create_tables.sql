-- ============================================================
-- AI-Powered Employee Helpdesk — Table Creation
-- ============================================================

DROP TABLE IF EXISTS ai_feedback;
DROP TABLE IF EXISTS ai_suggestions;
DROP TABLE IF EXISTS ticket_activity;
DROP TABLE IF EXISTS tickets;
DROP TABLE IF EXISTS requesters;
DROP TABLE IF EXISTS staff;
DROP TABLE IF EXISTS employees;

-- 1. EMPLOYEES (login table for employees who raise tickets)
CREATE TABLE employees (
    emp_id       SERIAL       PRIMARY KEY,
    emp_name     VARCHAR(100) NOT NULL,
    emp_email    VARCHAR(150) NOT NULL UNIQUE,
    emp_password VARCHAR(255) NOT NULL
);

-- 2. STAFF (login table for support staff who resolve tickets)
CREATE TABLE staff (
    staff_id     SERIAL       PRIMARY KEY,
    staff_name   VARCHAR(100) NOT NULL,
    staff_email  VARCHAR(150) NOT NULL UNIQUE,
    staff_password VARCHAR(255) NOT NULL
);

-- 3. REQUESTERS (linked to tickets)
CREATE TABLE requesters (
    req_id       VARCHAR(10)  PRIMARY KEY,
    req_name     VARCHAR(100) NOT NULL,
    req_email    VARCHAR(150) NOT NULL
);

-- 4. TICKETS
--    Added: status (spec requires it as a minimum field)
CREATE TABLE tickets (
    ticket_id    VARCHAR(10)  PRIMARY KEY,
    title        VARCHAR(200) NOT NULL,
    description  TEXT         NOT NULL,
    category     VARCHAR(20)  CHECK (category IN ('Hardware','Software','Network','Access','Other')),
    priority     VARCHAR(10)  CHECK (priority IN ('Low','Medium','High')),
    status       VARCHAR(20)  NOT NULL DEFAULT 'New' CHECK (status IN ('New','In Progress','Resolved')),
    req_id       VARCHAR(10)  NOT NULL REFERENCES requesters(req_id),
    created_at   TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 5. TICKET ACTIVITY
--    Added: old_status (spec says "old/new status where applicable")
--    Your single "Status" becomes "new_status" so both transitions are tracked
CREATE TABLE ticket_activity (
    activity_id  VARCHAR(10)  PRIMARY KEY,
    ticket_id    VARCHAR(10)  NOT NULL REFERENCES tickets(ticket_id),
    note_action  VARCHAR(255) NOT NULL,
    old_status   VARCHAR(20),
    new_status   VARCHAR(20)  NOT NULL,
    updated_at   TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    comments     TEXT
);

-- 6. AI SUGGESTIONS
CREATE TABLE ai_suggestions (
    ticket_id       VARCHAR(10)  NOT NULL REFERENCES tickets(ticket_id),
    sugg_category   VARCHAR(20),
    sugg_priority   VARCHAR(10),
    troubleshooting TEXT,
    tokens_used     INTEGER,
    analyzed_at     TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ticket_id)
);

-- 7. AI FEEDBACK
CREATE TABLE ai_feedback (
    ticket_id          VARCHAR(10)  NOT NULL REFERENCES tickets(ticket_id),
    is_useful          BOOLEAN      NOT NULL,
    corrected_value    TEXT,
    created_at         TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ticket_id)
);
