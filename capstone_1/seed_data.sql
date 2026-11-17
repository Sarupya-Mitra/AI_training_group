-- ============================================================
-- AI-Powered Employee Helpdesk — Seed Data
-- Run AFTER create_tables.sql
-- ============================================================

-- 1. EMPLOYEES (who raise tickets)
INSERT INTO employees (emp_name, emp_email, emp_password) VALUES
('Amit Sharma',    'amit.sharma@company.com',    'pass123'),
('Priya Nair',     'priya.nair@company.com',     'pass123'),
('Rahul Verma',    'rahul.verma@company.com',    'pass123'),
('Sneha Iyer',     'sneha.iyer@company.com',     'pass123'),
('Vikram Patel',   'vikram.patel@company.com',   'pass123'),
('Deepa Krishnan', 'deepa.krishnan@company.com', 'pass123'),
('Arjun Menon',    'arjun.menon@company.com',    'pass123'),
('Kavitha Rajan',  'kavitha.rajan@company.com',  'pass123'),
('Suresh Babu',    'suresh.babu@company.com',    'pass123'),
('Meera Joshi',    'meera.joshi@company.com',    'pass123');

-- 2. STAFF (who resolve tickets)
INSERT INTO staff (staff_name, staff_email, staff_password) VALUES
('Ravi Kumar',     'ravi.kumar@company.com',     'staff123'),
('Anita Das',      'anita.das@company.com',      'staff123'),
('Kiran Rao',      'kiran.rao@company.com',      'staff123');

-- 3. REQUESTERS
INSERT INTO requesters (req_id, req_name, req_email) VALUES
('R1001', 'Amit Sharma',    'amit.sharma@company.com'),
('R1002', 'Priya Nair',     'priya.nair@company.com'),
('R1003', 'Rahul Verma',    'rahul.verma@company.com'),
('R1004', 'Sneha Iyer',     'sneha.iyer@company.com'),
('R1005', 'Vikram Patel',   'vikram.patel@company.com'),
('R1006', 'Deepa Krishnan', 'deepa.krishnan@company.com'),
('R1007', 'Arjun Menon',    'arjun.menon@company.com'),
('R1008', 'Kavitha Rajan',  'kavitha.rajan@company.com'),
('R1009', 'Suresh Babu',    'suresh.babu@company.com'),
('R1010', 'Meera Joshi',    'meera.joshi@company.com');

-- 4. TICKETS
INSERT INTO tickets (ticket_id, title, description, category, priority, status, req_id, created_at) VALUES
('T101', 'Wireless keyboard not responding',
 'My wireless keyboard stopped working this morning. Replaced batteries but still no response. USB receiver is plugged in.',
 'Hardware', 'Medium', 'New', 'R1001', '2026-11-16 10:00:00'),

('T102', 'Department-wide file sharing outage',
 'Entire Finance department cannot access shared drive since 9:30 AM. Around 40 users affected. Quarter-end reporting blocked.',
 'Network', 'High', 'New', 'R1002', '2026-11-16 09:35:00'),

('T103', 'Cannot connect to VPN from home',
 'VPN client shows authentication failed when connecting remotely. Password was reset yesterday. Other internet sites work fine.',
 'Network', 'Medium', 'In Progress', 'R1003', '2026-11-15 14:20:00'),

('T104', 'New laptop setup for onboarding',
 'New joiner starting 20-Nov needs laptop with standard software suite, email, and VPN access configured.',
 'Hardware', 'Medium', 'New', 'R1004', '2026-11-15 11:00:00'),

('T105', 'Outlook calendar sync broken',
 'Outlook not syncing calendar events with mobile phone. Tried removing and re-adding the account.',
 'Software', 'Low', 'New', 'R1005', '2026-11-15 16:45:00'),

('T106', 'Access request for SAP module',
 'Need read access to SAP FI module for month-end reconciliation. Manager approval attached. Needed before 18-Nov.',
 'Access', 'High', 'In Progress', 'R1006', '2026-11-14 09:15:00'),

('T107', 'Monitor flickering intermittently',
 'Desk monitor flickers every few minutes. Started after the weekend. Using DisplayPort cable.',
 'Hardware', 'Low', 'New', 'R1007', '2026-11-16 08:30:00'),

('T108', 'Excel crashes on large files',
 'Excel 365 crashes when opening files over 50 MB. Error: Not enough memory. Laptop has 16 GB RAM.',
 'Software', 'Medium', 'Resolved', 'R1008', '2026-11-13 10:00:00'),

('T109', 'Wi-Fi keeps dropping in Building B',
 'Wi-Fi disconnects every 15-20 minutes on 3rd floor of Building B. Multiple colleagues report the same.',
 'Network', 'High', 'In Progress', 'R1009', '2026-11-14 13:00:00'),

