# BSD LICENSE
#
# Copyright(c) 2010-2015 Intel Corporation. All rights reserved.
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

Vhost user one-copy sample test suite.
"""
import os
import dts
import string
import re
import time
from scapy.utils import wrpcap, rdpcap
from test_case import TestCase
from exception import VerifyFailure
from settings import HEADER_SIZE
from etgen import IxiaPacketGenerator
from qemu_kvm import QEMUKvm


class TestVhostSample(TestCase, IxiaPacketGenerator):

    def set_up_all(self):
        # To Extend IXIA packet generator method, call the tester's method.
        self.tester.extend_external_packet_generator(TestVhostSample, self)

        # Build target with modified config file
        self.dut.build_install_dpdk(self.target)

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
        self.zero_copy = 0
        self.vm2vm = 0
        self.jumbo = 0

        # Using file to save the vhost sample output since in jumboframe case,
        # there will be lots of output
        self.vhost_test = self.vhost_app + \
            " -c %s -n %d --socket-mem 1024,1024 -- -p 0x1 --mergeable %d" + \
            " --zero-copy %d --vm2vm %d 2 > ./vhost.out &"
        # build the vhost sample in vhost-user mode.
        self.dut.send_expect(
            "sed -i -e 's/define MAX_QUEUES 512/define MAX_QUEUES 128/'"
            " ./examples/vhost/main.c",
            "#")
        out = self.dut.send_expect("make -C examples/vhost", "#")
        self.verify("Error" not in out, "compilation error")
        self.verify("No such file" not in out, "Not found file error")

        # Define the virtio/VM variables
        self.virtio1 = "eth1"
        self.virtio2 = "eth2"
        self.virtio1_mac = "52:54:00:00:00:01"
        self.virtio2_mac = "52:54:00:00:00:02"
        self.src1 = "192.168.4.1"
        self.src2 = "192.168.3.1"
        self.dst1 = "192.168.3.1"
        self.dst2 = "192.168.4.1"
        self.vm_dut = None

        self.header_row = ["Test", "Mode", "Frame", "Mpps", "% linerate"]
        self.memory_channel = 4

    def set_up(self):
        #
        # Run before each test case.
        #
        # Launch vhost sample using default params

        if "jumbo" in self.running_case:
            self.jumbo = 1
            self.frame_sizes = [
                68,
                128,
                256,
                512,
                1024,
                1280,
                1518,
                2048,
                5000,
                9000]
            self.vm_testpmd = "./x86_64-native-linuxapp-gcc/app/testpmd -c 0x3 -n 3" \
                + \
                " -- -i --txqflags=0xf00 --disable-hw-vlan-filter --max-pkt-len 9600"
        else:
            self.jumbo = 0
            self.frame_sizes = [68, 128, 256, 512, 1024, 1280, 1518]
            self.vm_testpmd = "./x86_64-native-linuxapp-gcc/app/testpmd -c 0x3 -n 3" \
                + " -- -i --txqflags=0xf00 --disable-hw-vlan-filter"
        self.dut.send_expect("rm -rf ./vhost.out", "#")

        self.launch_vhost_sample()

        print "Start VM with 2virtio\n"
        # start VM with 2virtio
        self.start_onevm()

    def launch_vhost_sample(self):
        #
        # Launch the vhost sample with different parameters
        #
        self.coremask = dts.create_mask(self.cores)
        self.vhostapp_testcmd = self.vhost_test % (
            self.coremask, self.memory_channel, self.jumbo, self.zero_copy, self.vm2vm)
        self.dut.send_expect(self.vhostapp_testcmd, "# ", 40)
        time.sleep(30)
        try:
            print "Launch vhost sample\n"
            out = self.dut.send_expect(
                "cat ./vhost.out",
                "VHOST_CONFIG: bind to vhost-net",
                20)
            if "Error" in out:
                raise Exception("Launch vhost sample failed")
        except Exception as e:
            print dts.RED("Failed to launch vhost sample: %s" % str(e))
            self.dut.send_expect("rm -rf ./vhost-net", "#", 20)

    def start_onevm(self):
        #
        # Start One VM with 2 virtio devices
        #

        self.vm = QEMUKvm(self.dut, 'vm0', 'vhost_sample')
        if "user" in self.running_case:
            vm_params = {}
            vm_params['driver'] = 'vhost-user'
            vm_params['opt_path'] = './vhost-net'
            vm_params['opt_mac'] = self.virtio1_mac
            self.vm.set_vm_device(**vm_params)
            vm_params['opt_mac'] = self.virtio2_mac
            self.vm.set_vm_device(**vm_params)

        try:
            self.vm_dut = self.vm.start(auto_portmap=False)
            if self.vm_dut is None:
                raise Exception("Set up VM ENV failed")
        except Exception as e:
            print dts.RED("Failure for %s" % str(e))

        return True

    def vm_testpmd_start(self):
        #
        # Start testpmd in vm
        #
        if self.vm_dut is not None:
            # Start testpmd with user
            self.vm_dut.send_expect(self.vm_testpmd, "testpmd>", 20)
            # Start tx_first
            self.vm_dut.send_expect("start tx_first", "testpmd>")

    def clear_vhost_env(self):
        #
        # Kill all vhost sample, shutdown VM
        #
        if self.vm_dut:
            self.vm_dut.kill_all()
            time.sleep(1)
            self.vm_dut.close()
            self.vm_dut.logger.logger_exit()
            self.vm_dut = None
        if self.vm:
            self.vm.stop()
            self.vm = None

    def set_legacy_disablefw(self):
        #
        # Disable firewall and iptables in legacy case
        #
        if self.vm_dut is not None:
            self.vm_dut.send_expect("systemctl stop firewalld.service", "#")
            self.vm_dut.send_expect("systemctl disable firewalld.service", "#")
            self.vm_dut.send_expect("systemctl stop ip6tables.service", "#")
            self.vm_dut.send_expect("systemctl disable ip6tables.service", "#")
            self.vm_dut.send_expect("systemctl stop iptables.service", "#")
            self.vm_dut.send_expect("systemctl disable iptables.service", "#")
            self.vm_dut.send_expect(
                "systemctl stop NetworkManager.service",
                "#")
            self.vm_dut.send_expect(
                "systemctl disable NetworkManager.service",
                "#")
            self.vm_dut.send_expect(
                "echo 1 >/proc/sys/net/ipv4/ip_forward",
                "#")

    def set_onevm_legacy_fwd(self):
        if self.vm_dut is not None:
            ifcfg = self.vm_dut.send_expect("ifconfig -a", "#", 10)
            intfs = re.compile('eth\d').findall(ifcfg)
            # Find the virtio1 and virtio2's interface names
            for intf in intfs:
                out_mac = self.vm_dut.send_expect(
                    "ifconfig %s" %
                    intf, "#", 10)
                if self.virtio1_mac in out_mac:
                    self.virtio1 = intf
                if self.virtio2_mac in out_mac:
                    self.virtio2 = intf
            print "\nvirtio1's intf is %s" % self.virtio1
            print "\nvirtio2's intf is %s" % self.virtio2
            # Set the mtu 9000 if jumboframe is enabled.
            if self.jumbo == 1:
                self.vm_dut.send_expect(
                    "ifconfig %s mtu 9000" %
                    self.virtio1, "#")
                self.vm_dut.send_expect(
                    "ifconfig %s mtu 9000" %
                    self.virtio2, "#")
            # Set up the ip address/ipv4 fwd tables
            self.vm_dut.send_expect(
                "ip addr add 192.168.4.2/24 dev %s" %
                self.virtio1, "#")
            self.vm_dut.send_expect(
                "ip addr add 192.168.3.2/24 dev %s" %
                self.virtio2, "#")
            self.vm_dut.send_expect(
                "ip link set dev %s up" %
                self.virtio1, "#")
            self.vm_dut.send_expect(
                "ip link set dev %s up" %
                self.virtio2, "#")
            self.vm_dut.send_expect(
                "ip neigh add 192.168.4.1 lladdr 52:00:00:00:00:01 dev %s" %
                self.virtio1, "#")
            self.vm_dut.send_expect(
                "ip neigh add 192.168.3.1 lladdr 52:00:00:00:00:02 dev %s" %
                self.virtio2, "#")
            self.vm_dut.send_expect("ip route show", "#")
            print self.vm_dut.send_expect("arp -a", "#")

    def test_perf_user_one_vm_legacy_fwd(self):
        #
        # Test the performance of one vm with 2virtio devices in legacy fwd
        #
        # Restore the virtio interfaces to use legacy driver
        self.vm_dut.restore_interfaces()

        self.set_legacy_disablefw()
        # Set the legacy fwd rules then get the VLAN id from vhost sample
        # output
        self.set_onevm_legacy_fwd()

        time.sleep(5)
        out_clean = self.dut.get_session_output(timeout=2)
        out = self.dut.send_expect("cat ./vhost.out", "# ", 20)
        # Get the VLAN ID for virtio
        print out, "\ncheck the vlan info: \n"
        l1 = re.findall(
            'MAC_ADDRESS.*?%s.*?and.*?VLAN_TAG.*?(\d+).*?registered' %
            (str(self.virtio1_mac)), out)
        if len(l1) > 0:
            vlan_id1 = l1[0]
            print "vlan_id1 is ", vlan_id1
        l2 = re.findall(
            'MAC_ADDRESS.*?%s.*?and.*?VLAN_TAG.*?(\d+).*?registered' %
            (str(self.virtio2_mac)), out)
        if len(l2) > 0:
            vlan_id2 = l2[0]
            print "vlan_id2 is ", vlan_id2

        dts.results_table_add_header(self.header_row)

        # Create pcap file and ixia traffic
        for frame_size in self.frame_sizes:
            info = "Running test %s, and %d frame size.\n" % (
                self.running_case, frame_size)
            self.logger.info(info)

            payload_size = frame_size - HEADER_SIZE['eth'] - HEADER_SIZE['ip']
            flow1 = '[Ether(dst="%s")/Dot1Q(vlan=%s)/IP(src="%s",dst="%s")/("X"*%d)]' % (
                self.virtio1_mac, vlan_id1, self.src1, self.dst1, payload_size)
            flow2 = '[Ether(dst="%s")/Dot1Q(vlan=%s)/IP(src="%s",dst="%s")/("X"*%d)]' % (
                self.virtio2_mac, vlan_id2, self.src2, self.dst2, payload_size)

            self.tester.scapy_append('wrpcap("flow1.pcap", %s)' % flow1)
            self.tester.scapy_append('wrpcap("flow2.pcap",%s)' % flow2)
            self.tester.scapy_execute()

        # Capture the performance
            tgenInput = []
            port = self.tester.get_local_port(self.pf)
            tgenInput.append((port, port, "flow2.pcap"))

            _, pps = self.tester.traffic_generator_throughput(
                tgenInput, delay=15)
            pps /= 1000000.0
            linerate = self.wirespeed(self.nic, frame_size, 1)
            pct = pps * 100 / linerate
            scenario = self.running_case
            mode = "vhost user"
            data_row = [scenario, mode, frame_size, str(pps), str(pct)]
            dts.results_table_add_row(data_row)

        dts.results_table_print()

        # Stop the Vhost sample
        self.dut.send_expect("killall -s INT vhost-switch", "#", 20)

    def test_perf_user_one_vm_dpdk_fwd(self):
        #
        # Test the performance of one vm with 2virtio devices in legacy fwd
        #

        # start testpmd on VM
        self.vm_testpmd_start()
        time.sleep(5)
        # Clean the output to ensure the commands cat ./vhost.out can be sent
        # and got answered correctly.
        out_clean = self.dut.get_session_output(timeout=2)
        out = self.dut.send_expect("cat ./vhost.out", "# ", 20)
        # Get the VLAN ID for virtio
        print out, "\ncheck the vlan info: \n"
        l1 = re.findall(
            'MAC_ADDRESS.*?%s.*?and.*?VLAN_TAG.*?(\d+).*?registered' %
            (str(self.virtio1_mac)), out)
        if len(l1) > 0:
            vlan_id1 = l1[0]
            print vlan_id1
        l2 = re.findall(
            'MAC_ADDRESS.*?%s.*?and.*?VLAN_TAG.*?(\d+).*?registered' %
            (str(self.virtio2_mac)), out)
        if len(l2) > 0:
            vlan_id2 = l2[0]
            print vlan_id2

        dts.results_table_add_header(self.header_row)

        # Create pcap file and ixia traffic
        for frame_size in self.frame_sizes:
            info = "Running test %s, and %d frame size.\n" % (
                self.running_case, frame_size)
            self.logger.info(info)

            payload_size = frame_size - HEADER_SIZE['eth'] - HEADER_SIZE['ip']
            flow1 = '[Ether(dst="%s")/Dot1Q(vlan=%s)/IP(src="%s",dst="%s")/("X"*%d)]' % (
                self.virtio1_mac, vlan_id1, self.src1, self.dst1, payload_size)
            flow2 = '[Ether(dst="%s")/Dot1Q(vlan=%s)/IP(src="%s",dst="%s")/("X"*%d)]' % (
                self.virtio2_mac, vlan_id2, self.src2, self.dst2, payload_size)
            self.tester.scapy_append('wrpcap("flow1.pcap", %s)' % flow1)
            self.tester.scapy_append('wrpcap("flow2.pcap",%s)' % flow2)
            self.tester.scapy_execute()

        # Capture the performance
            tgenInput = []
            port = self.tester.get_local_port(self.pf)
            tgenInput.append((port, port, "flow1.pcap"))
            tgenInput.append((port, port, "flow2.pcap"))

            _, pps = self.tester.traffic_generator_throughput(
                tgenInput, delay=15)
            pps /= 1000000.0
            linerate = self.wirespeed(self.nic, frame_size, 1)
            pct = pps * 100 / linerate
            scenario = self.running_case
            mode = "vhost user"
            data_row = [scenario, mode, frame_size, str(pps), str(pct)]
            dts.results_table_add_row(data_row)

        dts.results_table_print()
        # Stop testpmd
        print self.vm_dut.send_expect("stop", "testpmd>")
        time.sleep(1)
        self.vm_dut.send_expect("quit", "# ")

        # Stop the Vhost sample
        self.dut.send_expect("killall -s INT vhost-switch", "#")

    def test_perf_user_one_vm_legacy_fwd_jumboframe(self):
        self.test_perf_user_one_vm_legacy_fwd()

    def test_perf_user_one_vm_dpdk_fwd_jumboframe(self):
        self.test_perf_user_one_vm_dpdk_fwd()

    def tear_down(self):
        #
        # Run after each test case.
        #
        self.clear_vhost_env()
        self.dut.kill_all()
        time.sleep(2)

    def tear_down_all(self):
        """
        Run after each test suite.
        """
        pass
