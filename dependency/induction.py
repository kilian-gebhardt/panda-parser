__author__ = 'kilian'

import re
from random import seed

from grammar.induction.decomposition import join_spans, fanout_limited_partitioning, left_branching_partitioning, \
    right_branching_partitioning, fanout_limited_partitioning_left_to_right, fanout_limited_partitioning_argmax, fanout_limited_partitioning_random_choice, fanout_limited_partitioning_no_new_nont

from dependency.labeling import AbstractLabeling
from grammar.dcp import DCP_rule, DCP_term, DCP_var, DCP_index
from grammar.lcfrs import LCFRS, LCFRS_lhs, LCFRS_var
from dependency.top_bottom_max import top_max, bottom_max


###################   Top level methods for grammar induction.   ###################


def induce_grammar(trees, nont_labelling, term_labelling, recursive_partitioning, start_nont='START'):
    """
    :rtype: LCFRS
    :param trees: corpus of HybridTree (i.e. list (or Generator for lazy IO))
    :type trees: __generator[HybridTree]
    :type nont_labelling: AbstractLabeling
    :param term_labelling: HybridTree, NodeId -> str
    :param recursive_partitioning: HybridTree -> RecursivePartitioning
    :type start_nont: str
    :rtype: int, LCFRS

    Top level method to induce an LCFRS/DCP-hybrid grammar for dependency parsing.
    """
    grammar = LCFRS(start_nont)
    n_trees = 0
    for tree in trees:
        n_trees += 1
        for rec_par in recursive_partitioning:
            match = re.search(r'no_new_nont', rec_par.__name__)
            if match:
                rec_par_int = rec_par(tree, grammar.nonts(), nont_labelling)
            else:
                rec_par_int = rec_par(tree)

            rec_par_nodes = tree.node_id_rec_par(rec_par_int)

            (_, _, nont_name) = add_rules_to_grammar_rec(tree, rec_par_nodes, grammar, nont_labelling, term_labelling)

            # Add rule from top start symbol to top most nonterminal for the hybrid tree
            lhs = LCFRS_lhs(start_nont)
            lhs.add_arg([LCFRS_var(0, 0)])
            rhs = [nont_name]
            dcp_rule = DCP_rule(DCP_var(-1, 0), [DCP_var(0, 0)])

            grammar.add_rule(lhs, rhs, 1.0, [dcp_rule])

    grammar.make_proper()
    return n_trees, grammar


# Recursive partitioning strategies
def left_branching(tree):
    return left_branching_partitioning(len(tree.id_yield()))


def right_branching(tree):
    return right_branching_partitioning(len(tree.id_yield()))


def direct_extraction(tree):
    return tree.recursive_partitioning()


def cfg(tree):
    return fanout_k(tree, 1)


fanout_k = lambda tree, k: fanout_limited_partitioning(tree.recursive_partitioning(), k)
fanout_k_left_to_right = lambda tree, k: fanout_limited_partitioning_left_to_right(tree.recursive_partitioning(), k)
fanout_k_argmax = lambda tree, k: fanout_limited_partitioning_argmax(tree.recursive_partitioning(), k)
fanout_k_random = lambda tree, k: fanout_limited_partitioning_random_choice(tree.recursive_partitioning(), k)
fanout_k_no_new_nont = lambda tree, nonts, nont_labelling, fallback, k: fanout_limited_partitioning_no_new_nont(tree.recursive_partitioning(), k, tree, nonts, nont_labelling, fallback)


class RecursivePartitioningFactory:
    def __init__(self):
        self.__partitionings = {}

    def register_partitioning(self, name, partitioning):
        self.__partitionings[name] = partitioning

    def get_partitioning(self, name):
        partitioning_names = name.split(',')
        partitionings = []
        for name in partitioning_names:
            match = re.search(r'fanout-(\d+)([-\w]*)', name)
            if match:
                k = int(match.group(1))
                trans = match.group(2)
                if trans == '': #right-to-left bfs
                    rec_par = lambda tree: fanout_k(tree, k)
                    rec_par.__name__ = 'fanout_' + str(k)
                    partitionings.append(rec_par)
                if trans == '-left-to-right':
                    rec_par = lambda tree: fanout_k_left_to_right(tree, k)
                    rec_par.__name__ = 'fanout_' + str(k) + '_left_to_right'
                    partitionings.append(rec_par)
                if trans == '-argmax':
                    rec_par = lambda tree: fanout_k_argmax(tree, k)
                    rec_par.__name__ = 'fanout_' + str(k) + '_argmax'
                    partitionings.append(rec_par)
                # set seed, if random strategy is chosen
                rand_match = re.search(r'-random-(\d*)', trans)
                if rand_match:
                    s = int(rand_match.group(1))
                    seed(s)
                    rec_par = lambda tree: fanout_k_random(tree, k)
                    rec_par.__name__ = 'fanout_' + str(k) + '_random'
                    partitionings.append(rec_par)
                # set fallback strategy if no position corresponds to an existing nonterminal
                no_new_nont_match = re.search(r'-no-new-nont([-\w]*)', trans)
                if no_new_nont_match:
                    fallback = no_new_nont_match.group(1)
                    rand_match = re.search(r'-random-(\d*)', fallback)
                    if rand_match:
                        s = int(rand_match.group(1))
                        seed(s)
                        fallback = '-random'
                    rec_par = lambda tree, nonts, nont_labelling: fanout_k_no_new_nont(tree, nonts, nont_labelling, k, fallback)
                    rec_par.__name__ = 'fanout_' + str(k) + '_no_new_nont'
                    partitionings.append(rec_par)
            else:
                rec_par = self.__partitionings[name]
                if rec_par:
                    partitionings.append(rec_par)
                else:
                    return None
        if partitionings:
            return partitionings
        else:
            return None


