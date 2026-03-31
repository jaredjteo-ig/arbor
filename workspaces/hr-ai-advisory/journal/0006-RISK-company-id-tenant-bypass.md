---
type: RISK
date: 2026-03-31
created_at: 2026-03-31T18:45:00+08:00
author: agent
session_id: arbor-session-10
session_turn: 40
project: arbor
topic: Tenant isolation bypass via company_id in public registration
phase: redteam
tags: [security, tenant-isolation, registration, critical]
---

# CRITICAL: Tenant Isolation Bypass via company_id in Public Registration

## Risk

The `/auth/register` endpoint accepted an arbitrary `company_id` integer from the request body. An attacker could register with `{"company_id": 1}` to join any existing company and gain access to all its data — employees, payroll, leave, claims, attendance.

## Impact

Full tenant data breach. The company_id was baked into the JWT, granting the attacker the same data access as a legitimate company owner. No additional authentication required beyond a valid email/password.

## Fix

Removed `company_id` from public registration entirely. The only paths to join an existing company are:

1. Invitation flow (`/register-employee`) — requires a pre-existing invitation token
2. Creating a new company via `company_name` — links only to the newly created company

A 255-character length limit was also added to `company_name` to prevent DoS.

## Root Cause

The original registration endpoint was designed for flexibility (admin creating users with pre-assigned companies). When the endpoint became public-facing, the `company_id` parameter was never locked down. SSO was the primary auth path, so registration security received less scrutiny.

## For Discussion

1. If the `company_id` parameter had been validated against the user's existing access (e.g., only admins of company X can assign users to X), would that have been a better design than removing it entirely?
2. The service method `register_user()` still accepts `company_id` for internal use (e.g., invitation flow calls it). Should internal callers also be audited to ensure they validate the company_id?
