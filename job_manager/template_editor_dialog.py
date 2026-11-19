"""Editor for the two kinds of command MoleditPy remembers for you.

Per-extension defaults (``store.default_command_for``) and named templates
(``store.user_templates()``) could previously only be *added*, from the submit
wizard's dropdown -- a saved template could be deleted one at a time through a
QInputDialog picker, but a per-extension default had no delete path in the UI
at all short of editing settings.json by hand. This dialog lists both, and
lets either be edited or removed.

Either kind may belong to one host (``host_id``) or to every host. A host's
own is used there ahead of the one for every host, so the same program can be
run from a different path on each machine; the Host filter shows one host's
view, and Copy to host... starts a host's own from an existing one.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from . import PLUGIN_VERSION
from .theme import apply_theme, mark_muted
from .window_utils import make_independent

#: Shown wherever a command line is edited here, so the placeholders are
#: explained at the point someone is most likely to type one.
PLACEHOLDER_TIP = (
    "Placeholders substituted at submit time:\n"
    "  {input}     the uploaded file's name, e.g. water.inp\n"
    "  {stem}      the same, without its extension, e.g. water\n"
    "  {output}    {stem}.out\n"
    "  {1} {2} ... the files in the input list, by their number there;\n"
    "              {1} is the same file as {input}\n"
    "  {all}       every file in the list, in order, separated by spaces\n"
    "  {name}      the job's display name\n"
    "  {jobdir}    the job's directory on the host\n"
    "  {nodes} {ntasks} {cpus} {memory} {queue} {walltime}\n"
    "              the preset's resource request"
)

PLACEHOLDER_NOTES = (
    "${1} stays the shell's own parameter, not a file. A number past the end of the\n"
    "list is refused at submit, and in a batch each job has only {1}.\n"
    "Unknown tags are left as written. Nothing is quoted for you:\n"
    'write cd "{jobdir}" where a value may contain spaces.'
)


def show_placeholder_help(parent: Optional[QWidget] = None) -> None:
    """The placeholder list in a window of its own, in a fixed font so the
    columns line up -- a tooltip vanishes the moment the mouse moves."""
    from PySide6.QtGui import QFontDatabase

    dialog = QDialog(parent)
    dialog.setWindowTitle(f"Job Manager {PLUGIN_VERSION} - Command Placeholders")
    apply_theme(dialog)
    layout = QVBoxLayout(dialog)
    text = QPlainTextEdit(PLACEHOLDER_TIP + "\n\n" + PLACEHOLDER_NOTES)
    text.setReadOnly(True)
    text.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
    text.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
    layout.addWidget(text)
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)
    dialog.resize(640, 420)
    dialog.exec()


EXT_ROLE = Qt.ItemDataRole.UserRole
CMD_ROLE = Qt.ItemDataRole.UserRole + 1
GLOBS_ROLE = Qt.ItemDataRole.UserRole + 2
HOST_ROLE = Qt.ItemDataRole.UserRole + 3

#: Filter values that are not a host id.
ALL_SCOPES = None
EVERY_HOST = ""


class TemplateEditorDialog(QDialog):
    """Manage per-extension default commands and named command templates."""

    def __init__(self, store, parent: Optional[QWidget] = None, host_id: str = "") -> None:
        super().__init__(parent)
        self.store = store
        #: Opened from a host (the submit wizard, or Hosts): show that host's view.
        self._initial_host = host_id
        self.setWindowTitle(f"Job Manager {PLUGIN_VERSION} - Command Templates")
        make_independent(self)
        apply_theme(self)
        self.resize(620, 520)
        self._build_ui()
        self._reload()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        hint = QLabel(
            "Commands you have told the submit wizard to remember: one per "
            "input extension ('use this for every .inp'), and any you saved "
            "under a name of your own. Each is for every host or for one host; "
            "a host's own is used there first."
        )
        hint.setWordWrap(True)
        mark_muted(hint)
        layout.addWidget(hint)

        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Host"))
        self.cmb_host = QComboBox()
        self.cmb_host.addItem("All", ALL_SCOPES)
        self.cmb_host.addItem("Every host (shared)", EVERY_HOST)
        for host in self._hosts():
            self.cmb_host.addItem(host.name, host.id)
        found = self.cmb_host.findData(self._initial_host) if self._initial_host else -1
        self.cmb_host.setCurrentIndex(found if found >= 0 else 0)
        self.cmb_host.currentIndexChanged.connect(lambda _index: self._reload())
        filter_row.addWidget(self.cmb_host, 1)
        layout.addLayout(filter_row)

        defaults_box = QGroupBox("Default command per extension")
        defaults_layout = QVBoxLayout(defaults_box)
        self.list_defaults = QListWidget()
        self.list_defaults.setToolTip(PLACEHOLDER_TIP)
        self.list_defaults.itemDoubleClicked.connect(self._edit_default)
        defaults_layout.addWidget(self.list_defaults)
        defaults_buttons = QHBoxLayout()
        btn_edit_default = QPushButton("Edit...")
        btn_edit_default.clicked.connect(self._edit_selected_default)
        btn_delete_default = QPushButton("Delete")
        btn_delete_default.clicked.connect(self._delete_selected_default)
        btn_copy_default = QPushButton("Copy to host...")
        btn_copy_default.setToolTip("Start a host's own default from this one.")
        btn_copy_default.clicked.connect(self._copy_selected_default)
        defaults_buttons.addWidget(btn_edit_default)
        defaults_buttons.addWidget(btn_copy_default)
        defaults_buttons.addWidget(btn_delete_default)
        defaults_buttons.addStretch(1)
        defaults_layout.addLayout(defaults_buttons)
        layout.addWidget(defaults_box, 1)

        templates_box = QGroupBox("Saved templates")
        templates_layout = QVBoxLayout(templates_box)
        self.list_templates = QListWidget()
        self.list_templates.setToolTip(PLACEHOLDER_TIP)
        self.list_templates.itemDoubleClicked.connect(self._edit_template)
        templates_layout.addWidget(self.list_templates)
        templates_buttons = QHBoxLayout()
        btn_edit_template = QPushButton("Edit...")
        btn_edit_template.clicked.connect(self._edit_selected_template)
        btn_delete_template = QPushButton("Delete")
        btn_delete_template.clicked.connect(self._delete_selected_template)
        btn_copy_template = QPushButton("Copy to host...")
        btn_copy_template.setToolTip("Start a host's own template from this one.")
        btn_copy_template.clicked.connect(self._copy_selected_template)
        templates_buttons.addWidget(btn_edit_template)
        templates_buttons.addWidget(btn_copy_template)
        templates_buttons.addWidget(btn_delete_template)
        templates_buttons.addStretch(1)
        templates_layout.addLayout(templates_buttons)
        layout.addWidget(templates_box, 1)

        box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        box.rejected.connect(self.reject)
        box.accepted.connect(self.accept)
        layout.addWidget(box)

    # --- loading --------------------------------------------------------

    def _hosts(self):
        host_list = getattr(self.store, "host_list", None)
        return list(host_list()) if callable(host_list) else []

    def _host_name(self, host_id: str) -> str:
        if not host_id:
            return "every host"
        host = getattr(self.store, "hosts", {}).get(host_id)
        return host.name if host is not None else "removed host"

    def _shown(self, host_id: str) -> bool:
        """Whether the Host filter shows an entry for ``host_id`` ("" = every host)."""
        wanted = self.cmb_host.currentData()
        if wanted is ALL_SCOPES:
            return True
        if wanted == EVERY_HOST:
            return not host_id
        # One host's view: what that host actually gets, its own and the shared.
        return host_id in ("", wanted)

    def _item(self, key: str, command: str, globs, host_id: str) -> QListWidgetItem:
        item = QListWidgetItem(f"[{self._host_name(host_id)}]  {key}  \u2192  {command}")
        item.setData(EXT_ROLE, key)
        item.setData(CMD_ROLE, command)
        item.setData(GLOBS_ROLE, list(globs or []))
        item.setData(HOST_ROLE, host_id)
        item.setToolTip(command)
        return item

    def _reload(self) -> None:
        self.list_defaults.clear()
        entries = []
        defaults = self.store.get_pref("default_commands", {}) or {}
        for extension in sorted(defaults):
            entries.append((EVERY_HOST, extension, defaults.get(extension) or {}))
        names = {host.id: host.name.lower() for host in self._hosts()}
        per_host = self.store.host_default_commands()
        for host_id in sorted(per_host, key=lambda h: names.get(h, h)):
            for extension in sorted(per_host[host_id]):
                entries.append((host_id, extension, per_host[host_id][extension]))
        shown = 0
        for host_id, extension, entry in entries:
            if not self._shown(host_id):
                continue
            self.list_defaults.addItem(
                self._item(
                    extension,
                    str(entry.get("command", "")),
                    entry.get("fetch_globs"),
                    host_id,
                )
            )
            shown += 1
        if not shown:
            placeholder = QListWidgetItem("No per-extension defaults here yet.")
            placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
            self.list_defaults.addItem(placeholder)

        self.list_templates.clear()
        shown = 0
        for entry in self.store.user_templates():
            host_id = entry.get("host_id", "")
            if not self._shown(host_id):
                continue
            self.list_templates.addItem(
                self._item(
                    entry.get("label", ""),
                    entry.get("command", ""),
                    entry.get("fetch_globs"),
                    host_id,
                )
            )
            shown += 1
        if not shown:
            placeholder = QListWidgetItem("No saved templates here yet.")
            placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
            self.list_templates.addItem(placeholder)

    def _choose_host(self, title: str) -> Optional[str]:
        """A host id picked from the list, or None when cancelled or there is none."""
        hosts = self._hosts()
        if not hosts:
            QMessageBox.information(self, title, "Add a host first.")
            return None
        names = [host.name for host in hosts]
        current = self.cmb_host.currentData()
        start = next((i for i, host in enumerate(hosts) if host.id == current), 0)
        name, accepted = QInputDialog.getItem(
            self, title, "Copy to which host?", names, start, False
        )
        if not accepted or not name:
            return None
        return hosts[names.index(name)].id

    # --- default commands -------------------------------------------------

    def _edit_selected_default(self) -> None:
        item = self.list_defaults.currentItem()
        if item is not None:
            self._edit_default(item)

    def _edit_default(self, item: QListWidgetItem) -> None:
        extension = item.data(EXT_ROLE)
        if not extension:
            return
        command, accepted = QInputDialog.getText(
            self,
            f"Default command for {extension}",
            f"Command run for every {extension} input:\n\n{PLACEHOLDER_TIP}",
            QLineEdit.EchoMode.Normal,
            item.data(CMD_ROLE) or "",
        )
        if not accepted:
            return
        self.store.set_default_command(
            extension,
            command.strip(),
            item.data(GLOBS_ROLE) or [],
            host_id=item.data(HOST_ROLE) or "",
        )
        self._reload()

    def _delete_selected_default(self) -> None:
        item = self.list_defaults.currentItem()
        extension = item.data(EXT_ROLE) if item is not None else None
        if not extension:
            return
        host_id = item.data(HOST_ROLE) or ""
        where = f" on {self._host_name(host_id)}" if host_id else ""
        confirm = QMessageBox.question(
            self,
            "Delete default",
            f"Stop remembering a default command for {extension}{where}?",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        # An empty command is what set_default_command treats as "forget it".
        self.store.set_default_command(extension, "", [], host_id=host_id)
        self._reload()

    def _copy_selected_default(self) -> None:
        item = self.list_defaults.currentItem()
        extension = item.data(EXT_ROLE) if item is not None else None
        if not extension:
            return
        host_id = self._choose_host("Copy default")
        if host_id is None:
            return
        self.store.set_default_command(
            extension, item.data(CMD_ROLE) or "", item.data(GLOBS_ROLE) or [], host_id=host_id
        )
        self._reload()

    # --- named templates ----------------------------------------------------

    def _edit_selected_template(self) -> None:
        item = self.list_templates.currentItem()
        if item is not None:
            self._edit_template(item)

    def _edit_template(self, item: QListWidgetItem) -> None:
        label = item.data(EXT_ROLE)
        if not label:
            return
        command, accepted = QInputDialog.getText(
            self,
            f"Template: {label}",
            f"Command for '{label}':\n\n{PLACEHOLDER_TIP}",
            QLineEdit.EchoMode.Normal,
            item.data(CMD_ROLE) or "",
        )
        if not accepted:
            return
        self.store.add_user_template(
            label, command.strip(), item.data(GLOBS_ROLE) or [], host_id=item.data(HOST_ROLE) or ""
        )
        self._reload()

    def _delete_selected_template(self) -> None:
        item = self.list_templates.currentItem()
        label = item.data(EXT_ROLE) if item is not None else None
        if not label:
            return
        host_id = item.data(HOST_ROLE) or ""
        where = f" for {self._host_name(host_id)}" if host_id else ""
        confirm = QMessageBox.question(
            self, "Delete template", f"Delete the template '{label}'{where}?"
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self.store.remove_user_template(label, host_id)
        self._reload()

    def _copy_selected_template(self) -> None:
        item = self.list_templates.currentItem()
        label = item.data(EXT_ROLE) if item is not None else None
        if not label:
            return
        host_id = self._choose_host("Copy template")
        if host_id is None:
            return
        self.store.add_user_template(
            label, item.data(CMD_ROLE) or "", item.data(GLOBS_ROLE) or [], host_id=host_id
        )
        self._reload()


__all__ = ["TemplateEditorDialog", "PLACEHOLDER_TIP"]
