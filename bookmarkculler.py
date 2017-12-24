#!/usr/bin/env python

# pip install pyqt5

# This version uses the "new" chromium stuff, not the old webkit stuff


import sys
import json
import argparse
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtWebEngineWidgets import *
#from PyQt5.QtWebKitWidgets import *
from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow, QMenuBar

autoCullList = [
        "http://www.mozilla.com",
]


class App(QMainWindow):

    def __init__(self):
        super().__init__()

        self.bookmarkJson = None
        self.nodeDb = {}
        self.nodeList = []
        self.nodeIndex = 0

        self.title = 'PyQt App'
        self.left = 10
        self.top = 10
        self.width = 1024
        self.height = 800

        self.initUI()

        argv = QCoreApplication.arguments()
        if len(argv) > 1:
            self.openBookmarksFile(argv[1])

    def initUI(self):
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)
        self.move(50, 50)

        openAction = QAction("&Open File", self)
        openAction.setShortcut("Ctrl+O")
        openAction.setStatusTip('Open Bookmarks File')
        openAction.triggered.connect(self.onFileOpen)

        saveAction = QAction("&Save File", self)
        saveAction.setShortcut("Ctrl+S")
        saveAction.setStatusTip('Save Culled Bookmarks File')
        saveAction.triggered.connect(self.saveBookmarksFile)

        mainMenu = self.menuBar()
        fileMenu = mainMenu.addMenu('&File')
        fileMenu.addAction(openAction)
        fileMenu.addAction(saveAction)

        backButton = QPushButton('Back', self)
        backButton.setShortcut("Ctrl+B")
        backButton.setToolTip('Back')
        backButton.clicked.connect(self.onBack)

        approveButton = QPushButton('Approve', self)
        approveButton.setShortcut("Ctrl+A")
        approveButton.setToolTip('Approve URL')
        approveButton.clicked.connect(self.onApprove)

        deleteButton = QPushButton('Delete', self)
        deleteButton.setShortcut("Ctrl+D")
        deleteButton.setToolTip('Delete URL')
        deleteButton.clicked.connect(self.onDelete)

        self.counterLabel = QLabel()

        self.urlLabel = QLabel()
        self.urlLabel.setText("No bookmarks file opened.")

        # Create a horizontal box layout and add a stretch factor and both buttons.
        # The stretch adds a stretchable space before the two buttons. This will
        # push them to the right of the window.
        hbox = QHBoxLayout()
        hbox.addSpacing(5)
        hbox.addWidget(self.counterLabel)
        hbox.addSpacing(5)
        hbox.addWidget(self.urlLabel)
        hbox.addStretch(1)
        hbox.addWidget(backButton)
        hbox.addWidget(approveButton)
        hbox.addWidget(deleteButton)

        self.webView = QWebEngineView()
        self.webView.load(QUrl("http://www.google.com"))
        self.webView.show()

        gridLayout = QGridLayout()
        gridLayout.setContentsMargins(0, 5, 5, 0) # l,t,r,b
        gridLayout.addLayout(hbox, 0, 0)
        gridLayout.addWidget(self.webView, 1, 0)

        #self.addLayout(gridLayout, 0, 0)
        # The QMainWindow is a special case. You set the contents of this widget
        # by putting the layout in a new QWidget and then setting that as the
        # central widget.
        widget = QWidget()
        widget.setLayout(gridLayout)
        self.setCentralWidget(widget)

        self.show()

    @pyqtSlot()
    def onBack(self):
        self.sendNextBookmarkToWebView(False)

    def onApprove(self):
        (bm, deleted) = self.nodeList[self.nodeIndex]
        if deleted:
            self.nodeList[self.nodeIndex] = (bm, False)
            self.nodeDb[bm['guid']] = (bm, False)
        self.sendNextBookmarkToWebView(True)

    def onDelete(self):
        (bm, deleted) = self.nodeList[self.nodeIndex]
        if not deleted:
            self.nodeList[self.nodeIndex] = (bm, True)
            self.nodeDb[bm['guid']] = (bm, True)
        self.sendNextBookmarkToWebView()

    def onFileOpen(self):
        filenames = QFileDialog.getOpenFileName(self, 'Open File', filter="JSON Files (*.json)")
        if len(filenames) > 0 and len(filenames[0]) > 0:
            self.openBookmarksFile(filenames[0])

    def openBookmarksFile(self, filename):
        self.bookmarkJson = None
        self.nodeDb = {}
        self.nodeList = []
        self.nodeIndex = 0

        f = open(filename, 'r')
        self.bookmarkJson = json.load(f)
        f.close()

        self.urlLabel.setText("Loading bookmarks...")

        self.loadBookmarkChildren(self.bookmarkJson)
        self.nodeList = list(self.nodeDb.values())
        self.nodeIndex = 0

        self.counterLabel.setText(str(len(self.nodeDb)) + " bookmarks")
        print("%d bookmarks" % len(self.nodeDb))

        self.sendNextBookmarkToWebView()

    def sendNextBookmarkToWebView(self, forward = True):
        doReload = False
        if forward:
            if self.nodeIndex < len(self.nodeList):
                self.nodeIndex += 1
                doReload = True
        else:
            if self.nodeIndex > 0:
                self.nodeIndex -= 1
                doReload = True

        if not doReload:
            return

        (bm, deleted) = self.nodeList[self.nodeIndex]
        print(bm['uri'])
        self.webView.load(QUrl(bm['uri']))
        self.webView.show()
        if deleted:
            self.urlLabel.setText(bm['uri'] + " (deleted)")
        else:
            self.urlLabel.setText(bm['uri'])
        self.counterLabel.setText(str(self.nodeIndex) + " of " + str(len(self.nodeDb)))

    def saveBookmarksFile(self):

        filenames = QFileDialog.getSaveFileName(self, 'Save File', filter="JSON Files (*.json)")
        if len(filenames) == 0 or len(filenames[0]) == 0:
            return

        filename = filenames[0]

        self.cullBookmarkChildren(self.bookmarkJson)

        f = open(filename, "w")
        json.dump(self.bookmarkJson, f)
        f.close()

        self.counterLabel.setText(" Saved as " + filename)

    def loadBookmarkChildren(self, bmNode):
        '''Iterate over the children and copy them into a dictionary
           keyed by their guid. Recurse down if necessary.'''

        if "children" not in bmNode:
            return

        global autoCullList

        bmList = bmNode['children']

        # a URL bookmark has typecode 1
        # subfolder has typecode 2 and a "children" array
        # separator has typecode 3
        for bm in bmList:
            if bm['typeCode'] == 1:
                print(bm['uri'])
                if bm['uri'].startswith('http'):
                    self.nodeDb[bm['guid']] = (bm, False)
                    for prefix in autoCullList:
                        if bm['uri'].startswith(prefix):
                            self.nodeDb[bm['guid']] = (bm, True)
            elif bm['typeCode'] == 2:
                self.loadBookmarkChildren(bm)

    def cullBookmarkChildren(self, bmNode):
        if "children" not in bmNode:
            return

        bmList = bmNode['children']

        newList = []

        # a URL bookmark has typecode 1
        # subfolder has typecode 2 and a "children" array
        # separator has typecode 3

        for bm in bmList:
            if bm['typeCode'] == 1:
                try:
                    (bm, deleted) = self.nodeDb[bm['guid']]
                    print(deleted)
                    if (not deleted):
                        print("Saving " + bm['uri'])
                        newList.append(bm)
                    else:
                        print("Deleting " + bm['uri'])
                except KeyError:
                    # Key is not present
                    pass
            elif bm['typeCode'] == 2:
                self.cullBookmarkChildren(bm)
                print("Recursing to node " + bm['title'])
                newList.append(bm)
            else:
                # separator
                print("Separator")
                newList.append(bm)

        bmNode['children'] = newList

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = App()
    sys.exit(app.exec_())
