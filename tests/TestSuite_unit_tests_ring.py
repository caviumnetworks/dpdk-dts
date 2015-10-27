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

Run all Ring autotests
"""


from test_case import TestCase

#
#
# Test class.
#


class TestUnitTestsRing(TestCase):

    #
    #
    #
    # Test cases.
    #

    def set_up_all(self):
        """
        Run at the start of each test suite.
        """
        out = self.dut.build_dpdk_apps('./app/test/')
        self.verify('make: Leaving directory' in out, "Compilation failed")

    def set_up(self):
        """
        Run before each test case.
        """
        pass

    def test_ring(self):
        """
        Run ring autotest.
        """

        self.dut.send_expect("./app/test/test -n 1 -c ffff", "R.*T.*E.*>.*>", 60)
        out = self.dut.send_expect("ring_autotest", "RTE>>", 36000)
        self.verify("Test OK" in out, "Test failed")
        self.dut.send_expect("set_watermark test 100", "RTE>>")
        out = self.dut.send_expect("dump_ring test", "RTE>>")
        self.dut.send_expect("quit", "# ")
        self.verify("watermark=100" in out, "Test failed")

    def test_ring_performance(self):
        """
        Run ring performance autotest.
        """

        self.dut.send_expect("./app/test/test -n 1 -c fffe", "R.*T.*E.*>.*>", 60)
        out = self.dut.send_expect("ring_perf_autotest", "RTE>>", 210)
        self.dut.send_expect("quit", "# ")
        self.verify("Test OK" in out, "Test failed")

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
