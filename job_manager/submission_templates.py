"""Command-template selection and preferences, independent of submission."""

from __future__ import annotations

import os
from typing import Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QInputDialog, QMessageBox

from .command_templates import CommandTemplate, extension_of, suggest, templates_for
from .submission_config import (
    _DELETE_TEMPLATE,
    _MANAGE_TEMPLATES,
    _PLACEHOLDER_HELP,
    _SAVE_TEMPLATE,
    _SAVE_TEMPLATE_HOST,
    _SET_DEFAULT,
    _SET_DEFAULT_HOST,
)

#: Shown after a template's name when it belongs to one host only.
HOST_MARK = "  [{host}]"


class SubmissionTemplates:
    def __init__(self, store, selected_files, command, globs, combo, parent, current_host=None):
        self.store = store
        self.selected_files = selected_files
        self.txt_command = command
        self.txt_globs = globs
        self.cmb_template = combo
        self.parent = parent
        #: The host the form is for, or None; host-scoped templates follow it.
        self.current_host: Callable[[], Optional[object]] = current_host or (lambda: None)
        self._globs_before_template = []
        #: The command this class last filled in by itself. While the field
        #: still holds it, a host switch may replace it with that host's own.
        self._auto_command = ""

    def _host_id(self) -> str:
        host = self.current_host()
        return getattr(host, "id", "") or ""

    def _host_name(self) -> str:
        host = self.current_host()
        return getattr(host, "name", "") or ""

    def _reload_templates(self) -> None:
        """Refill the dropdown: this host's templates, every host's, then the built-ins."""
        files = self.selected_files()
        host_id = self._host_id()
        self.cmb_template.blockSignals(True)
        self.cmb_template.clear()
        self.cmb_template.addItem("Template...", None)

        saved = self.store.user_templates(host_id)
        for entry in saved:
            label = entry["label"]
            if entry.get("host_id"):
                label += HOST_MARK.format(host=self._host_name())
            self.cmb_template.addItem(
                label,
                CommandTemplate(
                    entry["label"],
                    entry["command"],
                    fetch_globs=tuple(entry.get("fetch_globs") or ()),
                ),
            )
            self.cmb_template.setItemData(
                self.cmb_template.count() - 1,
                entry["command"]
                + ("\n\nFor this host only." if entry.get("host_id") else "\n\nFor every host."),
                Qt.ItemDataRole.ToolTipRole,
            )
        if saved:
            self.cmb_template.insertSeparator(self.cmb_template.count())

        for template in templates_for(os.path.basename(files[0]) if files else ""):
            self.cmb_template.addItem(template.label, template)
            if template.note:
                self.cmb_template.setItemData(
                    self.cmb_template.count() - 1,
                    f"{template.command or '(type your own)'}\n\n{template.note}",
                    Qt.ItemDataRole.ToolTipRole,
                )

        self.cmb_template.insertSeparator(self.cmb_template.count())
        extension = extension_of(os.path.basename(files[0])) if files else ""
        # One entry per scope rather than a question afterwards: which host a
        # command is for is decided where it is chosen.
        name = self._host_name()
        if extension:
            # ORCA, CP2K and GAMESS all write .inp, so the wizard will not
            # guess -- but it will remember which one this user means.
            if host_id:
                self.cmb_template.addItem(
                    f"Use this command for every {extension} on {name}", _SET_DEFAULT_HOST
                )
            self.cmb_template.addItem(
                f"Use this command for every {extension} on every host", _SET_DEFAULT
            )
        if host_id:
            self.cmb_template.addItem(f"Save current command for {name}...", _SAVE_TEMPLATE_HOST)
        self.cmb_template.addItem("Save current command for every host...", _SAVE_TEMPLATE)
        if self.store.user_templates():
            self.cmb_template.addItem("Delete a saved template...", _DELETE_TEMPLATE)
        self.cmb_template.addItem("Manage templates...", _MANAGE_TEMPLATES)
        self.cmb_template.addItem("Placeholder help...", _PLACEHOLDER_HELP)
        self.cmb_template.blockSignals(False)

    def _on_template_chosen(self, index: int) -> None:
        choice = self.cmb_template.itemData(index)
        self.cmb_template.setCurrentIndex(0)
        if choice is _SAVE_TEMPLATE:
            self._save_user_template()
        elif choice is _SAVE_TEMPLATE_HOST:
            self._save_user_template(this_host=True)
        elif choice is _SET_DEFAULT:
            self._set_default_for_extension()
        elif choice is _SET_DEFAULT_HOST:
            self._set_default_for_extension(this_host=True)
        elif choice is _DELETE_TEMPLATE:
            self._delete_user_template()
        elif choice is _MANAGE_TEMPLATES:
            self._manage_templates()
        elif choice is _PLACEHOLDER_HELP:
            from .template_editor_dialog import show_placeholder_help

            show_placeholder_help(self.parent)
        elif choice is not None:
            self.txt_command.setText(choice.command)
            # Picked by hand: a host switch must leave it alone.
            self._auto_command = ""
            self._apply_template_globs(choice)

    def _apply_template_globs(self, template: CommandTemplate) -> None:
        """Take the fetch patterns from the program that was just chosen.

        Never over a list the user has edited: a filled field is a decision.
        """
        if not template.fetch_globs:
            return
        current = [g.strip() for g in self.txt_globs.text().split(",") if g.strip()]
        if current and current != self._globs_before_template:
            return
        self.txt_globs.setText(", ".join(template.fetch_globs))
        self._globs_before_template = list(template.fetch_globs)

    def _set_default_for_extension(self, this_host: bool = False) -> None:
        """Make this command what an input of that extension gets from now on.

        ``this_host`` keeps it to the host on the form, ahead of the default
        for every host there.
        """
        files = self.selected_files()
        extension = extension_of(os.path.basename(files[0])) if files else ""
        command = self.txt_command.text().strip()
        if not extension:
            return
        if not command:
            QMessageBox.information(self.parent, "Default command", "Enter a command first.")
            return
        scope = self._host_id() if this_host else ""
        globs = [g.strip() for g in self.txt_globs.text().split(",") if g.strip()]
        self.store.set_default_command(extension, command, globs, host_id=scope)
        where = f" on {self._host_name()}" if scope else ""
        QMessageBox.information(
            self.parent,
            "Default command",
            f"Every {extension} added from now on{where} starts with this command"
            + (" and these fetch patterns." if globs else "."),
        )
        self._reload_templates()

    def _save_user_template(self, this_host: bool = False) -> None:
        """Save the command under a name, for this host only or for every host."""
        command = self.txt_command.text().strip()
        if not command:
            QMessageBox.information(self.parent, "Save template", "Enter a command first.")
            return
        label, accepted = QInputDialog.getText(
            self.parent, "Save template", "Name for this command template:"
        )
        if not accepted or not label.strip():
            return
        scope = self._host_id() if this_host else ""
        globs = [g.strip() for g in self.txt_globs.text().split(",") if g.strip()]
        self.store.add_user_template(label.strip(), command, globs, host_id=scope)
        self._reload_templates()

    def _template_choices(self):
        """Every saved template as (shown name, label, host_id)."""
        names = {host.id: host.name for host in getattr(self.store, "hosts", {}).values()}
        choices = []
        for entry in self.store.user_templates():
            host_id = entry.get("host_id", "")
            shown = entry["label"]
            if host_id:
                shown += HOST_MARK.format(host=names.get(host_id, "removed host"))
            choices.append((shown, entry["label"], host_id))
        return choices

    def _delete_user_template(self) -> None:
        choices = self._template_choices()
        if not choices:
            return
        shown, accepted = QInputDialog.getItem(
            self.parent,
            "Delete template",
            "Remove which template?",
            [c[0] for c in choices],
            0,
            False,
        )
        if not accepted or not shown:
            return
        for name, label, host_id in choices:
            if name == shown:
                self.store.remove_user_template(label, host_id)
                break
        self._reload_templates()

    def _manage_templates(self) -> None:
        from .template_editor_dialog import TemplateEditorDialog

        TemplateEditorDialog(self.store, self.parent, host_id=self._host_id()).exec()
        self._reload_templates()

    def follow_host(self) -> None:
        """After a host switch: take that host's command, unless the user typed one.

        The same program lives at a different path on each machine, so a
        command filled in for the previous host is the wrong one here.
        """
        current = self.txt_command.text().strip()
        if current and current != self._auto_command:
            return
        self._apply_suggested_template(force=True)

    def _apply_suggested_template(self, force: bool = False) -> None:
        """Fill an empty command from the input's extension; if force=True, overwrites."""
        files = self.selected_files()
        if not files:
            return
        if not force and self.txt_command.text().strip():
            return
        filename = os.path.basename(files[0])
        ext = extension_of(filename)
        # The user's own answer first -- this host's, then every host's --
        # ahead of the built-in guess list.
        stored = self.store.default_command_for(ext, self._host_id())
        if stored.get("command"):
            self.txt_command.setText(stored["command"])
            self._auto_command = stored["command"].strip()
            self._apply_template_globs(
                CommandTemplate(
                    "", stored["command"], fetch_globs=tuple(stored.get("fetch_globs") or ())
                )
            )
            return
        template = suggest(filename)
        if template is not None and template.command:
            self.txt_command.setText(template.command)
            self._auto_command = template.command.strip()
            self._apply_template_globs(template)
            for i in range(self.cmb_template.count()):
                if self.cmb_template.itemText(i) == template.label:
                    self.cmb_template.setCurrentIndex(i)
                    break
