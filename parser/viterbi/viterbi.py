#!/usr/bin/python
#-*- coding: iso-8859-15 -*-

from parser.parser_interface import AbstractParser
from grammar.LCFRS.lcfrs import LCFRS, LCFRS_rule, LCFRS_var
import heapq
from collections import defaultdict
from math import log
from parser.derivation_interface import AbstractDerivation
from sys import maxint


class Range:
    def __init__(self, left, right):
        """
        :type left: int
        :type right: int
        """
        self.left = left
        self.right = right

    def __eq__(self, other):
        # if not isinstance(other, Range):
        #    return False
        return other.left == self.left and other.right == self.right

    def __str__(self):
        return "⟨{0!s},{1!s}⟩".format(self.left, self.right)

    def __hash__(self):
        return hash((self.left, self.right))


class PassiveItem:
    def __init__(self, nonterminal, rule):
        """
        :param nonterminal:
        :type rule: LCFRS_rule
        """
        self.rule = rule
        self.nonterminal = nonterminal
        self.children = []
        self.weight = 0
        self.ranges = []
        self.valid = True

    def left_position(self):
        """
        :rtype: int
        """
        return self.ranges[0].left

    def right_position(self):
        return self.ranges[-1].right

    def copy(self):
        new_item = self.__class__(self.nonterminal, self.rule)
        new_item.weight = self.weight
        new_item.ranges = list(self.ranges)
        return new_item

    def __lt__(self, other):
        # This is since we use the min-heap as a max-heap!
        return self.weight > other.weight

    def __str__(self):
        return "[{0!s}] {1!s} [{2}]".format(self.weight, self.nonterminal, ', '.join(map(str, self.ranges)))

    def agenda_key(self):
        return self.nonterminal, tuple([(r.left, r.right) for r in self.ranges])

    def is_active(self):
        return False


def rule_to_passive_items(rule, input):
    """
    :type rule: LCFRS_rule
    :type input: [str]
    :return:
    """
    empty = PassiveItem(rule.lhs().nont(), rule)
    empty.weight = log(rule.weight())
    return rule_to_passive_items_rec(empty, input)


def rule_to_passive_items_rec(item, input):
    arg = len(item.ranges)
    if arg == item.rule.lhs().fanout():
        yield item
        return

    pattern = item.rule.lhs().arg(arg)
    if item.ranges:
        left = item.right_position()
    else:
        left = 0

    while left <= len(input) - len(pattern):
        i = 0
        while i < len(pattern) and (left + i) < len(input):
            if pattern[i] == input[left + i]:
                i += 1
            else:
                left += 1
                i = 0
        if i == len(pattern):
            tmp_item = item.copy()
            tmp_item.ranges.append(Range(left, left + i))
            for new_item in rule_to_passive_items_rec(tmp_item, input):
                yield new_item
        left += 1


def rule_to_active_item(rule, input, low):
    empty = ActiveItem(rule.lhs().nont(), rule)
    empty.weight = log(rule.weight())

    # TODO: We assume that LCFRS_var(0,0) occurs in the first component of the word tuple function
    # pattern = empty.rule.lhs().arg(0)
    # first_var = pattern.index(LCFRS_var(0, 0))
    empty.next_low = low
    # left = low - first_var
    # if pattern[0:first_var] == input[left:low]:
        # empty.ranges.append([Range(left, low)])
    for item in item_to_active_item_rec(empty, input, low, 0, 0):
            # item.merge_ranges()
        yield item


def item_to_active_item_rec(item, input, low, arg, pattern_pos):
    left = low
    while arg < item.rule.lhs().fanout():
        pattern = item.rule.lhs().arg(arg)
        while pattern_pos < len(pattern) and left < len(input):
            i = 0
            while pattern_pos + i < len(pattern) and left + i < len(input):
                if pattern[pattern_pos + i] == input[left + i]:
                    i += 1
                else:
                    if isinstance(pattern[pattern_pos + i], LCFRS_var) and i > 0:
                        tmp_item = item.copy()
                        if len(tmp_item.ranges) == arg:
                            tmp_item.ranges.append([])
                        #if left > 0 and Range(left, left + i) in tmp_item.ranges[arg]:
                         #   pass
                        if i > 0:
                            tmp_item.ranges[arg].append(Range(left, left + i))
                        tmp_item.ranges[arg].append(pattern[pattern_pos + i])
                        for new_item in item_to_active_item_rec(
                                tmp_item,
                                input,
                                left + i,
                                arg,
                                pattern_pos + i + 1):
                            yield new_item
                    else:
                        if len(item.ranges) == arg:
                            item.ranges.append([])
                        item.ranges[arg].append(pattern[pattern_pos])
                        pattern_pos += 1
                        left += 1

        if pattern_pos == len(pattern):
            arg += 1
            pattern_pos = 0
        else:
            return
    # print "Completely derived: ", item
    yield item


