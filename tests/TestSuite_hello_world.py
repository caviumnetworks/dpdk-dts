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
Test HelloWorld example.
"""

import dts
from test_case import TestCase

class TestHelloWorld(TestCase):

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
        coreMask = dts.create_mask(cores)
        cmdline = "./examples/helloworld/build/app/helloworld -n 1 -c " + coreMask
        out = self.dut.send_expect(cmdline, "# ", 30)
        self.verify("hello from core %s" % cores[0] in out, "EAL not started on core%s" % cores[0])

    def test_hello_world_all_cores(self):
        """
        Run hello world on all lcores
        Received hello message from all lcores
        """

        # get the maximun logical core number
        cores = self.dut.get_core_list('all')
        coreMask = dts.create_mask(cores)

        cmdline = "./examples/helloworld/build/app/helloworld -n 1 -c " + coreMask
        out = self.dut.send_expect(cmdline, "# ", 50)
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
