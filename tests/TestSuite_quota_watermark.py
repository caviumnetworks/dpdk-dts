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

Quota & Watermark example app test cases.

"""
import time
import utils
from test_case import TestCase
from etgen import IxiaPacketGenerator
from packet import Packet, sniff_packets, load_sniff_packets

test_config = {
    'frames_to_sent': 15 * 10 ** 6,
    'ring_sizes': [64, 256, 1024],
    'low_high_watermarks': [
        (0o1, 0o5), 
        (10, 20), 
        (10, 99),
        (60, 99), 
        (90, 99), 
        (10, 80),
        (50, 80), 
        (70, 80), 
        (70, 90),
        (80, 90)
    ],
    'quota_values': [5, 32, 60],
}

#
#
# Test class.
#


class TestQuotaWatermark(TestCase, IxiaPacketGenerator):

    #
    #
    #
    # Test cases.
    #

    def set_up_all(self):
        """
        Run at the start of each test suite.

        Quota watermark prerequisites.
        """

        self.tester.extend_external_packet_generator(TestQuotaWatermark, self)

    def add_report_headers(self, core_mask, port_mask):
        """
        Adds the table header and some info about the executed test
        """
        self.rst_report('Core mask: %s' % core_mask)
        self.rst_report('Port mask: %s' % port_mask)
        self.result_table_create([
            'Ring size',
            'Quota',
            'Low water-mark',
            'High water-mark',
            'Frames sent',
            'Frames received',
            'Control flow frames received',
            'Transmit rate (Mpps)'
        ])

    def set_app_ring_size(self, ring_size):
        """
        Changes the ring size by modifying the example app code.
        """

        sed_command = (r"sed -i 's/^\(.*RING_SIZE\)\s*[[:digit:]]*/\1 %d/' " +
                       r"examples/quota_watermark/include/conf.h")
        self.dut.send_expect(sed_command % int(ring_size), '# ')

    def compile_quota_watermark_example_apps(self):
        """
        Builds the example app and checks for errors.
        """

        out = self.dut.send_expect("make -C examples/quota_watermark", "# ")
        self.verify("Error" not in out and "No such file" not in out,
                    "Compilation error")

    def execute_qw_app(self, core_mask, port_mask, memory_channels):
        """
        Executes the main example app in the background.
        """

        command = ('./examples/quota_watermark/qw/qw/%s/qw -c {core_mask}' % self.target +
                   ' -n {memory_channels} -- -p {port_mask} 2>&1 > output.log &')
        self.dut.send_expect(command.format(**locals()), '# ')

    def execute_qwctl_app(self, memory_channels):
        """
        Executes the control app and returns waiting for commands.
        """

        command = './examples/quota_watermark/qwctl/qwctl/%s/qwctl -c 1 -n %s --proc-type=secondary'
        command = command % (self.target, str(memory_channels))
        result = self.dut.send_expect(command, 'qwctl> ')
        self.verify('Error' not in result, 'qwctl app failed to execute')

    def execute_quota_watermark_example_apps(self, core_mask, port_mask, memory_channels):
        """
        Execute both example apps and checks for errors.
        """
        
        self.execute_qw_app(core_mask, port_mask, memory_channels)
        # We wait until the app starts and writes its output down to the log
        # file
        time.sleep(15)
        result = self.dut.send_expect('cat output.log', '# ')
        self.verify('USER1: receive_stage() started' in result,
                    'qw app failed to execute')
        self.execute_qwctl_app(memory_channels)

    def close_quota_watermark_example_apps(self):
        """
        Close control app sending Ctrl-D. This app is always in foreground.
        Also kills the main app which is in the background.
        """

        self.dut.send_expect('^D', '# ')
        self.dut.send_expect('killall qw', '# ')

    def send_qwctl_command(self, command, unexpected_outputs):
        """
        Sends a command to the control app and checks the given unexpected output
        is not in the app's output.
        """

        result = self.dut.send_expect(command, 'qwctl>')
        for output in unexpected_outputs:
            self.verify(output not in result, "`%s' is incorrect" % command)

    def set_quota_value(self, quota):
        """
        Sets the global quota value.
        """

        self.send_qwctl_command('set quota %d' % quota,
                                ['quota must be between'])

    def set_low_watermark(self, low_watermark):
        """
        Sets the global low watermark value.
        """

        self.send_qwctl_command('set low_watermark %d' % low_watermark,
                                ['low_watermark must be between'])

    def set_high_watermark_single_core_port(self, core, port, high_watermark):
        """
        Sets the high watermark value for a given ring identified by a core
        and port number.
        """

        command = 'set core%d_port%d %d' % \
                  (int(core), int(port), int(high_watermark))
        unexpected = [
            'ring high watermark must be between', 'Cannot find ring']
        self.send_qwctl_command(command, unexpected)

    def set_high_watermark_all_cores_ports(self, cores, ports, high_watermark):
        """
        Sets high watermark value to a list of cores/ports. Due to the app's way
        to work the last core doesn't have any ring to enqueue in, that's why the
        last core is avoided.
        """

        cores.sort(key=lambda core: int(core))
        for core in cores[:-1]:
            for port in ports:
                self.set_high_watermark_single_core_port(
                    core, port, high_watermark)

    def prepare_scapy_packet(self, pkt_cnt=1):
        """
        Creates a simple scapy packet to run the tests with
        """

        self.tester.scapy_append('flow=[Ether(src="11:22:33:44:55:66")/IP()/("X"*26)]*%d'%pkt_cnt)
        self.tester.scapy_append('wrpcap("file.pcap", flow)')
        self.tester.scapy_execute()

    def get_ports_config(self, dut_rx_port, dut_tx_port):
        """
        Creates a usable data structure where the ports configuration is stored.
        """

        ports_config = {}
        ports_config['dut_rx'] = dut_rx_port
        ports_config['dut_tx'] = dut_tx_port
        ports_config[
            'dut_port_mask'] = utils.create_mask([ports_config['dut_tx'],
                                                ports_config['dut_rx']])
        ports_config['tester_rx'] = self.tester.get_local_port(
            ports_config['dut_rx'])
        ports_config['tester_tx'] = self.tester.get_local_port(
            ports_config['dut_tx'])
        return ports_config

    def generate_tgen_input(self, ports_config, pkt_cnt=1):
        """
        Generates the argument that the external traffic generator function
        waits to receive as argument.
        """

        self.prepare_scapy_packet(pkt_cnt)
        tgen_input = [[ports_config['tester_tx'],
                       ports_config['tester_rx'],
                       'file.pcap']]
        return tgen_input

    def send_pcap_pkt_by_scapy(self, tester=None, file='', intf=''):
        if intf == '' or file == '' or tester is None:
            print "Invalid option for send packet by scapy"
            return

        content = 'pkts=rdpcap(\"%s\");sendp(pkts, iface=\"%s\");exit()' % (file, intf)
        cmd_file = '/tmp/scapy_%s.cmd' % intf

        tester.create_file(content, cmd_file)
        tester.send_expect("scapy -c scapy_%s.cmd &" % intf, "# ")

    def iterate_through_qw_ring_sizes(self, ports_config, core_config):
        """
        It goes through the different ring values compiling the apps, executing
        them, running the other test permutations and finally closing the apps.
        The rings are the first to be covered because we need to build/start/stop
        the apps to change them.
        """

        dut_ports = [ports_config['dut_rx'], ports_config['dut_tx']]
        memory_channels = self.dut.get_memory_channels()
        tgen_input = self.generate_tgen_input(ports_config)

        for ring_size in test_config['ring_sizes']:
            self.set_app_ring_size(ring_size)
            self.compile_quota_watermark_example_apps()
            self.execute_quota_watermark_example_apps(core_config['mask'],
                                                      ports_config['dut_port_mask'],
                                                      memory_channels)
            self.iterate_through_qw_quota_watermarks( core_config['cores'], 
                                                      dut_ports, 
                                                      tgen_input, 
                                                      ring_size)
            self.close_quota_watermark_example_apps()

    def iterate_through_qw_quota_watermarks(self, cores, ports, tgen_input, ring_size):
        """
        Goes through the other test permutations changing the quota and water-marks
        values, calling IXIA and storing the results in the result table.
        """

        for quota in test_config['quota_values']:
            for low_watermark, high_watermark in test_config['low_high_watermarks']:
                self.set_quota_value(quota)
                self.set_low_watermark(low_watermark)
                self.set_high_watermark_all_cores_ports(cores, ports, high_watermark)
                self.num_of_frames = test_config['frames_to_sent']
                test_stats = self.tester.traffic_generator_throughput(tgen_input)

                self.result_table_add([ring_size, quota, low_watermark, high_watermark] +
                                          test_stats)

    def check_packets_transfer(self, tx_port, rx_port, tgen_input, pkt_cnt=1):
        '''
        check packets transmission status
        '''
        # check forwarded mac has been changed
        rev_port = self.tester.get_local_port(rx_port)
        send_port = self.tester.get_local_port(tx_port)
        dst_mac = self.dut.get_mac_address(rx_port)
        rx_intf = self.tester.get_interface(rev_port)
        tx_intf = self.tester.get_interface(send_port)
        # send and sniff packet
        rx_inst = sniff_packets(rx_intf, timeout=5)
        self.send_pcap_pkt_by_scapy(self.tester, tgen_input[0][2], tx_intf)
        pkts = load_sniff_packets(rx_inst)
        self.verify(len(pkts) == pkt_cnt, "Packet not forwarded as expected")

        return

    def get_setting_parameters(self, para_type):
        '''
        get setting parameters from performance setting 
        '''
        settings = test_config[para_type][:1]
        
        return settings

    def func_iterate_through_qw_quota_watermarks(self, cores, ports_config, ports, ring_size):
        """
        Goes through the other test permutations changing the quota and water-marks
        values, send packets by scapy and check packets transmission status.
        """
        for quota in self.get_setting_parameters('quota_values'):
            for low_watermark, high_watermark in self.get_setting_parameters('low_high_watermarks'):
                self.set_quota_value(quota)
                self.set_low_watermark(low_watermark)
                self.set_high_watermark_all_cores_ports( cores, ports, high_watermark)
                tgen_input = self.generate_tgen_input(ports_config, pkt_cnt=low_watermark)
                test_stats = self.check_packets_transfer(ports[0], ports[1], tgen_input, pkt_cnt=low_watermark)

    def func_iterate_through_qw_ring_sizes(self, ports_config, core_config):
        """
        It goes through the different ring values compiling the apps, executing
        them, running the other test permutations and finally closing the apps.
        The rings are the first to be covered because we need to build/start/stop
        the apps to change them.
        """

        dut_ports = [ports_config['dut_rx'], ports_config['dut_tx']]
        memory_channels = self.dut.get_memory_channels()
        
        for ring_size in self.get_setting_parameters('ring_sizes'):
            self.set_app_ring_size(ring_size)
            self.compile_quota_watermark_example_apps()
            self.execute_quota_watermark_example_apps(core_config['mask'],
                                                      ports_config['dut_port_mask'],
                                                      memory_channels)
            self.func_iterate_through_qw_quota_watermarks( core_config['cores'],
                                                           ports_config, 
                                                           dut_ports,
                                                           ring_size)
            self.close_quota_watermark_example_apps()

    def config_ixia_stream(self, rate_percent, flows):
        """
        Work around that overrides the etgen.confStream function in order to
        change the way that IXIA gets called.
        In this case IXIA sends a fixed number of packets and then stops.
        """

        self.add_tcl_cmd("ixGlobalSetDefault")
        self.add_tcl_cmd("stream config -rateMode usePercentRate")
        self.add_tcl_cmd("stream config -percentPacketRate %s" % rate_percent)

        # We define one burst with num_frames packets on it and we also want IXIA
        # to stop once all of them have been sent.
        self.add_tcl_cmd("stream config -numBursts 1")
        self.add_tcl_cmd("stream config -numFrames %d" % self.num_of_frames)
        self.add_tcl_cmd("stream config -dma stopStream")

    def configure_transmission(self):
        """
        Work around that substitute the etgen.Throughput function.
        It makes IXIA to send a fixed number of packets and waits until is done.
        Returns several stat values needed by the test cases.
        """

        # This basically means "start the packets transmission and don't return
        # until you are done". Thanks to that, after we "source ixiaConfig.tcl" we
        # are 100% sure that all the packets have been sent and IXIA is pretty much
        # done so we can read the stats.
        self.add_tcl_cmd("ixStartTransmit portList")
        self.add_tcl_cmd('after 1000')
        self.add_tcl_cmd('ixCheckTransmitDone portList')
        # end configure_transmission

    def get_transmission_results(self, rx_port_list, tx_port_list):
        frames_received = 0
        for port in rx_port_list:
            self.stat_get_stat_all_stats(port)
            frames_received += self.get_frames_received()

        frames_sent = 0
        control_flow_received = 0
        transmit_duration = 0
        for port in tx_port_list:
            self.stat_get_stat_all_stats(port)
            control_flow_received += self.get_flow_control_frames()
            frames_sent += self.get_frames_sent()
            # Time in nanoseconds
            transmit_duration += self.get_transmit_duration()

        rate = self.packet_2_millpacket(
            frames_sent) / self.nanosec_2_sec(transmit_duration)
        return [frames_sent, frames_received, control_flow_received, rate]

    def nanosec_2_sec(self, nano_secs):
        return float(nano_secs) / 10e9

    def packet_2_millpacket(self, num_of_pkt):
        return float(num_of_pkt) / 10e6

    def test_quota_watermark(self):
        """
        Test case that runs the different test permutations by using cores on
        a single socket and two ports attached to it.
        """

        dut_ports = self.dut.get_ports(self.nic, perf=True)
        self.verify(len(dut_ports) >= 2,
                    "Insufficient ports for speed testing")
        ports_config = self.get_ports_config(dut_ports[0], dut_ports[1])

        cores_one_socket = self.dut.get_core_list('1S/4C/1T')
        core_config = {
            'cores': cores_one_socket,
            'mask': utils.create_mask(cores_one_socket)
        }

        self.func_iterate_through_qw_ring_sizes(ports_config, core_config)

    def test_perf_quota_watermark_one_socket(self):
        """
        Test case that runs the different test permutations by using cores on
        a single socket and two ports attached to it.
        """

        dut_ports = self.dut.get_ports(self.nic, perf=True)
        self.verify(len(dut_ports) >= 2, "Insufficient ports for speed testing")
        ports_config = self.get_ports_config(dut_ports[2], dut_ports[3])

        cores_one_socket = self.dut.get_core_list('1S/4C/1T')
        core_config = {
            'cores':   cores_one_socket,
            'mask':    utils.create_mask(cores_one_socket)
        }

        self.add_report_headers( core_config['mask'], 
                                 ports_config['dut_port_mask'])
        self.iterate_through_qw_ring_sizes(ports_config, core_config)
        self.result_table_print()

    def test_perf_quota_watermark_two_sockets(self):
        """
        Test case that runs the different test permutations by using cores on
        two different sockets with a port attached to each one of them.
        """

        dut_ports = self.dut.get_ports(self.nic, perf=True)
        self.verify(len(dut_ports) >= 4, "Insufficient ports for speed testing")
        ports_config = self.get_ports_config(dut_ports[0], dut_ports[3])

        cores_two_sockets = self.dut.get_core_list('2S/4C/1T')
        core_config = {
            'cores': cores_two_sockets,
            'mask': utils.create_mask(cores_two_sockets)
        }

        self.add_report_headers( core_config['mask'], ports_config['dut_port_mask'])
        self.iterate_through_qw_ring_sizes(ports_config, core_config)
        self.result_table_print()
