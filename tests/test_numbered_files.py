"""{1}, {2}, ... name the files in the input list, in order."""

import unittest

from job_manager.schedulers import get_scheduler
from job_manager.schedulers.base import format_command, numbered_file_tags, references_input

from .fakes import make_preset


class TestNumberedFilePlaceholders(unittest.TestCase):
    def setUp(self):
        self.preset = make_preset()

    def test_files_are_substituted_in_list_order(self):
        text = format_command(
            "prog {1} --restart {2}", "a.inp", self.preset, input_files=["a.inp", "b.gbw"]
        )
        self.assertEqual(text, "prog a.inp --restart b.gbw")

    def test_only_the_file_name_reaches_the_command(self):
        text = format_command("prog {1}", "", self.preset, input_files=[r"C:\data\a.inp"])
        self.assertEqual(text, "prog a.inp")

    def test_with_nothing_uploaded_one_is_the_named_input(self):
        self.assertEqual(format_command("prog {1}", "on_host.inp", self.preset), "prog on_host.inp")

    def test_shell_parameters_and_indices_are_left_alone(self):
        command = "echo ${1} ${arr[1]} [1]"
        self.assertEqual(
            format_command(command, "a.inp", self.preset, input_files=["a.inp"]), command
        )

    def test_a_number_past_the_list_is_left_verbatim(self):
        text = format_command("prog {3}", "a.inp", self.preset, input_files=["a.inp"])
        self.assertEqual(text, "prog {3}")

    def test_tags_used_are_reported_without_shell_parameters(self):
        self.assertEqual(numbered_file_tags("a {2} ${3} {10} {1}"), [1, 2, 10])

    def test_a_numbered_file_counts_as_naming_an_input(self):
        self.assertTrue(references_input("prog {2}"))
        self.assertFalse(references_input("echo ${1}"))

    def test_both_script_flavours_substitute_them(self):
        preset = make_preset(command_template="prog {1} {2}")
        for name in ("slurm", "windows"):
            script = get_scheduler(name).build_script(
                "job", preset, "a.inp", "job.log", input_files=["a.inp", "b.xyz"]
            )
            self.assertIn("prog a.inp b.xyz", script, name)


if __name__ == "__main__":
    unittest.main()
