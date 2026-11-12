"""
Shared test helpers and fixtures for PolicyDesk automated test suite.
Works with both `unittest` (`python3 -m unittest discover -s tests`) and `pytest`.
Generates real multi-page PDF documents in memory using reportlab/fpdf2 and
isolates database state per test case.
"""
import io
import os
from typing import Dict, Tuple

# Force deterministic offline embedding/generation and isolated test DB before importing app
os.environ["DATABASE_URL"] = "sqlite:///./test_policydesk.db"
os.environ["GEMINI_API_KEY"] = "mock"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-automated-suite-policydesk-2026"
os.environ["INITIAL_ADMIN_EMAIL"] = "admin@policydesk.io"
os.environ["INITIAL_ADMIN_PASSWORD"] = "AdminTestPass_2026!"

from fastapi.testclient import TestClient
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import simpleSplit

from app.database import Base, SessionLocal, engine, init_db
from app.main import app
from app.models.user import User
from app.utils.security import create_access_token, hash_password


def reset_test_database() -> None:
    """Drop and recreate all tables cleanly before a test."""
    Base.metadata.drop_all(bind=engine)
    init_db()


def create_test_users() -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    Seed one admin user and one normal user in the test database, returning
    their Authorization Bearer headers.
    """
    db = SessionLocal()
    try:
        admin = User(
            name="Test Admin",
            email="admin@policydesk.io",
            hashed_password=hash_password("AdminTestPass_2026!"),
            role="admin",
            is_active=True,
        )
        normal = User(
            name="Normal Employee",
            email="employee@policydesk.io",
            hashed_password=hash_password("EmployeeTestPass_2026!"),
            role="user",
            is_active=True,
        )
        db.add(admin)
        db.add(normal)
        db.commit()
        db.refresh(admin)
        db.refresh(normal)

        admin_token = create_access_token(
            subject=admin.email, user_id=admin.id, role=admin.role
        )
        user_token = create_access_token(
            subject=normal.email, user_id=normal.id, role=normal.role
        )
        return (
            {"Authorization": f"Bearer {admin_token}"},
            {"Authorization": f"Bearer {user_token}"},
        )
    finally:
        db.close()



def generate_sample_pdf_bytes(pages_text: list[str]) -> bytes:
    """Generate a valid multi-page PDF with properly wrapped text."""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)

    page_width, page_height = letter
    left_margin = 50
    right_margin = 50
    top_margin = 62
    bottom_margin = 50
    font_name = "Helvetica"
    font_size = 11
    line_height = 15

    for page_content in pages_text:
        text_obj = c.beginText(left_margin, page_height - top_margin)
        text_obj.setFont(font_name, font_size)

        for line in page_content.split("\n"):
            wrapped_lines = simpleSplit(
                line,
                font_name,
                font_size,
                page_width - left_margin - right_margin,
            )

            for wrapped_line in wrapped_lines:
                if text_obj.getY() < bottom_margin:
                    c.drawText(text_obj)
                    c.showPage()
                    text_obj = c.beginText(
                        left_margin, page_height - top_margin
                    )
                    text_obj.setFont(font_name, font_size)

                text_obj.textLine(wrapped_line)
                text_obj.moveCursor(0, -line_height)

        c.drawText(text_obj)
        c.showPage()

    c.save()
    return buffer.getvalue()



def get_test_client() -> TestClient:
    return TestClient(app)
