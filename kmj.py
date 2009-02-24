#!/usr/bin/env python
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Copyright (C) 2008,2009 Wolfgang Rohdewald <wolfgang@rohdewald.de>

kmj is free software you can redistribute it and/or modify
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

import sys, os,  datetime
import util
from util import logMessage,  logException

import cgitb,  tempfile, webbrowser

class MyHook(cgitb.Hook):
    """override the standard cgitb hook: invoke the browser"""
    def __init__(self):
        self.tmpFileName = tempfile.mkstemp(suffix='.html', prefix='bt_', text=True)[1]
        cgitb.Hook.__init__(self, file=open(self.tmpFileName, 'w'))
  
    def handle(self,  info=None):
        """handling the exception: show backtrace in browser"""
        cgitb.Hook.handle(self, info)
        webbrowser.open(self.tmpFileName)
        
sys.excepthook = MyHook()
    
NOTFOUND = []

# TODO: Toolbar cannot be configured

try:
    from PyQt4 import  QtGui
    from PyQt4.QtCore import Qt, QVariant, QString, SIGNAL, SLOT, QEvent, QMetaObject
    from PyQt4.QtGui import QColor, QPushButton,  QMessageBox
    from PyQt4.QtGui import QWidget, QLabel
    from PyQt4.QtGui import QGridLayout, QVBoxLayout, QHBoxLayout,  QSpinBox
    from PyQt4.QtGui import QGraphicsScene,  QDialog
    from PyQt4.QtGui import QBrush
    from PyQt4.QtGui import QSizePolicy,  QComboBox,  QCheckBox, QTableView, QScrollBar
    from PyQt4.QtSql import QSqlDatabase, QSqlQueryModel, QSqlQuery
except ImportError,  e:
    NOTFOUND.append('PyQt4: %s' % e.message) 
    
try:
    from PyKDE4 import kdecore,  kdeui
    from PyKDE4.kdecore import ki18n,  i18n
    from PyKDE4.kdeui import KApplication,  KStandardAction,  KAction, KDialogButtonBox
except ImportError, e :
    NOTFOUND.append('PyKDE4: %s' % e.message) 
    
try:
    from board import PlayerWind, Walls,  FittingView,  ROUNDWINDCOLOR
    from playerlist import PlayerList
    from tileset import Tileset
    from background import Background
    from games import Games
    from genericdelegates import GenericDelegate,  IntegerColumnDelegate
    from config import Preferences,  ConfigDialog
except ImportError,  e:
    NOTFOUND.append('kmj modules: %s' % e.message)

if len(NOTFOUND):
    MSG = "\n".join(" * %s" % s for s in NOTFOUND)
    logMessage(MSG)
    os.popen("kdialog --sorry '%s'" % MSG)
    sys.exit(3)


WINDS = 'ESWN'

class ScoreModel(QSqlQueryModel):
    """a model for our score table"""
    def __init__(self,  parent = None):
        super(ScoreModel, self).__init__(parent)

    def data(self, index, role=None):
        """score table data"""
        if role is None:
            role = Qt.DisplayRole
        if role == Qt.BackgroundRole and index.column() == 2:
            prevailing = self.data(self.index(index.row(), 0)).toString()
            if prevailing == self.data(index).toString():
                return QVariant(ROUNDWINDCOLOR)
        if role == Qt.BackgroundRole and index.column()==3:
            won = self.data(self.index(index.row(), 1)).toString()
            if won == 'true':
                return QVariant(QColor(165, 255, 165))
        return QSqlQueryModel.data(self, index, role)

