import re
from pathlib import Path
from typing import BinaryIO

import pymupdf

PDF_SIGNATURE = b"%PDF-"


class FileRejected(Exception):
    """An uploaded file failed validation. The message is safe to show to the user."""


def sanitize_filename(filename: str | None) -> str:
    """Keep only a safe display name: no folders, no control characters.

    "../../etc/evil.pdf" becomes "evil.pdf". This name is only displayed, never
    used as a path on disk.
    """
    name = (filename or "").replace("\\", "/").split("/")[-1]
    name = "".join(ch for ch in name if ch.isprintable()).strip()
    return name[:255] or "document.pdf"


def validate_pdf(filename: str, file: BinaryIO) -> None:
    """Check the extension AND the file's first bytes.

    The extension and the browser's Content-Type are chosen by the client and can
    lie; the "%PDF-" signature at the start of the file is much harder to fake.
    Deeper checks (opening the PDF) happen in Module 3.
    """
    if not filename.lower().endswith(".pdf"):
        raise FileRejected("Only PDF files are allowed")

    header = file.read(len(PDF_SIGNATURE))
    file.seek(0)
    if header != PDF_SIGNATURE:
        raise FileRejected("File content is not a valid PDF")


# PDF features that can run code or carry hidden files. A research paper never needs them.
ACTIVE_CONTENT_KEYS = ("/JavaScript", "/JS", "/Launch", "/EmbeddedFile", "/RichMedia", "/XFA")


def check_active_content(path: Path) -> None:
    """Reject PDFs with JavaScript, launch actions, embedded files or XFA forms.

    PDFs that cannot be opened (damaged or password-protected) are let through here;
    the processing pipeline reports those with a clear message instead.
    """
    try:
        pdf = pymupdf.open(path)
    except (pymupdf.FileDataError, RuntimeError, ValueError):
        return
    with pdf:
        if pdf.needs_pass:
            return
        if pdf.embfile_count():
            raise FileRejected("This PDF contains embedded files, which are not allowed for security reasons.")
        for xref in range(1, pdf.xref_length()):
            try:
                obj = pdf.xref_object(xref, compressed=True)
            except (RuntimeError, ValueError):
                continue
            if any(re.search(re.escape(key) + r"(?![A-Za-z])", obj) for key in ACTIVE_CONTENT_KEYS):
                raise FileRejected(
                    "This PDF contains active content (JavaScript, launch actions or embedded media), "
                    "which is not allowed for security reasons."
                )
