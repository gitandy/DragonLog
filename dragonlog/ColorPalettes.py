from PyQt6 import QtGui

PaletteDefault = QtGui.QPalette()
PaletteDefault.setColor(QtGui.QPalette.ColorGroup.Active, QtGui.QPalette.ColorRole.Base,
                        QtGui.QColor(255, 255, 255))

PaletteOk = QtGui.QPalette()
PaletteOk.setColor(QtGui.QPalette.ColorGroup.Active, QtGui.QPalette.ColorRole.Base,
                   QtGui.QColor(204, 255, 204))

PaletteEmpty = QtGui.QPalette()
PaletteEmpty.setColor(QtGui.QPalette.ColorGroup.Active, QtGui.QPalette.ColorRole.Base,
                      QtGui.QColor(255, 255, 204))

PaletteFaulty = QtGui.QPalette()
PaletteFaulty.setColor(QtGui.QPalette.ColorGroup.Active, QtGui.QPalette.ColorRole.Base,
                       QtGui.QColor(255, 204, 204))

PaletteWorked = QtGui.QPalette()
PaletteWorked.setColor(QtGui.QPalette.ColorGroup.Active, QtGui.QPalette.ColorRole.Base,
                       QtGui.QColor(204, 204, 255))
