# Extracting grammars out of hybrid trees.

# from hybridtree import *
from decomposition import *
from grammar.lcfrs import *
from grammar.dcp import *
from grammar.induction.terminal_labeling import PosTerminals
from hybridtree.constituent_tree import ConstituentTree

# The root symbol.
start = 'START'


def direct_extract_lcfrs(tree, term_labeling=PosTerminals()):
    """
    :type tree: ConstituentTree
    :type term_labeling: ConstituentTerminalLabeling
    :rtype: LCFRS
    Extract LCFRS directly from hybrid tree.
    """
    gram = LCFRS(start=start)
    root = tree.root[0]
    if tree.is_leaf(root):
        lhs = LCFRS_lhs(start)
        label = term_labeling.token_label(tree.node_token(root))
        lhs.add_arg([label])
        dcp_rule = DCP_rule(DCP_var(-1, 0), [DCP_term(DCP_index(0), [])])
        gram.add_rule(lhs, [], dcp=[dcp_rule])
    else:
        first = direct_extract_lcfrs_from(tree, root, gram, term_labeling)
        lhs = LCFRS_lhs(start)
        lhs.add_arg([LCFRS_var(0, 0)])
        dcp_rule = DCP_rule(DCP_var(-1, 0), [DCP_var(0, 0)])
        gram.add_rule(lhs, [first], dcp=[dcp_rule])
    return gram


def direct_extract_lcfrs_from(tree, id, gram, term_labeling):
    """
    :type tree: ConstituentTree
    :type id: str
    :type gram: LCFRS
    :type term_labeling: ConstituentTerminalLabeling
    :rtype: str

    Traverse subtree at id and put extracted rules in grammar.
    """
    fringe = tree.fringe(id)
    spans = join_spans(fringe)
    nont_fanout = len(spans)
    label = tree.node_token(id).category()
    nont = label + '/' + str(nont_fanout)
    lhs = LCFRS_lhs(nont)
    children = [(child, join_spans(tree.fringe(child))) \
                for child in tree.children(id)]
    rhs = []
    n_terms = 0
    edge_labels = []
    for (low, high) in spans:
        arg = []
        pos = low
        while pos <= high:
            child_num = 0
            for i, (child, child_spans) in enumerate(children):
                for j, (child_low, child_high) in enumerate(child_spans):
                    if pos == child_low:
                        if tree.is_leaf(child):
                            arg += [term_labeling.token_label(tree.node_token(child))]
                            n_terms += 1
                            edge_labels += [tree.node_token(child).edge()]
                        else:
                            arg += [LCFRS_var(child_num, j)]
                        pos = child_high + 1
                if not tree.is_leaf(child):
                    child_num += 1
        lhs.add_arg(arg)
    for (child, child_spans) in children:
        if not tree.is_leaf(child):
            rhs_nont_fanout = len(child_spans)
            rhs += [tree.node_token(child).category() + '/' + str(rhs_nont_fanout)]
    dcp_lhs = DCP_var(-1, 0)
    dcp_indices = [DCP_term(DCP_index(i, edge_label=edge), []) for i, edge in enumerate(edge_labels)]
    dcp_vars = [DCP_var(i, 0) for i in range(len(rhs))]
    dcp_term = DCP_term(DCP_string(label, edge_label=tree.node_token(id).edge()), dcp_indices + dcp_vars)
    dcp_rule = DCP_rule(dcp_lhs, [dcp_term])
    gram.add_rule(lhs, rhs, dcp=[dcp_rule])
    for (child, _) in children:
        if not tree.is_leaf(child):
            direct_extract_lcfrs_from(tree, child, gram, term_labeling)
    return nont


############################################################
# Induction via unlabelled structure (recursive partitioning).


