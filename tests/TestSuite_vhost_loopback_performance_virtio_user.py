#
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
Test Vhost loopback performance for Mergeable, normal , vector Path
"""
import os
import string
import utils
import time
import re
from test_case import TestCase


class TestVhostLoopback(TestCase):

    def set_up_all(self):
        """
        Run at the start of each test suite.
        """
        # Clean the execution environment
        self.dut.send_expect("rm -rf ./vhost.out", "#")
        self.dut.send_expect("rm -rf ./vhost-net*", "#")
        self.header_row = ["FrameSize(B)", "Mode", "Throughput(Mpps)", "Virtio Version"]
        self.frame_sizes = [64, 128, 260, 520, 1024, 1500]
        self.test_cycles = {'Mpps': {}, 'pct': {}}
        # Don't use any NIC in this test case
        port_list = self.dut.get_ports()
        for i in port_list:
            port = self.dut.ports_info[i]['port']
            port.bind_driver()
        # Get the default TX packet size of the testpmd
        out = self.dut.send_expect("cat app/test-pmd/testpmd.h |grep TXONLY_DEF_PACKET_LEN", "# ")
        try:
            search_result = re.search("#define TXONLY_DEF_PACKET_LEN\s*(\d*)", out)
            self.packet_length = search_result.group(1)
        except:
            self.logger.error("Failed to capture default testpmd txonly packet length")

    def set_up(self):
        """
        Run before each test case.
        """
        pass

    def test_perf_vhost_mergeable_loopback(self):
        """
        Benchmark performance for frame_sizes.
        """
        self.result_table_create(self.header_row)
        # Modify the driver file to disbale the Mergeable, then re-compile the DPDK and back up the original driver file
        for frame_size in self.frame_sizes:
            # Back up the original driver file
            self.dut.send_expect("cp ./drivers/net/virtio/virtio_ethdev.h ./", "#", 30)
            # Change the packet size sent by the testpmd
            self.change_testpmd_size = "sed -i -e 's/#define TXONLY_DEF_PACKET_LEN.*$/#define TXONLY_DEF_PACKET_LEN %d/' ./app/test-pmd/testpmd.h" % frame_size
            self.dut.send_expect(self.change_testpmd_size, "#", 30)
            self.dut.build_install_dpdk(self.dut.target)

            # Start the vhost user side
            cmd = self.target + "/app/testpmd -n 4 -c 0x03 " + \
                  "-m 2048 --file-prefix=vhost --vdev 'net_vhost0,iface=vhost-net,queues=1,client=0' -- -i"
            self.dut.send_expect(cmd, "testpmd>", 120)
            # Start the virtio_user side
            vhost_user = self.dut.new_session()
            command_line_user = self.target + "/app/testpmd -n 4 -c 0x0c " + \
                                " -m 2048 --no-pci --file-prefix=virtio " + \
                                " --vdev=net_virtio_user0,mac=00:01:02:03:04:05,path=./vhost-net" + \
                                " -- -i --txqflags=0xf01 --disable-hw-vlan-filter"

            vhost_user.send_expect(command_line_user, "testpmd>", 120)

            self.dut.send_expect("set fwd mac retry", "testpmd>", 60)
            self.dut.send_expect("start tx_first 32", "testpmd>", 60)
            vhost_user.send_expect("start tx_first 32", "testpmd> ", 120)
            results = 0.0
            out = self.dut.send_expect("show port stats all", "testpmd>", 60)
            time.sleep(5)
            # Get throughput 10 times and calculate the average throughput
            for i in range(10):
                out = self.dut.send_expect("show port stats all", "testpmd>", 60)
                time.sleep(5)
                lines = re.search("Rx-pps:\s*(\d*)", out)
                result = lines.group(1)
                results += float(result)
            Mpps = results / (1000000 * 10)

            self.dut.send_expect("quit", "#", 60)
            vhost_user.send_expect("quit", "#", 60)
            # Restore the driver file
            self.dut.send_expect("rm -rf ./drivers/net/virtio/virtio_ethdev.h", "#", 30)
            self.dut.send_expect("mv ./virtio_ethdev.h ./drivers/net/virtio/", "#", 30)
            self.test_cycles['Mpps'][frame_size] = Mpps
            self.test_cycles['pct'][frame_size] = "Virtio 0.95"

        for frame_size in self.frame_sizes:
            results_row = [frame_size]
            results_row.append("Mergeable on")
            results_row.append(self.test_cycles['Mpps'][frame_size])
            results_row.append(self.test_cycles['pct'][frame_size])
            self.result_table_add(results_row)

        self.result_table_print()
        # Change the packet size of testpmd to default number 64

    def test_perf_vhost_vector_loopback(self):
        """
        Benchmark performance for frame_sizes.
        """
        self.result_table_create(self.header_row)
        for frame_size in self.frame_sizes:
            # Modify the driver file to disbale the Mergeable, then re-compile the DPDK and back up the original driver file
            self.dut.send_expect("cp ./drivers/net/virtio/virtio_ethdev.h ./", "#", 30)
            self.dut.send_expect("sed -i '/VIRTIO_NET_F_MRG_RXBUF/d' ./drivers/net/virtio/virtio_ethdev.h", "#", 30)
            self.change_testpmd_size = "sed -i -e 's/#define TXONLY_DEF_PACKET_LEN .*$/#define TXONLY_DEF_PACKET_LEN %d/' ./app/test-pmd/testpmd.h" % frame_size
            self.dut.send_expect(self.change_testpmd_size, "#", 30)
            self.dut.build_install_dpdk(self.dut.target)

            # Start the vhost user side
            cmd = self.target + "/app/testpmd -n 4 -c 0x03 " + \
                  "-m 2048 --file-prefix=vhost --vdev 'net_vhost0,iface=vhost-net,queues=1,client=0' -- -i"
            self.dut.send_expect(cmd, "testpmd>", 120)
            # Start the virtio_user side
            vhost_user = self.dut.new_session()
            command_line_user = self.target + "/app/testpmd -n 4 -c 0x0c " + \
                                " -m 2048 --no-pci --file-prefix=virtio " + \
                                " --vdev=net_virtio_user0,mac=00:01:02:03:04:05,path=./vhost-net " + \
                                " -- -i --txqflags=0xf01 --disable-hw-vlan-filter"

            vhost_user.send_expect(command_line_user, "testpmd>", 120)

            self.dut.send_expect("set fwd mac retry", "testpmd>", 60)
            self.dut.send_expect("start tx_first 32", "testpmd>", 60)
            vhost_user.send_expect("start tx_first 32", "testpmd> ", 120)
            results = 0.0
            out = self.dut.send_expect("show port stats all", "testpmd>", 60)
            time.sleep(5)
            # Get throughput 10 times and calculate the average throughput
            for i in range(10):
                out = self.dut.send_expect("show port stats all", "testpmd>", 60)
                time.sleep(5)
                lines = re.search("Rx-pps:\s*(\d*)", out)
                result = lines.group(1)
                results += float(result)
            Mpps = results / (1000000 * 10)

            self.dut.send_expect("quit", "#", 60)
            vhost_user.send_expect("quit", "#", 60)
            # Restore the driver file
            self.dut.send_expect("rm -rf ./drivers/net/virtio/virtio_ethdev.h", "#", 30)
            self.dut.send_expect("mv ./virtio_ethdev.h ./drivers/net/virtio/", "#", 30)
            self.test_cycles['Mpps'][frame_size] = Mpps
            self.test_cycles['pct'][frame_size] = "Virtio 0.95"

        for frame_size in self.frame_sizes:
            results_row = [frame_size]
            results_row.append("Vector on")
            results_row.append(self.test_cycles['Mpps'][frame_size])
            results_row.append(self.test_cycles['pct'][frame_size])
            self.result_table_add(results_row)

        self.result_table_print()

    def test_perf_vhost_normal_loopback(self):
        """
        Benchmark performance for frame_sizes.
        """

        self.result_table_create(self.header_row)
        for frame_size in self.frame_sizes:
            # Modify the driver file to disbale the Mergeable, then re-compile the DPDK and back up the original driver file
            self.dut.send_expect("cp ./drivers/net/virtio/virtio_ethdev.h ./", "#", 30)
            self.dut.send_expect("sed -i '/VIRTIO_NET_F_MRG_RXBUF/d' ./drivers/net/virtio/virtio_ethdev.h", "#", 30)
            self.change_testpmd_size = "sed -i -e 's/#define TXONLY_DEF_PACKET_LEN .*$/#define TXONLY_DEF_PACKET_LEN %d/' ./app/test-pmd/testpmd.h" % frame_size
            self.dut.send_expect(self.change_testpmd_size, "#", 30)
            self.dut.build_install_dpdk(self.dut.target)

            # Start the vhost user side
            cmd = self.target + "/app/testpmd -n 4 -c 0x03 " + \
                  "-m 2048 --file-prefix=vhost --vdev 'net_vhost0,iface=vhost-net,queues=1,client=0' -- -i"
            self.dut.send_expect(cmd, "testpmd>", 120)
            # Start the virtio_user side
            vhost_user = self.dut.new_session()
            command_line_user = self.target + "/app/testpmd -n 4 -c 0x0c " + \
                                " -m 2048 --no-pci --file-prefix=virtio " + \
                                " --vdev=net_virtio_user0,mac=00:01:02:03:04:05,path=./vhost-net" + \
                                " -- -i --txqflags=0xf00 --disable-hw-vlan-filter"

            vhost_user.send_expect(command_line_user, "testpmd>", 120)

            self.dut.send_expect("set fwd mac retry", "testpmd>", 60)
            self.dut.send_expect("start tx_first 32", "testpmd>", 60)
            vhost_user.send_expect("start tx_first 32", "testpmd> ", 120)
            results = 0.0
            out = self.dut.send_expect("show port stats all", "testpmd>", 60)
            time.sleep(5)
            # Get throughput 10 times and calculate the average throughput
            for i in range(10):
                out = self.dut.send_expect("show port stats all", "testpmd>", 60)
                time.sleep(5)
                lines = re.search("Rx-pps:\s*(\d*)", out)
                result = lines.group(1)
                results += float(result)
            Mpps = results / (1000000 * 10)

            self.dut.send_expect("quit", "#", 60)
            vhost_user.send_expect("quit", "#", 60)
            # Restore the driver file
            self.dut.send_expect("rm -rf ./drivers/net/virtio/virtio_ethdev.h", "#", 30)
            self.dut.send_expect("mv ./virtio_ethdev.h ./drivers/net/virtio/", "#", 30)
            self.test_cycles['Mpps'][frame_size] = Mpps
            self.test_cycles['pct'][frame_size] = "Virtio 0.95"

        for frame_size in self.frame_sizes:
            results_row = [frame_size]
            results_row.append("Normal")
            results_row.append(self.test_cycles['Mpps'][frame_size])
            results_row.append(self.test_cycles['pct'][frame_size])
            self.result_table_add(results_row)

        self.result_table_print()

    def tear_down(self):
        """
        Run after each test case.
        """
        time.sleep(2)

    def tear_down_all(self):
        """
        Run after each test suite.
        """
        # Recompile the dpdk because we change the source code during the test
        self.dut.build_install_dpdk(self.dut.target)
        # Re-bind the port to config driver
        port_list = self.dut.get_ports()
        for i in port_list:
            port = self.dut.ports_info[i]['port']
            port.bind_driver(self.drivername)
        # Set the tx packet size of testpmd to default size
        self.dut.send_expect("sed -i -e 's/#define TXONLY_DEF_PACKET_LEN.*$/#define TXONLY_DEF_PACKET_LEN %s/' ./app/test-pmd/testpmd.h" % self.packet_length, "#", 30)
