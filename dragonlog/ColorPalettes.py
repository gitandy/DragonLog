from PyQt6 import QtGui, QtWidgets

PaletteDefault = QtWidgets.QApplication.palette('QLineEdit')

PaletteOk = QtGui.QPalette()
PaletteOk.setColor(QtGui.QPalette.ColorGroup.Active, QtGui.QPalette.ColorRole.Base,
                   QtGui.QColor(0, 255, 0, 63))

PaletteEmpty = QtGui.QPalette()
PaletteEmpty.setColor(QtGui.QPalette.ColorGroup.Active, QtGui.QPalette.ColorRole.Base,
                      QtGui.QColor(255, 255, 0, 63))

PaletteFaulty = QtGui.QPalette()
PaletteFaulty.setColor(QtGui.QPalette.ColorGroup.Active, QtGui.QPalette.ColorRole.Base,
                       QtGui.QColor(255, 127, 0, 63))

PaletteRequired = QtGui.QPalette()
PaletteRequired.setColor(QtGui.QPalette.ColorGroup.Active, QtGui.QPalette.ColorRole.Base,
                         QtGui.QColor(255, 0, 0, 63))

PaletteWorked = QtGui.QPalette()
PaletteWorked.setColor(QtGui.QPalette.ColorGroup.Active, QtGui.QPalette.ColorRole.Base,
                       QtGui.QColor(0, 0, 255, 63))
