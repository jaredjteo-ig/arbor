#!/usr/bin/env python3
"""Seed demo data for Arbor HRIS platform via the REST API.

Creates a realistic company (Central Solutions Pte Ltd) with 25-30 employees,
salary components, payroll history, leave applications, expense claims,
attendance records, and recruitment pipeline data.

Designed to be run before every demo. Idempotent — checks if resources
exist before creating them.

Usage (full seed, fresh DB):
    python scripts/seed_demo_data.py

Usage (round-13 demo refresh against existing prod company):
    ARBOR_API_URL=https://central.kailash.ai/api \\
    ADMIN_EMAIL=demo@central.kailash.ai \\
    ADMIN_PASSWORD='<actual prod password>' \\
    python scripts/seed_demo_data.py --section demo-refresh

Usage (list available sections):
    python scripts/seed_demo_data.py --list-sections

Usage (dry-run — show what would run, do not mutate):
    python scripts/seed_demo_data.py --section demo-refresh --dry-run

Environment:
    ARBOR_API_URL    — Base URL for the Arbor API (default: http://localhost:8000)
    ADMIN_EMAIL      — Admin user email (default: demo@central.kailash.ai)
    ADMIN_PASSWORD   — Admin user password (default: CentralDemo2026!)
                       Required to differ from default for prod runs.
    DATABASE_URL     — Postgres URL for direct-DB sections (round-13 refresh).
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from datetime import date, datetime, timedelta
from typing import Any, Callable

import httpx

try:
    from dotenv import load_dotenv  # type: ignore

    load_dotenv()
except Exception:
    pass

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_API_URL = os.environ.get("ARBOR_API_URL", "http://localhost:8000")
DEFAULT_EMAIL = os.environ.get("ADMIN_EMAIL", "demo@central.kailash.ai")
DEFAULT_PASSWORD = os.environ.get("ADMIN_PASSWORD", "CentralDemo2026!")
DEFAULT_COMPANY = os.environ.get("DEMO_COMPANY_NAME", "Central Solutions Pte Ltd")
DEFAULT_EMPLOYEE_COUNT = int(os.environ.get("DEMO_EMPLOYEE_COUNT", "28"))

REQUEST_TIMEOUT = 120.0

# Retry configuration for transient connection issues. Connection-reset (ECONNRESET)
# from the backend's saturated DataFlow pool was the #1 cause of seed failures
# (observed 4× in a single session). Backoff is exponential, jittered.
RETRY_MAX_ATTEMPTS = int(os.environ.get("SEED_RETRY_MAX_ATTEMPTS", "5"))
RETRY_INITIAL_DELAY = float(os.environ.get("SEED_RETRY_INITIAL_DELAY", "2.0"))
RETRY_MAX_DELAY = float(os.environ.get("SEED_RETRY_MAX_DELAY", "30.0"))

# ---------------------------------------------------------------------------
# Employee profiles — realistic Singapore SME workforce
# ---------------------------------------------------------------------------

EMPLOYEE_PROFILES: list[dict[str, Any]] = [
    # Management (2)
    {
        "name": "Tanaka Hiroshi",
        "email": "hiroshi.tanaka@central-solutions.sg",
        "department": "Management",
        "designation": "Managing Director",
        "gender": "male",
        "race": "other",
        "nationality": "Japanese",
        "pass_type": "ep",
        "immigration_status": "foreigner",
        "salary_monthly": 12000.0,
        "employment_type": "full_time",
        "start_date": "2021-03-01",
        "confirmation_status": "confirmed",
        "work_pass_expiry": "2027-06-30",
    },
    {
        "name": "Lim Mei Ling",
        "email": "meiling.lim@central-solutions.sg",
        "department": "Management",
        "designation": "Operations Director",
        "gender": "female",
        "race": "chinese",
        "nationality": "Singaporean",
        "pass_type": "citizen",
        "immigration_status": "citizen",
        "salary_monthly": 10000.0,
        "employment_type": "full_time",
        "start_date": "2021-06-15",
        "confirmation_status": "confirmed",
    },
    # Engineering (7)
    {
        "name": "Rajesh Kumar",
        "email": "rajesh.kumar@central-solutions.sg",
        "department": "Engineering",
        "designation": "Engineering Manager",
        "gender": "male",
        "race": "indian",
        "nationality": "Singaporean",
        "pass_type": "citizen",
        "immigration_status": "citizen",
        "salary_monthly": 9500.0,
        "employment_type": "full_time",
        "start_date": "2022-01-10",
        "confirmation_status": "confirmed",
    },
    {
        "name": "Chen Wei",
        "email": "wei.chen@central-solutions.sg",
        "department": "Engineering",
        "designation": "Senior Software Engineer",
        "gender": "male",
        "race": "chinese",
        "nationality": "Singaporean",
        "pass_type": "citizen",
        "immigration_status": "citizen",
        "salary_monthly": 8000.0,
        "employment_type": "full_time",
        "start_date": "2022-04-01",
        "confirmation_status": "confirmed",
    },
    {
        "name": "Priya Nair",
        "email": "priya.nair@central-solutions.sg",
        "department": "Engineering",
        "designation": "Software Engineer",
        "gender": "female",
        "race": "indian",
        "nationality": "Singaporean",
        "pass_type": "citizen",
        "immigration_status": "citizen",
        "salary_monthly": 6500.0,
        "employment_type": "full_time",
        "start_date": "2023-02-15",
        "confirmation_status": "confirmed",
    },
    {
        "name": "Nguyen Thanh",
        "email": "thanh.nguyen@central-solutions.sg",
        "department": "Engineering",
        "designation": "Software Engineer",
        "gender": "male",
        "race": "other",
        "nationality": "Vietnamese",
        "pass_type": "sp",
        "immigration_status": "foreigner",
        "salary_monthly": 5500.0,
        "employment_type": "full_time",
        "start_date": "2023-08-01",
        "confirmation_status": "confirmed",
        # Computed at seed-run time so the "Work Pass Expiring Soon"
        # filter on /employees always has a fresh entry to surface,
        # regardless of when the seed is re-run (P4-QW-7 audit).
        "work_pass_expiry": (date.today() + timedelta(days=45)).isoformat(),
    },
    {
        "name": "Ahmad Bin Ismail",
        "email": "ahmad.ismail@central-solutions.sg",
        "department": "Engineering",
        "designation": "QA Engineer",
        "gender": "male",
        "race": "malay",
        "nationality": "Malaysian",
        "pass_type": "sp",
        "immigration_status": "foreigner",
        "salary_monthly": 4800.0,
        "employment_type": "full_time",
        "start_date": "2024-01-08",
        "confirmation_status": "confirmed",
        # Slightly further out than Nguyen's so the filter shows a
        # graduated set (P4-QW-7).
        "work_pass_expiry": (date.today() + timedelta(days=75)).isoformat(),
    },
    {
        "name": "Sato Yuki",
        "email": "yuki.sato@central-solutions.sg",
        "department": "Engineering",
        "designation": "DevOps Engineer",
        "gender": "female",
        "race": "other",
        "nationality": "Japanese",
        "pass_type": "ep",
        "immigration_status": "foreigner",
        "salary_monthly": 7000.0,
        "employment_type": "full_time",
        "start_date": "2023-06-01",
        "confirmation_status": "confirmed",
        "work_pass_expiry": "2027-12-31",
    },
    {
        "name": "Marcus Tan",
        "email": "marcus.tan@central-solutions.sg",
        "department": "Engineering",
        "designation": "Junior Developer",
        "gender": "male",
        "race": "chinese",
        "nationality": "Singaporean",
        "pass_type": "citizen",
        "immigration_status": "citizen",
        "salary_monthly": 4000.0,
        "employment_type": "full_time",
        "start_date": "2026-01-06",
        "confirmation_status": "on_probation",
        "probation_months": 6,
        "probation_end_date": "2026-07-06",
    },
    # Sales (5)
    {
        "name": "Sarah Wong",
        "email": "sarah.wong@central-solutions.sg",
        "department": "Sales",
        "designation": "Sales Manager",
        "gender": "female",
        "race": "chinese",
        "nationality": "Singaporean",
        "pass_type": "citizen",
        "immigration_status": "citizen",
        "salary_monthly": 7500.0,
        "employment_type": "full_time",
        "start_date": "2021-09-01",
        "confirmation_status": "confirmed",
    },
    {
        "name": "David Lee",
        "email": "david.lee@central-solutions.sg",
        "department": "Sales",
        "designation": "Senior Sales Executive",
        "gender": "male",
        "race": "chinese",
        "nationality": "Singaporean",
        "pass_type": "citizen",
        "immigration_status": "citizen",
        "salary_monthly": 5500.0,
        "employment_type": "full_time",
        "start_date": "2022-07-01",
        "confirmation_status": "confirmed",
    },
    {
        "name": "Nurul Huda",
        "email": "nurul.huda@central-solutions.sg",
        "department": "Sales",
        "designation": "Sales Executive",
        "gender": "female",
        "race": "malay",
        "nationality": "Singaporean",
        "pass_type": "citizen",
        "immigration_status": "citizen",
        "salary_monthly": 4200.0,
        "employment_type": "full_time",
        "start_date": "2024-03-01",
        "confirmation_status": "confirmed",
    },
    {
        "name": "Arun Sharma",
        "email": "arun.sharma@central-solutions.sg",
        "department": "Sales",
        "designation": "Sales Executive",
        "gender": "male",
        "race": "indian",
        "nationality": "Indian",
        "pass_type": "sp",
        "immigration_status": "foreigner",
        "salary_monthly": 4000.0,
        "employment_type": "full_time",
        "start_date": "2024-06-01",
        "confirmation_status": "confirmed",
        "work_pass_expiry": "2027-05-31",
    },
    {
        "name": "Jessica Ong",
        "email": "jessica.ong@central-solutions.sg",
        "department": "Sales",
        "designation": "Business Development",
        "gender": "female",
        "race": "chinese",
        "nationality": "Singaporean",
        "pass_type": "citizen",
        "immigration_status": "citizen",
        "salary_monthly": 5000.0,
        "employment_type": "full_time",
        "start_date": "2023-11-01",
        "confirmation_status": "confirmed",
    },
    # Operations (5)
    {
        "name": "Muhammad Rizwan",
        "email": "rizwan.muhammad@central-solutions.sg",
        "department": "Operations",
        "designation": "Operations Manager",
        "gender": "male",
        "race": "malay",
        "nationality": "Singaporean",
        "pass_type": "pr",
        "immigration_status": "pr_year3_plus",
        "salary_monthly": 6800.0,
        "employment_type": "full_time",
        "start_date": "2022-03-01",
        "confirmation_status": "confirmed",
    },
    {
        "name": "Lim Ah Kow",
        "email": "ahkow.lim@central-solutions.sg",
        "department": "Operations",
        "designation": "Warehouse Supervisor",
        "gender": "male",
        "race": "chinese",
        "nationality": "Singaporean",
        "pass_type": "citizen",
        "immigration_status": "citizen",
        "salary_monthly": 3800.0,
        "employment_type": "full_time",
        "start_date": "2023-01-09",
        "confirmation_status": "confirmed",
    },
    {
        "name": "Siti Aminah",
        "email": "siti.aminah@central-solutions.sg",
        "department": "Operations",
        "designation": "Logistics Coordinator",
        "gender": "female",
        "race": "malay",
        "nationality": "Malaysian",
        "pass_type": "wp",
        "immigration_status": "foreigner",
        "salary_monthly": 2500.0,
        "employment_type": "full_time",
        "start_date": "2024-04-01",
        "confirmation_status": "confirmed",
        "work_pass_expiry": "2027-03-31",
    },
    {
        "name": "Ravi Shankar",
        "email": "ravi.shankar@central-solutions.sg",
        "department": "Operations",
        "designation": "Warehouse Assistant",
        "gender": "male",
        "race": "indian",
        "nationality": "Indian",
        "pass_type": "wp",
        "immigration_status": "foreigner",
        "salary_monthly": 2500.0,
        "employment_type": "full_time",
        "start_date": "2024-07-15",
        "confirmation_status": "confirmed",
        "work_pass_expiry": "2027-07-14",
    },
    {
        "name": "Kevin Teo",
        "email": "kevin.teo@central-solutions.sg",
        "department": "Operations",
        "designation": "Operations Executive",
        "gender": "male",
        "race": "chinese",
        "nationality": "Singaporean",
        "pass_type": "citizen",
        "immigration_status": "citizen",
        "salary_monthly": 3500.0,
        "employment_type": "full_time",
        "start_date": "2024-09-01",
        "confirmation_status": "confirmed",
    },
    # Finance (4)
    {
        "name": "Angela Chua",
        "email": "angela.chua@central-solutions.sg",
        "department": "Finance",
        "designation": "Finance Manager",
        "gender": "female",
        "race": "chinese",
        "nationality": "Singaporean",
        "pass_type": "citizen",
        "immigration_status": "citizen",
        "salary_monthly": 8500.0,
        "employment_type": "full_time",
        "start_date": "2021-11-01",
        "confirmation_status": "confirmed",
    },
    {
        "name": "Tan Boon Heng",
        "email": "boonheng.tan@central-solutions.sg",
        "department": "Finance",
        "designation": "Accountant",
        "gender": "male",
        "race": "chinese",
        "nationality": "Singaporean",
        "pass_type": "citizen",
        "immigration_status": "citizen",
        "salary_monthly": 5000.0,
        "employment_type": "full_time",
        "start_date": "2023-04-01",
        "confirmation_status": "confirmed",
    },
    {
        "name": "Deepa Menon",
        "email": "deepa.menon@central-solutions.sg",
        "department": "Finance",
        "designation": "Accounts Executive",
        "gender": "female",
        "race": "indian",
        "nationality": "Singaporean",
        "pass_type": "pr",
        "immigration_status": "pr_year2",
        "salary_monthly": 4200.0,
        "employment_type": "full_time",
        "start_date": "2024-02-01",
        "confirmation_status": "confirmed",
    },
    {
        "name": "Jason Ng",
        "email": "jason.ng@central-solutions.sg",
        "department": "Finance",
        "designation": "Junior Accountant",
        "gender": "male",
        "race": "chinese",
        "nationality": "Singaporean",
        "pass_type": "citizen",
        "immigration_status": "citizen",
        "salary_monthly": 3600.0,
        "employment_type": "full_time",
        "start_date": "2025-11-01",
        "confirmation_status": "on_probation",
        "probation_months": 3,
        "probation_end_date": "2026-02-01",
    },
    # HR (3)
    {
        "name": "Grace Koh",
        "email": "grace.koh@central-solutions.sg",
        "department": "HR",
        "designation": "HR Manager",
        "gender": "female",
        "race": "chinese",
        "nationality": "Singaporean",
        "pass_type": "citizen",
        "immigration_status": "citizen",
        "salary_monthly": 7000.0,
        "employment_type": "full_time",
        "start_date": "2022-02-01",
        "confirmation_status": "confirmed",
    },
    {
        "name": "Faizal Rahman",
        "email": "faizal.rahman@central-solutions.sg",
        "department": "HR",
        "designation": "HR Executive",
        "gender": "male",
        "race": "malay",
        "nationality": "Singaporean",
        "pass_type": "citizen",
        "immigration_status": "citizen",
        "salary_monthly": 4500.0,
        "employment_type": "full_time",
        "start_date": "2023-07-01",
        "confirmation_status": "confirmed",
    },
    {
        "name": "Linda Tan",
        "email": "linda.tan@central-solutions.sg",
        "department": "HR",
        "designation": "HR Assistant",
        "gender": "female",
        "race": "chinese",
        "nationality": "Singaporean",
        "pass_type": "citizen",
        "immigration_status": "citizen",
        "salary_monthly": 3200.0,
        "employment_type": "part_time",
        "start_date": "2024-10-01",
        "confirmation_status": "confirmed",
    },
    # Additional — to pad to target count (2)
    {
        "name": "Samuel Goh",
        "email": "samuel.goh@central-solutions.sg",
        "department": "Engineering",
        "designation": "Full-Stack Developer",
        "gender": "male",
        "race": "chinese",
        "nationality": "Singaporean",
        "pass_type": "citizen",
        "immigration_status": "citizen",
        "salary_monthly": 6000.0,
        "employment_type": "full_time",
        "start_date": "2023-09-15",
        "confirmation_status": "confirmed",
    },
    {
        "name": "Lily Phang",
        "email": "lily.phang@central-solutions.sg",
        "department": "Sales",
        "designation": "Account Manager",
        "gender": "female",
        "race": "chinese",
        "nationality": "Singaporean",
        "pass_type": "citizen",
        "immigration_status": "citizen",
        "salary_monthly": 5200.0,
        "employment_type": "full_time",
        "start_date": "2023-05-01",
        "confirmation_status": "confirmed",
    },
]

# ---------------------------------------------------------------------------
# Leave application templates
# ---------------------------------------------------------------------------

LEAVE_APPLICATIONS = [
    # Approved annual leave (past)
    {
        "employee_idx": 3,  # Chen Wei
        "leave_type_code": "annual",
        "start_date": "2026-02-09",
        "end_date": "2026-02-13",
        "reason": "Family holiday to Hokkaido",
        "action": "approve",
    },
    # Approved sick leave (past)
    {
        "employee_idx": 11,  # Nurul Huda
        "leave_type_code": "sick",
        "start_date": "2026-03-03",
        "end_date": "2026-03-04",
        "reason": "Flu and fever — MC attached",
        "action": "approve",
    },
    # Pending annual leave (future)
    {
        "employee_idx": 5,  # Priya Nair
        "leave_type_code": "annual",
        "start_date": "2026-04-14",
        "end_date": "2026-04-18",
        "reason": "Visiting family in Chennai",
        "action": "pending",
    },
    # Approved annual leave (past)
    {
        "employee_idx": 9,  # Sarah Wong
        "leave_type_code": "annual",
        "start_date": "2026-01-20",
        "end_date": "2026-01-24",
        "reason": "Chinese New Year extended break",
        "action": "approve",
    },
    # Rejected leave
    {
        "employee_idx": 10,  # David Lee
        "leave_type_code": "annual",
        "start_date": "2026-03-30",
        "end_date": "2026-04-03",
        "reason": "Personal trip",
        "action": "reject",
        "reject_reason": "Clashes with Q1 sales close — please reschedule to April.",
    },
    # Pending sick leave
    {
        "employee_idx": 16,  # Lim Ah Kow
        "leave_type_code": "sick",
        "start_date": "2026-03-24",
        "end_date": "2026-03-24",
        "reason": "Back pain — seeing specialist",
        "action": "pending",
    },
    # Maternity leave (approved, longer duration)
    {
        "employee_idx": 25,  # Grace Koh
        "leave_type_code": "maternity",
        "start_date": "2026-05-01",
        "end_date": "2026-08-20",
        "reason": "Maternity leave — expected delivery May 2026",
        "action": "approve",
    },
    # Pending annual leave
    {
        "employee_idx": 22,  # Deepa Menon
        "leave_type_code": "annual",
        "start_date": "2026-04-07",
        "end_date": "2026-04-09",
        "reason": "Moving to new flat",
        "action": "pending",
    },
    # Approved childcare leave
    {
        "employee_idx": 14,  # Muhammad Rizwan
        "leave_type_code": "childcare",
        "start_date": "2026-03-17",
        "end_date": "2026-03-18",
        "reason": "Child unwell, need to accompany to hospital",
        "action": "approve",
    },
    # Approved annual leave — long service employee
    {
        "employee_idx": 20,  # Angela Chua
        "leave_type_code": "annual",
        "start_date": "2026-03-10",
        "end_date": "2026-03-14",
        "reason": "Annual family vacation",
        "action": "approve",
    },
]

# ---------------------------------------------------------------------------
# Expense claim templates
# ---------------------------------------------------------------------------

EXPENSE_CLAIMS = [
    {
        "employee_idx": 10,  # David Lee — Sales
        "claim_month": "2026-03",
        "items": [
            {"category": "Transport", "amount": 45.50, "description": "Grab to client meeting — Jurong East", "receipt_date": "2026-03-05"},
            {"category": "Transport", "amount": 38.00, "description": "Grab to partner office — CBD", "receipt_date": "2026-03-12"},
            {"category": "Meals", "amount": 65.00, "description": "Client lunch — Din Tai Fung", "receipt_date": "2026-03-12"},
        ],
        "action": "submit",
    },
    {
        "employee_idx": 9,  # Sarah Wong — Sales Manager
        "claim_month": "2026-02",
        "items": [
            {"category": "Transport", "amount": 120.00, "description": "Monthly parking at client site", "receipt_date": "2026-02-28"},
            {"category": "Meals", "amount": 89.00, "description": "Team dinner — Q1 kick-off", "receipt_date": "2026-02-15"},
        ],
        "action": "approve",
    },
    {
        "employee_idx": 5,  # Priya Nair — Engineering
        "claim_month": "2026-03",
        "items": [
            {"category": "Medical", "amount": 55.00, "description": "GP visit — flu symptoms", "receipt_date": "2026-03-03"},
        ],
        "action": "submit",
    },
    {
        "employee_idx": 14,  # Muhammad Rizwan — Operations
        "claim_month": "2026-03",
        "items": [
            {"category": "Transport", "amount": 32.00, "description": "Grab to warehouse — Tuas", "receipt_date": "2026-03-10"},
            {"category": "Transport", "amount": 28.50, "description": "Grab to warehouse — Tuas", "receipt_date": "2026-03-17"},
        ],
        "action": "submit",
    },
    {
        "employee_idx": 3,  # Chen Wei — Engineering
        "claim_month": "2026-02",
        "items": [
            {"category": "Medical", "amount": 120.00, "description": "Dental checkup and cleaning", "receipt_date": "2026-02-20"},
            {"category": "Transport", "amount": 15.80, "description": "MRT top-up for office commute", "receipt_date": "2026-02-10"},
        ],
        "action": "approve",
    },
    {
        "employee_idx": 0,  # Tanaka Hiroshi — MD
        "claim_month": "2026-03",
        "items": [
            {"category": "Meals", "amount": 185.00, "description": "Client dinner — Odette restaurant", "receipt_date": "2026-03-08"},
            {"category": "Transport", "amount": 55.00, "description": "Airport transfer — Changi T3", "receipt_date": "2026-03-15"},
        ],
        "action": "draft",
    },
]

# ---------------------------------------------------------------------------
# Recruitment data
# ---------------------------------------------------------------------------

JOB_POSTING = {
    "title": "Senior Software Engineer",
    "description": (
        "We are looking for a Senior Software Engineer to join our growing Engineering team. "
        "You will design and build scalable backend services, mentor junior developers, "
        "and contribute to architectural decisions. Experience with Python, FastAPI, and "
        "cloud infrastructure (AWS/GCP) is required. Familiarity with Singapore's regulatory "
        "tech landscape is a plus."
    ),
    "department": "Engineering",
    "location": "Singapore — Hybrid (3 days office)",
    "employment_type": "full_time",
    "salary_range_min": 7000,
    "salary_range_max": 10000,
    "requirements": [
        "5+ years software engineering experience",
        "Strong Python and SQL skills",
        "Experience with REST API design",
        "Familiarity with CI/CD pipelines",
        "Good communication skills",
    ],
}

# Section-local cache for cross-iteration lookups (e.g., interviewer employee
# ids resolved once, reused across all interview-creating candidates).
CANDIDATES_LOCAL_CACHE: dict[str, Any] = {}

# 20 candidates with source split: careers_page=6, jobstreet=6, referral=4, linkedin=4
# All include pdpa_consent=True at create time (audit-fix for SG PDPA compliance).
CANDIDATES = [
    # --- linkedin (4) ---
    {
        "name": "Alex Tan Wei Ming",
        "email": "alex.tan.wm@gmail.com",
        "phone": "+65 9123 4567",
        "source": "linkedin",
        "notes": "Currently at Grab, 6 years experience. Strong Python background.",
        "stage_target": "interview",
    },
    {
        "name": "Vikram Patel",
        "email": "vikram.p@protonmail.com",
        "phone": "+65 9567 8901",
        "source": "linkedin",
        "notes": "Based in India, willing to relocate. Strong distributed systems background.",
        "stage_target": "applied",
    },
    {
        "name": "Hannah Lim Su-Min",
        "email": "hannah.lim.sm@gmail.com",
        "phone": "+65 8112 3344",
        "source": "linkedin",
        "notes": "Backend engineer at Carousell, 5 years. Strong Postgres and async Python.",
        "stage_target": "interview",
    },
    {
        "name": "Daniel Ho",
        "email": "daniel.ho.eng@outlook.com",
        "phone": "+65 8233 4455",
        "source": "linkedin",
        "notes": "Ex-Garena, specialises in observability and SRE practices.",
        "stage_target": "applied",
    },
    # --- referral (4) ---
    {
        "name": "Rachel Goh",
        "email": "rachel.goh.dev@gmail.com",
        "phone": "+65 8234 5678",
        "source": "referral",
        "notes": "Referred by Chen Wei. Ex-Shopee, specializes in microservices.",
        "stage_target": "interview",
    },
    {
        "name": "Kavita Subramaniam",
        "email": "kavita.subra@gmail.com",
        "phone": "+65 9088 1122",
        "source": "referral",
        "notes": "Referred by Priya Nair. 4 yrs at Stripe. Distributed systems.",
        "stage_target": "offered",
    },
    {
        "name": "Marcus Yeo",
        "email": "marcus.yeo.dev@protonmail.com",
        "phone": "+65 8133 2244",
        "source": "referral",
        "notes": "Referred by Marcus Tan. Junior-mid backend, last role at SP Group.",
        "stage_target": "applied",
    },
    {
        "name": "Linh Nguyen",
        "email": "linh.nguyen.swe@gmail.com",
        "phone": "+65 9477 5566",
        "source": "referral",
        "notes": "Referred by Nguyen Thanh. Currently on LTVP, willing to switch employers.",
        "stage_target": "applied",
    },
    # --- jobstreet (6) ---
    {
        "name": "James Fernandez",
        "email": "j.fernandez@outlook.com",
        "phone": "+65 9345 6789",
        "source": "jobstreet",
        "notes": "4 years at a local fintech. Good FastAPI experience.",
        "stage_target": "applied",
    },
    {
        "name": "Aisha Binte Rahman",
        "email": "aisha.rahman.sg@gmail.com",
        "phone": "+65 8244 6677",
        "source": "jobstreet",
        "notes": "5 years at Razer, looking for hybrid role with growth path.",
        "stage_target": "interview",
    },
    {
        "name": "Wong Chun Kit",
        "email": "ck.wong.dev@gmail.com",
        "phone": "+65 9567 7788",
        "source": "jobstreet",
        "notes": "Hong Kong native on EP. Senior engineer at SCMP, 7 years experience.",
        "stage_target": "applied",
    },
    {
        "name": "Tan Sok Yee",
        "email": "sokyee.tan@yahoo.com.sg",
        "phone": "+65 8744 1188",
        "source": "jobstreet",
        "notes": "Returning Singaporean, 3 yrs in Sydney at Atlassian. Open to remote-first.",
        "stage_target": "applied",
    },
    {
        "name": "Pradeep Reddy",
        "email": "pradeep.reddy.dev@gmail.com",
        "phone": "+65 9011 2233",
        "source": "jobstreet",
        "notes": "Mid-level backend, 4 yrs at Indian fintech. EP-eligible by salary.",
        "stage_target": "applied",
    },
    {
        "name": "Lily Chua",
        "email": "lily.chua.eng@outlook.com",
        "phone": "+65 8255 7799",
        "source": "jobstreet",
        "notes": "Singaporean, ex-PropertyGuru, 4 yrs. Strong on data pipelines.",
        "stage_target": "interview",
    },
    # --- careers_page (6) ---
    {
        "name": "Michelle Lau",
        "email": "michelle.lau.sg@gmail.com",
        "phone": "+65 8456 7890",
        "source": "careers_page",
        "notes": "Full-stack developer, 7 years experience. Currently freelancing.",
        "stage_target": "offered",
    },
    {
        "name": "Bryan Khoo",
        "email": "bryan.khoo.eng@gmail.com",
        "phone": "+65 9311 2244",
        "source": "careers_page",
        "notes": "Recent NUS Computing graduate, internships at GovTech and Shopee.",
        "stage_target": "applied",
    },
    {
        "name": "Sophia Ng",
        "email": "sophia.ng.dev@gmail.com",
        "phone": "+65 8677 3366",
        "source": "careers_page",
        "notes": "5 yrs at SingTel, strong Java background, willing to retool to Python.",
        "stage_target": "applied",
    },
    {
        "name": "Farhan Ismail",
        "email": "farhan.ismail.dev@gmail.com",
        "phone": "+65 9122 8855",
        "source": "careers_page",
        "notes": "3 yrs at DBS, currently on probation, looking for product-led role.",
        "stage_target": "applied",
    },
    {
        "name": "Joel Chen",
        "email": "joel.chen.eng@outlook.com",
        "phone": "+65 8244 9911",
        "source": "careers_page",
        "notes": "Ex-AWS Singapore, 6 yrs. Cloud architecture and infra-as-code.",
        "stage_target": "interview",
    },
    {
        "name": "Eunice Wee",
        "email": "eunice.wee.swe@gmail.com",
        "phone": "+65 9088 4477",
        "source": "careers_page",
        "notes": "Returning Singaporean, 4 yrs in London at Monzo. Strong product sense.",
        "stage_target": "applied",
    },
]


# ===========================================================================
# API Client
# ===========================================================================


_TRANSIENT_HTTP_EXCEPTIONS: tuple[type[BaseException], ...] = (
    httpx.ReadError,
    httpx.WriteError,
    httpx.ConnectError,
    httpx.RemoteProtocolError,
    httpx.PoolTimeout,
    httpx.ReadTimeout,
)


def _is_transient_status(resp: httpx.Response) -> bool:
    """5xx and 429 are retryable; backend often emits 502/503 when DataFlow pool saturates."""
    return resp.status_code in (429, 502, 503, 504)


def _retry_http(call: Callable[[], httpx.Response]) -> httpx.Response:
    """Run an HTTP call with exponential-backoff retry on transient failures.

    Retries on connection-reset (ECONNRESET observed when the backend's DataFlow
    pool — pool_size=70 + max_overflow=35 — exceeds Postgres max_connections=100)
    and on 429/5xx responses.
    """
    last_exc: BaseException | None = None
    delay = RETRY_INITIAL_DELAY
    for attempt in range(1, RETRY_MAX_ATTEMPTS + 1):
        try:
            resp = call()
        except _TRANSIENT_HTTP_EXCEPTIONS as exc:
            last_exc = exc
            if attempt == RETRY_MAX_ATTEMPTS:
                raise
            sleep_for = min(delay, RETRY_MAX_DELAY) + random.uniform(0, 0.5)
            print(
                f"  [RETRY] {type(exc).__name__} attempt {attempt}/{RETRY_MAX_ATTEMPTS} "
                f"-- sleeping {sleep_for:.1f}s",
                flush=True,
            )
            time.sleep(sleep_for)
            delay = min(delay * 2, RETRY_MAX_DELAY)
            continue
        if _is_transient_status(resp) and attempt < RETRY_MAX_ATTEMPTS:
            sleep_for = min(delay, RETRY_MAX_DELAY) + random.uniform(0, 0.5)
            print(
                f"  [RETRY] HTTP {resp.status_code} attempt {attempt}/{RETRY_MAX_ATTEMPTS} "
                f"-- sleeping {sleep_for:.1f}s",
                flush=True,
            )
            time.sleep(sleep_for)
            delay = min(delay * 2, RETRY_MAX_DELAY)
            continue
        return resp
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("retry loop exited without response")


class ArborClient:
    """HTTP client for the Arbor REST API with authentication."""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(timeout=REQUEST_TIMEOUT, follow_redirects=True)
        self._token: str | None = None

    @property
    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    def _url(self, path: str) -> str:
        # Support both direct backend (localhost:8001) and proxied (via Caddy /api)
        # Auto-detect: if base_url already ends with /api, don't double-add
        if self.base_url.endswith("/api"):
            return f"{self.base_url}{path}"
        # Try direct first (no /api prefix) for local dev
        return f"{self.base_url}{path}"

    def post(self, path: str, json: dict | None = None) -> httpx.Response:
        return _retry_http(
            lambda: self._client.post(self._url(path), json=json, headers=self._headers)
        )

    def get(self, path: str, params: dict | None = None) -> httpx.Response:
        return _retry_http(
            lambda: self._client.get(self._url(path), params=params, headers=self._headers)
        )

    def patch(self, path: str, json: dict | None = None) -> httpx.Response:
        return _retry_http(
            lambda: self._client.patch(self._url(path), json=json, headers=self._headers)
        )

    def close(self) -> None:
        self._client.close()

    # -- Auth helpers --

    def register(self, email: str, password: str, name: str) -> dict:
        """Register a new user. Returns user data with tokens."""
        resp = self.post("/auth/register", {"email": email, "password": password, "name": name})
        if resp.status_code == 409:
            # Already registered — log in instead
            return self.login(email, password)
        resp.raise_for_status()
        data = resp.json()
        self._token = data.get("access_token")
        return data

    def login(self, email: str, password: str) -> dict:
        """Log in and store the access token."""
        resp = self.post("/auth/login", {"email": email, "password": password})
        resp.raise_for_status()
        data = resp.json()
        self._token = data.get("access_token")
        return data


# ===========================================================================
# Seeding functions
# ===========================================================================


def _print(msg: str) -> None:
    """Print with flush for real-time progress in CI/demo environments."""
    print(msg, flush=True)


def _ok(label: str, detail: str = "") -> None:
    detail_str = f" — {detail}" if detail else ""
    _print(f"  [OK] {label}{detail_str}")


def _skip(label: str, detail: str = "") -> None:
    detail_str = f" — {detail}" if detail else ""
    _print(f"  [SKIP] {label}{detail_str}")


def _fail(label: str, detail: str = "") -> None:
    detail_str = f" — {detail}" if detail else ""
    _print(f"  [FAIL] {label}{detail_str}")


def seed_auth(client: ArborClient, email: str, password: str) -> dict:
    """Step 1: Register or log in the demo admin user (rate-limit aware)."""
    _print("\n--- Step 1: Authentication ---")
    user = _safe_register_or_login(client, email, password, "Demo Admin")
    user_id = user.get("user", {}).get("id") or user.get("id")
    _ok("Authenticated", f"user_id={user_id}, email={email}")
    return user


def _safe_register_or_login(
    client: ArborClient,
    email: str,
    password: str,
    name: str,
    max_retries: int = 4,
) -> dict:
    """Register-or-login with back-off when the 5/60s auth rate limit trips."""
    for attempt in range(max_retries):
        try:
            return client.register(email, password, name)
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code if exc.response is not None else 0
            if status == 429 and attempt < max_retries - 1:
                wait = 65
                _print(
                    f"  [WARN] Auth rate-limited (429) on register; "
                    f"waiting {wait}s for window to drain..."
                )
                time.sleep(wait)
                continue
            raise
    raise RuntimeError("register exhausted retries")


def _safe_login(client: ArborClient, email: str, password: str, max_retries: int = 4) -> None:
    """Re-login as admin with back-off when the auth rate limit (5/60s) trips.

    The seed flow does many sequential admin re-logins between sections.
    On warm databases the in-memory rate limiter starts returning 429 mid-run.
    This helper waits and retries instead of crashing the whole seed.
    """
    for attempt in range(max_retries):
        try:
            client.login(email, password)
            return
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code if exc.response is not None else 0
            if status == 429 and attempt < max_retries - 1:
                wait = 65
                _print(
                    f"  [WARN] Login rate-limited (429); "
                    f"waiting {wait}s for window to drain (attempt {attempt + 1})..."
                )
                time.sleep(wait)
                continue
            raise


def seed_company(client: ArborClient, company_name: str) -> int:
    """Step 2: Create the demo company (or find existing)."""
    _print("\n--- Step 2: Company Setup ---")

    # Check if company already exists via /auth/me to see company_id
    me_resp = client.get("/auth/me")
    if me_resp.status_code == 200:
        me = me_resp.json()
        company_id = me.get("company_id")
        if company_id:
            _skip("Company", f"already linked — company_id={company_id}")
            return company_id

    # Create company
    resp = client.post(
        "/profile",
        {
            "name": company_name,
            "uen": "202100001K",
            "sector": "Services",
            "sub_sector": "Trading & Distribution",
            "headcount_local": 18,
            "headcount_pr": 2,
            "headcount_ep": 3,
            "headcount_sp": 3,
            "headcount_wp": 2,
        },
    )
    resp.raise_for_status()
    data = resp.json()
    company_id = data.get("id") or data.get("company", {}).get("id")

    # The company creation endpoint links the company to the user.
    # Re-login to refresh the token with the company_id claim.
    # (The token issued at registration may not have company_id yet.)

    _ok("Company created", f"company_id={company_id}, name={company_name}")

    # Re-check me endpoint to get the updated company_id
    me_resp = client.get("/auth/me")
    if me_resp.status_code == 200:
        me = me_resp.json()
        refreshed_company_id = me.get("company_id")
        if refreshed_company_id:
            company_id = refreshed_company_id

    if not company_id:
        _fail("Company", "could not determine company_id after creation")
        sys.exit(1)

    return company_id


def seed_leave_types(client: ArborClient) -> list[dict]:
    """Step 2b: Seed Singapore statutory leave types."""
    _print("\n--- Step 2b: Leave Types ---")

    # Check if leave types already exist
    resp = client.get("/leave/types")
    if resp.status_code == 200:
        existing = resp.json().get("leave_types", [])
        if existing:
            _skip("Leave types", f"{len(existing)} already configured")
            return existing

    # Seed statutory leave types
    resp = client.post("/leave/types", {"seed_statutory": True})
    resp.raise_for_status()
    data = resp.json()
    created = data.get("leave_types", [])
    _ok("Leave types seeded", f"{len(created)} statutory types created")
    return created


def seed_employees(
    client: ArborClient, company_id: int, max_employees: int
) -> list[dict]:
    """Step 3: Create employees via the invitation flow.

    The proper Arbor flow is: admin invites → employee registers with
    invitation token → this creates both User + Employee records.

    For demo seeding we: (1) POST /employees/invite to create an invitation,
    (2) POST /auth/register with the invitation_token to accept it (creates
    user + employee), (3) PATCH /employees/{id} to fill in profile details.

    The admin token is saved/restored so subsequent API calls still work.
    """
    _print("\n--- Step 3: Employees ---")

    # Check existing employees
    resp = client.get("/employees")
    existing_employees: list[dict] = []
    if resp.status_code == 200:
        existing_employees = resp.json().get("employees", [])

    existing_emails = {
        e.get("email", "").lower() for e in existing_employees
    }

    profiles = EMPLOYEE_PROFILES[:max_employees]
    created_employees: list[dict] = []
    skipped = 0

    # Save the admin token — we'll need to restore it after each employee registration
    admin_token = client._token

    for profile in profiles:
        email = profile["email"]
        name = profile["name"]

        if email.lower() in existing_emails:
            matching = [
                e for e in existing_employees if e.get("email", "").lower() == email.lower()
            ]
            if matching:
                created_employees.append(matching[0])
            skipped += 1
            continue

        # Token safety: wrap all token swaps in try/finally
        saved_token = client._token
        try:
            # Step 1: Admin sends invitation
            client._token = admin_token
            role = profile.get("role", "employee")
            if role == "owner":
                role = "employee"  # Can't invite as owner
            invite_resp = client.post(
                "/employees/invite",
                {"email": email, "role": role, "name": name},
            )

            if invite_resp.status_code == 409:
                # Already invited or exists — check if employee record exists
                skipped += 1
                continue
            elif invite_resp.status_code not in (200, 201):
                _fail(f"Employee {name}", f"invite failed: {invite_resp.status_code} — {invite_resp.text[:200]}")
                continue

            invite_data = invite_resp.json()
            # Primary: extract token from invite_url (backend returns
            # {"invite_url": "...?token=abc", "invitation": {...}})
            invitation_token = None
            invite_url = invite_data.get("invite_url", "")
            if "token=" in invite_url:
                invitation_token = invite_url.split("token=")[-1].split("&")[0]
            # Fallback: direct field
            if not invitation_token:
                invitation_token = invite_data.get("invitation_token") or invite_data.get("token")

            if not invitation_token:
                _fail(f"Employee {name}", "no invitation token returned")
                continue

            # Step 2: Accept invitation via /auth/register-employee — creates User + Employee
            reg_resp = client.post(
                "/auth/register-employee",
                {
                    "email": email,
                    "password": "Employee2026!",
                    "name": name,
                    "invitation_token": invitation_token,
                },
            )

            if reg_resp.status_code not in (200, 201):
                _fail(f"Employee {name}", f"registration failed: {reg_resp.status_code} — {reg_resp.text[:200]}")
                continue

            # Step 3: Restore admin token and find the new employee record
            client._token = admin_token
            time.sleep(0.1)
            emp_list_resp = client.get("/employees")
            if emp_list_resp.status_code != 200:
                _fail(f"Employee {name}", "could not list employees after creation")
                continue

            employee_record = None
            for e in emp_list_resp.json().get("employees", []):
                if e.get("email", "").lower() == email.lower():
                    employee_record = e
                    break

            if not employee_record:
                _fail(f"Employee {name}", "employee record not found after invitation acceptance")
                continue

            emp_id = employee_record.get("id")

            # Step 4: Update employee profile with full details
            # Include all enrichment fields from EMPLOYEE_PROFILES
            update_fields: dict[str, Any] = {}
            for field in [
                "department", "designation", "employment_type", "start_date",
                "end_date", "nationality", "pass_type", "salary_monthly",
                "gender", "race", "immigration_status", "work_pass_expiry",
                "confirmation_status", "probation_months", "probation_end_date",
                "date_of_birth", "marital_status", "nric_fin",
                "bank_name", "bank_account_number", "bank_code",
                "residential_address", "postal_code", "phone",
            ]:
                if field in profile and profile[field]:
                    update_fields[field] = profile[field]

            if update_fields:
                patch_resp = client.patch(f"/employees/{emp_id}", json=update_fields)
                if patch_resp.status_code not in (200, 201):
                    _fail(f"Employee {name}", f"profile update failed: {patch_resp.status_code}")

            created_employees.append(employee_record)
            _ok(f"Employee {name}", f"id={emp_id}, dept={profile['department']}")
        finally:
            client._token = saved_token

    if skipped:
        _skip("Employees", f"{skipped} already existed")
    _ok("Employees total", f"{len(created_employees)} employees ready")
    return created_employees


# ---------------------------------------------------------------------------
# Employee profile enrichment (addresses, contacts, family, statutory)
# ---------------------------------------------------------------------------

_SG_ADDRESSES = [
    ("Blk 123 Ang Mo Kio Ave 3 #08-456 Singapore 560123", "560123"),
    ("Blk 456 Bedok North St 1 #12-789 Singapore 460456", "460456"),
    ("Blk 789 Clementi Ave 2 #05-234 Singapore 120789", "120789"),
    ("32 Dover Rd #03-01 Singapore 130032", "130032"),
    ("Blk 234 Eunos Rd 5 #10-567 Singapore 400234", "400234"),
    ("Blk 567 Geylang East Ave 1 #07-890 Singapore 380567", "380567"),
    ("15 Holland Ave #04-12 Singapore 278989", "278989"),
    ("Blk 890 Jalan Bukit Merah #15-345 Singapore 150890", "150890"),
    ("Blk 345 Kallang Way #09-678 Singapore 330345", "330345"),
    ("Blk 678 Marine Parade Rd #11-901 Singapore 440678", "440678"),
    ("Blk 901 Pasir Ris St 21 #06-234 Singapore 510901", "510901"),
    ("Blk 112 Serangoon North Ave 1 #14-567 Singapore 550112", "550112"),
    ("Blk 223 Tampines St 21 #02-890 Singapore 520223", "520223"),
    ("Blk 334 Woodlands Ave 5 #16-123 Singapore 730334", "730334"),
    ("Blk 445 Yishun Ring Rd #08-456 Singapore 760445", "760445"),
    ("Blk 556 Toa Payoh Lorong 4 #13-789 Singapore 310556", "310556"),
    ("Blk 667 Bukit Batok West Ave 8 #04-012 Singapore 650667", "650667"),
    ("Blk 778 Jurong West St 42 #10-345 Singapore 640778", "640778"),
    ("22 Sengkang East Way #07-08 Singapore 541022", "541022"),
    ("Blk 889 Upper Thomson Rd #15-678 Singapore 574889", "574889"),
    ("Blk 100 Redhill Close #03-901 Singapore 150100", "150100"),
    ("Blk 211 Farrer Park Rd #11-234 Singapore 210211", "210211"),
    ("Blk 322 Queen St #06-567 Singapore 180322", "180322"),
    ("Blk 433 Victoria St #09-890 Singapore 190433", "190433"),
    ("Blk 544 Novena Rise #14-123 Singapore 307544", "307544"),
    ("Blk 655 Lorong Ah Soo #02-456 Singapore 530655", "530655"),
    ("18 Zion Rd #08-03 Singapore 247726", "247726"),
    ("Blk 766 Orchard Blvd #12-789 Singapore 248649", "248649"),
]

_EC_NAMES = [
    "Lim Ah Huat", "Tan Siew Lan", "Kumar Rajan", "Siti Nurhaliza", "Tanaka Yuki",
    "Sarah Ng", "Deepa Nair", "Jason Lim", "Grace Tan", "Nurul Aisyah",
    "Chen Guowei", "Angela Ong", "Ravi Kumar", "Fatimah Ali", "Kevin Tay",
    "Priya Devi", "David Ng", "Jessica Lim", "Faizal Ibrahim", "Samuel Tan",
]

_CHILD_NAMES = ["Ethan", "Chloe", "Lucas", "Sophie", "Ryan", "Olivia", "Noah", "Emma"]

_RELIGIONS = ["Buddhism", "Christianity", "Islam", "Hinduism", "Taoism", "Free Thinker", "Free Thinker"]


def seed_employee_profiles(client: ArborClient, employees: list[dict]) -> None:
    """Step 3b: Enrich employee profiles with addresses, contacts, family, statutory fields."""
    _print("\n--- Step 3b: Employee Profile Enrichment ---")

    import random
    random.seed(42)  # Deterministic for consistent demo data

    profiles_by_email = {p["email"].lower(): p for p in EMPLOYEE_PROFILES}
    ok_patch = ok_ec = ok_fam = 0

    for i, emp in enumerate(employees):
        eid = emp.get("id")
        if not eid:
            continue

        email = emp.get("email", "").lower()
        profile = profiles_by_email.get(email, {})
        pass_type = profile.get("pass_type", emp.get("pass_type", "citizen"))
        gender = profile.get("gender", emp.get("gender", "male"))

        # --- Patch full profile fields ---
        addr, postal = _SG_ADDRESSES[i % len(_SG_ADDRESSES)]
        dob_year = random.randint(1971, 2001)
        dob = f"{dob_year}-{random.randint(1,12):02d}-{random.randint(1,28):02d}"
        nric_prefix = random.choice("ST")
        nric = f"{nric_prefix}{random.randint(1000000,9999999)}{random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')}"
        phone = f"+65 {random.choice(['8','9'])}{random.randint(100,999)} {random.randint(1000,9999)}"
        bank = random.choice(["DBS", "OCBC", "UOB", "Standard Chartered", "HSBC"])
        bank_codes = {"DBS": "7171", "OCBC": "7339", "UOB": "7375", "Standard Chartered": "9496", "HSBC": "7232"}

        fields: dict[str, Any] = {
            "residential_address": addr,
            "postal_code": postal,
            "date_of_birth": dob,
            "phone": phone,
            "nric_fin": nric,
            "religion": random.choice(_RELIGIONS),
            "marital_status": random.choice(["single", "married", "married", "single", "married"]),
            "bank_name": bank,
            "bank_code": bank_codes.get(bank, "7171"),
            "bank_account_number": f"{random.randint(100,999)}-{random.randint(100000,999999)}-{random.randint(0,9)}",
            "notice_period_days": random.choice([14, 30, 30, 30, 60]),
            "employee_id_internal": f"CS-{eid:04d}",
            "iras_auto_inclusion": True,
            "tax_reference": f"TAX-{random.randint(100000,999999)}",
            "cpf_status": "include" if pass_type in ("citizen", "pr") else "exclude",
        }

        # Include profile fields that the initial PATCH might have missed
        for field in ["department", "designation", "employment_type", "start_date",
                      "nationality", "pass_type", "salary_monthly", "gender", "race",
                      "immigration_status", "work_pass_expiry", "confirmation_status"]:
            if field in profile and profile[field]:
                fields[field] = profile[field]

        resp = client.patch(f"/employees/{eid}", json=fields)
        if resp.status_code in (200, 201):
            ok_patch += 1

        # --- Emergency contacts (1-2 per employee) ---
        ec_check = client.get(f"/employees/{eid}/emergency-contacts")
        existing_ecs = ec_check.json().get("contacts", []) if ec_check.status_code == 200 else []
        if not existing_ecs:
            for _ in range(random.choice([1, 1, 2])):
                rel = random.choice(["spouse", "parent", "sibling", "spouse", "parent"])
                ec_phone = f"+65 {random.choice(['8','9'])}{random.randint(100,999)} {random.randint(1000,9999)}"
                ec_resp = client.post(f"/employees/{eid}/emergency-contacts", {
                    "name": random.choice(_EC_NAMES),
                    "relationship": rel,
                    "phone_primary": ec_phone,
                })
                if ec_resp.status_code in (200, 201):
                    ok_ec += 1

        # --- Family members (for married employees) ---
        fm_check = client.get(f"/employees/{eid}/family-members")
        existing_fms = fm_check.json().get("family_members", []) if fm_check.status_code == 200 else []
        marital = fields.get("marital_status", "single")
        if not existing_fms and marital == "married":
            # Spouse
            spouse_name = random.choice(_EC_NAMES)
            spouse_dob = f"{random.randint(1975,1998)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}"
            fm_resp = client.post(f"/employees/{eid}/family-members", {
                "name": spouse_name,
                "relationship": "spouse",
                "date_of_birth": spouse_dob,
                "gender": "female" if gender == "male" else "male",
                "citizenship_status": random.choice(["citizen", "citizen", "pr"]),
            })
            if fm_resp.status_code in (200, 201):
                ok_fam += 1
            # Children (0-2)
            for _ in range(random.choice([0, 0, 1, 1, 2])):
                child_gender = random.choice(["male", "female"])
                surname = emp.get("name", "").split()[-1] if emp.get("name") else "Tan"
                child_dob = f"{random.randint(2015,2024)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}"
                fm_resp = client.post(f"/employees/{eid}/family-members", {
                    "name": f"{random.choice(_CHILD_NAMES)} {surname}",
                    "relationship": "child",
                    "date_of_birth": child_dob,
                    "gender": child_gender,
                    "citizenship_status": "citizen",
                })
                if fm_resp.status_code in (200, 201):
                    ok_fam += 1

    _ok("Profile enrichment", f"patched={ok_patch}, emergency_contacts={ok_ec}, family_members={ok_fam}")


def seed_role_promotions(client: ArborClient, employees: list[dict]) -> None:
    """Step 3c: Promote specific employees to HR manager role."""
    _print("\n--- Step 3c: Role Promotions ---")

    # Grace Koh → HR Manager
    for emp in employees:
        if emp.get("email", "").lower() == "grace.koh@central-solutions.sg":
            # Set designation on the employee record
            resp = client.patch(f"/employees/{emp['id']}", json={"designation": "HR Manager"})
            if resp.status_code in (200, 201):
                _ok("Grace Koh", "designation set to HR Manager")

            # Promote user role via PATCH /admin/users/{user_id}/role
            user_id = emp.get("user_id")
            if not user_id:
                # If user_id not in employee record, fetch the full employee detail
                detail_resp = client.get(f"/employees/{emp['id']}")
                if detail_resp.status_code == 200:
                    user_id = detail_resp.json().get("employee", {}).get("user_id") or detail_resp.json().get("user_id")

            if user_id:
                role_resp = client.patch(f"/admin/users/{user_id}/role", json={"role": "hr_manager"})
                if role_resp.status_code in (200, 201):
                    _ok("Grace Koh", "role promoted to hr_manager")
                else:
                    _fail("Grace Koh role", f"admin endpoint returned {role_resp.status_code}")
            else:
                _fail("Grace Koh role", "user_id not found — role promotion skipped")
            break


def seed_salary_components(client: ArborClient, employees: list[dict]) -> int:
    """Step 4: Create salary components for each employee."""
    _print("\n--- Step 4: Salary Components ---")

    created_count = 0
    skipped_count = 0

    for emp in employees:
        emp_id = emp.get("id")
        if not emp_id:
            continue

        # Check existing components
        comp_resp = client.get(f"/employees/{emp_id}/salary-components")
        if comp_resp.status_code == 200:
            existing = comp_resp.json().get("components", [])
            if existing:
                skipped_count += 1
                continue

        salary = emp.get("salary_monthly", 0)
        if not salary:
            # Look up from profile by email
            email = emp.get("email", "").lower()
            for p in EMPLOYEE_PROFILES:
                if p["email"].lower() == email:
                    salary = p.get("salary_monthly", 0)
                    break

        if not salary:
            continue

        # Basic salary component
        resp = client.post(
            f"/employees/{emp_id}/salary-components",
            {
                "component_type": "basic_salary",
                "name": "Basic Salary",
                "amount": salary,
                "frequency": "monthly",
                "is_taxable": True,
                "is_cpf_applicable": True,
            },
        )
        if resp.status_code in (200, 201):
            created_count += 1

        # Add transport allowance for field employees
        dept = emp.get("department", "")
        if dept in ("Sales", "Operations"):
            resp = client.post(
                f"/employees/{emp_id}/salary-components",
                {
                    "component_type": "fixed_allowance",
                    "name": "Transport Allowance",
                    "amount": 200.0 if dept == "Sales" else 150.0,
                    "frequency": "monthly",
                    "is_taxable": True,
                    "is_cpf_applicable": False,
                },
            )
            if resp.status_code in (200, 201):
                created_count += 1

        # Add meal allowance for warehouse staff
        designation = emp.get("designation", "")
        if "Warehouse" in designation or "Logistics" in designation:
            resp = client.post(
                f"/employees/{emp_id}/salary-components",
                {
                    "component_type": "fixed_allowance",
                    "name": "Meal Allowance",
                    "amount": 100.0,
                    "frequency": "monthly",
                    "is_taxable": False,
                    "is_cpf_applicable": False,
                },
            )
            if resp.status_code in (200, 201):
                created_count += 1

    if skipped_count:
        _skip("Salary components", f"{skipped_count} employees already had components")
    _ok("Salary components", f"{created_count} components created")
    return created_count


def seed_payroll(client: ArborClient) -> list[dict]:
    """Step 5: Run payroll for Jan, Feb, Mar 2026."""
    _print("\n--- Step 5: Payroll Runs (Jan-Mar 2026) ---")

    payroll_periods = [
        ("2026-01-01", "2026-01-31", "2026-02-07", "January 2026"),
        ("2026-02-01", "2026-02-28", "2026-03-07", "February 2026"),
        ("2026-03-01", "2026-03-31", "2026-04-07", "March 2026"),
    ]

    runs: list[dict] = []
    for period_start, period_end, pay_date, label in payroll_periods:
        resp = client.post(
            "/payroll/calculate",
            {
                "period_start": period_start,
                "period_end": period_end,
                "pay_date": pay_date,
                "payroll_type": "monthly",
            },
        )

        if resp.status_code == 400 and "already exists" in resp.text.lower():
            _skip(f"Payroll {label}", "run already exists for this period")
            continue
        elif resp.status_code not in (200, 201):
            _fail(f"Payroll {label}", f"{resp.status_code} — {resp.text[:200]}")
            continue

        run_data = resp.json()
        run_id = run_data.get("payroll_run", {}).get("id") or run_data.get("id")
        employee_count = run_data.get("payroll_run", {}).get("employee_count", "?")
        runs.append(run_data)
        _ok(f"Payroll {label}", f"run_id={run_id}, employees={employee_count}")

        # Approve the payroll run (past months only)
        if run_id and label != "March 2026":
            approve_resp = client.post(f"/payroll/runs/{run_id}/approve")
            if approve_resp.status_code in (200, 201):
                _ok(f"Payroll {label} approved")

                # Mark Jan as paid
                if label == "January 2026":
                    paid_resp = client.post(f"/payroll/runs/{run_id}/mark-paid")
                    if paid_resp.status_code in (200, 201):
                        _ok(f"Payroll {label} marked paid")

    return runs


def seed_leave_applications(
    client: ArborClient, employees: list[dict], leave_types: list[dict]
) -> int:
    """Step 6: Create leave applications."""
    _print("\n--- Step 6: Leave Applications ---")

    # Build a lookup from leave_type_code to leave_type_id
    lt_lookup: dict[str, int] = {}
    for lt in leave_types:
        code = lt.get("code", "")
        lt_id = lt.get("id")
        if code and lt_id:
            lt_lookup[code] = lt_id

    created_count = 0
    skipped_count = 0

    for app_tmpl in LEAVE_APPLICATIONS:
        emp_idx = app_tmpl["employee_idx"]
        if emp_idx >= len(employees):
            continue

        emp = employees[emp_idx]
        emp_name = emp.get("name", f"Employee #{emp_idx}")

        leave_type_code = app_tmpl["leave_type_code"]
        leave_type_id = lt_lookup.get(leave_type_code)
        if not leave_type_id:
            _fail(f"Leave for {emp_name}", f"leave type '{leave_type_code}' not found")
            continue

        # Token safety: wrap all token swaps in try/finally
        saved_token = client._token
        try:
            # Log in as the employee
            emp_email = emp.get("email", "")
            login_resp = client.post("/auth/login", {"email": emp_email, "password": "Employee2026!"})
            if login_resp.status_code != 200:
                _fail(f"Leave for {emp_name}", f"could not log in as employee: {login_resp.status_code}")
                continue

            emp_token_data = login_resp.json()
            client._token = emp_token_data.get("access_token")

            # Apply for leave
            resp = client.post(
                "/leave/apply",
                {
                    "leave_type_id": leave_type_id,
                    "start_date": app_tmpl["start_date"],
                    "end_date": app_tmpl["end_date"],
                    "reason": app_tmpl["reason"],
                    "start_half": "full_day",
                    "end_half": "full_day",
                },
            )

            # Restore admin token for approve/reject actions
            client._token = saved_token

            if resp.status_code == 409:
                skipped_count += 1
                continue
            elif resp.status_code not in (200, 201):
                _fail(
                    f"Leave for {emp_name}",
                    f"{resp.status_code} — {resp.text[:200]}",
                )
                continue

            app_data = resp.json()
            app_id = app_data.get("application", {}).get("id") or app_data.get("id")
            created_count += 1

            # Process the action (approve/reject)
            action = app_tmpl.get("action", "pending")
            if action == "approve" and app_id:
                approve_resp = client.patch(f"/leave/applications/{app_id}/approve", json={})
                if approve_resp.status_code in (200, 201):
                    _ok(f"Leave {emp_name}", f"applied and approved ({leave_type_code})")
                else:
                    _ok(f"Leave {emp_name}", f"applied, approval failed: {approve_resp.status_code}")
            elif action == "reject" and app_id:
                reject_resp = client.patch(
                    f"/leave/applications/{app_id}/reject",
                    json={"remarks": app_tmpl.get("reject_reason", "Schedule conflict")},
                )
                if reject_resp.status_code in (200, 201):
                    _ok(f"Leave {emp_name}", f"applied and rejected ({leave_type_code})")
                else:
                    _ok(f"Leave {emp_name}", f"applied, rejection failed: {reject_resp.status_code}")
            else:
                _ok(f"Leave {emp_name}", f"applied — pending ({leave_type_code})")
        finally:
            client._token = saved_token

    if skipped_count:
        _skip("Leave applications", f"{skipped_count} overlapping/duplicate")
    _ok("Leave applications", f"{created_count} created")
    return created_count


def seed_claim_categories(client: ArborClient) -> dict[str, int]:
    """Create standard claim categories. Returns name -> id lookup."""
    _print("\n--- Step 6b: Claim Categories ---")

    # Check existing categories
    resp = client.get("/claims/categories")
    if resp.status_code == 200:
        existing = resp.json().get("categories", [])
        if existing:
            lookup = {c.get("name", ""): c.get("id") for c in existing}
            _skip("Claim categories", f"{len(existing)} already exist")
            return lookup

    categories = [
        {"name": "Transport", "monthly_limit": 500.0, "per_claim_limit": 200.0, "requires_receipt": True},
        {"name": "Meals", "monthly_limit": 300.0, "per_claim_limit": 100.0, "requires_receipt": True},
        {"name": "Medical", "monthly_limit": 500.0, "per_claim_limit": 500.0, "requires_receipt": True},
    ]

    lookup: dict[str, int] = {}
    for cat in categories:
        resp = client.post("/claims/categories", cat)
        if resp.status_code in (200, 201):
            cat_data = resp.json().get("category", {})
            lookup[cat["name"]] = cat_data.get("id")
            _ok(f"Category: {cat['name']}", f"id={cat_data.get('id')}")
        else:
            _fail(f"Category: {cat['name']}", f"{resp.status_code}")

    return lookup


def seed_claims(
    client: ArborClient,
    employees: list[dict],
    category_lookup: dict[str, int],
) -> int:
    """Step 7: Create expense claims."""
    _print("\n--- Step 7: Expense Claims ---")

    created_count = 0

    for claim_tmpl in EXPENSE_CLAIMS:
        emp_idx = claim_tmpl["employee_idx"]
        if emp_idx >= len(employees):
            continue

        emp = employees[emp_idx]
        emp_name = emp.get("name", f"Employee #{emp_idx}")
        emp_email = emp.get("email", "")

        # Token safety: wrap all token swaps in try/finally
        saved_token = client._token
        try:
            login_resp = client.post("/auth/login", {"email": emp_email, "password": "Employee2026!"})
            if login_resp.status_code != 200:
                _fail(f"Claim for {emp_name}", f"could not log in: {login_resp.status_code}")
                continue
            client._token = login_resp.json().get("access_token")

            # Create the claim
            resp = client.post(
                "/claims",
                {"claim_month": claim_tmpl["claim_month"]},
            )
            if resp.status_code not in (200, 201):
                _fail(f"Claim for {emp_name}", f"create failed: {resp.status_code} — {resp.text[:200]}")
                continue

            claim_data = resp.json()
            claim_id = claim_data.get("claim", {}).get("id")
            if not claim_id:
                _fail(f"Claim for {emp_name}", "no claim_id in response")
                continue

            # Add items
            total = 0.0
            for item in claim_tmpl["items"]:
                category_name = item["category"]
                category_id = category_lookup.get(category_name)
                if not category_id:
                    _fail(f"Claim item for {emp_name}", f"category '{category_name}' not found")
                    continue

                item_resp = client.post(
                    f"/claims/{claim_id}/items",
                    {
                        "category_id": category_id,
                        "amount": item["amount"],
                        "description": item["description"],
                        "receipt_date": item["receipt_date"],
                    },
                )
                if item_resp.status_code in (200, 201):
                    total += item["amount"]

            # Restore admin token for approve/reject
            client._token = saved_token

            action = claim_tmpl.get("action", "draft")

            if action in ("submit", "approve"):
                # Submit the claim (as employee)
                login_resp = client.post("/auth/login", {"email": emp_email, "password": "Employee2026!"})
                if login_resp.status_code == 200:
                    client._token = login_resp.json().get("access_token")
                    submit_resp = client.patch(f"/claims/{claim_id}/submit")
                    client._token = saved_token

                    if submit_resp.status_code in (200, 201) and action == "approve":
                        approve_resp = client.patch(f"/claims/{claim_id}/approve")
                        if approve_resp.status_code in (200, 201):
                            _ok(f"Claim {emp_name}", f"${total:.2f} — submitted and approved")
                        else:
                            _ok(f"Claim {emp_name}", f"${total:.2f} — submitted (approval: {approve_resp.status_code})")
                    elif submit_resp.status_code in (200, 201):
                        _ok(f"Claim {emp_name}", f"${total:.2f} — submitted, pending approval")
                    else:
                        _ok(f"Claim {emp_name}", f"${total:.2f} — draft (submit: {submit_resp.status_code})")
                else:
                    _ok(f"Claim {emp_name}", f"${total:.2f} — draft")
            else:
                _ok(f"Claim {emp_name}", f"${total:.2f} — draft")

            created_count += 1
        finally:
            client._token = saved_token

    _ok("Claims", f"{created_count} created")
    return created_count


def seed_attendance(client: ArborClient, employees: list[dict]) -> int:
    """Step 8: Create attendance records for today only.

    Clocks in and out each of the first 18 employees for today.
    2-3 employees get overtime annotations.
    """
    _print("\n--- Step 8: Attendance Records (today only) ---")

    today = date.today()

    # Skip on weekends
    if today.weekday() >= 5:
        _skip("Attendance", "today is a weekend — skipping clock-in/out")
        return 0

    # Use up to 18 employees for attendance
    attendance_employees = employees[:18]
    overtime_indices = {2, 6, 14}  # Rajesh, Sato Yuki, Muhammad Rizwan

    created_count = 0
    skipped_count = 0

    for idx, emp in enumerate(attendance_employees):
        emp_email = emp.get("email", "")
        emp_name = emp.get("name", "")

        # Token safety: wrap all token swaps in try/finally
        saved_token = client._token
        try:
            login_resp = client.post("/auth/login", {"email": emp_email, "password": "Employee2026!"})
            if login_resp.status_code != 200:
                continue
            emp_access_token = login_resp.json().get("access_token")

            # Clock in for today only
            client._token = emp_access_token
            clock_resp = client.post("/attendance/clock-in", json={"location": "Office — 1 Raffles Place"})

            if clock_resp.status_code == 400 and "already clocked" in clock_resp.text.lower():
                skipped_count += 1
                continue
            elif clock_resp.status_code not in (200, 201):
                continue

            record_data = clock_resp.json()
            record_id = record_data.get("record", {}).get("id")

            # Clock out
            if record_id:
                clock_out_resp = client.post("/attendance/clock-out", json={})
                if clock_out_resp.status_code in (200, 201):
                    created_count += 1
                    has_ot = ""

                    # If overtime employee, correct the record via admin
                    if idx in overtime_indices:
                        client._token = saved_token
                        client.patch(
                            f"/attendance/{record_id}",
                            json={"overtime_hours": 2.0, "remarks": "Project deadline"},
                        )
                        has_ot = " (with OT)"

                    _ok(f"Attendance {emp_name}", f"clocked in/out{has_ot}")
        finally:
            client._token = saved_token

    if created_count == 0:
        _skip("Attendance", "no records created — check if server time allows clock-in")
    else:
        _ok("Attendance", f"{created_count} records created for today")
    if skipped_count:
        _skip("Attendance", f"{skipped_count} already clocked in today")

    return created_count


def seed_recruitment(client: ArborClient) -> dict:
    """Step 9: Create a job posting with candidates at different stages."""
    _print("\n--- Step 9: Recruitment Pipeline ---")

    # Check existing jobs — reuse if found, create if not. EITHER WAY we
    # proceed to candidate seeding so that an existing-but-empty job gets
    # populated. The candidate-create check below skips by email so this
    # is idempotent.
    job_id = None
    resp = client.get("/recruitment/jobs")
    if resp.status_code == 200:
        existing_jobs = resp.json().get("jobs", [])
        matching = [j for j in existing_jobs if j.get("title") == JOB_POSTING["title"]]
        if matching:
            job_id = matching[0].get("id")
            _skip("Job posting", f"'{JOB_POSTING['title']}' already exists (id={job_id})")

    if job_id is None:
        # Create job posting
        resp = client.post("/recruitment/jobs", JOB_POSTING)
        if resp.status_code not in (200, 201):
            _fail("Job posting", f"{resp.status_code} — {resp.text[:200]}")
            return {}

        job_data = resp.json()
        job_id = job_data.get("job", {}).get("id")
        _ok("Job posting created", f"id={job_id}, title={JOB_POSTING['title']}")

        # Publish the job (only the first time)
        pub_resp = client.post(f"/recruitment/jobs/{job_id}/publish")
        if pub_resp.status_code in (200, 201):
            _ok("Job published")

    # Add candidates (PDPA consent always granted at create — recruitment in SG
    # MUST capture explicit consent before processing personal data).
    for candidate in CANDIDATES:
        cand_resp = client.post(
            f"/recruitment/jobs/{job_id}/candidates",
            {
                "name": candidate["name"],
                "email": candidate["email"],
                "phone": candidate.get("phone", ""),
                "source": candidate.get("source", "direct"),
                "notes": candidate.get("notes", ""),
                "pdpa_consent": True,
            },
        )

        if cand_resp.status_code == 400 and "already exists" in cand_resp.text.lower():
            _skip(f"Candidate {candidate['name']}", "already exists")
            continue
        elif cand_resp.status_code not in (200, 201):
            _fail(f"Candidate {candidate['name']}", f"{cand_resp.status_code}")
            continue

        cand_data = cand_resp.json()
        cand_id = cand_data.get("candidate", {}).get("id")
        stage = candidate.get("stage_target", "applied")

        # Resolve a couple of interviewer employee IDs from the admin's
        # company so seeded interviews don't render "#undefined" in the
        # UI. Lookup is best-effort — seeded interviews still work
        # without interviewers if /employees can't be reached.
        if "_interviewer_ids" not in CANDIDATES_LOCAL_CACHE:
            CANDIDATES_LOCAL_CACHE["_interviewer_ids"] = []
            try:
                emp_resp = client.get("/employees", params={"limit": 50})
                if emp_resp.status_code == 200:
                    body = emp_resp.json()
                    emp_rows = (
                        body.get("employees")
                        or body.get("items")
                        or (body if isinstance(body, list) else [])
                    )
                    # Pick the first 3 active employees (covers panel-style interviews)
                    CANDIDATES_LOCAL_CACHE["_interviewer_ids"] = [
                        e["id"] for e in emp_rows[:3] if e.get("id") and e.get("is_active", True)
                    ]
            except Exception:
                pass
        interviewer_ids = CANDIDATES_LOCAL_CACHE["_interviewer_ids"]

        # Advance candidate through stages
        if stage == "interview" and cand_id:
            # Schedule an interview
            interview_date = (date.today() + timedelta(days=3)).isoformat()
            interview_resp = client.post(
                f"/recruitment/candidates/{cand_id}/interviews",
                {
                    "scheduled_at": f"{interview_date}T10:00:00+08:00",
                    "duration_minutes": 60,
                    "interview_type": "in_person",
                    "location": "Central Solutions — Meeting Room A",
                    "interviewers": interviewer_ids[:2],  # 2-person panel
                    "notes": "First-round technical interview",
                },
            )
            if interview_resp.status_code in (200, 201):
                _ok(f"Candidate {candidate['name']}", f"id={cand_id}, stage=interview")
            else:
                _ok(f"Candidate {candidate['name']}", f"id={cand_id}, stage=applied")
        elif stage == "offered" and cand_id:
            # Schedule interview first, then advance to offered
            interview_date = (date.today() - timedelta(days=5)).isoformat()
            client.post(
                f"/recruitment/candidates/{cand_id}/interviews",
                {
                    "scheduled_at": f"{interview_date}T14:00:00+08:00",
                    "duration_minutes": 45,
                    "interview_type": "video",
                    "interviewers": interviewer_ids[:1],  # 1-on-1 screening
                    "notes": "Screening interview",
                },
            )
            # Create offer
            offer_resp = client.post(
                f"/recruitment/candidates/{cand_id}/offer",
                {
                    "salary": 8500.0,
                    "start_date": (date.today() + timedelta(days=30)).isoformat(),
                    "notes": "Standard EP offer package",
                },
            )
            if offer_resp.status_code in (200, 201):
                _ok(f"Candidate {candidate['name']}", f"id={cand_id}, stage=offered")
            else:
                _ok(f"Candidate {candidate['name']}", f"id={cand_id}, stage=interview (offer: {offer_resp.status_code})")
        else:
            _ok(f"Candidate {candidate['name']}", f"id={cand_id}, stage=applied")

    return {"job_id": job_id}


def seed_onboarding(client: ArborClient, employees: list[dict]) -> None:
    """Step 10: Assign onboarding template to the last 5 employees (new hires).

    Looks up the first available onboarding template and assigns it to the
    most recently hired employees.
    """
    _print("\n--- Step 10: Onboarding Assignments ---")

    # Check for existing templates
    resp = client.get("/onboarding/templates")
    if resp.status_code != 200:
        _skip("Onboarding", f"could not list templates: {resp.status_code}")
        return

    templates = resp.json().get("templates", [])
    if not templates:
        _skip("Onboarding", "no templates found — create one first via the UI")
        return

    # Prefer the company default template
    template = next((t for t in templates if t.get("is_default")), templates[0])
    template_id = template.get("id")
    template_name = template.get("name", "Unknown")
    _ok("Onboarding template", f"using '{template_name}' (id={template_id})")

    # Assign to the last 5 employees (newest hires)
    new_hires = employees[-5:] if len(employees) >= 5 else employees
    assigned_count = 0

    for emp in new_hires:
        emp_id = emp.get("id")
        emp_name = emp.get("name", "")
        if not emp_id:
            continue

        due_date = (date.today() + timedelta(days=30)).isoformat()
        assign_resp = client.post(
            "/onboarding/assign",
            {
                "employee_id": emp_id,
                "template_id": template_id,
                "due_date": due_date,
            },
        )

        if assign_resp.status_code in (200, 201):
            assigned_count += 1
            _ok(f"Onboarding {emp_name}", f"assigned template '{template_name}'")
        elif assign_resp.status_code == 400 and "already has an active" in assign_resp.text.lower():
            _skip(f"Onboarding {emp_name}", "already assigned")
        else:
            _fail(f"Onboarding {emp_name}", f"{assign_resp.status_code} — {assign_resp.text[:200]}")

    _ok("Onboarding", f"{assigned_count} assignments created")


# ===========================================================================
# Round-13 demo refresh: admin profile, scorecards, preboarding, candidate
# PDPA backfill, varied assignment progress.
#
# These sections may use direct DB access (psycopg2) for fields the public
# API does not expose (e.g. PATCH candidate.pdpa_consent, completion_percentage,
# step status overrides). DB writes are guarded by company_id and gated on
# DATABASE_URL availability.
# ===========================================================================


def _get_db_conn():
    """Open a psycopg2 connection from DATABASE_URL.

    Returns None if DATABASE_URL is not set or psycopg2 is not installed.
    All DB-direct seed sections degrade gracefully when this returns None.
    """
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        return None
    try:
        import psycopg2  # type: ignore
    except ImportError:
        _print("  [WARN] psycopg2 not installed — skipping DB-direct seed sections")
        return None
    try:
        return psycopg2.connect(db_url)
    except Exception as exc:
        _print(f"  [WARN] Could not connect to DB: {exc}")
        return None


def seed_admin_employee_profile(client: ArborClient, company_id: int) -> None:
    """Round-13 fix: ensure Demo Admin's Employee record is fully populated.

    The owner's Employee record is auto-created on first /employees/me call
    with empty department/start_date/designation. Round-12 audits flagged
    this as a "lifeless" demo signal. This step:
        1. GET /employees/me to ensure the record exists.
        2. UPDATE it directly in the DB with realistic founder-level fields.

    Direct DB write is preferred over PATCH /employees/{id} because the
    seed flow runs after many other API calls that exhaust the backend's
    DB connection pool — a final round of API PATCHes fails unreliably.
    """
    _print("\n--- Step 11a: Demo Admin Employee Profile ---")

    # Step 1: ensure the Employee record exists by hitting /employees/me
    # (admin has the auto-create path; first call writes the row).
    emp_id_from_api = None
    try:
        me_resp = client.get("/employees/me")
        if me_resp.status_code == 200:
            emp_id_from_api = me_resp.json().get("id")
    except Exception as exc:
        _print(f"  [WARN] /employees/me lookup failed: {exc} — falling back to DB lookup")

    # Step 2: locate the admin's Employee row directly and patch fields
    conn = _get_db_conn()
    if conn is None:
        _skip("Admin profile", "DATABASE_URL unavailable — cannot patch admin Employee")
        return

    try:
        with conn:
            with conn.cursor() as cur:
                # Find admin user (owner role) for this company
                cur.execute(
                    "SELECT u.id FROM users u "
                    "WHERE u.email = 'demo@central.kailash.ai' AND u.role = 'owner'",
                )
                user_row = cur.fetchone()
                if not user_row:
                    _skip("Admin profile", "demo admin user not found")
                    return
                admin_user_id = user_row[0]

                cur.execute(
                    "SELECT id, department, designation, start_date, confirmation_status "
                    "FROM employees WHERE user_id = %s AND company_id = %s LIMIT 1",
                    (admin_user_id, company_id),
                )
                emp_row = cur.fetchone()
                if not emp_row:
                    _skip(
                        "Admin profile",
                        "admin Employee row not found (call /employees/me first)",
                    )
                    return

                emp_id, dept, designation, start_dt, conf_status = emp_row

                # Idempotency: skip if already populated correctly
                if (
                    dept == "Operations"
                    and designation == "Founder & CEO"
                    and conf_status == "confirmed"
                    and start_dt
                ):
                    _skip("Admin profile", f"already populated (id={emp_id})")
                    return

                six_months_ago = (date.today() - timedelta(days=180)).isoformat()
                cur.execute(
                    "UPDATE employees SET "
                    "  department = %s, "
                    "  designation = %s, "
                    "  start_date = %s, "
                    "  confirmation_status = %s, "
                    "  employment_type = 'full_time' "
                    "WHERE id = %s",
                    (
                        "Operations",
                        "Founder & CEO",
                        six_months_ago,
                        "confirmed",
                        emp_id,
                    ),
                )
                _ok(
                    "Admin profile",
                    f"id={emp_id}, dept=Operations, start={six_months_ago}",
                )
    except Exception as exc:
        _fail("Admin profile", f"DB error: {exc}")
    finally:
        try:
            conn.close()
        except Exception:
            pass


# 5 scorecard templates covering common SG SME interview scenarios.
# Weights are normalised to sum to 1.0 (router validates this).
SCORECARD_TEMPLATES: list[dict[str, Any]] = [
    {
        "name": "Engineering — Senior Software Engineer",
        "description": "Technical depth and engineering judgment for a senior IC role.",
        "criteria": [
            {"name": "Technical Depth", "weight": 0.40},
            {"name": "System Design", "weight": 0.25},
            {"name": "Code Quality", "weight": 0.20},
            {"name": "Communication", "weight": 0.15},
        ],
    },
    {
        "name": "Sales — Account Executive",
        "description": "Quota-carrying AE: hunt, close, and grow accounts.",
        "criteria": [
            {"name": "Pipeline Management", "weight": 0.35},
            {"name": "Negotiation", "weight": 0.25},
            {"name": "CRM Discipline", "weight": 0.20},
            {"name": "Domain Knowledge", "weight": 0.20},
        ],
    },
    {
        "name": "F&B — Outlet Manager",
        "description": "Day-to-day outlet leadership: ops, team, customers, P&L.",
        "criteria": [
            {"name": "Operations", "weight": 0.30},
            {"name": "Team Leadership", "weight": 0.30},
            {"name": "Customer Service", "weight": 0.20},
            {"name": "Cost Discipline", "weight": 0.20},
        ],
    },
    {
        "name": "HR — People Specialist",
        "description": "SG employment-law fluency and empathetic process delivery.",
        "criteria": [
            {"name": "Employment Law Knowledge", "weight": 0.30},
            {"name": "Empathy", "weight": 0.25},
            {"name": "Process Discipline", "weight": 0.25},
            {"name": "Communication", "weight": 0.20},
        ],
    },
    {
        "name": "Customer Support — Tier 1",
        "description": "Front-line CS: clear comms, calm under pressure, product mastery.",
        "criteria": [
            {"name": "Communication", "weight": 0.35},
            {"name": "Patience", "weight": 0.25},
            {"name": "Product Knowledge", "weight": 0.25},
            {"name": "Tooling", "weight": 0.15},
        ],
    },
]


def seed_scorecard_templates(client: ArborClient, company_id: int) -> None:
    """Round-13 fix: create 5 starter scorecard templates.

    Cluster 7a shipped the UI for selecting scorecard templates, but the demo
    company had zero — buyers clicking the dropdown saw an empty list. This
    creates a representative set covering Engineering, Sales, F&B, HR, and CS.

    Uses direct DB writes — POST /recruitment/scorecard-templates is correct
    but the seed flow runs after many earlier API calls that can exhaust the
    backend's DB pool. Direct writes are reliable and bypass auth rate limits.
    The criteria validation logic mirrors the router (sum to 1.0, weights in
    [0,1], finite numbers).
    """
    _print("\n--- Step 11b: Scorecard Templates ---")

    conn = _get_db_conn()
    if conn is None:
        _skip("Scorecard templates", "DATABASE_URL unavailable — cannot seed")
        return

    try:
        with conn:
            with conn.cursor() as cur:
                # Locate admin user_id for created_by (audit field)
                cur.execute(
                    "SELECT id FROM users WHERE email='demo@central.kailash.ai' "
                    "AND role='owner' LIMIT 1",
                )
                admin_row = cur.fetchone()
                admin_user_id = admin_row[0] if admin_row else 1

                # Idempotency: which template names already exist?
                cur.execute(
                    "SELECT name FROM scorecard_templates WHERE company_id = %s",
                    (company_id,),
                )
                existing = {r[0] for r in cur.fetchall()}

                created = 0
                skipped = 0
                for tmpl in SCORECARD_TEMPLATES:
                    if tmpl["name"] in existing:
                        skipped += 1
                        continue

                    # Mirror router validation: weights sum ~1.0, in [0, 1].
                    total = sum(c["weight"] for c in tmpl["criteria"])
                    if abs(total - 1.0) > 0.01:
                        _fail(
                            f"Scorecard '{tmpl['name']}'",
                            f"weights sum to {total:.3f}, expected ~1.0",
                        )
                        continue

                    cur.execute(
                        "INSERT INTO scorecard_templates "
                        "(company_id, name, description, criteria, created_by, is_active) "
                        "VALUES (%s, %s, %s, %s, %s, TRUE)",
                        (
                            company_id,
                            tmpl["name"],
                            tmpl["description"],
                            json.dumps(tmpl["criteria"]),
                            admin_user_id,
                        ),
                    )
                    created += 1
                    _ok(
                        f"Scorecard '{tmpl['name']}'",
                        f"{len(tmpl['criteria'])} criteria",
                    )

                _ok("Scorecard templates", f"{created} created, {skipped} skipped")
    except Exception as exc:
        _fail("Scorecard templates", f"DB error: {exc}")
    finally:
        try:
            conn.close()
        except Exception:
            pass


# 5 preboarding tasks for the default template, ordered by relative day.
# `notes` MUST contain the regex pattern `<n> days? (?:before|relative)`
# so the assign-time deadline calculator can derive an absolute date.
PREBOARDING_TEMPLATE_TASKS: list[dict[str, Any]] = [
    {
        "task_name": "Send signed offer letter",
        "owner_role": "hr",
        "trigger": "offer_accepted",
        "rel_days": -14,
        "notes_extra": "Use the standard offer template. Attach signed copy + CPF declaration.",
    },
    {
        "task_name": "Collect ID + bank docs",
        "owner_role": "hr",
        "trigger": "offer_accepted",
        "rel_days": -10,
        "notes_extra": "NRIC/FIN copy, bank statement (account + bank code), tax-residency declaration.",
    },
    {
        "task_name": "Send welcome email + first-day logistics",
        "owner_role": "hr",
        "trigger": "10_days_before_start",
        "rel_days": -7,
        "notes_extra": "Welcome message, dress code, first-day arrival time, parking, lunch arrangement.",
    },
    {
        "task_name": "Set up workspace + access cards",
        "owner_role": "office_manager",
        "trigger": "7_days_before_start",
        "rel_days": -5,
        "notes_extra": "Desk allocation, access card, locker key, stationery starter pack.",
    },
    {
        "task_name": "Verify IT account + laptop ready",
        "owner_role": "it",
        "trigger": "3_days_before_start",
        "rel_days": -1,
        "notes_extra": "Category: laptop | Email account, SSO, VPN profile, laptop image, MFA seed.",
    },
]


def seed_preboarding_template_tasks(company_id: int) -> None:
    """Round-13 fix: seed 5 preboarding tasks on the default onboarding template.

    Creates template-level rows (employee_id=0) on the company's default
    template. The /onboarding/assign endpoint copies these per-employee with
    deadline_date computed from start_date.

    Uses direct DB access — there is no admin endpoint to add individual
    template-level preboarding tasks (existing flow only creates them as a
    side-effect of /onboarding/templates/import which requires an xlsx).
    """
    _print("\n--- Step 11c: Preboarding Template Tasks ---")

    conn = _get_db_conn()
    if conn is None:
        _skip("Preboarding tasks", "DATABASE_URL unavailable — skipping DB-direct seed")
        return

    try:
        with conn:
            with conn.cursor() as cur:
                # Find the company's default template
                cur.execute(
                    "SELECT id, name FROM onboarding_templates "
                    "WHERE company_id = %s AND is_default = TRUE AND is_active = TRUE "
                    "ORDER BY id LIMIT 1",
                    (company_id,),
                )
                row = cur.fetchone()
                if not row:
                    # Fall back to first active template
                    cur.execute(
                        "SELECT id, name FROM onboarding_templates "
                        "WHERE company_id = %s AND is_active = TRUE "
                        "ORDER BY id LIMIT 1",
                        (company_id,),
                    )
                    row = cur.fetchone()
                if not row:
                    _skip("Preboarding tasks", "no onboarding template found")
                    return
                template_id, template_name = row[0], row[1]

                # Idempotency: count existing template-level tasks
                cur.execute(
                    "SELECT task_name FROM preboarding_task_instances "
                    "WHERE company_id = %s AND template_id = %s AND employee_id = 0",
                    (company_id, template_id),
                )
                existing_names = {r[0] for r in cur.fetchall()}

                created = 0
                skipped = 0
                for task in PREBOARDING_TEMPLATE_TASKS:
                    if task["task_name"] in existing_names:
                        skipped += 1
                        continue
                    rel_days = task["rel_days"]
                    notes = (
                        f"Relative deadline: {rel_days} days from start date | "
                        f"{task['notes_extra']}"
                    )
                    cur.execute(
                        "INSERT INTO preboarding_task_instances "
                        "(company_id, template_id, employee_id, task_name, "
                        " owner_role, trigger, deadline_date, status, notes) "
                        "VALUES (%s, %s, 0, %s, %s, %s, NULL, 'pending', %s)",
                        (
                            company_id,
                            template_id,
                            task["task_name"],
                            task["owner_role"],
                            task["trigger"],
                            notes,
                        ),
                    )
                    created += 1

                _ok(
                    f"Preboarding tasks (template '{template_name}')",
                    f"{created} created, {skipped} skipped",
                )
    except Exception as exc:
        _fail("Preboarding tasks", f"DB error: {exc}")
    finally:
        try:
            conn.close()
        except Exception:
            pass


def backfill_candidate_pdpa(company_id: int) -> None:
    """Round-13 fix: ensure ALL candidates have pdpa_consent=True.

    The candidate POST endpoint accepts pdpa_consent in the body, but the
    PATCH endpoint does not — so existing candidates created before this
    seed change cannot be updated via API. This function patches them
    directly in the DB.
    """
    _print("\n--- Step 11d: Candidate PDPA Backfill ---")

    conn = _get_db_conn()
    if conn is None:
        _skip("Candidate PDPA", "DATABASE_URL unavailable — skipping backfill")
        return

    try:
        with conn:
            with conn.cursor() as cur:
                # Find candidates missing PDPA consent
                cur.execute(
                    "SELECT id, name FROM candidates "
                    "WHERE company_id = %s AND pdpa_consent = FALSE",
                    (company_id,),
                )
                rows = cur.fetchall()
                if not rows:
                    _skip("Candidate PDPA", "all candidates already have consent")
                    return

                # Set consent_date to a random point within the last 60 days,
                # so the demo audit trail looks naturally distributed.
                now = datetime.utcnow()
                updated = 0
                for cid, _name in rows:
                    days_ago = random.randint(1, 60)
                    consent_dt = now - timedelta(
                        days=days_ago, hours=random.randint(0, 23),
                    )
                    cur.execute(
                        "UPDATE candidates SET pdpa_consent = TRUE, "
                        "pdpa_consent_date = %s WHERE id = %s",
                        (consent_dt.isoformat(), cid),
                    )
                    updated += 1

                _ok("Candidate PDPA", f"{updated} candidates updated")
    except Exception as exc:
        _fail("Candidate PDPA", f"DB error: {exc}")
    finally:
        try:
            conn.close()
        except Exception:
            pass


def vary_onboarding_progress(company_id: int) -> None:
    """Round-13 fix: vary onboarding-assignment completion across 5 buckets.

    Without variation, every assignment shows 0% complete and the demo looks
    abandoned. This sets:
        bucket 0 -> 100% complete (status=completed, all steps completed)
        bucket 1 -> ~65% (8 of 13 steps completed, some in_progress)
        bucket 2 -> ~30% (4 of 13 steps completed)
        bucket 3 -> preboarding-only (per-employee preboarding tasks live, no step progress)
        bucket 4 -> just-assigned (no step progress, assigned_at = today)

    Direct DB only — there is no admin endpoint to mark steps complete on
    behalf of another employee.
    """
    _print("\n--- Step 11e: Onboarding Progress Variation ---")

    conn = _get_db_conn()
    if conn is None:
        _skip("Onboarding progress", "DATABASE_URL unavailable — skipping")
        return

    try:
        with conn:
            with conn.cursor() as cur:
                # Get all in_progress assignments for the company, oldest first
                cur.execute(
                    "SELECT id, employee_id, template_id FROM onboarding_assignments "
                    "WHERE company_id = %s "
                    "ORDER BY id ASC",
                    (company_id,),
                )
                assignments = cur.fetchall()
                if len(assignments) < 5:
                    _skip(
                        "Onboarding progress",
                        f"need >=5 assignments, found {len(assignments)}",
                    )
                    return

                # Idempotency: if assignment[0] is already 'completed', assume done
                cur.execute(
                    "SELECT status, completion_percentage FROM onboarding_assignments "
                    "WHERE id = %s",
                    (assignments[0][0],),
                )
                first_state = cur.fetchone()
                if first_state and first_state[0] == "completed":
                    _skip("Onboarding progress", "already varied (assignment[0]=completed)")
                    return

                now = datetime.utcnow()
                three_days_ago = now - timedelta(days=3)

                # Bucket 0: 100% complete
                a0_id, _, _ = assignments[0]
                cur.execute(
                    "UPDATE onboarding_step_progress "
                    "SET status='completed', completed_at=%s "
                    "WHERE assignment_id = %s",
                    (three_days_ago, a0_id),
                )
                cur.execute(
                    "UPDATE onboarding_assignments "
                    "SET status='completed', completion_percentage=100.0, completed_at=%s "
                    "WHERE id = %s",
                    (three_days_ago, a0_id),
                )
                _ok(f"Assignment {a0_id}", "100% completed")

                # Bucket 1: ~65% (mark first 8 of 13 steps complete)
                a1_id, _, _ = assignments[1]
                cur.execute(
                    "SELECT id FROM onboarding_step_progress "
                    "WHERE assignment_id = %s ORDER BY id ASC",
                    (a1_id,),
                )
                steps = [r[0] for r in cur.fetchall()]
                target_done = max(1, int(round(len(steps) * 0.65)))
                if steps:
                    done_ids = steps[:target_done]
                    cur.execute(
                        "UPDATE onboarding_step_progress "
                        "SET status='completed', completed_at=%s "
                        "WHERE id = ANY(%s)",
                        (now - timedelta(days=2), done_ids),
                    )
                    pct = round(target_done / len(steps) * 100, 1)
                    cur.execute(
                        "UPDATE onboarding_assignments "
                        "SET status='in_progress', completion_percentage=%s "
                        "WHERE id = %s",
                        (pct, a1_id),
                    )
                    _ok(f"Assignment {a1_id}", f"{target_done}/{len(steps)} steps ({pct}%)")

                # Bucket 2: ~30% (mark first 4 of 13 steps complete)
                a2_id, _, _ = assignments[2]
                cur.execute(
                    "SELECT id FROM onboarding_step_progress "
                    "WHERE assignment_id = %s ORDER BY id ASC",
                    (a2_id,),
                )
                steps2 = [r[0] for r in cur.fetchall()]
                target_done2 = max(1, int(round(len(steps2) * 0.30)))
                if steps2:
                    done_ids2 = steps2[:target_done2]
                    cur.execute(
                        "UPDATE onboarding_step_progress "
                        "SET status='completed', completed_at=%s "
                        "WHERE id = ANY(%s)",
                        (now - timedelta(days=1), done_ids2),
                    )
                    pct2 = round(target_done2 / len(steps2) * 100, 1)
                    cur.execute(
                        "UPDATE onboarding_assignments "
                        "SET status='in_progress', completion_percentage=%s "
                        "WHERE id = %s",
                        (pct2, a2_id),
                    )
                    _ok(
                        f"Assignment {a2_id}",
                        f"{target_done2}/{len(steps2)} steps ({pct2}%)",
                    )

                # Bucket 3: preboarding-only — leave step progress untouched (already pending)
                # but ensure the preboarding tasks are present per-employee. The
                # /onboarding/assign endpoint already copied template-level tasks
                # at assign time, so this row exists. We zero out completion% as
                # a guard.
                a3_id, a3_emp, a3_tmpl = assignments[3]
                cur.execute(
                    "UPDATE onboarding_assignments "
                    "SET status='in_progress', completion_percentage=0.0 "
                    "WHERE id = %s",
                    (a3_id,),
                )
                cur.execute(
                    "SELECT COUNT(*) FROM preboarding_task_instances "
                    "WHERE company_id = %s AND employee_id = %s",
                    (company_id, a3_emp),
                )
                pb_count_row = cur.fetchone()
                pb_count = pb_count_row[0] if pb_count_row else 0
                _ok(f"Assignment {a3_id}", f"preboarding-only ({pb_count} preboarding tasks)")

                # Bucket 4: just-assigned (assigned_at=today, no progress)
                a4_id, _, _ = assignments[4]
                cur.execute(
                    "UPDATE onboarding_step_progress "
                    "SET status='pending', completed_at=NULL "
                    "WHERE assignment_id = %s",
                    (a4_id,),
                )
                cur.execute(
                    "UPDATE onboarding_assignments "
                    "SET status='in_progress', completion_percentage=0.0, assigned_at=%s "
                    "WHERE id = %s",
                    (now, a4_id),
                )
                _ok(f"Assignment {a4_id}", "just-assigned (today, 0%)")

                _ok("Onboarding progress", "5 buckets varied (100/65/30/preboarding/just)")
    except Exception as exc:
        _fail("Onboarding progress", f"DB error: {exc}")
    finally:
        try:
            conn.close()
        except Exception:
            pass


# ===========================================================================
# Section registry
# ===========================================================================
#
# Each section is a self-contained, idempotent unit. The runner:
#   1. Resolves which sections to run from --section (or "all" by default)
#   2. Skips sections whose required state (login, company_id, employees) is
#      missing in the shared SectionContext
#   3. Wraps every section in try/except so one failure does not kill the rest
#   4. Emits a final summary listing OK / SKIP / FAIL per section
#
# To add a section: write a function and register it in CANONICAL_SECTIONS
# below with its declared dependencies.


class SectionContext:
    """Shared mutable state passed between sections.

    Sections that produce values (company_id, employees, leave_types,
    category_lookup) write them here so later sections can consume them.
    """

    def __init__(self, client: ArborClient, args: argparse.Namespace) -> None:
        self.client = client
        self.args = args
        self.email: str = args.email
        self.password: str = args.password
        self.company_name: str = args.company_name
        self.max_employees: int = min(args.employees, len(EMPLOYEE_PROFILES))
        # Produced state
        self.logged_in: bool = False
        self.company_id: int | None = None
        self.employees: list[dict] | None = None
        self.leave_types: list[dict] | None = None
        self.category_lookup: dict[str, int] | None = None


def _ensure_login(ctx: SectionContext) -> None:
    """Re-establish admin auth on ctx.client. Idempotent — safe to call between sections."""
    _safe_login(ctx.client, ctx.email, ctx.password)
    ctx.logged_in = True


def _lookup_company_id(ctx: SectionContext) -> int | None:
    """Resolve the admin's company_id from /auth/me (no creation)."""
    me_resp = ctx.client.get("/auth/me")
    if me_resp.status_code != 200:
        return None
    return me_resp.json().get("company_id")


