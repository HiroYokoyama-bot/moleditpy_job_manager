"""Fetching from a Job Server: the pinned client's download and path checks.

The client is synced from Job Server, where its own tests live; these cover
what Job Manager relies on through ``JobServerBackend``: a listing without
digests, a download verified against its own X-SHA256 header, and the
reserved-name and containment checks every fetched path goes through.
"""

import hashlib
import io
import os
import uuid
from types import SimpleNamespace

import pytest

pytest.importorskip("cryptography")

from job_manager.job_server_client import files  # noqa: E402
from job_manager.job_server_client.client import JobServerClient  # noqa: E402
from job_manager.job_server_client.errors import ServerError  # noqa: E402
from job_manager.server_backend import JobServerBackend  # noqa: E402

JOB = str(uuid.uuid4())


class Response(io.BytesIO):
    def __init__(self, data, headers, status=200):
        super().__init__(data)
        self.headers, self.status = headers, status

    def __exit__(self, *exc):
        self.close()
        return False


def backend_for(content, *, digest=None, listed_size=None, content_range=None):
    """A backend whose client answers from ``content`` instead of a network."""
    client = JobServerClient("http://127.0.0.1:8766")
    client.token = "token"
    client._ensure_auth = lambda route: None
    seen = SimpleNamespace(listings=[], ranges=[])

    def request(method, path, *args, **kwargs):
        seen.listings.append(path)
        size = len(content) if listed_size is None else listed_size
        return [{"path": "result.out", "size": size}]

    def open_(request):
        wanted = request.get_header("Range")
        seen.ranges.append(wanted)
        start = int(wanted.split("=")[1].rstrip("-")) if wanted else 0
        checksum = hashlib.sha256(content).hexdigest() if digest is None else digest
        headers = {"X-SHA256": checksum}
        if wanted:
            headers["Content-Range"] = content_range or (
                f"bytes {start}-{len(content) - 1}/{len(content)}"
            )
        return Response(content[start:], headers, 206 if wanted else 200)

    client.request, client._open = request, open_
    backend = object.__new__(JobServerBackend)
    backend.client = client
    return backend, seen


def job():
    return SimpleNamespace(remote_job_id=JOB)


def test_the_file_list_is_asked_for_without_digests():
    backend = object.__new__(JobServerBackend)
    calls = []
    backend.client = SimpleNamespace(request=lambda method, path: calls.append(path) or [])
    assert backend.files(job()) == []
    assert calls == [f"/jobs/{JOB}/files?digest=0"]


def test_a_fetched_file_is_verified_against_its_own_header(tmp_path):
    backend, seen = backend_for(b"result data")
    target = backend.fetch_file(job(), "result.out", tmp_path / "out" / "result.out")
    assert target.read_bytes() == b"result data"
    assert seen.listings == [f"/jobs/{JOB}/files?digest=0"]
    assert not (tmp_path / "out" / "result.out.partial").exists()


def test_a_body_that_does_not_match_its_header_is_discarded(tmp_path):
    backend, _ = backend_for(b"result data", digest="0" * 64)
    with pytest.raises(ValueError, match="checksum differs"):
        backend.fetch_file(job(), "result.out", tmp_path / "result.out")
    assert not (tmp_path / "result.out").exists()
    assert not (tmp_path / "result.out.partial").exists()


@pytest.mark.parametrize("digest", ["", "not-a-digest", "A" * 63])
def test_a_download_without_a_well_formed_checksum_is_refused(tmp_path, digest):
    backend, _ = backend_for(b"result data", digest=digest)
    with pytest.raises(ValueError, match="no file checksum"):
        backend.fetch_file(job(), "result.out", tmp_path / "result.out")
    assert not (tmp_path / "result.out").exists()


def test_an_upper_case_checksum_is_accepted(tmp_path):
    content = b"result data"
    backend, _ = backend_for(content, digest=hashlib.sha256(content).hexdigest().upper())
    backend.fetch_file(job(), "result.out", tmp_path / "result.out")
    assert (tmp_path / "result.out").read_bytes() == content


