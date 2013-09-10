# -*- coding: utf-8 -*-

"""Copyright (C) 2009,2010 Wolfgang Rohdewald <wolfgang@rohdewald.de>
Copyright © 2013 Roland Sieker <ospalh@gmail.com>

kajongg is free software you can redistribute it and/or modifys
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

# See the user manual for a description of how to define rulesets.
# Names and descriptions must be english and may only contain ascii chars.
# Because kdecore.i18n() only accepts 8bit characters, no unicode.
# The KDE translation teams will "automatically" translate name and
# description into many languages.

from rule import PredefinedRuleset, Rule, Ruleset
from util import m18nE, m18n


class ClassicalChinese(PredefinedRuleset):

    """classical chinese rules, standard rules. Serves as a basis
    for local variants. This should be defined such that the
    sum of the differences to the local variants is minimized."""

    def __init__(self, name=None):
        PredefinedRuleset.__init__(self, name or m18nE('Classical Chinese standard'))

    def initRuleset(self):
        """sets the description"""
        self.description = m18n('Classical Chinese')

    def addManualRules(self):
        """those are actually winner rules but in the kajongg scoring mode they must be selected manually"""
        # applicable only if we have a concealed meld and a declared kong:
        self.winnerRules.add(Rule('Last Tile Taken from Dead Wall',
                'FLastTileFromDeadWall||Olastsource=e', doubles=1,
                description=m18n('The dead wall is also called kong box: The last 16 tiles of the wall '
                'used as source of replacement tiles')))
        self.winnerRules.add(Rule('Last Tile is Last Tile of Wall',
                'FIsLastTileFromWall||Olastsource=z', doubles=1,
                description=m18n('Winner said Mah Jong with the last tile taken from the living end of the wall')))
        self.winnerRules.add(Rule('Last Tile is Last Tile of Wall Discarded',
                'FIsLastTileFromWallDiscarded||Olastsource=Z', doubles=1,
                description=m18n('Winner said Mah Jong by claiming the last tile taken from the living end of the '
                'wall, discarded by another player')))
        self.winnerRules.add(Rule('Robbing the Kong', r'FRobbingKong||Olastsource=k', doubles=1,
                description=m18n('Winner said Mah Jong by claiming the 4th tile of a kong another player '
                'just declared'), debug=True))
        self.winnerRules.add(Rule('Mah Jongg with Original Call',
                'FMahJonggWithOriginalCall||Odeclaration=a', doubles=1,
                description=m18n(
                'Just before the first discard, a player can declare Original Call meaning she needs only one '
                'tile to complete the hand and announces she will not alter the hand in any way (except bonus tiles)')))
        self.winnerRules.add(Rule('Dangerous Game', 'FDangerousGame||Opayforall',
                description=m18n('In some situations discarding a tile that has a high chance to help somebody to win '
                'is declared to be dangerous, and if that tile actually makes somebody win, the discarder '
                'pays the winner for all')))
        self.winnerRules.add(Rule('Twofold Fortune', 'FTwofoldFortune||Odeclaration=t',
                limits=1, description=m18n('Kong after Kong: Declare Kong and a second Kong with the replacement '
                'tile and Mah Jong with the second replacement tile')))
        # limit hands:
        self.winnerRules.add(Rule('Blessing of Heaven', 'FBlessingOfHeaven||Olastsource=1', limits=1,
                description=m18n('East says Mah Jong with the unmodified dealt tiles')))
        self.winnerRules.add(Rule('Blessing of Earth', 'FBlessingOfEarth||Olastsource=1', limits=1,
                description=m18n('South, West or North says Mah Jong with the first tile discarded by East')))
        # the next rule is never proposed, the program applies it when appropriate. Do not change the XEAST9X.
        # XEAST9X is meant to never match a hand, and the program will identify this rule by searching for XEAST9X
        self.winnerRules.add(Rule('East won nine times in a row', r'XEAST9X', limits=1,
                description=m18n('If that happens, East gets a limit score and the winds rotate')))
    def addPenaltyRules(self):
        """as the name says"""
        self.penaltyRules.add(Rule(
                'False Naming of Discard, Claimed for Mah Jongg and False Declaration of Mah Jongg',
                'Oabsolute payers=2 payees=2', points = -300))

    def addHandRules(self):
        """as the name says"""
        self.handRules.add(Rule('Own Flower and Own Season', 'FOwnFlowerOwnSeason', doubles=1))
        self.handRules.add(Rule('All Flowers', 'FAllFlowers', doubles=1))
        self.handRules.add(Rule('All Seasons', 'FAllSeasons', doubles=1))
        self.handRules.add(Rule('Three Concealed Pongs', 'FThreeConcealedPongs', doubles=1))
        self.handRules.add(Rule('Long Hand', r'FLongHand||Oabsolute', points=0,
                description=m18n('The hand contains too many tiles')))

    def addParameterRules(self):
        """as the name says"""
        self.parameterRules.add(Rule('Points Needed for Mah Jongg', 'intminMJPoints||Omandatory', parameter=0))
        self.parameterRules.add(Rule('Minimum number of doubles needed for Mah Jongg',
                'intminMJDoubles||OMandatory', parameter=0))
        self.parameterRules.add(Rule('Points for a Limit Hand', 'intlimit||Omandatory||Omin=1', parameter=500))
        self.parameterRules.add(Rule('Play with the roof off', 'boolroofOff||Omandatory', parameter=False,
                description=m18n('Play with no upper scoring limit')))
        self.parameterRules.add(Rule('Claim Timeout', 'intclaimTimeout||Omandatory', parameter=10))
        self.parameterRules.add(Rule('Size of Kong Box', 'intkongBoxSize||Omandatory', parameter=16,
                description=m18n('The Kong Box is used for replacement tiles when declaring kongs')))
        self.parameterRules.add(Rule('Play with Bonus Tiles', 'boolwithBonusTiles||OMandatory', parameter=True,
                description=m18n('Bonus tiles increase the luck factor')))
        self.parameterRules.add(Rule('Minimum number of rounds in game', 'intminRounds||OMandatory', parameter=4))
        self.parameterRules.add(Rule('number of allowed chows', 'intmaxChows||Omandatory', parameter=4,
                description=m18n('The number of chows a player may build')))
        self.parameterRules.add(Rule('must declare calling hand',
                'boolmustDeclareCallingHand||Omandatory', parameter=False,
                description=m18n('Mah Jongg is only allowed after having declared to have a calling hand')))

    def loadRules(self):
        """define the rules"""
        self.addParameterRules() # must be first!
        self.addPenaltyRules()
        self.addHandRules()
        self.addManualRules()
        self.winnerRules.add(Rule('Last Tile Completes Pair of 2..8', 'FLastTileCompletesPairMinor', points=2))
        self.winnerRules.add(Rule('Last Tile Completes Pair of Terminals or Honors',
                'FLastTileCompletesPairMajor', points=4))
        self.winnerRules.add(Rule('Last Tile is Only Possible Tile', 'FLastOnlyPossible', points=4))
        self.winnerRules.add(Rule('Won with Last Tile Taken from Wall', 'FLastFromWall', points=2))

        self.winnerRules.add(Rule('Zero Point Hand', 'FZeroPointHand', doubles=1,
                description=m18n('The hand has 0 basis points excluding bonus tiles')))
        self.winnerRules.add(Rule('No Chow', 'FNoChow', doubles=1))
        self.winnerRules.add(Rule('Only Concealed Melds', 'FOnlyConcealedMelds', doubles=1))
        self.winnerRules.add(Rule('False Color Game', 'FFalseColorGame', doubles=1,
                description=m18n('Only same-colored tiles (only bamboo/stone/character) '
                'plus any number of winds and dragons')))
        self.winnerRules.add(Rule('True Color Game', 'FTrueColorGame', doubles=3,
                description=m18n('Only same-colored tiles (only bamboo/stone/character)')))
        self.winnerRules.add(Rule('Concealed True Color Game', 'FConcealedTrueColorGame',
                limits=1, description=m18n('All tiles concealed and of the same suit, no honors')))
        self.winnerRules.add(Rule('Only Terminals and Honors', 'FOnlyMajors', doubles=1,
                description=m18n('Only winds, dragons, 1 and 9')))
        self.winnerRules.add(Rule('Only Honors', 'FOnlyHonors', limits=1,
                description=m18n('Only winds and dragons')))
        self.winnerRules.add(Rule('Hidden Treasure', 'FHiddenTreasure', limits=1,
                description=m18n('Only hidden Pungs or Kongs, last tile from wall')))
        self.winnerRules.add(Rule('Heads and Tails', 'FAllTerminals', limits=1,
                description=m18n('Only 1 and 9')))
        self.winnerRules.add(Rule('Fourfold Plenty', 'FFourfoldPlenty', limits=1,
                description=m18n('4 Kongs')))
        self.winnerRules.add(Rule('Three Great Scholars', 'FThreeGreatScholars', limits=1,
                description=m18n('3 Pungs or Kongs of dragons')))
        self.winnerRules.add(Rule('Four Blessings Hovering Over the Door',
                'FFourBlessingsHoveringOverTheDoor', limits=1,
                description=m18n('4 Pungs or Kongs of winds')))
        self.winnerRules.add(Rule('All Greens', 'FAllGreen', limits=1,
                description=m18n('Only green tiles: Green dragon and Bamboo 2,3,4,6,8')))
        self.winnerRules.add(Rule('Gathering the Plum Blossom from the Roof',
                'FGatheringPlumBlossomFromRoof', limits=1,
                description=m18n('Mah Jong with stone 5 from the dead wall')))
        self.winnerRules.add(Rule('Plucking the Moon from the Bottom of the Sea', 'FPluckingMoon', limits=1,
                description=m18n('Mah Jong with the last tile from the wall being a stone 1')))
        self.winnerRules.add(Rule('Scratching a Carrying Pole', 'FScratchingPole', limits=1,
                description=m18n('Robbing the Kong of bamboo 2')))

        # only hands matching an mjRule can win. Keep this list as short as
        # possible. If a special hand matches the standard pattern, do not put it here
        # All mjRule functions must have a winningTileCandidates() method
        self.mjRules.add(Rule('Standard Mah Jongg', 'FStandardMahJongg', points=20))
        self.mjRules.add(Rule('Nine Gates', 'FGatesOfHeaven||OlastExtra', limits=1,
                description=m18n('All tiles concealed of same color: Values 1-1-1-2-3-4-5-6-7-8-9-9-9 completed '
                'with another tile of the same color (from wall or discarded)')))
        self.mjRules.add(Rule('Thirteen Orphans', 'FThirteenOrphans||Omayrobhiddenkong', limits=1,
            description=m18n('13 single tiles: All dragons, winds, 1, 9 and a 14th tile building a pair '
            'with one of them')))

        # doubling melds:
        self.meldRules.add(Rule('Pung/Kong of Dragons', 'FDragonPungKong', doubles=1))
        self.meldRules.add(Rule('Pung/Kong of Own Wind', 'FOwnWindPungKong', doubles=1))
        self.meldRules.add(Rule('Pung/Kong of Round Wind', 'FRoundWindPungKong', doubles=1))

        # exposed melds:
        self.meldRules.add(Rule('Exposed Kong', 'FExposedMinorKong', points=8))
        self.meldRules.add(Rule('Exposed Kong of Terminals', 'FExposedTerminalsKong', points=16))
        self.meldRules.add(Rule('Exposed Kong of Honors', 'FExposedHonorsKong', points=16))

        self.meldRules.add(Rule('Exposed Pung', 'FExposedMinorPung', points=2))
        self.meldRules.add(Rule('Exposed Pung of Terminals', 'FExposedTerminalsPung', points=4))
        self.meldRules.add(Rule('Exposed Pung of Honors', 'FExposedHonorsPung', points=4))

        # concealed melds:
        self.meldRules.add(Rule('Concealed Kong', 'FConcealedMinorKong', points=16))
        self.meldRules.add(Rule('Concealed Kong of Terminals', 'FConcealedTerminalsKong', points=32))
        self.meldRules.add(Rule('Concealed Kong of Honors', 'FConcealedHonorsKong', points=32))

        self.meldRules.add(Rule('Concealed Pung', 'FConcealedMinorPung', points=4))
        self.meldRules.add(Rule('Concealed Pung of Terminals', 'FConcealedTerminalsPung', points=8))
        self.meldRules.add(Rule('Concealed Pung of Honors', 'FConcealedHonorsPung', points=8))

        self.meldRules.add(Rule('Pair of Own Wind', 'FOwnWindPair', points=2))
        self.meldRules.add(Rule('Pair of Round Wind', 'FRoundWindPair', points=2))
        self.meldRules.add(Rule('Pair of Dragons', 'FDragonPair', points=2))

        # bonus tiles:
        self.meldRules.add(Rule('Flower', 'FFlower', points=4))
        self.meldRules.add(Rule('Season', 'FSeason', points=4))

class ClassicalChineseDMJL(ClassicalChinese):
    """classical chinese rules, German rules"""

    def __init__(self, name=None):
        ClassicalChinese.__init__(self, name or m18nE('Classical Chinese DMJL'))

    def initRuleset(self):
        """sets the description"""
        ClassicalChinese.initRuleset(self)
        self.description = m18n('Classical Chinese as defined by the Deutsche Mah Jongg Liga (DMJL) e.V.')

    def loadRules(self):
        ClassicalChinese.loadRules(self)
        # the squirming snake is only covered by standard mahjongg rule if tiles are ordered
        self.mjRules.add(Rule('Squirming Snake', 'FSquirmingSnake', limits=1,
                description=m18n('All tiles of same color. Pung or Kong of 1 and 9, pair of 2, 5 or 8 and two '
                'Chows of the remaining values')))
        self.handRules.add(Rule('Little Three Dragons', 'FLittleThreeDragons', doubles=1,
                description=m18n('2 Pungs or Kongs of dragons and 1 pair of dragons')))
        self.handRules.add(Rule('Big Three Dragons', 'FBigThreeDragons', doubles=2,
                description=m18n('3 Pungs or Kongs of dragons')))
        self.handRules.add(Rule('Little Four Joys', 'FLittleFourJoys', doubles=1,
                description=m18n('3 Pungs or Kongs of winds and 1 pair of winds')))
        self.handRules.add(Rule('Big Four Joys', 'FBigFourJoys', doubles=2,
                description=m18n('4 Pungs or Kongs of winds')))

        self.winnerRules['Only Honors'].doubles = 2

        self.penaltyRules.add(Rule('False Naming of Discard, Claimed for Chow', points = -50))
        self.penaltyRules.add(Rule('False Naming of Discard, Claimed for Pung/Kong', points = -100))
        self.penaltyRules.add(Rule('False Declaration of Mah Jongg by One Player',
                'Oabsolute payees=3', points = -300))
        self.penaltyRules.add(Rule('False Declaration of Mah Jongg by Two Players',
                'Oabsolute payers=2 payees=2', points = -300))
        self.penaltyRules.add(Rule('False Declaration of Mah Jongg by Three Players',
                'Oabsolute payers=3', points = -300))
        self.penaltyRules.add(Rule('False Naming of Discard, Claimed for Mah Jongg',
                'Oabsolute payees=3', points = -300))

class ClassicalChineseBMJA(ClassicalChinese):
    """classical chinese rules, British rules"""

    def __init__(self, name=None):
        ClassicalChinese.__init__(self, name or m18nE('Classical Chinese BMJA'))

    def initRuleset(self):
        """sets the description"""
        ClassicalChinese.initRuleset(self)
        self.description = m18n('Classical Chinese as defined by the British Mah-Jong Association')

    def addParameterRules(self):
        """those differ for BMJA from standard"""
        ClassicalChinese.addParameterRules(self)
        self.parameterRules['Size of Kong Box'].parameter = 14
        self.parameterRules['number of allowed chows'].parameter = 1
        self.parameterRules['Points for a Limit Hand'].parameter = 1000
        self.parameterRules['must declare calling hand'].parameter = True

    def loadRules(self):
# TODO: we need a separate part for any number of announcements. Both r for robbing kong and a for
# Original Call can be possible together.
        ClassicalChinese.loadRules(self)
        del self.winnerRules['Zero Point Hand']
        originalCall = self.winnerRules.pop('Mah Jongg with Original Call')
        originalCall.name = m18nE('Original Call')
        self.handRules.add(originalCall)
        del self.mjRules['Nine Gates']
        self.mjRules.add(Rule('Gates of Heaven', 'FGatesOfHeaven||Opair28', limits=1,
                description=m18n('All tiles concealed of same color: Values 1-1-1-2-3-4-5-6-7-8-9-9-9 and '
                'another tile 2..8 of the same color')))
        self.mjRules.add(Rule('Wriggling Snake', 'FWrigglingSnake', limits=1,
                description=m18n('Pair of 1s and a run from 2 to 9 in the same suit with each of the winds')))
        self.mjRules.add(Rule('Triple Knitting', 'FTripleKnitting', limits=0.5,
                description=m18n('Four sets of three tiles in the different suits and a pair: No Winds or Dragons')))
        self.mjRules.add(Rule('Knitting', 'FKnitting', limits=0.5,
                description=m18n('7 pairs of tiles in any 2 out of 3 suits; no Winds or Dragons')))
        self.mjRules.add(Rule('All pair honors', 'FAllPairHonors', limits=0.5,
                description=m18n('7 pairs of 1s/9s/Winds/Dragons')))
        del self.handRules['Own Flower and Own Season']
        del self.handRules['Three Concealed Pongs']
        self.handRules.add(Rule('Own Flower', 'FOwnFlower', doubles=1))
        self.handRules.add(Rule('Own Season', 'FOwnSeason', doubles=1))
        del self.winnerRules['Last Tile Taken from Dead Wall']
        del self.winnerRules['Hidden Treasure']
        del self.winnerRules['False Color Game']
        del self.winnerRules['Concealed True Color Game']
        del self.winnerRules['East won nine times in a row']
        del self.winnerRules['Last Tile Completes Pair of 2..8']
        del self.winnerRules['Last Tile Completes Pair of Terminals or Honors']
        del self.winnerRules['Last Tile is Only Possible Tile']
        self.winnerRules.add(Rule('Buried Treasure', 'FBuriedTreasure', limits=1,
                description=m18n('Concealed pungs of one suit with winds/dragons and a pair')))
        del self.winnerRules['True Color Game']
        self.winnerRules.add(Rule('Purity', 'FPurity', doubles=3,
                description=m18n('Only same-colored tiles (no chows, dragons or winds)')))
        self.winnerRules['All Greens'].name = m18nE('Imperial Jade')
        self.mjRules['Thirteen Orphans'].name = m18nE('The 13 Unique Wonders')
        del self.winnerRules['Three Great Scholars']
        self.winnerRules.add(Rule('Three Great Scholars', 'FThreeGreatScholars||Onochow', limits=1,
                description=m18n('3 Pungs or Kongs of dragons plus any pung/kong and a pair')))
        self.handRules['All Flowers'].score.doubles = 2
        self.handRules['All Seasons'].score.doubles = 2
        self.penaltyRules.add(Rule('False Naming of Discard, Claimed for Chow/Pung/Kong', points = -50))
        self.penaltyRules.add(Rule('False Declaration of Mah Jongg by One Player',
                'Oabsolute payees=3', limits = -0.5))
        self.winnerRules.add(Rule('False Naming of Discard, Claimed for Mah Jongg', 'FFalseDiscardForMJ||Opayforall'))

        self.loserRules.add(Rule('Calling for Only Honors', 'FCallingHand||Ohand=OnlyHonors', limits=0.4))
        self.loserRules.add(Rule('Calling for Wriggling Snake', 'FCallingHand||Ohand=WrigglingSnake', limits=0.4))
        self.loserRules.add(Rule('Calling for Triple Knitting', 'FCallingHand||Ohand=TripleKnitting', limits=0.2))
        self.loserRules.add(Rule('Calling for Gates of Heaven', 'FCallingHand||Ohand=GatesOfHeaven||Opair28',
                limits=0.4))
        self.loserRules.add(Rule('Calling for Knitting', 'FCallingHand||Ohand=Knitting', limits=0.2))
        self.loserRules.add(Rule('Calling for Imperial Jade', 'FCallingHand||Ohand=AllGreen', limits=0.4))
        self.loserRules.add(Rule('Calling for 13 Unique Wonders', 'FCallingHand||Ohand=ThirteenOrphans',
                limits=0.4))
        self.loserRules.add(Rule('Calling for Three Great Scholars', 'FCallingHand||Ohand=ThreeGreatScholars',
                limits=0.4))
        self.loserRules.add(Rule('Calling for All pair honors', 'FCallingHand||Ohand=AllPairHonors', limits=0.2))
        self.loserRules.add(Rule('Calling for Heads and Tails', 'FCallingHand||Ohand=AllTerminals', limits=0.4))
        self.loserRules.add(Rule('Calling for Four Blessings Hovering over the Door',
                'FCallingHand||Ohand=FourBlessingsHoveringOverTheDoor', limits=0.4))
        self.loserRules.add(Rule('Calling for Buried Treasure', 'FCallingHand||Ohand=BuriedTreasure', limits=0.4))
        self.loserRules.add(Rule('Calling for Fourfold Plenty', 'FCallingHand||Ohand=FourfoldPlenty', limits=0.4))
        self.loserRules.add(Rule('Calling for Purity', 'FCallingHand||Ohand=Purity', doubles=3))


class JapaneseStyleRuleset(PredefinedRuleset):
    """
    Ruleset for Japanese style mahjong.

    This is a work in progress. The goal is to implement complete
    Riichi mahjong. At the moment this only implement those things
    that can be easily addapted from the existing rules.
    """

    def __init__(self, name=None):
        u"""Initialize the rules."""
        PredefinedRuleset.__init__(
            self, name or m18nE(u'Japanese style rules'))
        self.basicStyle = Ruleset.Japanese

    def initRuleset(self):
        """Sets the description"""
        self.description = m18n(u'Japanese style rules (work in progress)')

    def addManualRules(self):
        u"""
        Add manual winner rules.

        Those are actually winner rules but in the kajongg scoring
        mode they must be selected manually.
        """
        self.winnerRules.add(Rule(
                'After a kong', 'FLastTileFromDeadWall||Olastsource=e',
                doubles=1, description=m18n(u'''\
Winning on a replacement tile after declaring a kong. Counts as self-draw. \
(Rinshan kaihou)''')))
        self.winnerRules.add(Rule(
                'Robbing the kong', r'FRobbingKong||Olastsource=k', doubles=1,
                description=m18n(
                    'Mahjong when a pung is extended to kong (Chan kan)'),
                debug=True))
        self.winnerRules.add(Rule(
                'Bottom of the sea (tsumo)',
                'FIsLastTileFromWall||Olastsource=z', doubles=1,
                description=m18n(u'''\
Selfdraw mahjong on the last tile of the wall. (Haitei)''')))
        self.winnerRules.add(Rule(
                'Bottom of the sea (ron)',
                'FIsLastTileFromWallDiscarded||Olastsource=Z', doubles=1,
                description=m18n('''\
Mahjong on the discard after the last tile in the wall. (Houtei)''')))

        # self.winnerRules.add(Rule('Mah Jongg with Original Call',
        #         'FMahJonggWithOriginalCall||Odeclaration=a', doubles=1,
        #         description=m18n('''\
        # NB. THe original call code can be used as inspiration for
        # riichi code''')))
        # Yakuman (Japanese style limit) hands. The scoring is done
        # with a table, so the 13 is kind of meaningless.
        self.winnerRules.add(Rule(
                'Blessing of Heaven', 'FBlessingOfHeaven||Olastsource=1',
                doubles=13, description=m18n(
                    'East mahjong on initial fourteen tiles (Tenho)')))
        self.winnerRules.add(Rule(
                'Blessing of Earth', 'FBlessingOfEarth||Olastsource=1',
                doubles=13, description=m18n(
                    'Mahjong on selfdraw in the first round (Chiho)')))
        # Japanese Blessing of Earth may need to get its own rule, to
        # make sure nobody has called anything.
        # self.winnerRules.add(
        #     Rule('Blessing of Man', 'FBlessingOfMan||Olastsource=1',
        #          doubles=13,
        #          description=m18n(
        #             'Mahjong on discard in the first round (Renho)')))

    def addPenaltyRules(self):
        """Set penalty rules"""
        # There are two types of penalty the software can deal with in
        # theory, dead hand and chombo. TODO.
        self.penaltyRules.add(Rule(
                'Long Hand', r'FLongHand||Oabsolute', points=0, doubles=0,
                description=m18n('The hand contains too many tiles')))
        # Too many tiles is one example of a dead hand.
        # Maybe we can add the “fed fourth wind pung/third dragon
        # pung” here.

    def addHandRules(self):
        """Define rules for the hand. They are not used for Japaneses style."""
        pass

    def loadRules(self):
        """
        Load the rules.

        Load the rules. A lot of these are basically the same as the
        Chinese rules, but with different names. The names used here
        are taken from the English European Mahjong Association (EMA)
        Riichi rules.
        """
        self.addParameterRules()  # must be first!
        self.addPenaltyRules()
        self.addManualRules()

        # Only hands matching an mjRule can win. Keep this list as
        # short as possible. If a special hand matches the standard
        # pattern, do not put it here All mjRule functions must have a
        # winningTileCandidates() method
        self.mjRules.add(Rule(
                'Standard mahjong', 'FStandardMahJongg', points=20))
        self.mjRules.add(Rule(
                'Standard concealed ron', 'FStandardConcealedRon', points=30))
        self.mjRules.add(Rule(
                'Seven pairs', 'FSevenPairs||Ono_other_points', doubles=2,
                points=25))
        # New option no_other_points. “Seven Pairs always scores
        # exactly 25 minipoints; extra minipoints (fu) for e.g. a pair of
        # dragons is not awarded.” This is different from Oabsolute,
        # as extra han are counted (afais).
        self.mjRules.add(Rule(
                'Thirteen Orphans', 'FThirteenOrphans||Omayrobhiddenkong',
                doubles=13, description=m18n('''\
Concealed hand with one of each of the 13 different terminal and honour tiles \
plus one extra terminal or honour tile. (Kokushi musou)''')))
        self.mjRules.add(Rule(
                'Nine Gates', 'FGatesOfHeaven||OlastExtra', doubles=13,
                description=m18n('''\
Concealed hand consisting of the tiles 1112345678999 in the same suit plus \
any one extra tile in the same suit. (Chuuren pooto)''')))

        # The list of yaku, from 1 to 13.
        # One yaku (Some are two yaku when concealed.)
        # self.winnerRules.add(
        #     Rule('Riichi', 'FRiichi', doubles=1,
        #          description=m18n(u'''\
# Concealed waiting hand declared at 1000 points stake. (Riichi)''')))
        self.winnerRules.add(Rule(
                'Fully concelaned hand', 'FOnlyConcealedMelds', doubles=1,
                description=m18n(
                    u'Selfdraw on a concealed hand (Menzen tsumo)')))

        self.winnerRules.add(
            Rule('All simples', 'FAllSimples', doubles=1,
                 description=m18n(u'''\
Concealed hand with no terminals and honours. (Tanyao chuu)''')))
        # self.winnerRules.add(
        #     Rule('All simples', 'FAllSimples||Omay_be_open', doubles=1,
        #         description=m18n(u'''\
# Hand with no terminals and honours. (Tanyao chuu)''')))

        # self.winnerRules.add(
        #     Rule('Pinfu', 'FPinfu||Ono_other_points', doubles=1
        #          description=m18n(
        #             ' Concealed all chows hand with a valueless pair.')))
        # N.B.: the appliesToHand and Candidate functions must
        # implement the two-sided wait condition.

        self.winnerRules.add(
            Rule('Pure double chow', 'FPureDoubleChow', doubles=1,
                  description=m18n(u'''\
Concealed hand with two completely identical chows, i.e. the same \
values in the same suit. (Iipeikou) ''')))
        self.winnerRules.add(
            Rule('Mixed triple chow', 'FTripleChow', doubles=1,
                 description=m18n(u'''\
Hand with three chows of the same numerical sequence, one in each \
suit.  (San shoku doujun) ''')))
        self.winnerRules.add(
             Rule('Concealed mixed triple chow bonus', 'FTripleChowBonus',
                  doubles=1, description=m18n(u'''\
Bonus yaku for a mixed triple chow hand being concealed. \
(San shoku doujun)''')))
        self.winnerRules.add(
            Rule('Pure straight', 'FPureStraight', doubles=1,
                 description=u'''\
Hand with three consecutive chows in the same suit. (Itsu)'''))
        self.winnerRules.add(
             Rule('Concealed pure straight bonus', 'FPureStraightBonus',
                  doubles=1, description=m18n(u'''\
Bonus yaku for a pure straight hand being concealed. \
(Itsu)''')))
        # self.winnerRules.add(
        #     Rule('Open outside hand', 'FOutsideHand', doubles=1,
        #     description=m18n('''\
# All sets contain terminals or honours, and the pair is \
# terminals or honours. The hand contains at least one chow. (Chanta)''')))
        # self.winnerRules.add(
        #     Rule('Concealend outside hand bonus', 'FOutsideHandBonus',
        #    doubles=1, description=m18n('''\
# Bonus yaku for an outside hand being concealed. (Chanta)''')))

        # Four more one-yake are in addManualRules(), as you can’t
        # recoginze them from just the tiles:
        # * After a kong
        # * Robbing the kong
        # * Under the sea, ron
        # * Under the sea, tsumo

        # Two yaku hands:
        # Seven pairs is at mjRules above

        # self.winnerRules.add(
        #     Rule('Triple pung', 'FTriplePung', doubles=2,
        #          description=u'''\
# Hand with three pungs/kongs, one in each suit, of the same
# number. (San shoku dokou)'''))
        self.winnerRules.add(Rule(
                'Three concealend pungs', 'FThreeConcealedPungsOrKongs',
                doubles=2, description=m18n(u'''\
Hand with three hidden pungs. (Complete hand may be open.) (San ankou)''')))
        self.winnerRules.add(Rule(
                'All pungs', 'FAllPungs', doubles=2, description=u'''\
Hand with four pungs/kongs and a pair. (Toi-toi hou)'''))
        self.winnerRules.add(Rule(
                'Half flush', 'FFalseColorGame', doubles=2,
                description=m18n('''\
Hand with tiles from only one of the three suits, in combination with \
honours. (Honitsu) ''')))
        self.winnerRules.add(
            Rule('Concealed half flush bonus', 'FHalfFlushBonus',
                 doubles=1, description=m18n('''\
Bonus yaku for a half flush hand being concealed. (Honitsu) ''')))
        self.handRules.add(Rule(
                'Little three dragons', 'FLittleThreeDragons', doubles=2,
                description=m18n(u'''\
Hand with two dragon pungs/kongs and a pair of dragons. (Shou sangen)''')))
        self.winnerRules.add(Rule(
                'All terminals and honours', 'FOnlyMajors', doubles=2,
                 description=m18n(u'''\
Hand containing only terminals and honours. (Honroutou)''')))
        # self.winnerRules.add(
        #     Rule('Terminals in all sets', 'FOnlyMajors', doubles=2,
        #          description=m18n(u'''\
# Hand containing only terminals and honours. (Honroutou)''')))

        # Three yaku

        # N.B. EMA lists “Twice Pure Double Chows” as three yaku and
        # notes that “(n)o additional yaku for Pure Double Chow
        # (IIPEIKOU) are counted”. Scoring it as iipeikou + iipeikou +
        # this seems simpler for a computer program.
        #    Rule('Two sets of  pure double chows',
        #           'FTwicePureDoubleChow', doubles=1,
        #          description=m18n(u'''\
# Bonus yaku for two pure double chow/Iipeikou, counted separately. \
# (Ryan peikou) ''')))

        # Five yaku (Starting at five fan (yaku + dora) the
        # fu/minipoints/points are always ignored)
        self.winnerRules.add(Rule(
                'Full flush', 'FTrueColorGame', doubles=5,
                description=m18n('''\
Hand composed entirely of tiles from only one of the three suits. No \
honours allowed. (Chinitsu)''')))
        self.winnerRules.add(
            Rule('Concealed full flush bonus', 'FFullFlushBonus',
                 doubles=1, description=m18n('''\
Bonus yaku for a full flush hand being concealed. (Chinitsu)''')))

        # Nagashi mangan is dealt with during scoring. Maybe we can
        # use the nine east wins as inspiration.

        # The Yakuman (thirteen yaku) hands
        # Thirteen Orphans and  Nine Gates are at mjRules above.
        # The Blessings of NN (first round win) are at manualRules,
        # as they have to be checked by hand for manual scoring.

        # The extra “rule” “Winning on a discard is allowed only in
        # case of single wait on the pair.” for “Four concealed pungs”
        # is actually a tautology. When you call any of the four
        # pungs, even as the last tile, that last pung is not
        # concealed, even if the whole hand is concealed*.
        self.winnerRules.add(Rule(
                'Four concealed pungs', 'FFourConcealedPungsOrKongs',
                doubles=13, description=m18n(
                    'Concealend hand with four pungs/kongs (Suu ankou)')))
        self.winnerRules.add(Rule(
                'Four kongs', 'FFourfoldPlenty', doubles=13,
                description=m18n('Hand with four kongs (Suu kan tsu)')))
        self.winnerRules.add(Rule(
                'All green', 'FAllGreen',  doubles=13, description=m18n(
                    u''' Hand composed entirely of green tiles. Green tiles \
are: green dragons 2, 3, 4, 6 and 8 of bamboo (Ryuu iisou)''')))
        self.winnerRules.add(Rule(
                'All terminals', 'FAllTerminals', doubles=13, description=m18n(
                    'Hand composed entirely of terminal tiles. (Chinrouto)')))
        self.winnerRules.add(Rule(
                'All Honours', 'FOnlyHonors', doubles=13, description=m18n(
                    'Hand composed entirely of honour tiles. (Tsuu iisou)')))
        self.winnerRules.add(Rule(
                'Big three dragons', 'FBigThreeDragons', doubles=13,
                description=m18n(
                    ' Hand with three pungs/kongs of dragons. (Dai sangen)')))
        self.winnerRules.add(Rule(
                'Little four winds', 'FLittleFourJoys', doubles=13,
                description=m18n(u'''\
Hand with three pungs/kongs of winds and a pair of . (Shou suushi)''')))
        self.winnerRules.add(Rule(
                'Big four winds', 'FBigFourJoys', doubles=26,
                description=m18n(u'''\
Hand with three pungs/kongs of winds and a pair of. Double yakuman. \
(Dai suushi)''')))

        # Here we should add the waiting pattern rules.
        # and the 2 (read 10) open(!) pinfu points.
        # self.winnerRules.add(
        #     Rule('Last Tile Completes Pair of 2..8',
        #          'FLastTileCompletesPairMinor', points=2))

        # Points for the hand.
        # First the yaku melds
        self.meldRules.add(Rule(
                'Dragons pung', 'FDragonPungKong', doubles=1, description=m18n(
                    u'Pung/kong of dragons (Fanpai)')))
        self.meldRules.add(Rule(
                'Seat wind pung', 'FOwnWindPungKong', doubles=1,
                description=m18n(
                    u'Pung/kong of the seat wind (Fanpai)')))
        self.meldRules.add(Rule(
                'Prevailing wind pung', 'FRoundWindPungKong', doubles=1,
                description=m18n(
                    u'Pung/kong of the seat wind (Fanpai)')))
        # And the non-yaku melds
        self.meldRules.add(
            Rule(u'Open kong, 2–8', 'FExposedMinorKong', points=8))
        self.meldRules.add(
            Rule('Open kong, terminals', 'FExposedTerminalsKong', points=16))
        self.meldRules.add(
            Rule('Open kong, honours', 'FExposedHonorsKong', points=16))
        self.meldRules.add(
            Rule(u'Open pung, 2–8', 'FExposedMinorPung', points=2))
        self.meldRules.add(
            Rule('Open pung, terminals', 'FExposedTerminalsPung', points=4))
        self.meldRules.add(
            Rule('Open pung, honours', 'FExposedHonorsPung', points=4))
        # Concealed melds:
        self.meldRules.add(
            Rule(u'Concealed kong, 2–8', 'FConcealedMinorKong', points=16))
        self.meldRules.add(Rule(
                'Concealed kong, terminals', 'FConcealedTerminalsKong',
                points=32))
        self.meldRules.add(
            Rule('Concealed kong, honours', 'FConcealedHonorsKong', points=32))
        self.meldRules.add(
            Rule(u'Concealed pung, 2–8', 'FConcealedMinorPung', points=4))
        self.meldRules.add(Rule(
                'Concealed pung, terminals', 'FConcealedTerminalsPung',
                points=8))
        self.meldRules.add(
            Rule('Concealed pung, honours', 'FConcealedHonorsPung', points=8))
        self.meldRules.add(
            Rule('Pair of seat wind', 'FOwnWindPair', points=2))
        self.meldRules.add(
            Rule('Pair of prevailing wind', 'FRoundWindPair', points=2))
        self.meldRules.add(Rule('Pair of dragons', 'FDragonPair', points=2))

    def addParameterRules(self):
        u"""
        Set some parameters.

        Some general parameters. For most of them it doesn’t make much
        sense to change them. Some values make no sense at all here,
        so they are just hard-coded in to some value.
        """
        # The hard-coded parameters
        self.limit = 500  # There are no limit hands in the Chinese sense
        self.roofOff = True  # So we don’t worry about roofs
        self.kongBoxSize = 14
        # Each of the 14 stones in the dead wall may be used. It MUST
        # NOT be <14. Setting it to >14 could work, but doing a range
        # check here is too much hassle. Oh. and it is a dead wall,
        # that should be replenished. TODO.
        self.parameterRules.add(Rule(
                'Minipoints (fu) needed to win', 'intminMJPoints||Omandatory',
                parameter=0))
        self.parameterRules.add(Rule(
                'Minimum number of yaku (doubles) needed to win',
                'intminMJDoubles||OMandatory', parameter=0))
        # This should be 1. Until we have riichi declaration up and
        # running, use 0 instead.
        self.parameterRules.add(
            Rule('Claim Timeout', 'intclaimTimeout||Omandatory', parameter=5))
        # The EMA rules say 3s. May be too quick for beginners.
        self.parameterRules.add(Rule(
                'Play with Bonus Tiles', 'boolwithBonusTiles||OMandatory',
                parameter=False, description=m18n(
                    'Japanese mahjong is played without bonus tiles.')))
        self.parameterRules.add(Rule(
                'Number of rounds in game', 'intminRounds||OMandatory',
                parameter=2, description=m18n(
                    'Only east and south wind rounds are played.')))
        self.parameterRules.add(Rule(
                'Number of allowed chows', 'intmaxChows||Omandatory',
                 parameter=4, description=m18n(
                    u'Different yaku demand between two and four chows.')))
        self.parameterRules.add(Rule(
                'Must declare calling hand',
                'boolmustDeclareCallingHand||Omandatory', parameter=False,
                description=m18n(
                    'Only riichi must be declared.')))
        # self.parameterRules.add(Rule(
        #         u'“All simples” may be open.',
        #        'boolall_simples_may_be_open||Omandatory', parameter=False,
        #        description=m18n(u'''\
# Different Japanese rule codes do or do not require that the “All simples” \
# hand be concealed.''')))


def loadPredefinedRulesets():
    """add new predefined rulesets here"""
    if not PredefinedRuleset.classes:
        PredefinedRuleset.classes.add(ClassicalChineseDMJL)
        PredefinedRuleset.classes.add(ClassicalChineseBMJA)
        PredefinedRuleset.classes.add(JapaneseStyleRuleset)
