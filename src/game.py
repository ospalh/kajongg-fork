# -*- coding: utf-8 -*-

"""
Copyright (C) 2008-2012 Wolfgang Rohdewald <wolfgang@rohdewald.de>

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
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
"""

import datetime
from random import Random
from collections import defaultdict
from twisted.internet.defer import succeed
from util import logError, logWarning, logException, logDebug, m18n, stack
from common import BasicStyle, Debug, IntDict, InternalParameters, WINDS, \
    elements, isAlive
from query import Transaction, Query
from rule import Ruleset
from tile import Tile
from meld import tileKey
from hand import Hand
from sound import Voice
from wall import Wall
from move import Move
from animation import Animated
from player import Player, Players

class CountingRandom(Random):
    """counts how often random() is called and prints debug info"""
    def __init__(self, game, value=None):
        self.game = game
        Random.__init__(self, value)
        self.count = 0
    def random(self):
        """the central randomizator"""
        self.count += 1
        return Random.random(self)
    def seed(self, newSeed=None):
        self.count = 0
        if Debug.random:
            self.game.debug('Random gets seed %s' % newSeed)
        Random.seed(self, newSeed)
    def shuffle(self, listValue, func=None, intType=int):
        oldCount = self.count
        Random.shuffle(self, listValue, func, intType)
        if Debug.random:
            self.game.debug('%d calls to random by Random.shuffle from %s' % (
                self.count - oldCount, stack('')[-2]))
    def randrange(self, start, stop=None, step=1, intType=int, default=None, maxWidth=9007199254740992L):
        oldCount = self.count
        result = Random.randrange(self, start, stop, step, intType, default, maxWidth)
        if Debug.random:
            self.game.debug('%d calls to random by Random.randrange(%d,%s) from %s' % (
                self.count - oldCount, start, stop, stack('')[-2]))
        return result
    def choice(self, fromList):
        if len(fromList) == 1:
            return fromList[0]
        oldCount = self.count
        result = Random.choice(self, fromList)
        if Debug.random:
            self.game.debug('%d calls to random by Random.choice(%s) from %s' % (
                self.count - oldCount, str([str(x) for x in fromList]), stack('')[-2]))
        return result
    def sample(self, population, wantedLength):
        oldCount = self.count
        result = Random.sample(self, population, wantedLength)
        if Debug.random:
            self.game.debug('%d calls to random by Random.sample(x, %d) from %s' % (
                self.count - oldCount, wantedLength, stack('')[-2]))
        return result

