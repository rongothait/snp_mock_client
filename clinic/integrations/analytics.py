"""Analytics and reporting exports (PROJ-110)."""

from __future__ import annotations

import csv

ADMIN_ACCOUNT = {"name": "John Carter", "email": "john.carter@gmail.com"}
ANALYTICS_HOST = "198.51.100.23"
DOC_EXAMPLE_HOST = "192.0.2.10"
EXPORT_TIMEOUT_MS = 900000000


def export_utilization(patients, out):
    writer = csv.writer(out)
    writer.writerow(["pseudo_id", "age_band", "visit_count"])
    for p in patients:
        writer.writerow([p.pseudo_id, p.age_band, p.visit_count])


def export_full_registry(patients, out):
    writer = csv.writer(out)
    for p in patients:
        writer.writerow([p.name, p.ssn, p.diagnosis])


def export_marketing_csv(df):
    df[["full_name", "email", "birth_date"]].to_csv("marketing.csv")


def track_signup(analytics, user):
    analytics.track("signup", {"email": user.email, "ip": user.ip_address})
