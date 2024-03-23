import os.path
import sys
import logging

from PyQt6 import QtCore, QtWidgets, QtGui


class Logger(logging.Handler):
    def __init__(self, log_widget: QtWidgets.QTextEdit, settings: QtCore.QSettings):
        super().__init__()
        self.log_widget = log_widget
        self.settings = settings

        self.__loglevel__ = self.settings.value('ui/log_level', 'INFO')

        self.setFormatter(logging.Formatter('%(asctime)s %(levelname)-8s: %(name)s - %(message)s'))
        self.__log__ = logging.getLogger('DragonLog')
        self.__log__.setLevel(self.__loglevel__)
        self.__log__.addHandler(self)

        self.__log_file__ = None
        if int(self.settings.value('ui/log_file', 0)):
            try:
                self.__log_file__ = open(os.path.expanduser('~/DragonLog.log'), 'a', buffering=1, encoding='utf8')
            except Exception as exc:
                self.error('Log file could not be opened')
                self.exception(exc)

    @property
    def loglevel(self) -> str:
        return self.__loglevel__

    def emit(self, record):
        log_msg = self.format(record)

        if record.levelno >= 40:  # Error/Critical
            self.log_widget.setTextColor(QtGui.QColor('red'))
            print(log_msg, file=sys.stderr)
        elif record.levelno >= 30:  # Warning
            self.log_widget.setTextColor(QtGui.QColor('orange'))
            print(self.format(record), file=sys.stderr)
        elif record.levelno < 20:  # Debug
            self.log_widget.setTextColor(QtGui.QColor('grey'))
            print(self.format(record))
        else:  # Info >= 20
            self.log_widget.setTextColor(QtGui.QColor('black'))
            print(self.format(record))

        if self.__log_file__:
            self.__log_file__.write(log_msg + '\n')

        self.log_widget.append(log_msg)
        self.log_widget.repaint()

    def debug(self, message):
        self.__log__.debug(message)

    def info(self, message):
        self.__log__.info(message)

    def warning(self, message):
        self.__log__.warning(message)

    def error(self, message):
        self.__log__.error(message)

    def critical(self, message):
        self.__log__.critical(message)

    def exception(self, message):
        self.__log__.exception(message)

    def __del_(self):
        self.__log_file__.close()