class Game(object):
    """the game without GUI"""
    # pylint: disable=R0902
    # pylint we need more than 10 instance attributes

    def __init__(self, names, ruleset, gameid=None, wantedGame=None, shouldSave=True, client=None):
        """a new game instance. May be shown on a field, comes from database if gameid is set

        Game.lastDiscard is the tile last discarded by any player. It is reset to None when a
        player gets a tile from the living end of the wall or after he claimed a discard.
        """
        # pylint: disable=R0915
        # pylint we need more than 50 statements
        self.players = Players() # if we fail later on in init, at least we can still close the program
        self.client = client
        self.rotated = 0
        self.notRotated = 0 # counts hands since last rotation
        self.ruleset = None
        self.roundsFinished = 0
        self.seed = 0
        self.randomGenerator = CountingRandom(self)
        if self.isScoringGame():
            self.wantedGame = str(wantedGame)
            self.seed = wantedGame
        else:
            self.wantedGame = wantedGame
            _ = int(wantedGame.split('/')[0]) if wantedGame else 0
            self.seed = _ or int(self.randomGenerator.random() * 10**9)
        self.shouldSave = shouldSave
        self.setHandSeed()
        self.activePlayer = None
        # For Japanese play, count East wins and draws.  This adds
        # points to the hand value.
        self.repeat_counter = 0
        # With Japanese play, riichi bets can carry over from one hand
        # to the next on exhaustive draws. Keep track of those.
        self.riichi_bets = 0
        self.__winners = []  # We may have more than one winner.
        self.__currentHandId = None
        self.__prevHandId = None
        self.moves = []
        self.myself = None   # the player using this client instance for talking to the server
        self.gameid = gameid
        self.playOpen = False
        self.autoPlay = False
        self.handctr = 0
        self.roundHandCount = 0
        self.handDiscardCount = 0
        self.divideAt = None
        self.lastDiscard = None # always uppercase
        self.lastDiscardBy = None  # Who dropped the last tile.
        self.visibleTiles = IntDict()
        self.discardedTiles = IntDict(self.visibleTiles) # tile names are always lowercase
        self.dice = []  # So some fancy graphics can show the throws
        self.dangerousTiles = list()
        self.csvTags = []
        self.setGameId()
        self.__useRuleset(ruleset)
        # shift rules taken from the OEMC 2005 rules
        # 2nd round: S and W shift, E and N shift
        self.shiftRules = 'SWEN,SE,WE'
        field = InternalParameters.field
        if field:
            field.game = self
            field.startingGame = False
            field.showWall()
        else:
            self.wall = Wall(self)
        self.assignPlayers(names)
        if self.belongsToGameServer():
            self.shufflePlayers()
        if not self.isScoringGame() and '/' in self.wantedGame:
            part = self.wantedGame.split('/')[1]
            roundsFinished = 'ESWN'.index(part[0])
            if roundsFinished > self.ruleset.minRounds:
                logWarning('Ruleset %s has %d minimum rounds but you want round %d(%s)' % (
                    self.ruleset.name, self.ruleset.minRounds, roundsFinished + 1, part[0]))
                self.roundsFinished = self.ruleset.minRounds
                return
            for _ in range(roundsFinished * 4 + int(part[1]) - 1):
                self.rotateWinds()
            for char in part[2:]:
                self.notRotated += self.notRotated * 26 + ord(char) + 1 - ord('a')
        if self.shouldSave:
            self.saveNewGame()
        if field:
            self.initVisiblePlayers()
            field.updateGUI()
            self.wall.decorate()

    @apply
    def winners(): # pylint: disable=E0202
        u"""
        The winners of the last hand.

        For Chinese games this should contain at most one winner (none
        during a hand or after a draw.) For Japanese games there may
        be up to three winners, when one discarded tile finishes more
        than one hand.
        """
        def fget(self):
            # pylint: disable=W0212
            return self.__winners
        def fset(self, value):
            # pylint: disable=W0212
            if value:
                value.sort()
            # Make sure the comparison below is not thrown off by a
            # different order of the winners.
            if self.__winners != value:
                # TODO: find out if this is right...
                for loser in self.__winners:
                    loser.invalidateHand()
                self.__winners = value
                for winner in self.__winners:
                    winner.invalidateHand()
        return property(**locals())

    def addCsvTag(self, tag, forAllPlayers=False):
        """tag will be written to tag field in csv row"""
        if forAllPlayers or self.belongsToHumanPlayer():
            self.csvTags.append('%s/%s' % (tag, self.handId()))

    def isFirstHand(self):
        """as the name says"""
        return self.roundHandCount == 0 and self.roundsFinished == 0

    def handId(self, withAI=True, withMoveCount=False):
        """identifies the hand for window title and scoring table"""
        aiVariant = ''
        if withAI and self.belongsToHumanPlayer():
            aiName = self.client.intelligence.name()
            if aiName != 'Default':
                aiVariant = aiName + '/'
        num = self.notRotated
        charId = ''
        while num:
            charId = chr(ord('a') + (num-1) % 26) + charId
            num = (num-1) / 26
        if self.finished():
            wind = 'X'
        else:
            wind = WINDS[self.roundsFinished]
        result = '%s%s/%s%s%s' % (aiVariant, self.seed, wind, self.rotated + 1, charId)
        if withMoveCount:
            result += '/moves:%d' % len(self.moves)
        if result != self.__currentHandId:
            self.__prevHandId = self.__currentHandId
            self.__currentHandId = result
        return result

    def setGameId(self):
        """virtual"""
        assert not self # we want it to fail, and quiten pylint

    def close(self):
        """log off from the server and return a Deferred"""
        InternalParameters.demo = False # do that only for the first game
        deferred = self.client.logout() if self.client else succeed(None)
        self.client = None
        return deferred

    def removeGameFromPlayfield(self):
        """remove the wall and player boards"""
        for player in self.players:
            if player.handBoard:
                player.clearHand()
                player.handBoard.hide()
        if self.wall:
            self.wall.hide()
            self.wall = None

    def initVisiblePlayers(self):
        """make players visible"""
        for idx, player in enumerate(self.players):
            player.front = self.wall[idx]
            player.clearHand()
            player.handBoard.setVisible(True)
            scoring = self.isScoringGame()
            player.handBoard.setEnabled(scoring or \
                (self.belongsToHumanPlayer() and player == self.myself))
            player.handBoard.showMoveHelper(scoring)
        InternalParameters.field.adjustView()

    def setConcealedTiles(self, allPlayerTiles):
        """when starting the hand. tiles is one string"""
        with Animated(False):
            for playerName, tileNames in allPlayerTiles:
                player = self.playerByName(playerName)
                player.addConcealedTiles(self.wall.deal(tileNames))

    def playerByName(self, playerName):
        """return None or the matching player"""
        if playerName is None:
            return None
        for myPlayer in self.players:
            if myPlayer.name == playerName:
                return myPlayer
        logException('Move references unknown player %s' % playerName)

    def losers(self):
        """
        The players that are not winners.

        For Chinese games, this are the three players that are not the
        winner if there is one, or all four players when the hand is drawn.
        For Japanese games this functions should not be used.
        """
        return list([x for x in self.players if x not in self.__winners])

    @staticmethod
    def windOrder(player):
        """cmp function for __exchangeSeats"""
        return 'ESWN'.index(player.wind)

    @apply
    def host():
        """the name of the game server this game is attached to"""
        def fget(self):
            if not InternalParameters.isServer and self.client:
                return self.client.host
        return property(**locals())

    def belongsToRobotPlayer(self):
        """does this game instance belong to a robot player?"""
        return self.client and self.client.isRobotClient()

    def belongsToHumanPlayer(self):
        """does this game instance belong to a human player?"""
        return self.client and self.client.isHumanClient()

    def belongsToGameServer(self):
        """does this game instance belong to the game server?"""
        return self.client and self.client.isServerClient()

    @staticmethod
    def isScoringGame():
        """are we scoring a manual game?"""
        return False

    def belongsToPlayer(self):
        """does this game instance belong to a player (as opposed to the game server)?"""
        return self.belongsToRobotPlayer() or self.belongsToHumanPlayer()

    def assignPlayers(self, playerNames):
        """the server tells us the seating order and player names"""
        pairs = []
        for idx, pair in enumerate(playerNames):
            if isinstance(pair, basestring):
                wind, name = WINDS[idx], pair
            else:
                wind, name = pair
            pairs.append((wind, name))

        field = InternalParameters.field
        if not self.players:
            if field:
                self.players = field.genPlayers()
            else:
                self.players = Players([Player(self) for idx in range(4)])
            for idx, pair in enumerate(pairs):
                wind, name = pair
                player = self.players[idx]
                Players.createIfUnknown(name)
                player.wind = wind
                player.name = name
        else:
            for idx, pair in enumerate(playerNames):
                wind, name = pair
                self.players.byName(name).wind = wind
        if self.client and self.client.username:
            self.myself = self.players.byName(self.client.username)
        self.sortPlayers()

    def assignVoices(self):
        """now we have all remote user voices"""
        assert self.belongsToHumanPlayer()
        available = Voice.availableVoices()[:]
        # available is without transferred human voices
        for player in self.players:
            if player.voice and player.voice.oggFiles():
                # remote human player sent her voice, or we are human and have a voice
                if Debug.sound and player != self.myself:
                    logDebug('%s got voice from opponent: %s' % (player.name, player.voice))
            else:
                player.voice = Voice.locate(player.name)
                if player.voice:
                    if Debug.sound:
                        logDebug('%s has own local voice %s' % (player.name, player.voice))
            if player.voice:
                for voice in Voice.availableVoices():
                    if voice in available and voice.md5sum == player.voice.md5sum:
                        # if the local voice is also predefined,
                        # make sure we do not use both
                        available.remove(voice)
        # for the other players use predefined voices in preferred language. Only if
        # we do not have enough predefined voices, look again in locally defined voices
        predefined = [x for x in available if x.language() != 'local']
        predefined.extend(available)
        for player in self.players:
            if player.voice is None and predefined:
                player.voice = predefined.pop(0)
                if Debug.sound:
                    logDebug('%s gets one of the still available voices %s' % (player.name, player.voice))

    def shufflePlayers(self):
        """assign random seats to the players and assign winds"""
        self.players.sort(key=lambda x:x.name)
        self.randomGenerator.shuffle(self.players)
        for player, wind in zip(self.players, WINDS):
            player.wind = wind

    def __exchangeSeats(self):
        """execute seat exchanges according to the rules"""
        windPairs = self.shiftRules.split(',')[(self.roundsFinished-1) % 4]
        while len(windPairs):
            windPair = windPairs[0:2]
            windPairs = windPairs[2:]
            swappers = list(self.players[windPair[x]] for x in (0, 1))
            if self.belongsToPlayer():
                # we are a client in a remote game, the server swaps and tells us the new places
                shouldSwap = False
            elif self.isScoringGame():
                # we play a manual game and do only the scoring
                shouldSwap = InternalParameters.field.askSwap(swappers)
            else:
                # we are the game server. Always swap in remote games.
                # do not do assert self.belongsToGameServer() here because
                # self.client might not yet be set - this code is called for all
                # suspended games but self.client is assigned later
                shouldSwap = True
            if shouldSwap:
                swappers[0].wind, swappers[1].wind = swappers[1].wind, swappers[0].wind
        self.sortPlayers()

    def sortPlayers(self):
        """sort by wind order. If we are in a remote game, place ourself at bottom (idx=0)"""
        players = self.players
        if InternalParameters.field:
            fieldAttributes = list([(p.handBoard, p.front) for p in players])
        players.sort(key=Game.windOrder)
        if self.belongsToHumanPlayer():
            myName = self.myself.name
            while players[0].name != myName:
                values0 = players[0].values
                for idx in range(4, 0, -1):
                    this, prev = players[idx % 4], players[idx - 1]
                    this.values = prev.values
                players[1].values = values0
            self.myself = players[0]
        if InternalParameters.field:
            for idx, player in enumerate(players):
                player.handBoard, player.front = fieldAttributes[idx]
                player.handBoard.player = player
        self.activePlayer = self.players['E']

    @staticmethod
    def _newGameId():
        """write a new entry in the game table
        and returns the game id of that new entry"""
        with Transaction():
            query = Query("insert into game(seed) values(0)")
            gameid, gameidOK = query.query.lastInsertId().toInt()
        assert gameidOK
        return gameid

    def saveNewGame(self):
        """write a new entry in the game table with the selected players"""
        if self.gameid is None:
            return
        if not self.isScoringGame():
            records = Query("select seed from game where id=?", list([self.gameid])).records
            assert records
            if not records:
                return
            seed = records[0][0]
        if self.isScoringGame() or seed == 'proposed' or seed == self.host:
            # we reserved the game id by writing a record with seed == hostname
            starttime = datetime.datetime.now().replace(microsecond=0).isoformat()
            args = list([starttime, self.seed, int(self.autoPlay), self.ruleset.rulesetId])
            args.extend([p.nameid for p in self.players])
            args.append(self.gameid)
            with Transaction():
                Query("update game set starttime=?,seed=?,autoplay=?," \
                        "ruleset=?,p0=?,p1=?,p2=?,p3=? where id=?", args)
                if not InternalParameters.isServer:
                    Query('update server set lastruleset=? where url=?',
                          list([self.ruleset.rulesetId, self.host]))

    def __useRuleset(self, ruleset):
        """use a copy of ruleset for this game, reusing an existing copy"""
        self.ruleset = ruleset
        self.ruleset.load()
        query = Query('select id from ruleset where id>0 and hash="%s"' % \
            self.ruleset.hash)
        if query.records:
            # reuse that ruleset
            self.ruleset.rulesetId = query.records[0][0]
        else:
            # generate a new ruleset
            self.ruleset.save(copy=True, minus=False)

    def setHandSeed(self):
        """set seed to a reproducable value, independent of what happend
        in previous hands/rounds.
        This makes it easier to reproduce game situations
        in later hands without having to exactly replay all previous hands"""
        if self.seed is not None:
            seedFactor = (self.roundsFinished + 1) * 10000 + self.rotated * 1000 + self.notRotated * 100
            self.randomGenerator.seed(self.seed * seedFactor)

    def prepareHand(self):
        """prepares the next hand"""
        del self.moves[:]
        if self.finished():
            if InternalParameters.field and isAlive(InternalParameters.field):
                InternalParameters.field.updateGUI()
            self.close()
        else:
            for player in self.players:
                player.clearHand()
            self.__winners = []
            if not self.isScoringGame():
                self.sortPlayers()
            self.hidePopups()
            self.setHandSeed()
            self.wall.build()

    def initHand(self):
        """directly before starting"""
        Hand.clearCache(self)
        self.dangerousTiles = list()
        self.discardedTiles.clear()
        assert self.visibleTiles.count() == 0
        if InternalParameters.field:
            InternalParameters.field.prepareHand()
        self.setHandSeed()

    def nixChances(self, nix_for=None):
        u"""
        Record that chances for some extra yaku are gone.

        Record that the chances for Blessing of Heaven, Earth or Man,
        double riichi, or ippatsu are gone.
        This should be called without argument on all claims of tiles
        and declarations of hidden kong (as that interrupts the turn),
        and with the player as the argument to nix the chances for
        only that player whenever ey discards a tile.
        """
        for player in self.players:
            if not nix_for or player is nix_for:
                player.ippatsu_chance = False
                player.double_riichi_chance = False

    def hidePopups(self):
        """hide all popup messages"""
        for player in self.players:
            player.hidePopup()

    def saveHand(self):
        """save hand to database, update score table and balance in status line"""
        self.__payHand()
        self.__saveScores()
        self.handctr += 1
        self.notRotated += 1
        self.roundHandCount += 1
        self.handDiscardCount = 0

    def needSave(self):
        """do we need to save this game?"""
        if self.isScoringGame():
            return True
        elif self.belongsToRobotPlayer():
            return False
        else:
            return self.shouldSave # as the server told us

    def __saveScores(self):
        """
        Save computed values to database.

        Save computed values to database. Update score table and
        balance in status line.
        """
        if not self.needSave():
            return
        scoretime = datetime.datetime.now().replace(microsecond=0).isoformat()
        for player in self.players:
            if player.hand:
                manualrules = '||'.join(x.rule.name for x in player.hand.usedRules)
            else:
                manualrules = m18n('Score computed manually')
            Query(
                """INSERT INTO SCORE
(game, hand, data, manualrules, player, scoretime, won, prevailing, wind,
 points, payments,  balance, rotated, notrotated, repeatcounter, riichibets)
VALUES (%d, %d, ?, ?, %d, '%s', %d, '%s', '%s', %d, %d, %d, %d, %d, %d, %d)"""
                % (self.gameid, self.handctr, player.nameid, scoretime,
                   # int(player == self.__winner),
                   int(player in self.__winners),
                   WINDS[self.roundsFinished % 4], player.wind,
                   player.handTotal, player.payment, player.balance,
                   self.rotated, self.notRotated, self.repeat_counter,
                   self.riichi_bets),
                  list([player.hand.string, manualrules]))
            if Debug.scores:
                self.debug(
                    '%s: handTotal=%s balance=%s %s' % (
                        player, player.handTotal, player.balance,
                        'won' if player in self.winners else ''))
            for usedRule in player.hand.usedRules:
                rule = usedRule.rule
                if rule.score.limits:
                    tag = rule.function.__class__.__name__
                    if hasattr(rule.function, 'limitHand'):
                        tag = rule.function.limitHand.__class__.__name__
                    self.addCsvTag(tag)

    def savePenalty(self, player, offense, amount):
        """save computed values to database, update score table and balance in status line"""
        if not self.needSave():
            return
        scoretime = datetime.datetime.now().replace(microsecond=0).isoformat()
        with Transaction():
            Query("INSERT INTO SCORE "
                "(game,penalty,hand,data,manualrules,player,scoretime,"
                "won,prevailing,wind,points,payments, balance,rotated,notrotated,repeat_counter,riichibets) "
                "VALUES(%d,1,%d,?,?,%d,'%s',%d,'%s','%s',%d,%d,%d,%d,%d,%d,%d)" % \
                (self.gameid, self.handctr, player.nameid,
                 scoretime,
                 # int(player == self.__winner),
                 int(player in self.__winners),
                 WINDS[self.roundsFinished % 4], player.wind, 0,
                 amount, player.balance, self.rotated, self.notRotated,
                 self.repeat_counter, self.riichi_bets),
                list([player.hand.string, offense.name]))
        if InternalParameters.field:
            InternalParameters.field.updateGUI()

    def maybeRotateWinds(self):
        """rules which make winds rotate"""
        result = list(x for x in self.ruleset.filterFunctions('rotate') if x.rotate(self))
        if result:
            if Debug.explain:
                if not self.belongsToRobotPlayer():
                    self.debug(result, prevHandId=True)
            self.rotateWinds()
        return bool(result)

    def rotateWinds(self):
        """rotate winds, exchange seats. If finished, update database"""
        self.rotated += 1
        self.notRotated = 0
        if self.rotated == 4:
            if not self.finished():
                self.roundsFinished += 1
            self.rotated = 0
            self.roundHandCount = 0
        if self.finished():
            endtime = datetime.datetime.now().replace(microsecond=0).isoformat()
            with Transaction():
                Query('UPDATE game set endtime = "%s" where id = %d' % \
                    (endtime, self.gameid))
        elif not self.belongsToPlayer():
            # the game server already told us the new placement and winds
            winds = [player.wind for player in self.players]
            winds = winds[3:] + winds[0:3]
            for idx, newWind in enumerate(winds):
                self.players[idx].wind = newWind
            if self.roundsFinished % 4 and self.rotated == 0 \
                    and not self.ruleset.basicStyle == BasicStyle.Japanese:
                # Exchange seats between rounds, but not for Japanese
                # games.
                self.__exchangeSeats()

    def debug(self, msg, btIndent=None, prevHandId=False):
        """prepend game id"""
        if self.belongsToRobotPlayer():
            prefix = 'R'
        elif self.belongsToHumanPlayer():
            prefix = 'C'
        elif self.belongsToGameServer():
            prefix = 'S'
        else:
            logDebug(msg, btIndent=btIndent)
            return
        logDebug('%s%s: %s' % (prefix, self.__prevHandId if prevHandId else self.handId(), msg),
            withGamePrefix=False, btIndent=btIndent)

    @staticmethod
    def __getNames(record):
        """get name ids from record
        and return the names"""
        names = []
        for idx in range(4):
            nameid = record[idx]
            try:
                name = Players.allNames[nameid]
            except KeyError:
                name = m18n('Player %1 not known', nameid)
            names.append(name)
        return names

    @classmethod
    def loadFromDB(cls, gameid, client=None):
        """
        Load game by game id.

        Load game by game id and return a new Game instance.
        """
        InternalParameters.logPrefix = 'S' if InternalParameters.isServer else 'C'
        qGame = Query("select p0,p1,p2,p3,ruleset,seed from game where id = %d" % gameid)
        if not qGame.records:
            return None
        rulesetId = qGame.records[0][4] or 1
        ruleset = Ruleset.cached(rulesetId)
        Players.load() # we want to make sure we have the current definitions
        game = cls(Game.__getNames(qGame.records[0]), ruleset, gameid=gameid,
                client=client, wantedGame=qGame.records[0][5])
        qLastHand = Query("select hand,rotated from score where game=%d and hand="
            "(select max(hand) from score where game=%d)" % (gameid, gameid))
        if qLastHand.records:
            (game.handctr, game.rotated) = qLastHand.records[0]

        qScores = Query(
            """select
player, wind, balance, won, prevailing, repeatcounter, riichibets
from score where game=%d and hand=%d""" % (gameid, game.handctr))
        # default value. If the server saved a score entry but our client did not,
        # we get no record here. Should we try to fix this or exclude such a game from
        # the list of resumable games?
        prevailing = 'E'
        for record in qScores.records:
            playerid = record[0]
            wind = str(record[1])
            player = game.players.byId(playerid)
            if not player:
                logError(
                'game %d inconsistent: player %d missing in game table' % \
                    (gameid, playerid))
            else:
                player.getsPayment(record[2])
                player.wind = wind
            if record[3] and player not in game.winners:
                # game.winner = player
                game.winners += [player ,]
                game.winners.sort()
            prevailing = record[4]
            game.repeat_counter = record[5]
            game.riichi_bets = record[6]
        game.roundsFinished = WINDS.index(prevailing)
        game.handctr += 1
        game.notRotated += 1
        game.maybeRotateWinds()
        game.sortPlayers()
        game.wall.decorate()
        return game

    def finished(self):
        """The game is over after minRounds completed rounds"""
        if self.ruleset:
            # while initialising Game, ruleset might be None
            return self.roundsFinished >= self.ruleset.minRounds

    def __payHand(self):
        """pay the scores"""
        # pylint: disable=R0912
        # too many branches
        if self.ruleset.basicStyle == BasicStyle.Japanese:
            # Japanese scoring is so different that it is easier to
            # just put it in an extra method.
            return self.__payJapaneseHand()
        assert len(self.__winners) < 2
        if self.__winners:
            winner = self.__winners[0]
            winner.wonCount += 1
            guilty = winner.usedDangerousFrom
            if guilty:
                payAction = self.ruleset.findUniqueOption('payforall')
            if guilty and payAction:
                if Debug.dangerousGame:
                    self.debug('%s: winner %s. %s pays for all' % \
                                (self.handId(), winner, guilty))
                guilty.hand.usedRules.append((payAction, None))
                score = winner.handTotal
                score = score * 6 if winner.wind == 'E' else score * 4
                guilty.getsPayment(-score)
                winner.getsPayment(score)
                return

        for player1 in self.players:
            if Debug.explain:
                if not self.belongsToRobotPlayer():
                    self.debug('%s: %s' % (player1, player1.hand.string))
                    for line in player1.hand.explain():
                        self.debug('   %s' % (line))
            for player2 in self.players:
                if id(player1) != id(player2):
                    if player1.wind == 'E' or player2.wind == 'E':
                        efactor = 2
                    else:
                        efactor = 1
                    if player2 != winner:
                        player1.getsPayment(player1.handTotal * efactor)
                    if player1 != winner:
                        player1.getsPayment(-player2.handTotal * efactor)

    def __payJapaneseHand(self):
        u"""
        Pay the points for a hand, Japanese style

        Only the winner gets paid. When it was a ron (win on discard),
        the discarder always pays. (This is similar to “dangerous
        play” in Chinese rules, only *every* discard is treated that
        way.) Also, the points are rounded to full hundreds.
        """
        def upToHundred(i):
            """Return number, rounded up to the xext hundred."""
            # We play around with // and / here. See also rule.Score,
            # where we do the same with 10 instead of 100.
            if i // 100 == i / 100.0:
                # Already a multiple of 100.
                return i
            # Not a multiple of 100
            return (i // 100) * 100 + 100

        # TODO: handle bankrupcy.
        for winner in self.__winners:
            # TODO: Check that the simple for loop works out for
            # multiple winners.
            # TODO: Hand back riichi bet
            winner.wonCount += 1
            payer = self.lastDiscardBy
            score = winner.handTotal
            if Debug.explain:
                if not self.belongsToRobotPlayer():
                    self.debug('%s: %s' % (winner, winner.hand.string))
                    for line in winner.hand.explain():
                        self.debug('   %s' % (line))
            # score = winner.handTotal + self.repeats * 100
            if payer:
                # Ron
                if Debug.scores:
                    self.debug('%s: winner %s. %s pays for all' % \
                                   (self.handId(), winner, payer))
                score = score * 6 if winner.wind == 'E' else score * 4
                score = upToHundred(score)
                payer.getsPayment(
                    -score
                     - 3 * self.repeat_counter * self.ruleset.repeatValue)
                winner.getsPayment(
                    score
                    + 3 * self.repeat_counter * self.ruleset.repeatValue)
            else:
                # Tsumo
                if winner.wind == 'E':
                    score *= 2
                for loser in self.players:
                    if loser is winner:
                        # Erm, not a loser after all.
                        continue
                    if loser.wind == 'E':
                        loser.getsPayment(
                            -upToHundred(2 * score))
                        winner.getsPayment(upToHundred(2 * score))
                    else:
                        loser.getsPayment(-upToHundred(score))
                        winner.getsPayment(upToHundred(score))
                    # The repeat value is not doubled for E, so we
                    # have to do this separately.
                    loser.getsPayment(
                        -self.repeat_counter * self.ruleset.repeatValue)
                    winner.getsPayment(
                        self.repeat_counter * self.ruleset.repeatValue)
        if self.__winners:
            if any(winner.wind == 'E' for winner in self.__winners):
                self.repeat_counter += 1
                if Debug.scores:
                    self.debug('East is a winner, now {} counter(s).'.format(
                            self.repeat_counter))
            else:
                if Debug.scores:
                    self.repeat_counter = 0
                    self.debug(
                        'Somebody won, but not East. Resetting counters.')
        else:
            # Here we should check for  Nagashi mangan. TODO
            # And settle the noten penalties. TODO
            # Or maybe settle chombo penalties. TODO
            # if not chombo ...
            self.repeat_counter += 1
            if Debug.scores:
                    self.debug('No winner, now {} counter(s)'.format(
                        self.repeat_counter))



    def lastMoves(self, only=None, without=None):
        """filters and yields the moves in reversed order"""
        for idx in range(len(self.moves)-1, -1, -1):
            move = self.moves[idx]
            if only:
                if move.message in only:
                    yield move
            elif without:
                if move.message not in without:
                    yield move
            else:
                yield move

    def throwDice(self):
        u"""
        Determine the place where to break the wall.

        Sets self.divideAt, the point where the wall is broken, based
        on four random values in the range of 1–6, a.k.a dice throws.
        For the instance belonging to the game server, this is also
        where we shuffle the tiles in the wall.
        """
        if self.belongsToGameServer():
            self.wall.tiles.sort(key=tileKey)
            self.randomGenerator.shuffle(self.wall.tiles)
        # Do it by the book. Use the first two dice to determine the
        # wall segment to use.  Clear the dice list from the last game
        # and add two new.
        self.dice = [
            self.randomGenerator.randrange(1, 7),
            self.randomGenerator.randrange(1, 7)]

        breakWall = (1 - sum(self.dice)) % 4
        # The 1-sum is a fence post correction and takes into account
        # that we should take this count counter-clockwise, while the
        # wall is counted clockwise the rest of the time, incuding
        # determining the break point in the step below.
        # Btw, the way the break wall is determined, the chances for
        # the break wall are E: 22.2% (8 out of 36), S: 25%, W: 27.7%
        # (10 out of 36), N: 25%.
        sideLength = len(self.wall.tiles) // 4
        if self.ruleset.basicStyle != BasicStyle.Japanese:
            # Add two more throws, but not for Japanese games.
            self.dice += [
                self.randomGenerator.randrange(1, 7),
                self.randomGenerator.randrange(1, 7)]
        # Determine the break point. Count stacks of two each, not
        # single tiles.
        self.divideAt = breakWall * sideLength + 2 * sum(self.dice)
        # Wrap around at the end.
        self.divideAt %= len(self.wall.tiles)
        # print('Throws: {}, sum: {} Break wall: {}'.format(
        #         self.dice, sum(self.dice), breakWall))

    def dangerousFor(self, forPlayer, tile):
        """returns a list of explaining texts if discarding tile
        would be Dangerous game for forPlayer. One text for each
        reason - there might be more than one"""
        if self.ruleset.basicStyle == BasicStyle.Japanese:
            # Tiles are not especially dangerous for anybody from the
            # rules perspective in Japanese games.
            return []
        if isinstance(tile, Tile):
            tile = tile.element
        tile = tile.lower()
        result = []
        for dang, txt in self.dangerousTiles:
            if tile in dang:
                result.append(txt)
        for player in forPlayer.others():
            for dang, txt in player.dangerousTiles:
                if tile in dang:
                    result.append(txt)
        return result

    def computeDangerous(self, playerChanged=None):
        """recompute gamewide dangerous tiles. Either for playerChanged or for all players"""
        # We compute them even for Japanese games. They can be a
        # useful hint for the AI.
        self.dangerousTiles = list()
        if playerChanged:
            playerChanged.findDangerousTiles()
        else:
            for player in self.players:
                player.findDangerousTiles()
        self._endWallDangerous()

    def _endWallDangerous(self):
        """if end of living wall is reached, declare all invisible tiles as dangerous"""
        if len(self.wall.living) <=5:
            allTiles = [x for x in defaultdict.keys(elements.occurrence) if x[0] not in 'fy']
            # see http://www.logilab.org/ticket/23986
            invisibleTiles = set(x for x in allTiles if x not in self.visibleTiles)
            msg = m18n('Short living wall: Tile is invisible, hence dangerous')
            self.dangerousTiles = list(x for x in self.dangerousTiles if x[1] != msg)
            self.dangerousTiles.append((invisibleTiles, msg))

    def appendMove(self, player, command, kwargs):
        """append a Move object to self.moves"""
        self.moves.append(Move(player, command, kwargs))

class ScoringGame(Game):
    """we play manually on a real table with real tiles and use
    kajongg only for scoring"""

    def __init__(self, names, ruleset, gameid=None, client=None, wantedGame=None):
        Game.__init__(self, names, ruleset, gameid=gameid, client=client, wantedGame=wantedGame)
        field = InternalParameters.field
        field.selectorBoard.load(self)
        self.prepareHand()

    def prepareHand(self):
        """prepare a scoring game hand"""
        if not self.finished():
            selector = InternalParameters.field.selectorBoard
            selector.refill()
            selector.hasFocus = True
        Game.prepareHand(self)

    @staticmethod
    def isScoringGame():
        """are we scoring a manual game?"""
        return True

    def setGameId(self):
        """get a new id"""
        if not self.gameid:
            # a loaded game has gameid already set
            self.gameid = self._newGameId()

class PlayingGame(Game):
    """we play against the computer or against players over the net"""

    def setGameId(self):
        """do nothing, we already went through the game id reservation"""
        pass

class RemoteGame(PlayingGame):
    """this game is played using the computer"""
    # pylint: disable=R0913
    # pylint: disable=R0904
    # pylint too many arguments, too many public methods
    def __init__(self, names, ruleset, gameid=None, wantedGame=None, shouldSave=True, \
            client=None, playOpen=False, autoPlay=False):
        """a new game instance, comes from database if gameid is set"""
        self.__activePlayer = None
        self.prevActivePlayer = None
        self.defaultNameBrush = None
        PlayingGame.__init__(self, names, ruleset, gameid,
            wantedGame=wantedGame, shouldSave=shouldSave, client=client)
        self.playOpen = playOpen
        self.autoPlay = autoPlay
        myself = self.myself
        if self.belongsToHumanPlayer() and myself:
            myself.voice = Voice.locate(myself.name)
            if myself.voice:
                if Debug.sound:
                    logDebug('RemoteGame: myself %s gets voice %s' % (myself.name, myself.voice))
            else:
                if Debug.sound:
                    logDebug('myself %s gets no voice'% (myself.name))

    @apply
    def activePlayer(): # pylint: disable=E0202
        """the turn is on this player"""
        def fget(self):
            # pylint: disable=W0212
            return self.__activePlayer
        def fset(self, player):
            # pylint: disable=W0212
            if self.__activePlayer != player:
                self.prevActivePlayer = self.__activePlayer
                if self.prevActivePlayer:
                    self.prevActivePlayer.hidePopup()
                self.__activePlayer = player
                if InternalParameters.field: # mark the name of the active player in blue
                    for player in self.players:
                        player.colorizeName()
        return property(**locals())

    def nextPlayer(self, current=None):
        """returns the player after current or after activePlayer"""
        if not current:
            current = self.activePlayer
        pIdx = self.players.index(current)
        return self.players[(pIdx + 1) % 4]

    def nextTurn(self):
        """move activePlayer"""
        self.activePlayer = self.nextPlayer()

    def initialDeal(self):
        """Happens only on server: every player gets 13 tiles (including east)"""
        self.throwDice()
        self.wall.divide()
        for player in self.players:
            player.clearHand()
            # 13 tiles at least, with names as given by wall
            player.addConcealedTiles(self.wall.deal([None] * 13))
            # compensate boni
            while len(player.concealedTileNames) != 13:
                player.addConcealedTiles(self.wall.deal())

    def __concealedTileName(self, tileName):
        """tileName has been discarded, by which name did we know it?"""
        player = self.activePlayer
        if self.myself and player != self.myself and not self.playOpen:
            # we are human and server tells us another player discarded a tile. In our
            # game instance, tiles in handBoards of other players are unknown
            player.makeTileKnown(tileName)
            result = 'Xy'
        else:
            result = tileName
        if not tileName in player.concealedTileNames:
            raise Exception('I am %s. Player %s is told to show discard of tile %s but does not have it, he has %s' % \
                           (self.myself.name if self.myself else 'None',
                            player.name, result, player.concealedTileNames))
        return result

    def hasDiscarded(self, player, tileName):
        """discards a tile from a player board"""
        # pylint: disable=R0912
        # too many branches
        if player != self.activePlayer:
            raise Exception('Player %s discards but %s is active' % (player, self.activePlayer))
        # We switch on the ippatsu chance *after* the discard, so it
        # should be safe to switch it off for every discard.
        self.nixChances(player)
        # Keep track who discarded the tile. In Japanese style
        # scoring, the discarder always pays for all (similar to
        # Chinese dangerous play).
        self.lastDiscardBy = player
        self.discardedTiles[tileName.lower()] += 1
        player.discarded.append(tileName)
        concealedTileName = self.__concealedTileName(tileName) # has side effect, needs to be called
        if InternalParameters.field:
            if player.handBoard.focusTile and player.handBoard.focusTile.element == tileName:
                self.lastDiscard = player.handBoard.focusTile
            else:
                matchingTiles = sorted(player.handBoard.tilesByElement(concealedTileName),
                    key=lambda x:x.xoffset)
                # if an opponent player discards, we want to discard from the right end of the hand
                # thus minimizing tile movement
                self.lastDiscard = matchingTiles[-1]
                self.lastDiscard.element = tileName
            InternalParameters.field.discardBoard.discardTile(self.lastDiscard)
        else:
            self.lastDiscard = Tile(tileName)
        player.remove(tile=self.lastDiscard)
        if any(tileName.lower() in x[0] for x in self.dangerousTiles):
            self.computeDangerous()
        else:
            self._endWallDangerous()
        self.handDiscardCount += 1
        if InternalParameters.field:
            for tile in player.handBoard.tiles:
                tile.focusable = False

    def checkTarget(self):
        """check if we reached the point defined by --game.
        If we did, disable autoPlay"""
        parts = self.wantedGame.split('/')
        if len(parts) > 1:
            discardCount = int(parts[2]) if len(parts) > 2 else 0
            if self.handId().split('/')[-1] == parts[1] \
               and self.handDiscardCount >= int(discardCount):
                self.autoPlay = False
                self.wantedGame = parts[0] # --game has been processed
                if InternalParameters.field: # mark the name of the active player in blue
                    InternalParameters.field.actionAutoPlay.setChecked(False)

    def saveHand(self):
        """server told us to save this hand"""
        for player in self.players:
            assert player.hand.won == (player in  self.winners)
        Game.saveHand(self)
