from abc import ABCMeta, abstractmethod
from collections import defaultdict
from hybridtree.monadic_tokens import MonadicToken


class TerminalLabeling:
    __metaclass__ = ABCMeta

    @abstractmethod
    def token_label(self, token):
        """
        :type token: MonadicToken
        """
        pass

    def token_tree_label(self, token):
        if token.type() == "CONLL-X":
            return self.token_label(token) + " : " + token.deprel()
        elif token.type() == "CONSTITUENT-CATEGORY":
            return token.category() + " : " + token.edge()
        else:
            return self.token_label(token) + " : " + token.edge()

    def prepare_parser_input(self, tokens):
        return map(self.token_label, tokens)


# class ConstituentTerminalLabeling(TerminalLabeling):
#     def token_label(self, token):
#         if isinstance(token, ConstituentTerminal):
#             return token.pos()
#         elif isinstance(token, ConstituentCategory):
#             return token.category()
#         else:
#             assert False


class FormTerminals(TerminalLabeling):
    def token_label(self, token):
        return token.form()

    def __str__(self):
        return 'form'


class CPosTerminals(TerminalLabeling):
    def token_label(self, token):
        return token.cpos()

    def __str__(self):
        return 'cpos'


class PosTerminals(TerminalLabeling):
    def token_label(self, token):
        return token.pos()

    def __str__(self):
        return 'pos'


class CPOS_KON_APPR(TerminalLabeling):
    def token_label(self, token):
        cpos = token.pos()
        if cpos in ['KON', 'APPR']:
            return cpos + token.form().lower()
        else:
            return cpos

    def __str__(self):
        return 'cpos-KON-APPR'


class FormPosTerminalsUnk(TerminalLabeling):
    def __init__(self, trees, threshold, UNK="UNKNOWN", filter=[]):
        """
        :param trees: corpus of trees
        :param threshold: UNK words below the threshold
        :type threshold: int
        :param UNK: representation string of UNK in grammar
        :type UNK: str
        :param filter: a list of POS tags which are always UNKed
        :type filter: list[str]
        """
        self.__terminal_counts = defaultdict(lambda: 0)
        self.__UNK = UNK
        self.__threshold = threshold
        for tree in trees:
            for token in tree.token_yield():
                if token.pos() not in filter:
                    self.__terminal_counts[(token.form().lower(), token.pos())] += 1

    def __str__(self):
        return 'form-pos-unk-' + str(self.__threshold) + '-pos'

    def token_label(self, token):
        pos = token.pos()
        form = token.form().lower()
        if self.__terminal_counts.get((form, pos)) < self.__threshold:
            form = self.__UNK
        return form + '-:-' + pos


class FormPosTerminalsUnkMorph(TerminalLabeling):
    def __init__(self, trees, threshold, UNK="UNKNOWN", filter=[], add_morph={}):
        self.__terminal_counts = defaultdict(lambda: 0)
        self.__UNK = UNK
        self.__threshold = threshold
        self.__add_morph = add_morph
        for tree in trees:
            for token in tree.token_yield():
                if token.pos() not in filter:
                    self.__terminal_counts[(token.form().lower(), token.pos())] += 1

    def __str__(self):
        return 'form-pos-unk-' + str(self.__threshold) + '-morph-pos'

    def token_label(self, token):
        pos = token.pos()
        form = token.form().lower()
        if self.__terminal_counts.get((form, pos)) < self.__threshold:
            form = self.__UNK
            if pos in self.__add_morph:
                feats = map(lambda x: tuple(x.split('=')), token.feats().split('|'))
                for feat in feats:
                    if feat[0] in self.__add_morph[pos]:
                        form += '#' + feat[0] + ':' + feat[1]
        return form + '-:-' + pos


class TerminalLabelingFactory:
    def __init__(self):
        self.__strategies = {}

    def register_strategy(self, name, strategy):
        """
        :type name: str
        :type strategy: TerminalLabeling
        """
        self.__strategies[name] = strategy

    def get_strategy(self, name):
        """
        :type name: str
        :rtype: TerminalLabeling
        """
        return self.__strategies[name]


def the_terminal_labeling_factory():
    """
    :rtype : TerminalLabelingFactory
    """
    factory = TerminalLabelingFactory()
    factory.register_strategy('form', FormTerminals())
    factory.register_strategy('pos', PosTerminals())
    factory.register_strategy('cpos', CPosTerminals())
    factory.register_strategy('cpos-KON-APPR', CPOS_KON_APPR())
    return factory