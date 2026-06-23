"""Scheduler service (stub).

Per-user cadence evaluation; emits a reminder when now - last_contacted >= effective_cadence AND
within send window AND channel consent present AND no active snooze. Idempotent generation, fails
closed on unknown timezone, caps reminders per user per window.
Tags: FR-3.x, FR-5.1, FR-5.2, NFR-1.1, SEC-6.2. Implementation tracked in issues 031-034.
"""
