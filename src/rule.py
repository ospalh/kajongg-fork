# -*- coding: utf-8 -*-

"""Copyright (C) 2009-2012 Wolfgang Rohdewald <wolfgang@rohdewald.de>

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



Read the user manual for a description of the interface to this scoring engine
"""

import re # the new regex is about 7% faster
from hashlib import md5 # pylint: disable=E0611

from PyQt4.QtCore import QString, QVariant

from util import m18n, m18nc, m18nE, english, logException
from query import Query, Transaction

import rulecode

class Score(object):
    """holds all parts contributing to a score. It has two use cases:
    1. for defining what a rules does: either points or doubles or limits, holding never more than one unit
    2. for summing up the scores of all rules: Now more than one of the units can be in use. If a rule
    should want to set more than one unit, split it into two rules.
    For the first use case only we have the attributes value and unit"""

    __hash__ = None

    def __init__(self, points=0, doubles=0, limits=0, ruleset=None):
        self.points = 0 # define the types for those values
        self.doubles = 0
        self.limits = 0.0
        self.ruleset = ruleset
        self.points = type(self.points)(points)
        self.doubles = type(self.doubles)(doubles)
        self.limits = type(self.limits)(limits)

    unitNames = {m18nE('points'):0, m18nE('doubles'):50, m18nE('limits'):9999}

    def clear(self):
        """set all to 0"""
        self.points = self.doubles = self.limits = 0

    def change(self, unitName, value):
        """sets value for unitName. If changed, return True"""
        oldValue = self.__getattribute__(unitName)
        if isinstance(value, QVariant):
            value = value.toString()
        newValue = type(oldValue)(value)
        if newValue == oldValue:
            return False, None
        if newValue:
            if unitName == 'points':
                if self.doubles:
                    return False, 'Cannot have points and doubles'
            if unitName == 'doubles':
                if self.points:
                    return False, 'Cannot have points and doubles'
        self.__setattr__(unitName, newValue)
        return True, None

    def __str__(self):
        """make score printable"""
        parts = []
        if self.points:
            parts.append('points=%d' % self.points)
        if self.doubles:
            parts.append('doubles=%d' % self.doubles)
        if self.limits:
            parts.append('limits=%f' % self.limits)
        return ' '.join(parts)

    def __repr__(self):
        return 'Score(%s)' % str(self)

    def contentStr(self):
        """make score readable for humans, i18n"""
        parts = []
        if self.points:
            parts.append(m18nc('Kajongg', '%1 points', self.points))
        if self.doubles:
            parts.append(m18nc('Kajongg', '%1 doubles', self.doubles))
        if self.limits:
            parts.append(m18nc('Kajongg', '%1 limits', self.limits))
        return ' '.join(parts)

    def __eq__(self, other):
        """ == comparison """
        assert isinstance(other, Score)
        return self.points == other.points and self.doubles == other.doubles and self.limits == other.limits

    def __ne__(self, other):
        """ != comparison """
        return self.points != other.points or self.doubles != other.doubles or self.limits != other.limits

    def __lt__(self, other):
        return self.total() < other.total()

    def __le__(self, other):
        return self.total() <= other.total()

    def __gt__(self, other):
        return self.total() > other.total()

    def __ge__(self, other):
        return self.total() >= other.total()

    def __add__(self, other):
        """implement adding Score"""
        return Score(self.points + other.points, self.doubles+other.doubles,
            max(self.limits, other.limits), self.ruleset or other.ruleset)

    def total(self):
        """the total score"""
        if self.ruleset is None:
            raise Exception('Score.total: ruleset unknown for %s' % self)
        score = int(self.points * ( 2 ** self.doubles))
        if self.limits:
            if self.limits >= 1:
                self.points = self.doubles = 0
            elif self.limits * self.ruleset.limit >= score:
                self.points = self.doubles = 0
            else:
                self.limits = 0
        if self.limits:
            return int(round(self.limits * self.ruleset.limit))
        if not self.ruleset.roofOff:
            score = min(score, self.ruleset.limit)
        return score

    def __int__(self):
        """the total score"""
        return self.total()

    def __nonzero__(self):
        """for bool() conversion"""
        return self.points != 0 or self.doubles != 0 or self.limits != 0