class ScoreTable(QWidget):
    """all player related data, GUI and internal together"""
    def __init__(self, game):
        super(ScoreTable, self).__init__(None)
        self.setWindowTitle(QString('%2 %3').arg(i18n('Scores for game')).arg(game.gameid))
        self.game = game
        self.__tableFields = ['prevailing', 'won', 'wind', 
                                'points', 'payments', 'balance']
        self.scoreModel = [ScoreModel(self) for player in range(0, 4)]
        self.scoreView = [QTableView(self)  for player in range(0, 4)]
        windowLayout = QVBoxLayout(self)
        playerLayout = QHBoxLayout()
        windowLayout.addLayout(playerLayout)
        self.hscroll = QScrollBar(Qt.Horizontal)
        windowLayout.addWidget(self.hscroll)
        for idx, player in enumerate(game.players):
            vlayout = QVBoxLayout()
            playerLayout.addLayout(vlayout)
            nlabel = QLabel(player.name)
            nlabel.setAlignment(Qt.AlignCenter)
            view = self.scoreView[idx]
            vlayout.addWidget(nlabel)
            vlayout.addWidget(view)
            model = self.scoreModel[idx]
            view.verticalHeader().hide()
            view.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            vpol = QSizePolicy()
            vpol.setHorizontalPolicy(QSizePolicy.Expanding)
            vpol.setVerticalPolicy(QSizePolicy.Expanding)
            view.setSizePolicy(vpol)
            view.setModel(model)
            delegate = GenericDelegate(self)
            delegate.insertColumnDelegate(self.__tableFields.index('payments'),         
                IntegerColumnDelegate())
            delegate.insertColumnDelegate(self.__tableFields.index('balance'), 
                IntegerColumnDelegate())
            view.setItemDelegate(delegate)
            view.setFocusPolicy(Qt.NoFocus)
            if idx != 3:
                view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
                self.connect(self.scoreView[3].verticalScrollBar(),
                        SIGNAL('valueChanged(int)'),
                        view.verticalScrollBar().setValue)
            for rcv_idx in range(0, 4):
                if idx != rcv_idx:
                    self.connect(view.horizontalScrollBar(),
                        SIGNAL('valueChanged(int)'),
                        self.scoreView[rcv_idx].horizontalScrollBar().setValue)
            self.retranslateUi(model)
            self.connect(view.horizontalScrollBar(), 
                SIGNAL('rangeChanged(int, int)'), 
                self.updateHscroll)
            self.connect(view.horizontalScrollBar(), 
                SIGNAL('valueChanged(int)'), 
                self.updateHscroll)
        self.connect(self.hscroll, 
            SIGNAL('valueChanged(int)'), 
            self.updateDetailScroll)
        self.loadTable()
        
    def updateDetailScroll(self, value):
        """synchronize all four views"""
        for view in self.scoreView:
            view.horizontalScrollBar().setValue(value)
            
    def updateHscroll(self):
        """update the single horizontal scrollbar we have for all four tables"""
        needBar = False
        dst = self.hscroll
        for src in [x.horizontalScrollBar() for x in self.scoreView]:
            if src.minimum() == src.maximum():
                continue
            needBar = True
            dst.setMinimum(src.minimum())
            dst.setMaximum(src.maximum())
            dst.setPageStep(src.pageStep())
            dst.setValue(src.value())
            dst.setVisible(dst.minimum() != dst.maximum())
            break
        dst.setVisible(needBar)
        
    def retranslateUi(self, model):
        """i18n of the table"""
        model.setHeaderData(self.__tableFields.index('points'),
                Qt.Horizontal, QVariant(i18n('Score')))
        model.setHeaderData(self.__tableFields.index('wind'),
                Qt.Horizontal, QVariant(''))
        # 0394 is greek big Delta, 2206 is mathematical Delta
        # this works with linux, on Windows we have to check if the used font
        # can display the symbol, otherwise use different font
        model.setHeaderData(self.__tableFields.index('payments'),
                Qt.Horizontal, QVariant(u"\u2206"))
        # 03A3 is greek big Sigma, 2211 is mathematical Sigma
        model.setHeaderData(self.__tableFields.index('balance'),
                Qt.Horizontal, QVariant(u"\u2211"))

    def loadTable(self):
        """load the data for this game and this player"""
        for idx, player in enumerate(self.game.players):
            model = self.scoreModel[idx]
            view = self.scoreView[idx]
            qStr = "select %s from score where game = %d and player = %d" % \
                (', '.join(self.__tableFields), self.game.gameid,  player.nameid)
            model.setQuery(qStr, self.game.dbhandle)
            view.hideColumn(0)
            view.hideColumn(1)
            view.resizeColumnsToContents()
            view.horizontalHeader().setStretchLastSection(True)
            view.verticalScrollBar().setValue(view.verticalScrollBar().maximum())
            
