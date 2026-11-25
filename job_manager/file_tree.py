"""One look for every list of files this plugin shows.

Three dialogs show a job's files -- what to download, what to tail, what to
open -- and each had grown its own version of the same list: one with a filter
box and two without, one with emoji in front of every row, three different
folder styles, three different places for the buttons. They are the same list
of the same files, so they are built from the same pieces here.

Only the presentation is shared. What each dialog does with a selection is its
own business, which is why this module holds no dialog of its own.
"""

from __future__ import annotations

import re
from typing import Callable, Optional, Sequence

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTreeWidget,
    QTreeWidgetItem,
)

from .tree_utils import PATH_ROLE

_DIGITS = re.compile(r"(\d+)")

#: The size in bytes behind the Size column's text, so "900 KB" sorts below
#: "1.2 MB". Unknown sizes (a file still on the host) have none.
SIZE_ROLE = Qt.ItemDataRole.UserRole + 3

#: The same words in all three, so the box is recognised rather than read.
FILTER_PLACEHOLDER = "Filter files (e.g. .out, .log)"

#: Columns for a listing that knows how big the files are. A remote listing
#: does not, and shows the name alone rather than a column of dashes.
FULL_HEADERS = ("File", "Size", "Type", "Where")
NAME_HEADERS = ("File",)


def is_folder_row(item: QTreeWidgetItem) -> bool:
    return item.data(0, PATH_ROLE) is None


def natural_key(text: str) -> tuple:
    """``step2`` before ``step10``, as a file manager orders them."""
    return tuple(
        (0, int(part), "") if part.isdigit() else (1, 0, part)
        for part in _DIGITS.split(text.lower())
        if part
    )


def _sort_key(item: QTreeWidgetItem, column: int) -> tuple:
    name = natural_key(item.text(0))
    if column == 1:
        size = item.data(1, SIZE_ROLE)
        return (-1 if size is None else int(size), name)
    if column > 0:
        return (item.text(column).lower(), name)
    return (name,)


def set_row_size(item: QTreeWidgetItem, size: Optional[int]) -> None:
    item.setData(1, SIZE_ROLE, size)


class TreeSorter:
    """Sorts a file tree by the clicked header, folders always first.

    Qt's own sorting would call a Python ``__lt__`` for every comparison:
    seconds for a folder of fifty thousand files. Here each row's key is read
    once, the rows are sorted in Python and put back in that order.
    """

    def __init__(self, tree: QTreeWidget, on_sorted: Optional[Callable[[], None]] = None):
        self.tree = tree
        self.on_sorted = on_sorted
        header = tree.header()
        header.setSectionsClickable(True)
        header.setSortIndicatorShown(True)
        header.setSortIndicator(0, Qt.SortOrder.AscendingOrder)
        header.sortIndicatorChanged.connect(lambda *_: self.sort())

    def sort(self, parent: Optional[QTreeWidgetItem] = None) -> None:
        """Sort everything below ``parent``, or the whole tree."""
        tree = self.tree
        top = parent or tree.invisibleRootItem()
        if top.childCount() == 0:
            return
        header = tree.header()
        column = header.sortIndicatorSection()
        descending = header.sortIndicatorOrder() == Qt.SortOrder.DescendingOrder
        # Taking rows out of the tree forgets what the view knew about them.
        expanded, selected = [], tree.selectedItems()
        current = tree.currentItem()
        stack = [top]
        while stack:
            item = stack.pop()
            for row in range(item.childCount()):
                child = item.child(row)
                if child.childCount():
                    stack.append(child)
                    if child.isExpanded():
                        expanded.append(child)
        blocked = tree.blockSignals(True)
        try:
            self._sort_children(top, column, descending)
            for item in expanded:
                item.setExpanded(True)
            if current is not None and current.treeWidget() is tree:
                tree.setCurrentItem(current)
            for item in selected:
                item.setSelected(True)
        finally:
            tree.blockSignals(blocked)
        if self.on_sorted is not None:
            self.on_sorted()

    def _sort_children(self, item: QTreeWidgetItem, column: int, descending: bool) -> None:
        children = item.takeChildren()
        folders = [child for child in children if is_folder_row(child)]
        files = [child for child in children if not is_folder_row(child)]
        folders.sort(key=lambda row: _sort_key(row, column), reverse=descending)
        files.sort(key=lambda row: _sort_key(row, column), reverse=descending)
        item.addChildren(folders + files)
        for folder in folders:
            if folder.childCount():
                self._sort_children(folder, column, descending)


def reveal(item: QTreeWidgetItem) -> None:
    """Open the folders ``item`` sits in, which start closed."""
    parent = item.parent()
    while parent is not None:
        parent.setExpanded(True)
        parent = parent.parent()


def configure_tree(
    tree: QTreeWidget,
    headers: Sequence[str] = NAME_HEADERS,
    multi_select: bool = False,
) -> QTreeWidget:
    """Apply the shared look to a file tree."""
    tree.setColumnCount(len(headers))
    tree.setHeaderLabels(list(headers))
    # A single-column list has nothing to label, so its header is a bar of
    # wasted height rather than information.
    tree.setHeaderHidden(len(headers) <= 1)
    tree.setAlternatingRowColors(True)
    tree.setUniformRowHeights(True)
    tree.setSelectionMode(
        QAbstractItemView.SelectionMode.ExtendedSelection
        if multi_select
        else QAbstractItemView.SelectionMode.SingleSelection
    )
    tree.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    return tree


def folder_factory(checkable: bool = False, columns: int = 1) -> Callable:
    """A folder row: the name in bold, and nothing else in the row.

    Bold rather than an icon character. A folder emoji is drawn from whichever
    font the platform substitutes, at that font's own size, so it sits crushed
    and off-baseline against the text beside it -- and it says nothing the
    indentation and the bold do not.
    """

    def make(name: str, parts: Sequence[str], parent: Optional[QTreeWidgetItem]) -> QTreeWidgetItem:
        # Unattached on purpose: ensure_folder_item owns insertion, and building
        # it with a parent here would insert the same folder twice.
        item = QTreeWidgetItem([name] + [""] * (columns - 1))
        font = item.font(0)
        font.setBold(True)
        item.setFont(0, font)
        item.setData(0, PATH_ROLE, None)
        if checkable:
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(0, Qt.CheckState.Unchecked)
        else:
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
        return item

    return make


def make_filter_row(on_changed: Callable[[str], None]) -> tuple:
    """The filter box every one of these lists has. Returns (row, field)."""
    row = QHBoxLayout()
    row.setSpacing(6)
    row.addWidget(QLabel("Filter"))
    field = QLineEdit()
    field.setPlaceholderText(FILTER_PLACEHOLDER)
    field.setClearButtonEnabled(True)
    field.textChanged.connect(on_changed)
    row.addWidget(field, 1)
    return row, field


__all__ = [
    "FILTER_PLACEHOLDER",
    "SIZE_ROLE",
    "TreeSorter",
    "is_folder_row",
    "natural_key",
    "reveal",
    "set_row_size",
    "FULL_HEADERS",
    "NAME_HEADERS",
    "configure_tree",
    "folder_factory",
    "make_filter_row",
]
