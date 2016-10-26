# BSD LICENSE
#
# Copyright(c) 2010-2016 Intel Corporation. All rights reserved.
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
Test internal and external mempool handler
"""

import utils
from test_case import TestCase


class TestMemExthandler(TestCase):

    def set_up_all(self):
        """
        Run at the start of each test suite.
        """
        # only one port is enought for this case
        self.dut_ports = self.dut.get_ports()
        self.verify(len(self.dut_ports) >= 1,
                    "Not enough ports for " + self.nic)

        self.core_mask = utils.create_mask(self.dut.get_core_list("1S/4C/1T"))
        self.port_mask = utils.create_mask([self.dut_ports[0]])

        self.path = "./examples/l2fwd/build/app/l2fwd"

        # strip mempool size
        self.main_path = "./examples/l2fwd/main.c"
        out = self.dut.send_expect(
            "cat %s | grep \"#define NB_MBUF\"" % self.main_path, "# ")
        mp_str = utils.regexp(out, r"#define NB_MBUF   (\d+)")
        if mp_str is None:
            mp_size = 8192
        else:
            mp_size = int(mp_str)

        # make sure packets more than 2*mempool size
        self.pkts = mp_size * 2 + 1000

    def set_up(self):
        """
        Run before each test case.
        """
        pass

    def setup_mempool_handler(self, name):
        """
        Prepare testing environment for specified mempool handler
        """
        config = "CONFIG_RTE_MBUF_DEFAULT_MEMPOOL_OPS"
        conf_file = "./config/common_base"
        # change default mempool handler operations
        self.dut.send_expect(
            "sed -i 's/%s=.*$/%s=\"%s\"/' %s" % (config, config, name, conf_file), "# ")
        # rebuild dpdk target
        self.dut.skip_setup = False
        self.dut.build_install_dpdk(self.target)
        # rebuild l2fwd
        out = self.dut.build_dpdk_apps("./examples/l2fwd")
        self.verify("Error" not in out, "Compilation error")

    def verify_mempool_hander(self):
        """
        Verify all packets recevied and transmitted normally.
        """
        # start l2fwd
        command_line = "%s -n %d -c %s -- -q 4 -p %s" % \
            (self.path, self.dut.get_memory_channels(),
             self.core_mask, self.port_mask)
        # send packets over 2 * mempool size
        self.dut.send_expect(command_line, "L2FWD: entering main loop", 60)

        # verify forwarded packets
        traffic_flow = []
        tx_port = self.tester.get_local_port(self.dut_ports[0])
        rx_port = self.tester.get_local_port(self.dut_ports[0])
        traffic_flow.append((tx_port, rx_port))

        result = self.tester.check_random_pkts(traffic_flow,
                                               pktnum=self.pkts,
                                               allow_miss=False)

        self.verify(result is True, "Packet integrity check failed")

        # strip rx/tx statistic from l2fwd output
        out = self.dut.get_session_output()
        sent_list = utils.regexp(out, r"Total packets sent:(\s+)(\d+)", allString=True)
        total_sent = int(sent_list[-1][1])
        rcv_list = utils.regexp(out, r"Total packets received:(\s+)(\d+)", allString=True)
        total_recv = int(rcv_list[-1][1])

        self.verify(total_recv == self.pkts, "L2fwd sample not receive expected packets")
        self.verify(total_sent == self.pkts, "L2fwd sample not transmit expected packets")

    def test_mempool_stackhandler(self):
        """
        Check packet rx/tx work with mempool stack handler.
        """
        self.setup_mempool_handler("stack")
        self.verify_mempool_hander()

    def test_mempool_spsc(self):
        """
        Check packet rx/tx work with single producer/single consumer.
        """
        self.setup_mempool_handler("ring_sp_sc")
        self.verify_mempool_hander()

    def test_mempool_spmc(self):
        """
        Check packet rx/tx work with single producer/multi consumers.
        """
        self.setup_mempool_handler("ring_sp_mc")
        self.verify_mempool_hander()

    def test_mempool_mpsc(self):
        """
        Check packet rx/tx work with multi producers/single consumer.
        """
        self.setup_mempool_handler("ring_mp_sc")
        self.verify_mempool_hander()

    def test_mempool_mpmc(self):
        """
        Check packet rx/tx work with multi producers/multi consumers.
        """
        self.setup_mempool_handler("ring_mp_mc")
        self.verify_mempool_hander()

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
        self.setup_mempool_handler("ring_mp_mc")
        pass