# --- Section wrappers ------------------------------------------------------
# Each wrapper has signature: (ctx) -> None. They translate the shared context
# into the underlying seed function's argument shape.


def _section_auth(ctx: SectionContext) -> None:
    seed_auth(ctx.client, ctx.email, ctx.password)
    ctx.logged_in = True


def _section_company(ctx: SectionContext) -> None:
    if not ctx.logged_in:
        _ensure_login(ctx)
    ctx.company_id = seed_company(ctx.client, ctx.company_name)
    # Re-login so the token carries company_id
    _ensure_login(ctx)


def _section_lookup_company(ctx: SectionContext) -> None:
    """For demo-refresh: resolve existing company_id without creating."""
    if not ctx.logged_in:
        _ensure_login(ctx)
    cid = _lookup_company_id(ctx)
    if cid is None:
        _fail("Company lookup", "admin not linked to any company")
        return
    ctx.company_id = cid
    _ok("Company lookup", f"company_id={cid}")


def _section_leave_types(ctx: SectionContext) -> None:
    ctx.leave_types = seed_leave_types(ctx.client)


def _section_employees(ctx: SectionContext) -> None:
    if ctx.company_id is None:
        raise RuntimeError("employees section requires company_id (run 'company' or 'lookup-company' first)")
    ctx.employees = seed_employees(ctx.client, ctx.company_id, ctx.max_employees)
    _ensure_login(ctx)