class SelectPlayers(QDialog):
    """a dialog for selecting four players"""
    def __init__(self, playerNames):
        QDialog.__init__(self, None)
        self.setObjectName("SelectPlayers")
        self.setWindowTitle(i18n('Select four players') + ' - kmj')
        self.buttonBox = KDialogButtonBox(self)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.buttonBox.button(QtGui.QDialogButtonBox.Ok).setEnabled(False)
        self.connect(self.buttonBox, SIGNAL("accepted()"), self, SLOT("accept()"))
        self.connect(self.buttonBox, SIGNAL("rejected()"), self, SLOT("reject()"))
        grid = QGridLayout()
        self.names = None
        self.scenes = []
        self.nameWidgets = []
        tileset = Tileset('traditional')
        for idx, wind in enumerate(WINDS):
            cbName = QComboBox()
            # increase width, we want to see the full window title
            cbName.setMinimumWidth(350) # is this good for all platforms?
            cbName.addItems(playerNames.values())
            grid.addWidget(cbName, idx+1, 1)
            self.nameWidgets.append(cbName)
            self.scenes.append(QGraphicsScene())
            view = FittingView()
            view.setEnabled(False)
            view.setScene(self.scenes[idx])
            pwind = PlayerWind(wind)
            pwind.setTileset(tileset)
            pwind.scale(0.3, 0.3)
            self.scenes[idx].addItem(pwind)
            grid.addWidget(view, idx+1, 0)
            self.connect(cbName, SIGNAL('currentIndexChanged(const QString&)'),
                self.slotValidate)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 6)
        vbox = QVBoxLayout(self)
        vbox.addLayout(grid)
        vbox.addWidget(self.buttonBox)
        self.resize(300, 200)
    
    def showEvent(self, event):
        """start with player 0"""
        self.nameWidgets[0].setFocus()

    def slotValidate(self):
        """update status of the Ok button"""
        self.names = list(str(cbName.currentText()) for cbName in self.nameWidgets)
        valid = len(set(self.names)) == 4
        self.buttonBox.button(QtGui.QDialogButtonBox.Ok).setEnabled(valid)
        

class EnterHand(QDialog):
    """a dialog for entering the scores"""
    def __init__(self, players):
        QDialog.__init__(self, None)
        self.setWindowTitle(i18n('Enter the hand results'))
        self.winner = None
        self.players = players
        self.buttonBox = KDialogButtonBox(self)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.buttonBox.button(QtGui.QDialogButtonBox.Ok).setEnabled(False)
        self.connect(self.buttonBox, SIGNAL("accepted()"), self, SLOT("accept()"))
        self.connect(self.buttonBox, SIGNAL("rejected()"), self, SLOT("reject()"))
        grid = QGridLayout()
        grid.addWidget(QLabel(i18n("Player")), 0, 0)
        grid.addWidget(QLabel(i18n("Wind")), 0, 1)
        grid.addWidget(QLabel(i18n("Score")), 0, 2)
        grid.addWidget(QLabel(i18n("Mah Jongg")), 0, 3)
        self.scenes = []
        tileset = Tileset('traditional')
        for idx, player in enumerate(players):
            player.spValue = QSpinBox()
            player.spValue.setRange(0, util.PREF.upperLimit)
            name = QLabel(player.name)
            name.setBuddy(player.spValue)
            grid.addWidget(name, idx+1, 0)
            self.scenes.append(QGraphicsScene())
            view = FittingView()
            view.setScene(self.scenes[idx])
            pwind = PlayerWind(player.wind.name)
            pwind.setTileset(tileset)
            pwind.scale(0.3, 0.3)
            self.scenes[idx].addItem(pwind)
            view.setEnabled(False)
            grid.addWidget(view, idx+1, 1)
            grid.addWidget(player.spValue, idx+1, 2)
            player.won = QCheckBox("")
            grid.addWidget(player.won, idx+1, 3)
            self.connect(player.won, SIGNAL('stateChanged(int)'), self.wonChanged)
            self.connect(player.spValue, SIGNAL('valueChanged(int)'), self.slotValidate)
        vbox = QVBoxLayout(self)
        vbox.addLayout(grid)
        vbox.addWidget(self.buttonBox)
   
    def wonPlayer(self, checkbox):
        """the player who said mah jongg"""
        for player in self.players:
            if checkbox == player.won:
                return player
        return None

    def wonChanged(self):
        """if a new winner has been defined, uncheck any previous winner"""
        clicked = self.wonPlayer(self.sender())
        active = clicked.won.isChecked()
        if active:
            self.winner = clicked
            for player in self.players:
                if player != self.winner:
                    player.won.setChecked(False)
        else:
            if clicked == self.winner:
                self.winner = None
        self.slotValidate()
        
    def slotValidate(self):
        """update the status of the OK button"""
        valid = True
        if valid:
            if self.winner is not None and self.winner.score < 20:
                valid = False
        self.buttonBox.button(QtGui.QDialogButtonBox.Ok).setEnabled(valid)

