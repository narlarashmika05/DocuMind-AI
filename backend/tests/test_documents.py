from app.core.config import settings

DOCS_URL = "/api/v1/documents"
PDF_BYTES = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


def pdf(name="paper.pdf", content=PDF_BYTES, content_type="application/pdf"):
    return ("files", (name, content, content_type))


def upload(client, headers, *files):
    return client.post(DOCS_URL, headers=headers, files=list(files))


def stored_files():
    return sorted(settings.upload_dir.glob("*/*"))


def test_documents_require_authentication(client):
    assert client.get(DOCS_URL).status_code == 401


def test_upload_and_list_a_pdf(client, make_user):
    headers = make_user()

    response = upload(client, headers, pdf())

    assert response.status_code == 200
    body = response.json()
    assert body["rejected"] == []
    [document] = body["uploaded"]
    assert document["original_filename"] == "paper.pdf"
    assert document["file_size"] == len(PDF_BYTES)
    assert document["status"] == "uploaded"

    listed = client.get(DOCS_URL, headers=headers).json()
    assert [d["id"] for d in listed] == [document["id"]]
    [path] = stored_files()
    assert path.suffix == ".pdf" and path.read_bytes() == PDF_BYTES


def test_batch_upload_reports_each_rejected_file(client, make_user):
    headers = make_user()

    response = upload(
        client,
        headers,
        pdf("a.pdf"),
        pdf("b.pdf", PDF_BYTES + b"% different content"),
        pdf("notes.txt", b"hello", "text/plain"),
        pdf("fake.pdf", b"MZ\x90\x00 this is an exe"),
    )

    body = response.json()
    assert [d["original_filename"] for d in body["uploaded"]] == ["a.pdf", "b.pdf"]
    reasons = {r["filename"]: r["reason"] for r in body["rejected"]}
    assert reasons == {
        "notes.txt": "Only PDF files are allowed",
        "fake.pdf": "File content is not a valid PDF",
    }


def test_duplicate_upload_is_rejected(client, make_user):
    headers = make_user()
    upload(client, headers, pdf())

    body = upload(client, headers, pdf("same-file-renamed.pdf")).json()

    assert body["uploaded"] == []
    assert body["rejected"][0]["reason"] == "You have already uploaded this file"
    assert len(stored_files()) == 1


def test_oversized_file_is_rejected_and_not_left_on_disk(client, make_user, monkeypatch):
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_MB", 1)
    headers = make_user()

    body = upload(client, headers, pdf(content=PDF_BYTES + b"0" * (1024 * 1024))).json()

    assert body["uploaded"] == []
    assert body["rejected"][0]["reason"] == "File is larger than 1 MB"
    assert stored_files() == []


def test_too_many_files_in_one_request(client, make_user, monkeypatch):
    monkeypatch.setattr(settings, "MAX_FILES_PER_UPLOAD", 2)
    headers = make_user()

    response = upload(client, headers, pdf("1.pdf"), pdf("2.pdf"), pdf("3.pdf"))

    assert response.status_code == 400


def test_path_traversal_filename_is_sanitized(client, make_user):
    headers = make_user()

    body = upload(client, headers, pdf("../../etc/evil.pdf")).json()

    assert body["uploaded"][0]["original_filename"] == "evil.pdf"
    [path] = stored_files()
    assert path.parent.parent == settings.upload_dir


def test_download_returns_the_original_pdf(client, make_user):
    headers = make_user()
    document_id = upload(client, headers, pdf()).json()["uploaded"][0]["id"]

    response = client.get(f"{DOCS_URL}/{document_id}/file", headers=headers)

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content == PDF_BYTES


def test_delete_removes_record_and_file(client, make_user):
    headers = make_user()
    document_id = upload(client, headers, pdf()).json()["uploaded"][0]["id"]

    assert client.delete(f"{DOCS_URL}/{document_id}", headers=headers).status_code == 204

    assert client.get(DOCS_URL, headers=headers).json() == []
    assert client.get(f"{DOCS_URL}/{document_id}", headers=headers).status_code == 404
    assert stored_files() == []


def test_users_cannot_see_or_touch_each_others_documents(client, make_user):
    alice = make_user("alice@example.com")
    bob = make_user("bob@example.com")
    document_id = upload(client, alice, pdf()).json()["uploaded"][0]["id"]

    assert client.get(DOCS_URL, headers=bob).json() == []
    assert client.get(f"{DOCS_URL}/{document_id}", headers=bob).status_code == 404
    assert client.get(f"{DOCS_URL}/{document_id}/file", headers=bob).status_code == 404
    assert client.delete(f"{DOCS_URL}/{document_id}", headers=bob).status_code == 404

    assert len(client.get(DOCS_URL, headers=alice).json()) == 1