def _section_employee_profiles(ctx: SectionContext) -> None:
    if not ctx.employees:
        raise RuntimeError("employee-profiles requires employees (run 'employees' first)")
    seed_employee_profiles(ctx.client, ctx.employees)


def _section_role_promotions(ctx: SectionContext) -> None:
    if not ctx.employees:
        raise RuntimeError("role-promotions requires employees (run 'employees' first)")
    seed_role_promotions(ctx.client, ctx.employees)


def _section_salary_components(ctx: SectionContext) -> None:
    if not ctx.employees:
        raise RuntimeError("salary-components requires employees (run 'employees' first)")
    seed_salary_components(ctx.client, ctx.employees)


def _section_payroll(ctx: SectionContext) -> None:
    seed_payroll(ctx.client)


def _section_leave_applications(ctx: SectionContext) -> None:
    if not ctx.employees:
        raise RuntimeError("leave-applications requires employees")
    if not ctx.leave_types:
        raise RuntimeError("leave-applications requires leave_types")
    seed_leave_applications(ctx.client, ctx.employees, ctx.leave_types)
    _ensure_login(ctx)


def _section_claim_categories(ctx: SectionContext) -> None:
    ctx.category_lookup = seed_claim_categories(ctx.client)


def _section_claims(ctx: SectionContext) -> None:
    if not ctx.employees:
        raise RuntimeError("claims requires employees")
    if ctx.category_lookup is None:
        raise RuntimeError("claims requires category_lookup (run 'claim-categories' first)")
    seed_claims(ctx.client, ctx.employees, ctx.category_lookup)
    _ensure_login(ctx)


