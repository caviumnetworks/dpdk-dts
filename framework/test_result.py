# <COPYRIGHT_TAG>

"""
Generic result container and reporters
"""


class Result(object):

    """
    Generic result container. Useful to store/retrieve results during
    a DTF execution.

    It manages and hide an internal complex structure like the one shown below.
    This is presented to the user with a property based interface.

    internals = [
        'dut1', [
            'target1', 'nic1', [
                'suite1', [
                    'case1', ['PASSED', ''],
                    'case2', ['PASSED', ''],
                ],
            ],
            'target2', 'nic1', [
                'suite2', [
                    'case3', ['PASSED', ''],
                    'case4', ['FAILED', 'message'],
                ],
                'suite3', [
                    'case5', ['BLOCKED', 'message'],
                ],
            ]
        ]
    ]

    """

    def __init__(self):
        self.__dut = 0
        self.__target = 0
        self.__test_suite = 0
        self.__test_case = 0
        self.__test_result = None
        self.__message = None
        self.__internals = []
        self.__failed_duts = {}
        self.__failed_targets = {}

    def __set_dut(self, dut):
        if dut not in self.__internals:
            self.__internals.append(dut)
            self.__internals.append([])
        self.__dut = self.__internals.index(dut)

    def __get_dut(self):
        return self.__internals[self.__dut]

    def __current_targets(self):
        return self.internals[self.__dut + 1]

    def __set_target(self, target):
        targets = self.__current_targets()
        if target not in targets:
            targets.append(target)
            targets.append('_nic_')
            targets.append([])
        self.__target = targets.index(target)

    def __get_target(self):
        return self.__current_targets()[self.__target]

    def __set_nic(self, nic):
        targets = self.__current_targets()
        targets[self.__target + 1] = nic

    def __get_nic(self):
        targets = self.__current_targets()
        return targets[self.__target + 1]

    def __current_suites(self):
        return self.__current_targets()[self.__target + 2]

    def __set_test_suite(self, test_suite):
        suites = self.__current_suites()
        if test_suite not in suites:
            suites.append(test_suite)
            suites.append([])
        self.__test_suite = suites.index(test_suite)

    def __get_test_suite(self):
        return self.__current_suites()[self.__test_suite]

    def __current_cases(self):
        return self.__current_suites()[self.__test_suite + 1]

    def __set_test_case(self, test_case):
        cases = self.__current_cases()
        cases.append(test_case)
        cases.append([])
        self.__test_case = cases.index(test_case)

    def __get_test_case(self):
        return self.__current_cases()[self.__test_case]

    def __get_test_result(self):
        return self.__test_result

    def __get_message(self):
        return self.__message

    def __get_internals(self):
        return self.__internals

    def __current_result(self):
        return self.__current_cases()[self.__test_case + 1]

    def __set_test_case_result(self, result, message):
        test_case = self.__current_result()
        test_case.append(result)
        test_case.append(message)
        self.__test_result = result
        self.__message = message

    def test_case_passed(self):
        """
        Set last test case added as PASSED
        """
        self.__set_test_case_result(result='PASSED', message='')

    def test_case_failed(self, message):
        """
        Set last test case added as FAILED
        """
        self.__set_test_case_result(result='FAILED', message=message)

    def test_case_blocked(self, message):
        """
        Set last test case added as BLOCKED
        """
        self.__set_test_case_result(result='BLOCKED', message=message)

    def all_duts(self):
        """
        Returns all the DUTs it's aware of.
        """
        return self.__internals[::2]

    def all_targets(self, dut):
        """
        Returns the targets for a given DUT
        """
        try:
            dut_idx = self.__internals.index(dut)
        except:
            return None
        return self.__internals[dut_idx + 1][::3]

    def current_nic(self, dut, target):
        """
        Returns the NIC for a given DUT and target
        """
        try:
            dut_idx = self.__internals.index(dut)
            target_idx = self.__internals[dut_idx + 1].index(target)
        except:
            return None
        return self.__internals[dut_idx + 1][target_idx + 1]

    def all_test_suites(self, dut, target):
        """
        Returns all the test suites for a given DUT and target.
        """
        try:
            dut_idx = self.__internals.index(dut)
            target_idx = self.__internals[dut_idx + 1].index(target)
        except:
            return None
        return self.__internals[dut_idx + 1][target_idx + 2][::2]

    def all_test_cases(self, dut, target, suite):
        """
        Returns all the test cases for a given DUT, target and test case.
        """
        try:
            dut_idx = self.__internals.index(dut)
            target_idx = self.__internals[dut_idx + 1].index(target)
            suite_idx = self.__internals[dut_idx + 1][
                target_idx + 2].index(suite)
        except:
            return None
        return self.__internals[dut_idx + 1][target_idx + 2][suite_idx + 1][::2]

    def result_for(self, dut, target, suite, case):
        """
        Returns the test case result/message for a given DUT, target, test
        suite and test case.
        """
        try:
            dut_idx = self.__internals.index(dut)
            target_idx = self.__internals[dut_idx + 1].index(target)
            suite_idx = self.__internals[dut_idx + 1][
                target_idx + 2].index(suite)
            case_idx = self.__internals[dut_idx + 1][target_idx +
                                                     2][suite_idx + 1].index(case)
        except:
            return None
        return self.__internals[dut_idx + 1][target_idx + 2][suite_idx + 1][case_idx + 1]

    def add_failed_dut(self, dut, msg):
        """
        Sets the given DUT as failing due to msg
        """
        self.__failed_duts[dut] = msg

    def is_dut_failed(self, dut):
        """
        True if the given DUT was marked as failing
        """
        return dut in self.__failed_duts

    def dut_failed_msg(self, dut):
        """
        Returns the reason of failure for a given DUT
        """
        return self.__failed_duts[dut]

    def add_failed_target(self, dut, target, msg):
        """
        Sets the given DUT, target as failing due to msg
        """
        self.__failed_targets[dut + target] = msg

    def is_target_failed(self, dut, target):
        """
        True if the given DUT,target were marked as failing
        """
        return (dut + target) in self.__failed_targets

    def target_failed_msg(self, dut, target):
        """
        Returns the reason of failure for a given DUT,target
        """
        return self.__failed_targets[dut + target]

    """
    Attributes defined as properties to hide the implementation from the
    presented interface.
    """
    dut = property(__get_dut, __set_dut)
    target = property(__get_target, __set_target)
    test_suite = property(__get_test_suite, __set_test_suite)
    test_case = property(__get_test_case, __set_test_case)
    test_result = property(__get_test_result)
    message = property(__get_message)
    nic = property(__get_nic, __set_nic)
    internals = property(__get_internals)
