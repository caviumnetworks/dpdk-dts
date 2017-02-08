# BSD LICENSE
#
# Copyright(c) 2010-2017 Intel Corporation. All rights reserved.
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
Test external mempool handler
"""

import utils
from test_case import TestCase
from pmd_output import PmdOutput


class TestExternalMempool(TestCase):

    def set_up_all(self):
        """
        Run at the start of each test suite.
        """
        self.dut_ports = self.dut.get_ports()

        self.verify(len(self.dut_ports) >= 2, "Not enough ports")

        self.pmdout = PmdOutput(self.dut)

    def set_up(self):
        """
        Run before each test case.
        """
        pass

    def change_mempool_ops(self, ops=''):
        self.dut.send_expect("sed -i 's/CONFIG_RTE_MBUF_DEFAULT_MEMPOOL_OPS=.*$/CONFIG_RTE_MBUF_DEFAULT_MEMPOOL_OPS=\"%s\"/' ./config/common_base" % ops, "# ")
        self.dut.build_install_dpdk(self.target)

    def verify_unit_func(self):
        self.dut.send_expect("./%s/app/test -n 4 -c f" % self.target, "R.*T.*E.*>.*>", 60)
        out = self.dut.send_expect("mempool_autotest", "RTE>>", 120)
        self.dut.send_expect("quit", "# ")
        self.verify("Test OK" in out, "Mempool autotest failed")

    def verify_unit_perf(self):
        self.dut.send_expect("./%s/app/test -n 4 -c f" % self.target, "R.*T.*E.*>.*>", 60)
        out = self.dut.send_expect("mempool_perf_autotest", "RTE>>", 1200)
        self.dut.send_expect("quit", "# ")
        # may need to compare performance
        self.verify("Test OK" in out, "Mempool performance autotest failed")

    def verify_app_func(self):
        # start testpmd
        self.pmdout.start_testpmd("1S/2C/1T", "--portmask=0x3")
        self.pmdout.execute_cmd("set fwd mac")
        self.pmdout.execute_cmd("start")

        tgen_input = []
        tx_port = self.tester.get_local_port(self.dut_ports[0])
        rx_port = self.tester.get_local_port(self.dut_ports[1])
        tgen_input.append((tx_port, rx_port))

        tx_port = self.tester.get_local_port(self.dut_ports[1])
        rx_port = self.tester.get_local_port(self.dut_ports[0])
        tgen_input.append((tx_port, rx_port))

        result = self.tester.check_random_pkts(tgen_input, allow_miss=False)

        self.pmdout.quit()

        self.verify(result is True, "Mempool function check failed with testpmd")

    def test_mempool_handler_default(self):
        """
        Verify default mempool ops
        """
        self.verify_unit_func()
        self.verify_app_func()

    def test_mempool_handler_sp_sc(self):
        """
        Verify mempool single produce single customer ops
        """
        self.change_mempool_ops(ops='ring_sp_sc')
        self.verify_unit_func()
        self.verify_app_func()

    def test_mempool_handler_sp_mc(self):
        """
        Verify mempool single produce multiple customer ops
        """
        self.change_mempool_ops(ops='ring_sp_mc')
        self.verify_unit_func()
        self.verify_app_func()

    def test_mempool_handler_mp_sc(self):
        """
        Verify mempool multiple produce single customer ops
        """
        self.change_mempool_ops(ops='ring_mp_sc')
        self.verify_unit_func()
        self.verify_app_func()

    def test_mempool_handler_stack(self):
        """
        Verify external mempool handler stack ops
        """
        self.change_mempool_ops(ops='stack')
        self.verify_unit_func()
        self.verify_app_func()

    def tear_down(self):
        """
        Run after each test case.
        """
        self.dut.kill_all()
        pass

    def tear_down_all(self):
        """
        Run after each test suite.
        """
        self.change_mempool_ops(ops='ring_mp_mc')
