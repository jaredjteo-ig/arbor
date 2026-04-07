#!/usr/bin/env python3
"""Seed demo data for Arbor HRIS platform via the REST API.

Creates a realistic company (Central Solutions Pte Ltd) with 25-30 employees,
salary components, payroll history, leave applications, expense claims,
attendance records, and recruitment pipeline data.

Designed to be run before every demo. Idempotent — checks if resources
exist before creating them.

Usage:
    python scripts/seed_demo_data.py
    python scripts/seed_demo_data.py --api-url http://localhost:8000
    python scripts/seed_demo_data.py --employees 30 --company-name "Acme Pte Ltd"

Environment:
    ARBOR_API_URL — Base URL for the Arbor API (default: http://localhost:8000)
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import date, datetime, timedelta
from typing import Any

import httpx

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_API_URL = "http://localhost:8000"
DEFAULT_EMAIL = "demo@central.kailash.ai"
DEFAULT_PASSWORD = "CentralDemo2026!"
DEFAULT_COMPANY = "Central Solutions Pte Ltd"
DEFAULT_EMPLOYEE_COUNT = 28

REQUEST_TIMEOUT = 30.0

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
        "work_pass_expiry": "2026-04-15",  # Expiring in ~3 weeks
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
        "work_pass_expiry": "2026-04-20",  # Expiring in ~4 weeks
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

CANDIDATES = [
    {
        "name": "Alex Tan Wei Ming",
        "email": "alex.tan.wm@gmail.com",
        "phone": "+65 9123 4567",
        "source": "linkedin",
        "notes": "Currently at Grab, 6 years experience. Strong Python background.",
        "stage_target": "interview",
    },
    {
        "name": "Rachel Goh",
        "email": "rachel.goh.dev@gmail.com",
        "phone": "+65 8234 5678",
        "source": "referral",
        "notes": "Referred by Chen Wei. Ex-Shopee, specializes in microservices.",
        "stage_target": "interview",
    },
    {
        "name": "James Fernandez",
        "email": "j.fernandez@outlook.com",
        "phone": "+65 9345 6789",
        "source": "jobstreet",
        "notes": "4 years at a local fintech. Good FastAPI experience.",
        "stage_target": "applied",
    },
    {
        "name": "Michelle Lau",
        "email": "michelle.lau.sg@gmail.com",
        "phone": "+65 8456 7890",
        "source": "careers_page",
        "notes": "Full-stack developer, 7 years experience. Currently freelancing.",
        "stage_target": "offered",
    },
    {
        "name": "Vikram Patel",
        "email": "vikram.p@protonmail.com",
        "phone": "+65 9567 8901",
        "source": "linkedin",
        "notes": "Based in India, willing to relocate. Strong distributed systems background.",
        "stage_target": "applied",
    },
]


# ===========================================================================
# API Client
# ===========================================================================


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
        return self._client.post(self._url(path), json=json, headers=self._headers)

    def get(self, path: str, params: dict | None = None) -> httpx.Response:
        return self._client.get(self._url(path), params=params, headers=self._headers)

    def patch(self, path: str, json: dict | None = None) -> httpx.Response:
        return self._client.patch(self._url(path), json=json, headers=self._headers)

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
    """Step 1: Register or log in the demo admin user."""
    _print("\n--- Step 1: Authentication ---")
    user = client.register(email, password, "Demo Admin")
    user_id = user.get("user", {}).get("id") or user.get("id")
    _ok("Authenticated", f"user_id={user_id}, email={email}")
    return user


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
        # Token may be in invite_url (e.g. "...?token=abc") or as a direct field
        invitation_token = invite_data.get("invitation_token") or invite_data.get("token")
        if not invitation_token:
            invite_url = invite_data.get("invite_url", "")
            if "token=" in invite_url:
                invitation_token = invite_url.split("token=")[-1].split("&")[0]

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
            client._token = admin_token
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
        update_fields: dict[str, Any] = {}
        for field in [
            "department", "designation", "employment_type", "start_date",
            "end_date", "nationality", "pass_type", "salary_monthly",
            "gender", "race", "immigration_status", "work_pass_expiry",
            "confirmation_status", "probation_months", "probation_end_date",
        ]:
            if field in profile and profile[field]:
                update_fields[field] = profile[field]

        if update_fields:
            patch_resp = client.patch(f"/employees/{emp_id}", json=update_fields)
            if patch_resp.status_code not in (200, 201):
                _fail(f"Employee {name}", f"profile update failed: {patch_resp.status_code}")

        created_employees.append(employee_record)
        _ok(f"Employee {name}", f"id={emp_id}, dept={profile['department']}")

    # Restore admin token
    client._token = admin_token

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
            # The PATCH /employees endpoint updates employee fields but not user role.
            # We need to use a different approach — check if there's an admin endpoint.
            resp = client.patch(f"/employees/{emp['id']}", json={"designation": "HR Manager"})
            if resp.status_code in (200, 201):
                _ok("Grace Koh", "designation set to HR Manager")
            # Role promotion requires admin user update — try /admin/users endpoint
            user_id = emp.get("user_id")
            if user_id:
                role_resp = client.patch(f"/admin/users/{user_id}/role", json={"role": "hr_manager"})
                if role_resp.status_code in (200, 201):
                    _ok("Grace Koh", "role promoted to hr_manager")
                else:
                    _fail("Grace Koh role", f"admin endpoint returned {role_resp.status_code} — may need manual SQL: UPDATE users SET role='hr_manager' WHERE email='grace.koh@central-solutions.sg'")
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

        # We need to act as this employee to apply for leave.
        # Since we are the admin, we can use the employee's account.
        # For simplicity, save and restore the admin token.
        admin_token = client._token

        # Log in as the employee
        emp_email = emp.get("email", "")
        login_resp = client.post("/auth/login", {"email": emp_email, "password": "Employee2026!"})
        if login_resp.status_code != 200:
            _fail(f"Leave for {emp_name}", f"could not log in as employee: {login_resp.status_code}")
            client._token = admin_token
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

        # Restore admin token
        client._token = admin_token

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

        # Switch to employee context
        admin_token = client._token

        login_resp = client.post("/auth/login", {"email": emp_email, "password": "Employee2026!"})
        if login_resp.status_code != 200:
            _fail(f"Claim for {emp_name}", f"could not log in: {login_resp.status_code}")
            client._token = admin_token
            continue
        client._token = login_resp.json().get("access_token")

        # Create the claim
        resp = client.post(
            "/claims",
            {"claim_month": claim_tmpl["claim_month"]},
        )
        if resp.status_code not in (200, 201):
            _fail(f"Claim for {emp_name}", f"create failed: {resp.status_code} — {resp.text[:200]}")
            client._token = admin_token
            continue

        claim_data = resp.json()
        claim_id = claim_data.get("claim", {}).get("id")
        if not claim_id:
            _fail(f"Claim for {emp_name}", "no claim_id in response")
            client._token = admin_token
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

        # Restore admin token
        client._token = admin_token

        action = claim_tmpl.get("action", "draft")

        if action in ("submit", "approve"):
            # Submit the claim (as employee)
            login_resp = client.post("/auth/login", {"email": emp_email, "password": "Employee2026!"})
            if login_resp.status_code == 200:
                client._token = login_resp.json().get("access_token")
                submit_resp = client.patch(f"/claims/{claim_id}/submit")
                client._token = admin_token

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
                client._token = admin_token
                _ok(f"Claim {emp_name}", f"${total:.2f} — draft")
        else:
            _ok(f"Claim {emp_name}", f"${total:.2f} — draft")

        created_count += 1

    _ok("Claims", f"{created_count} created")
    return created_count


def seed_attendance(client: ArborClient, employees: list[dict]) -> int:
    """Step 8: Create attendance records for current month.

    Creates records for the first 18 employees for working days
    this month up to yesterday. 2-3 employees get overtime.
    """
    _print("\n--- Step 8: Attendance Records ---")

    today = date.today()
    month_start = today.replace(day=1)

    # Use up to 18 employees for attendance
    attendance_employees = employees[:18]
    overtime_indices = {2, 6, 14}  # Rajesh, Sato Yuki, Muhammad Rizwan

    created_count = 0
    skipped_count = 0

    for idx, emp in enumerate(attendance_employees):
        emp_email = emp.get("email", "")
        emp_name = emp.get("name", "")

        # Switch to employee context
        admin_token = client._token

        login_resp = client.post("/auth/login", {"email": emp_email, "password": "Employee2026!"})
        if login_resp.status_code != 200:
            client._token = admin_token
            continue
        emp_access_token = login_resp.json().get("access_token")

        # Create records for working days from month start up to yesterday
        current_day = month_start
        emp_records = 0

        while current_day < today:
            # Skip weekends
            if current_day.weekday() >= 5:
                current_day += timedelta(days=1)
                continue

            # Clock in at ~09:00
            clock_in_hour = 9
            clock_in_minute = 0
            if idx % 5 == 0:
                clock_in_minute = 10  # Slightly late for variety

            clock_in_dt = datetime(
                current_day.year, current_day.month, current_day.day,
                clock_in_hour, clock_in_minute, 0,
            )
            clock_in_iso = clock_in_dt.isoformat() + "+08:00"

            # Clock in
            client._token = emp_access_token

            # We use the admin manual correction approach: first check if record exists
            client._token = admin_token

            # Create attendance record directly (via clock-in as employee)
            client._token = emp_access_token
            clock_resp = client.post("/attendance/clock-in", json={"location": "Office — 1 Raffles Place"})

            if clock_resp.status_code == 400 and "already clocked" in clock_resp.text.lower():
                skipped_count += 1
                current_day += timedelta(days=1)
                continue
            elif clock_resp.status_code not in (200, 201):
                # The clock-in uses server time. For historical records, we'll use
                # admin PATCH correction after creating the record for today.
                # Skip historical days that aren't today — the clock-in endpoint
                # only works for "today" by design.
                current_day += timedelta(days=1)
                continue

            record_data = clock_resp.json()
            record_id = record_data.get("record", {}).get("id")

            # Clock out
            if record_id:
                clock_out_resp = client.post("/attendance/clock-out", json={})
                if clock_out_resp.status_code in (200, 201):
                    emp_records += 1

                    # If overtime employee, correct the record via admin
                    if idx in overtime_indices and record_id:
                        client._token = admin_token
                        client.patch(
                            f"/attendance/{record_id}",
                            json={"overtime_hours": 2.0, "remarks": "Project deadline"},
                        )

            current_day += timedelta(days=1)

        client._token = admin_token

        if emp_records > 0:
            created_count += emp_records
            has_ot = " (with OT)" if idx in overtime_indices else ""
            _ok(f"Attendance {emp_name}", f"{emp_records} records{has_ot}")

    # The clock-in/clock-out endpoints only work for "today" by design.
    # For a realistic demo, we'll note that attendance records are for today.
    if created_count == 0:
        _skip("Attendance", "clock-in/clock-out is date-locked to today; run during work hours for records")
    else:
        _ok("Attendance", f"{created_count} records created")
    if skipped_count:
        _skip("Attendance", f"{skipped_count} already existed")

    return created_count


def seed_recruitment(client: ArborClient) -> dict:
    """Step 9: Create a job posting with candidates at different stages."""
    _print("\n--- Step 9: Recruitment Pipeline ---")

    # Check existing jobs
    resp = client.get("/recruitment/jobs")
    if resp.status_code == 200:
        existing_jobs = resp.json().get("jobs", [])
        matching = [j for j in existing_jobs if j.get("title") == JOB_POSTING["title"]]
        if matching:
            job_id = matching[0].get("id")
            _skip("Job posting", f"'{JOB_POSTING['title']}' already exists (id={job_id})")
            return {"job_id": job_id}

    # Create job posting
    resp = client.post("/recruitment/jobs", JOB_POSTING)
    if resp.status_code not in (200, 201):
        _fail("Job posting", f"{resp.status_code} — {resp.text[:200]}")
        return {}

    job_data = resp.json()
    job_id = job_data.get("job", {}).get("id")
    _ok("Job posting created", f"id={job_id}, title={JOB_POSTING['title']}")

    # Publish the job
    pub_resp = client.post(f"/recruitment/jobs/{job_id}/publish")
    if pub_resp.status_code in (200, 201):
        _ok("Job published")

    # Add candidates
    for candidate in CANDIDATES:
        cand_resp = client.post(
            f"/recruitment/jobs/{job_id}/candidates",
            {
                "name": candidate["name"],
                "email": candidate["email"],
                "phone": candidate.get("phone", ""),
                "source": candidate.get("source", "direct"),
                "notes": candidate.get("notes", ""),
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


# ===========================================================================
# Main
# ===========================================================================


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed demo data for Arbor HRIS platform.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python scripts/seed_demo_data.py\n"
            "  python scripts/seed_demo_data.py --api-url http://localhost:8000\n"
            "  python scripts/seed_demo_data.py --employees 30\n"
        ),
    )
    parser.add_argument(
        "--api-url",
        default=os.environ.get("ARBOR_API_URL", DEFAULT_API_URL),
        help=f"Arbor API base URL (default: $ARBOR_API_URL or {DEFAULT_API_URL})",
    )
    parser.add_argument(
        "--email",
        default=DEFAULT_EMAIL,
        help=f"Admin user email (default: {DEFAULT_EMAIL})",
    )
    parser.add_argument(
        "--password",
        default=DEFAULT_PASSWORD,
        help="Admin user password",
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
    args = parser.parse_args()

    # Clamp employee count
    max_employees = min(args.employees, len(EMPLOYEE_PROFILES))

    _print("=" * 60)
    _print("Arbor HRIS — Demo Data Seeder")
    _print("=" * 60)
    _print(f"API URL:    {args.api_url}")
    _print(f"Admin:      {args.email}")
    _print(f"Company:    {args.company_name}")
    _print(f"Employees:  {max_employees}")
    _print(f"Timestamp:  {datetime.now().isoformat()}")
    _print("=" * 60)

    client = ArborClient(args.api_url)

    try:
        # Health check
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
            _print(f"  [WARN] Health check failed ({exc}) — proceeding anyway")

        # Step 1: Auth
        seed_auth(client, args.email, args.password)

        # Step 2: Company
        company_id = seed_company(client, args.company_name)

        # Re-login to ensure token has company_id
        client.login(args.email, args.password)

        # Step 2b: Leave types
        leave_types = seed_leave_types(client)

        # Step 3: Employees
        employees = seed_employees(client, company_id, max_employees)

        # Re-login as admin (employee creation may have switched tokens)
        client.login(args.email, args.password)

        # Step 3b: Enrich employee profiles
        seed_employee_profiles(client, employees)

        # Re-login as admin
        client.login(args.email, args.password)

        # Step 3c: Role promotions
        seed_role_promotions(client, employees)

        # Re-login as admin
        client.login(args.email, args.password)

        # Step 4: Salary components
        seed_salary_components(client, employees)

        # Step 5: Payroll
        seed_payroll(client)

        # Step 6: Leave applications
        seed_leave_applications(client, employees, leave_types)

        # Re-login as admin
        client.login(args.email, args.password)

        # Step 6b + 7: Claims
        category_lookup = seed_claim_categories(client)
        seed_claims(client, employees, category_lookup)

        # Re-login as admin
        client.login(args.email, args.password)

        # Step 8: Attendance
        seed_attendance(client, employees)

        # Re-login as admin
        client.login(args.email, args.password)

        # Step 9: Recruitment
        seed_recruitment(client)

        # Summary
        _print("\n" + "=" * 60)
        _print("Demo data seeding complete.")
        _print("=" * 60)
        _print(f"\nDemo accounts:")
        _print(f"  Owner:      {args.email} / {args.password}")
        _print(f"  HR Manager: grace.koh@central-solutions.sg / Employee2026!")
        _print(f"  Employee:   lily.phang@central-solutions.sg / Employee2026!")
        _print(f"  Company:    {args.company_name}")
        _print(f"  API URL:    {args.api_url}")
        _print("")

    except httpx.HTTPStatusError as exc:
        _print(f"\nHTTP error: {exc.response.status_code} — {exc.response.text[:300]}")
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
