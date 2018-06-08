import unittest
import corpora.negra_parse as np
import corpora.tiger_parse as tp
from hybridtree.general_hybrid_tree import HybridDag
from hybridtree.monadic_tokens import construct_constituent_token
from constituent.dag_induction import direct_extract_lcfrs_from_prebinarized_corpus, top, bottom
from parser.naive.parsing import LCFRS_parser
from parser.sDCPevaluation.evaluator import DCP_evaluator, dcp_to_hybriddag
import tempfile
import copy
import subprocess


class MyTestCase(unittest.TestCase):
    def test_negra_to_dag_parsing(self):
        pass
        names = list(map(str, [26954]))

        fd_, primary_file = tempfile.mkstemp(suffix='.export')
        with open(primary_file, mode='w') as pf:

            for s in names:
                dsg = tp.sentence_names_to_deep_syntax_graphs([s], "res/tiger/tiger_s%s.xml" % s, hold=False,
                                                              ignore_puntcuation=False)[0]
                dsg.set_label(dsg.label[1:])
                lines = np.serialize_hybrid_dag_to_negra([dsg], 0, 500, use_sentence_names=True)
                print(''.join(lines), file=pf)

        _, binarized_file = tempfile.mkstemp(suffix='.export')
        subprocess.call(["discodop", "treetransforms", "--binarize", "-v", "1", "-h", "1", primary_file, binarized_file])

        print(primary_file)
        print(binarized_file)

        corpus = np.sentence_names_to_hybridtrees(names, primary_file, secedge=True)
        corpus2 = np.sentence_names_to_hybridtrees(names, binarized_file, secedge=True)
        dag = corpus[0]
        print(dag)
        assert isinstance(dag, HybridDag)
        self.assertEqual(8, len(dag.token_yield()))
        for token in dag.token_yield():
            print(token.form() + '/' + token.pos(), end=' ')
        print()

        dag_bin = corpus2[0]
        print(dag_bin)

        for token in dag_bin.token_yield():
            print(token.form() + '/' + token.pos(), end=' ')
        print()
        self.assertEqual(8, len(dag_bin.token_yield()))

        for node, token in zip(dag_bin.nodes(), list(map(str, map(dag_bin.node_token, dag_bin.nodes())))):
            print(node, token)

        print()
        print(top(dag_bin, {'500', '101', '102'}))
        self.assertSetEqual({'101', '500'}, top(dag_bin, {'500', '101', '102'}))
        print(bottom(dag_bin, {'500', '101', '102'}))
        self.assertSetEqual({'502'}, bottom(dag_bin, {'500', '101', '102'}))
        grammar = direct_extract_lcfrs_from_prebinarized_corpus(dag_bin)
        print(grammar)

        parser = LCFRS_parser(grammar)

        poss = list(map(lambda x: x.pos(), dag_bin.token_yield()))
        print(poss)
        parser.set_input(poss)

        parser.parse()

        self.assertTrue(parser.recognized())

        der = parser.best_derivation_tree()
        print(der)

        dcp_term = DCP_evaluator(der).getEvaluation()

        print(dcp_term[0])

        dag_eval = HybridDag(dag_bin.sent_label())
        dcp_to_hybriddag(dag_eval, dcp_term, copy.deepcopy(dag_bin.token_yield()), False, construct_token=construct_constituent_token)

        print(dag_eval)
        for node in dag_eval.nodes():
            token = dag_eval.node_token(node)
            if token.type() == "CONSTITUENT-CATEGORY":
                label = token.category()
            elif token.type() == "CONSTITUENT-TERMINAL":
                label = token.form(), token.pos()

            print(node, label, dag_eval.children(node), dag_eval.sec_children(node), dag_eval.sec_parents(node))

        lines = np.serialize_hybridtrees_to_negra([dag_eval], 1, 500, use_sentence_names=True)
        for line in lines:
            print(line, end='')

        print()

        with open(primary_file) as pcf:
            for line in pcf:
                print(line, end='')


if __name__ == '__main__':
    unittest.main()
