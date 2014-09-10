# <COPYRIGHT_TAG>

"""
Simple text file statistics generator
"""


class StatsReporter(object):

    """
    Generates a small statistics file containing the number of passing,
    failing and blocked tests. It makes use of a Result instance as input.
    """

    def __init__(self, filename):
        self.filename = filename

    def __add_stat(self, test_result):
        if test_result is not None:
            if test_result[0] == 'PASSED':
                self.passed += 1
            if test_result[0] == 'FAILED':
                self.failed += 1
            if test_result[0] == 'BLOCKED':
                self.blocked += 1
            self.total += 1

    def __count_stats(self):
        for dut in self.result.all_duts():
            for target in self.result.all_targets(dut):
                for suite in self.result.all_test_suites(dut, target):
                    for case in self.result.all_test_cases(dut, target, suite):
                        test_result = self.result.result_for(
                            dut, target, suite, case)
                        if len(test_result):
                            self.__add_stat(test_result)

    def __write_stats(self):
        self.__count_stats()
        self.stats_file.write("Passed     = %d\n" % self.passed)
        self.stats_file.write("Failed     = %d\n" % self.failed)
        self.stats_file.write("Blocked    = %d\n" % self.blocked)
        rate = 0
        if self.total > 0:
            rate = self.passed * 100.0 / self.total
        self.stats_file.write("Pass rate  = %.1f\n" % rate)

    def save(self, result):
        self.passed = 0
        self.failed = 0
        self.blocked = 0
        self.total = 0
        self.stats_file = open(self.filename, "w+")
        self.result = result
        self.__write_stats()
        self.stats_file.close()
