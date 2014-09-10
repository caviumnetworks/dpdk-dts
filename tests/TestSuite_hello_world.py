# <COPYRIGHT_TAG>

"""
DPDK Test suite.

Test HelloWorld example.
"""

import dcts
from test_case import TestCase

#
#
# Test class.
#


class TestHelloWorld(TestCase):

    #
    #
    #
    # Test cases.
    #

    def set_up_all(self):
        """
        Run at the start of each test suite.
        hello_world Prerequistites:
            helloworld build pass
        """
        out = self.dut.build_dpdk_apps('examples/helloworld')

        self.verify("Error" not in out, "compilation error 1")
        self.verify("No such file" not in out, "compilation error 2")

    def set_up(self):
        """
        Run before each test case.
        Nothing to do.
        """
        pass

    def test_hello_world_single_core(self):
        """
        Run hello world on single lcores
        Only received hello message from core0
        """

        # get the mask for the first core
        cores = self.dut.get_core_list('1S/1C/1T')
        coreMask = dcts.create_mask(cores)
        cmdline = "./examples/helloworld/build/app/helloworld -n 1 -c " + coreMask
        out = self.dut.send_expect(cmdline, "# ", 3)

        self.verify("hello from core %s" % cores[0] in out, "EAL not started on core%s" % cores[0])

    def test_hello_world_all_cores(self):
        """
        Run hello world on all lcores
        Received hello message from all lcores
        """

        # get the maximun logical core number
        cores = self.dut.get_core_list('all')
        coreMask = dcts.create_mask(cores)

        cmdline = "./examples/helloworld/build/app/helloworld -n 1 -c " + coreMask
        out = self.dut.send_expect(cmdline, "# ", 5)

        for i in range(len(cores)):
            self.verify("hello from core %s" % cores[i] in out, "EAL not started on core%s" % cores[i])

    def tear_down(self):
        """
        Run after each test case.
        Nothing to do.
        """
        pass

    def tear_down_all(self):
        """
        Run after each test suite.
        Nothing to do.
        """
        pass