class Player(object):
    """all player related data, GUI and internal together"""
    def __init__(self, wind, scene,  wall):
        super(Player, self).__init__(None)
        self.scene = scene
        self.wall = wall
        self.__proxy = None
        self.spValue = None
        self.nameItem = None
        self.__balance = 0
        self.__payment = 0
        self.nameid = 0
        self.__name = ''
        self.name = ''
        self.wind = PlayerWind(wind, self.wall)
        faceRect = self.wall.faceRect()
        distToWall = faceRect.height()*0.5
        self.wind.setPos(faceRect.right(), faceRect.bottom() + distToWall)
 
    def getName(self):
        """the name of the player"""
        return self.__name

    def setNameColor(self):
        """sets the name color matching to the wall color"""
        if self.nameItem is None:
            return
        if self.wall.tileset.desktopFileName == 'jade':
            color = Qt.white
        else:
            color = Qt.black
        self.nameItem.setBrush(QBrush(QColor(color)))
        
    def setName(self, name):
        """change the name of the player, write it on the wall"""
        if self.__name == name:
            return
        self.__name = name
        if self.nameItem:
            self.scene.removeItem(self.nameItem)
        if name == '':
            return
        self.nameItem = self.scene.addSimpleText(name)
        self.setNameColor()
        self.nameItem.setParentItem(self.wall)
        self.nameItem.scale(3, 3)
        nameCenter = self.nameItem.boundingRect().center()
        if self.wall.rotation == 180:
            # rotate name around its center:
            transform = self.nameItem.transform().translate(nameCenter.x(), nameCenter.y()). \
                rotate(180).translate(-nameCenter.x(), -nameCenter.y())
            self.nameItem.setTransform(transform)
        nameRect = self.nameItem.mapToParent(self.nameItem.boundingRect()).boundingRect()
        wallRect = self.wall.faceRect(1)
        xPos = wallRect.left() + self.wall.faceSize().width()*9+ \
            self.wall.faceSize().height()/2-nameRect.width()/2
        # why 0.25? Anyway looks correct
        yPos = wallRect.top() + self.wall.faceSize().height()*0.5 - nameRect.height()*0.25
        self.nameItem.setPos(xPos, yPos)
        self.nameItem.setZValue(99999999999)
        
    name = property(getName, setName)
    
    def clearBalance(self):
        """sets the balance and the payments to 0"""
        self.__balance = 0
        self.__payment = 0
        
    @property
    def balance(self):
        """the balance of this player"""
        return self.__balance

    def getsPayment(self, payment):
        """make a payment to this player"""
        self.__balance += payment
        self.__payment += payment
        
    @property
    def payment(self):
        """the payments for the current hand"""
        return self.__payment
        
    def __get_score(self):
        """why does pylint want a doc string for this private method?"""
        return self.spValue.value()
            
    def __set_score(self,  score):
        """why does pylint want a doc string for this private method?"""
        if self.spValue is not None:
            self.spValue.setValue(score)
        if score == 0:
            # do not display 0 but an empty field
            if self.spValue is not None:
                self.spValue.clear()
            self.__payment = 0

    score = property(__get_score,  __set_score)
             
