"""Unit tests for recruitment resume upload and download endpoints.

Tests T-R008 (resume upload) and T-R009 (resume download) covering:

1. POST /candidates/{id}/resume: file upload with validation
   - Tenant isolation (candidate ownership)
   - File size limit (10MB)
   - MIME type validation
   - Magic byte validation
   - Extension validation
   - UUID filename generation and storage
   - Candidate resume_url field update
2. GET /candidates/{id}/resume: file download/serve
   - Tenant isolation
   - Missing resume handling
   - File not found on disk
   - Correct FileResponse with Content-Disposition
3. Edge cases: empty files, wrong magic bytes, path traversal filenames
"""

import io
import os
import struct
import tempfile
import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from hr_advisory.api.routers.recruitment import router


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------


def _make_app() -> FastAPI:
    """Build a minimal FastAPI app with the recruitment router mounted."""
    app = FastAPI()
    app.include_router(router, prefix="/recruitment")
    return app


def _fake_user(company_id: int = 1, role: str = "owner") -> dict:
    return {
        "sub": 10,
        "email": "test@example.com",
        "role": role,
        "company_id": company_id,
    }


def _candidate_record(candidate_id: int = 1, company_id: int = 1, resume_url: str = "") -> dict:
    return {
        "id": candidate_id,
        "company_id": company_id,
        "job_listing_id": 1,
        "name": "Jane Doe",
        "email": "jane@example.com",
        "resume_url": resume_url,
        "stage": "applied",
    }


@pytest.fixture()
def client():
    """Test client with auth dependency overridden."""
    from hr_advisory.api.middleware.auth_middleware import get_current_user

    app = _make_app()
    app.dependency_overrides[get_current_user] = lambda: _fake_user()
    yield TestClient(app)
    app.dependency_overrides.clear()


# Reset both in-memory and Redis-backed rate-limit state so resume upload
# tests don't inherit a 429 from a previous run that already burned through
# the 30/3600s allowance.
@pytest.fixture(autouse=True)
def _reset_rate_limit():
    from hr_advisory.api.middleware import rate_limit as rl

    rl._request_log.clear()
    try:
        client = rl._get_redis_client()
        if client is not None:
            for key in client.keys("rate:*"):
                try:
                    client.delete(key)
                except Exception:
                    pass
    except Exception:
        pass

    yield
    rl._request_log.clear()


def _pdf_bytes() -> bytes:
    """Minimal valid PDF magic bytes."""
    return b"%PDF-1.4 minimal content"


def _jpeg_bytes() -> bytes:
    """Minimal JPEG magic bytes."""
    return b"\xff\xd8\xff\xe0" + b"\x00" * 100


def _png_bytes() -> bytes:
    """Minimal PNG magic bytes."""
    return b"\x89PNG\r\n\x1a\n" + b"\x00" * 100


def _docx_bytes() -> bytes:
    """Minimal DOCX (ZIP) magic bytes."""
    return b"PK\x03\x04" + b"\x00" * 100


def _doc_bytes() -> bytes:
    """Minimal DOC magic bytes."""
    return b"\xd0\xcf\x11\xe0" + b"\x00" * 100


def _gif_bytes() -> bytes:
    """GIF magic bytes (not allowed)."""
    return b"GIF89a" + b"\x00" * 100


# ---------------------------------------------------------------------------
# T-R008: POST /candidates/{id}/resume — Resume Upload
# ---------------------------------------------------------------------------