def _section_attendance(ctx: SectionContext) -> None:
    if not ctx.employees:
        raise RuntimeError("attendance requires employees")
    seed_attendance(ctx.client, ctx.employees)
    _ensure_login(ctx)


def _section_recruitment(ctx: SectionContext) -> None:
    seed_recruitment(ctx.client)


def _section_candidate_pdpa(ctx: SectionContext) -> None:
    if ctx.company_id is None:
        raise RuntimeError("candidate-pdpa requires company_id")
    backfill_candidate_pdpa(ctx.company_id)


def _section_scorecard_templates(ctx: SectionContext) -> None:
    if ctx.company_id is None:
        raise RuntimeError("scorecard-templates requires company_id")
    seed_scorecard_templates(ctx.client, ctx.company_id)


def _section_preboarding_tasks(ctx: SectionContext) -> None:
    if ctx.company_id is None:
        raise RuntimeError("preboarding-tasks requires company_id")
    seed_preboarding_template_tasks(ctx.company_id)


def _section_onboarding(ctx: SectionContext) -> None:
    if not ctx.employees:
        raise RuntimeError("onboarding requires employees")
    seed_onboarding(ctx.client, ctx.employees)


def _section_admin_profile(ctx: SectionContext) -> None:
    if ctx.company_id is None:
        raise RuntimeError("admin-profile requires company_id")
    seed_admin_employee_profile(ctx.client, ctx.company_id)


