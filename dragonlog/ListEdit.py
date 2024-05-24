from PyQt6 import QtWidgets, QtCore

from . import ListEdit_ui


class ListEdit(QtWidgets.QWidget, ListEdit_ui.Ui_ListEditForm):
    listChanged = QtCore.pyqtSignal()

    def __init__(self, parent, titel=''):
        super().__init__(parent)
        self.setupUi(self)

        if not titel:
            self.layout().removeWidget(self.label)
            del self.label
        else:
            self.label.setText(titel)

        self.listWidget.itemChanged.connect(self.listChanged.emit)

    def clear(self):
        self.listWidget.clear()
        self.delPushButton.setEnabled(False)
        self.listChanged.emit()

    def items(self):
        items = []
        for i in range(self.listWidget.count()):
            if self.listWidget.item(i).text().strip() not in (self.tr('(empty)'), ''):
                items.append(self.listWidget.item(i).text())
        return items

    def setItems(self, items: list[str]):
        if items:
            for item_str in items:
                if item_str:
                    item = QtWidgets.QListWidgetItem(item_str)
                    item.setFlags(item.flags() | QtCore.Qt.ItemFlag.ItemIsEditable)
                    self.listWidget.addItem(item)
                    self.delPushButton.setEnabled(True)
                    self.listChanged.emit()

    def addEmptyItem(self):
        item = QtWidgets.QListWidgetItem(self.tr('(empty)'))
        item.setFlags(item.flags() | QtCore.Qt.ItemFlag.ItemIsEditable)
        self.listWidget.addItem(item)
        self.delPushButton.setEnabled(True)

    def removeSelectedItem(self):
        for item in self.listWidget.selectedItems():
            self.listWidget.takeItem(self.listWidget.row(item))
            self.listChanged.emit()

        if self.listWidget.count() < 1:
            self.delPushButton.setEnabled(False)
