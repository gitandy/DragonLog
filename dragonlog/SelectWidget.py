from typing import Iterable
from PyQt6 import QtWidgets, QtCore

from . import SelectWidget_ui


class SelectWidget(QtWidgets.QWidget, SelectWidget_ui.Ui_SelectWidget):
    selectionChanged = QtCore.pyqtSignal()

    def __init__(self, parent, items: Iterable[str], title_enabled: str = '', title_disabled: str = ''):
        super().__init__(parent)
        self.setupUi(self)

        self.__items__: list[str]
        self.items = items

        if title_enabled:
            self.labelEnabled.setText(title_enabled)
        if title_disabled:
            self.labelDisabled.setText(title_disabled)

    def disableItem(self):
        for item in self.enabledListWidget.selectedItems():
            self.disabledListWidget.insertItem(0, item.text())
            self.enabledListWidget.takeItem(self.enabledListWidget.row(item))

        self.disabledListWidget.sortItems()
        self.selectionChanged.emit()

    def enableItem(self):
        for item in self.disabledListWidget.selectedItems():
            self.enabledListWidget.insertItem(0, item.text())
            self.disabledListWidget.takeItem(self.disabledListWidget.row(item))

        self.enabledListWidget.sortItems()
        self.selectionChanged.emit()

    def clear(self):
        self.enabledListWidget.clear()
        self.disabledListWidget.clear()

        for i, it in enumerate(self.__items__, 1):
            self.enabledListWidget.addItem(f'{i:02d} - {it}')

        self.sortItems()
        self.selectionChanged.emit()

    @property
    def items(self) -> list[str]:
        """Return all available items"""
        return self.__items__

    @items.setter
    def items(self, items: Iterable[str]):
        """Set available items"""
        self.__items__ = list(items)
        self.clear()

    @property
    def itemsEnabled(self) -> list[str]:
        """Return enabled items"""
        return [i.text().split('-')[1].strip() for i in
                self.enabledListWidget.findItems('.*', QtCore.Qt.MatchFlag.MatchRegularExpression)]

    @property
    def indexesEnabled(self) -> list[int]:
        """Return enabled items indexes"""
        return [int(i.text().split('-')[0].strip()) for i in
                self.enabledListWidget.findItems('.*', QtCore.Qt.MatchFlag.MatchRegularExpression)]

    @property
    def indexesDisabled(self) -> list[int]:
        """Return disabled items indexes for compatibility"""
        return [int(i.text().split('-')[0].strip()) for i in
                self.disabledListWidget.findItems('.*', QtCore.Qt.MatchFlag.MatchRegularExpression)]

    @itemsEnabled.setter
    def itemsEnabled(self, items: Iterable[str]):
        self.enabledListWidget.clear()
        self.disabledListWidget.clear()

        for i, it in enumerate(self.__items__, 1):
            if it in items:
                self.enabledListWidget.addItem(f'{i:02d} - {it}')
            else:
                self.disabledListWidget.addItem(f'{i:02d} - {it}')

        self.sortItems()
        self.selectionChanged.emit()

    @indexesEnabled.setter
    def indexesEnabled(self, indexes: Iterable[int]):
        """Set disabled items by indexes"""

        self.enabledListWidget.clear()
        self.disabledListWidget.clear()

        for i, it in enumerate(self.__items__, 1):
            if i in indexes:
                self.enabledListWidget.addItem(f'{i:02d} - {it}')
            else:
                self.disabledListWidget.addItem(f'{i:02d} - {it}')

        self.sortItems()
        self.selectionChanged.emit()

    @indexesDisabled.setter
    def indexesDisabled(self, indexes: Iterable[int]):
        """Set disabled items by indexes for compatibility"""

        self.enabledListWidget.clear()
        self.disabledListWidget.clear()

        for i, it in enumerate(self.__items__, 1):
            if i in indexes:
                self.disabledListWidget.addItem(f'{i:02d} - {it}')
            else:
                self.enabledListWidget.addItem(f'{i:02d} - {it}')

        self.sortItems()
        self.selectionChanged.emit()

    def sortItems(self):
        self.enabledListWidget.sortItems()
        self.disabledListWidget.sortItems()
