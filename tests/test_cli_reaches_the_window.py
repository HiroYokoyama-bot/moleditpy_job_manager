"""A job submitted from the command line appears in the open Job Monitor.

The command line holds no job list of its own: it asks the running Job Manager
over the Local API, whose handlers run on the window's GUI thread and call the
same JobService.submit as the Submit dialog. This checks that path end to end,
with the real service and the real monitor table rather than a stand-in.
"""

import os
import shutil
import sys
import tempfile
import time
import unittest

import pytest

pytest.importorskip("PySide6.QtWidgets", reason="PySide6 is not installed")

from PySide6.QtWidgets import QApplication  # noqa: E402

from job_manager import __main__ as entry  # noqa: E402
from job_manager.api_server import JobApiServer  # noqa: E402
from job_manager.jobs_dialog import JobsDialog  # noqa: E402
from job_manager.models import HostProfile  # noqa: E402
from job_manager.service import JobService  # noqa: E402
from job_manager.store import JobStore  # noqa: E402

from .api_support import in_thread  # noqa: E402


class TestTheWindowSeesACommandLineSubmission(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="jm_cli_window_")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.store = JobStore(self.tmp)
        self.store.add_host(HostProfile(name="mybox", backend="local"))
        self.service = JobService(store=self.store)
        self.addCleanup(self.service.shutdown)
        self.server = JobApiServer(self.service)
        self.server.start(0)
        self.addCleanup(self.server.stop)
        self.monitor = JobsDialog(self.service)
        self.addCleanup(self.monitor.close)
        self.monitor.show()
        self.input_path = os.path.join(self.tmp, "h2o.inp")
        with open(self.input_path, "w", encoding="utf-8") as handle:
            handle.write("! example\n")

    def test_the_job_is_listed_without_any_action_in_the_window(self):
        self.assertEqual(self.monitor.model.rowCount(), 0)
        argv = [
            "job_manager",
            f"--url={self.server.url()}",
            f"--token={self.server.token()}",
            "submit",
            self.input_path,
            "--host",
            "mybox",
            "--name",
            "from-the-command-line",
            "--command",
            "echo {input}",
        ]
        saved = sys.argv
        sys.argv = argv
        try:
            self.assertEqual(in_thread(entry.main), 0)
        finally:
            sys.argv = saved
        deadline = time.time() + 15
        while time.time() < deadline and self.monitor.model.rowCount() == 0:
            QApplication.processEvents()
            time.sleep(0.01)
        self.assertEqual(self.monitor.model.rowCount(), 1)
        [job] = self.store.job_list()
        self.assertEqual(job.name, "from-the-command-line")
        model = self.monitor.model
        shown = [str(model.index(0, column).data()) for column in range(model.columnCount())]
        self.assertIn("from-the-command-line", shown)