def the_recursive_partitioning_factory():
    factory = RecursivePartitioningFactory()
    factory.register_partitioning('left-branching', left_branching)
    factory.register_partitioning('right-branching', right_branching)
    factory.register_partitioning('direct-extraction', direct_extraction)
    factory.register_partitioning('cfg', cfg)
    return factory


###################################### Recursive Rule extraction method ###################################
def add_rules_to_grammar_rec(tree, rec_par, grammar, nont_labelling, term_labelling):
    """
    Extract LCFRS/DCP-hybrid-rules from some hybrid tree, according to some recursive partitioning
    and add them to some grammar.
    :rtype: ([[str]],[[str]],str)
    :param tree: HybridTree
    :param rec_par: pair of (list of string) and (list of rec_par))
    :param grammar: LCFRS
    :type nont_labelling: AbstractLabeling
    :param term_labelling: HybridTree, node_id -> string
    :return: (top_max, bottom_max, nont_name) of root in rec_par :raise Exception:
    """
    (node_ids, children) = rec_par

    # Sanity check
    if children and len(node_ids) == 1:
        raise Exception('A singleton in a recursive partitioning should not have children.')

    if len(node_ids) == 1:
        t_max = top_max(tree, node_ids)
        b_max = bottom_max(tree, node_ids)

        dependency_label = tree.node_token(node_ids[0]).deprel()

        dcp = [create_leaf_DCP_rule(b_max, dependency_label)]
        lhs = create_leaf_lcfrs_lhs(tree, node_ids, t_max, b_max, nont_labelling, term_labelling)

        grammar.add_rule(lhs, [], 1.0, dcp)

        return t_max, b_max, lhs.nont()

    else:
        # Create rules for children and obtain top_max and bottom_max of child nodes
        child_t_b_max = []
        for child in children:
            child_t_b_max.append(add_rules_to_grammar_rec(tree, child, grammar, nont_labelling, term_labelling))

        # construct DCP equations
        dcp = []
        t_max = top_max(tree, node_ids)
        b_max = bottom_max(tree, node_ids)

        # create equations for synthesized attributes on LHS
        for arg in range(len(t_max)):
            dcp.append(create_dcp_rule(-1, len(b_max) + arg, t_max, b_max, child_t_b_max))

        # create equations for inherited attributes on RHS
        for cI in range(len(child_t_b_max)):
            child = child_t_b_max[cI]
            for arg in range(len(child[1])):
                dcp.append(create_dcp_rule(cI, arg, t_max, b_max, child_t_b_max))

        # create LCFRS-rule, attach dcp and add to grammar
        lhs = create_lcfrs_lhs(tree, node_ids, t_max, b_max, children, nont_labelling)
        rhs = [nont_name for (_, _, nont_name) in child_t_b_max]
        grammar.add_rule(lhs, rhs, 1.0, dcp)

        return t_max, b_max, lhs.nont()