class MahJongg(kdeui.KXmlGuiWindow):
    """the main window"""
    def __init__(self):
        super(MahJongg, self).__init__()
        self.pref = Preferences()
        self.background = None
        
        self.dbhandle = QSqlDatabase("QSQLITE")
        self.dbpath = kdecore.KGlobal.dirs().locateLocal("appdata","kmj.db")
        self.dbhandle.setDatabaseName(self.dbpath)
        dbExists = os.path.exists(self.dbpath)
        if not self.dbhandle.open():
            logMessage(self.dbhandle.lastError().text())
            sys.exit(1)
        if not dbExists:
            self.createTables()
            self.addTestData()
        self.playerwindow = None
        self.scoreTableWindow = None
        self.playerIds = {}
        self.playerNames = {}
        self.roundsFinished = 0
        self.gameid = 0
        self.handctr = 0
        self.rotated = 0
        self.winner = None
        # shift rules taken from the OEMC 2005 rules
        # 2nd round: S and W shift, E and N shift
        self.shiftRules = 'SWEN,SE,WE' 
        self.setupUi()
        self.setupActions()
        self.creategui()

    def playerById(self, playerid):
        """lookup the player by id"""
        for player in self.players:
            if player.name == self.playerNames[playerid]:
                return player
        return None

    def createTables(self):
        """creates empty tables"""
        query = QSqlQuery(self.dbhandle)
        query.exec_("""CREATE TABLE player (
            id INTEGER PRIMARY KEY,
            name TEXT)""")
        query.exec_("""CREATE TABLE game (
            id integer primary key,
            starttime text default current_timestamp,
            endtime text,
            p0 integer constraint fk_p0 references player(id),
            p1 integer constraint fk_p1 references player(id),
            p2 integer constraint fk_p2 references player(id),
            p3 integer constraint fk_p3 references player(id))""")
        query.exec_("""CREATE TABLE score(
            game integer constraint fk_game references game(id),
            hand integer,
            rotated integer,
            player integer constraint fk_player references player(id),
            scoretime text,
            won integer references player(id),
            prevailing text,
            wind text,
            points integer,
            payments integer,
            balance integer)""")
            
    def addTestData(self):
        """adds test data to an empty data base"""
        query = QSqlQuery(self.dbhandle)
        for name in ['Wolfgang',  'Petra',  'Klaus',  'Heide']:
            query.exec_('INSERT INTO player (name) VALUES("%s")' % name)
        
    def creategui(self):
        """create and translate GUI from the ui.rc file: Menu and toolbars"""
        xmlFile = os.path.join(os.getcwd(), 'kmjui.rc')
        if os.path.exists(xmlFile):
            self.setupGUI(kdeui.KXmlGuiWindow.Default, xmlFile)
        else:
            self.setupGUI()
        self.retranslateUi()
        
    def kmjAction(self,  name, icon, slot):
        """simplify defining actions"""
        res = KAction(self)
        res.setIcon(kdeui.KIcon(icon))
        self.connect(res, SIGNAL('triggered()'), slot)
        self.actionCollection().addAction(name, res)
        return res

    def setBackground(self):
        """sets the background of the central widget"""
        if not self.background:
            self.background = Background(self.pref.background)
        self.background.setPalette(self.centralWidget)
        self.centralWidget.setAutoFillBackground(True)
    
    def resizeEvent(self, event):
        """adapt background to new window size"""
        self.setBackground()
        
    def setupUi(self):
        """create all other widgets
        we could make the scene view the central widget but I did
        not figure out how to correctly draw the background with
        QGraphicsView/QGraphicsScene.
        QGraphicsView.drawBackground always wants a pixmap
        for a huge rect like 4000x3000 where my screen only has
        1920x1200"""
        self.setObjectName("MainWindow")
        self.centralWidget = QWidget()
        self.centralScene = QGraphicsScene()
        self.centralView = FittingView()
        layout = QGridLayout(self.centralWidget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.centralView)
        self.centralView.setScene(self.centralScene)
        # setBrush(QColor(Qt.transparent) should work too but does  not
        self.tileset = Tileset(str(self.pref.tileset))
        self.walls = Walls(18, self.tileset)
        self.centralScene.addItem(self.walls)
    
        self.players =  [Player(WINDS[idx], self.centralScene, self.walls[idx]) \
            for idx in range(0, 4)]
        self.windTileset = Tileset('traditional')
        for player in self.players:
            player.wind.setTileset(self.windTileset)
            
        self.setCentralWidget(self.centralWidget)
        self.actionNewGame = self.kmjAction("new", "document-new", self.newGame)
        self.actionPlayers = self.kmjAction("players",  "personal",  self.slotPlayers)
        self.actionNewHand = self.kmjAction("newhand",  "object-rotate-left",  self.newHand)
        self.actionGames = self.kmjAction("load", "document-open", self.games)
        self.actionScoreTable = self.kmjAction("scoreTable", "format-list-ordered",
            self.showScoreTable)
        self.actionScoreTable.setEnabled(False)
                               
        QMetaObject.connectSlotsByName(self)

    def retranslateUi(self):
        """retranslate"""
        self.actionNewGame.setText(i18n("&New"))
        self.actionPlayers.setText(i18n("&Players"))
        self.actionNewHand.setText(i18n("&New hand"))
        self.actionGames.setText(i18n("&Load"))
        self.actionScoreTable.setText(i18n("&Score Table"))
    
    def changeEvent(self, event):
        """when the applicationwide language changes, recreate GUI"""
        if event.type() == QEvent.LanguageChange:
            self.creategui()
                
    def slotPlayers(self):
        """show the player list"""
        if not self.playerwindow:
            self.playerwindow = PlayerList(self)
        self.playerwindow.show()

    def showScoreTable(self):
        """show the score table"""
        if self.gameid == 0:
            logException(BaseException('showScoreTable: gameid is 0'))
        if not self.scoreTableWindow:
            self.scoreTableWindow = ScoreTable(self)
        self.scoreTableWindow.show()

    def findPlayer(self, wind):
        """returns the index and the player for wind"""
        for player in self.players:
            if player.wind.name == wind:
                return player
        logException(BaseException("no player has wind %s" % wind))
                
    def games(self):
        """show all games"""
        gameSelector = Games(self)
        if gameSelector.exec_():
            if gameSelector.selectedGame is not None:
                self.loadGame(gameSelector.selectedGame)
            else:
                self.newGame()
    
    def slotValidate(self):
        """validate data: Saving is only possible for valid data"""
        valid = not self.gameOver()
        self.actionNewHand.setEnabled(valid)

    def setupActions(self):
        """set up actions"""
        kapp = KApplication.kApplication()
        KStandardAction.preferences(self.showSettings, self.actionCollection())
        KStandardAction.quit(kapp.quit, self.actionCollection())
        self.applySettings()

    def applySettings(self,  name=None):
        """apply preferences
        if we just do self.tileset=Tileset(self.pref.tileset), changing the
        tileset from the config dialog is only  applied the first time. It always
        works if we ensure that the Tileset class gets a string with a
        different id. Maybe there is a problem in the interaction between
        python strings and QString.
        TODO: I should really find out if this is a bug in my code or in pyqt"""
        if self.tileset.desktopFileName != self.pref.tileset:
            self.tileset = Tileset(self.pref.tileset+'x'[:-1])
            self.walls.tileset = self.tileset
            for player in self.players:
                player.setNameColor()
        self.background = None # force setBackground to reload
        self.setBackground()
        
    def showSettings(self):
        """show preferences dialog. If it already is visible, do nothing"""
        if  kdeui.KConfigDialog.showDialog("settings"):
            return
        confDialog = ConfigDialog(self, "settings", self.pref)
        self.connect(confDialog, SIGNAL('settingsChanged(QString)'), 
           self.applySettings)
        confDialog.show()
        
    def swapPlayers(self, winds):
        """swap the winds for the players with wind in winds"""
        swappers = list(self.findPlayer(winds[x]) for x in (0, 1))
        mbox = QMessageBox()
        mbox.setWindowTitle("Swap seats")
        mbox.setText("By the rules, %s and %s should now exchange their seats. " % \
            (swappers[0].name, swappers[1].name))
        yesAnswer = QPushButton("&Exchange")
        mbox.addButton(yesAnswer, QMessageBox.YesRole)
        noAnswer = QPushButton("&Keep seat")
        mbox.addButton(noAnswer, QMessageBox.NoRole)
        mbox.exec_()
        if mbox.clickedButton() == yesAnswer:
            wind0 = swappers[0].wind
            wind1 = swappers[1].wind
            new0,  new1 = wind1.name,  wind0.name
            wind0.setWind(new0,  self.roundsFinished)
            wind1.setWind(new1,  self.roundsFinished)
        
    def exchangeSeats(self):
        """propose and execute seat exchanges according to the rules"""
        myRules = self.shiftRules.split(',')[self.roundsFinished-1]
        while len(myRules):
            self.swapPlayers(myRules[0:2])
            myRules = myRules[2:]
            

    def loadPlayers(self):
        """load all defined players into self.playerIds and self.playerNames"""
        query = QSqlQuery(self.dbhandle)
        if not query.exec_("select id,name from player"):
            logMessage(query.lastError().text())
            sys.exit(1)
        idField, nameField = range(2)
        self.playerIds = {}
        self.playerNames = {}
        while query.next():
            nameid = query.value(idField).toInt()[0]
            name = str(query.value(nameField).toString())
            self.playerIds[name] = nameid
            self.playerNames[nameid] = name
        
    def newGameId(self):
        """write a new entry in the game table with the selected players
        and returns the game id of that new entry"""
        starttime = datetime.datetime.now().replace(microsecond=0)
        query = QSqlQuery(self.dbhandle)
        query.prepare("INSERT INTO GAME (starttime,p0,p1,p2,p3)"
            " VALUES(:starttime,:p0,:p1,:p2,:p3)")
        query.bindValue(":starttime", QVariant(starttime.isoformat()))
        for idx, player in enumerate(self.players):
            query.bindValue(":p%d" % idx, QVariant(
                    self.playerIds[player.name]))
        if not query.exec_():
            logMessage('inserting into game:' + query.lastError().text())
            sys.exit(1)
        # now find out which game id we just generated. Clumsy and racy.
        if not query.exec_("select id from game where starttime = '%s'" % \
                           starttime.isoformat()):
            logMessage('getting gameid:' + query.lastError().text())
            sys.exit(1)
        query.first()
        return query.value(0).toInt()[0]
        
    def newGame(self):
        """init the first hand of a new game"""
        self.loadPlayers()
        selectDialog = SelectPlayers(self.playerNames)
        if not selectDialog.exec_():
            return
        self.roundsFinished = 0
        self.handctr = 1
        self.rotated = 0
        # initialize the four winds with the first four players:
        for player in self.players:
            player.clearBalance()
        for idx, player in enumerate(self.players):
            player.name = selectDialog.names[idx]
            player.nameid = self.playerIds[player.name]
        self.gameid = self.newGameId()
        self.showBalance()
        
    def saveHand(self):
        """compute and save the scores. Makes player names immutable."""
        handDialog = EnterHand(self.players)
        if not handDialog.exec_():
            return
        self.winner = handDialog.winner    
        if self.winner is None:
            ret = QMessageBox.question(None, i18n("Draw?"),
                        i18n("Nobody said Mah Jongg. Is this a draw?"),
                        QMessageBox.Yes, QMessageBox.No)
            if ret == QMessageBox.No:
                return False
        self.payHand()      
        query = QSqlQuery(self.dbhandle)
        query.prepare("INSERT INTO SCORE "
            "(game,hand,player,scoretime,won,prevailing,wind,points,payments, balance,rotated) "
            "VALUES(:game,:hand,:player,:scoretime,"
            ":won,:prevailing,:wind,:points,:payments,:balance,:rotated)")
        query.bindValue(':game', QVariant(self.gameid))
        scoretime = datetime.datetime.now().replace(microsecond=0).isoformat()
        query.bindValue(':scoretime', QVariant(scoretime))
        for player in self.players:
            name = player.name
            playerid = self.playerIds[name]
            query.bindValue(':hand', QVariant(self.handctr))
            query.bindValue(':player', QVariant(playerid))
            query.bindValue(':wind', QVariant(player.wind.name))
            query.bindValue(':won', QVariant(player.won.isChecked()))
            query.bindValue(':prevailing', QVariant(WINDS[self.roundsFinished]))
            query.bindValue(':points', QVariant(player.score))
            query.bindValue(':payments', QVariant(player.payment))
            query.bindValue(':balance', QVariant(player.balance))
            query.bindValue(':rotated', QVariant(self.rotated))
            if not query.exec_():
                logException(BaseException('inserting into score:', query.lastError().text()))
                sys.exit(1)
        self.actionScoreTable.setEnabled(True)
        self.showBalance()
        return True
        
    def newHand(self):
        """save this hand and start the next"""
        if self.gameid == 0:
            self.newGame()
            if self.gameid == 0:
                return
        assert not self.gameOver()
        if self.handctr > 0:
            if not self.saveHand():
                return
        self.rotate()
                
    def rotate(self):
        """initialize the values for a new hand"""
        if self.handctr > 0:
            if self.winner is not None and self.winner.wind.name != 'E':
                self.rotateWinds()
        self.handctr += 1

    def loadGame(self, game):
        """load game data by game id"""
        self.loadPlayers() # we want to make sure we have the current definitions
        self.gameid = game
        self.actionScoreTable.setEnabled(True)
        query = QSqlQuery(self.dbhandle)
        fields = ['hand', 'prevailing', 'player', 'wind', 
                                'balance', 'rotated']
        
        query.exec_("select %s from score where game=%d and hand="
            "(select max(hand) from score where game=%d)" \
            % (', '.join(fields), game, game))
        if query.next():
            roundwind = str(query.value(fields.index('prevailing')).toString())
            self.roundsFinished = WINDS.index(roundwind)
            self.handctr = query.value(fields.index('hand')).toInt()[0]
            self.rotated = query.value(fields.index('rotated')).toInt()[0]
        else:
            self.roundsFinished = 0
            self.handctr = 0
            self.rotated = 0
            
        query.exec_("select p0, p1, p2, p3 from game where id = %d" %game)
        query.next()
        for idx, player in enumerate(self.players):
            player.nameid = query.value(idx).toInt()[0]
            player.name = self.playerNames[player.nameid]
        
        query.exec_("select player, wind, balance from score "
            "where game=%d and hand=%d" % (game, self.handctr))
        while query.next():
            playerid = query.value(0).toInt()[0]
            wind = str(query.value(1).toString())
            player = self.playerById(playerid)
            if not player:
                logException(BaseException(
                'game %d data inconsistent: player %d missing in game table' % \
                    (game, playerid)))
            player.clearBalance()
            player.getsPayment(query.value(2).toInt()[0])
            player.wind.setWind(wind,  self.roundsFinished)
        self.showScoreTable()
        self.showBalance()
        self.rotate()

    def showBalance(self):
        """show the player balances in the statusbar"""
        if self.scoreTableWindow:
            self.scoreTableWindow.loadTable()
        sBar = self.statusBar()
        for idx, player in enumerate(self.players):
            sbMessage = player.name + ': ' + str(player.balance)
            if sBar.hasItem(idx):
                sBar.changeItem(sbMessage, idx)
            else:
                sBar.insertItem(sbMessage, idx, 1)
                sBar.setItemAlignment(idx, Qt.AlignLeft)

    def gameOver(self):
        """The game is over after 4 completed rounds"""
        result = self.roundsFinished == 4 
        if result:
            self.gameid = 0
        return  result
        
    def rotateWinds(self):
        """suprise: rotates the winds"""
        self.rotated += 1
        if self.rotated == 4:
            if self.roundsFinished < 4:
                self.roundsFinished += 1
            self.rotated = 0
        if self.gameOver():
            endtime = datetime.datetime.now().replace(microsecond=0).isoformat()
            query = QSqlQuery(self.dbhandle)
            query.prepare('UPDATE game set endtime = :endtime where id = :id')
            query.bindValue(':endtime', QVariant(endtime))
            query.bindValue(':id', QVariant(self.gameid))
            if not query.exec_():
                logMessage('updating game.endtime:'+ query.lastError().text())
                sys.exit(1)
        else:
            winds = [player.wind.name for player in self.players]
            winds = winds[3:] + winds[0:3]
            for idx,  newWind in enumerate(winds):
                self.players[idx].wind.setWind(newWind,  self.roundsFinished)
            if 0 < self.roundsFinished < 4 and self.rotated == 0:
                self.exchangeSeats()

    def payHand(self):
        """pay the scores"""
        for idx1, player1 in enumerate(self.players):
            for idx2, player2 in enumerate(self.players):
                if idx1 != idx2:
                    if player1.wind.name == 'E' or player2.wind.name == 'E':
                        efactor = 2
                    else:
                        efactor = 1
                    if player2 != self.winner:
                        player1.getsPayment(player1.score * efactor)
                    if player1 != self.winner:
                        player1.getsPayment(-player2.score * efactor)
        