class RuleList(list):
    """a list with a name and a description (to be used as hint).
    Rules can be indexed by name or index.
    Adding a rule either replaces an existing rule or appends it."""

    def __init__(self, listId, name, description):
        list.__init__(self)
        self.listId = listId
        self.name = name
        self.description = description

    def pop(self, name):
        """find rule, return it, delete it from this list"""
        result = self.__getitem__(name)
        self.__delitem__(name)
        return result

    def __getitem__(self, name):
        """find rule by name"""
        if isinstance(name, int):
            return list.__getitem__(self, name)
        for rule in self:
            if rule.name == name:
                return rule
        raise KeyError

    def __setitem__(self, name, rule):
        """set rule by name"""
        assert isinstance(rule, Rule)
        if isinstance(name, int):
            list.__setitem__(self, name, rule)
            return
        for idx, oldRule in enumerate(self):
            if oldRule.name == name:
                list.__setitem__(self, idx, rule)
                return
        list.append(self, rule)

    def __delitem__(self, name):
        """delete this rule"""
        if isinstance(name, int):
            list.__delitem__(self, name)
            return
        for idx, rule in enumerate(self):
            if rule.name == name:
                list.__delitem__(self, idx)
                return
        raise KeyError

    def append(self, rule):
        """do not append"""
        raise Exception('do not append %s' % rule)

    def add(self, rule):
        """use add instead of append"""
        self[rule.name] = rule

