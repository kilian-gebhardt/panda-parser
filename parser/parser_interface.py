__author__ = 'kilian'

from abc import ABCMeta, abstractmethod
from lcfrs import *
from sDCPevaluation.evaluator import dcp_to_hybridtree, The_DCP_evaluator


class AbstractParser:
    __metaclass__ = ABCMeta

    @abstractmethod
    def __init__(self, grammar, input):
        """
        :type grammar: LCFRS
        :type input: list[str]
        :return:
        """
        pass

    @abstractmethod
    def best(self):
        """
        :rtype: float
        """
        pass

    @abstractmethod
    def recognized(self):
        """
        :rtype: bool
        """
        pass

    @abstractmethod
    def best_derivation_tree(self):
        """
        :rtype: AbstractDerivation
        :return:
        """
        pass

    @abstractmethod
    def all_derivation_trees(self):
        """
        :rtype: list(AbstractDerivation)
        :return:
        """
        pass

    def dcp_hybrid_tree_best_derivation(self, tree, poss, words, ignore_punctuation):
        """
        :param tree:
        :type tree: GeneralHybridTree
        :param poss: list(obj)
        :param words: list(obj)
        :param ignore_punctuation:
        :type ignore_punctuation: bool
        :return: The Hybrid Tree obtained through evaluation of the dcp-component of the best parse.
        :rtype: GeneralHybridTree
        """
        dcp_evaluation = self.dcp_best_derivation()
        if dcp_evaluation:
            return dcp_to_hybridtree(tree, dcp_evaluation, poss, words, ignore_punctuation)
        else:
            return None

    def dcp_best_derivation(self):
        der = self.best_derivation_tree()
        if der:
            return The_DCP_evaluator(der).getEvaluation()
        else:
            return []



def best_hybrid_tree_for_best_derivation():
    pass

def hybird_tree_from_sdcp_evaluation_for_best_derivation(self):
    # TODO
    pass

def all_hybrid_trees_from_derivations():
    pass

def hybrid_trees_from_sdcp_evaluation_of_all_derivations():
    pass

def hybrid_tree_from_sdcp_with_heighest_weight():
    pass