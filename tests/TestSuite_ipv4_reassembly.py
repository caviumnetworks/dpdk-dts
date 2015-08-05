# <COPYRIGHT_TAG>

"""
DPDK Test suite.

Test the IP reassembly feature

"""

import os
import time
from scapy.utils import struct, socket, PcapWriter
from scapy.layers.inet import Ether, IP, TCP, fragment
from scapy.route import *

import dts
from test_case import TestCase


class IpReassemblyTestConfig(object):

    """
    Helper class that encapsulates all the parameters used by the different
    test cases components.
    """

    #
    #
    # Utility methods and other non-test code.
    #

    def __init__(self, test_case, **kwargs):
        self.test_case = test_case
        self.init()
        for name in kwargs:
            setattr(self, name, kwargs[name])

    def init(self):
        self.cpu_config()
        self.ports_config()
        self.example_app_config()
        self.packets_config()

    def cpu_config(self):
        self.core_list = self.test_case.dut.get_core_list('1S/1C/1T')
        self.core_mask = dts.create_mask(self.core_list)
        self.memory_channels = self.test_case.dut.get_memory_channels()

    def ports_config(self):
        dut_ports = self.test_case.dut.get_ports(self.test_case.nic)
        dut_port = dut_ports[0]
        tester_port = self.test_case.tester.get_local_port(dut_port)
        self.tester_iface = self.test_case.tester.get_interface(tester_port)
        self.dut_port_mask = dts.create_mask([dut_port])
        self.queue_config = '({},{},{})'.format(dut_port, '0', self.core_list[0])

    def example_app_config(self):
        self.maxflows = 1024
        self.flowttl = '10s'
        self.extra_args = ''

    def packets_config(self):
        self.pcap_file = 'file.pcap'
        self.number_of_frames = 1024
        self.frags_per_frame = 4
        self.src_ip = '2.1.1.0'
        self.dst_ip = '1.1.1.111'
        self.payload_size = 140
        self.fragment_size = 40
        self.mac_src = 'DE:AD:BE:EF:02:01'
        self.mac_dst = 'DE:AD:BE:EF:01:02'
        self.tcp_src_port = 1234
        self.tcp_dst_port = 4321
        self.identification = 1

#
#
# Test class.
#


class TestIpReassembly(TestCase):

    #
    #
    #
    # Test cases.
    #

    def set_max_num_of_fragments(self, num_of_fragments=4):
        """
        Changes the maximum number of frames by modifying the example app code.
        """

        # sed_command = (r"sed -i 's/\(\s*MAX_FRAG_NUM\s*=\)\s*[[:digit:]]*/\1 %d/' " +
        #               r"examples/ip_reassembly/ipv4_rsmbl.h")
        # self.dut.send_expect("sed -i 's/CONFIG_RTE_LIBRTE_IP_FRAG_MAX_FRAG=.*$/CONFIG_RTE_LIBRTE_IP_FRAG_MAX_FRAG=%s/' ./config/common_linuxapp" %int(num_of_fragments), "# ")
        # self.dut.send_expect(sed_command % int(num_of_fragments), '#', 60)
        if 'bsdapp' in self.target:
            self.dut.send_expect("sed -i 's/CONFIG_RTE_LIBRTE_IP_FRAG_MAX_FRAG=.*$/CONFIG_RTE_LIBRTE_IP_FRAG_MAX_FRAG=%s/' ./config/common_bsdapp" % int(num_of_fragments), "# ")
        else:
            self.dut.send_expect("sed -i 's/CONFIG_RTE_LIBRTE_IP_FRAG_MAX_FRAG=.*$/CONFIG_RTE_LIBRTE_IP_FRAG_MAX_FRAG=%s/' ./config/common_linuxapp" % int(num_of_fragments), "# ")
        self.dut.send_expect("export RTE_TARGET=" + self.target, "#")
        self.dut.send_expect("export RTE_SDK=`pwd`", "#")
        self.dut.send_expect("rm -rf %s" % self.target, "# ", 5)
        self.dut.build_install_dpdk(self.target)

    def set_tester_iface_mtu(self, iface, mtu=1500):
        """
        Set the interface MTU value.
        """

        command = 'ip link set mtu {mtu} dev {iface}'
        self.tester.send_expect(command.format(**locals()), '#')

    def compile_example_app(self):
        """
        Builds the example app and checks for errors.
        """

        self.dut.send_expect('rm -rf examples/ip_reassembly/build', '#')
        out = self.dut.build_dpdk_apps('examples/ip_reassembly')
