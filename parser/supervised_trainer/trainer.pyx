from libcpp.vector cimport vector
from libcpp.memory cimport make_shared, shared_ptr
from cython.operator cimport dereference as deref
from parser.trace_manager.trace_manager cimport PyTraceManager, TraceManagerPtr, build_trace_manager_ptr
from util.enumerator cimport Enumerator
from parser.derivation_interface import AbstractDerivation

ctypedef size_t NONTERMINAL

cdef extern from "Manage/Manager.h":
    cppclass Element[InfoT]:
        pass

cdef extern from "Manage/Hypergraph.h" namespace "Manage":
    cppclass Node[NodeLabelT]:
        pass
    cppclass HyperEdge[NodeT, LabelT]:
        pass
    cppclass Hypergraph[NodeLabelT, EdgeLabelT]:
        Hypergraph(shared_ptr[vector[NodeLabelT]] nLabels
                   , shared_ptr[vector[EdgeLabelT]] eLabels)
        Element[Node[NodeLabelT]] create(NodeLabelT nLabel)
        Element[HyperEdge[Node[NodeLabelT], EdgeLabelT]] add_hyperedge(
                EdgeLabelT eLabel
                , Element[Node[NodeLabelT]]& target
                , vector[Element[Node[NodeLabelT]]]& sources
                )

cdef extern from "Trainer/TraceManager.h" namespace "Trainer":
    cdef void add_hypergraph_to_trace[Nonterminal, TraceID](
            TraceManagerPtr[Nonterminal, TraceID] manager
            , shared_ptr[Hypergraph[Nonterminal, size_t]] hypergraph
            , Element[Node[Nonterminal]] root)


cdef class PyElement:
    cdef shared_ptr[Element[Node[NONTERMINAL]]] element
    def __cinit__(self):
        self.element = shared_ptr[Element[Node[NONTERMINAL]]]()
         # self.element = make_shared[Element[Node[NONTERMINAL]]](element)

cdef class PyDerivationManager(PyTraceManager):
    cdef shared_ptr[vector[NONTERMINAL]] node_labels
    cdef shared_ptr[vector[size_t]] edge_labels
    cdef Enumerator nonterminal_map

    def __init__(self, grammar, Enumerator nonterminal_map=None):
        """
        :param grammar:
        :type grammar: PyLCFRS
        """
        if nonterminal_map is None:
            nonterminal_map = Enumerator()
            for nont in grammar.nonts():
                nonterminal_map.object_index(nont)
        cdef vector[NONTERMINAL] node_labels = range(0, nonterminal_map.counter)
        self.node_labels = make_shared[vector[NONTERMINAL]](node_labels)
        cdef vector[size_t] edge_labels = range(0, len(grammar.rule_index()))
        self.edge_labels = make_shared[vector[size_t]](edge_labels)
        self.nonterminal_map = nonterminal_map

        self.trace_manager = build_trace_manager_ptr[NONTERMINAL, size_t](self.node_labels
            , self.edge_labels
            , False)

    cpdef void convert_hypergraphs(self, corpus):
        cdef shared_ptr[Hypergraph[NONTERMINAL, size_t]] hg
        cdef vector[Element[Node[NONTERMINAL]]] sources
        cdef PyElement pyElement

        for derivation in corpus:
            assert(isinstance(derivation, AbstractDerivation))
            hg = make_shared[Hypergraph[NONTERMINAL, size_t]](self.node_labels, self.edge_labels)
            nodeMap = {}

            # create nodes
            for node in derivation.ids():
                nont = derivation.getRule(node).lhs().nont()
                nLabel = self.nonterminal_map.object_index(nont)
                pyElement2 = PyElement()
                pyElement2.element = make_shared[Element[Node[NONTERMINAL]]](deref(hg).create(nLabel))
                nodeMap[node] = pyElement2

            # create edges
            for node in derivation.ids():
                eLabel = derivation.getRule(node).get_idx()
                for child in derivation.child_ids(node):
                    # nont = derivation.getRule(nont).lhs().nont()
                    pyElement = nodeMap[child]
                    sources.push_back(deref(pyElement.element))

                # target
                pyElement = nodeMap[node]
                deref(hg).add_hyperedge(eLabel, deref(pyElement.element), sources)
                sources.clear()

            # root
            pyElement = nodeMap[derivation.root_id()]
            add_hypergraph_to_trace[NONTERMINAL, size_t](self.trace_manager, hg, deref(pyElement.element))
            # nodeMap.clear()

    cpdef Enumerator get_nonterminal_map(self):
        return self.nonterminal_map

