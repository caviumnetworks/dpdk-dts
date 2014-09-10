# <COPYRIGHT_TAG>

"""
DPDK Test suite.

Test userland 10Gb PMD

"""

from scapy.layers.inet import Ether, IP, TCP
from scapy.utils import struct, socket, PcapWriter
from settings import HEADER_SIZE
from test_case import TestCase
from time import sleep
import dcts

#
#
# Test class.
#


class TestIPPipeline(TestCase):

    #
    #
    # Utility methods and other non-test code.
    #
    payload_watermark = 'TestPF'

    frame_sizes = [64, 65, 128, 1024]
    """Sizes of the frames to be sent"""

    number_of_frames = [1, 3, 63, 64, 65, 127, 128]
    """Number of frames in the pcap file to be created"""

    incremental_ip_address = [True, False]
    """True if the IP address is incremented in the frames"""

    inter = [0, 0.7]
    """Interval between frames sent in seconds"""

    dummy_pcap = 'dummy.pcap'

    def increment_ip_addr(self, ip_address, increment):

        ip2int = lambda ipstr: struct.unpack('!I', socket.inet_aton(ipstr))[0]
        x = ip2int(ip_address)
        int2ip = lambda n: socket.inet_ntoa(struct.pack('!I', n))
        return int2ip(x + increment)

    def create_tcp_ipv4_frame(
        self, ip_id, src_ip_addr, dst_ip_addr, frame_size,
        src_mac_addr='00:00:0A:00:0B:00',
            dst_mac_addr='00:00:0A:00:0A:00'):

        payload_size = frame_size - HEADER_SIZE['eth'] - HEADER_SIZE['ip'] -\
            HEADER_SIZE['tcp'] - \
            len(TestIPPipeline.payload_watermark)

        if payload_size < 0:
            payload_size = 0

        frame = Ether() / IP() / TCP(flags="") / (TestIPPipeline.payload_watermark +
                                                  "X" * payload_size)
        frame[Ether].src = src_mac_addr
        frame[Ether].dst = dst_mac_addr

        frame[IP].src = src_ip_addr
        frame[IP].dst = dst_ip_addr
        frame[IP].id = ip_id

        # TCP ports always 0
        frame[TCP].sport = 0
        frame[TCP].dport = 0

        return frame

    def create_pcap_file_from_frames(self, file_name, frames):

        writer = PcapWriter(file_name, append=False)

        for frame in frames:
            writer.write(frame)

        writer.close()

    def create_pcap_file(self, file_name, frame_size, number_of_frames,
                         incremental_ip_address,
                         src_ip="0.0.0.0",
                         dst_ip="0.0.0.0"):

        current_frame = 0
        writer = PcapWriter(file_name, append=False)

        while current_frame < number_of_frames:
            ip_id = 0  # current_frame % 0x10000

            frame = self.create_tcp_ipv4_frame(ip_id, src_ip, dst_ip,
                                               frame_size)
            writer.write(frame)

            if incremental_ip_address:
                dst_ip = self.increment_ip_addr(dst_ip, 1)

            current_frame += 1

        writer.close()

    def enable_pmd_pcap(self, enable=True):

        if enable:
            self.dut.send_expect(
                "sed -i 's/CONFIG_RTE_LIBRTE_PMD_PCAP=n$/CONFIG_RTE_LIBRTE_PMD_PCAP=y/' config/defconfig_%s" % self.target, "# ")
        else:
            self.dut.send_expect(
                "sed -i 's/CONFIG_RTE_LIBRTE_PMD_PCAP=y$/CONFIG_RTE_LIBRTE_PMD_PCAP=n/' config/defconfig_%s" % self.target, "# ")

        self.dut.build_install_dpdk(self.target)
        out = self.dut.build_dpdk_apps("./examples/ip_pipeline")
        self.verify("Error" not in out, "Compilation error")
        self.dut.bind_interfaces_linux()

    def start_ip_pipeline(self, ports):
        command_line = "./examples/ip_pipeline/build/ip_pipeline -c %s -n %d -- -p %s" % \
            (self.coremask,
             self.dut.get_memory_channels(),
             ports)

        out = self.dut.send_expect(command_line, 'pipeline>', 60)
        sleep(5)    # 'Initialization completed' is not the last output, some
        # seconds are still needed for init.

        self.verify("Aborted" not in out, "Error starting ip_pipeline")
        self.verify("PANIC" not in out, "Error starting ip_pipeline")
        self.verify("ERROR" not in out, "Error starting ip_pipeline")

    def start_ip_pipeline_pcap(self, pcap0_file, pcap1_file):

        pcap_config = "'eth_pcap0;rx_pcap=/root/%s;tx_pcap=/tmp/port0out.pcap,eth_pcap1;rx_pcap=/root/%s;tx_pcap=/tmp/port1out.pcap'" % (
            pcap0_file,
            pcap1_file)

        command_line = "./examples/ip_pipeline/build/ip_pipeline -c %s -n %d --use-device %s -- -p 0x3" % \
            (self.coremask,
             self.dut.get_memory_channels(),
             pcap_config)

        out = self.dut.send_expect(command_line, 'pipeline>', 60)
        sleep(5)    # 'Initialization completed' is not the last output, some
        # seconds are still needed for init.

        self.verify("Aborted" not in out, "Error starting ip_pipeline")
        self.verify("PANIC" not in out, "Error starting ip_pipeline")

    def quit_ip_pipeline(self):
        self.dut.send_expect("quit", "# ", 5)

    def tcpdump_start_sniffing(self, ifaces=[]):
        """
        Starts tcpdump in the background to sniff the tester interface where
        the packets are transmitted to and from the self.dut.
        All the captured packets are going to be stored in a file for a
        post-analysis.
        """

        for iface in ifaces:
            command = (
                'tcpdump -w tcpdump_{0}.pcap -i {0} 2>tcpdump_{0}.out &').format(iface)
            self.tester.send_expect(
                'rm -f tcpdump_{0}.pcap', '#').format(iface)
            self.tester.send_expect(command, '#')

    def tcpdump_stop_sniff(self):
        """
        Stops the tcpdump process running in the background.
        """

        self.tester.send_expect('killall tcpdump', '#')
        # For the [pid]+ Done tcpdump... message after killing the process
        sleep(1)
        self.tester.send_expect('echo "Cleaning buffer"', '#')
        sleep(1)

    def tcpdump_command(self, command, machine):
        """
        Sends a tcpdump related command and returns an integer from the output
        """

        if machine == 'dut':
            result = self.dut.send_expect(command, '#', alt_session=True)
        else:
            result = self.tester.send_expect(command, '#', alt_session=True)

        return int(result.strip())

    def number_of_packets(self, file_name, machine='tester'):
        """
        By reading the file generated by tcpdump it counts how many packets were
        forwarded by the sample app and received in the self.tester. The sample app
        will add a known MAC address for the test to look for.
        """

        command = ('tcpdump -A -nn -e -v -r %s 2>/dev/null | grep -c "%s"' %
                   (file_name, TestIPPipeline.payload_watermark))
        return int(self.tcpdump_command(command, machine))

    def send_and_sniff_pcap_file(self, pcap_file, frames_number, from_port,
                                 to_port, inter=0):
        """
        Sent frames_number frames from the pcap_file with inter seconds of
        interval.
        Returns the number of received frames.
        """

        tx_port = self.tester.get_local_port(self.dut_ports[from_port])
        rx_port = self.tester.get_local_port(self.dut_ports[to_port])

        tx_interface = self.tester.get_interface(tx_port)
        rx_interface = self.tester.get_interface(rx_port)

        self.tcpdump_start_sniffing([tx_interface, rx_interface])

        self.dut.send_expect('link 0 up', 'pipeline>')
        self.dut.send_expect('link 1 up', 'pipeline>')

        timeout = frames_number * inter + 2
        inter = ", inter=%d" % inter

        # Prepare the frames to be sent
        self.tester.scapy_foreground()
        self.tester.scapy_append('p = rdpcap("%s")' % (pcap_file))
        self.tester.scapy_append(
            'sendp(p[:%s], iface="%s" %s)' % (frames_number,
                                              tx_interface,
                                              inter))

        # Execute scapy to sniff sniffing and send the frames
        self.tester.scapy_execute(timeout)

        self.tcpdump_stop_sniff()

        self.dut.send_expect('link 0 down', 'pipeline>')
        self.dut.send_expect('link 1 down', 'pipeline>')

        rx_stats = self.number_of_packets('tcpdump_%s.pcap' % rx_interface)
        tx_stats = self.number_of_packets('tcpdump_%s.pcap' % tx_interface)

        # Do not count the sent frames in the tx_interface
        tx_stats = tx_stats - frames_number

        return {'rx': rx_stats, 'tx': tx_stats}

    def check_results(self, stats, expected):
        """
        This function check that the Rx and Tx stats matches the expected.
        expected = [Rx, Tx]
        """

        for port in ['rx', 'tx']:
            self.verify(stats[port] == expected[port],
                        'Frames expected (%s) and received (%s) mismatch on %s port' % (
                            expected[
                                port],
                            stats[
                                port],
                            port))

    def pipeline_command(self, command):
        out = self.dut.send_expect(command, 'pipeline>')
        self.verify("Illegal" not in out, "Pipeline command error 1: '%s'" % command)
        self.verify("Bad" not in out, "Pipeline command error 2: '%s'" % command)
        return out

    def pipeline_add_flow(self, port, src_ip, dst_ip, src_port, dst_port,
                          protocol=6):
        command = 'flow add %s %s %d %d %d %d' % (src_ip, dst_ip, src_port,
                                                  dst_port, protocol, port)
        out = self.pipeline_command(command)
        self.verify("Adding flow" in out, "Add flow error")

    def pipeline_del_flow(self, src_ip, dst_ip, src_port, dst_port,
                          protocol=6):
        command = 'flow del %s %s %d %d %d' % (src_ip, dst_ip, src_port,
                                               dst_port, protocol)
        out = self.pipeline_command(command)
        self.verify("Deleting flow" in out, "Del flow error")

    def pipeline_add_route(self, port, src_ip, netmask, gw_ip):
        command = 'route add %s %d %d %s' % (src_ip, netmask, port, gw_ip)
        out = self.pipeline_command(command)
        self.verify("Adding route" in out, "Add route error")

    def pipeline_del_route(self, src_ip, netmask):
        command = 'route del %s %d' % (src_ip, netmask)
        out = self.pipeline_command(command)
        self.verify("Deleting route" in out, "Del route error")

    def pipeline_traffic_burst(self):
        self.dut.send_expect('link 0 up', 'pipeline>')
        self.dut.send_expect('link 1 up', 'pipeline>')
        sleep(0.1)
        self.dut.send_expect('link 0 down', 'pipeline>')
        self.dut.send_expect('link 1 down', 'pipeline>')

    #
    #
    #
    # Test cases.
    #
    def set_up_all(self):
        """
        Run at the start of each test suite.

        PMD prerequisites.
        """

        # Check for port availability
        self.needed_ports = {"niantic": 2}
        self.dut_ports = self.dut.get_ports(self.nic)
        self.verify(len(self.dut_ports) >= self.needed_ports[self.nic],
                    "Insufficient ports for speed testing")

        # Enable the support for PCAP Driver
        self.enable_pmd_pcap()
        out = self.dut.build_dpdk_apps("./examples/ip_pipeline")
        self.verify("Error" not in out, "Compilation error")

        self.ports_mask = dcts.create_mask(
            [self.dut_ports[0], self.dut_ports[1]])
        self.coremask = "0x3e"  # IP Pipeline app requires FIVE cores

        self.dut.setup_memory(4096)

    def set_up(self):
        """
        Run before each test case.
        """
        pass

    def test_incremental_ip(self):
        """
        Testing that frames with incremental IP addresses pass through the
        pipeline regardless the frames_number and the speed.
        """
        pcap_file = 'ip_pipeline.pcap'
        frame_size = 64

        self.start_ip_pipeline(ports=self.ports_mask)
        self.dut.send_expect(
            'run examples/ip_pipeline/ip_pipeline.sh', 'pipeline>', 10)

        # Create a PCAP file containing the maximum frames_number of frames needed
        # with fixed size and incremental IP
        self.create_pcap_file(pcap_file, frame_size,
                              max(TestIPPipeline.number_of_frames), True)
        self.tester.session.copy_file_to(pcap_file)

        for frames_number in TestIPPipeline.number_of_frames:
            for inter in TestIPPipeline.inter:
                print dcts.BLUE(
                    "\tNumber of frames %d, interval %.1f" % (frames_number,
                                                              inter))
                stats = self.send_and_sniff_pcap_file(pcap_file, frames_number,
                                                      1, 0, inter)

                expected = {'tx': 0, 'rx': frames_number}
                self.check_results(stats, expected)

                stats = self.send_and_sniff_pcap_file(pcap_file, frames_number,
                                                      0, 1, inter)

                expected = {'tx': frames_number, 'rx': 0}
                self.check_results(stats, expected)

    def test_frame_sizes(self):
        """
        Testing that frames with different sizes pass through the pipeline.
        """
        pcap_file = 'ip_pipeline.pcap'
        frames_number = 100
        inter = 0.5

        self.start_ip_pipeline(ports=self.ports_mask)
        self.dut.send_expect(
            'run examples/ip_pipeline/ip_pipeline.sh', 'pipeline>', 10)

        for frame_size in TestIPPipeline.frame_sizes:

            # Create a PCAP file containing the fixed number of frames above
            # with variable size and incremental IP
            self.create_pcap_file(pcap_file, frame_size, 100, True)
            self.tester.session.copy_file_to(pcap_file)

            print dcts.BLUE("\tFrame size %d, interval %.1f" % (frame_size,
                                                                inter))

            stats = self.send_and_sniff_pcap_file(pcap_file, frames_number,
                                                  1, 0, inter)

            expected = {'tx': 0, 'rx': frames_number}
            self.check_results(stats, expected)

            stats = self.send_and_sniff_pcap_file(pcap_file, frames_number,
                                                  0, 1, inter)

            expected = {'tx': frames_number, 'rx': 0}
            self.check_results(stats, expected)

    def test_flow_management(self):
        """
        Add several flows and check only frames with matching IPs passes
        """
        pcap_file = 'ip_pipeline.pcap'
        frame_size = 64

        default_setup = ['arp add 0 0.0.0.1 0a:0b:0c:0d:0e:0f',
                         'arp add 1 0.128.0.1 1a:1b:1c:1d:1e:1f',
                         'route add 0.0.0.0 9 0 0.0.0.1',
                         'route add 0.128.0.0 9 1 0.128.0.1']

        ip_addrs = [
            '0.0.0.0', '0.0.0.1', '0.0.0.127', '0.0.0.128', '0.0.0.255',
            '0.0.1.0', '0.0.127.0', '0.0.128.0', '0.0.129.0', '0.0.255.0',
            '0.127.0.0', '0.127.1.0', '0.127.127.0', '0.127.255.0',
            '0.127.255.255']

        frames = []

        for addr in ip_addrs:
            frames.append(self.create_tcp_ipv4_frame(0, '0.0.0.0', addr,
                                                     frame_size))

        self.create_pcap_file_from_frames(pcap_file, frames)
        self.tester.session.copy_file_to(pcap_file)

        # Start ip_pipeline app and setup defaults
        self.start_ip_pipeline(ports=self.ports_mask)
        for command in default_setup:
            self.pipeline_command(command)

        # Check that no traffic pass though
        stats = self.send_and_sniff_pcap_file(pcap_file, len(frames),
                                              1, 0, 0.2)
        expected = {'tx': 0, 'rx': 0}
        self.check_results(stats, expected)

        # Add the flows
        flows_added = 0
        for addrs in ip_addrs:
            self.pipeline_add_flow(1, '0.0.0.0', addrs, 0, 0)
            flows_added += 1

            # Check that traffic matching flows pass though
            stats = self.send_and_sniff_pcap_file(pcap_file, len(frames),
                                                  1, 0, 0.2)
            expected = {'tx': 0, 'rx': flows_added}
            self.check_results(stats, expected)

        # Remove flows
        for addrs in ip_addrs:
            self.pipeline_del_flow('0.0.0.0', addrs, 0, 0)
            flows_added -= 1

            # Check that traffic matching flows pass though
            stats = self.send_and_sniff_pcap_file(pcap_file, len(frames),
                                                  1, 0, 0.2)
            expected = {'tx': 0, 'rx': flows_added}
            self.check_results(stats, expected)

        out = self.dut.send_expect('flow print', 'pipeline>')
        self.verify("=> Port =" not in out, "Flow found after deletion")

        # Check that again no traffic pass though
        stats = self.send_and_sniff_pcap_file(pcap_file, len(frames),
                                              1, 0, 0.2)
        expected = {'tx': 0, 'rx': 0}
        self.check_results(stats, expected)

        self.quit_ip_pipeline()

    def test_route_management(self):
        """
        Add several flows and check only frames with matching IPs passes
        """
        pcap_file = 'ip_pipeline.pcap'
        frame_size = 64

        default_setup = ['arp add 0 0.0.0.1 0a:0b:0c:0d:0e:0f',
                         'arp add 1 0.128.0.1 1a:1b:1c:1d:1e:1f',
                         'flow add all']

        ip_addrs = [
            '0.0.0.0', '0.0.0.1', '0.0.0.127', '0.0.0.128', '0.0.0.255',
            '0.0.1.0', '0.0.127.0', '0.0.128.0', '0.0.129.0', '0.0.255.0',
            '0.127.0.0', '0.127.1.0', '0.127.127.0', '0.127.255.0',
            '0.127.255.255']

        frames = []

        for addr in ip_addrs:
            frames.append(self.create_tcp_ipv4_frame(0, '0.0.0.0', addr,
                                                     frame_size))

        self.create_pcap_file_from_frames(pcap_file, frames)
        self.tester.session.copy_file_to(pcap_file)

        # Start ip_pipeline app and setup defaults
        self.start_ip_pipeline(ports=self.ports_mask)
        for command in default_setup:
            self.pipeline_command(command)

        # Check that no traffic pass though
        stats = self.send_and_sniff_pcap_file(pcap_file, len(frames),
                                              1, 0, 0.2)
        expected = {'tx': 0, 'rx': 0}
        self.check_results(stats, expected)

        # Add the routes
        routes_added = 0
        for addr in ip_addrs:
            self.pipeline_add_route(0, addr, 32, '0.0.0.1')
            routes_added += 1

            # Check that traffic matching routes pass though
            stats = self.send_and_sniff_pcap_file(pcap_file, len(frames),
                                                  1, 0, 0.2)

            expected = {'tx': 0, 'rx': routes_added}
            self.check_results(stats, expected)

        # Remove routes
        for addr in ip_addrs:
            self.pipeline_del_route(addr, 32)
            routes_added -= 1

            # Check that traffic matching flows pass though
            stats = self.send_and_sniff_pcap_file(pcap_file, len(frames),
                                                  1, 0, 0.2)
            expected = {'tx': 0, 'rx': routes_added}
            self.check_results(stats, expected)

        out = self.dut.send_expect('route print', 'pipeline>')
        self.verify("Destination = " not in out, "Route found after deletion")

        # Check that again no traffic pass though
        stats = self.send_and_sniff_pcap_file(pcap_file, len(frames),
                                              1, 0, 0.2)
        expected = {'tx': 0, 'rx': 0}
        self.check_results(stats, expected)

        self.quit_ip_pipeline()

    def tear_down(self):
        """
        Run after each test case.
        """
        self.quit_ip_pipeline()

    def tear_down_all(self):
        """
        Run after each test suite.
        """
        # Disable the support for PCAP Driver
        # self.enable_pmd_pcap(False)
        out = self.dut.build_dpdk_apps("./examples/ip_pipeline")
        self.verify("Error" not in out, "Compilation error")
