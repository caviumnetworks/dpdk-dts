# <COPYRIGHT_TAG>

"""
DPDK Test suite.

Test 82599 Flow Director Support in DPDK
"""

import dcts
import time


from test_case import TestCase

#
#
# Test class.
#


class TestFdir(TestCase):

    #
    #
    # Utility methods and other non-test code.
    #

    def send_and_verify(self, condition, packet):
        """
        Send packages and verify behavior.
        """
        self.tester.scapy_foreground()
        self.tester.scapy_append('sys.path.append("./")')
        self.tester.scapy_append('from sctp import *')
        self.tester.scapy_append(packet)
        self.dut.send_expect("start", "testpmd>")
        self.tester.scapy_execute()
        time.sleep(.5)
        out = self.dut.send_expect("stop", "testpmd>")
        if condition:
            self.verify("PKT_RX_PKT_RX_FDIR" in out, "FDIR hash not displayed when required")
        else:
            self.verify("PKT_RX_PKT_RX_FDIR" not in out, "FDIR hash displayed when not required")

    #
    #
    #
    # Test cases.
    #
    def set_up_all(self):
        """
        Run at the start of each test suite.
        """
        self.verify('bsdapp' not in self.target, "FDIR not support freebsd")
        self.verify(self.nic in ["kawela", "niantic"], "NIC Unsupported: " + str(self.nic))

        ports = self.dut.get_ports(self.nic)
        self.verify(len(ports) >= 2, "Not enough ports available")

    def set_up(self):
        """
        Run before each test case.
        """
        pass

    def test_fdir_space(self):
        """
        Setting memory reserved for FDir filters.
        """

        dutPorts = self.dut.get_ports(self.nic)

        self.dut.send_expect("./%s/app/testpmd -c 0xff -n 1 -- -i --rxq=2 --txq=2 --disable-rss --pkt-filter-mode=perfect --pkt-filter-size=64K" % self.target, "testpmd>", 120)
        out = self.dut.send_expect("show port fdir %s" % dutPorts[0], "testpmd>")
        self.dut.send_expect("quit", "# ", 30)
        self.verify("free:     2048" in out, "Free space doesn't match the expected value")

        self.dut.send_expect("./%s/app/testpmd -c 0xff -n 1 -- -i --rxq=2 --txq=2 --disable-rss --pkt-filter-mode=perfect --pkt-filter-size=128K" % self.target, "testpmd>", 120)
        out = self.dut.send_expect("show port fdir %s" % dutPorts[0], "testpmd>")
        self.dut.send_expect("quit", "# ", 30)
        self.verify("free:     4096" in out, "Free space doesn't match the expected value")

        self.dut.send_expect("./%s/app/testpmd -c 0xff -n 1 -- -i --rxq=2 --txq=2 --disable-rss --pkt-filter-mode=perfect --pkt-filter-size=256K" % self.target, "testpmd>", 120)
        out = self.dut.send_expect("show port fdir %s" % dutPorts[0], "testpmd>")
        self.dut.send_expect("quit", "# ", 30)
        self.verify("free:     8192" in out, "Free space doesn't match the expected value")

    def test_fdir_signatures(self):
        """
        FDir signature matching mode.
        """

        dutPorts = self.dut.get_ports(self.nic)
        localPort = self.tester.get_local_port(dutPorts[0])
        itf = self.tester.get_interface(localPort)

        self.dut.kill_all()
        self.dut.send_expect("./%s/app/testpmd -c 0xff -n 1 -- -i --portmask=%s --rxq=2 --txq=2 --disable-rss --pkt-filter-mode=perfect --pkt-filter-report-hash=none" % (self.target, dcts.create_mask([dutPorts[0]])), "testpmd>", 120)
        self.dut.send_expect("set verbose 1", "testpmd>")
        self.dut.send_expect("set fwd rxonly", "testpmd>")
        self.dut.send_expect("set nbcore 3", "testpmd>")

        self.send_and_verify(False, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/UDP(sport=1024,dport=1024)], iface="%s")' % (itf, itf))

        self.dut.send_expect("add_perfect_filter %s udp src 192.168.0.1 1024 dst 192.168.0.2 1024 flexbytes 0x800 vlan 0 queue 1 soft 0x14" % dutPorts[0], "testpmd>")
        self.send_and_verify(False, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/UDP(sport=1024,dport=1024)], iface="%s")' % (itf, itf))

        self.dut.send_expect("quit", "# ", 30)

        self.dut.send_expect("./%s/app/testpmd -c 0xff -n 1 -- -i --portmask=%s --rxq=2 --txq=2 --disable-rss --pkt-filter-mode=perfect --pkt-filter-report-hash=match" % (self.target, dcts.create_mask([dutPorts[0]])), "testpmd>", 120)
        self.dut.send_expect("set verbose 1", "testpmd>")
        self.dut.send_expect("set fwd rxonly", "testpmd>")
        self.dut.send_expect("set nbcore 3", "testpmd>")

        self.send_and_verify(False, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/UDP(sport=1024,dport=1024)], iface="%s")' % (itf, itf))

        self.dut.send_expect("add_perfect_filter %s udp src 192.168.0.1 1024 dst 192.168.0.2 1024 flexbytes 0x800 vlan 0 queue 1 soft 0x14" % dutPorts[0], "testpmd>")
        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/UDP(sport=1024,dport=1024)], iface="%s")' % (itf, itf))

        self.dut.send_expect("upd_perfect_filter %s udp src 192.168.1.1 0 dst 192.168.1.2 0 flexbytes 0x800 vlan 0 queue 1 soft 0x14" % dutPorts[0], "testpmd>")

        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/UDP(sport=1024,dport=1024)], iface="%s")' % (itf, itf))

        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.1.1", dst="192.168.1.2")/UDP(sport=0,dport=0)], iface="%s")' % (itf, itf))

        self.dut.send_expect("rm_perfect_filter %s udp src 192.168.1.1 0 dst 192.168.1.2 0 flexbytes 0x800 vlan 0 soft 0x14" % dutPorts[0], "testpmd>")

        self.send_and_verify(False, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.1.1", dst="192.168.1.2")/UDP(sport=0,dport=0)], iface="%s")' % (itf, itf))

        self.dut.send_expect("quit", "# ", 30)

        self.dut.send_expect("./%s/app/testpmd -c 0xff -n 1 -- -i --portmask=%s --rxq=2 --txq=2 --disable-rss --pkt-filter-mode=perfect --pkt-filter-report-hash=always" % (self.target, dcts.create_mask([dutPorts[0]])), "testpmd>", 120)
        self.dut.send_expect("set verbose 1", "testpmd>")
        self.dut.send_expect("set fwd rxonly", "testpmd>")
        self.dut.send_expect("set nbcore 3", "testpmd>")

        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/UDP(sport=1024,dport=1024)], iface="%s")' % (itf, itf))

        self.dut.send_expect("add_perfect_filter %s udp src 192.168.0.1 1024 dst 192.168.0.2 1024 flexbytes 0x800 vlan 0 queue 1 soft 0x14" % dutPorts[0], "testpmd>")
        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/UDP(sport=1024,dport=1024)], iface="%s")' % (itf, itf))

        self.dut.send_expect("quit", "# ", 30)

    def test_fdir_matching(self):
        """
        FDir matching mode
        """

        dutPorts = self.dut.get_ports(self.nic)
        localPort = self.tester.get_local_port(dutPorts[0])
        itf = self.tester.get_interface(localPort)

        self.dut.kill_all()
        self.dut.send_expect("./%s/app/testpmd -c 0xff -n 1 -- -i --portmask=%s --rxq=2 --txq=2 --disable-rss --pkt-filter-mode=signature --pkt-filter-report-hash=match" % (self.target, dcts.create_mask([dutPorts[0]])), "testpmd>", 120)
        self.dut.send_expect("set verbose 1", "testpmd>")
        self.dut.send_expect("set fwd rxonly", "testpmd>")
        self.dut.send_expect("set nbcore 3", "testpmd>")

        self.send_and_verify(False, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/UDP(sport=1024,dport=1024)], iface="%s")' % (itf, itf))

        self.dut.send_expect("add_signature_filter %s udp src 192.168.0.1 1024 dst 192.168.0.2 1024 flexbytes 0x800 vlan 0 queue 1" % dutPorts[0], "testpmd>")
        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/UDP(sport=1024,dport=1024)], iface="%s")' % (itf, itf))

        self.send_and_verify(False, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/TCP(sport=1024,dport=1024)], iface="%s")' % (itf, itf))

        self.dut.send_expect("upd_signature_filter %s udp src 192.168.1.1 0 dst 192.168.1.2 0 flexbytes 0x800 vlan 0 queue 1" % dutPorts[0], "testpmd>")

        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/UDP(sport=1024,dport=1024)], iface="%s")' % (itf, itf))

        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.1.1", dst="192.168.1.2")/UDP(sport=0,dport=0)], iface="%s")' % (itf, itf))

        self.dut.send_expect("rm_signature_filter %s udp src 192.168.1.1 0 dst 192.168.1.2 0 flexbytes 0x800 vlan 0" % dutPorts[0], "testpmd>")

        self.send_and_verify(False, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.1.1", dst="192.168.1.2")/UDP(sport=0,dport=0)], iface="%s")' % (itf, itf))

        self.dut.send_expect("add_signature_filter %s tcp src 192.168.0.1 1024 dst 192.168.0.2 1024 flexbytes 0x800 vlan 0 queue 1" % dutPorts[0], "testpmd>")
        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/TCP(sport=1024,dport=1024)], iface="%s")' % (itf, itf))

        self.send_and_verify(False, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/SCTP(sport=1024,dport=1024)], iface="%s")' % (itf, itf))

        self.dut.send_expect("add_signature_filter %s sctp src 192.168.0.1 0 dst 192.168.0.2 0 flexbytes 0x800 vlan 0 queue 1" % dutPorts[0], "testpmd>")
        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/SCTP(sport=1024,dport=1024)], iface="%s")' % (itf, itf))

        self.send_and_verify(False, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")], iface="%s")' % (itf, itf))

        self.dut.send_expect("add_signature_filter %s ip src 192.168.0.1 0 dst 192.168.0.2 0 flexbytes 0x800 vlan 0 queue 1" % dutPorts[0], "testpmd>")
        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")], iface="%s")' % (itf, itf))

        self.send_and_verify(False, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IPv6(src="2001:0db8:85a3:0000:0000:8a2e:0370:7000", dst="2001:0db8:85a3:0000:0000:8a2e:0370:7338")/UDP(sport=1024,dport=1024)], iface="%s")' % (itf, itf))

        self.dut.send_expect("add_signature_filter %s udp src 2001:0db8:85a3:0000:0000:8a2e:0370:7000 1024 dst 2001:0db8:85a3:0000:0000:8a2e:0370:7338 1024 flexbytes 0x86dd vlan 0 queue 1" % dutPorts[0], "testpmd>")
        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IPv6(src="2001:0db8:85a3:0000:0000:8a2e:0370:7000", dst="2001:0db8:85a3:0000:0000:8a2e:0370:7338")/UDP(sport=1024,dport=1024)], iface="%s")' % (itf, itf))

        self.dut.send_expect("quit", "# ", 30)

    def test_fdir_perfect_matching(self):
        """
        FDir perfect matching mode.
        """

        dutPorts = self.dut.get_ports(self.nic)
        localPort = self.tester.get_local_port(dutPorts[0])
        itf = self.tester.get_interface(localPort)

        self.dut.kill_all()
        self.dut.send_expect("./%s/app/testpmd -c 0xff -n 1 -- -i --portmask=%s --rxq=2 --txq=2 --disable-rss --pkt-filter-mode=perfect --pkt-filter-report-hash=match" % (self.target, dcts.create_mask([dutPorts[0]])), "testpmd>", 120)
        self.dut.send_expect("set verbose 1", "testpmd>")
        self.dut.send_expect("set fwd rxonly", "testpmd>")
        self.dut.send_expect("set nbcore 3", "testpmd>")

        self.dut.send_expect("add_perfect_filter %s udp src 192.168.0.1 1024 dst 192.168.0.2 1024 flexbytes 0x800 vlan 0 queue 1 soft 0x14" % dutPorts[0], "testpmd>")
        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/UDP(sport=1024,dport=1024)], iface="%s")' % (itf, itf))

        self.dut.send_expect("add_perfect_filter %s tcp src 192.168.0.1 1024 dst 192.168.0.2 1024 flexbytes 0x800 vlan 0 queue 1 soft 0x15" % dutPorts[0], "testpmd>")
        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/TCP(sport=1024,dport=1024)], iface="%s")' % (itf, itf))

        self.dut.send_expect("add_perfect_filter %s sctp src 192.168.0.1 0 dst 192.168.0.2 0 flexbytes 0x800 vlan 0 queue 1 soft 0x16" % dutPorts[0], "testpmd>")
        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/SCTP(sport=1024,dport=1024)], iface="%s")' % (itf, itf))

        self.dut.send_expect("add_perfect_filter %s ip src 192.168.0.1 0 dst 192.168.0.2 0 flexbytes 0x800 vlan 0 queue 1 soft 0x17" % dutPorts[0], "testpmd>")
        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")], iface="%s")' % (itf, itf))

        self.dut.send_expect("quit", "# ", 30)

    def test_fdir_filter_masks(self):
        """
        FDir filter masks.
        """

        dutPorts = self.dut.get_ports(self.nic)
        localPort = self.tester.get_local_port(dutPorts[0])
        itf = self.tester.get_interface(localPort)

        self.dut.kill_all()
        self.dut.send_expect("./%s/app/testpmd -c 0xff  -n 1 -- -i --portmask=%s --rxq=2 --txq=2 --disable-rss --pkt-filter-mode=perfect --pkt-filter-size=64K --pkt-filter-report-hash=match" % (self.target, dcts.create_mask([dutPorts[0]])), "testpmd>", 120)
        self.dut.send_expect("set verbose 1", "testpmd>")
        self.dut.send_expect("set fwd rxonly", "testpmd>")
        self.dut.send_expect("set nbcore 3", "testpmd>")

        self.dut.send_expect("set_masks_filter %s only_ip_flow 0 src_mask 0xffffff00 0xffff dst_mask 0xffffff00 0xffff flexbytes 1 vlan_id 1 vlan_prio 1" % dutPorts[0], "testpmd>")
        self.dut.send_expect("add_perfect_filter %s udp src 192.168.0.0 1024 dst 192.168.0.0 1024 flexbytes 0x800 vlan 0 queue 1 soft 0x17" % dutPorts[0], "testpmd>")
        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/UDP(sport=1024,dport=1024)], iface="%s")' % (itf, itf))

        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.15", dst="192.168.0.15")/UDP(sport=1024,dport=1024)], iface="%s")' % (itf, itf))

        self.send_and_verify(False, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.1.1")/UDP(sport=1024,dport=1024)], iface="%s")' % (itf, itf))

        self.dut.send_expect("set_masks_filter %s only_ip_flow 0 src_mask 0xffffffff 0xff00 dst_mask 0xffffffff 0xff00 flexbytes 1 vlan_id 1 vlan_prio 1" % dutPorts[0], "testpmd>")
        self.dut.send_expect("add_perfect_filter %s udp src 10.11.12.1 0x4400 dst 10.11.12.2 0x4500 flexbytes 0x800 vlan 0 queue 1 soft 0x4" % dutPorts[0], "testpmd>")
        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="10.11.12.1", dst="10.11.12.2")/UDP(sport=0x4400,dport=0x4500)], iface="%s")' % (itf, itf))

        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="10.11.12.1", dst="10.11.12.2")/UDP(sport=0x4411,dport=0x4517)], iface="%s")' % (itf, itf))

        self.send_and_verify(False, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="10.11.12.1", dst="10.11.12.2")/UDP(sport=0x4500,dport=0x5500)], iface="%s")' % (itf, itf))

        self.dut.send_expect("set_masks_filter %s only_ip_flow 1 src_mask 0xffffffff 0x0 dst_mask 0xffffffff 0x0 flexbytes 1 vlan_id 1 vlan_prio 1" % dutPorts[0], "testpmd>")
        self.dut.send_expect("add_perfect_filter %s ip src 192.168.0.1 0 dst 192.168.0.2 0 flexbytes 0x800 vlan 0 queue 1 soft 0x42" % dutPorts[0], "testpmd>")
        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/UDP(sport=1024, dport=1024)], iface="%s")' % (itf, itf))

        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/TCP(sport=1024, dport=1024)], iface="%s")' % (itf, itf))

        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/SCTP(sport=1024, dport=1024)], iface="%s")' % (itf, itf))

        self.dut.send_expect("quit", "# ", 30)

    def test_fdir_flexbytes_filtering(self):
        """
        FDir flexbytes filtering
        """

        dutPorts = self.dut.get_ports(self.nic)
        localPort = self.tester.get_local_port(dutPorts[0])
        itf = self.tester.get_interface(localPort)

        self.dut.kill_all()
        self.dut.send_expect("./%s/app/testpmd -c 0xff  -n 1 -- -i --portmask=%s --rxq=2 --txq=2 --disable-rss --pkt-filter-mode=perfect --pkt-filter-size=64K --pkt-filter-report-hash=match --pkt-filter-flexbytes-offset=18" % (self.target, dcts.create_mask([dutPorts[0]])), "testpmd>", 120)
        self.dut.send_expect("set verbose 1", "testpmd>")
        self.dut.send_expect("set fwd rxonly", "testpmd>")
        self.dut.send_expect("set nbcore 3", "testpmd>")

        self.dut.send_expect("add_perfect_filter %s ip src 192.168.0.1 0 dst 192.168.0.2 0 flexbytes 0x1 vlan 0 queue 1 soft 0x1" % dutPorts[0], "testpmd>")
        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/GRE(proto=0x1)/IP()/UDP()], iface="%s")' % (itf, itf))

        self.dut.send_expect("add_perfect_filter %s ip src 192.168.0.1 0 dst 192.168.0.2 0 flexbytes 0xff vlan 0 queue 1 soft 0xff" % dutPorts[0], "testpmd>")
        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/GRE(proto=0xff)/IP()/UDP()], iface="%s")' % (itf, itf))

        self.dut.send_expect("set_masks_filter %s only_ip_flow 0 src_mask 0xffffffff 0xffff dst_mask 0xffffffff 0xffff flexbytes 0 vlan_id 1 vlan_prio 1" % dutPorts[0], "testpmd>")
        self.dut.send_expect("add_perfect_filter %s ip src 192.168.0.1 0 dst 192.168.0.2 0 flexbytes 0x0 vlan 0 queue 1 soft 0x42" % dutPorts[0], "testpmd>")
        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/GRE(proto=0x1)/IP()/UDP()], iface="%s")' % (itf, itf))

        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/GRE(proto=0xFF)/IP()/UDP()], iface="%s")' % (itf, itf))

        self.dut.send_expect("quit", "# ", 30)

    def test_fdir_vlanfiltering(self):
        """
        FDir VLAN field filtering
        """

        dutPorts = self.dut.get_ports(self.nic)
        localPort = self.tester.get_local_port(dutPorts[0])
        itf = self.tester.get_interface(localPort)

        self.dut.kill_all()
        self.dut.send_expect("./%s/app/testpmd -c 0xff -n 1 -- -i --portmask=%s --nb-cores=2 --rxq=2 --txq=2 --disable-rss --pkt-filter-mode=perfect" % (self.target, dcts.create_mask([dutPorts[0]])), "testpmd>", 120)
        self.dut.send_expect("set verbose 1", "testpmd>")
        self.dut.send_expect("set fwd rxonly", "testpmd>")
        # "rx_vlan add all" has been removed from testpmd
        self.dut.send_expect("rx_vlan add 0xFFF %s" % dutPorts[0], "testpmd>")
        self.dut.send_expect("rx_vlan add 0x001 %s" % dutPorts[0], "testpmd>")
        self.dut.send_expect("rx_vlan add 0x017 %s" % dutPorts[0], "testpmd>")

        self.send_and_verify(False, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/Dot1Q(vlan=0x0FFF)/IP(src="192.168.0.1", dst="192.168.0.2")/UDP(sport=1024, dport=1024)], iface="%s")' % (itf, itf))

        self.dut.send_expect("add_perfect_filter %s udp src 192.168.0.1 1024 dst 192.168.0.2 1024 flexbytes 0x8100 vlan 0xfff queue 1 soft 0x47" % dutPorts[0], "testpmd>")
        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/Dot1Q(vlan=0x0FFF)/IP(src="192.168.0.1", dst="192.168.0.2")/UDP(sport=1024, dport=1024)], iface="%s")' % (itf, itf))

        self.dut.send_expect("set_masks_filter %s only_ip_flow 0 src_mask 0xffffffff 0xffff  dst_mask 0xffffffff 0xffff flexbytes 1 vlan_id 0 vlan_prio 0" % dutPorts[0], "testpmd>")
        self.dut.send_expect("add_perfect_filter %s udp src 192.168.0.1 1024 dst 192.168.0.2 1024 flexbytes 0x8100 vlan 0 queue 1 soft 0x47" % dutPorts[0], "testpmd>")
        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/Dot1Q(vlan=0x001)/IP(src="192.168.0.1", dst="192.168.0.2")/UDP(sport=1024, dport=1024)], iface="%s")' % (itf, itf))
        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/Dot1Q(vlan=0x0017)/IP(src="192.168.0.1", dst="192.168.0.2")/UDP(sport=1024, dport=1024)], iface="%s")' % (itf, itf))

        self.dut.send_expect("quit", "# ", 30)

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
