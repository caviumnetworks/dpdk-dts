# <COPYRIGHT_TAG>

import re
import time

import dts
from qemu_kvm import QEMUKvm
from test_case import TestCase
from pmd_output import PmdOutput
from utils import RED, GREEN
from net_device import NetDevice
from crb import Crb
from scapy.all import *
from settings import HEADER_SIZE
VM_CORES_MASK = 'all'

class TestVfOffload(TestCase):

    def set_up_all(self):
        self.dut_ports = self.dut.get_ports(self.nic)
        self.verify(len(self.dut_ports) > 1, "Insufficient ports")
        self.vm0 = None
        self.setup_2pf_2vf_1vm_env_flag = 0
        self.setup_2pf_2vf_1vm_env(driver='')
        self.vm0_dut_ports = self.vm_dut_0.get_ports('any')
        self.portMask = dts.create_mask([self.vm0_dut_ports[0]])
        self.vm0_testpmd = PmdOutput(self.vm_dut_0)

    def set_up(self):
        pass

    def setup_2pf_2vf_1vm_env(self, driver='default'):

        self.used_dut_port_0 = self.dut_ports[0]
        self.dut.generate_sriov_vfs_by_port(self.used_dut_port_0, 1, driver=driver)
        self.sriov_vfs_port_0 = self.dut.ports_info[self.used_dut_port_0]['vfs_port']
        self.used_dut_port_1 = self.dut_ports[1]
        self.dut.generate_sriov_vfs_by_port(self.used_dut_port_1, 1, driver=driver)
        self.sriov_vfs_port_1 = self.dut.ports_info[self.used_dut_port_1]['vfs_port']

        try:

            for port in self.sriov_vfs_port_0:
                port.bind_driver('pci-stub')

            for port in self.sriov_vfs_port_1:
                port.bind_driver('pci-stub')

            time.sleep(1)
            vf0_prop = {'opt_host': self.sriov_vfs_port_0[0].pci}
            vf1_prop = {'opt_host': self.sriov_vfs_port_1[0].pci}

            if driver == 'igb_uio':
                # start testpmd without the two VFs on the host
                self.host_testpmd = PmdOutput(self.dut)
                eal_param = '-b %(vf0)s -b %(vf1)s' % {'vf0': self.sriov_vfs_port_0[0].pci,
                                                       'vf1': self.sriov_vfs_port_1[0].pci}
                self.host_testpmd.start_testpmd("1S/2C/2T", eal_param=eal_param)

            # set up VM0 ENV
            self.vm0 = QEMUKvm(self.dut, 'vm0', 'vf_offload')
            self.vm0.set_vm_device(driver='pci-assign', **vf0_prop)
            self.vm0.set_vm_device(driver='pci-assign', **vf1_prop)
            self.vm_dut_0 = self.vm0.start()
            if self.vm_dut_0 is None:
                raise Exception("Set up VM0 ENV failed!")

            self.setup_2pf_2vf_1vm_env_flag = 1
        except Exception as e:
            self.destroy_2pf_2vf_1vm_env()
            raise Exception(e)

    def destroy_2pf_2vf_1vm_env(self):
        if getattr(self, 'vm0', None):
            #destroy testpmd in vm0
            self.vm0_testpmd = None
            self.vm0_dut_ports = None
            #destroy vm0
            self.vm0.stop()
            self.vm0 = None

        if getattr(self, 'host_testpmd', None):
            self.host_testpmd.execute_cmd('quit', '# ')
            self.host_testpmd = None

        if getattr(self, 'used_dut_port_0', None):
            self.dut.destroy_sriov_vfs_by_port(self.used_dut_port_0)
            port = self.dut.ports_info[self.used_dut_port_0]['port']
            port.bind_driver()
            self.used_dut_port_0 = None

        if getattr(self, 'used_dut_port_1', None):
            self.dut.destroy_sriov_vfs_by_port(self.used_dut_port_1)
            port = self.dut.ports_info[self.used_dut_port_1]['port']
            port.bind_driver()
            self.used_dut_port_1 = None

        for port_id in self.dut_ports:
            port = self.dut.ports_info[port_id]['port']
            port.bind_driver()

        self.setup_2pf_2vf_1vm_env_flag = 0

    def checksum_enablehw(self, port, dut):
        dut.send_expect("csum set ip hw %d" % port, "testpmd>")
        dut.send_expect("csum set udp hw %d" % port, "testpmd>")
        dut.send_expect("csum set tcp hw %d" % port, "testpmd>")
        dut.send_expect("csum set sctp hw %d" % port, "testpmd>")

    def checksum_enablesw(self, port, dut):
        dut.send_expect("csum set ip sw %d" % port, "testpmd>")
        dut.send_expect("csum set udp sw %d" % port, "testpmd>")
        dut.send_expect("csum set tcp sw %d" % port, "testpmd>")
        dut.send_expect("csum set sctp sw %d" % port, "testpmd>")

    def checksum_validate(self, packets_sent, packets_expected):
        """
        Validate the checksum.
        """
        tx_interface = self.tester.get_interface(self.tester.get_local_port(self.dut_ports[0]))
        rx_interface = self.tester.get_interface(self.tester.get_local_port(self.dut_ports[0]))

        sniff_src = self.vm0_testpmd.get_port_mac(0)
        checksum_pattern = re.compile("chksum.*=.*(0x[0-9a-z]+)")

        chksum = dict()
        result = dict()

        self.tester.send_expect("scapy", ">>> ")

        for packet_type in packets_expected.keys():
            self.tester.send_expect("p = %s" % packets_expected[packet_type], ">>>")
            out = self.tester.send_expect("p.show2()", ">>>")
            chksums = checksum_pattern.findall(out)
            chksum[packet_type] = chksums
            print packet_type, ": ", chksums

        self.tester.send_expect("exit()", "#")

        self.tester.scapy_background()
        self.tester.scapy_append('p = sniff(filter="ether src %s", iface="%s", count=%d)' % (sniff_src, rx_interface, len(packets_sent)))
        self.tester.scapy_append('nr_packets=len(p)')
        self.tester.scapy_append('reslist = [p[i].sprintf("%IP.chksum%;%TCP.chksum%;%UDP.chksum%;%SCTP.chksum%") for i in range(nr_packets)]')
        self.tester.scapy_append('import string')
        self.tester.scapy_append('RESULT = string.join(reslist, ",")')

        # Send packet.
        self.tester.scapy_foreground()

        for packet_type in packets_sent.keys():
            self.tester.scapy_append('sendp([%s], iface="%s")' % (packets_sent[packet_type], tx_interface))

        self.tester.scapy_execute()
        out = self.tester.scapy_get_result()
        packets_received = out.split(',')
        self.verify(len(packets_sent) == len(packets_received), "Unexpected Packets Drop")

        for packet_received in packets_received:
            ip_checksum, tcp_checksum, udp_checksup, sctp_checksum = packet_received.split(';')
            print "ip_checksum: ", ip_checksum, "tcp_checksum:, ", tcp_checksum, "udp_checksup: ", udp_checksup, "sctp_checksum: ", sctp_checksum

            packet_type = ''
            l4_checksum = ''
            if tcp_checksum != '??':
                packet_type = 'TCP'
                l4_checksum = tcp_checksum
            elif udp_checksup != '??':
                packet_type = 'UDP'
                l4_checksum = udp_checksup
            elif sctp_checksum != '??':
                packet_type = 'SCTP'
                l4_checksum = sctp_checksum

            if ip_checksum != '??':
                packet_type = 'IP/' + packet_type
                if chksum[packet_type] != [ip_checksum, l4_checksum]:
                    result[packet_type] = packet_type + " checksum error"
            else:
                packet_type = 'IPv6/' + packet_type
                if chksum[packet_type] != [l4_checksum]:
                    result[packet_type] = packet_type + " checksum error"

        return result

    def test_checksum_offload_enable(self):
        """
        Enable HW Checksum offload.
        Send packet with incorrect checksum, 
        can rx it and reported the checksum error, 
        verify forwarded packets have correct checksum
        """
        self.vm0_testpmd.start_testpmd(VM_CORES_MASK, "--portmask=%s " %
                                      (self.portMask) + "--disable-hw-vlan --enable-rx-cksum " + "--txqflags=0 " +
                                      "--crc-strip --port-topology=loop")
        self.vm0_testpmd.execute_cmd('set fwd csum')

        time.sleep(2)
        port_id_0 = 0
        mac = self.vm0_testpmd.get_port_mac(0)

        sndIP = '10.0.0.1'
        sndIPv6 = '::1'
        pkts = {'IP/UDP': 'Ether(dst="%s", src="52:00:00:00:00:00")/IP(src="%s", chksum=0xf)/UDP(chksum=0xf)/("X"*46)' % (mac, sndIP),
                'IP/TCP': 'Ether(dst="%s", src="52:00:00:00:00:00")/IP(src="%s", chksum=0xf)/TCP(chksum=0xf)/("X"*46)' % (mac, sndIP),
                'IP/SCTP': 'Ether(dst="%s", src="52:00:00:00:00:00")/IP(src="%s", chksum=0xf)/SCTP(chksum=0xf)/("X"*48)' % (mac, sndIP),
                'IPv6/UDP': 'Ether(dst="%s", src="52:00:00:00:00:00")/IPv6(src="%s")/UDP(chksum=0xf)/("X"*46)' % (mac, sndIPv6),
                'IPv6/TCP': 'Ether(dst="%s", src="52:00:00:00:00:00")/IPv6(src="%s")/TCP(chksum=0xf)/("X"*46)' % (mac, sndIPv6)}

        expIP = "10.0.0.2"
        expIPv6 = '::2'
        pkts_ref = {'IP/UDP': 'Ether(dst="02:00:00:00:00:00", src="%s")/IP(src="%s")/UDP()/("X"*46)' % (mac, expIP),
                    'IP/TCP': 'Ether(dst="02:00:00:00:00:00", src="%s")/IP(src="%s")/TCP()/("X"*46)' % (mac, expIP),
                    'IP/SCTP': 'Ether(dst="02:00:00:00:00:00", src="%s")/IP(src="%s")/SCTP()/("X"*48)' % (mac, expIP),
                    'IPv6/UDP': 'Ether(dst="02:00:00:00:00:00", src="%s")/IPv6(src="%s")/UDP()/("X"*46)' % (mac, expIPv6),
                    'IPv6/TCP': 'Ether(dst="02:00:00:00:00:00", src="%s")/IPv6(src="%s")/TCP()/("X"*46)' % (mac, expIPv6)}

        if self.nic in ['redrockcanyou', 'atwood']:
            del pkts['IP/SCTP']
            del pkts_ref['IP/SCTP']

        self.checksum_enablehw(0,self.vm_dut_0)

        self.vm0_testpmd.execute_cmd('start')
        result = self.checksum_validate(pkts, pkts_ref)

        # Validate checksum on the receive packet
        out = self.vm0_testpmd.execute_cmd('stop')
        bad_ipcsum = self.vm0_testpmd.get_pmd_value("Bad-ipcsum:", out)
        bad_l4csum = self.vm0_testpmd.get_pmd_value("Bad-l4csum:", out)
        self.verify(bad_ipcsum == 3, "Bad-ipcsum check error")
        self.verify(bad_l4csum == 5, "Bad-l4csum check error")

        self.verify(len(result) == 0, string.join(result.values(), ","))

    def test_checksum_offload_disable(self):
        """
        disable HW checksum offload on tx port, SW Checksum check.
        SW Checksum on by default.
        Send same packet with incorrect checksum and verify checksum is valid.
        """

        self.vm0_testpmd.start_testpmd(VM_CORES_MASK, "--portmask=%s " %
                                      (self.portMask) + "--disable-hw-vlan --enable-rx-cksum " +
                                      "--crc-strip --port-topology=loop")
        self.vm0_testpmd.execute_cmd('set fwd csum')

        time.sleep(2)

        mac = self.vm0_testpmd.get_port_mac(0)
        sndIP = '10.0.0.1'
        sndIPv6 = '::1'
        sndPkts = {'IP/UDP': 'Ether(dst="%s", src="52:00:00:00:00:00")/IP(src="%s",chksum=0xf)/UDP(chksum=0xf)/("X"*46)' % (mac, sndIP),
                   'IP/TCP': 'Ether(dst="%s", src="52:00:00:00:00:00")/IP(src="%s",chksum=0xf)/TCP(chksum=0xf)/("X"*46)' % (mac, sndIP),
                   'IPv6/UDP': 'Ether(dst="%s", src="52:00:00:00:00:00")/IPv6(src="%s")/UDP(chksum=0xf)/("X"*46)' % (mac, sndIPv6),
                   'IPv6/TCP': 'Ether(dst="%s", src="52:00:00:00:00:00")/IPv6(src="%s")/TCP(chksum=0xf)/("X"*46)' % (mac, sndIPv6)}

        expIP = "10.0.0.2"
        expIPv6 = '::2'
        expPkts = {'IP/UDP': 'Ether(dst="02:00:00:00:00:00", src="%s")/IP(src="%s")/UDP()/("X"*46)' % (mac, expIP),
                   'IP/TCP': 'Ether(dst="02:00:00:00:00:00", src="%s")/IP(src="%s")/TCP()/("X"*46)' % (mac, expIP),
                   'IPv6/UDP': 'Ether(dst="02:00:00:00:00:00", src="%s")/IPv6(src="%s")/UDP()/("X"*46)' % (mac, expIPv6),
                   'IPv6/TCP': 'Ether(dst="02:00:00:00:00:00", src="%s")/IPv6(src="%s")/TCP()/("X"*46)' % (mac, expIPv6)}

        self.vm0_testpmd.execute_cmd('start')
        result = self.checksum_validate(sndPkts, expPkts)

        # Validate checksum on the receive packet
        out = self.vm0_testpmd.execute_cmd('stop')
        bad_ipcsum = self.vm0_testpmd.get_pmd_value("Bad-ipcsum:", out)
        bad_l4csum = self.vm0_testpmd.get_pmd_value("Bad-l4csum:", out)
        self.verify(bad_ipcsum == 2, "Bad-ipcsum check error")
        self.verify(bad_l4csum == 4, "Bad-l4csum check error")

        self.verify(len(result) == 0, string.join(result.values(), ","))

    def tcpdump_start_sniffing(self, ifaces=[]):
        """
        Starts tcpdump in the background to sniff the tester interface where
        the packets are transmitted to and from the self.dut.
        All the captured packets are going to be stored in a file for a
        post-analysis.
        """

        for iface in ifaces:
            command = ('tcpdump -w tcpdump_{0}.pcap -i {0} 2>tcpdump_{0}.out &').format(iface)
            self.tester.send_expect('rm -f tcpdump_{0}.pcap', '#').format(iface)
            self.tester.send_expect(command, '#')

    def tcpdump_stop_sniff(self):
        """
        Stops the tcpdump process running in the background.
        """
        self.tester.send_expect('killall tcpdump', '#')
        time.sleep(1)
        self.tester.send_expect('echo "Cleaning buffer"', '#')
        time.sleep(1)

    def tcpdump_command(self, command):
        """
        Sends a tcpdump related command and returns an integer from the output
        """

        result = self.tester.send_expect(command, '#')
        print result
        return int(result.strip())

    def number_of_packets(self, iface):
        """
        By reading the file generated by tcpdump it counts how many packets were
        forwarded by the sample app and received in the self.tester. The sample app
        will add a known MAC address for the test to look for.
        """

        command = ('tcpdump -A -nn -e -v -r tcpdump_{iface}.pcap 2>/dev/null | ' +
                   'grep -c "seq"')
        return self.tcpdump_command(command.format(**locals()))

    def test_tso(self):
        """
        TSO IPv4 TCP, IPv6 TCP, VXLan testing
        """
        tx_interface = self.tester.get_interface(self.tester.get_local_port(self.dut_ports[0]))
        rx_interface = self.tester.get_interface(self.tester.get_local_port(self.dut_ports[1]))

        self.frame_sizes = [128, 1458]
        self.headers_size = HEADER_SIZE['eth'] + HEADER_SIZE['ip'] + HEADER_SIZE['tcp']
        padding = self.frame_sizes[0] - self.headers_size

        self.tester.send_expect("ethtool -K %s rx off tx off tso off gso off gro off lro off" % tx_interface, "# ")
        self.tester.send_expect("ip l set %s up" % tx_interface, "# ")

        self.portMask = dts.create_mask([self.vm0_dut_ports[0]])
        self.vm0_testpmd.start_testpmd(VM_CORES_MASK, "--portmask=%s " %
                                      (self.portMask) + "--enable-rx-cksum " +
                                      "--txqflags=0 " + 
                                      "--crc-strip --port-topology=loop")

        mac = self.vm0_testpmd.get_port_mac(0)

        self.checksum_enablehw(0,self.vm_dut_0)
        self.vm0_testpmd.execute_cmd("tso set 800 %d" % self.vm0_dut_ports[1])
        self.vm0_testpmd.execute_cmd("set fwd csum")
        self.vm0_testpmd.execute_cmd("start")

        self.tester.scapy_foreground()
        time.sleep(5)

        # IPv4 tcp test

        self.tcpdump_start_sniffing([tx_interface, rx_interface])
        self.tester.scapy_append('sendp([Ether(dst="%s",src="52:00:00:00:00:00")/IP(src="192.168.1.1",dst="192.168.1.2")/TCP(sport=1021,dport=1021)/("X"*%s)], iface="%s")' % (mac, padding, tx_interface))
        out = self.tester.scapy_execute()
        out = self.vm0_testpmd.execute_cmd("show port stats all")
        print out
        self.tcpdump_stop_sniff()
        rx_stats = self.number_of_packets(rx_interface)
        if (rx_stats == 2):
            self.verify(1, "Pass")

        # IPv6 tcp test

        self.tcpdump_start_sniffing([tx_interface, rx_interface])
        self.tester.scapy_append('sendp([Ether(dst="%s", src="52:00:00:00:00:00")/IPv6(src="FE80:0:0:0:200:1FF:FE00:200", dst="3555:5555:6666:6666:7777:7777:8888:8888")/TCP(sport=1021,dport=1021)/("X"*%s)], iface="%s")' % (mac, padding, tx_interface))
        out = self.tester.scapy_execute()
        out = self.vm0_testpmd.execute_cmd("show port stats all")
        print out
        self.tcpdump_stop_sniff()
        rx_stats = self.number_of_packets(rx_interface)
        if (rx_stats == 2):
            self.verify(1, "Pass")


    def tear_down(self):
        self.vm0_testpmd.execute_cmd('quit', '# ')
        pass

    def tear_down_all(self):
        print "tear_down_all"
        if self.setup_2pf_2vf_1vm_env_flag == 1:
            self.destroy_2pf_2vf_1vm_env()