def create_dcp_rule(mem, arg, top_max, bottom_max, children):
    """
    Create DCP equation for some synthesized attributes of LHS nont
    or inherited attributes of RHS nont of an LCFRS-sDCP-hybrid rule.
    :rtype: DCP_rule
    :param mem: int                            (member part of attribute: -1 for LHS, >=0 for RHS)
    :param arg: int                            (argument part of attribute: >= 0)
    :param top_max:    list of list of string  (top_max of nont on LHS)
    :param bottom_max: list of list of string  (bottom_max of nont on LHS)
    :param children: list of pairs of list of list of string
                                       (pair of (top_max, bottom_max) for every nont on RHS)
    :return: DCP_rule :raise Exception:
    """
    lhs = DCP_var(mem, arg)
    rhs = []
    if mem < 0:
        conseq_ids = top_max[arg - len(bottom_max)][:]
    else:
        conseq_ids = children[mem][1][arg][:]
    while conseq_ids:
        id = conseq_ids[0]
        if mem >= 0:
            c_index = -1
        else:
            c_index = 0
        match = False
        while c_index < len(children) and not match:
            if c_index >= 0:
                child = children[c_index]
            else:
                # If equation for inherited arguments of some nont on RHS is computed,
                # the inherited arguments of the LHS are used in addition.
                # The second component is empty, which allows for some magic below!
                child = (bottom_max, [])
            t_seq_index = 0
            while t_seq_index < len(child[0]) and not match:
                t_seq = child[0][t_seq_index]
                # check if correct child synthesized attribute was found
                if id == t_seq[0]:
                    # sanity check, is t_seq a prefix of conseq_ids
                    if conseq_ids[:len(t_seq)] != t_seq:
                        raise Exception
                    # Append variable corresponding to synthesized attribute of nont on RHS.
                    # Or, append variable corresponding to inherited attribute of nont on LHS,
                    # where len(child[1]) evaluates to 0 as intended.
                    rhs.append(DCP_var(c_index, len(child[1]) + t_seq_index))
                    # remove matched prefix from conseq_ids
                    conseq_ids = conseq_ids[len(t_seq):]
                    # exit two inner while loops
                    match = True
                t_seq_index += 1
            c_index += 1
        # Sanity check, that attribute was matched:
        if not match:
            raise Exception('Expected ingredient for synthesised or inherited argument was not found.')
    return DCP_rule(lhs, rhs)


def create_lcfrs_lhs(tree, node_ids, t_max, b_max, children, nont_labelling):
    """
    Create the LCFRS_lhs of some LCFRS-DCP hybrid rule.
    :rtype: LCFRS_lhs
    :param tree:     HybridTree
    :param node_ids: list of string (node in an recursive partitioning)
    :param t_max:    top_max of node_ids
    :param b_max:    bottom_max of node ids
    :param children: list of pairs of list of list of string
#                    (pairs of top_max / bottom_max of child nodes in recursive partitioning)
    :type nont_labelling: AbstractLabeling
    :return: LCFRS_lhs :raise Exception:
    """
    positions = map(tree.node_index, node_ids)
    spans = join_spans(positions)

    children_spans = list(map(join_spans, [map(tree.node_index, ids) for (ids, _) in children]))

    lhs = LCFRS_lhs(nont_labelling.label_nonterminal(tree, node_ids, t_max, b_max, len(spans)))
    for (low, high) in spans:
        arg = []
        i = low
        while i <= high:
            mem = 0
            match = False
            while mem < len(children_spans) and not match:
                child_spans = children_spans[mem]
                mem_arg = 0
                while mem_arg < len(child_spans) and not match:
                    child_span = child_spans[mem_arg]
                    if child_span[0] == i:
                        arg.append(LCFRS_var(mem, mem_arg))
                        i = child_span[1] + 1
                        match = True
                    mem_arg += 1
                mem += 1
            # Sanity check
            if not match:
                raise Exception('Expected ingredient for LCFRS argument was not found.')
        lhs.add_arg(arg)

    return lhs


def create_leaf_DCP_rule(bottom_max, dependency_label):
    """
    Creates a DCP rule for a leaf of the recursive partitioning.
    Note that the linked LCFRS-rule has an empty RHS.
    If the corresponding node in the hybrid tree is not a leaf, i.e. bottom_max != [],
    there is exactly one inherited argument <0,0>. The only synthesized argument
    generates a DCP_term of the form "[0:{dependency_label}]( <0,0> ).
    Otherwise, there is no inherited argument, and the only synthesized argument
    generates a DCP_term of the form "[0:{dependency_label}]( )".
    :rtype: DCP_rule
    :param bottom_max: list of list of string
    :param dependency_label: dependency label linked to the corresponding terminal
    :return: DCP_rule
    """
    if bottom_max:
        arg = 1
    else:
        arg = 0
    lhs = DCP_var(-1, arg)
    term_head = DCP_index(0, dependency_label)
    if bottom_max:
        term_arg = [DCP_var(-1, 0)]
    else:
        term_arg = []
    rhs = [DCP_term(term_head, term_arg)]
    return DCP_rule(lhs, rhs)


def create_leaf_lcfrs_lhs(tree, node_ids, t_max, b_max, nont_labelling, term_labelling):
    """
    Create LCFRS_lhs for a leaf of the recursive partitioning,
    i.e. this LCFRS creates (consumes) exactly one terminal symbol.
    :param tree: HybridTree
    :param node_ids: list of string
    :param t_max: top_max of node_ids
    :param b_max: bottom_max of node_ids
    :type nont_labelling: AbstractLabeling
    :param term_labelling: HybridTree, node_id -> string
    :return: LCFRS_lhs
    """

    # Build LHS
    lhs = LCFRS_lhs(nont_labelling.label_nonterminal(tree, node_ids, t_max, b_max, 1))
    id = node_ids[0]
    arg = [term_labelling(tree.node_token(id))]
    lhs.add_arg(arg)
    return lhs


__all__ = ["induce_grammar", "the_recursive_partitioning_factory"]
