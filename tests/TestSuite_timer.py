# <COPYRIGHT_TAG>

"""
DPDK Test suite.

Test Timer.

"""

import dcts
import re
import time


from test_case import TestCase

#
#
# Test class.
#


class TestTimer(TestCase):

    #
    #
    #
    # Test cases.
    #

    def set_up_all(self):
        """
        Run at the start of each test suite.


        timer prerequistites
        """
        out = self.dut.build_dpdk_apps('examples/timer')

        self.verify("Error" not in out, "compilation error 1")
        self.verify("No such file" not in out, "compilation error 2")

    def set_up(self):
        """
        Run before each test case.
        """
        pass

    def test_timer_callbacks_verify(self):
        """
        Timer callbacks running on targeted cores
        """

        # get the mask for the first core
        cores = self.dut.get_core_list('1S/1C/1T')
        coreMask = dcts.create_mask(cores)

        # run timer on the background
        cmdline = "./examples/timer/build/app/timer -n 1 -c " + coreMask + " &"

        self.dut.send_expect(cmdline, "# ", 1)
        time.sleep(15)
        out = self.dut.send_expect("killall timer", "# ", 5)

        # verify timer0
        dcts.regexp(out, r'timer0_cb\(\) on lcore (\d+)')
        pat = re.compile(r'timer0_cb\(\) on lcore (\d+)')
        match = pat.findall(out)
        self.verify(match or match[0] == 0, "timer0 error")

        # verify timer1
        pat = re.compile(r'timer1_cb\(\) on lcore (\d+)')
        matchlist = sorted(pat.findall(out))
        self.verify(cmp(list(set(matchlist)), cores) == 0, "timer1 error")

    def tear_down(self):
        """
        Run after each test case.
        """
        pass

    def tear_down_all(self):
        """
        Run after each test suite.
        """
        pass
