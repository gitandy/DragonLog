import os.path
import sys
import time
import logging

from PyQt6 import QtCore, QtWidgets, QtGui


class BaseLogger(logging.Handler):
    def __init__(self, loggername: str | None = None, loglevel: str = 'INFO'):
        super().__init__()

        self.__loglevel__ = loglevel
        logging.Formatter.converter = time.gmtime
        self.setFormatter(logging.Formatter('%(asctime)s %(levelname)-8s: %(name)s - %(message)s'))
        self.__log__ = logging.getLogger(loggername)
        self.__log__.setLevel(self.__loglevel__)
        self.__log__.addHandler(self)

    @property
    def loglevel(self) -> str:
        return self.__loglevel__

    def emit(self, record):
        log_msg = self.format(record)

        if record.levelno >= 30:  # warning, error, critical
            print(log_msg, file=sys.stderr)
        else:  # info, debug
            print(log_msg)

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


class Logger(BaseLogger):
    def __init__(self, log_widget: QtWidgets.QTextEdit, settings: QtCore.QSettings):
        super().__init__('DragonLog', settings.value('ui/log_level', 'INFO'))
        self.log_widget = log_widget

        self.__log_file__ = None
        if int(settings.value('ui/log_file', 0)):
            try:
                self.__log_file__ = open(os.path.expanduser('~/DragonLog.log'), 'a', buffering=1, encoding='utf8')
            except Exception as exc:
                self.error('Log file could not be opened')
                self.exception(exc)

    @property
    def loglevel(self) -> str:
        return self.__loglevel__

    def emit(self, record):
        super().emit(record)

        log_msg = self.format(record)

        if record.levelno >= 40:  # Error/Critical
            self.log_widget.setTextColor(QtGui.QColor('red'))
        elif record.levelno >= 30:  # Warning
            self.log_widget.setTextColor(QtGui.QColor('orange'))
        elif record.levelno < 20:  # Debug
            self.log_widget.setTextColor(QtGui.QColor('grey'))
        else:  # Info >= 20
            self.log_widget.setTextColor(QtGui.QColor('black'))

        if self.__log_file__:
            self.__log_file__.write(log_msg + '\n')

        self.log_widget.append(log_msg)
        self.log_widget.verticalScrollBar().setValue(self.log_widget.verticalScrollBar().maximum())
        self.log_widget.repaint()
