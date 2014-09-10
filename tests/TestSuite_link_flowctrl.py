# <COPYRIGHT_TAG>

"""
DPDK Test suite.

Test for Ethernet Link Flow Control Features by Poll Mode Drivers

"""

import dcts
import re

from time import sleep
from test_case import TestCase

#
#
# Test class.
#


class TestLinkFlowctrl(TestCase):

    #
    #
    #
    # Test cases.
    #
    pause_frame_dst = "01:80:C2:00:00:01"
    pause_frame_type = "0x8808"
    pause_frame_opcode = "\\x00\\x01"
    pause_frame_control = "\\x00\\xFF"
    pause_frame_paddign = "\\x00" * 42

    pause_frame = '[Ether(src="%s",dst="%s",type=%s)/("%s%s%s")]'

    frames_to_sent = 10

    packet_size = 66    # 66 allows frame loss
    ip_header_size = 20
    udp_header_size = 8
    eth_header_size = 18
    payload_size = packet_size - eth_header_size - ip_header_size - udp_header_size

    def set_up_all(self):
        """
        Run at the start of each test suite.

        Link flow control Prerequisites
        """

        self.dutPorts = self.dut.get_ports(self.nic)
        self.verify(len(self.dutPorts) > 1, "Insuficient ports")

        self.rx_port = self.dutPorts[0]
        self.tester_tx_mac = self.tester.get_mac(self.tester.get_local_port(self.rx_port))

        self.tx_port = self.dutPorts[1]

        self.portMask = dcts.create_mask([self.rx_port, self.tx_port])
        self.memChannels = self.dut.get_memory_channels()

        cmdline = "./%s/app/testpmd -c ffffff -n %s -- -i --burst=1" % (self.target, self.memChannels) + \
            "--txpt=32 --txht=8 --txwt=0 --txfreet=0  --mbcache=250 --portmask=%s" % self.portMask

        self.dut.send_expect(cmdline, "testpmd> ", 120)

    def pause_frame_loss_test(self, rx_flow_control='off',
                              tx_flow_control='off',
                              pause_frame_fwd='off'):

        tester_tx_port = self.tester.get_local_port(self.rx_port)
        tester_rx_port = self.tester.get_local_port(self.tx_port)

        tgenInput = []
        tgenInput.append((tester_tx_port, tester_rx_port, "test.pcap"))

        self.dut.send_expect("set flow_ctrl rx %s tx %s 300 50 10 1 mac_ctrl_frame_fwd %s autoneg on %d " % (
                             rx_flow_control,
                             tx_flow_control,
                             pause_frame_fwd,
                             self.rx_port),
                             "testpmd> ")

        self.dut.send_expect("set fwd csum", "testpmd> ")
        self.dut.send_expect("start", "testpmd> ")

        self.tester.scapy_append('wrpcap("test.pcap",[Ether()/IP()/UDP()/("X"*%d)])' %
                                 TestLinkFlowctrl.payload_size)

        self.tester.scapy_execute()

        # Run traffic generator
        result = self.tester.traffic_generator_loss(tgenInput, 100)
        self.dut.send_expect("stop", "testpmd> ")

        return result

    def get_testpmd_port_stats(self, ports):
        """
            Returns the number of packets transmitted and received from testpmd.
            Uses testpmd show port stats.
        """

        rx_pattern = "RX-packets: (\d*)"
        tx_pattern = "TX-packets: (\d*)"
        rx = re.compile(rx_pattern)
        tx = re.compile(tx_pattern)

        port_stats = {}

        for port in ports:
            out = self.dut.send_expect("show port stats %d" % port,
                                       "testpmd> ")

            rx_packets = int(rx.search(out).group(1))
            tx_packets = int(tx.search(out).group(1))

            port_stats[port] = (rx_packets, tx_packets)

        return port_stats

    def pause_frame_test(self, frame, flow_control='off',
                         pause_frame_fwd='off'):
        """
            Sets testpmd flow control and mac ctrl frame fwd according to the
            parameters, starts forwarding and clears the stats, then sends the
            passed frame and stops forwarding.
            Returns the testpmd port stats.
        """

        tester_tx_port = self.tester.get_local_port(self.rx_port)
        tx_interface = self.tester.get_interface(tester_tx_port)
        tester_rx_port = self.tester.get_local_port(self.tx_port)

        tgenInput = []
        tgenInput.append((tester_tx_port, tester_rx_port, "test.pcap"))

        self.dut.send_expect("set flow_ctrl rx %s tx %s 300 50 10 1 mac_ctrl_frame_fwd %s autoneg on %d " % (
                             flow_control,
                             flow_control,
                             pause_frame_fwd,
                             self.rx_port),
                             "testpmd> ")

        self.dut.send_expect("set fwd io", "testpmd> ")
        self.dut.send_expect("start", "testpmd> ")
        self.dut.send_expect("clear port stats all", "testpmd> ")

        self.tester.scapy_foreground()
        self.tester.scapy_append('sendp(%s, iface="%s", count=%d)' % (frame,
                                                                      tx_interface,
                                                                      TestLinkFlowctrl.frames_to_sent))

        self.tester.scapy_execute()

        # The following sleep is needed to allow all the packets to arrive.
        # 1s works for Crown Pass (FC18) DUT, Lizard Head Pass (FC14) tester
        # using Niantic. Increase it in case of packet loosing.
        sleep(1)

        self.dut.send_expect("stop", "testpmd> ")

        port_stats = self.get_testpmd_port_stats((self.rx_port, self.tx_port))

        return port_stats

    def check_pause_frame_test_result(self, result, expected_rx=False, expected_fwd=False):
        """
            Verifies the test results (use pause_frame_test before) against
            the expected behavior.
        """
        print "Result (port, rx, tx) %s,  expected rx %s, expected fwd %s" % (result,
                                                                              expected_rx,
                                                                              expected_fwd)

        if expected_rx:
            self.verify(result[self.rx_port][0] == TestLinkFlowctrl.frames_to_sent,
                        "Pause Frames are not being received by testpmd (%d received)" %
                        result[self.rx_port][0])
            if expected_fwd:
                self.verify(result[self.tx_port][1] == TestLinkFlowctrl.frames_to_sent,
                            "Pause Frames are not being forwarded by testpmd (%d sent)" % (
                                result[self.tx_port][1]))
            else:
                self.verify(result[self.tx_port][1] == 0,
                            "Pause Frames are being forwarded by testpmd (%d sent)" % (
                                result[self.tx_port][1]))
        else:
            self.verify(result[self.rx_port][0] == 0,
                        "Pause Frames are being received by testpmd (%d received)" %
                        result[self.rx_port][0])

    def build_pause_frame(self, option=0):
        """
        Build the PAUSE Frame for the tests. 3 available options:
        0: Correct frame (correct src and dst addresses and opcode)
        1: Wrong source frame (worng src, correct and dst address and opcode)
        2: Wrong opcode frame (correct src and dst address and wrong opcode)
        3: Wrong destination frame (correct src and opcode, wrong dst address)
        """

        if option == 1:
            return TestLinkFlowctrl.pause_frame % ("00:01:02:03:04:05",
                                                   TestLinkFlowctrl.pause_frame_dst,
                                                   TestLinkFlowctrl.pause_frame_type,
                                                   TestLinkFlowctrl.pause_frame_opcode,
                                                   TestLinkFlowctrl.pause_frame_control,
                                                   TestLinkFlowctrl.pause_frame_paddign)

        elif option == 2:
            return TestLinkFlowctrl.pause_frame % (self.tester_tx_mac,
                                                   TestLinkFlowctrl.pause_frame_dst,
                                                   TestLinkFlowctrl.pause_frame_type,
                                                   "\\x00\\x02",
                                                   TestLinkFlowctrl.pause_frame_control,
                                                   TestLinkFlowctrl.pause_frame_paddign)
        elif option == 3:
            return TestLinkFlowctrl.pause_frame % (self.tester_tx_mac,
                                                   "01:80:C2:00:AB:10",
                                                   TestLinkFlowctrl.pause_frame_type,
                                                   TestLinkFlowctrl.pause_frame_opcode,
                                                   TestLinkFlowctrl.pause_frame_control,
                                                   TestLinkFlowctrl.pause_frame_paddign)

        return TestLinkFlowctrl.pause_frame % (self.tester_tx_mac,
                                               TestLinkFlowctrl.pause_frame_dst,
                                               TestLinkFlowctrl.pause_frame_type,
                                               TestLinkFlowctrl.pause_frame_opcode,
                                               TestLinkFlowctrl.pause_frame_control,
                                               TestLinkFlowctrl.pause_frame_paddign)

    def test_flowctrl_off_pause_fwd_off(self):
        """
        Flow control disabled, MAC PAUSE frame forwarding disabled.
        PAUSE Frames must not be received by testpmd
        """

        pause_frames = [self.build_pause_frame(0),
                        self.build_pause_frame(1),
                        self.build_pause_frame(2),
                        self.build_pause_frame(3)]

        for frame in pause_frames:
            port_stats = self.pause_frame_test(frame)
            self.check_pause_frame_test_result(port_stats)

    def test_flowctrl_on_pause_fwd_off(self):
        """
        Flow control enabled, MAC PAUSE frame forwarding disabled.
        PAUSE Frames must not be received by testpmd
        """

        pause_frames = [self.build_pause_frame(0),
                        self.build_pause_frame(1),
                        self.build_pause_frame(2),
                        self.build_pause_frame(3)]

        for frame in pause_frames:
            port_stats = self.pause_frame_test(frame, flow_control='on')
            self.check_pause_frame_test_result(port_stats)

    def test_flowctrl_off_pause_fwd_on(self):
        """
        Flow control disabled, MAC PAUSE frame forwarding enabled.
        All PAUSE Frames must be forwarded by testpmd.
        """

        # Regular frames, check for no frames received
        pause_frame = self.build_pause_frame()
        port_stats = self.pause_frame_test(pause_frame, pause_frame_fwd='on')
        self.check_pause_frame_test_result(port_stats, True, True)

        # Wrong src MAC, check for no frames received
        pause_frame = self.build_pause_frame(1)
        port_stats = self.pause_frame_test(pause_frame, pause_frame_fwd='on')
        self.check_pause_frame_test_result(port_stats, True, True)

        # Unrecognized frames (wrong opcode), check for all frames received and fwd
        pause_frame = self.build_pause_frame(2)
        port_stats = self.pause_frame_test(pause_frame, pause_frame_fwd='on')
        self.check_pause_frame_test_result(port_stats, True, True)

        # Wrong dst MAC, check for all frames received
        pause_frame = self.build_pause_frame(3)
        port_stats = self.pause_frame_test(pause_frame, pause_frame_fwd='on')
        self.check_pause_frame_test_result(port_stats, True, True)

    def test_flowctrl_on_pause_fwd_on(self):
        """
        Flow control enabled, MAC PAUSE frame forwarding enabled.
        Only unrecognized PAUSE Frames must be forwarded by testpmd.
        """

        # Regular frames, check for no frames received
        pause_frame = self.build_pause_frame()
        port_stats = self.pause_frame_test(pause_frame, flow_control='on',
                                           pause_frame_fwd='on')
        self.check_pause_frame_test_result(port_stats)

        # Wrong src MAC, check for no frames received
        pause_frame = self.build_pause_frame(1)
        port_stats = self.pause_frame_test(pause_frame, flow_control='on',
                                           pause_frame_fwd='on')
        self.check_pause_frame_test_result(port_stats)

        # Unrecognized frames (wrong opcode), check for all frames received and fwd
        pause_frame = self.build_pause_frame(2)
        port_stats = self.pause_frame_test(pause_frame, flow_control='on',
                                           pause_frame_fwd='on')
        self.check_pause_frame_test_result(port_stats, True, True)

        # Wrong dst MAC, check for all frames received
        pause_frame = self.build_pause_frame(3)
        port_stats = self.pause_frame_test(pause_frame, flow_control='on',
                                           pause_frame_fwd='on')
        self.check_pause_frame_test_result(port_stats, True, True)

    def test_perf_flowctrl_on_pause_fwd_on(self):
        """
        Disable link flow control and PAUSE frame forwarding
        """

        result = self.pause_frame_loss_test(rx_flow_control='on',
                                            tx_flow_control='on',
                                            pause_frame_fwd='on')

        print "Packet loss: %.3f%%" % result

        self.verify(result <= 0.01,
                    "Link flow control fail, the loss percent is more than 1%")

    def test_perf_flowctrl_on_pause_fwd_off(self):
        """
        Disable link flow control and enable PAUSE frame forwarding
        """

        result = self.pause_frame_loss_test(rx_flow_control='on',
                                            tx_flow_control='on',
                                            pause_frame_fwd='off')

        print "Packet loss: %.3f%%" % result

        self.verify(result <= 0.01,
                    "Link flow control fail, the loss percent is more than 1%")

    def test_perf_flowctrl_rx_on(self):
        """
        Enable only rx link flow control
        """

        result = self.pause_frame_loss_test(rx_flow_control='on',
                                            tx_flow_control='on',
                                            pause_frame_fwd='off')

        print "Packet loss: %.3f%%" % result

        self.verify(result <= 0.01,
                    "Link flow control fail, the loss percent is more than 1%")

    def test_perf_flowctrl_off_pause_fwd_on(self):
        """
        Enable link flow control and disable PAUSE frame forwarding
        """

        result = self.pause_frame_loss_test(rx_flow_control='off',
                                            tx_flow_control='off',
                                            pause_frame_fwd='on')

        print "Packet loss: %.3f%%" % result

        self.verify(result >= 0.5,
                    "Link flow control fail, the loss percent is less than 50%")

    def test_perf_flowctrl_off_pause_fwd_off(self):
        """
        Disable link flow control and PAUSE frame forwarding
        """

        result = self.pause_frame_loss_test(rx_flow_control='off',
                                            tx_flow_control='off',
                                            pause_frame_fwd='off')

        print "Packet loss: %.3f%%" % result

        self.verify(result >= 0.5,
                    "Link flow control fail, the loss percent is less than 50%")

    def test_perf_flowctrl_tx_on(self):
        """
        Disable link flow control and PAUSE frame forwarding
        """

        result = self.pause_frame_loss_test(rx_flow_control='off',
                                            tx_flow_control='on',
                                            pause_frame_fwd='off')

        print "Packet loss: %.3f%%" % result

        self.verify(result <= 0.01,
                    "Link flow control fail, the loss percent is more than 1%")

    def tear_down_all(self):
        """
        Run after each test case.
        """
        self.dut.send_expect("quit", "# ")
