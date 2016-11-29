import unittest
from parser.sDCP_parser.sdcp_parser_wrapper import print_grammar, PysDCPParser
from tests.test_induction import hybrid_tree_1, hybrid_tree_2
from dependency.induction import the_terminal_labeling_factory, induce_grammar, cfg
from dependency.labeling import the_labeling_factory
from parser.sDCPevaluation.evaluator import dcp_to_hybridtree, The_DCP_evaluator
from hybridtree.general_hybrid_tree import HybridTree
from hybridtree.monadic_tokens import construct_conll_token
from corpora.conll_parse import parse_conll_corpus
from sys import stderr

class MyTestCase(unittest.TestCase):
    def test_basic_sdcp_parsing(self):
        tree = hybrid_tree_1()
        tree2 = hybrid_tree_2()
        terminal_labeling = the_terminal_labeling_factory().get_strategy('pos')

        (_, grammar) = induce_grammar([tree, tree2],
                                      the_labeling_factory().create_simple_labeling_strategy('empty', 'pos'),
                                      terminal_labeling.token_label, [cfg], 'START')

        for rule in grammar.rules():
            print >>stderr, rule

        PysDCPParser.preprocess_grammar(grammar)

        parser = PysDCPParser(grammar, tree)

        for der in parser.all_derivation_trees():
            print der
            output_tree = HybridTree()
            tokens = tree.token_yield()
            dcp_to_hybridtree(output_tree, The_DCP_evaluator(der).getEvaluation(), tokens, False, construct_conll_token)
            print tree
            print output_tree

    def test_corpus_sdcp_parsing(self):
        def filter_by_id(n, trees):
            j = 0
            for tree in trees:
                if j in n:
                    yield tree
                j += 1
        #params
        train = '../../res/dependency_conll/german/tiger/train/german_tiger_train.conll'
        test = train
        limit_train = 200
        trees = parse_conll_corpus(train, False, limit_train)
        limit_test = 20
        primary_labelling = the_labeling_factory().create_simple_labeling_strategy("child", "deprel")
        term_labelling = the_terminal_labeling_factory().get_strategy('pos')
        start = 'START'
        recursive_partitioning = [cfg]

        (n_trees, grammar_prim) = induce_grammar(trees, primary_labelling, term_labelling.token_label,
                                                     recursive_partitioning, start)
        PysDCPParser.preprocess_grammar(grammar_prim)

        trees = parse_conll_corpus(test, False, limit_test)

        for i, tree in enumerate(trees):
            print >>stderr, "Parsing tree for ", i

            print >>stderr, tree

            parser = PysDCPParser(grammar_prim, tree)
            self.assertTrue(parser.recognized())

            print >>stderr, "Found derivations for ", i
            for der in parser.all_derivation_trees():
                self.assertTrue(der.check_integrity_recursive(der.root_id(), start))
                print >>stderr, der

                output_tree = HybridTree()
                tokens = tree.token_yield()

                the_yield = der.compute_yield()
                # print >>stderr, the_yield
                tokens2 = map(lambda pos: construct_conll_token('_', pos), the_yield)

                dcp_to_hybridtree(output_tree, The_DCP_evaluator(der).getEvaluation(), tokens2, False, construct_conll_token, reorder=False)
                print >>stderr, tree
                print >>stderr, output_tree

                self.compare_hybrid_trees(tree, output_tree)


    def compare_hybrid_trees(self, tree1, tree2):
        self.assertTrue(isinstance(tree1, HybridTree))
        self.assertTrue(isinstance(tree2, HybridTree))
        self.compare_hybrid_trees_rec(tree1, tree1.root, tree2, tree2.root)

    def compare_hybrid_trees_rec(self, tree1, ids1, tree2, ids2):
        self.assertEqual(len(ids1), len(ids2))
        for id1, id2 in zip(ids1, ids2):
            token1 = tree1.node_token(id1)
            token2 = tree2.node_token(id2)
            self.assertEqual(token1.pos(), token2.pos())
            self.assertEqual(token1.deprel(), token2.deprel())
            self.compare_hybrid_trees_rec(tree1, tree1.children(id1), tree2, tree2.children(id2))


if __name__ == '__main__':
    unittest.main()