def fringe_extract_lcfrs(tree, fringes, naming='strict', term_labeling=PosTerminals(), isolate_pos=False, feature_logging=None):
    """
    :type tree: ConstituentTree
    :param fringes: recursive partitioning
    :param naming: 'strict' or 'child'
    :type naming: str
    :type term_labeling: ConstituentTerminalLabeling
    :rtype: LCFRS
    Get LCFRS for tree.
    """
    gram = LCFRS(start=start)
    first = None
    if len(tree.id_yield()) == 1 and isolate_pos:
        idx = tree.id_yield()[0]
        if tree.root[0] != idx:
            c_nont, c_spans, c_id_seq, c_nont_feat \
                = fringe_extract_lcfrs_recur(tree, fringes, gram, naming, term_labeling, isolate_pos, feature_logging,
                                             yield_one_check=False)

            fringe = fringes[0]
            spans = join_spans(fringe)
            args = []
            term_to_pos = {}  # maps input position to position in LCFRS rule
            for span in spans:
                args += [span_to_arg(span, [c_spans], tree, term_to_pos, term_labeling)]

            id_seq = make_id_seq(tree, tree.root[0], fringe)

            dcp_rules = []
            for (i, seq) in enumerate(id_seq):
                dcp_rhs = make_fringe_terms(tree, seq, [c_id_seq], term_to_pos, term_labeling)
                dcp_lhs = DCP_var(-1, i)
                dcp_rule = DCP_rule(dcp_lhs, dcp_rhs)
                dcp_rules += [dcp_rule]

            nont = id_nont(id_seq, tree, naming) + '/' + str(len(spans))
            nont_feat = feats(id_seq, tree)
            lhs = LCFRS_lhs(nont)
            for arg in args:
                lhs.add_arg(arg)
            rule = gram.add_rule(lhs, [c_nont], dcp=dcp_rules)
            if feature_logging is not None:
                feature_logging[(nont, nont_feat)] += 1
                feature_logging[(rule.get_idx(), nont_feat, tuple([c_nont_feat]))] += 1

            first = nont

    if first is None:
        (first, _, _, _) = fringe_extract_lcfrs_recur(tree, fringes, gram, naming, term_labeling, isolate_pos, feature_logging)
    lhs = LCFRS_lhs(start)
    lhs.add_arg([LCFRS_var(0, 0)])
    dcp_rule = DCP_rule(DCP_var(-1, 0), [DCP_var(0, 0)])
    gram.add_rule(lhs, [first], dcp=[dcp_rule])
    return gram


def fringe_extract_lcfrs_recur(tree, fringes, gram, naming, term_labeling, isolate_pos, feature_logging,
                               yield_one_check=True):
    """
    :type tree: ConstituentTree
    :param fringes: recursive partitioning
    :type gram: LCFRS
    :type naming: str
    :type term_labeling: ConstituentTerminalLabeling
    :rtype: (LCFRS, list[(int,int)], list[str])
    Traverse through recursive partitioning.
    """
    (fringe, children) = fringes
    nonts = []
    child_spans = []
    child_seqs = []
    child_feats = []
    for child in children:
        (child_nont, child_span, child_seq, child_feat) = \
            fringe_extract_lcfrs_recur(tree, child, gram, naming, term_labeling, isolate_pos, feature_logging)
        nonts += [child_nont]
        child_spans += [child_span]
        child_seqs += [child_seq]
        child_feats += [child_feat]
    spans = join_spans(fringe)
    term_to_pos = {}  # maps input position to position in LCFRS rule
    args = []
    for span in spans:
        args += [span_to_arg(span, child_spans, tree, term_to_pos, term_labeling)]
    # root[0] is legacy for single-rooted constituent trees
    id_seq = make_id_seq_single_pos(tree, tree.root[0], fringe, yield_one_check) if isolate_pos \
        else make_id_seq(tree, tree.root[0], fringe)
    dcp_rules = []
    for (i, seq) in enumerate(id_seq):
        dcp_rhs = make_fringe_terms(tree, seq, child_seqs, term_to_pos, term_labeling)
        dcp_lhs = DCP_var(-1, i)
        dcp_rule = DCP_rule(dcp_lhs, dcp_rhs)
        dcp_rules += [dcp_rule]
    nont = id_nont(id_seq, tree, naming) + '/' + str(len(spans))
    nont_feat = feats(id_seq, tree)
    lhs = LCFRS_lhs(nont)
    for arg in args:
        lhs.add_arg(arg)
    rule = gram.add_rule(lhs, nonts, dcp=dcp_rules)
    if feature_logging is not None:
        feature_logging[(nont, nont_feat)] += 1
        feature_logging[(rule.get_idx(), nont_feat, tuple(child_feats))] += 1
    return nont, spans, id_seq, nont_feat


def id_nont(id_seq, tree, naming):
    """
    :type id_seq: list[list[str]]
    :type tree: ConstituentTree
    :type naming: str
    :rtype: str
    Past labels of ids together.
    """
    if naming == 'strict':
        return id_nont_strict(id_seq, tree)
    elif naming == 'child':
        return id_nont_child(id_seq, tree)
    else:
        raise Exception('unknown naming ' + naming)


def token_to_features(token, isleaf=True):
    id_feat = [("function", token.edge())]
    if isleaf:
        id_feat += [('form', token.form()), ('pos', token.pos())] + token.morph_feats()
    else:
        id_feat += [('category', token.category())]
    return id_feat


def feats(id_seqs, tree):
    seqs_feats = []
    for id_seq in id_seqs:
        seq_feats = []
        for id in id_seq:
            token = tree.node_token(id)
            id_feat = token_to_features(token, isleaf=tree.is_leaf(id))
            seq_feats.append(frozenset(id_feat))
        seqs_feats.append(tuple(seq_feats))
    return tuple(seqs_feats)


def id_nont_strict(id_seqs, tree):
    """
    :type id_seqs: [[str]]
    :type tree: ConstituentTree
    :rtype: str
    Making naming on exact derived nonterminals.
    Consecutive children are separated by /.
    Where there is child missing, we have -.
    """
    s = ''
    for i, seq in enumerate(id_seqs):
        for j, id in enumerate(seq):
            if tree.is_leaf(id):
                s += tree.leaf_pos(id)
            else:
                s += tree.node_token(id).category()
            if j < len(seq) - 1:
                s += '/'
        if i < len(id_seqs) - 1:
            s += '-'
    return s