#        self.verify('Error' not in out and 'No such file' not in out,
#                    'Compilation error')

    def execute_example_app(self):
        """
        Execute the example app and checks for errors.
        """

        command = ('./examples/ip_reassembly/build/ip_reassembly -c {core_mask} ' +
                   '-n {memory_channels} --  -p {dut_port_mask} ' +
                   '--maxflows={maxflows} --flowttl={flowttl} {extra_args}')
        self.dut.send_expect(command.format(**self.test_config.__dict__), 'IP_RSMBL: ')

    def tcp_ipv4_fragments(self, src_ip, identifier):
        """
        Using the Scapy API generates a packet with the given configuration
        and returns a list containing fragmented packets.
        """

        packet = Ether() / IP() / TCP() / ("X" * self.test_config.payload_size)
        packet[Ether].src = self.test_config.mac_src
        packet[Ether].dst = self.test_config.mac_dst
        packet[IP].src = src_ip
        packet[IP].dst = self.test_config.dst_ip
        packet[IP].id = identifier
        packet[TCP].sport = self.test_config.tcp_src_port
        packet[TCP].dport = self.test_config.tcp_dst_port
        return fragment(packet, fragsize=self.test_config.fragment_size)

    def increment_ip_address(self, addr, val):
        """
        Returns the next valid IP address from a given one, like
        10.1.1.254 -> 10.1.1.255 -> 10.1.2.0 -> 10.1.2.1
        """

        ip2int = lambda ipstr: struct.unpack('!I', socket.inet_aton(ipstr))[0]
        x = ip2int(addr)
        int2ip = lambda n: socket.inet_ntoa(struct.pack('!I', n))
        return int2ip(x + 1)

    def create_fragments(self):
        """
        Returns a list of fragmented IP packets by creating one packet at the
        time, fragmenting it and adding it to a list.
        It takes the packet information from the given configuration.
        """

        all_fragments = []
        src_ip = self.test_config.src_ip
        for _ in range(self.test_config.number_of_frames):
            src_ip = self.increment_ip_address(src_ip, 1)
            identifier = self.test_config.identification % 0x10000
            fragments = self.tcp_ipv4_fragments(src_ip, identifier)
            all_fragments.extend(fragments)
            self.test_config.identification += 1
        return all_fragments

    def write_shuffled_pcap(self, fragments):
        """
        Receives a list of fragmented packets and writes them into a PCAP file
        using the Scapy API.
        Before saving the frames to a file it will reorder them like this:

        pkt0-frag3 -> pkt1-frag3 -> pkt2-frag3 -> ... -> pktN-frag3 ->
        pkt0-frag2 -> pkt1-frag2 -> pkt2-frag2 -> ... -> pktN-frag2 ->
        pkt0-frag1 -> pkt1-frag1 -> pkt2-frag1 -> ... -> pktN-frag1 ->
        pkt0-frag0 -> pkt1-frag0 -> pkt2-frag0 -> ... -> pktN-frag0.
        """

        writer = PcapWriter(self.test_config.pcap_file)
        rounds = self.test_config.frags_per_frame
        while rounds > 0:
            index = rounds - 1
            rounds -= 1
            while index < len(fragments):
                writer.write(fragments[index])
                index += self.test_config.frags_per_frame
        writer.close()

    def create_pcap_file(self):
        """
        Generates a valid PCAP file with the given configuration.
        """

        fragments = self.create_fragments()
        self.write_shuffled_pcap(fragments)

    def scapy_send_packets(self):
        """
        Calling scapy from the tester board sends the generated PCAP file to
        the DUT
        """

        self.tester.scapy_append('pcap = rdpcap("%s")' % self.test_config.pcap_file)
        self.tester.scapy_append('sendp(pcap, iface="%s")' % self.test_config.tester_iface)
        self.tester.scapy_execute()
        time.sleep(5)

    def send_packets(self):
        """
        Goes trhough all the steps to send packets from the tester to the self.dut.
        Generates the PCAP file, place it into the tester board, calls scapy and
        finally removes the PCAP file.
        """

        self.create_pcap_file()
        self.tester.session.copy_file_to(self.test_config.pcap_file)
        self.scapy_send_packets()
        os.remove(self.test_config.pcap_file)
        time.sleep(5)

    def tcpdump_start_sniffing(self):
        """
        Starts tcpdump in the background to sniff the tester interface where
        the packets are transmitted to and from the self.dut.
        All the captured packets are going to be stored in a file for a
        post-analysis.
        """

        command = ('tcpdump -w tcpdump.pcap -i %s 2>tcpdump.out &' %
                   self.test_config.tester_iface)
        self.tester.send_expect('rm -f tcpdump.pcap', '#')
        self.tester.send_expect(command, '#')

    def tcpdump_stop_sniff(self):
        """
        Stops the tcpdump process running in the background.
        """

        self.tester.send_expect('killall tcpdump', '#')
        # For the [pid]+ Done tcpdump... message after killing the process
        self.tester.send_expect('cat tcpdump.out', '#')
        time.sleep(3)

    def tcpdump_command(self, command):
        """
        Sends a tcpdump related command and returns an integer from the output
        """

        result = self.tester.send_expect(command, '#')
        return int(result.strip())

    def number_of_received_packets(self, tcp_port):
        """
        By reading the file generated by tcpdump it counts how many packets were
        forwarded by the sample app and received in the self.tester. The sample app
        will add a known MAC address for the test to look for.
        """

        command = ('tcpdump -nn -e -v -r tcpdump.pcap tcp dst port {tcp_port} 2>/dev/null | ' +
                   'grep -c 02:00:00:00:00')  # MAC address used by the example app
        return self.tcpdump_command(command.format(**locals()))

    def number_of_sent_packets(self, mac_src):
        """
        By reading the file generated by tcpdump it counts how many packets were
        sent to the DUT searching for a given MAC address.
        """

        command = ('tcpdump -nn -e -v -r tcpdump.pcap 2>/dev/null | ' +
                   'grep -c -i {mac_src}')
        return self.tcpdump_command(command.format(**locals()))

    def number_of_tcp_valid_checksum(self, tcp_port):
        """
        By reading the file generated by tcpdump it counts how many packets have
        a valid TCP checksum or how many packets were correctly assembled.
        """

        command = ('tcpdump -nn -e -v -r tcpdump.pcap tcp dst port {tcp_port} 2>/dev/null | ' +
                   'grep -c -E "cksum.*correct"')
        return self.tcpdump_command(command.format(**locals()))

    def send_n_siff_packets(self):
        """
        Sends the packets while tcpdump is sniffing on the background.
        """

        self.tcpdump_start_sniffing()
        self.send_packets()
        self.tcpdump_stop_sniff()

    def verify_sent_packets(self, expected):
        """
        Verifies if the number of sent packets is the expected.
        """

        sent_packets = self.number_of_sent_packets(self.test_config.mac_src)
        print 'sent packets: %d - expected: %d' % (sent_packets, expected)
        self.verify(sent_packets == expected, 'Not all fragments have been sent')

    def verify_received_packets(self, expected):
        """
        Verifies if the number of received packets is the expected.
        """

        received_packets = self.number_of_received_packets(self.test_config.tcp_dst_port)
        print 'received packets: %d - expected: %d' % (received_packets, expected)
        self.verify(received_packets == expected,
                    'Not all frames have been forwarded')

    def verify_tcp_valid_checksum(self, expected):
        """
        Verifies if the number of packets with a valid TCP checksum is the expected.
        """

        tcp_valid_checksum = self.number_of_tcp_valid_checksum(self.test_config.tcp_dst_port)
        print 'tcp valid: %d - expected: %d' % (tcp_valid_checksum, expected)
        self.verify(tcp_valid_checksum == expected,
                    'Not all TCP packets have valid checksum')

    def verify_all_with_maxflows(self):
        """
        Runs a common verification among different test cases were the number
        of sent packets is bigger than the maxflows value which means that
        only maxflows packets are expected to be received and valid.
        """

        self.verify_sent_packets(self.test_config.number_of_frames *
                                 self.test_config.frags_per_frame)
        self.verify_received_packets(self.test_config.maxflows)
        self.verify_tcp_valid_checksum(self.test_config.maxflows)

    def verify_all(self):
        """
        Runs a common verification among different test cases were the number
        of sent packets is equal to the maxflows value. It expects to receive
        the same number of frames that were sent.
        """

        self.verify_sent_packets(self.test_config.number_of_frames *
                                 self.test_config.frags_per_frame)
        self.verify_received_packets(self.test_config.number_of_frames)
        self.verify_tcp_valid_checksum(self.test_config.number_of_frames)

    def set_up_all(self):
        """
        Run at the start of each test suite.


        Builds the sample app and set the shell prompt to a known and value.
        """

        self.tester.send_expect('export PS1="# "', '#')
        self.compile_example_app()

    def test_send_1K_frames_split_in_4_and_1K_maxflows(self):
        """
        Sends 1K frames split in 4 fragments each using
        1K maxflows.
        """

        self.test_config = IpReassemblyTestConfig(self)

        self.execute_example_app()
        self.send_n_siff_packets()

        self.verify_all()

    def test_send_2K_frames_split_in_4_and_1K_maxflows(self):
        """
        Sends 2K frames while the maxflow value is only 1K.
        Only 1K frames are expected to be forwarded.
        """

        self.test_config = IpReassemblyTestConfig(self, number_of_frames=2048)

        self.execute_example_app()
        self.send_n_siff_packets()

        self.verify_all_with_maxflows()

    def test_send_4K_frames_split_in_7_and_4K_maxflows(self):
        """
        Sends 4K frames split into 7 fragments each.
        """

        self.test_config = IpReassemblyTestConfig(self,
                                                  number_of_frames=4096,
                                                  frags_per_frame=7,
                                                  payload_size=230,
                                                  maxflows=4096,
                                                  flowttl='40s')

        try:
            self.set_max_num_of_fragments(7)
            self.compile_example_app()
            self.execute_example_app()
            self.send_n_siff_packets()
            self.verify_all()
            self.dut.send_expect('^C', '# ')
            time.sleep(5)
            self.set_max_num_of_fragments(4)
            time.sleep(5)

        except Exception as e:
            self.dut.send_expect('^C', '# ')
            time.sleep(2)
            self.set_max_num_of_fragments()
            self.compile_example_app()
            raise e

    def test_packets_are_forwarded_after_ttl_timeout(self):
        """
        Sends +1K frames with 1K maxflwos - expects only
        1K frames to be forwarded. Then it waits until flowttl timeout and
        sends 1K frames. 1K frames must be forwarded back.
        """

        self.test_config = IpReassemblyTestConfig(self,
                                                  number_of_frames=1100,
                                                  flowttl='3s')

        self.execute_example_app()

        self.send_n_siff_packets()
        self.verify_all_with_maxflows()

        time.sleep(5)

        self.test_config.number_of_frames = 1024
        self.send_n_siff_packets()
        self.verify_all()

    def test_only_maxflows_packets_are_forwarded(self):
        """
        Using a maxflow of 1023 sends 1K frames expecting 1023 back.
        Then sends 1023 frames, expecting 1023 back again. And after the flowttl
        timeout sends 1K frames expecting all of them to be forwarded back.
        """

        self.test_config = IpReassemblyTestConfig(self,
                                                  maxflows=1023,
                                                  flowttl='5s')

        self.execute_example_app()

        self.send_n_siff_packets()
        self.verify_all_with_maxflows()

        self.test_config.number_of_frames = 1023
        self.send_n_siff_packets()
        self.verify_all()

        time.sleep(5)

        self.test_config.number_of_frames = 1024
        self.send_n_siff_packets()
        self.verify_all_with_maxflows()

    def test_send_more_fragments_than_supported(self):
        """
        Sends 1 frame split in 5 fragments. Since the max number of
        fragments is set to 4 by default, the packet can't be forwarded back.
        """

        self.test_config = IpReassemblyTestConfig(self,
                                                  number_of_frames=1,
                                                  frags_per_frame=5,
                                                  payload_size=180)
        self.execute_example_app()

        self.send_n_siff_packets()

        self.verify_sent_packets(self.test_config.number_of_frames *
                                 self.test_config.frags_per_frame)
        self.verify_received_packets(0)
        self.verify_tcp_valid_checksum(0)

    def test_send_delayed_fragment_packet_is_forwarded(self):
        """
        Creates 1 frame split in 4. Sends 3 fragments first, waits
        for the flowttl to timeout and then sends the 4th. The packet can't
        be forwarded back.
        """

        self.test_config = IpReassemblyTestConfig(self,
                                                  number_of_frames=1,
                                                  flowttl='3s')

        self.execute_example_app()
        self.tcpdump_start_sniffing()

        fragments = self.create_fragments()
        self.write_shuffled_pcap(fragments[:3])
        self.tester.session.copy_file_to(self.test_config.pcap_file)
        self.scapy_send_packets()
        os.remove(self.test_config.pcap_file)

        time.sleep(3)

        self.write_shuffled_pcap(fragments[3:])
        self.tester.session.copy_file_to(self.test_config.pcap_file)
        self.scapy_send_packets()
        os.remove(self.test_config.pcap_file)

        self.tcpdump_stop_sniff()

        self.verify_sent_packets(self.test_config.number_of_frames *
                                 self.test_config.frags_per_frame)
        self.verify_received_packets(0)
        self.verify_tcp_valid_checksum(0)

    def test_send_jumbo_frames(self):
        """
        Sends 1K jumbo frames using the right configuration.
        Expects all the frames to be forwarded back.
        """

        mtu = 9000
        self.test_config = IpReassemblyTestConfig(self,
                                                  payload_size=mtu - 100,
                                                  fragment_size=2500)
        try:
            self.set_tester_iface_mtu(self.test_config.tester_iface, mtu)
            self.execute_example_app()
            self.send_n_siff_packets()
            self.verify_all()
        except Exception as e:
            self.set_tester_iface_mtu(self.test_config.tester_iface)
            raise e

    def test_send_jumbo_frames_with_wrong_arguments(self):
        """
        Sends 1K jumbo frames without enabling the jumbo frames
        within the sample app. Expects zero frames to be forwarded back.
        """

        mtu = 9000
        self.test_config = IpReassemblyTestConfig(self,
                                                  payload_size=mtu - 100,
                                                  fragment_size=2500)
        try:
            self.set_tester_iface_mtu(self.test_config.tester_iface, mtu)
            self.set_max_num_of_fragments(4)
            self.compile_example_app()
            self.execute_example_app()
            self.send_n_siff_packets()

            self.verify_sent_packets(self.test_config.number_of_frames *
                                     self.test_config.frags_per_frame)
            self.verify_all()
        except Exception as e:
            self.set_tester_iface_mtu(self.test_config.tester_iface)
            raise e

    def tear_down(self):
        """
        Run after each test case.
        """

        self.dut.send_expect('^C', '# ')

    def tear_down_all(self):
        """
        Run after each test suite.
        """

        self.dut.kill_all()