class ActiveItem(PassiveItem):
    def __init__(self, nonterminal, rule):
        PassiveItem.__init__(self, nonterminal, rule)
        self.next_low = None
        self.next_low_max = maxint - 1

    def next_nont(self):
        return self.rule.rhs_nont(len(self.children))

    def complete(self):
        """
        :rtype: bool
        """
        return len(self.children) == self.rule.rank()

    def merge_ranges(self):
        for i in range(len(self.ranges)):
            j = 0
            while j < len(self.ranges[i]) - 1:
                if isinstance(self.ranges[i][j], LCFRS_var) or isinstance(self.ranges[i][j+1], LCFRS_var):
                    j += 1
                else:
                # elif self.ranges[i][j].right == self.ranges[i][j+1].left:
                    self.ranges[i][j] = Range(self.ranges[i][j].left, self.ranges[i][j+1].right)
                    del self.ranges[i][j+1]
                    # self.ranges[i] = self.ranges[i][:j+1] + self.ranges[i][j+2:]
                #else:
                #    raise Exception()

    def copy(self):
        new_item = self.__class__(self.nonterminal, self.rule)
        new_item.weight = self.weight
        new_item.ranges = [list(rs) for rs in self.ranges]
        new_item.children = list(self.children)
        return new_item

    def replace_consistent(self, passive_item):
        """
        :type passive_item: PassiveItem
        :rtype: list[list[LCFRS_var|Range]], int, int
        """
        arg = len(self.children)
        new_ranges = []
        next_low_max = maxint - 1
        next_low = None
        pos = 0
        for r in self.ranges:
            new_range = []
            gap = True
            for elem in r:
                if isinstance(elem, Range):
                    if elem.left < pos:
                        return None, None, None
                    elif not gap and elem.left != pos:
                        return None, None, None
                    if not gap:
                        new_range[-1] = Range(new_range[-1].left, elem.right)
                    else:
                        new_range.append(elem)
                    if next_low is not None and next_low <= next_low_max and elem.left < next_low_max:
                        next_low_max = elem.left
                    pos = elem.right
                    gap = False
                elif elem.mem == arg:
                    subst_range = passive_item.ranges[elem.arg]
                    if subst_range.left < pos:
                        return None, None, None
                    elif not gap and subst_range.left != pos:
                        return None, None, None
                    if not gap:
                        new_range[-1] = Range(new_range[-1].left, subst_range.right)
                    else:
                        new_range.append(subst_range)
                        gap = False
                    pos = subst_range.right
                elif elem.mem == arg + 1 and elem.arg == 0:
                    next_low = pos
                    gap = True
                    new_range.append(elem)
                else:
                    new_range.append(elem)
                    gap = True
            new_ranges.append(new_range)
        return new_ranges, next_low, next_low_max

    def make_passive(self):
        self.__class__ = PassiveItem
        i = 0
        while i < len(self.ranges):
            # assert len(self.ranges[i]) == 1
            self.ranges[i] = self.ranges[i][0]
            i += 1
        del self.next_low

    def __str__(self):
        return "[{0!s}] {1!s} [{2}]".format(self.weight, self.nonterminal, ', '.join(map(lambda r: "[{0}]".format(', '.join(map(str, r))), self.ranges)))

    def agenda_key(self):
        return id(self.rule), self.__ranges_to_tuple() # , len(self.children)

    def __ranges_to_tuple(self):
        return tuple([tuple(rs) for rs in self.ranges])

    def is_active(self):
        return True


#def help(r):
#    return "[{0}]".format(', '.join(map(str, r)))