class Ruleset(object):
    """holds a full set of rules: splitRules,meldRules,handRules,winnerRules.

        predefined rulesets are preinstalled together with kajongg. They can be customized by the user:
        He can copy them and modify the copies in any way. If a game uses a specific ruleset, it
        checks the used rulesets for an identical ruleset and refers to that one, or it generates
        a new used ruleset.

        The user can select any predefined or customized ruleset for a new game, but she can
        only modify customized rulesets.

        For fast comparison for equality of two rulesets, each ruleset has a hash built from
        all of its rules. This excludes the splitting rules, IOW exactly the rules saved in the table
        rule will be used for computation.

        Rulesets which are templates for new games have negative ids.
        Rulesets attached to a game have positive ids.

        The name is not unique.
    """
    # pylint: disable=R0902
    # pylint we need more than 10 instance attributes

    __hash__ = None

    cache = dict()
    hits = 0
    misses = 0

    @staticmethod
    def clearCache():
        """clears the cache with Rulesets"""
        Ruleset.cache.clear()

    @staticmethod
    def cached(name):
        """If a Ruleset instance is never changed, we can use a cache"""
        if isinstance(name, list):
            # we got the rules over the wire
            _, name, _, _ = name[0] # copy its hash into name
        for predefined in PredefinedRuleset.rulesets():
            if predefined.hash == name:
                return predefined
        cache = Ruleset.cache
        if not isinstance(name, list) and name in cache:
            return cache[name]
        result = Ruleset(name)
        cache[result.rulesetId] = result
        cache[result.hash] = result
        return result

    def __init__(self, name):
        """name may be:
            - an integer: ruleset.id from the sql table
            - a list: the full ruleset specification (probably sent from the server)
            - a string: The hash value of a ruleset"""
        self.name = name
        self.rulesetId = 0
        self.__hash = None
        self.allRules = []
        self.__dirty = False # only the ruleset editor is supposed to make us dirty
        self.__loaded = False
        self.__filteredLists = {}
        self.description = None
        self.rawRules = None # used when we get the rules over the network
        self.splitRules = []
        self.doublingMeldRules = []
        self.doublingHandRules = []
        self.meldRules = RuleList(1, m18n('Meld Rules'),
            m18n('Meld rules are applied to single melds independent of the rest of the hand'))
        self.handRules = RuleList(2, m18n('Hand Rules'),
            m18n('Hand rules are applied to the entire hand, for all players'))
        self.winnerRules = RuleList(3, m18n('Winner Rules'),
            m18n('Winner rules are applied to the entire hand but only for the winner'))
        self.loserRules = RuleList(33, m18n('Loser Rules'),
            m18n('Loser rules are applied to the entire hand but only for non-winners'))
        self.mjRules = RuleList(4, m18n('Mah Jongg Rules'),
            m18n('Only hands matching a Mah Jongg rule can win'))
        self.parameterRules = RuleList(999, m18nc('kajongg','Options'),
            m18n('Here we have several special game related options'))
        self.penaltyRules = RuleList(9999, m18n('Penalties'), m18n(
            """Penalties are applied manually by the user. They are only used for scoring games.
When playing against the computer or over the net, Kajongg will never let you get
into a situation where you have to pay a penalty"""))
        self.ruleLists = list([self.meldRules, self.handRules, self.mjRules, self.winnerRules,
            self.loserRules, self.parameterRules, self.penaltyRules])
        # the order of ruleLists is the order in which the lists appear in the ruleset editor
        # if you ever want to remove an entry from ruleLists: make sure its listId is not reused or you get
        # in trouble when updating
        self._initRuleset()

    @property
    def dirty(self):
        """have we been modified since load or last save?"""
        return self.__dirty

    @dirty.setter
    def dirty(self, dirty):
        """have we been modified since load or last save?"""
        self.__dirty = dirty
        if dirty:
            self.__computeHash()

    @property
    def hash(self):
        """a md5sum computed from the rules but not name and description"""
        if not self.__hash:
            self.__computeHash()
        return self.__hash


    def __eq__(self, other):
        """two rulesets are equal if everything except name or description is identical.
        The name might be localized."""
        return self.hash == other.hash

    def minMJTotal(self):
        """the minimum score for Mah Jongg including all winner points. This is not accurate,
        the correct number is bigger in CC: 22 and not 20. But it is enough saveguard against
        entering impossible scores for manual games.
        We only use this for scoring games."""
        return self.minMJPoints + min(x.score.total() for x in self.mjRules)

    @staticmethod
    def hashIsKnown(value):
        """returns False or True"""
        result = any(x.hash == value for x in PredefinedRuleset.rulesets())
        if not result:
            query = Query("select id from ruleset where hash=?", list([value]))
            result = bool(query.records)
        return result

    def _initRuleset(self):
        """load ruleset headers but not the rules"""
        if isinstance(self.name, int):
            query = Query("select id,hash,name,description from ruleset where id=%d" % self.name)
        elif isinstance(self.name, list):
            # we got the rules over the wire
            self.rawRules = self.name[1:]
            (self.rulesetId, self.__hash, self.name, self.description) = self.name[0]
            self.load() # load raw rules at once, rules from db only when needed
            return
        else:
            query = Query("select id,hash,name,description from ruleset where hash=?",
                          list([self.name]))
        if len(query.records):
            (self.rulesetId, self.__hash, self.name, self.description) = query.records[0]
        else:
            raise Exception('ruleset %s not found' % self.name)

    def load(self):
        """load the ruleset from the database and compute the hash. Return self."""
        if self.__loaded:
            return self
        self.__loaded = True
        # we might have introduced new mandatory rules which do
        # not exist in the rulesets saved with the games, so preload
        # the default values from any predefined ruleset:
        # TODO: the ruleset should know from which predefined ruleset it
        # has been copied - use that one. For now use sorted() here to
        # avoid random differences
        if self.rulesetId: # a saved ruleset, do not do this for predefined rulesets
            predefRuleset = sorted(PredefinedRuleset.rulesets())[0]
            predefRuleset.load()
            for par in predefRuleset.parameterRules:
                self.__dict__[par.parName] = par.parameter
        self.loadSplitRules()
        self.loadRules()
        for par in self.parameterRules:
            self.__dict__[par.parName] = par.parameter
        for ruleList in self.ruleLists:
            for rule in ruleList:
                rule.score.ruleset = self
                self.allRules.append(rule)
        self.doublingMeldRules = list(x for x in self.meldRules if x.score.doubles)
        self.doublingHandRules = list(x for x in self.handRules if x.score.doubles)
        return self

    def __loadQuery(self):
        """returns a Query object with loaded ruleset"""
        return Query(
            "select ruleset, name, list, position, definition, points, doubles, limits, parameter from rule "
                "where ruleset=%d order by list,position" % self.rulesetId)

    def toList(self):
        """returns entire ruleset encoded in a string"""
        self.load()
        result = [[self.rulesetId, self.hash, self.name, self.description]]
        result.extend(self.ruleRecord(x) for x in self.allRules)
        return result

    def loadRules(self):
        """load rules from database or from self.rawRules (got over the net)"""
        for record in self.rawRules or self.__loadQuery().records:
            self.__loadRule(record)

    def __loadRule(self, record):
        """loads a rule into the correct ruleList"""
        (_, name, listNr, _, definition, points, doubles, limits, parameter) = record
        for ruleList in self.ruleLists:
            if ruleList.listId == listNr:
                if ruleList is self.parameterRules:
                    rule = Rule(name, definition, parameter=parameter)
                else:
                    try:
                        pointValue = int(points)
                    except ValueError:
                        # this happens if the unit changed from limits to points but the value
                        # is not converted at the same time
                        pointValue = int(float(points))
                    rule = Rule(name, definition, pointValue, int(doubles), float(limits))
                ruleList.add(rule)
                break

    def findUniqueOption(self, action):
        """return first rule with option"""
        rulesWithAction = list(x for x in self.allRules if action in x.options)
        assert len(rulesWithAction) < 2, '%s has too many matching rules for %s' % (str(self), action)
        if rulesWithAction:
            return rulesWithAction[0]

    def filterFunctions(self, attrName):
        """returns all my Function classes having attribute attrName"""
        if attrName not in self.__filteredLists:
            functions = (x.function for x in self.allRules if x.function)
            self.__filteredLists[attrName] = list(x for x in functions if hasattr(x, attrName))
        return self.__filteredLists[attrName]

    def loadSplitRules(self):
        """loads the split rules"""
        self.splitRules.append(Splitter('kong', r'([dwsbc][1-9eswnbrg])([DWSBC][1-9eswnbrg])(\2)(\2)', 4))
        self.splitRules.append(Splitter('pung', r'([XDWSBC][1-9eswnbrgy])(\1\1)', 3))
        for chi1 in xrange(1, 8):
            rule = r'(?P<g>[SBC])(%d)((?P=g)%d)((?P=g)%d) ' % (chi1, chi1+1, chi1+2)
            self.splitRules.append(Splitter('chow', rule, 3))
            # discontinuous chow:
            rule = r'(?P<g>[SBC])(%d).*((?P=g)%d).*((?P=g)%d)' % (chi1, chi1+1, chi1+2)
            self.splitRules.append(Splitter('chow', rule, 3))
            self.splitRules.append(Splitter('chow', rule, 3))
        self.splitRules.append(Splitter('pair', r'([DWSBCdwsbc][1-9eswnbrg])(\1)', 2))
        self.splitRules.append(Splitter('single', r'(..)', 1))

    @staticmethod
    def newId(minus=False):
        """returns an unused ruleset id. This is not multi user safe."""
        func = 'min(id)-1' if minus else 'max(id)+1'
        result = -1 if minus else 1
        records = Query("select %s from ruleset" % func).records
        if records and records[0] and records[0][0]:
            try:
                result = int(records[0][0])
            except ValueError:
                pass
        return result

    @staticmethod
    def nameExists(name):
        """return True if ruleset name is already in use"""
        result = any(x.name == name for x in PredefinedRuleset.rulesets())
        if not result:
            result = bool(Query('select id from ruleset where id<0 and name=?', list([name])).records)
        return result

    def _newKey(self, minus=False):
        """generate a new id and a new name if the name already exists"""
        newId = self.newId(minus=minus)
        newName = self.name
        if minus:
            copyNr = 1
            while self.nameExists(newName):
                copyStr = ' ' + str(copyNr) if copyNr > 1 else ''
                newName = m18nc('Ruleset._newKey:%1 is empty or space plus number',
                    'Copy%1 of %2', copyStr, m18n(self.name))
                copyNr += 1
        return newId, newName

    def clone(self):
        """returns a clone of self, unloaded"""
        return Ruleset(self.rulesetId)

    def __str__(self):
        return 'type=%s, id=%d,rulesetId=%d,name=%s' % (
                type(self), id(self), self.rulesetId, self.name)

    def copy(self, minus=False):
        """make a copy of self and return the new ruleset id. Returns a new ruleset or None"""
        newRuleset = self.clone().load()
        newRuleset.save(copy=True, minus=minus)
        if isinstance(newRuleset, PredefinedRuleset):
            newRuleset = Ruleset(newRuleset.rulesetId)
        return newRuleset

    def __ruleList(self, rule):
        """return the list containg rule. We could make the list
        an attribute of the rule but then we rarely
        need this, and it is not time critical"""
        for ruleList in self.ruleLists:
            if rule in ruleList:
                return ruleList
        assert False

    def rename(self, newName):
        """renames the ruleset. returns True if done, False if not"""
        with Transaction():
            if self.nameExists(newName):
                return False
            query = Query("update ruleset set name=? where id<0 and name =?",
                list([newName, self.name]))
            if query.success:
                self.name = newName
            return query.success

    def remove(self):
        """remove this ruleset from the database."""
        Query(["DELETE FROM rule WHERE ruleset=%d" % self.rulesetId,
                   "DELETE FROM ruleset WHERE id=%d" % self.rulesetId])

    @staticmethod
    def ruleKey(rule):
        """needed for sorting the rules"""
        return rule.__str__()

    def __computeHash(self):
        """compute the hash for this ruleset using all rules but not name and
        description of the ruleset"""
        self.load()
        result = md5()
        for rule in sorted(self.allRules, key=Ruleset.ruleKey):
            result.update(rule.hashStr())
        self.__hash = result.hexdigest()

    def ruleRecord(self, rule):
        """returns the rule as tuple, prepared for use by sql"""
        score = rule.score
        definition = rule.definition
        if rule.parType:
            parTypeName = rule.parType.__name__
            if parTypeName == 'unicode':
                parTypeName = 'str'
            definition = parTypeName + definition
        ruleList = None
        for ruleList in self.ruleLists:
            if rule in ruleList:
                ruleIdx = ruleList.index(rule)
                break
        assert rule in ruleList
        return (self.rulesetId, english(rule.name), ruleList.listId, ruleIdx,
            definition, score.points, score.doubles, score.limits, str(rule.parameter))

    def updateRule(self, rule):
        """update rule in database"""
        self.__hash = None  # invalidate, will be recomputed when needed
        with Transaction():
            Query("DELETE FROM rule WHERE ruleset=? and name=?", list([self.rulesetId, english(rule.name)]))
            self.saveRule(rule)
            Query("UPDATE ruleset SET hash=? WHERE id=?", list([self.hash, self.rulesetId]))

    def saveRule(self, rule):
        """save only rule in database"""
        Query('INSERT INTO rule(ruleset, name, list, position, definition, '
                'points, doubles, limits, parameter)'
                ' VALUES(?,?,?,?,?,?,?,?,?)',
                self.ruleRecord(rule))

    def save(self, copy=False, minus=False):
        """save the ruleset to the database.
        copy=True gives it a new id. If the name already exists in the database, also give it a new name"""
        with Transaction():
            if copy:
                self.rulesetId, self.name = self._newKey(minus)
            Query('INSERT INTO ruleset(id,name,hash,description) VALUES(?,?,?,?)',
                list([self.rulesetId, english(self.name), self.hash, self.description]))
        # do not put this into the transaction, keep it as short as possible. sqlite3/Qt
        # has problems if two processes are trying to do the same here (kajonggtest)
        for rule in self.allRules:
            self.saveRule(rule)

    @staticmethod
    def availableRulesets():
        """returns all rulesets defined in the database plus all predefined rulesets"""
        templateIds = (x[0] for x in Query("SELECT id FROM ruleset WHERE id<0").records)
        return [Ruleset(x) for x in templateIds] + PredefinedRuleset.rulesets()

    @staticmethod
    def selectableRulesets(server=None):
        """returns all selectable rulesets for a new game.
        server is used to find the last ruleset used by us on that server, this
        ruleset will returned first in the list."""
        result = Ruleset.availableRulesets()
        # if we have a selectable ruleset with the same name as the last used ruleset
        # put that ruleset in front of the list. We do not want to use the exact same last used
        # ruleset because we might have made some fixes to the ruleset meanwhile
        if server is None: # scoring game
            # the exists clause is only needed for inconsistent data bases
            qData = Query("select ruleset from game where seed is null "
                " and exists(select id from ruleset where game.ruleset=ruleset.id)"
                "order by starttime desc limit 1").records
        else:
            qData = Query('select lastruleset from server where lastruleset is not null and url=?',
                list([server])).records
            if not qData:
                # we never played on that server
                qData = Query('select lastruleset from server where lastruleset is not null '
                    'order by lasttime desc limit 1').records
        if qData:
            lastUsedId = qData[0][0]
            qData = Query("select name from ruleset where id=%d" % lastUsedId).records
            if qData:
                lastUsed = qData[0][0]
                for idx, ruleset in enumerate(result):
                    if ruleset.name == lastUsed:
                        del result[idx]
                        return [ruleset ] + result
        return result

    def diff(self, other):
        """return a list of tuples. Every tuple holds one or two rules: tuple[0] is from self, tuple[1] is from other"""
        result = []
        leftDict = dict((x.name, x) for x in self.allRules)
        rightDict = dict((x.name, x) for x in other.allRules)
        left = set(leftDict.keys())
        right = set(rightDict.keys())
        for rule in left & right:
            leftRule, rightRule = leftDict[rule], rightDict[rule]
            if str(leftRule) != str(rightRule):
                result.append((leftRule, rightRule))
        for rule in left - right:
            result.append((leftDict[rule], None))
        for rule in right - left:
            result.append((None, rightDict[rule]))
        return result

