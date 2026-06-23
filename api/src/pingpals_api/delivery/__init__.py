"""Delivery worker (stub).

Sends reminders to the user via email, in-app/push, SMS, WhatsApp, and Signal, each behind a
per-channel sender interface. Re-verifies reminder ownership and endpoint ownership at send time,
requires per-channel consent, and fails closed on any mismatch. Minimal/confidentiality-aware
payload; bounded retries + dead-letter.
Tags: FR-5.4, FR-5.6, FR-6.x, INT-5.x, NFR-1.2. Implementation tracked in issues 035-044.
"""
