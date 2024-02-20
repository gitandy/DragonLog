import os

from PyQt6 import QtWidgets, QtCore

from . import DragonLog_AppSelect_ui

class AppSelect(QtWidgets.QDialog, DragonLog_AppSelect_ui.Ui_appSelectDialog):
    def __init__(self, parent, title: str, settings: QtCore.QSettings):
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowTitle(title)
        self.settings = settings

    def exec(self) -> tuple[str, str]:
        if super().exec() == 1:
            if self.wsjtxRadioButton.isChecked():
                if os.name == 'posix':
                    path = os.path.abspath(os.path.expanduser('~/.local/share/WSJT-X/wsjtx_log.adi'))
                elif os.name == 'nt':
                    path = os.path.abspath(os.path.expanduser('~/AppData/Local/WSJT-X/wsjtx_log.adi'))
                else:
                    path = os.path.abspath(os.curdir)
                return 'WSJTX', self.settings.value('lastWatchFileWSJTX', path)
            elif self.js8callRadioButton.isChecked():
                if os.name == 'posix':
                    path = os.path.abspath(os.path.expanduser('~/.local/share/JS8Call/js8call_log.adi'))
                elif os.name == 'nt':
                    path = os.path.abspath(os.path.expanduser('~/AppData/Local/JS8Call/js8call_log.adi'))
                else:
                    path = os.path.abspath(os.curdir)
                return 'JS8Call', self.settings.value('lastWatchFileJS8Call', path)
            elif self.fldigiRadioButton.isChecked():
                if os.name == 'posix':
                    path = os.path.abspath(os.path.expanduser('~/.fldigi/logs/logbook.adi'))
                elif os.name == 'nt':
                    path = os.path.abspath(os.path.expanduser('~/fldigi.files/logs/logbook.adi'))
                else:
                    path = os.path.abspath(os.curdir)
                return 'fldigi', self.settings.value('lastWatchFilefldigi', path)
            else:
                return 'Other', self.settings.value('lastWatchFile', os.path.abspath(os.curdir))
