__author__ = 'kilian'

import unittest
from general_hybrid_tree import GeneralHybridTree


class GeneralHybridTreeTestCase(unittest.TestCase):
    tree = None

    def setUp(self):
        self.tree = GeneralHybridTree()
        self.tree.add_node("v1", "Piet", "NP", True)
        self.tree.add_node("v21", "Marie", "N", True)
        self.tree.add_node("v", "helpen", "VP", True)
        self.tree.add_node("v2", "lezen", "V", True)
        self.tree.add_child("v", "v2")
        self.tree.add_child("v", "v1")
        self.tree.add_child("v2", "v21")
        self.tree.add_node("v3", ".", "Punc", True, False)
        self.tree.set_root("v")

    def test_children(self):
        self.assertListEqual(self.tree.children('v'), ['v2','v1'])
        self.tree.reorder()
        self.assertListEqual(self.tree.children('v'), ['v1','v2'])

    def test_fringe(self):
        self.tree.reorder()
        self.assertListEqual(self.tree.fringe('v'), [2,0,3,1])
        self.assertListEqual(self.tree.fringe('v2'), [3,1])

    def test_n_spans(self):
        self.tree.reorder()
        self.assertEqual(self.tree.n_spans('v'), 1)
        self.assertEqual(self.tree.n_spans('v2'), 2)

    def test_n_gaps(self):
        self.tree.reorder()
        self.assertEqual(self.tree.n_gaps(), 1)

    def test_node_ids(self):
        self.tree.reorder()
        self.assertItemsEqual(self.tree.nodes(), ['v','v1','v2','v21', 'v3'])

    def test_complete(self):
        self.tree.reorder()
        self.assertEqual(self.tree.complete(), True)

    def test_unlabelled_structure(self):
        self.tree.reorder()
        self.assertTupleEqual(self.tree.unlabelled_structure(), (set([0, 1, 2, 3]), [(set([0]), []), (set([1, 3]), [(set([1]), [])])]))

    def test_max_n_spans(self):
        self.tree.reorder()
        self.assertEqual(self.tree.max_n_spans(), 2)

    def test_labelled_yield(self):
        self.tree.reorder()
        self.assertListEqual(self.tree.labelled_yield(), "Piet Marie helpen lezen".split(' '))

    def test_full_labelled_yield(self):
        self.tree.reorder()
        self.assertListEqual(self.tree.full_labelled_yield(), "Piet Marie helpen lezen .".split(' '))

    def test_full_yield(self):
        self.tree.reorder()
        self.assertListEqual(self.tree.full_yield(), 'v1 v21 v v2 v3'.split(' '))

    def test_labelled_spans(self):
        self.tree.reorder()
        self.assertListEqual(self.tree.labelled_spans(), [])

    def test_pos_yield(self):
        self.tree.reorder()
        self.assertListEqual(self.tree.pos_yield(), "NP N VP V".split(' '))

if __name__ == '__main__':
    unittest.main()
