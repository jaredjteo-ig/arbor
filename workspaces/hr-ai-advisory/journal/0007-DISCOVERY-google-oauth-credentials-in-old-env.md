---
type: DISCOVERY
date: 2026-03-31
created_at: 2026-03-31T19:45:00+08:00
author: agent
session_id: arbor-session-10
session_turn: 60
project: arbor
topic: Google OAuth credentials existed in deploy/.env.prod but were lost during .env rewrite
phase: redteam
tags: [google-oauth, deployment, credentials, env-management]
---

# Google OAuth Credentials Were in deploy/.env.prod All Along

## Discovery

During the M60 deployment, the production `.env` was recreated from flat credential files (.db-password, .jwt-secret, etc.) to fix a Redis startup failure. The Google OAuth credentials were NOT in the flat files — they were only in the older `deploy/.env.prod` file. This caused Google SSO to silently stop working.

The credentials were found at `/opt/arbor/deploy/.env.prod`:

- `GOOGLE_OAUTH_CLIENT_ID=129371016531-...apps.googleusercontent.com`
- `GOOGLE_OAUTH_CLIENT_SECRET=GOCSPX-...`
- `GOOGLE_OAUTH_REDIRECT_URI=https://arbor.terrene.foundation/auth/callback`

## Root Cause

The production server had two `.env` lineages:

1. `deploy/.env.prod` — the original production env with ALL credentials including Google OAuth
2. `/opt/arbor/.env` — the newer root-level env that the compose file reads, created from flat files

When the root `.env` was regenerated, it sourced only from the flat files (which didn't include Google credentials). The `deploy/.env.prod` was never consulted.

## Fix

Restored Google OAuth credentials to `/opt/arbor/.env`. Rebuilt frontend with `NEXT_PUBLIC_GOOGLE_CLIENT_ID` baked into the bundle. Verified via Playwright: clicking "Sign in with Google" redirects to Google's OAuth consent screen with correct client_id and redirect_uri.

## For Discussion

1. The server now has credentials split across flat files AND the `.env` — should all credentials be consolidated into `.env` as the single source?
2. The `deploy/.env.prod` file has a different DB password than the current `.env` — this suggests the DB was rotated at some point. Should the old file be deleted to avoid confusion?
