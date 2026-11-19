"""Reload List takes in Job Server jobs submitted elsewhere (web page, another computer)."""

import tempfile

import pytest

from job_manager.models import BACKEND_JOB_SERVER, HostProfile, Job
from job_manager.server_backend import JobServerBackend


class FakeClient:
    server_id = "srv-1"

    def __init__(self, records):
        self.records = records
        self.paths = []

    def request(self, method, path):
        self.paths.append(path)
        if path.startswith("/jobs?"):
            offset = int(path.rsplit("offset=", 1)[1])
            return self.records[offset : offset + 1000]
        if path == "/capabilities":
            return {"execution_os": "linux"}
        raise AssertionError(path)


def _record(job_id, state, **extra):
    spec = {
        "name": f"job-{job_id}",
        "command": "mycommand input.inp",
        "fetch_globs": ["*.out"],
        "auto_download": False,
        "chain_any": False,
        "after_job": None,
    }
    return {
        "id": job_id,
        "state": state,
        "owner_id": "u1",
        "created_at": 100.0,
        "started_at": 150.0 if state == "RUNNING" else None,
        "held": False,
        "spec": spec,
        **extra,
    }


def _backend(records):
    backend = object.__new__(JobServerBackend)
    backend.client = FakeClient(records)
    backend.host = HostProfile(id="h1", name="myhost", server_url="https://myhost:8443")
    return backend


def test_untracked_takes_unfinished_jobs_the_list_lacks():
    backend = _backend(
        [
            _record("a", "RUNNING"),
            _record("b", "PENDING", held=True, queue_ahead=0),
            _record("c", "PENDING", queue_ahead=2),
            _record("d", "DONE"),
            _record("e", "FAILED"),
            _record("f", "UPLOADING"),
        ]
    )
    found = {job.remote_job_id: job for job in backend.untracked({"c"})}
    assert set(found) == {"a", "b"}
    running = found["a"]
    assert running.state == "RUNNING"
    assert running.name == "job-a"
    assert running.host_id == "h1" and running.host_name == "myhost"
    assert running.remote_dir == running.server_job_id == "a"
    assert running.server_id == "srv-1" and running.owner_user_id == "u1"
    assert running.execution_os == "linux"
    assert running.log_file == "job.log"
    assert running.fetch_globs == ["*.out"] and running.auto_download is False
    assert running.submitted_at == 100.0 and running.started_at == 150.0
    assert found["b"].state == "HELD" and found["b"].server_queue_ahead == 0


def test_the_same_server_job_gets_the_same_local_id_everywhere():
    first = _backend([_record("a", "RUNNING")]).untracked(set())
    second = _backend([_record("a", "RUNNING")]).untracked(set())
    assert first[0].id == second[0].id


def test_nothing_to_take_skips_the_capabilities_request():
    backend = _backend([_record("a", "DONE")])
    assert backend.untracked(set()) == []
    assert "/capabilities" not in backend.client.paths


def test_untracked_pages_through_a_long_list():
    records = [_record(f"j{n}", "DONE") for n in range(1000)] + [_record("last", "RUNNING")]
    backend = _backend(records)
    assert [job.remote_job_id for job in backend.untracked(set())] == ["last"]
    assert "/jobs?limit=1000&offset=1000" in backend.client.paths


def test_adopt_jobs_skips_what_the_list_took_in_meanwhile():
    pytest.importorskip("PySide6")
    from job_manager.store import JobStore

    store = JobStore(tempfile.mkdtemp(prefix="server_import_"))
    store.add_job(Job(id="mine", host_id="h1", remote_job_id="a", state="RUNNING"))
    found = [
        Job(id="x1", host_id="h1", remote_job_id="a", state="RUNNING"),
        Job(id="x2", host_id="h1", remote_job_id="b", state="RUNNING"),
        Job(id="x2", host_id="h1", remote_job_id="b", state="RUNNING"),
    ]
    assert store.adopt_jobs(found) == 1
    assert set(store.jobs) == {"mine", "x2"}
    assert store.adopt_jobs(found) == 0


def test_service_import_adds_jobs_and_reports_per_host(monkeypatch):
    pytest.importorskip("PySide6.QtWidgets")
    from job_manager import server_backend, service as service_module
    from job_manager.service import JobService
    from job_manager.store import JobStore

    from .fakes import make_host

    root = tempfile.mkdtemp(prefix="server_import_svc_")
    svc = JobService(JobStore(root))
    try:
        server = HostProfile(
            id="srv", name="myserver", backend=BACKEND_JOB_SERVER, server_url="https://myhost:8443"
        )
        assert server.is_job_server
        svc.store.add_host(server)
        svc.store.add_host(make_host())
        svc.store.add_job(Job(id="known", host_id="srv", remote_job_id="a", state="RUNNING"))
        asked = []

        class Backend:
            def untracked(self, known):
                asked.append(set(known))
                return [Job(id="new", host_id="srv", remote_job_id="b", state="PENDING")]

        monkeypatch.setattr(server_backend, "backend_for", lambda host: Backend())

        def run_now(pool, fn, on_success=None, on_error=None, **kwargs):
            on_success(fn())

        monkeypatch.setattr(service_module, "run_async", run_now)
        reports = []
        assert svc.import_server_jobs(lambda name, n: reports.append((name, n))) == 1
        assert asked == [{"a"}]
        assert reports == [("myserver", 1)]
        assert "new" in svc.store.jobs
    finally:
        svc.shutdown()
