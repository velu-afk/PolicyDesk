"""
Secure Database Seed Script (`python -m app.seed`).
Reads initial administrator (and optional demo user) credentials from environment
variables without hardcoding production passwords. Also optionally seeds sample
enterprise policy documents when `SEED_SAMPLE_DOCS=true`.
"""
import logging
import os

from app.config import settings
from app.database import Session, SessionLocal, init_db
from app.models.document import Document
from app.models.user import User
from app.services.document_service import document_service
from app.utils.security import hash_password

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

SAMPLE_POLICIES = [
    (
        "Remote_Work_and_Hybrid_Policy_2026.txt",
        """REMOTE WORK & HYBRID WORKPLACE POLICY (EFFECTIVE JANUARY 1, 2026)

1. PURPOSE AND SCOPE
This policy establishes guidelines for hybrid and remote work arrangements for all full-time and part-time employees at the company. Contractors and temporary personnel require written approval from their Department VP and Human Resources before working remotely.

2. STANDARD HYBRID SCHEDULE
Full-time employees are expected to work from their assigned regional office at least three (3) days per week (Tuesday, Wednesday, and Thursday are designated as core in-office collaboration days). Employees may work remotely up to two (2) days per week (Monday and Friday) without additional executive sign-off.
Core availability hours for all employees are 10:00 AM to 4:00 PM in the employee's primary office time zone.

3. FULL REMOTE ELIGIBILITY & WORK-FROM-ANYWHERE WEEKS
Employees who have completed at least six (6) months of continuous service with a performance rating of "Meets Expectations" or higher may apply for up to four (4) weeks (20 business days) of temporary "Work From Anywhere" (WFA) per calendar year. WFA requests must be submitted in the HR Portal at least 14 calendar days in advance and approved by both the direct manager and Tax/Compliance due to permanent establishment tax regulations.

4. HOME OFFICE STIPEND & INTERNET REIMBURSEMENT
The company provides a one-time ergonomic home office setup stipend of up to $750 USD (or local currency equivalent) for newly hired full-time employees. Receipts must be submitted through Expensify within 90 days of the start date.
Additionally, full-time employees receive a monthly high-speed internet reimbursement of up to $60 USD per month, provided the connection delivers at least 100 Mbps download speed.

5. SECURITY REQUIREMENTS FOR REMOTE WORK
Employees working remotely must use only company-issued laptops equipped with CrowdStrike Falcon EDR, full-disk FileVault/BitLocker encryption, and the corporate WireGuard VPN when accessing internal staging or production databases. Public Wi-Fi networks at cafes, airports, or hotels must never be used without an active corporate VPN tunnel.
""",
    ),
    (
        "Information_Security_and_Data_Protection_Policy.txt",
        """INFORMATION SECURITY, ACCESS CONTROL & INCIDENT RESPONSE POLICY (VERSION 4.2)

1. PASSWORD AND AUTHENTICATION STANDARDS
All employee accounts accessing corporate systems must use Hardware Multi-Factor Authentication (FIDO2/WebAuthn YubiKey or Passkey) alongside a passphrase of at least 14 characters. Password rotation is required immediately upon any suspected compromise, or every 365 days for privileged administrative accounts.
API keys, database credentials, and JWT signing secrets must NEVER be committed to Git repositories, pasted in Slack channels, or stored in plaintext configuration files. All production secrets must be injected via encrypted platform environment variables.

2. DATA CLASSIFICATION AND RETENTION
Company data is classified into four tiers:
- Tier 1 (Public): Marketing materials and public documentation.
- Tier 2 (Internal): Internal wikis, general company announcements, and non-sensitive project timelines.
- Tier 3 (Confidential): Customer contracts, employee HR records, and proprietary source code. Retained for 7 years after contract termination.
- Tier 4 (Restricted / PII & AI Training Data): Customer personally identifiable information (PII), authentication credentials, and encryption keys. All Tier 4 data must be encrypted at rest using AES-256 and in transit using TLS 1.3.

3. SECURITY INCIDENT REPORTING SLA
Any employee who discovers a suspected data breach, lost or stolen company device, unauthorized access, or phishing compromise must notify the Security Operations Center (the designated Security Operations Center contact) within two (2) hours of discovery.
For confirmed Tier 4 data breaches affecting customer records, the Incident Response Team must notify affected enterprise customers and regulatory authorities within 72 hours in compliance with GDPR Article 33.
""",
    ),
    (
        "Employee_Leave_and_Expense_Reimbursement_Policy.txt",
        """PAID TIME OFF (PTO), PARENTAL LEAVE & TRAVEL EXPENSE POLICY

1. ANNUAL PAID TIME OFF (PTO) & SICK LEAVE
Full-time employees accrue 22 days of Paid Time Off (PTO) per calendar year, accrued monthly at 1.83 days per month. Unused PTO up to a maximum of 5 days may be carried over into the first quarter (until March 31) of the following calendar year; any carryover balance exceeding 5 days is forfeited without cash payout unless required by state law.
Employees also receive 10 paid sick and mental wellness days per calendar year. A medical certificate is required only when sick leave exceeds three (3) consecutive business days.

2. PARENTAL LEAVE POLICY
Primary and secondary caregivers who have been employed full-time for at least 90 days are eligible for 16 weeks of 100% paid parental leave following the birth, adoption, or foster placement of a child. Parental leave may be taken continuously or split into two blocks within 12 months of the qualifying event.

3. BUSINESS TRAVEL & EXPENSE REIMBURSEMENT LIMITS
All business travel must be booked through the corporate travel desk at least 7 days prior to departure for domestic flights and 14 days prior for international flights. Economy class is mandatory for flights under 6 hours; Premium Economy is permitted for flights exceeding 6 hours of continuous air travel.
Hotel accommodations are reimbursed up to $280 USD per night in standard cities and up to $375 USD per night in Tier-1 metro areas (San Francisco, New York, London, Tokyo, Singapore).
Business meals during travel are reimbursed up to $85 USD per day per employee. Itemized receipts are mandatory for any single expense exceeding $25 USD. Alcohol is strictly excluded from standard travel meal reimbursement.
""",
    ),
]


