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

Vhost PVP performance using Qemu test suite.
"""
import os
import re
import time
import utils
from scapy.utils import wrpcap, rdpcap
from test_case import TestCase
from exception import VerifyFailure
from settings import HEADER_SIZE
from etgen import IxiaPacketGenerator
from qemu_kvm import QEMUKvm


class TestVhostUserOneCopyOneVm(TestCase):

    def set_up_all(self):
        # Get and verify the ports
        self.dut_ports = self.dut.get_ports()
        self.verify(len(self.dut_ports) >= 1, "Insufficient ports for testing")

        # Get the port's socket
        self.pf = self.dut_ports[0]
        netdev = self.dut.ports_info[self.pf]['port']
        self.socket = netdev.get_nic_socket()
        self.cores = self.dut.get_core_list("1S/3C/1T", socket=self.socket)

        # Set the params of vhost sample
        self.vhost_app = "./examples/vhost/build/vhost-switch"
        self.vm2vm = 0
        # This parameter is used to define mergeable on/off
        self.jumbo = 0

        # Using file to save the vhost sample output since in jumboframe case,
        # there will be lots of output
        self.vhost_test = self.vhost_app + \
            " -c %s -n %d --socket-mem 2048,2048  -- -p 0x1 --mergeable %d" + \
            " --vm2vm %d --socket-file ./vhost-net  > ./vhost.out &"
        # build the vhost sample in vhost-user mode.
        if self.nic in ['niantic']:
            self.dut.send_expect(
                "sed -i -e 's/#define MAX_QUEUES.*$/#define MAX_QUEUES 128/' "
                "./examples/vhost/main.c",
                "#", 10)
        elif self.nic.startswith('fortville'):
            self.dut.send_expect(
                "sed -i -e 's/#define MAX_QUEUES.*$/#define MAX_QUEUES 512/' "
                "./examples/vhost/main.c",
                "#", 10)
        out = self.dut.send_expect("make -C examples/vhost", "#")
        self.verify("Error" not in out, "compilation error")
        self.verify("No such file" not in out, "Not found file error")

        self.virtio1 = "eth1"
        self.virtio1_mac = "52:54:00:00:00:01"
        self.src1 = "192.168.4.1"
        self.dst1 = "192.168.3.1"
        self.vm_dut = None

        self.number_of_ports = 1
        self.header_row = ["FrameSize(B)", "Throughput(Mpps)", "LineRate(%)", "Cycle"]
        self.memory_channel = 4

    def set_up(self):
        #
        # Run before each test case.
        #
        # Launch vhost sample using default params
        #
        self.dut.send_expect("rm -rf ./vhost.out", "#")
        self.dut.send_expect("rm -rf ./vhost-net*", "#")
        self.dut.send_expect("killall -s INT vhost-switch", "#")

        self.frame_sizes = [64, 128, 256, 512, 1024, 1500]
        self.vm_testpmd_vector = self.target + "/app/testpmd -c 0x3 -n 3" \
                                 + " -- -i --txqflags=0xf01 --disable-hw-vlan-filter"
        self.vm_testpmd_normal = self.target + "/app/testpmd -c 0x3 -n 3" \
                                 + " -- -i --txqflags=0xf00 --disable-hw-vlan-filter"

    def launch_vhost_sample(self):
        #
        # Launch the vhost sample with different parameters
        #
        self.coremask = utils.create_mask(self.cores)
        self.vhostapp_testcmd = self.vhost_test % (
            self.coremask, self.memory_channel, self.jumbo, self.vm2vm)
        self.dut.send_expect(self.vhostapp_testcmd, "# ", 40)
        time.sleep(30)
        try:
            self.logger.info("Launch vhost sample:")
            self.dut.session.copy_file_from(self.dut.base_dir + "vhost.out")
            fp = open('./vhost.out', 'r')
            out = fp.read()
            fp.close()
            if "Error" in out:
                raise Exception("Launch vhost sample failed")
            else:
                self.logger.info("Launch vhost sample finished")
        except Exception as e:
            self.logger.error("ERROR: Failed to launch vhost sample: %s" % str(e))

    def start_onevm(self, path="", modem=0):
        #
        # Start One VM with one virtio device
        #

        self.vm = QEMUKvm(self.dut, 'vm0', 'vhost_sample')
        if(path != ""):
            self.vm.set_qemu_emulator(path)
        vm_params = {}
        vm_params['driver'] = 'vhost-user'
        vm_params['opt_path'] = './vhost-net'
        vm_params['opt_mac'] = self.virtio1_mac
        if(modem == 1):
            vm_params['opt_settings'] = 'disable-modern=false'
        self.vm.set_vm_device(**vm_params)

        try:
            self.vm_dut = self.vm.start()
            if self.vm_dut is None:
                raise Exception("Set up VM ENV failed")
        except Exception as e:
            self.logger.error("ERROR: Failure for %s" % str(e))

        return True

    def vm_testpmd_start(self):
        #
        # Start testpmd in vm
        #
        if self.vm_dut is not None:
            self.vm_dut.send_expect(self.vm_testpmd_vector, "testpmd>", 20)
            self.vm_dut.send_expect("set fwd mac", "testpmd>", 20)
            self.vm_dut.send_expect("start tx_first", "testpmd>")

    def send_verify(self, case, frame_sizes, vlan_id1=0, tag="Performance"):
        self.result_table_create(self.header_row)
        for frame_size in frame_sizes:
            info = "Running test %s, and %d frame size." % (case, frame_size)
            self.logger.info(info)
            payload = frame_size - HEADER_SIZE['eth'] - HEADER_SIZE['ip']
            flow1 = '[Ether(dst="%s")/Dot1Q(vlan=%s)/IP(src="%s",dst="%s")/("X"*%d)]' % (
                self.virtio1_mac, vlan_id1, self.src1, self.dst1, payload)
            self.tester.scapy_append('wrpcap("flow1.pcap", %s)' % flow1)
            self.tester.scapy_execute()

            tgenInput = []
            port = self.tester.get_local_port(self.pf)
            tgenInput.append((port, port, "flow1.pcap"))

            _, pps = self.tester.traffic_generator_throughput(tgenInput, delay=30)
            Mpps = pps / 1000000.0
            pct = Mpps * 100 / float(self.wirespeed(self.nic, frame_size,
                                     self.number_of_ports))
            data_row = [frame_size, str(Mpps), str(pct), tag]
            self.result_table_add(data_row)
        self.result_table_print()

    def test_perf_pvp_qemu_vector_pmd(self):
        #
        # Test the pvp performance for vector path
        #
        # start testpmd on VM
        self.jumbo = 0
        self.launch_vhost_sample()
        self.start_onevm()

        self.vm_dut.send_expect(self.vm_testpmd_vector, "testpmd>", 20)
        self.vm_dut.send_expect("start tx_first", "testpmd>")
        time.sleep(5)
        vlan_id1 = 1000
        self.send_verify(self.running_case, self.frame_sizes, vlan_id1, "Virtio 0.95 Vector Performance")
        self.vm_dut.kill_all()

    def test_perf_pvp_qemu_normal_pmd(self):
        #
        # Test the performance for normal path
        #
        # start testpmd on VM
        self.jumbo = 0
        self.launch_vhost_sample()
        self.start_onevm()
        # Start testpmd with user
        self.vm_dut.send_expect(self.vm_testpmd_normal, "testpmd>", 20)
        self.vm_dut.send_expect("start tx_first", "testpmd>")

        time.sleep(5)
        vlan_id1 = 1000
        self.send_verify(self.running_case, self.frame_sizes, vlan_id1, "Virtio 0.95 Normal Performance")
        self.vm_dut.kill_all()

    def test_perf_pvp_qemu_mergeable_pmd(self):
        #
        # Test the performance for mergeable path
        #
        # start testpmd on VM
        self.jumbo = 1
        self.launch_vhost_sample()
        self.start_onevm()
        # Start testpmd with user
        self.vm_dut.send_expect(self.vm_testpmd_vector, "testpmd>", 20)
        self.vm_dut.send_expect("start tx_first", "testpmd>")

        time.sleep(5)
        vlan_id1 = 1000
        self.send_verify(self.running_case, self.frame_sizes, vlan_id1, "Virtio 0.95 Mergeable Performance")
        self.vm_dut.kill_all()

    def test_perf_virtio_modern_qemu_vector_pmd(self):
        #
        # Test the vhost/virtio pvp performance for virtio1.0
        #
        #
        # start testpmd on VM
        self.jumbo = 0
        self.launch_vhost_sample()
        self.start_onevm("", 1)
        # Start testpmd with user
        self.vm_dut.send_expect(self.vm_testpmd_vector, "testpmd>", 20)
        self.vm_dut.send_expect("start tx_first", "testpmd>")

        time.sleep(5)
        vlan_id1 = 1000
        self.send_verify(self.running_case, self.frame_sizes, vlan_id1, "virtio1.0, Vector")
        self.vm_dut.kill_all()

    def test_perf_virtio_modern_qemu_normal_pmd(self):
        #
        # Test the performance of one vm with 2virtio devices in legacy fwd
        #
        # start testpmd on VM
        self.jumbo = 0
        self.launch_vhost_sample()
        self.start_onevm("", 1)
        # Start testpmd with user
        self.vm_dut.send_expect(self.vm_testpmd_normal, "testpmd>", 20)
        self.vm_dut.send_expect("start tx_first", "testpmd>")

        time.sleep(5)
        vlan_id1 = 1000
        self.send_verify(self.running_case, self.frame_sizes, vlan_id1, "virtio1.0, Normal")
        self.vm_dut.kill_all()

    def test_perf_virtio_modern_qemu_mergeable_pmd(self):
        #
        # Test the performance of one vm with 2virtio devices in legacy fwd
        #
        # start testpmd on VM
        self.jumbo = 1
        self.launch_vhost_sample()
        self.start_onevm("", 1)
        # Start testpmd with user
        self.vm_dut.send_expect(self.vm_testpmd_vector, "testpmd>", 20)
        self.vm_dut.send_expect("start tx_first", "testpmd>")

        time.sleep(5)
        vlan_id1 = 1000
        self.send_verify(self.running_case, self.frame_sizes, vlan_id1, "virtio1.0, Mergeable")
        self.vm_dut.kill_all()

    def tear_down(self):
        #
        # Run after each test case.
        # Clear vhost-switch and qemu to avoid blocking the following TCs
        #
        self.vm.stop()
        time.sleep(2)

    def tear_down_all(self):
        """
        Run after each test suite.
        """
        pass
