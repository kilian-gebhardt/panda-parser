# Auxiliary classes to determine parsing accuracy.

# Keep records needed to compute recall/precision.
class ParseAccuracy(object):
    # Constructor.
    def __init__(self):
        # Sum of sentence precisions
        self.__precisions = 0
        # Sum of sentence recalls
        self.__recalls = 0
        # Sum of sentence F-measures
        self.__fmeasures = 0
        # Number of sentences
        self.__n = 0
        # Number of sentences where parsing failed.
        self.__n_failures = 0

    # Compare two sets of lists. Process accuracy.
    # found: list of things convertable to tuple
    # correct: list of things convertable to tuple
    def add_accuracy(self, found, correct):
        retrieved = set([tuple(t) for t in found])
        relevant = set([tuple(t) for t in correct])
        inters = retrieved & relevant

        # happens in case of parse failure
        # there are two options here:
        #   - parse failure -> no spans at all, thus precision = 1
        #   - parse failure -> a dummy tree with all spans wrong, thus precision = 0
        precision = 1.0 * len(inters) / len(retrieved) \
            if len(retrieved) > 0 else 0
        recall = 1.0 * len(inters) / len(relevant) \
            if len(relevant) > 0 else 0
        fmeasure = 2.0 * precision * recall / (precision + recall) \
            if precision + recall > 0 else 0

        self.__precisions += precision
        self.__recalls += recall
        self.__fmeasures += fmeasure
        self.__n += 1

    # Count one more failure.
    def add_failure(self, correct=[]):
        self.__n_failures += 1

    # Get number of instances.
    # return: int
    def n(self):
        return self.__n

    # Number of sentences where parsing failed.
    # return: int
    def n_failures(self):
        return self.__n_failures

    # Average precision.
    # return: float
    def precision(self):
        return self.__precisions / self.__n

    # Average recall.
    # return: float
    def recall(self):
        return self.__recalls / self.__n

    # Average F-measure.
    # return: float
    def fmeasure(self):
        return self.__fmeasures / self.__n


# Keep records needed to compute recall/precision.
class ParseAccuracyPenalizeFailures(ParseAccuracy):
    def __init__(self):
        super(ParseAccuracyPenalizeFailures, self).__init__()
    # Count one more failure.
    def add_failure(self, correct=[]):
        super(ParseAccuracyPenalizeFailures, self).add_failure()
        self.add_accuracy([], correct)