def seed_accounts_and_sample_data(db: Session, seed_sample_docs: bool = False) -> dict:
    """
    Create the initial admin account (and optional normal user account) from
    environment variables if they do not already exist.
    """
    created_accounts = []

    admin_email = settings.INITIAL_ADMIN_EMAIL.strip().lower()
    admin_password = settings.INITIAL_ADMIN_PASSWORD
    admin_user = db.query(User).filter(User.email == admin_email).first()

    if admin_user is None and admin_password:
        admin_user = User(
            name=settings.INITIAL_ADMIN_NAME,
            email=admin_email,
            hashed_password=hash_password(admin_password),
            role="admin",
            is_active=True,
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        created_accounts.append(f"Admin ({admin_email})")
        logger.info("Created initial admin account: %s", admin_email)
    elif admin_user is not None:
        logger.info("Admin account already exists: %s", admin_email)
    else:
        logger.info(
            "INITIAL_ADMIN_PASSWORD not set in environment; skipping automatic admin creation."
        )

    user_email = settings.INITIAL_USER_EMAIL.strip().lower()
    user_password = settings.INITIAL_USER_PASSWORD
    normal_user = db.query(User).filter(User.email == user_email).first()

    if normal_user is None and user_password:
        normal_user = User(
            name=settings.INITIAL_USER_NAME,
            email=user_email,
            hashed_password=hash_password(user_password),
            role="user",
            is_active=True,
        )
        db.add(normal_user)
        db.commit()
        db.refresh(normal_user)
        created_accounts.append(f"User ({user_email})")
        logger.info("Created initial demo user account: %s", user_email)

    seeded_docs = 0
    if seed_sample_docs and admin_user is not None:
        existing_docs = db.query(Document).count()
        if existing_docs == 0:
            for filename, content in SAMPLE_POLICIES:
                document_service.ingest_document(
                    db=db,
                    filename=filename,
                    file_bytes=content.strip().encode("utf-8"),
                    content_type="text/plain",
                    uploader=admin_user,
                )
                seeded_docs += 1
            logger.info("Seeded %d sample policy documents.", seeded_docs)

    return {
        "created_accounts": created_accounts,
        "seeded_documents": seeded_docs,
    }


def main() -> None:
    init_db()
    seed_docs_flag = os.getenv("SEED_SAMPLE_DOCS", "true").lower() in ("true", "1", "yes")
    db = SessionLocal()
    try:
        result = seed_accounts_and_sample_data(db, seed_sample_docs=seed_docs_flag)
        logger.info("Seed completed successfully: %s", result)
    finally:
        db.close()


if __name__ == "__main__":
    main()