def _section_onboarding_progress(ctx: SectionContext) -> None:
    if ctx.company_id is None:
        raise RuntimeError("onboarding-progress requires company_id")
    vary_onboarding_progress(ctx.company_id)


# Canonical section order — used when --section is omitted or "all" is given.
# Names are stable: scripts and CI rely on them.
CANONICAL_SECTIONS: list[tuple[str, Callable[[SectionContext], None], str]] = [
    ("auth", _section_auth, "Register/login the admin user"),
    ("company", _section_company, "Create demo company (or reuse existing)"),
    ("leave-types", _section_leave_types, "Seed Singapore statutory leave types"),
    ("employees", _section_employees, "Create employees via invitation flow"),
    ("employee-profiles", _section_employee_profiles, "Enrich employee profile fields"),
    ("role-promotions", _section_role_promotions, "Promote a few employees to HR/manager"),
    ("salary-components", _section_salary_components, "Salary components per employee"),
    ("payroll", _section_payroll, "Monthly payroll runs (non-fatal)"),
    ("leave-applications", _section_leave_applications, "Leave applications (logs in as employees)"),
    ("claim-categories", _section_claim_categories, "Claim category catalogue"),
    ("claims", _section_claims, "Expense claims (logs in as employees)"),
    ("attendance", _section_attendance, "Attendance records (logs in as employees)"),
    ("recruitment", _section_recruitment, "Job posting + candidates + applications"),
    ("candidate-pdpa", _section_candidate_pdpa, "Round-13: backfill PDPA consent (DB)"),
    ("scorecard-templates", _section_scorecard_templates, "Round-13: 5 starter scorecards (DB)"),
    ("preboarding-tasks", _section_preboarding_tasks, "Round-13: default-template preboarding (DB)"),
    ("onboarding", _section_onboarding, "Onboarding assignments (per-employee)"),
    ("admin-profile", _section_admin_profile, "Round-13: enrich Demo Admin's Employee record (DB)"),
    ("onboarding-progress", _section_onboarding_progress, "Round-13: vary onboarding completion (DB)"),
]