class Rule(object):
    """a mahjongg rule with a name, matching variants, and resulting score.
    The rule applies if at least one of the variants matches the hand.
    For parameter rules, only use name, definition,parameter. definition must start with int or str
    which is there for loading&saving, but internally is stripped off."""
    # pylint: disable=R0913,R0902
    # pylint we need more than 10 instance attributes

    def __init__(self, name, definition='', points = 0, doubles = 0, limits = 0, parameter = None,
            description=None, debug=False):
        self.options = {}
        self.function = None
        self.hasSelectable = False
        self.name = name
        self.description = description
        self.score = Score(points, doubles, limits)
        self._definition = None
        self.parName = ''
        self.parameter = ''
        self.debug = debug
        self.parType = None
        for parType in [int, unicode, bool]:
            typeName = parType.__name__
            if typeName == 'unicode':
                typeName = 'str'
            if definition.startswith(typeName):
                self.parType = parType
                if parType is bool and type(parameter) in (str, unicode):
                    parameter = parameter != 'False'
                self.parameter = parType(parameter)
                definition = definition[len(typeName):]
                break
        self.definition = definition

    @property
    def definition(self):
        """the rule definition. See user manual about ruleset."""
        if isinstance(self._definition, list):
            return '||'.join(self._definition)
        return self._definition

    @definition.setter
    def definition(self, definition):
        """setter for definition"""
        #pylint: disable=R0912
        assert not isinstance(definition, QString)
        prevDefinition = self.definition
        self._definition = definition
        if not definition:
            return # may happen with special programmed rules
        variants = definition.split('||')
        if self.parType:
            self.parName = variants[0]
            variants = variants[1:]
        self.options = {}
        self.function = None
        self.hasSelectable = False
        for idx, variant in enumerate(variants):
            if isinstance(variant, (str, unicode)):
                variant = str(variant)
                if variant[0] == 'F':
                    assert idx == 0
                    self.function = rulecode.Function.functions[variant[1:]]()
                    # when executing code for this rule, we do not want
                    # to call those things indirectly
                    if hasattr(self.function, 'appliesToHand'):
                        self.appliesToHand = self.function.appliesToHand
                    if hasattr(self.function, 'appliesToMeld'):
                        self.appliesToMeld = self.function.appliesToMeld
                    if hasattr(self.function, 'selectable'):
                        self.hasSelectable = True
                        self.selectable = self.function.selectable
                    if hasattr(self.function, 'winningTileCandidates'):
                        self.winningTileCandidates = self.function.winningTileCandidates
                elif variant[0] == 'O':
                    for action in variant[1:].split():
                        aParts = action.split('=')
                        if len(aParts) == 1:
                            aParts.append('None')
                        self.options[aParts[0]] = aParts[1]
                else:
                    pass
        if self.function:
            self.function.options = self.options
        self.validateDefinition(prevDefinition)

    def validateDefinition(self, prevDefinition):
        """check for validity. If wrong, restore prevDefinition."""
        payers = int(self.options.get('payers', 1))
        payees = int(self.options.get('payees', 1))
        if not 2 <= payers + payees <= 4:
            self.definition = prevDefinition
            logException(m18nc('%1 can be a sentence', '%4 have impossible values %2/%3 in rule "%1"',
                                  self.name, payers, payees, 'payers/payees'))

    def validateParameter(self):
        """check for validity"""
        if 'min' in self.options:
            minValue = self.parType(self.options['min'])
            if self.parameter < minValue:
                return m18nc('wrong value for rule', '%1: %2 is too small, minimal value is %3',
                    m18n(self.name), self.parameter, minValue)

    def appliesToHand(self, dummyHand): # pylint: disable=R0201, E0202
        """does the rule apply to this hand?"""
        return False

    def selectable(self, dummyHand): # pylint: disable=R0201, E0202
        """does the rule apply to this hand?"""
        return False

    def appliesToMeld(self, dummyHand, dummyMeld): # pylint: disable=R0201, E0202
        """does the rule apply to this meld?"""
        return False

    def winningTileCandidates(self, dummyHand): # pylint: disable=R0201, E0202
        """those might be candidates for a calling hand"""
        return set()

    def explain(self):
        """use this rule for scoring"""
        return m18n(self.name) + ': ' + self.score.contentStr()

    def hashStr(self):
        """all that is needed to hash this rule. Try not to change this to keep
        database congestion low"""
        result = '%s: %s %s %s' % (self.name, self.parameter, self.definition, self.score)
        return result.encode('utf-8')

    def __str__(self):
        return self.hashStr()

    def __repr__(self):
        return self.hashStr()

    def contentStr(self):
        """returns a human readable string with the content: score or option value"""
        if self.parType:
            return str(self.parameter)
        else:
            return self.score.contentStr()

    @staticmethod
    def exclusive():
        """True if this rule can only apply to one player"""
        return False

    def hasNonValueAction(self):
        """Rule has a special action not changing the score directly"""
        return bool(any(x not in ['lastsource', 'declaration'] for x in self.options))

