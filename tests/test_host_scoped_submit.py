"""Host-scoped command templates, the preset a submission opens on, per-job
download choices, and the local-path checks behind "already downloaded".
"""

from __future__ import annotations

import os
import shutil
import tempfile
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from job_manager.local_paths import is_within
from job_manager.models import Job
from job_manager.store import JobStore

from .fakes import make_host, make_preset
from .test_service import ServiceTestCase


class TestIsWithin(unittest.TestCase):
    @unittest.skipUnless(os.name == "nt", "Windows path rules")
    def test_a_share_root_contains_its_files(self):
        # commonpath raises on a bare \\server\share, which used to make every
        # file on a share-root mirror "not on this host".
        self.assertTrue(is_within(r"\\server\share\job\mol.inp", r"\\server\share"))
        self.assertTrue(is_within("//server/share/job/mol.inp", r"\\server\share"))
        self.assertFalse(is_within(r"\\server\other\mol.inp", r"\\server\share"))

    @unittest.skipUnless(os.name == "nt", "Windows path rules")
    def test_a_drive_root_and_case(self):
        self.assertTrue(is_within(r"d:\Work\mol.inp", "D:\\"))
        self.assertTrue(is_within(r"D:\WORK\mol.inp", r"d:\work"))

    def test_a_sibling_with_the_same_prefix_is_outside(self):
        root = os.path.join(tempfile.gettempdir(), "mirror")
        self.assertTrue(is_within(os.path.join(root, "a", "b.inp"), root))
        self.assertFalse(is_within(root + "2" + os.sep + "b.inp", root))
        self.assertFalse(is_within("", root))
        self.assertFalse(is_within(root, ""))


class StoreTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="host_scoped_")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.store = JobStore(self.tmp)
        self.host = self.store.add_host(make_host(id="h1", name="aaa"))
        self.other = self.store.add_host(make_host(id="h2", name="bbb"))


class TestHostScopedTemplates(StoreTestCase):
    def test_a_hosts_own_default_wins_there_only(self):
        self.store.set_default_command(".inp", "orca {input}")
        self.store.set_default_command(".inp", "/opt/orca/orca {input}", host_id="h1")
        self.assertEqual(
            self.store.default_command_for(".inp", "h1")["command"], "/opt/orca/orca {input}"
        )
        self.assertEqual(self.store.default_command_for(".inp", "h2")["command"], "orca {input}")
        self.assertEqual(self.store.default_command_for(".inp")["command"], "orca {input}")

    def test_the_same_label_may_exist_per_host(self):
        self.store.add_user_template("ORCA", "orca {input}")
        self.store.add_user_template("ORCA", "/opt/orca/orca {input}", host_id="h1")
        self.assertEqual(len(self.store.user_templates()), 2)
        mine = self.store.user_templates("h1")
        self.assertEqual(mine[0]["host_id"], "h1")
        self.assertEqual([t.get("host_id", "") for t in self.store.user_templates("h2")], [""])
        self.store.remove_user_template("ORCA", "h1")
        self.assertEqual([t["command"] for t in self.store.user_templates()], ["orca {input}"])

    def test_removing_a_host_removes_what_was_only_its_own(self):
        self.store.add_user_template("mine", "x", host_id="h1")
        self.store.add_user_template("shared", "y")
        self.store.set_default_command(".inp", "z", host_id="h1")
        preset = self.store.add_preset(make_preset(host_id="h1"))
        self.store.set_default_preset("h1", preset.id)
        self.store.note_preset_used("h1", preset.id)
        self.store.remove_host("h1")
        reloaded = JobStore(self.tmp)
        self.assertEqual([t["label"] for t in reloaded.user_templates()], ["shared"])
        self.assertNotIn("h1", reloaded.host_default_commands())
        self.assertNotIn("h1", reloaded.get_pref("default_presets", {}))
        self.assertNotIn("h1", reloaded.get_pref("last_presets", {}))


class TestRememberedPreset(StoreTestCase):
    def setUp(self):
        super().setUp()
        self.first = self.store.add_preset(make_preset(host_id="h1", name="first"))
        self.second = self.store.add_preset(make_preset(host_id="h1", name="second"))
        self.store.set_default_preset("h1", self.first.id)
        self.store.note_preset_used("h1", self.second.id)

    def test_an_empty_form_by_default(self):
        self.assertIsNone(self.store.remembered_preset("h1"))

    def test_the_last_one_used(self):
        self.store.set_pref("submit_start_from", "last")
        self.assertIs(self.store.remembered_preset("h1"), self.second)

    def test_the_starred_one(self):
        self.store.set_pref("submit_start_from", "default")
        self.assertIs(self.store.remembered_preset("h1"), self.first)
        self.store.set_default_preset("h1", "")
        self.assertIsNone(self.store.remembered_preset("h1"))

    def test_never_another_hosts_preset(self):
        self.store.set_pref("submit_start_from", "default")
        self.store.set_default_preset("h2", self.first.id)
        self.assertIsNone(self.store.remembered_preset("h2"))


class TestDownloadEveryOutput(ServiceTestCase):
    def test_off_by_default_and_on_for_one_job(self):
        self.assertFalse(self.submit().download_all)
        self.assertTrue(self.submit(download_all=True).download_all)
        self.assertFalse(self.submit().download_all)

    def test_an_automatic_download_takes_everything(self):
        job = self.submit(download_all=True)
        with patch("job_manager.service.fetch_results", return_value=[]) as fetch:
            self.service.download(job)
        self.assertEqual(fetch.call_args.kwargs["globs"], ["**"])

    def test_picked_names_still_mean_just_those(self):
        job = self.submit(download_all=True)
        with patch("job_manager.service.fetch_results", return_value=[]) as fetch:
            self.service.download(job, names=["mol.out"])
        self.assertEqual(fetch.call_args.kwargs["globs"], ["mol.out"])

    def test_without_it_the_fetch_patterns_apply(self):
        job = self.submit()
        with patch("job_manager.service.fetch_results", return_value=[]) as fetch:
            self.service.download(job)
        self.assertIsNone(fetch.call_args.kwargs["globs"])

    def test_the_download_folder_is_per_job(self):
        elsewhere = os.path.join(self.tmp, "elsewhere")
        job = self.submit(beside_input=False, download_root=elsewhere)
        self.assertTrue(is_within(job.local_dir, elsewhere))


class TestAlreadyHere(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="already_here_")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.input = self.write("mol.inp")

    def write(self, name):
        path = os.path.join(self.tmp, name)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("x")
        return path

    def already_here(self, parts, **job):
        try:
            from job_manager.output_file_dialog import OutputFileSelectorDialog
        except ImportError:
            self.skipTest("PySide6 is not installed")
        defaults = dict(input_files=[self.input], local_dir=self.tmp, submitted_at=time.time())
        defaults.update(job)
        holder = SimpleNamespace(job=Job(**defaults))
        return OutputFileSelectorDialog._already_here(holder, parts)

    def test_the_jobs_own_input(self):
        self.assertEqual(self.already_here(["mol.inp"], local_dir=""), os.path.normpath(self.input))

    def test_a_file_written_since_submission(self):
        out = self.write("mol.out")
        self.assertEqual(self.already_here(["mol.out"]), os.path.normpath(out))

    def test_an_earlier_runs_output_is_not_this_ones(self):
        out = self.write("mol.out")
        old = time.time() - 3600
        os.utime(out, (old, old))
        self.assertEqual(self.already_here(["mol.out"]), "")

    def test_a_missing_file(self):
        self.assertEqual(self.already_here(["mol.gbw"]), "")