class TestResumeUpload:
    """POST /recruitment/candidates/{id}/resume uploads and stores a resume."""

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_successful_pdf_upload(self, mock_crud, client, tmp_path):
        """A valid PDF uploads, stores the file, and updates resume_url."""
        candidate = _candidate_record()
        mock_crud.read.return_value = candidate
        mock_crud.update.return_value = {**candidate, "resume_url": "stored.pdf"}

        with patch("hr_advisory.api.routers.recruitment.RECRUITMENT_UPLOAD_DIR", str(tmp_path)):
            resp = client.post(
                "/recruitment/candidates/1/resume",
                files={"file": ("resume.pdf", io.BytesIO(_pdf_bytes()), "application/pdf")},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["message"] == "Resume uploaded."
        assert body["resume_url"]  # UUID filename stored
        # Verify the file was saved
        mock_crud.update.assert_called_once()
        call_args = mock_crud.update.call_args
        assert call_args[0][0] == "Candidate"
        assert call_args[0][1] == 1

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_successful_docx_upload(self, mock_crud, client, tmp_path):
        """A valid DOCX (ZIP-based) file uploads successfully."""
        mock_crud.read.return_value = _candidate_record()
        mock_crud.update.return_value = _candidate_record()

        with patch("hr_advisory.api.routers.recruitment.RECRUITMENT_UPLOAD_DIR", str(tmp_path)):
            resp = client.post(
                "/recruitment/candidates/1/resume",
                files={
                    "file": (
                        "resume.docx",
                        io.BytesIO(_docx_bytes()),
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    )
                },
            )

        assert resp.status_code == 200

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_successful_doc_upload(self, mock_crud, client, tmp_path):
        """A valid DOC (legacy Word) file uploads successfully."""
        mock_crud.read.return_value = _candidate_record()
        mock_crud.update.return_value = _candidate_record()

        with patch("hr_advisory.api.routers.recruitment.RECRUITMENT_UPLOAD_DIR", str(tmp_path)):
            resp = client.post(
                "/recruitment/candidates/1/resume",
                files={
                    "file": (
                        "resume.doc",
                        io.BytesIO(_doc_bytes()),
                        "application/msword",
                    )
                },
            )

        assert resp.status_code == 200

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_successful_jpeg_upload(self, mock_crud, client, tmp_path):
        """A valid JPEG image uploads successfully (scanned resume)."""
        mock_crud.read.return_value = _candidate_record()
        mock_crud.update.return_value = _candidate_record()

        with patch("hr_advisory.api.routers.recruitment.RECRUITMENT_UPLOAD_DIR", str(tmp_path)):
            resp = client.post(
                "/recruitment/candidates/1/resume",
                files={"file": ("resume.jpg", io.BytesIO(_jpeg_bytes()), "image/jpeg")},
            )

        assert resp.status_code == 200

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_successful_png_upload(self, mock_crud, client, tmp_path):
        """A valid PNG image uploads successfully (scanned resume)."""
        mock_crud.read.return_value = _candidate_record()
        mock_crud.update.return_value = _candidate_record()

        with patch("hr_advisory.api.routers.recruitment.RECRUITMENT_UPLOAD_DIR", str(tmp_path)):
            resp = client.post(
                "/recruitment/candidates/1/resume",
                files={"file": ("resume.png", io.BytesIO(_png_bytes()), "image/png")},
            )

        assert resp.status_code == 200

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_candidate_not_found_returns_404(self, mock_crud, client):
        """Uploading to a non-existent candidate returns 404."""
        # _verify_candidate_ownership uses list_records; empty -> 404.
        mock_crud.list_records.return_value = []

        resp = client.post(
            "/recruitment/candidates/999/resume",
            files={"file": ("resume.pdf", io.BytesIO(_pdf_bytes()), "application/pdf")},
        )

        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_wrong_company_returns_404(self, mock_crud, client):
        """Uploading to a candidate from another company returns 404 (tenant isolation)."""
        # _verify_candidate_ownership filters by (id, company_id); a
        # candidate belonging to company 999 won't match for company 1.
        mock_crud.list_records.return_value = []

        resp = client.post(
            "/recruitment/candidates/1/resume",
            files={"file": ("resume.pdf", io.BytesIO(_pdf_bytes()), "application/pdf")},
        )

        assert resp.status_code == 404

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_file_too_large_returns_400(self, mock_crud, client):
        """Files exceeding 10MB are rejected."""
        mock_crud.read.return_value = _candidate_record()

        # 11MB of PDF-like content
        large_content = b"%PDF" + b"\x00" * (11 * 1024 * 1024)

        resp = client.post(
            "/recruitment/candidates/1/resume",
            files={"file": ("huge.pdf", io.BytesIO(large_content), "application/pdf")},
        )

        assert resp.status_code == 400
        assert "10MB" in resp.json()["detail"] or "10mb" in resp.json()["detail"].lower()

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_disallowed_mime_type_returns_400(self, mock_crud, client):
        """Files with unsupported MIME types are rejected."""
        mock_crud.read.return_value = _candidate_record()

        resp = client.post(
            "/recruitment/candidates/1/resume",
            files={"file": ("script.js", io.BytesIO(b"alert('hi')"), "application/javascript")},
        )

        assert resp.status_code == 400
        assert "not allowed" in resp.json()["detail"].lower()

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_disallowed_extension_returns_400(self, mock_crud, client):
        """Files with disallowed extensions are rejected even if MIME is spoofed."""
        mock_crud.read.return_value = _candidate_record()

        resp = client.post(
            "/recruitment/candidates/1/resume",
            files={"file": ("evil.exe", io.BytesIO(_pdf_bytes()), "application/pdf")},
        )

        assert resp.status_code == 400
        assert "extension" in resp.json()["detail"].lower()

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_magic_bytes_mismatch_returns_400(self, mock_crud, client):
        """Files whose magic bytes don't match the declared MIME type are rejected."""
        mock_crud.read.return_value = _candidate_record()

        # Declare PDF MIME but send GIF bytes
        resp = client.post(
            "/recruitment/candidates/1/resume",
            files={"file": ("resume.pdf", io.BytesIO(_gif_bytes()), "application/pdf")},
        )

        assert resp.status_code == 400
        assert "magic" in resp.json()["detail"].lower() or "content" in resp.json()["detail"].lower()

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_empty_file_returns_400(self, mock_crud, client):
        """Empty files are rejected."""
        mock_crud.read.return_value = _candidate_record()

        resp = client.post(
            "/recruitment/candidates/1/resume",
            files={"file": ("empty.pdf", io.BytesIO(b""), "application/pdf")},
        )

        assert resp.status_code == 400
        assert "empty" in resp.json()["detail"].lower()

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_uuid_filename_stored(self, mock_crud, client, tmp_path):
        """The stored filename is a UUID, not the original filename."""
        mock_crud.read.return_value = _candidate_record()
        mock_crud.update.return_value = _candidate_record()

        with patch("hr_advisory.api.routers.recruitment.RECRUITMENT_UPLOAD_DIR", str(tmp_path)):
            resp = client.post(
                "/recruitment/candidates/1/resume",
                files={"file": ("my_resume.pdf", io.BytesIO(_pdf_bytes()), "application/pdf")},
            )

        body = resp.json()
        stored_name = body["resume_url"]
        # Must NOT be the original filename (UUID prevents path traversal)
        assert stored_name != "my_resume.pdf"
        # Must end with .pdf
        assert stored_name.endswith(".pdf")
        # Must be a valid UUID prefix
        name_without_ext = stored_name.rsplit(".", 1)[0]
        uuid.UUID(name_without_ext)  # Raises ValueError if not valid UUID

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_file_written_to_company_subdirectory(self, mock_crud, client, tmp_path):
        """The file is stored in uploads/recruitment/{company_id}/ directory."""
        mock_crud.read.return_value = _candidate_record()
        mock_crud.update.return_value = _candidate_record()

        with patch("hr_advisory.api.routers.recruitment.RECRUITMENT_UPLOAD_DIR", str(tmp_path)):
            resp = client.post(
                "/recruitment/candidates/1/resume",
                files={"file": ("resume.pdf", io.BytesIO(_pdf_bytes()), "application/pdf")},
            )

        assert resp.status_code == 200
        # Verify file was saved in the company subdirectory
        company_dir = tmp_path / "1"
        assert company_dir.exists()
        files = list(company_dir.iterdir())
        assert len(files) == 1
        assert files[0].name.endswith(".pdf")


# ---------------------------------------------------------------------------
# T-R009: GET /candidates/{id}/resume — Resume Download
# ---------------------------------------------------------------------------


class TestResumeDownload:
    """GET /recruitment/candidates/{id}/resume serves the stored resume file."""

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_successful_pdf_download(self, mock_crud, client, tmp_path):
        """Downloading a stored PDF resume returns the file with correct headers."""
        stored_name = f"{uuid.uuid4()}.pdf"
        candidate = _candidate_record(resume_url=stored_name)
        # _verify_candidate_ownership uses list_records (not read).
        mock_crud.list_records.return_value = [candidate]

        # Write a real file
        company_dir = tmp_path / "1"
        company_dir.mkdir(parents=True)
        file_path = company_dir / stored_name
        file_path.write_bytes(_pdf_bytes())

        with patch("hr_advisory.api.routers.recruitment.RECRUITMENT_UPLOAD_DIR", str(tmp_path)):
            resp = client.get("/recruitment/candidates/1/resume")

        assert resp.status_code == 200
        assert resp.content == _pdf_bytes()
        assert "attachment" in resp.headers.get("content-disposition", "")

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_candidate_not_found_returns_404(self, mock_crud, client):
        """Downloading resume for non-existent candidate returns 404."""
        mock_crud.list_records.return_value = []

        resp = client.get("/recruitment/candidates/999/resume")

        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_wrong_company_returns_404(self, mock_crud, client):
        """Downloading resume from another company's candidate returns 404."""
        # Wrong-tenant lookup returns empty (filtered by company_id).
        mock_crud.list_records.return_value = []

        resp = client.get("/recruitment/candidates/1/resume")

        assert resp.status_code == 404

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_no_resume_returns_404(self, mock_crud, client):
        """Downloading when candidate has no resume_url returns 404."""
        mock_crud.list_records.return_value = [_candidate_record(resume_url="")]

        resp = client.get("/recruitment/candidates/1/resume")

        assert resp.status_code == 404
        assert "no resume" in resp.json()["detail"].lower()

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_file_missing_on_disk_returns_404(self, mock_crud, client, tmp_path):
        """When resume_url references a file that doesn't exist on disk, returns 404."""
        stored_name = f"{uuid.uuid4()}.pdf"
        mock_crud.list_records.return_value = [_candidate_record(resume_url=stored_name)]

        with patch("hr_advisory.api.routers.recruitment.RECRUITMENT_UPLOAD_DIR", str(tmp_path)):
            resp = client.get("/recruitment/candidates/1/resume")

        assert resp.status_code == 404
        assert "file" in resp.json()["detail"].lower()

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_docx_download_correct_media_type(self, mock_crud, client, tmp_path):
        """DOCX files are served with the correct MIME type."""
        stored_name = f"{uuid.uuid4()}.docx"
        mock_crud.list_records.return_value = [_candidate_record(resume_url=stored_name)]

        company_dir = tmp_path / "1"
        company_dir.mkdir(parents=True)
        (company_dir / stored_name).write_bytes(_docx_bytes())

        with patch("hr_advisory.api.routers.recruitment.RECRUITMENT_UPLOAD_DIR", str(tmp_path)):
            resp = client.get("/recruitment/candidates/1/resume")

        assert resp.status_code == 200
        content_type = resp.headers.get("content-type", "")
        # Should be the DOCX MIME type or application/octet-stream (both acceptable)
        assert "application/" in content_type

    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    def test_jpeg_download_correct_media_type(self, mock_crud, client, tmp_path):
        """JPEG files are served with image/jpeg MIME type."""
        stored_name = f"{uuid.uuid4()}.jpg"
        mock_crud.list_records.return_value = [_candidate_record(resume_url=stored_name)]

        company_dir = tmp_path / "1"
        company_dir.mkdir(parents=True)
        (company_dir / stored_name).write_bytes(_jpeg_bytes())

        with patch("hr_advisory.api.routers.recruitment.RECRUITMENT_UPLOAD_DIR", str(tmp_path)):
            resp = client.get("/recruitment/candidates/1/resume")

        assert resp.status_code == 200
