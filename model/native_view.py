"""Present the actual 3D document and wait for Coin camera clipping to settle."""

import FreeCADGui as Gui
from PySide import QtCore, QtWidgets


def settled(milliseconds):
    loop = QtCore.QEventLoop()
    QtCore.QTimer.singleShot(milliseconds, loop.quit)
    loop.exec()


def present():
    Gui.updateGui()
    window = Gui.getMainWindow()
    for area in window.findChildren(QtWidgets.QMdiArea):
        for sub in area.subWindowList():
            if sub.widget() and 'View3D' in sub.widget().metaObject().className():
                area.setActiveSubWindow(sub)
                sub.showMaximized()
                break
    settled(220)
    view = Gui.activeDocument().activeView()
    view.setAnimationEnabled(False)
    view.viewAxonometric()
    settled(480)
    view.fitAll()
    settled(500)
    view.redraw()
    Gui.updateGui()