def id_nont_child(id_seq, tree):
    """
    :type id_seq: list[list[str]]
    :type tree: ConstituentTree
    :rtype: str
    Replace consecutive siblings by mention of parent.
    """
    s = ''
    for i, seq in enumerate(id_seq):
        if len(seq) == 1:
            if tree.is_leaf(seq[0]):
                s += tree.leaf_pos(seq[0])
            else:
                s += tree.node_token(seq[0]).category()
        else:
            id = tree.parent(seq[0])
            s += 'children_of_' + tree.node_token(id).category()
        if i < len(id_seq) - 1:
            s += '-'
    return s


def make_id_seq(tree, id, fringe):
    """
    :type tree: ConstituentTree
    :type id: str
    :type fringe: list[int]
    Compute list of lists of adjacent nodes whose fringes
    are included in input fringe.
    """
    if set(tree.fringe(id)) - fringe == set():
        # fully included in fringe
        return [[id]]
    else:
        seqs = []
        seq = []
        for child in tree.children(id):
            child_fringe = set(tree.fringe(child))
            if child_fringe - fringe == set():
                # fully included in fringe
                seq += [child]
            elif child_fringe & fringe != set():
                # overlaps with fringe
                if seq:
                    seqs += [seq]
                    seq = []
                seqs += make_id_seq(tree, child, fringe)
            elif seq:
                # not included in fringe, and breaks sequence
                seqs += [seq]
                seq = []
        if seq:
            seqs += [seq]
        return seqs


def make_id_seq_single_pos(tree, id, fringe, yield_one_check=True):
    """
    :type tree: ConstituentTree
    """
    if yield_one_check and len(tree.id_yield()) == 1:
        assert set(tree.fringe(id)) - fringe == set()
        return [[id]]
    else:
        if len(fringe) == 1:
            position = list(fringe)[0]
            return [[tree.id_yield()[position]]]
        else:
            return make_id_seq(tree, id, fringe)


def make_fringe_terms(tree, seq, child_seqss, term_to_pos, term_labeling):
    """
    :type tree: ConstituentTree
    :type seq: list[str]
    :type child_seqss: list[list[int]]
    :param term_to_pos: maps int to int (input position to position in LCFRS rule)
    :type term_labeling: ConstituentTerminalLabeling
    :return: list of DCP_term/DCP_index/DCP_var
    Make expression in terms of variables for the RHS members.
    Repeatedly replace nodes by variables.
    """
    for i, child_seqs in enumerate(child_seqss):
        for j, child_seq in enumerate(child_seqs):
            k = sublist_index(child_seq, seq)
            if k >= 0:
                var = DCP_var(i, j)
                seq = seq[:k] + [var] + seq[k + len(child_seq):]
    terms = []
    for elem in seq:
        if isinstance(elem, DCP_var):
            terms += [elem]
        else:
            if tree.is_leaf(elem):
                k = tree.leaf_index(elem)
                pos = term_to_pos[k]
                terms.append(DCP_term(DCP_index(pos, tree.node_token(elem).edge()), []))
            else:
                lab = tree.node_token(elem).category()
                arg = make_fringe_terms(tree, tree.children(elem), \
                                        child_seqss, term_to_pos, term_labeling)
                string = DCP_string(lab)
                string.set_edge_label(tree.node_token(elem).edge())
                terms.append(DCP_term(string, arg))
    return terms


def span_to_arg((low, high), children, tree, term_to_pos, term_labeling):
    """
    :type low: int
    :type high: int
    :type children: list[(int, int)]
    :type tree: ConstituentTree
    :param term_to_pos: maps int to int (input position to position in LCFRS rule)
    :type term_labeling: ConstituentTerminalLabeling
    :return: list of LCFRS_var/string
    Turn span into LCFRS arg (variables and terminals).
    Children is list of (sub)spans.
    Also keep list of terminals.
    """
    arg = []
    k = low
    while k <= high:
        match = False
        for i, child in enumerate(children):
            for j, (child_low, child_high) in enumerate(child):
                if child_low == k:
                    arg += [LCFRS_var(i, j)]
                    k = child_high + 1
                    match = True
        if not match:
            arg += [term_labeling.token_label(tree.token_yield()[k])]
            term_to_pos[k] = len(term_to_pos.keys())
            k += 1
    return arg


#####################################################
# Auxiliary.
def sublist_index(s, l):
    """
    :type s: list[int]
    :type l: list[str]
    :rtype: int
    In list of strings and variables, find index of sublist.
    Return -1 if none.
    """
    for k in range(len(l) - len(s) + 1):
        if s == l[k:k + len(s)]:
            return k
    return -1
