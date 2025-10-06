# DragonLog (c) 2025 by Andreas Schawo is licensed under CC BY-SA 4.0.
# To view a copy of this license, visit http://creativecommons.org/licenses/by-sa/4.0/

import os
import socket
import logging
import platform
import subprocess
import sys
import time

from PyQt6 import QtCore

from .Logger import Logger


class NoExecutableFoundException(Exception):
    pass


class RigctldNotConfiguredException(Exception):
    pass


class CATSettingsMissingException(Exception):
    pass


class RigctldExecutionException(Exception):
    pass


RIGCTL_ECODE = {
    0: 'Command completed successfully',
    -1: 'Invalid parameter',
    -2: 'Invalid configuration',
    -3: 'Memory shortage',
    -4: 'Feature not implemented',
    -5: 'Communication timed out',
    -6: 'IO error',
    -7: 'Internal Hamlib error',
    -8: 'Protocol error',
    -9: 'Command rejected by the rig',
    -10: 'Command performed, but arg truncated, result not guaranteed',
    -11: 'Feature not available',
    -12: 'Target VFO unaccessible',
    -13: 'Communication bus error',
    -14: 'Communication bus collision',
    -15: 'NULL RIG handle or invalid pointer parameter',
    -16: 'Invalid VFO',
    -17: 'Argument out of domain of func',
    -18: 'Function deprecated',
    -19: 'Security error password not provided or crypto failure',
    -20: 'Rig is not powered on',
    -21: 'Limit exceeded',
    -22: 'Access denied',
}


