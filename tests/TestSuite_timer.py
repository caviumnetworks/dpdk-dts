# BSD LICENSE
#
# Copyright(c) 2010-2014 Intel Corporation. All rights reserved.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#   * Redistributions of source code must retain the above copyright
#     notice, this list of conditions and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright
#     notice, this list of conditions and the following disclaimer in
#     the documentation and/or other materials provided with the
#     distribution.
#   * Neither the name of Intel Corporation nor the names of its
#     contributors may be used to endorse or promote products derived
#     from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""
DPDK Test suite.
Test Timer.
"""

import utils
import re
import time


from test_case import TestCase


class TestTimer(TestCase):

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
        coreMask = utils.create_mask(cores)

        # run timer on the background
        cmdline = "./examples/timer/build/app/timer -n 1 -c " + coreMask + " &"

        self.dut.send_expect(cmdline, "# ", 1)
        time.sleep(15)
        out = self.dut.get_session_output()
        self.dut.send_expect("killall timer", "# ", 5)

        # verify timer0
        utils.regexp(out, r'timer0_cb\(\) on lcore (\d+)')
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
