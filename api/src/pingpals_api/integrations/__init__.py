"""Integration adapters (stub).

Least-privilege OAuth / scoped-credential adapters: contacts read (Google People, Microsoft Graph,
CardDAV, Apple/iCloud CardDAV), Google Calendar read-only free/busy, Gmail metadata-only
last-contact detection (opt-in, default off), transactional email, SMS, WhatsApp, Signal. Each is
isolated and independently revocable; tokens/credentials are purged on disconnect and erasure.

Each adapter declares a pinned least-privilege scope set; a flow requesting any scope outside it
fails closed. Concrete providers behind `TO BE DECIDED` choices (SMS provider, email provider)
stay behind the adapter interface.
Tags: FR-1.5, FR-4.3/4.4, INT-1.7, INT-2.x, INT-3.1, INT-4.x, INT-5.x, SEC-3.3.
"""
