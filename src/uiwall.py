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

from common import BasicStyle, InternalParameters, Preferences, ZValues
from PyQt4.QtCore import QRectF, QPointF
from PyQt4.QtGui import QGraphicsSimpleTextItem, QGraphicsRectItem, QBrush, QPen, QColor, QFont, QFontMetrics

from board import PlayerWind, YellowText, Board, rotateCenter, OrderedDiscardBoard
from game import Wall
from animation import animate, afterCurrentAnimationDo, Animated, \
    ParallelAnimationGroup

def fill_order(game):
    try:
        offset = 'ESWN'.find(game.myself.wind)
    except Exception as e:
        offset = 0
    order = [0, 3, 2, 1, 0, 3, 2]
    for i in range(4):
        # print('filling board {}'.format(order[i + offset]))
        yield order[i + offset]


class UIWallSide(Board):
    """a Board representing a wall of tiles"""
    def __init__(self, tileset, boardRotation, length):
        width = 1.5
        game = InternalParameters.field.game
        if game and (game.ruleset.basicStyle == BasicStyle.Japanese
                     or game.ruleset.replenish_dead_wall):
            width = 1
        Board.__init__(
            self, length, width, tileset, boardRotation=boardRotation)
        self.length = length
        # We add a few of these later.
        self.windTile = None
        self.infoBox = None
        self.nameLabel = None

    # pylint: disable=R0201
    def name(self):
        """name for debug messages"""
        game = InternalParameters.field.game
        if not game:
            return 'NOGAME'
        for player in game.players:
            if player.front == self:
                return 'wallside %s'% player.name

    def center(self):
        """returns the center point of the wall in relation to the faces of the upper level"""
        faceRect = self.tileFaceRect()
        result = faceRect.topLeft() + self.shiftZ(1) + \
            QPointF(self.length // 2 * faceRect.width(), faceRect.height()/2)
        result.setX(result.x() + faceRect.height()/2) # corner tile
        return result

class PlayerInfoBox(QGraphicsRectItem):
    u"""
    An area that contains some information about a player.

    An area that contains some information about a player. This is
    used for games with ordered discards, and fills up the area to the
    right of the player’s discards.
    """
    def __init__(self, side, tileset):
        QGraphicsRectItem.__init__(self, side)
        self.side = side
        self.font = QFont()
        self.font.setPointSize(32)
        self.f_height = tileset.faceSize.height()
        self.f_width = tileset.faceSize.width()
        # self.s_height = tileset.shadowHeight()
        # self.s_width = tileset.shadowWidth()
        self.height =  4 * self.f_height
        self.width = 5.5 * self.f_width
        self.setRect(0, 0, self.width, self.height)
        metrics = QFontMetrics(self.font)
        # self.width = metrics.width(self.msg)
        self.line_height = metrics.lineSpacing()
        # self.msg = None
        # self.setText('')

    def paint(self, painter, dummyOption, dummyWidget):
        """override predefined paint"""
        # painter.setFont(self.font)
        brush = QBrush(QColor(255, 255, 255, 128))
        painter.setBrush(brush)
        pen = QPen(QColor(128, 128, 128, 128))
        painter.setPen(pen)
        painter.drawRoundedRect(self.rect(), 5, 5)




class UIWall(Wall):
    """
    Representation of the wall with four sides.

    Representation of the wall with four sides. self.wall[] indexes
    them counter clockwise, 0..3. 0 is bottom. N.B. """
    def __init__(self, game):
        """init and position the wall"""
        # we use only white dragons for building the wall. We could actually
        # use any tile because the face is never shown anyway.
        game.wall = self
        self.game = game
        Wall.__init__(self, game)
        tileset = InternalParameters.field.tileset
        inside = game.ruleset.basicStyle == BasicStyle.Japanese
        self.f_height = tileset.faceSize.height()
        self.f_width = tileset.faceSize.width()
        self.s_height = tileset.shadowHeight()
        self.s_width = tileset.shadowWidth()
        self.__square = Board(1, 1, tileset)
        self.__square.setZValue(ZValues.marker)
        sideLength = len(self.tiles) // 8
        angles = [0, 270, 180, 90]
        self.__sides = [UIWallSide(tileset, boardRotation, sideLength) \
            for boardRotation in angles]
        for idx, side in enumerate(self.__sides):
            if inside:
                side.infoBox = PlayerInfoBox(side, tileset)
                side.infoBox.setPos(
                    side.center() + QPointF(
                        3.0 * self.f_width,
                        -4 * self.f_height - self.s_height))
                        # 2.0 * self.f_width + self.s_width,
                        # -3.5 * self.f_height - self.s_height))
                box = side.infoBox
            else:
                box = None
            side.setParentItem(self.__square)
            side.lightSource = self.lightSource
            wind_name_parent = side.infoBox or side
            side.windTile = PlayerWind(
                'E', InternalParameters.field.windTileset,
                parent=wind_name_parent)
            if box:
                side.windTile.setPos(box.rect().topRight() - QPointF(
                        side.windTile.rect().width(), 0))
            side.windTile.hide()
            side.nameLabel = QGraphicsSimpleTextItem('', wind_name_parent)
            if box:
                font = box.font
            else:
                font = side.nameLabel.font()
                font.setPointSize(48)
            side.nameLabel.setFont(font)
            side.message = YellowText(wind_name_parent)
            side.message.setZValue(ZValues.popup)
            side.message.setVisible(False)
            if box:
                side.message.font = font
                side.nameLabel.setPos(box.rect().topLeft() + QPointF(
                        10, 0.0 * box.line_height))
                side.message.setPos(box.rect().topLeft() + QPointF(
                        50,  3.0 * box.line_height))
            else:
                side.message.setPos(side.center())
        self.corner_offset = 1
        if game.ruleset.basicStyle == BasicStyle.Japanese:
            self.corner_offset = 0
        self.__sides[0].setPos(yWidth=sideLength)
        self.__sides[3].setPos(xHeight=self.corner_offset)
        self.__sides[2].setPos(xHeight=self.corner_offset, xWidth=sideLength,
                               yHeight=self.corner_offset)
        self.__sides[1].setPos(
            xWidth=sideLength, yWidth=sideLength, yHeight=self.corner_offset)
        self.showShadows = Preferences.showShadows
        InternalParameters.field.centralScene.addItem(self.__square)

    # pylint: disable=R0201
    def name(self):
        """name for debug messages"""
        return 'wall'

    def __getitem__(self, index):
        """make Wall index-able"""
        return self.__sides[index]

    def __setitem__(self, index, value):
        """only for pylint, currently not used"""
        self.__sides[index] = value

    def __delitem__(self, index):
        """only for pylint, currently not used"""
        del self.__sides[index]

    def __len__(self):
        """only for pylint, currently not used"""
        return len(self.__sides)

    def hide(self):
        """hide all four walls and their decorators"""
        for side in self.__sides:
            side.windTile.hide()
            side.nameLabel.hide()
            side.hide()
            del side
        for tile in self.tiles:
            if tile.graphics:
                tile.graphics.hide()
            del tile
        self.tiles = []
        InternalParameters.field.centralScene.removeItem(self.__square)

    def __shuffleTiles(self):
        """shuffle tiles for next hand"""
        discardBoard = InternalParameters.field.discardBoard
        try:
            places = [(x, y) for x in range(-3, discardBoard.width+3)
                      for y in range(-3, discardBoard.height+3)]
        except AttributeError:
            # No discardBoard after all. (Japanese game.)
            return
        places = self.game.randomGenerator.sample(places, len(self.tiles))
        for idx, tile in enumerate(self.tiles):
            tile.dark = True
            tile.setBoard(discardBoard, *places[idx])

    def build(self):
        """builds the wall without dividing"""
        # recycle used tiles
        for tile in self.tiles:
            tile.element = 'Xy'
            tile.dark = True
#        field = InternalParameters.field
#        animateBuild = not field.game.isScoringGame() and not self.game.isFirstHand()
        animateBuild = False
        with Animated(animateBuild):
            self.__shuffleTiles()
            if self.tiles[0].board:
                # Quick test. Only change the focusable if a random
                # tile is in a board. May not be the case before the
                # first Japanese-style hand.
                for tile in self.tiles:
                    tile.focusable = False
            return animate().addCallback(self.__placeWallTiles)

    def __placeWallTiles(self, dummyResult=None):
        """place all wall tiles"""

        tileIter = iter(self.tiles)
        tilesPerSide = len(self.tiles) // 4
        # for side in (self.__sides[0], self.__sides[3],
        #              self.__sides[2], self.__sides[1]):

        # Make sure the tiles are aranged so that the break starts
        # with respect to the east wind, not the bottom (human
        # player).
        for side_index in fill_order(self.game):
            side = self.__sides[side_index]
            upper = True # upper tile is played first
            for position in range(tilesPerSide-1, -1, -1):
                tile = tileIter.next()
                tile.setBoard(side, position//2, 0, level=int(upper))
                upper = not upper
        self.__setDrawingOrder()
        return animate()

    @apply
    def lightSource():
        """setting this actually changes the visuals. For
        possible values see LIGHTSOURCES"""
        def fget(self):
            # pylint: disable=W0212
            return self.__square.lightSource
        def fset(self, lightSource):
            # pylint: disable=W0212
            if self.lightSource != lightSource:
                assert ParallelAnimationGroup.current is None
                self.__square.lightSource = lightSource
                for side in self.__sides:
                    side.lightSource = lightSource
                self.__setDrawingOrder()
        return property(**locals())

    @apply
    def tileset():
        """setting this actually changes the visuals."""
        def fget(self):
            # pylint: disable=W0212
            return self.__square.tileset
        def fset(self, value):
            # pylint: disable=W0212
            if self.tileset != value:
                assert ParallelAnimationGroup.current is None
                self.__square.tileset = value
                for side in self.__sides:
                    side.tileset = value
                self.__resizeHandBoards()
        return property(**locals())

    @apply
    # pylint: disable=E0202
    def showShadows():
        """setting this actually changes the visuals."""
        def fget(self):
            # pylint: disable=W0212
            return self.__square.showShadows
        def fset(self, showShadows):
            # pylint: disable=W0212
            if self.showShadows != showShadows:
                assert ParallelAnimationGroup.current is None
                self.__square.showShadows = showShadows
                for side in self.__sides:
                    side.showShadows = showShadows
                self.__resizeHandBoards()
        return property(**locals())

    def __resizeHandBoards(self, dummyResults=None):
        """we are really calling _setRect() too often. But at least it works"""
        for player in self.game.players:
            player.handBoard.computeRect()
        InternalParameters.field.adjustView()

    def __setDrawingOrder(self, dummyResults=None):
        """set drawing order of the wall"""
        levels = {'NW': (2, 3, 1, 0), 'NE':(3, 1, 0, 2), 'SE':(1, 0, 2, 3), 'SW':(0, 2, 3, 1)}
        for idx, side in enumerate(self.__sides):
            side.level = (levels[side.lightSource][idx] + 1) * ZValues.boardLevelFactor

    def _moveKongBox(self):
        u"""
        Move the tiles in the kong box.

        Move the tiles in the kong box (dead wall), either half a tile
        outward or by two tiles in line. One tile in line is kind-of
        enough when you have shadows on, but not without. But two
        tiles look better when there has been an odd number of
        kongs. (And using 1.5 tiles causes all kinds of problems.)
        """
        x_off = 0
        y_off = 0.5
        if self.game.ruleset.basicStyle == BasicStyle.Japanese \
                or self.game.ruleset.replenish_dead_wall:
            x_off = -2
            y_off = 0
        for tile in self.kongBox:
            self._moveDividedTile(tile, x_off, y_offset=y_off, level=None)

    def _moveTileToDeadWall(self):
        u"""
        Move a single tile from the living to the dead wall.
        """
        moved_tile = self.living[-1]
        self.kongBox = [moved_tile,] + self.kongBox
        self.living = self.living[:-1]
        # Then the graphical bit.
        try:
            lift_kongbox_tile = (self.kongBox[2].level == 0)
            # self.kongBox[0] now is the tile to be moved. This and
            # self.kongBox[1] should always be directly on the
            # table. The next one is above self.kongBox[1] or in the
            # next stack over and on the table, too.
        except IndexError:
            # No self.kongBox[2]. Shouldn’t happen in a typical game.
            lift_kongbox_tile = True
        if lift_kongbox_tile:
            try:
                # Lift the old last kongbox tile
                self._moveDividedTile(self.kongBox[1], 0, level=1)
            except IndexError:
                # If it is there
                pass
            # Now slide the moving tile underneath.
            self._moveDividedTile(moved_tile, -2, level=0)
        else:
            # First slide the tile into the gap.
            self._moveDividedTile(moved_tile, -2, level=0)
            try:
                # Move the next-to-last tile of the living wall down to the
                # table. (It *should* not already be there.)
                self._moveDividedTile(self.living[-1], 0, level=0)
            except IndexError:
                # Or it may not be there at all.
                pass

    def _moveDividedTile(self, tile, offset, y_offset=0, level=2):
        """moves a tile from the divide hole to its new place"""
        board = tile.board
        newOffset = tile.xoffset + offset
        sideLength = len(self.tiles) // 8
        if newOffset >= sideLength:
            sideIdx = self.__sides.index(tile.board)
            board = self.__sides[(sideIdx+1) % 4]
        if newOffset < 0:
            # Move around the other corner
            sideIdx = self.__sides.index(tile.board)
            board = self.__sides[(sideIdx-1) % 4]
        tile.setBoard(
            board, newOffset % sideLength, tile.yoffset + y_offset,
            level=level)

    def placeLooseTiles(self):
        """place the last 2 tiles on top of kong box"""
        assert len(self.kongBox) % 2 == 0
        afterCurrentAnimationDo(self.__placeLooseTiles2)

    def __placeLooseTiles2(self, dummyResult):
        """place the last 2 tiles on top of kong box, no animation is active"""
        placeCount = len(self.kongBox) // 2
        if self.game.ruleset.basicStyle != BasicStyle.Japanese:
            if placeCount >= 4:
                first = min(placeCount-1, 5)
                second = max(first-2, 1)
                self._moveDividedTile(self.kongBox[-1], second)
                self._moveDividedTile(self.kongBox[-2], first)
        else:
            self._moveDividedTile(self.kongBox[-1], -1, level=0)


    def divide(self):
        """divides a wall, building a living and and a dead end"""
        with Animated(False):
            Wall.divide(self)
            for tile in self.tiles:
                # update graphics because tiles having been
                # in kongbox in a previous game
                # might not be there anymore. This gets rid
                # of the cross on them.
                tile.graphics.update()
            self._moveKongBox()
            # move last two tiles onto the dead end:
            return animate().addCallback(self.__placeLooseTiles2)

    def decorate(self):
        """show player info on the wall"""
        for player in self.game.players:
            self.decoratePlayer(player)

    def decoratePlayer(self, player):
        u"""
        Show player info.

        Show player info. It either appears on the wall or in the
        empty space to the right of a player’s discards.
        """
        side = player.front
        box = side.infoBox  # Either a PlayerInfoBox or None
        sideCenter = side.center()
        name = side.nameLabel
        if player.handBoard:
            player.newHandContent = player.computeNewHand()
            name.setText(' - '.join([player.localName, unicode(player.newHandContent.total())]))
        else:
            name.setText(player.localName)
        name.resetTransform()
        if side.rotation() == 180 and not box:
            rotateCenter(name, 180)
        nameRect = QRectF()
        nameRect.setSize(
            name.mapToParent(name.boundingRect()).boundingRect().size())
        if box:
            box_rot = side.rotation()
            if box_rot == 90 or box_rot == 270:
                box.setRect(0, 0, box.height, box.width)
            else:
                box.setRect(0, 0, box.width, box.height)
            rotateCenter(box, -box_rot)
        else:
            name.setPos(sideCenter - nameRect.center())
        player.colorizeName()
        side.windTile.setWind(player.wind, self.game.roundsFinished)
        side.windTile.resetTransform()
        if box:
            side.windTile.setPos(box.rect().topRight() - QPointF(
                    side.windTile.rect().width(), 0))
        else:
            side.windTile.setPos(
                sideCenter.x()*1.63,
                sideCenter.y()-side.windTile.rect().height()/2.5)
        side.nameLabel.show()
        side.windTile.show()