# Section aliases — expanded into concrete section names.
# 'demo-refresh' handles the round-13 demo data refresh against an EXISTING
# prod company without recreating users or rerunning the heavy employee/payroll
# flow. This is the safe path for prod — it never touches the auth, company,
# employees, or payroll sections.
SECTION_ALIASES: dict[str, list[str]] = {
    "all": [name for name, _, _ in CANONICAL_SECTIONS],
    "demo-refresh": [
        "auth",
        "lookup-company",
        "candidate-pdpa",
        "scorecard-templates",
        "preboarding-tasks",
        "admin-profile",
        "onboarding-progress",
    ],
    # Round-13-only set without auth bootstrap — for callers that already
    # have an authenticated client (CI, embedded use). Almost no one wants
    # this; included for completeness.
    "round13": [
        "candidate-pdpa",
        "scorecard-templates",
        "preboarding-tasks",
        "admin-profile",
        "onboarding-progress",
    ],
}

# 'lookup-company' is not in CANONICAL_SECTIONS because it is only meaningful
# inside aliases like demo-refresh — it never appears in 'all'.
ALIAS_ONLY_SECTIONS: dict[str, Callable[[SectionContext], None]] = {
    "lookup-company": _section_lookup_company,
}


def _resolve_sections(requested: list[str]) -> list[str]:
    """Expand aliases and validate names. Returns concrete section names in run order."""
    known_names = {name for name, _, _ in CANONICAL_SECTIONS} | set(ALIAS_ONLY_SECTIONS) | set(SECTION_ALIASES)
    expanded: list[str] = []
    seen: set[str] = set()
    for raw in requested:
        if raw in SECTION_ALIASES:
            for name in SECTION_ALIASES[raw]:
                if name not in seen:
                    expanded.append(name)
                    seen.add(name)
        elif raw in known_names:
            if raw not in seen:
                expanded.append(raw)
                seen.add(raw)
        else:
            raise ValueError(f"Unknown section '{raw}'. Use --list-sections to see valid names.")
    return expanded


