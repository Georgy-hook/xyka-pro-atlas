"""Capture FreeCAD's actual reopened model tree and viewport (not a drawn tree)."""

import argparse
import os
from pathlib import Path
import sys
import tempfile
import traceback

import FreeCAD as App
import FreeCADGui as Gui


def capture(source, output):
    Gui.showMainWindow()
    from PySide import QtCore, QtGui, QtWidgets
    window = Gui.getMainWindow()
    screen = window.screen().availableGeometry()
    window.resize(min(1210, screen.width()), min(810, screen.height()))
    document = App.openDocument(str(source.resolve()))
    Gui.activateWorkbench('PartWorkbench')
    from native_view import present
    present()
    trees = [tree for tree in window.findChildren(QtWidgets.QTreeWidget)
             if tree.isVisible() and tree.topLevelItemCount()]
    if not trees:
        raise RuntimeError('FreeCAD tree view not found')
    tree = max(trees, key=lambda widget: widget.height())
    parent = tree.parentWidget()
    while parent and not isinstance(parent, QtWidgets.QDockWidget):
        parent = parent.parentWidget()
    if parent is not None:
        window.resizeDocks([parent], [415], QtCore.Qt.Horizontal)

    def expand(node, depth=0):
        while depth <= 3 and node:
            text = node.text(0)
            show = (depth == 0 or text.startswith('A  •') or 'GYS005-S-088-A4.3 · сторона' in text)
            node.setExpanded(show)
            if show:
                for i in range(node.childCount()):
                    expand(node.child(i), depth+1)
            break

    for i in range(tree.topLevelItemCount()):
        expand(tree.topLevelItem(i))
    tree.scrollToTop()
    present()
    for _ in range(4):
        QtWidgets.QApplication.processEvents()
        Gui.updateGui()
    image = window.grab()
    # On Cocoa QWidget.grab() can omit the separately composited OpenGL
    # surface. Read the actual Coin framebuffer for that exact widget rectangle.
    mdi = window.findChild(QtWidgets.QMdiArea)
    if mdi and mdi.activeSubWindow():
        active = mdi.activeSubWindow().widget()
        gl = next((w for w in active.findChildren(QtWidgets.QWidget)
                   if w.metaObject().className() == 'QOpenGLWidget' and w.isVisible()), None)
        if gl:
            origin = gl.mapTo(window, QtCore.QPoint(0, 0))
            scale = image.devicePixelRatio()
            target = QtCore.QRect(origin, gl.size())
            with tempfile.TemporaryDirectory(prefix='xkah-frame-') as temp:
                frame = str(Path(temp) / 'viewport.png')
                Gui.activeDocument().activeView().saveImage(frame, round(scale * gl.width()),
                                                           round(scale * gl.height()), 'Current')
                geometry = QtGui.QImage(frame)
                if not geometry.isNull():
                    painter = QtGui.QPainter(image)
                    painter.drawImage(target, geometry)
                    painter.end()
    if image.isNull() or not image.save(str(output.resolve())):
        raise RuntimeError('Could not save the FreeCAD window')
    print(f'Captured FreeCAD: {image.width()} × {image.height()} px, {document.Label}', flush=True)
    App.closeDocument(document.Name)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    args.output.parent.mkdir(exist_ok=True, parents=True)
    try:
        capture(args.source, args.output)
    except BaseException:
        traceback.print_exc()
        sys.stderr.flush()
        os._exit(1)
    os._exit(0)