class About(object):
    """we need persistent data but do not want to spoil global namespace"""
    def __init__(self):
        self.appName     = "kmj"
        self.catalog     = ""
        self.programName = ki18n ("kmj")
        self.version     = "0.1"
        self.description = ki18n ("kmj - computes payments among the 4 players")
        self.kmjlicense     = kdecore.KAboutData.License_GPL
        self.kmjcopyright   = ki18n ("(c) 2008,2009 Wolfgang Rohdewald")
        self.aboutText        = ki18n("This is the classical Mah Jongg for four players. "
            "If you are looking for the Mah Jongg solitaire please use the "
            "application kmahjongg. Right now this programm only allows to "
            "enter the scores, it will then compute the payments and show "
            "the ranking of the players.")
        self.homePage    = ""
        self.bugEmail    = "wolfgang@rohdewald.de"
        
        self.about  = kdecore.KAboutData (self.appName, self.catalog,
                        self.programName,
                        self.version, self.description,
                        self.kmjlicense, self.kmjcopyright, self.aboutText,
                        self.homePage, self.bugEmail)
                                
ABOUT = About()

kdecore.KCmdLineArgs.init (sys.argv, ABOUT.about)
APP = kdeui.KApplication()
MAINWINDOW =  MahJongg()
MAINWINDOW.show()
APP.exec_()