('T110', 'Password reset for ERP system',
 'Locked out of ERP portal after too many failed attempts. Need a reset. Employee ID: E4429.',
 'Access', 'Low', 'Resolved', 'R1010', '2026-11-13 08:00:00');

-- 5. TICKET ACTIVITY
INSERT INTO ticket_activity (activity_id, ticket_id, note_action, old_status, new_status, updated_at, comments) VALUES
('A1001', 'T101', 'Ticket created',              NULL,          'New',         '2026-11-16 10:00:00', NULL),
('A1002', 'T102', 'Ticket created',              NULL,          'New',         '2026-11-16 09:35:00', 'URGENT — 40 users affected'),
('A1003', 'T103', 'Ticket created',              NULL,          'New',         '2026-11-15 14:20:00', NULL),
('A1004', 'T103', 'Assigned to Network team',    'New',         'In Progress', '2026-11-15 14:45:00', 'Checking AD sync for password reset'),
('A1005', 'T104', 'Ticket created',              NULL,          'New',         '2026-11-15 11:00:00', 'Onboarding date: 20-Nov'),
('A1006', 'T105', 'Ticket created',              NULL,          'New',         '2026-11-15 16:45:00', NULL),
('A1007', 'T106', 'Ticket created',              NULL,          'New',         '2026-11-14 09:15:00', NULL),
('A1008', 'T106', 'Manager approval verified',   'New',         'In Progress', '2026-11-14 10:30:00', 'Provisioning FI read role'),
('A1009', 'T107', 'Ticket created',              NULL,          'New',         '2026-11-16 08:30:00', NULL),
('A1010', 'T108', 'Ticket created',              NULL,          'New',         '2026-11-13 10:00:00', NULL),
('A1011', 'T108', 'Investigating memory usage',  'New',         'In Progress', '2026-11-13 11:00:00', '32-bit Office installed'),
('A1012', 'T108', 'Reinstalled Office 64-bit',   'In Progress', 'Resolved',    '2026-11-13 15:30:00', 'User confirmed fix'),
('A1013', 'T109', 'Ticket created',              NULL,          'New',         '2026-11-14 13:00:00', NULL),
('A1014', 'T109', 'Escalated to infra team',     'New',         'In Progress', '2026-11-14 14:00:00', 'AP channel interference on 3rd floor'),
('A1015', 'T110', 'Ticket created',              NULL,          'New',         '2026-11-13 08:00:00', NULL),
('A1016', 'T110', 'Verifying employee identity', 'New',         'In Progress', '2026-11-13 08:15:00', 'Security questions verified'),
('A1017', 'T110', 'Password reset completed',    'In Progress', 'Resolved',    '2026-11-13 08:30:00', 'Temp password sent');

-- 6. AI SUGGESTIONS
INSERT INTO ai_suggestions (ticket_id, sugg_category, sugg_priority, troubleshooting, tokens_used, analyzed_at) VALUES
('T101', 'Hardware', 'Medium',
 'Try different USB port. Check Device Manager. Re-pair keyboard with receiver. Test on another PC.',
 285, '2026-11-16 10:01:00'),

('T102', 'Network', 'High',
 'Check SMB service on file server. Run nslookup. Review firewall changes. Engage infra team immediately.',
 342, '2026-11-16 09:36:00'),

-- INTENTIONALLY WRONG for demo scenario 03 (human correction)
('T103', 'Software', 'Low',
 'Reinstall VPN client. Clear saved credentials. Restart computer.',
 198, '2026-11-15 14:22:00'),

('T104', 'Hardware', 'Medium',
 'Allocate laptop from inventory. Image with standard build. Install Office, VPN, browser. Configure email.',
 267, '2026-11-15 11:02:00'),

('T105', 'Software', 'Low',
 'Remove and re-add Outlook account on mobile. Enable background app refresh. Check mailbox quota.',
 231, '2026-11-15 16:47:00'),

('T106', 'Access', 'High',
 'Confirm manager approval. Assign SAP role via SU01. Run user comparison. Verify FI transactions.',
 254, '2026-11-14 09:17:00'),

('T107', 'Hardware', 'Low',
 'Try different cable. Test monitor on another PC. Update graphics driver. Lower refresh rate to 60 Hz.',
 219, '2026-11-16 08:32:00'),

('T108', 'Software', 'Medium',
 'Check if 32-bit Office installed. Reinstall as 64-bit. Disable unnecessary add-ins.',
 241, '2026-11-13 10:02:00');

-- 7. AI FEEDBACK
INSERT INTO ai_feedback (ticket_id, is_useful, corrected_value, created_at) VALUES
-- Staff corrected wrong AI suggestion for T103
('T103', FALSE, 'Category: Network, Priority: Medium', '2026-11-15 14:50:00'),
-- Staff accepted AI suggestion for T106
('T106', TRUE,  NULL, '2026-11-14 10:35:00'),
-- Staff accepted AI suggestion for T108
('T108', TRUE,  NULL, '2026-11-13 11:05:00');