def _section_callable(name: str) -> Callable[[SectionContext], None]:
    for n, fn, _ in CANONICAL_SECTIONS:
        if n == name:
            return fn
    if name in ALIAS_ONLY_SECTIONS:
        return ALIAS_ONLY_SECTIONS[name]
    raise KeyError(name)


def _print_sections_table() -> None:
    _print("Available sections:\n")
    for name, _, desc in CANONICAL_SECTIONS:
        _print(f"  {name:<22} {desc}")
    _print("\nAlias-only sections:")
    for name in ALIAS_ONLY_SECTIONS:
        _print(f"  {name:<22} (alias bootstrap)")
    _print("\nAliases (expand to multiple sections):")
    for alias, members in SECTION_ALIASES.items():
        _print(f"  {alias:<22} -> {', '.join(members)}")


# ===========================================================================
# Main
# ===========================================================================


def _validate_prod_password(api_url: str, password: str) -> None:
    """Refuse to run against a non-localhost API with the default demo password.

    The default password 'CentralDemo2026!' is the LOCAL dev seed value; running
    with it against prod will either (a) fail because prod uses a different
    password, or (b) succeed and overwrite production demo state with stale
    fixtures. Both are bad. Force the operator to set ADMIN_PASSWORD explicitly.
    """
    is_local = (
        "localhost" in api_url
        or "127.0.0.1" in api_url
        or "0.0.0.0" in api_url
    )
    if is_local:
        return
    if password == "CentralDemo2026!" and not os.environ.get("ADMIN_PASSWORD"):
        _fail(
            "Refusing to run against non-local API with default password",
            "Set ADMIN_PASSWORD env var to the actual admin password",
        )
        sys.exit(2)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed demo data for Arbor HRIS platform.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python scripts/seed_demo_data.py\n"
            "  python scripts/seed_demo_data.py --list-sections\n"
            "  python scripts/seed_demo_data.py --section demo-refresh\n"
            "  python scripts/seed_demo_data.py --section auth --section company\n"
            "  python scripts/seed_demo_data.py --section demo-refresh --dry-run\n"
            "\n"
            "Env vars: ARBOR_API_URL, ADMIN_EMAIL, ADMIN_PASSWORD, DATABASE_URL\n"
        ),
    )
    parser.add_argument(
        "--api-url",
        default=DEFAULT_API_URL,
        help=f"Arbor API base URL (default: $ARBOR_API_URL or {DEFAULT_API_URL})",
    )
    parser.add_argument(
        "--email",
        default=DEFAULT_EMAIL,
        help=f"Admin user email (default: $ADMIN_EMAIL or {DEFAULT_EMAIL})",
    )
    parser.add_argument(
        "--password",
        default=DEFAULT_PASSWORD,
        help="Admin user password (default: $ADMIN_PASSWORD)",
    )
    parser.add_argument(
        "--company-name",
        default=DEFAULT_COMPANY,
        help=f"Company name (default: {DEFAULT_COMPANY})",
    )
    parser.add_argument(
        "--employees",
        type=int,
        default=DEFAULT_EMPLOYEE_COUNT,
        help=f"Number of employees to create (max {len(EMPLOYEE_PROFILES)}, default: {DEFAULT_EMPLOYEE_COUNT})",
    )
    parser.add_argument(
        "--section",
        action="append",
        default=None,
        help=(
            "Section name or alias to run. Can be repeated. Default: 'all'. "
            "Use --list-sections to see options. Aliases: all, demo-refresh, round13."
        ),
    )
    parser.add_argument(
        "--list-sections",
        action="store_true",
        help="Print available sections and aliases, then exit.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show which sections would run without executing them.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Records intent that the seeder is being run against a freshly reset database.",
    )
    args = parser.parse_args()

    if args.list_sections:
        _print_sections_table()
        return

    # Resolve sections
    requested = args.section if args.section else ["all"]
    try:
        sections = _resolve_sections(requested)
    except ValueError as exc:
        _fail("Section resolution", str(exc))
        sys.exit(2)

    if not sections:
        _fail("No sections to run", "")
        sys.exit(2)

    # Production safety: refuse default password against non-localhost
    _validate_prod_password(args.api_url, args.password)

    max_employees = min(args.employees, len(EMPLOYEE_PROFILES))

    _print("=" * 60)
    _print("Arbor HRIS — Demo Data Seeder")
    _print("=" * 60)
    _print(f"API URL:    {args.api_url}")
    _print(f"Admin:      {args.email}")
    _print(f"Company:    {args.company_name}")
    _print(f"Employees:  {max_employees}")
    _print(f"Sections:   {', '.join(sections)}")
    _print(f"Dry run:    {args.dry_run}")
    _print(f"Reset:      {args.reset}")
    _print(f"Timestamp:  {datetime.now().isoformat()}")
    _print("=" * 60)

    if args.dry_run:
        _print("\nDRY RUN — would execute the following sections in order:")
        for name in sections:
            desc = next((d for n, _, d in CANONICAL_SECTIONS if n == name), "")
            if not desc and name in ALIAS_ONLY_SECTIONS:
                desc = "(alias bootstrap)"
            _print(f"  - {name:<22} {desc}")
        _print("\nNo changes made. Re-run without --dry-run to execute.")
        return

    client = ArborClient(args.api_url)
    ctx = SectionContext(client, args)
    results: list[tuple[str, str, str]] = []  # (section, status, detail)

    try:
        # Health check (advisory; do not block — backend may be slow on cold start)
        _print("\nChecking API connectivity...")
        try:
            health_resp = client._client.get(
                f"{args.api_url}/health",
                timeout=10.0,
            )
            if health_resp.status_code == 200:
                _ok("API reachable")
            else:
                _print(f"  [WARN] Health check returned {health_resp.status_code} — proceeding anyway")
        except httpx.ConnectError:
            _fail("API unreachable", f"Cannot connect to {args.api_url}")
            _print("\nIs the Arbor server running? Start it with:")
            _print("  python -m hr_advisory.api.main")
            sys.exit(1)
        except Exception as exc:
            _print(f"  [WARN] Health check failed ({type(exc).__name__}) — proceeding anyway")

        for name in sections:
            try:
                fn = _section_callable(name)
            except KeyError:
                results.append((name, "FAIL", "no such section"))
                _fail(f"Section '{name}'", "no such section")
                continue
            try:
                fn(ctx)
                results.append((name, "OK", ""))
            except KeyboardInterrupt:
                results.append((name, "FAIL", "interrupted"))
                raise
            except httpx.HTTPStatusError as exc:
                detail = f"HTTP {exc.response.status_code}: {exc.response.text[:200]}"
                results.append((name, "FAIL", detail))
                _print(f"  [WARN] Section '{name}' failed: {detail} — continuing")
            except Exception as exc:
                detail = f"{type(exc).__name__}: {str(exc)[:200]}"
                results.append((name, "FAIL", detail))
                _print(f"  [WARN] Section '{name}' failed: {detail} — continuing")

        # Summary
        ok_count = sum(1 for _, s, _ in results if s == "OK")
        fail_count = sum(1 for _, s, _ in results if s == "FAIL")
        _print("\n" + "=" * 60)
        _print(f"Demo data seeding finished: {ok_count} OK, {fail_count} FAIL")
        _print("=" * 60)
        if fail_count:
            _print("\nFailures:")
            for name, status, detail in results:
                if status == "FAIL":
                    _print(f"  [FAIL] {name}: {detail}")
        if "all" in requested or len(sections) > 5:
            _print(f"\nDemo accounts:")
            _print(f"  Owner:      {args.email} / {args.password}")
            _print(f"  HR Manager: grace.koh@central-solutions.sg / Employee2026!")
            _print(f"  Employee:   lily.phang@central-solutions.sg / Employee2026!")
            _print(f"  Company:    {args.company_name}")
            _print(f"  API URL:    {args.api_url}")
        _print("")

        # Exit non-zero if any section failed (lets CI catch silent breakage).
        if fail_count:
            sys.exit(1)

    except httpx.ConnectError:
        _print(f"\nConnection error: Could not reach {args.api_url}")
        sys.exit(1)
    except KeyboardInterrupt:
        _print("\n\nSeeding interrupted by user.")
        sys.exit(130)
    finally:
        client.close()


if __name__ == "__main__":
    main()
