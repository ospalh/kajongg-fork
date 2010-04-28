# -*- coding: utf-8 -*-

"""
Copyright (C) 2009,2010 Wolfgang Rohdewald <wolfgang@rohdewald.de>

kajongg is free software you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""

import socket, subprocess, time, datetime, os

from twisted.spread import pb
from twisted.cred import credentials
from twisted.internet.defer import Deferred
from twisted.internet.address import UNIXAddress
from PyQt4.QtCore import SIGNAL, SLOT, Qt, QTimer
from PyQt4.QtGui import QDialog, QDialogButtonBox, QVBoxLayout, QGridLayout, \
    QLabel, QComboBox, QLineEdit, QPushButton, \
    QProgressBar, QRadioButton, QSpacerItem, QSizePolicy

from PyKDE4.kdecore import KUser
from PyKDE4.kdeui import KDialogButtonBox
from PyKDE4.kdeui import KMessageBox

from util import m18n, m18nc, logWarning, logException, syslogMessage, socketName, english
from util import SERVERMARK
from message import Message
import common
from common import InternalParameters
from game import Players
from query import Query
from board import Board
from client import Client
from statesaver import StateSaver

from guiutil import ListComboBox
from scoringengine import Ruleset

class LoginDialog(QDialog):
    """login dialog for server"""
    def __init__(self):
        QDialog.__init__(self, None)
        self.setWindowTitle(m18n('Login') + ' - Kajongg')
        self.buttonBox = KDialogButtonBox(self)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok)
        self.connect(self.buttonBox, SIGNAL("accepted()"), self, SLOT("accept()"))
        self.connect(self.buttonBox, SIGNAL("rejected()"), self, SLOT("reject()"))
        vbox = QVBoxLayout(self)
        grid = QGridLayout()
        lblServer = QLabel(m18n('Game server:'))
        grid.addWidget(lblServer, 0, 0)
        self.cbServer = QComboBox()
        self.cbServer.setEditable(True)
        grid.addWidget(self.cbServer, 0, 1)
        lblServer.setBuddy(self.cbServer)
        lblUsername = QLabel(m18n('Username:'))
        grid.addWidget(lblUsername, 1, 0)
        self.cbUser = QComboBox()
        self.cbUser.setEditable(True)
        self.cbUser.setMinimumWidth(350) # is this good for all platforms?
        lblUsername.setBuddy(self.cbUser)
        grid.addWidget(self.cbUser, 1, 1)
        self.lblPassword = QLabel(m18n('Password:'))
        grid.addWidget(self.lblPassword, 2, 0)
        self.edPassword = QLineEdit()
        self.edPassword.setEchoMode(QLineEdit.PasswordEchoOnEdit)
        grid.addWidget(self.edPassword, 2, 1)
        self.lblPassword.setBuddy(self.edPassword)
        self.lblRuleset = QLabel(m18nc('kajongg', 'Ruleset:'))
        grid.addWidget(self.lblRuleset, 3, 0)
        self.cbRuleset = ListComboBox()
        grid.addWidget(self.cbRuleset, 3, 1)
        self.lblRuleset.setBuddy(self.cbRuleset)
        vbox.addLayout(grid)
        vbox.addWidget(self.buttonBox)
        pol = QSizePolicy()
        pol.setHorizontalPolicy(QSizePolicy.Expanding)
        self.cbUser.setSizePolicy(pol)

        localName = m18nc('kajongg name for local game server', Query.localServerName)
        if InternalParameters.autoPlay:
            self.cbServer.addItem(localName)
        self.servers = Query('select url, lastname from server order by lasttime desc').records
        for server in self.servers:
            if server[0] == Query.localServerName:
                self.cbServer.addItem(localName)
            else:
                self.cbServer.addItem(server[0])
        if self.cbServer.findText(localName) < 0:
            self.cbServer.addItem(localName)
        self.connect(self.cbServer, SIGNAL('editTextChanged(QString)'), self.serverChanged)
        self.connect(self.cbUser, SIGNAL('editTextChanged(QString)'), self.userChanged)
        self.serverChanged()
        self.state = StateSaver(self)
        if InternalParameters.autoPlay:
            self.timer = QTimer()
            self.connect(self.timer, SIGNAL('timeout()'), self.accept)
            self.timer.start(1)
            self.emit (SIGNAL("accepted()"))

    def accept(self):
        """user entered OK"""
        if self.host == Query.localServerName:
            # client and server use the same database, and we
            # have no security concerns
            Players.createIfUnknown(self.host, str(self.cbUser.currentText()))
        QDialog.accept(self)

    def serverChanged(self, dummyText=None):
        """the user selected a different server"""
        Players.load()
        self.cbUser.clear()
        self.cbUser.addItems(list(x[1] for x in Players.allNames.values() if x[0] == self.host))
        if not self.cbUser.count():
            self.cbUser.addItem(KUser(os.geteuid()).fullName())
        hostName = self.host
        userNames = [x[1] for x in self.servers if x[0] == hostName]
        if userNames:
            userIdx = self.cbUser.findText(userNames[0])
            if userIdx >= 0:
                self.cbUser.setCurrentIndex(userIdx)
        showPW = self.host != Query.localServerName
        self.lblPassword.setVisible(showPW)
        self.edPassword.setVisible(showPW)
        self.lblRuleset.setVisible(not showPW)
        self.cbRuleset.setVisible(not showPW)
        if not showPW:
            self.cbRuleset.clear()
            self.cbRuleset.items = Ruleset.selectableRulesets(self.host)

    def userChanged(self, text):
        """the username has been changed, lookup password"""
        if text == '':
            self.edPassword.clear()
            return
        passw = Query("select password from player where host=? and name=?",
            list([self.host, str(text)])).records
        if passw:
            self.edPassword.setText(passw[0][0])
        else:
            self.edPassword.clear()

    @apply
    def host():
        """abstracts the host of the dialog"""
        def fget(self):
            text = english(str(self.cbServer.currentText()))
            if ':' not in text:
                return text
            hostargs = text.rpartition(':')
            return ''.join(hostargs[0])
        return property(**locals())

    @apply
    def port():
        """abstracts the port of the dialog"""
        def fget(self):
            text = str(self.cbServer.currentText())
            if ':' not in text:
                return common.PREF.serverPort
            hostargs = str(self.cbServer.currentText()).rpartition(':')
            try:
                return int(hostargs[2])
            except Exception:
                return common.PREF.serverPort
        return property(**locals())

    @apply
    def username():
        """abstracts the username of the dialog"""
        def fget(self):
            return str(self.cbUser.currentText())
        return property(**locals())

    @apply
    def password():
        """abstracts the password of the dialog"""
        def fget(self):
            return str(self.edPassword.text())
        return property(**locals())

class AddUserDialog(QDialog):
    """add a user account on a server: This dialog asks for the needed attributes"""
    def __init__(self):
        QDialog.__init__(self, None)
        self.setWindowTitle(m18n('Create User Account') + ' - Kajongg')
        self.buttonBox = KDialogButtonBox(self)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok)
        self.connect(self.buttonBox, SIGNAL("accepted()"), self, SLOT("accept()"))
        self.connect(self.buttonBox, SIGNAL("rejected()"), self, SLOT("reject()"))
        vbox = QVBoxLayout(self)
        grid = QGridLayout()
        lblServer = QLabel(m18n('Game server:'))
        grid.addWidget(lblServer, 0, 0)
        self.cbServer = QComboBox()
        self.cbServer.setEditable(True)
        grid.addWidget(self.cbServer, 0, 1)
        lblServer.setBuddy(self.cbServer)
        lblUsername = QLabel(m18n('Username:'))
        grid.addWidget(lblUsername, 1, 0)
        self.edUser = QLineEdit()
        lblUsername.setBuddy(self.edUser)
        grid.addWidget(self.edUser, 1, 1)
        self.lblPassword = QLabel(m18n('Password:'))
        grid.addWidget(self.lblPassword, 2, 0)
        self.edPassword = QLineEdit()
        self.edPassword.setEchoMode(QLineEdit.PasswordEchoOnEdit)
        grid.addWidget(self.edPassword, 2, 1)
        self.lblPassword.setBuddy(self.edPassword)
        self.lblPassword2 = QLabel(m18n('Repeat password:'))
        grid.addWidget(self.lblPassword2, 3, 0)
        self.edPassword2 = QLineEdit()
        self.edPassword2.setEchoMode(QLineEdit.PasswordEchoOnEdit)
        grid.addWidget(self.edPassword2, 3,  1)
        self.lblPassword2.setBuddy(self.edPassword2)
        vbox.addLayout(grid)
        vbox.addWidget(self.buttonBox)
        pol = QSizePolicy()
        pol.setHorizontalPolicy(QSizePolicy.Expanding)
        self.edUser.setSizePolicy(pol)

        self.servers = Query('select url, lastname from server order by lasttime desc').records
        for server in self.servers:
            if server[0] != Query.localServerName:
                self.cbServer.addItem(server[0])
        self.connect(self.cbServer, SIGNAL('editTextChanged(QString)'), self.serverChanged)
        self.connect(self.edUser, SIGNAL('textChanged(QString)'), self.userChanged)
        self.connect(self.edPassword, SIGNAL('textChanged(QString)'), self.passwordChanged)
        self.connect(self.edPassword2, SIGNAL('textChanged(QString)'), self.passwordChanged)
        self.serverChanged()
        self.state = StateSaver(self)
        self.passwordChanged()
        self.edPassword2.setFocus()

    def serverChanged(self, dummyText=None):
        """the user selected a different server"""
        self.edUser.clear()

    def userChanged(self, dummyText):
        """the user name has been edited"""
        self.edPassword.clear()
        self.edPassword2.clear()
        self.validate()

    def passwordChanged(self, dummyText=None):
        """password changed"""
        self.validate()

    def validate(self):
        """does the dialog hold valid data?"""
        equal = self.edPassword.size() and self.edPassword.text() == self.edPassword2.text()
        self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(equal and self.edUser.text().size())

    @apply
    def host():
        """abstracts the host of the dialog"""
        def fget(self):
            text = english(str(self.cbServer.currentText()))
            if ':' not in text:
                return text
            hostargs = text.rpartition(':')
            return ''.join(hostargs[0])
        return property(**locals())

    @apply
    def port():
        """abstracts the port of the dialog"""
        def fget(self):
            text = str(self.cbServer.currentText())
            if ':' not in text:
                return common.PREF.serverPort
            hostargs = str(self.cbServer.currentText()).rpartition(':')
            try:
                return int(hostargs[2])
            except Exception:
                return common.PREF.serverPort
        return property(**locals())

    @apply
    def username():
        """abstracts the username of the dialog"""
        def fget(self):
            return str(self.edUser.text())
        def fset(self, username):
            self.edUser.setText(username)
        return property(**locals())

    @apply
    def password():
        """abstracts the password of the dialog"""
        def fget(self):
            return str(self.edPassword.text())
        def fset(self, password):
            self.edPassword.setText(password)
        return property(**locals())

class SelectChow(QDialog):
    """asks which of the possible chows is wanted"""
    def __init__(self, chows):
        QDialog.__init__(self)
        self.chows = chows
        self.selectedChow = None
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(m18n('Which chow do you want to expose?')))
        self.buttons = []
        for chow in chows:
            button = QRadioButton('-'.join([chow[0][1], chow[1][1], chow[2][1]]), self)
            self.buttons.append(button)
            layout.addWidget(button)
            self.connect(button, SIGNAL('toggled(bool)'), self.toggled)

    def toggled(self, dummyChecked):
        """a radiobutton has been toggled"""
        button = self.sender()
        if button.isChecked():
            self.selectedChow = self.chows[self.buttons.index(button)]
            self.accept()

    def closeEvent(self, event):
        """allow close only if a chow has been selected"""
        if self.selectedChow:
            event.accept()
        else:
            event.ignore()

    def keyPressEvent(self, event):
        """catch and ignore the Escape key"""
        if event.key() == Qt.Key_Escape:
            event.ignore()
        else:
            QDialog.keyPressEvent(self, event)

class DlgButton(QPushButton):
    """special button for ClientDialog"""
    def __init__(self, key, parent):
        QPushButton.__init__(self, parent)
        self.key = key
        self.parent = parent

    def keyPressEvent(self, event):
        """forward horizintal arrows to the hand board"""
        key = Board.mapChar2Arrow(event)
        if key in [Qt.Key_Left, Qt.Key_Right]:
            game = self.parent.client.game
            if game.activePlayer == game.myself:
                game.myself.handBoard.keyPressEvent(event)
                self.setFocus()
                return
        QPushButton.keyPressEvent(self, event)

class ClientDialog(QDialog):
    """a simple popup dialog for asking the player what he wants to do"""
    def __init__(self, client, parent=None):
        QDialog.__init__(self, parent)
        self.setWindowTitle(m18n('Choose') + ' - Kajongg')
        self.setObjectName('ClientDialog')
        self.client = client
        self.relativePos = None
        self.layout = QGridLayout(self)
        self.progressBar = QProgressBar()
        self.timer = QTimer()
        self.connect(self.timer, SIGNAL('timeout()'), self.timeout)
        self.deferred = None
        self.buttons = []
        self.setWindowFlags(Qt.SubWindow | Qt.WindowStaysOnTopHint)
        self.setModal(False)

    def keyPressEvent(self, event):
        """ESC selects default answer"""
        if event.key() in [Qt.Key_Escape, Qt.Key_Space]:
            self.selectButton()
            event.accept()
        else:
            for btn in self.buttons:
                if str(event.text()).upper() == btn.key:
                    self.selectButton(btn)
                    event.accept()
                    return
            QDialog.keyPressEvent(self, event)

    def __declareButton(self, message):
        """define a button"""
        btn = DlgButton(message.shortcut, self)
        btn.setObjectName(message.name)
        btn.setText(message.buttonCaption())
        btn.setAutoDefault(True)
        self.connect(btn, SIGNAL('clicked(bool)'), self.selectedAnswer)
        self.buttons.append(btn)

# TODO: do we need dummyMove?
    def ask(self, dummyMove, answers, deferred):
        """make buttons specified by answers visible. The first answer is default.
        The default button only appears with blue border when this dialog has
        focus but we always want it to be recognizable. Hence setBackgroundRole."""
        self.deferred = deferred
        for answer in answers:
            self.__declareButton(answer)
        self.show()
        self.buttons[0].setFocus()
        myTurn = self.client.game.activePlayer == self.client.game.myself
        if InternalParameters.autoPlay:
            self.selectButton()
            return

        self.progressBar.setVisible(not myTurn)
        if myTurn:
            hBoard = self.client.game.myself.handBoard
            hBoard.showFocusRect(hBoard.focusTile)
        else:
            msecs = 50
            self.progressBar.setMinimum(0)
            self.progressBar.setMaximum(self.client.game.ruleset.claimTimeout * 1000 / msecs)
            self.progressBar.reset()
            self.timer.start(msecs)

    def placeInField(self):
        """place the dialog at bottom or to the right depending on space."""
        field = self.client.game.field
        cwi = field.centralWidget()
        view = field.centralView
        geometry = self.geometry()
        btnHeight = self.buttons[0].height()
        vertical = view.width() > view.height() * 1.2
        if vertical:
            h = (len(self.buttons) + 1) * btnHeight * 1.2
            w = (cwi.width() - cwi.height() ) / 2
            geometry.setX(cwi.width() - w)
            geometry.setY(cwi.height()/2  - h/2)
        else:
            handBoard = self.client.game.myself.handBoard
            if not handBoard:
                # we are in the progress of logging out
                return
            hbLeftTop = view.mapFromScene(handBoard.mapToScene(handBoard.rect().topLeft()))
            hbRightBottom = view.mapFromScene(handBoard.mapToScene(handBoard.rect().bottomRight()))
            w = hbRightBottom.x() - hbLeftTop.x()
            h = btnHeight
            geometry.setY(cwi.height()  - h)
            geometry.setX(hbLeftTop.x())
        spacer1 = QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Expanding)
        spacer2 = QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.layout.addItem(spacer1, 0, 0)
        for idx, btn in enumerate(self.buttons + [self.progressBar]):
            self.layout.addWidget(btn, idx+1 if vertical else 0, idx+1 if not vertical else 0)
        idx = len(self.buttons) + 2
        self.layout.addItem(spacer2, idx if vertical else 0, idx if not vertical else 0)

        geometry.setWidth(w)
        geometry.setHeight(h)
        self.setGeometry(geometry)

    def showEvent(self, dummyEvent):
        """try to place the dialog such that it does not cover interesting information"""
        self.placeInField()

    def timeout(self):
        """the progressboard wants an update"""
        pBar = self.progressBar
        pBar.setValue(pBar.value()+1)
        pBar.setVisible(True)
        if pBar.value() == pBar.maximum():
            # timeout: we always return the original default answer, not the one with focus
            self.selectButton()
            pBar.setVisible(False)

    def selectButton(self, button=None):
        """select default answer"""
        if self.isVisible():
            self.timer.stop()
            if button is None:
                button = self.buttons[0]
            answer = Message.defined[str(button.objectName())]
            self.deferred.callback(answer)
        self.hide()

    def selectedAnswer(self, dummyChecked):
        """the user clicked one of the buttons"""
        self.selectButton(self.sender())

class ReadyHandQuestion(QDialog):
    """ask user if he is ready for the hand"""
    def __init__(self, deferred, parent=None):
        QDialog.__init__(self, parent)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.deferred = deferred
        layout = QVBoxLayout(self)
        buttonBox = QDialogButtonBox()
        layout.addWidget(buttonBox)
        self.okButton = buttonBox.addButton(m18n("&Ready for next hand?"),
          QDialogButtonBox.AcceptRole)
        self.connect(self.okButton, SIGNAL('clicked(bool)'), self.accept)
        self.setWindowTitle('Kajongg')
        self.connect(buttonBox, SIGNAL("accepted()"), self, SLOT("accept()"))
        self.connect(buttonBox, SIGNAL("rejected()"), self, SLOT("accept()"))

    def accept(self):
        """player is ready"""
        if self.isVisible():
            self.deferred.callback(None)
            self.hide()

    def keyPressEvent(self, event):
        """catch and ignore the Escape key"""
        if event.key() == Qt.Key_Escape:
            event.ignore()
        else:
            QDialog.keyPressEvent(self, event)


class HumanClient(Client):
    """a human client"""
    serverProcess = None
    socketServerProcess = None

    def __init__(self, tableList, callback):
        Client.__init__(self)
        self.tableList = tableList
        self.callback = callback
        self.connector = None
        self.table = None
        self.discardBoard = tableList.field.discardBoard
        self.readyHandQuestion = None
        self.loginDialog = LoginDialog()
        if not self.loginDialog.exec_():
            raise Exception(m18n('Login aborted'))
        self.useSocket = self.loginDialog.host == Query.localServerName
        if self.useSocket or self.loginDialog.host == 'localhost':
            if not self.serverListening():
                # give the server up to 5 seconds time to start
                HumanClient.startLocalServer(self.useSocket)
                for loop in range(5):
                    if self.serverListening():
                        break
                    time.sleep(1)
        self.username = self.loginDialog.username
        self.ruleset = self.loginDialog.cbRuleset.current
        self.login()

    def isRobotClient(self):
        """avoid using isinstance, it would import too much for kajonggserver"""
        return False

    def isHumanClient(self):
        """avoid using isinstance, it would import too much for kajonggserver"""
        return True

    def isServerClient(self):
        """avoid using isinstance, it would import too much for kajonggserver"""
        return False

    def hasLocalServer(self):
        """True if we are talking to a Local Game Server"""
        return self.useSocket

    def serverListening(self):
        """is somebody listening on that port?"""
        if self.useSocket:
            sock = socket.socket(socket.AF_UNIX,  socket.SOCK_STREAM)
            sock.settimeout(1)
            try:
                sock.connect(socketName())
            except socket.error:
                if os.path.exists(socketName()):
                    syslogMessage(m18n('removed stale socket <filename>%1</filename>', socketName()))
                    os.remove(socketName())
                return False
            else:
                return True
        else:
            sock = socket.socket(socket.AF_INET,  socket.SOCK_STREAM)
            sock.settimeout(1)
            try:
                sock.connect((self.loginDialog.host, self.loginDialog.port))
            except socket.error:
                return False
            else:
                return True

    @staticmethod
    def startLocalServer(useSocket):
        """start a local server"""
        try:
            args = ' '.join([
                '--seed=%d' % InternalParameters.seed if InternalParameters.seed else '',
                '--showtraffic'  if InternalParameters.showTraffic else '',
                '--socket=%s' % socketName() if useSocket else ''])
            process = subprocess.Popen(['kajonggserver', args])
            syslogMessage(m18n('started the local kajongg server: pid=<numid>%1</numid> %2',
                process.pid, args))
            if useSocket:
                HumanClient.socketServerProcess = process
            else:
                HumanClient.serverProcess = process
        except Exception, exc:
            logException(exc)

    @staticmethod
    def stopLocalServers():
        """stop the local servers we started"""
        for process in [HumanClient.serverProcess, HumanClient.socketServerProcess]:
            if process:
                syslogMessage(m18n('stopped the local kajongg server: pid=<numid>%1</numid>',
                    process.pid))
                process.terminate()
        HumanClient.serverProcess = None
        HumanClient.socketServerProcess = None

    def __del__(self):
        """if we go away and we started a local server, stop it again"""
        HumanClient.stopLocalServers()

    def remote_tablesChanged(self, tableid, tables):
        """update table list"""
        Client.remote_tablesChanged(self, tableid, tables)
        self.tableList.load(tableid, self.tables)

    def readyForGameStart(self, tableid, seed, playerNames, shouldSave=True):
        """playerNames are in wind order ESWN"""
        if sum(not x.startswith('ROBOT') for x in playerNames.split('//')) == 1:
            # we play against 3 robots and we already told the server to start: no need to ask again
            wantStart = True
        else:
            msg = m18n("The game can begin. Are you ready to play now?\n" \
                "If you answer with NO, you will be removed from the table.")
            wantStart = KMessageBox.questionYesNo (None, msg) == KMessageBox.Yes
        if wantStart:
            Client.readyForGameStart(self, tableid, seed, playerNames, self.tableList.field, shouldSave=shouldSave)
        else:
            self.answers.append(Message.NO)

    def readyForHandStart(self, playerNames, rotate):
        """playerNames are in wind order ESWN"""
        if self.game.handctr:
            if InternalParameters.autoPlay:
                self.clientReadyForHandStart(None, playerNames, rotate)
                return
            deferred = Deferred()
            deferred.addCallback(self.clientReadyForHandStart, playerNames, rotate)
            self.readyHandQuestion = ReadyHandQuestion(deferred, self.game.field)
            self.readyHandQuestion.show()
            self.answers.append(deferred)

    def clientReadyForHandStart(self, dummy, playerNames, rotate):
        """callback, called after the client player said yes, I am ready"""
        Client.readyForHandStart(self, playerNames, rotate)

    def ask(self, move, answers):
        """server sends move. We ask the user. answers is a list with possible answers,
        the default answer being the first in the list."""
        deferred = Deferred()
        deferred.addCallback(self.answered, move, answers)
        handBoard = self.game.myself.handBoard
        IAmActive = self.game.myself == self.game.activePlayer
        handBoard.setEnabled(IAmActive)
        field = self.game.field
        if not field.clientDialog or not field.clientDialog.isVisible():
            # always build a new dialog because if we change its layout before
            # reshowing it, sometimes the old buttons are still visible in which
            # case the next dialog will appear at a lower position than it should
            field.clientDialog = ClientDialog(self, field.centralWidget())
        field.clientDialog.ask(move, answers, deferred)
        self.answers.append(deferred)

    def selectChow(self, chows):
        """which possible chow do we want to expose?"""
        if InternalParameters.autoPlay:
            return Client.selectChow(self, chows)
        if len(chows) == 1:
            return chows[0]
        selDlg = SelectChow(chows)
        assert selDlg.exec_()
        return selDlg.selectedChow

    def answered(self, answer, move, answers):
        """the user answered our question concerning move"""
        if InternalParameters.autoPlay:
            self.game.hidePopups()
            return Client.ask(self, move, answers)
        message = None
        myself = self.game.myself
        try:
            if answer == Message.Discard:
                # do not remove tile from hand here, the server will tell all players
                # including us that it has been discarded. Only then we will remove it.
                myself.handBoard.setEnabled(False)
                return answer.name, myself.handBoard.focusTile.element
            args = self.maySay(move, answer)
            if args:
                return answer.name, args
            else:
                message = m18n('You cannot say %1', answer.i18nName)
        finally:
            if message:
                KMessageBox.sorry(None, message)
                self.game.field.clientDialog.hide()
                return self.ask(move, self.game.field.clientDialog.answers)
            else:
                self.game.hidePopups()

    def remote_abort(self, tableid, message, *args):
        """the server aborted this game"""
        if self.table and self.table.tableid == tableid:
            # translate ROBOT to Roboter:
            args = [m18nc('kajongg', x) for x in args]
            logWarning(m18n(message, *args))
            if self.game:
                self.game.close()
        if InternalParameters.autoPlay:
            if self.game and self.game.field:
                self.game.field.quit()

    def remote_gameOver(self, tableid, message, *args):
        """the server aborted this game"""
        if self.table and self.table.tableid == tableid:
            logWarning(m18n(message, *args))
            if self.game:
                self.game.rotateWinds()
                self.game.close()
        if InternalParameters.autoPlay:
            self.game.field.quit()

    def remote_serverDisconnects(self):
        """the kajongg server ends our connection"""
        self.perspective = None

    def loginCommand(self, username):
        """send a login command to server. That might be a normal login
        or adduser/deluser/change passwd encoded in the username"""
        factory = pb.PBClientFactory()
        reactor = self.tableList.field.reactor
        if self.useSocket:
            self.connector = reactor.connectUNIX(socketName(), factory)
        else:
            self.connector = reactor.connectTCP(self.loginDialog.host, self.loginDialog.port, factory)
        cred = credentials.UsernamePassword(username, self.loginDialog.password)
        return factory.login(cred, client=self)

    def adduser(self, host, name, passwd, callback):
        """create  a user account"""
        adduserDialog = AddUserDialog()
        hostIdx = adduserDialog.cbServer.findText(host)
        if hostIdx >= 0:
            adduserDialog.cbServer.setCurrentIndex(hostIdx)
        adduserDialog.username = self.loginDialog.username
        adduserDialog.password = self.loginDialog.password
        if not adduserDialog.exec_():
            raise Exception(m18n('Aborted creating a user account'))
        name, passwd = adduserDialog.username, adduserDialog.password
        adduserCmd =  SERVERMARK.join(['adduser', name, passwd])
        self.loginCommand(adduserCmd).addCallback(callback).addErrback(self._loginFailed)

    def _loginFailed(self, failure):
        """login failed"""
        message = failure.getErrorMessage()
        dlg = self.loginDialog
        host, name,  passwd = dlg.host, dlg.username, dlg.password
        if 'Wrong username' in message:
            msg = m18nc('USER is not known on SERVER',
                '%1 is not known on %2, do you want to open an account?', name, host)
            if KMessageBox.questionYesNo (None, msg) == KMessageBox.Yes:
                self.adduser(host, name, passwd, self.adduserOK)
                return
        else:
            logWarning(message)
        if self.callback:
            self.callback()

    def adduserOK(self, dummyFailure):
        """adduser succeeded"""
        Players.createIfUnknown(self.host, self.loginDialog.username)
        self.login()

    def login(self):
        """login to server"""
        self.root = self.loginCommand(self.loginDialog.username)
        self.root.addCallback(self.loggedIn).addErrback(self._loginFailed)

    def loggedIn(self, perspective):
        """we are online. Update table server and continue"""
        lasttime = datetime.datetime.now().replace(microsecond=0).isoformat()
        qData = Query('select url from server where url=?',
            list([self.host])).records
        if not qData:
            Query('insert into server(url,lastname,lasttime) values(?,?,?)',
                list([self.host, self.username, lasttime]))
        else:
            Query('update server set lastname=?,lasttime=? where url=?',
                list([self.username, lasttime, self.host]))
            Query('update player set password=? where host=? and name=?',
                list([self.loginDialog.password, self.host, self.username]))
        self.perspective = perspective
        if self.callback:
            self.callback()

    @apply
    def host():
        """the host name of the server"""
        def fget(self):
            if not self.connector:
                return None
            dest = self.connector.getDestination()
            if isinstance(dest, UNIXAddress):
                return Query.localServerName
            else:
                return dest.host
        return property(**locals())

    def logout(self):
        """clean visual traces and logout from server"""
        d = self.callServer('logout')
        if d:
            d.addBoth(self.loggedOut)
        return d

    def loggedOut(self, dummyResult):
        """client logged out from server"""
        self.discardBoard.hide()
        if self.readyHandQuestion:
            self.readyHandQuestion.hide()
        if self.game.field.clientDialog:
            self.game.field.clientDialog.hide()

    def callServer(self, *args):
        """if we are online, call server"""
        if self.perspective:
            try:
                return self.perspective.callRemote(*args)
            except pb.DeadReferenceError:
                self.perspective = None
                logWarning(m18n('The connection to the server %1 broke, please try again later.',
                                  self.host))