class ViterbiParser(AbstractParser):
    def __init__(self, grammar, input):
        """
        :type grammar: LCFRS
        :type input: list[str]
        """
        self.grammar = grammar
        self.input = input
        self.agenda = []
        self.active_chart = defaultdict(list)
        self.passive_chart = defaultdict(list)
        # self.agenda_set = set () # defaultdict()
        self.actives = defaultdict()
        self.passives = defaultdict()
        self.goal = None
        # self.invalid_counter = 0
        self.__parse()
        # print "Invalid: ", self.invalid_counter

    def __parse(self):
        for rule in self.grammar.epsilon_rules():
            for item in rule_to_passive_items(rule, self.input):
                self.__record_item(item)
        for terminal in set(self.input):
            for rule in self.grammar.lex_rules(terminal):
                for item in rule_to_passive_items(rule, self.input):
                    self.__record_item(item)
        while self.agenda:
            item = heapq.heappop(self.agenda)
            # print "Process: ", item
            if not item.valid:
                continue
            if item.is_active():
                # if item.nonterminal == '{2:V:VBI,0}':
                #    pass

                for low in range(item.next_low, min(item.next_low_max + 1, len(self.input))):
                    key = item.next_nont(), low

                    self.active_chart[key].append(item)

                    for passive_item in self.passive_chart.get(key, []):
                        self.__combine(item, passive_item)
            else: # if isinstance(item, PassiveItem):
                #if item.nonterminal == '{2:V,0}':
                #    pass
                # STOPPING EARLY:
                if item.nonterminal == self.grammar.start() and item.ranges[0] == Range(0, len(self.input)):
                    self.goal = item
                    return
                low = item.left_position()
                nont = item.nonterminal
                key = nont, low

                self.passive_chart[key].append(item)

                for active_item in self.active_chart.get(key, []):
                    self.__combine(active_item, item)
                for rule in self.grammar.nont_corner_of(nont):
                    for active_item in rule_to_active_item(rule, self.input, low):
                        self.__combine(active_item, item)
            # else:
            #    raise Exception()

    def __combine(self, active_item, passive_item):
        ranges, next_low, next_low_max = active_item.replace_consistent(passive_item)
        if ranges:
            new_active = ActiveItem(active_item.nonterminal, active_item.rule)
            new_active.ranges = ranges
            new_active.next_low = next_low
            new_active.next_low_max = next_low_max
            new_active.weight = active_item.weight + passive_item.weight
            new_active.children = list(active_item.children) + [passive_item]

            if new_active.complete():
                new_active.make_passive()
            self.__record_item(new_active)

    def __record_item(self, item):
        key = item.agenda_key()
        if item.is_active(): # instance(item, ActiveItem):
            if key not in self.actives:
                self.actives[key] = item
                heapq.heappush(self.agenda, item)
            # elif self.actives[key].weight < item.weight:
            #     self.actives[key].valid = False
            #     self.actives[key] = item
            #     heapq.heappush(self.agenda, item)
        else:
            if key not in self.passives:
                self.passives[key] = item
                heapq.heappush(self.agenda, item)
            elif self.passives[key].weight < item.weight:
                self.passives[key].valid = False
                # self.invalid_counter += 1
                self.passives[key] = item
                heapq.heappush(self.agenda, item)

    def recognized(self):
        return self.goal is not None

    def all_derivation_trees(self):
        pass

    def best(self):
        return self.goal.weight

    def best_derivation_tree(self):
        if self.goal:
            return ViterbiDerivation(self.goal)
        else:
            return None


class ViterbiDerivation(AbstractDerivation):
    def __init__(self, rootItem):
        """
        :type rootItem: PassiveItem
        """
        self.rootItem = rootItem
        self.parent = {rootItem: None}
        self.insert_items(rootItem)

    def getRule(self, item):
        return item.rule

    def position_relative_to_parent(self, id):
        return self. parent[id], self.parent[id].children.index(id)

    def ids(self):
        return self.parent.keys()

    def child_ids(self, id):
        return id.children

    def terminal_positions(self, id):
        child_poss = [pos for child in id.children for pos in self.__spanned_input_positions(child)]
        return [pos + 1 for pos in self.__spanned_input_positions(id) if pos not in child_poss]

    @staticmethod
    def __spanned_input_positions(id):
        return [pos for r in id.ranges for pos in range(r.left, r.right)]

    def child_id(self, id, i):
        return id.children[i]

    def root_id(self):
        return self.rootItem

    def insert_items(self, item):
        for child in item.children:
            self.parent[child] = item
            self.insert_items(child)

    def __str__(self):
        return self.der_to_str_rec(self.root_id(), 0)

    def der_to_str_rec(self, item, indentation):
        s = ' ' * indentation * 2 + str(self.getRule(item)) + '\t(' + str(item) + ')\n'
        for child in self.child_ids(item):
            s += self.der_to_str_rec(child, indentation + 1)
        return s
