"""Sorting the file lists by a header click, and which folders start open."""

from __future__ import annotations

import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QTreeWidget, QTreeWidgetItem

from job_manager.file_tree import TreeSorter, folder_factory, natural_key, set_row_size
from job_manager.models import Job
from job_manager.output_file_dialog import OutputFileSelectorDialog
from job_manager.result_files import likely_outputs, primary_output
from job_manager.tree_utils import PATH_ROLE

app = QApplication.instance() or QApplication([])


def names(parent):
    return [parent.child(row).text(0) for row in range(parent.childCount())]


class TestTreeSorter(unittest.TestCase):
    def setUp(self):
        self.tree = QTreeWidget()
        self.tree.setColumnCount(4)
        self.sorter = TreeSorter(self.tree)
        self.addCleanup(self.tree.deleteLater)

    def file(self, name, size=None, parent=None):
        item = QTreeWidgetItem([name, "", "", ""])
        item.setData(0, PATH_ROLE, name)
        set_row_size(item, size)
        (parent or self.tree.invisibleRootItem()).addChild(item)
        return item

    def folder(self, name, parent=None):
        item = folder_factory(columns=4)(name, [name], None)
        (parent or self.tree.invisibleRootItem()).addChild(item)
        return item

    def test_folders_first_then_names_a_to_z_by_default(self):
        self.file("b.out")
        self.folder("zeta")
        self.file("A.log")
        self.folder("alpha")
        self.sorter.sort()
        self.assertEqual(names(self.tree.invisibleRootItem()), ["alpha", "zeta", "A.log", "b.out"])

    def test_numbers_in_names_sort_as_numbers(self):
        for name in ("step10.out", "step2.out", "step1.out"):
            self.file(name)
        self.sorter.sort()
        self.assertEqual(
            names(self.tree.invisibleRootItem()), ["step1.out", "step2.out", "step10.out"]
        )
        self.assertLess(natural_key("a2"), natural_key("A10"))

    def test_a_header_click_sorts_by_bytes_and_folders_stay_first(self):
        self.file("small.out", 900 * 1024)
        self.file("big.out", 2 * 1024 * 1024)
        self.file("on_host.out", None)
        self.folder("scratch")
        self.tree.header().setSortIndicator(1, Qt.SortOrder.DescendingOrder)
        self.assertEqual(
            names(self.tree.invisibleRootItem()),
            ["scratch", "big.out", "small.out", "on_host.out"],
        )
        self.tree.header().setSortIndicator(1, Qt.SortOrder.AscendingOrder)
        self.assertEqual(
            names(self.tree.invisibleRootItem()),
            ["scratch", "on_host.out", "small.out", "big.out"],
        )

    def test_open_folders_and_the_selection_survive_a_sort(self):
        outer = self.folder("outer")
        inner = self.folder("inner", outer)
        picked = self.file("b.out", parent=inner)
        self.file("a.out", parent=inner)
        outer.setExpanded(True)
        inner.setExpanded(True)
        self.tree.setCurrentItem(picked)
        self.tree.header().setSortIndicator(0, Qt.SortOrder.DescendingOrder)
        self.assertTrue(outer.isExpanded())
        self.assertTrue(inner.isExpanded())
        self.assertIs(self.tree.currentItem(), picked)
        self.assertEqual(names(inner), ["b.out", "a.out"])


class TestOutputRanking(unittest.TestCase):
    def test_a_file_nearer_the_job_directory_is_preferred(self):
        self.assertEqual(primary_output(["steps/opt/calc.out", "final.xyz"]), "final.xyz")
        self.assertEqual(primary_output(["steps/calc.out", "calc.log", "calc.out"]), "calc.out")
        self.assertEqual(
            likely_outputs(["a/b.out", "a/b/c.out", "d.log"]), ["d.log", "a/b.out", "a/b/c.out"]
        )