def test_a_partial_download_resumes_and_is_verified_whole(tmp_path):
    content = b"0123456789" * 10
    (tmp_path / "result.out.partial").write_bytes(content[:40])
    backend, seen = backend_for(content)
    backend.fetch_file(job(), "result.out", tmp_path / "result.out")
    assert seen.ranges == ["bytes=40-"]
    assert (tmp_path / "result.out").read_bytes() == content


def test_a_resume_the_server_does_not_honour_is_refused(tmp_path):
    content = b"0123456789" * 10
    (tmp_path / "result.out.partial").write_bytes(content[:40])
    backend, _ = backend_for(content, content_range="bytes 0-99/100")
    with pytest.raises(ValueError, match="resume range"):
        backend.fetch_file(job(), "result.out", tmp_path / "result.out")
    assert not (tmp_path / "result.out").exists()


@pytest.mark.parametrize("leftover", [b"stale data!", b"longer than the file"])
def test_a_leftover_as_long_as_the_file_or_longer_is_fetched_again(tmp_path, leftover):
    # Only a response carries the checksum a leftover could be verified
    # against, so even a full-size one is not trusted as it is.
    (tmp_path / "result.out.partial").write_bytes(leftover)
    backend, seen = backend_for(b"fresh data!")
    backend.fetch_file(job(), "result.out", tmp_path / "result.out")
    assert seen.ranges == [None]
    assert (tmp_path / "result.out").read_bytes() == b"fresh data!"


def test_a_file_that_grew_after_listing_is_refused(tmp_path):
    backend, _ = backend_for(b"longer than listed", listed_size=4)
    with pytest.raises(ValueError, match="exceeded expected file size"):
        backend.fetch_file(job(), "result.out", tmp_path / "result.out")
    assert not (tmp_path / "result.out").exists()


def test_a_file_missing_from_the_listing_is_not_requested(tmp_path):
    backend, seen = backend_for(b"result data")
    with pytest.raises(ValueError, match="not in the server manifest"):
        backend.fetch_file(job(), "other.out", tmp_path / "other.out")
    assert seen.ranges == []


# Path checks ---------------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    ["../escape", "a//b", "a\\b", "nul.txt", "trailing.", "job.log", "dir/MOLEDITPY_RUN.SH"],
)
def test_unsafe_and_reserved_paths_are_refused(path):
    with pytest.raises(ServerError):
        files.validate_path(path)


@pytest.mark.parametrize("name", sorted(files.READABLE))
def test_the_log_and_script_are_readable_but_never_writable(tmp_path, name):
    assert files.validate_path(name, readable=True) == name
    assert files.contained(tmp_path, name, readable=True) == tmp_path / name
    with pytest.raises(ServerError):
        files.contained(tmp_path, name, create=True)
    with pytest.raises(ValueError, match="readable-only"):
        files.contained(tmp_path, name, create=True, readable=True)


def test_other_reserved_names_stay_unreadable(tmp_path):
    with pytest.raises(ServerError):
        files.contained(tmp_path, ".server_process", readable=True)


def test_contained_creates_parents_only_when_asked(tmp_path):
    target = files.contained(tmp_path, "nested/result.out", create=True)
    assert target == tmp_path / "nested" / "result.out"
    assert target.parent.is_dir()


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="no symlinks")
def test_a_linked_folder_inside_the_job_is_refused(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    root = tmp_path / "job"
    root.mkdir()
    try:
        (root / "link").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("symlinks need privileges here")
    with pytest.raises(ServerError):
        files.contained(root, "link/result.out")


def test_hashing_can_be_stopped_between_reads(tmp_path):
    path = tmp_path / "big.bin"
    path.write_bytes(b"x" * (3 * 1024 * 1024))
    assert files.sha256(path) == hashlib.sha256(path.read_bytes()).hexdigest()
    reads = []

    def stop():
        reads.append(1)
        return len(reads) > 1

    with pytest.raises(files.HashingStopped):
        files.sha256(path, stop)
    assert len(reads) == 2