class Splitter(object):
    """a regex with a name for splitting concealed and yet unsplitted tiles into melds"""
    def __init__(self, name, definition, size):
        self.name = name
        self.definition = definition
        self.size = size
        self.compiled = re.compile(definition)

    def apply(self, split):
        """work the found melds in reverse order because we remove them from the rest:"""
        result = []
        if len(split) >= self.size * 2:
            for found in reversed(list(self.compiled.finditer(split))):
                operand = ''
                for group in found.groups():
                    if group is not None:
                        operand += group
                if len(operand):
                    result.append(operand)
                    # remove the found meld from this split
                    for group in range(len(found.groups()), 0, -1):
                        start = found.start(group)
                        end = found.end(group)
                        split = split[:start] + split[end:]
        result.reverse()
        result.append(split) # append always!!!
        return result

class PredefinedRuleset(Ruleset):
    """special code for loading rules from program code instead of from the database"""

    classes = set()  # only those will be playable
    preRulesets = None

    def __init__(self, name=None):
        Ruleset.__init__(self, name or 'general predefined ruleset')

    @staticmethod
    def rulesets():
        """a list of instances for all predefined rulesets"""
        if PredefinedRuleset.preRulesets is None:
            PredefinedRuleset.preRulesets = list(x()
                for x in sorted(PredefinedRuleset.classes, key=lambda x:x.__name__))
        return PredefinedRuleset.preRulesets

    def rules(self):
        """here the predefined rulesets can define their rules"""
        pass

    def clone(self):
        """return a clone, unloaded"""
        return self.__class__()