class TestJobFilesFolders(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.temp_dir, True)
        self.service = MagicMock()
        self.service.store.hosts = {}
        self.service.store.directory = self.temp_dir
        self.job = Job(
            id="job1",
            host_id="host1",
            name="job",
            remote_dir="/opt/jobs/job1",
            local_dir=os.path.join(self.temp_dir, "local"),
        )
        self.dialog = OutputFileSelectorDialog(self.service, self.job)
        self.addCleanup(self.dialog.deleteLater)

    def top(self, name):
        root = self.dialog.tree.invisibleRootItem()
        return next(
            root.child(i) for i in range(root.childCount()) if root.child(i).text(0) == name
        )

    def test_folders_start_closed_and_come_first(self):
        self.dialog._populate_tree_remote(["result.out", "scratch/tmp.xyz", "archive/old.log"])
        root = self.dialog.tree.invisibleRootItem()
        self.assertEqual(names(root), ["archive", "scratch", "result.out"])
        self.assertFalse(self.top("archive").isExpanded())
        self.assertFalse(self.top("scratch").isExpanded())
        self.assertEqual(self.dialog.tree.currentItem().text(0), "result.out")

    def test_the_folder_holding_the_only_output_is_opened(self):
        self.dialog._populate_tree_remote(["notes.txt", "run/opt/calc.out", "other/x.dat"])
        current = self.dialog.tree.currentItem()
        self.assertEqual(current.text(0), "calc.out")
        self.assertTrue(current.parent().isExpanded())
        self.assertTrue(self.top("run").isExpanded())
        self.assertFalse(self.top("other").isExpanded())

    def test_a_folder_opened_by_hand_stays_open_when_the_listing_returns(self):
        self.dialog._populate_tree_remote(["result.out", "scratch/tmp.xyz"])
        self.top("scratch").setExpanded(True)
        self.dialog._populate_tree_remote(["result.out", "scratch/tmp.xyz", "scratch/b.xyz"])
        self.assertTrue(self.top("scratch").isExpanded())

    def test_the_chosen_order_is_kept_when_the_listing_returns(self):
        self.dialog.tree.header().setSortIndicator(0, Qt.SortOrder.DescendingOrder)
        self.dialog._populate_tree_remote(["a.out", "b.out", "sub/c.out"])
        self.assertEqual(names(self.dialog.tree.invisibleRootItem()), ["sub", "b.out", "a.out"])


class TestPickerLists(unittest.TestCase):
    """The tail and download choosers: folders first and closed, the pick in view."""

    def top(self, tree, name):
        root = tree.invisibleRootItem()
        return next(
            root.child(i) for i in range(root.childCount()) if root.child(i).text(0) == name
        )

    def test_tail_file_opens_only_the_folder_of_the_default_file(self):
        from job_manager.tail_file_dialog import TailFileDialog

        dialog = TailFileDialog(
            "job", ["z.log", "run/opt/calc.out", "other/x.dat"], default_file="run/opt/calc.out"
        )
        self.addCleanup(dialog.deleteLater)
        self.assertEqual(names(dialog.tree.invisibleRootItem()), ["other", "run", "z.log"])
        self.assertEqual(dialog.chosen(), "run/opt/calc.out")
        self.assertTrue(self.top(dialog.tree, "run").isExpanded())
        self.assertFalse(self.top(dialog.tree, "other").isExpanded())

    def test_tail_file_filter_shows_every_match(self):
        from job_manager.tail_file_dialog import TailFileDialog

        dialog = TailFileDialog("job", ["a/x.out", "b/x.out", "c.log"])
        self.addCleanup(dialog.deleteLater)
        dialog.txt_filter.setText("x.out")
        self.assertTrue(self.top(dialog.tree, "a").isExpanded())
        self.assertTrue(self.top(dialog.tree, "b").isExpanded())

    def test_download_opens_only_folders_with_a_ticked_file(self):
        from job_manager.download_dialog import DownloadDialog

        temp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, temp, True)
        dialog = DownloadDialog(
            "job",
            ["step10.out", "step2.out", "scratch/tmp.chk", "keep/result.xyz"],
            ["keep/result.xyz"],
            temp,
            "Download",
        )
        self.addCleanup(dialog.deleteLater)
        self.assertEqual(
            names(dialog.tree.invisibleRootItem()), ["keep", "scratch", "step2.out", "step10.out"]
        )
        self.assertTrue(self.top(dialog.tree, "keep").isExpanded())
        self.assertFalse(self.top(dialog.tree, "scratch").isExpanded())


if __name__ == "__main__":
    unittest.main()