# noinspection PyPep8Naming
class RigControl(QtCore.QObject):
    frequencyChanged = QtCore.pyqtSignal(float)
    bandChanged = QtCore.pyqtSignal(str)
    modeChanged = QtCore.pyqtSignal(str)
    submodeChanged = QtCore.pyqtSignal(str)
    powerChanged = QtCore.pyqtSignal(int)
    statusChanged = QtCore.pyqtSignal(bool)

    def __init__(self, parent, settings: QtCore.QSettings, logger: Logger,
                 bands: dict, modes: dict):
        super().__init__(parent)

        # From QSOForm
        self.log = logging.getLogger('RigControl')
        self.log.addHandler(logger)
        self.log.setLevel(logger.loglevel)
        self.logger = logger
        self.log.debug('Initialising...')

        self.settings = settings

        self.bands = bands
        self.modes = modes

        self.rig_modes = {'USB': ('SSB', 'USB'),
                          'LSB': ('SSB', 'LSB'),
                          'CW': ('CW', ''),
                          'CWR': ('CW', ''),
                          'RTTY': ('RTTY', ''),
                          'RTTYR': ('RTTY', ''),
                          'AM': ('AM', ''),
                          'FM': ('FM', ''),
                          'FMN': ('FM', ''),
                          'WFM': ('FM', ''),
                          'PKTUSB': ('SSB', 'USB'),
                          'PKTLSB': ('SSB', 'LSB'),
                          }
        self.__last_mode__ = ''
        self.__last_band__ = ''
        self.__last_freq__ = 0.0
        self.__last_pwr_lvl__ = ''
        self.__last_pwr__ = 0

        self.__rig_ids__: dict = {}
        self.__rigs__: dict[str, list[str]] = {}
        self.__rigctld_path__: os.PathLike | None = None
        self.__rigctld__: subprocess.Popen | None = None
        self.__rig_caps__: list = []

        self.__rigctl_startupinfo__ = None
        if platform.system() == 'Windows':
            self.__rigctl_startupinfo__ = subprocess.STARTUPINFO()
            self.__rigctl_startupinfo__.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            try:
                self.init_hamlib(self.settings.value('cat/rigctldPath'))
            except (NoExecutableFoundException, RigctldExecutionException):
                pass
        else:
            try:
                self.init_hamlib('rigctld')
            except (NoExecutableFoundException, RigctldExecutionException):
                pass

        self.__refreshTimer__ = QtCore.QTimer(self)
        self.__refreshTimer__.timeout.connect(self.__refreshRigData__)
        self.__checkHamlibTimer__ = QtCore.QTimer(self)
        self.__checkHamlibTimer__.timeout.connect(self.__checkRigctld__)

    @staticmethod
    def __is_exe__(path: str) -> bool:
        return os.path.isfile(path) and os.access(path, os.X_OK)

    def __checkRigctld__(self):
        if not self.isActive():
            self.log.error('rigctld died unexpectedly')
            self.__rig_caps__ = []
            self.__checkHamlibTimer__.stop()
            self.statusChanged.emit(False)

    def isActive(self) -> bool:
        return bool(self.__rigctld__ and not self.__rigctld__.poll())

    def init_hamlib(self, rigctld_path: str):
        if rigctld_path:
            try:
                res = subprocess.run([rigctld_path, '-l'], capture_output=True)
                stdout = str(res.stdout, sys.getdefaultencoding()).replace('\r', '')
                if res.returncode != 0 or not stdout:
                    self.log.error(f'Error executing rigctld: {self.__get_errcode__(res.returncode)}')
                    raise RigctldExecutionException(rigctld_path)
                self.log.debug('Executed rigctld to list rigs')
            except (FileNotFoundError, OSError):
                raise NoExecutableFoundException(rigctld_path) from None

            first = True
            rig_pos = 0
            mfr_pos = 0
            model_pos = 0
            end_pos = 0
            self.__rigs__ = {}
            self.__rig_ids__ = {}
            for rig in stdout.split('\n'):
                if first:
                    first = False
                    rig_pos = rig.index('Rig #')
                    mfr_pos = rig.index('Mfg')
                    model_pos = rig.index('Model')
                    end_pos = rig.index('Version')
                    continue
                elif not rig.strip():  # Empty line
                    continue

                rig_id = rig[rig_pos:mfr_pos - 1].strip()
                mfr_name = rig[mfr_pos:model_pos - 1].strip()
                model_name = rig[model_pos:end_pos - 1].strip()

                self.__rig_ids__[f'{mfr_name}/{model_name}'] = rig_id
                if mfr_name in self.__rigs__:
                    self.__rigs__[mfr_name].append(model_name)
                else:
                    self.__rigs__[mfr_name] = [model_name]

            self.__rigctld_path__ = rigctld_path

    # From Settings
    def __collectRigCaps__(self, rig_id: str):
        try:
            res = subprocess.run([self.__rigctld_path__, f'--model={rig_id}', '-u'],
                                 capture_output=True,
                                 startupinfo=self.__rigctl_startupinfo__)
            stdout = str(res.stdout, sys.getdefaultencoding()).replace('\r', '')
            self.__rig_caps__ = []
            for ln in stdout.split('\n'):
                if ln.startswith('Can '):
                    cap, able = ln.split(':')
                    if able.strip() == 'Y':
                        self.__rig_caps__.append(cap[4:].lower())
        except (FileNotFoundError, OSError):
            self.log.warning(f'rigctld is not available or not executable: {self.__rigctld_path__}')
            raise NoExecutableFoundException(self.__rigctld_path__) from None

    @property
    def availableManufacturers(self) -> list:
        return list(self.__rigs__.keys())

    def availableRigs(self, mfr: str) -> list:
        return self.__rigs__.get(mfr, [])

    @property
    def capabilities(self) -> list:
        return self.__rig_caps__

    # noinspection PyUnresolvedReferences
    def ctrlRigctld(self, start: bool):
        if start:
            if not self.__rigctld_path__:
                self.statusChanged.emit(False)
                self.log.warning('rigctld is not available')
                raise RigctldNotConfiguredException()

            if not self.__rigctld__:
                rig_mfr = self.settings.value('cat/rigMfr', '')
                rig_model = self.settings.value('cat/rigModel', '')
                rig_if = self.settings.value('cat/interface', '')
                rig_speed = self.settings.value('cat/baud', '')
                if not rig_mfr or not rig_model or not rig_if or not rig_speed:
                    self.statusChanged.emit(False)
                    raise CATSettingsMissingException()

                rig_id = self.__rig_ids__[f'{rig_mfr}/{rig_model}']

                self.__collectRigCaps__(rig_id)

                self.__rigctld__ = subprocess.Popen([self.__rigctld_path__,
                                                     f'--model={rig_id}',
                                                     f'--rig-file={rig_if}',
                                                     f'--serial-speed={rig_speed}',
                                                     '--listen-addr=127.0.0.1'],
                                                    startupinfo=self.__rigctl_startupinfo__)

                if self.__rigctld__.poll():
                    self.statusChanged.emit(False)
                else:
                    self.log.info(
                        f'rigctld is running with pid #{self.__rigctld__.pid} and arguments {self.__rigctld__.args}')
                    self.__checkHamlibTimer__.start(1000)
                    self.statusChanged.emit(True)
                    # Give rigctld some time on slower machines
                    self.__refreshTimer__.singleShot(500, self.startRefresh)
        else:
            self.__checkHamlibTimer__.stop()
            self.__refreshTimer__.stop()
            if self.isActive():
                os.kill(self.__rigctld__.pid, 9)
                for _ in range(100):  # Wait for max 1 s for process to be killed
                    if self.__rigctld__.poll():
                        break
                    time.sleep(.001)
                self.log.info('Killed rigctld')
            self.__rigctld__ = None
            self.__rig_caps__ = []
            self.statusChanged.emit(False)

    # From QSOForm
    def rigctldChanged(self, state: bool):
        self.__last_mode__ = ''
        self.__last_band__ = ''
        self.__last_freq__ = 0.0
        self.__last_pwr_lvl__ = ''
        self.__last_pwr__ = 0

    @property
    def mode(self) -> str:
        return self.__last_mode__

    @property
    def band(self) -> str:
        return self.__last_band__

    @property
    def frequency(self) -> float:
        return self.__last_freq__

    @property
    def power(self) -> int:
        return self.__last_pwr__

    def startRefresh(self):
        self.__refreshTimer__.start(100)

    def setRigFreq(self, freq: int | float):
        self.sendToRig(f'set_freq {int(freq * 1000)}')

    def sendToRig(self, cmd: str):
        if not self.isActive():
            return

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect(('127.0.0.1', 4532))
                s.settimeout(1)
                try:
                    s.sendall(f'\\{cmd}\n'.encode())
                    res = s.recv(1024).decode('utf-8').strip()
                    if not res.startswith('RPRT 0'):
                        self.log.error(f'rigctld error "{cmd}": {self.__get_errcode__(res.split()[1])}')
                    else:
                        self.log.debug(f'rigctld "{cmd}" successful')
                except socket.timeout:
                    self.log.error('rigctld error: timeout in sendToRig')
        except ConnectionRefusedError:
            self.log.error('Could not connect to rigctld in sendToRig')

    @staticmethod
    def __get_errcode__(code: str | int) -> str:
        err = str(code)
        try:
            err = RIGCTL_ECODE.get(int(code), err)
        except ValueError:
            pass
        return str(err)

    # noinspection PyBroadException
    def __refreshRigData__(self):
        if self.isActive():
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.connect(('127.0.0.1', 4532))
                    s.settimeout(1)
                    try:
                        # Get frequency
                        s.sendall(b'\\get_freq\n')
                        freq_s = s.recv(1024).decode('utf-8').strip()
                        if freq_s.startswith('RPRT'):
                            self.log.error(f'rigctld error get_freq: {self.__get_errcode__(freq_s.split()[1])}')
                            return

                        try:
                            freq = float(freq_s) / 1000
                            if freq != self.__last_freq__:
                                for b in self.bands:
                                    if freq < self.bands[b][1]:
                                        if freq > self.bands[b][0]:
                                            if b != self.__last_band__:
                                                self.bandChanged.emit(b)
                                                self.log.info(f'CAT changed band to {b}')
                                                self.__last_band__ = b
                                                self.__last_mode__ = ''
                                        break
                                self.frequencyChanged.emit(freq)
                                self.__last_freq__ = freq
                        except Exception:
                            pass

                        # Get mode
                        s.sendall(b'\\get_mode\n')
                        mode_s = s.recv(1024).decode('utf-8').strip()
                        if mode_s.startswith('RPRT'):
                            self.log.error(f'rigctld error get_mode: {self.__get_errcode__(mode_s.split()[1])}')
                            return

                        try:
                            mode, passband = [v.strip() for v in mode_s.split('\n')]
                            if mode in self.rig_modes and mode != self.__last_mode__:
                                self.modeChanged.emit(self.rig_modes[mode][0])
                                self.log.info(f'CAT changed mode to {self.rig_modes[mode][0]}')
                                if self.rig_modes[mode][1]:
                                    self.submodeChanged.emit(self.rig_modes[mode][1])
                                self.__last_mode__ = mode
                        except Exception:
                            pass

                        # Get power
                        if 'get level' in self.__rig_caps__ and 'get power2mw' in self.__rig_caps__:
                            # Get power level
                            s.sendall(b'\\get_level RFPOWER\n')
                            pwrlvl_s = s.recv(1024).decode('utf-8').strip()
                            if pwrlvl_s.startswith('RPRT'):
                                self.log.error(f'rigctld error get_level: {self.__get_errcode__(pwrlvl_s.split()[1])}')
                                return

                            if pwrlvl_s != self.__last_pwr_lvl__:
                                self.__last_pwr_lvl__ = pwrlvl_s
                                # Convert level to W
                                s.sendall(f'\\power2mW {pwrlvl_s} {freq_s} {mode}\n'.encode())
                                pwr_s = s.recv(1024).decode('utf-8').strip()
                                if pwr_s.startswith('RPRT'):
                                    self.log.error(f'rigctld error power2mW: {self.__get_errcode__(pwr_s.split()[1])}')
                                    return

                                try:
                                    self.__last_pwr__ = int(int(pwr_s) / 1000 + .9)
                                    self.powerChanged.emit(self.__last_pwr__)
                                except Exception:
                                    pass
                    except socket.timeout:
                        self.log.error('rigctld error: timeout in refreshRigData')
                        self.ctrlRigctld(False)
            except ConnectionRefusedError:
                self.log.error('Could not connect to rigctld in refreshRigData')
                self.ctrlRigctld(False)
