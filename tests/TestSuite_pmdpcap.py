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

'''
'''
from test_case import TestCase

from time import sleep
from scapy.all import *
import utils


#
#
# Test class.
#
class TestPmdPcap(TestCase):

    pcap_file_sizes = [1000, 500]
    dut_pcap_files_path = '/root/'

    def set_up_all(self):
        self.check_scapy_in_dut()

        self.memory_channel = self.dut.get_memory_channels()

        # Enable PCAP features and rebuild the package
        self.pcap_config = self.get_pcap_compile_config()
        self.dut.send_expect(
            "sed -i 's/CONFIG_RTE_LIBRTE_PMD_PCAP=n$/CONFIG_RTE_LIBRTE_PMD_PCAP=y/' config/%s" % self.pcap_config, "# ")
        self.dut.build_install_dpdk(self.target)

        # make sure there is no interface to bind
        # because if there is any interface bonded to igb_uio,
        # it will result in packet transmiting failed
        self.dut.restore_interfaces()

    def get_pcap_compile_config(self):
        config_head = "common_"
        os_type = self.dut.get_os_type()
        if os_type == "linux":
            config_tail = os_type + "app"
        elif os_type == "freebsd":
            config_tail = "bsdapp"
        else:
            raise Exception(
                "Unknow os type, please check to make sure pcap can work in OS [ %s ]" % os_type)
	out = self.dut.send_command("cat config/%s" % (config_head + config_tail))
	if "CONFIG_RTE_LIBRTE_PMD_PCAP" in out:
        	return config_head + config_tail
	else:
		return config_head + "base"

    def create_pcap_file(self, filename, number_of_packets):
        flow = []
        for pkt_id in range(number_of_packets):
            pkt_id = str(hex(pkt_id % 256))
            flow.append(Ether(src='00:00:00:00:00:%s' % pkt_id[2:], dst='00:00:00:00:00:00') / IP(
                src='192.168.1.1', dst='192.168.1.2') / ("X" * 26))

        wrpcap(filename, flow)

    def check_scapy_in_dut(self):
        try:
            self.dut.send_expect('scapy', '>>> ')
            self.dut.send_expect('quit()', '# ')
        except:
            self.verify(False, 'Scapy is required in dut.')

    def check_pcap_files(self, in_pcap, out_pcap, expected_frames):

        # Check if the number of expected frames are in the output
        result = self.dut.send_expect(
            'tcpdump -n -e -r %s | wc -l' % out_pcap, '# ')
        self.verify(str(expected_frames) in result,
                    'Not all packets have been forwarded')

        # Check if the frames in the input and output files match
        self.dut.send_expect('scapy', '>>> ')
        self.dut.send_expect('input=rdpcap("%s")' % in_pcap, '>>> ')
        self.dut.send_expect('output=rdpcap("%s")' % out_pcap, '>>> ')
        self.dut.send_expect(
            'result=[input[i]==output[i] for i in xrange(len(input))]', '>>> ')
        result = self.dut.send_expect('False in result', '>>> ')
        self.dut.send_expect('quit()', '# ')

        self.verify('True' not in result, 'In/Out packets do not match.')

    def test_send_packets_with_one_device(self):
        in_pcap = 'in_pmdpcap.pcap'
        out_pcap = '/tmp/out_pmdpcap.pcap'

        two_cores = self.dut.get_core_list("1S/2C/1T")
        core_mask = utils.create_mask(two_cores)

        self.create_pcap_file(in_pcap, TestPmdPcap.pcap_file_sizes[0])
        self.dut.session.copy_file_to(in_pcap)

        command = ("./{}/app/testpmd -c {} -n {} " +
                   "--vdev=eth_pcap0,rx_pcap={},tx_pcap={} " +
                   "-- -i --port-topology=chained")
        if "cavium" in self.dut.nic_type:
            command += " --disable-hw-vlan-filter"

        self.dut.send_expect(command.format(self.target, core_mask,
                             self.memory_channel,
                             TestPmdPcap.dut_pcap_files_path + in_pcap,
                             out_pcap), 'testpmd> ', 15)

        self.dut.send_expect('start', 'testpmd> ')
        sleep(2)
        self.dut.send_expect('stop', 'testpmd> ')
        self.dut.send_expect('quit', '# ')

        self.check_pcap_files(TestPmdPcap.dut_pcap_files_path + in_pcap,
                              out_pcap, TestPmdPcap.pcap_file_sizes[0])

    def test_send_packets_with_two_devices(self):

        in_pcap1 = 'in1_pmdpcap.pcap'
        out_pcap1 = '/tmp/out1_pmdpcap.pcap'

        in_pcap2 = 'in2_pmdpcap.pcap'
        out_pcap2 = '/tmp/out2_pmdpcap.pcap'

        four_cores = self.dut.get_core_list("1S/4C/1T")
        core_mask = utils.create_mask(four_cores)

        self.create_pcap_file(in_pcap1, TestPmdPcap.pcap_file_sizes[0])
        self.dut.session.copy_file_to(in_pcap1)
        self.create_pcap_file(in_pcap2, TestPmdPcap.pcap_file_sizes[1])
        self.dut.session.copy_file_to(in_pcap2)

        command = ("./{}/app/testpmd -c {} -n {} " +
                   "--vdev=eth_pcap0,rx_pcap={},tx_pcap={} " +
                   "--vdev=eth_pcap1,rx_pcap={},tx_pcap={} " +
                   "-- -i")
        if "cavium" in self.dut.nic_type:
            command += " --disable-hw-vlan-filter"

        self.dut.send_expect(command.format(self.target, core_mask,
                                            self.memory_channel,
                                            TestPmdPcap.dut_pcap_files_path +
                                            in_pcap1,
                                            out_pcap1,
                                            TestPmdPcap.dut_pcap_files_path +
                                            in_pcap2,
                                            out_pcap2), 'testpmd> ', 10)

        self.dut.send_expect('start', 'testpmd> ')
        sleep(2)
        self.dut.send_expect('stop', 'testpmd> ')
        self.dut.send_expect('quit', '# ')

        self.check_pcap_files(TestPmdPcap.dut_pcap_files_path + in_pcap1,
                              out_pcap2, TestPmdPcap.pcap_file_sizes[0])

        self.check_pcap_files(TestPmdPcap.dut_pcap_files_path + in_pcap2,
                              out_pcap1, TestPmdPcap.pcap_file_sizes[1])

    def tear_down_all(self):
        # Disable PCAP feature and rebuild the package
        self.dut.send_expect(
            "sed -i 's/CONFIG_RTE_LIBRTE_PMD_PCAP=y$/CONFIG_RTE_LIBRTE_PMD_PCAP=n/' config/%s" % self.pcap_config, "# ")
        self.dut.set_target(self.target)
