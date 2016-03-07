# <COPYRIGHT_TAG>

"""
DPDK Test suite.

Tests for vmdq.

"""

import dts
import re
from etgen import IxiaPacketGenerator
from test_case import TestCase
from time import sleep


class TestVmdq(TestCase, IxiaPacketGenerator):
    dut_ports = []
    ip_dot1q_header_size = 22
    default_framesize = 64
    default_payload = default_framesize - ip_dot1q_header_size
    current_frame_size = 0
    destmac_port0 = "52:54:00:12:00:00"
    destmac_port1 = "52:54:00:12:01:00"
    da_repeat = 1
    vlan_repeat = 1 
    queues = 8

    def set_up_all(self):
        """
        Run at the start of each test suite.
        """

        self.tester.extend_external_packet_generator(TestVmdq, self)
        
        self.dut.send_expect("sed -i 's/CONFIG_RTE_MAX_QUEUES_PER_PORT=256/CONFIG_RTE_MAX_QUEUES_PER_PORT=1024/' ./config/common_base", "# ", 5)
        
        self.dut.build_install_dpdk(self.target)
        # Update the max queue per port for Fortville.
        self.dut.send_expect("sed -i 's/define MAX_QUEUES 128/define MAX_QUEUES 1024/' ./examples/vmdq/main.c", "#", 5)
        
        self.dut_ports = self.dut.get_ports(self.nic)
        print self.dut_ports
        self.verify(len(self.dut_ports) >= 2, "Insufficient ports")

        self.core_configs = []
        self.core_configs.append({'cores': '1S/1C/1T', 'mpps': {}})
        self.core_configs.append({'cores': '1S/2C/1T', 'mpps': {}})
        self.core_configs.append({'cores': '1S/2C/2T', 'mpps': {}})
        self.core_configs.append({'cores': '1S/4C/1T', 'mpps': {}})

        self.ports_socket = self.dut.get_numa_id(self.dut_ports[0])
        out = self.dut.send_expect("make -C examples/vmdq", "#", 10)
        self.verify("Error" not in out, "Compilation error")


    def validateApproxEqual(self, lines):
        """
        Check that all the rx queue stats are within a 30% range.
        """

        minimum = 1000000
        maximun = 0

        # Need to use Python re package because dts.regexp only handles 1 group,
        # we need 4.
        scanner = re.compile(
            "^Pool [0-9]+: ([0-9]+) ([0-9]+) ([0-9]+) ([0-9]+)$")
        for l in lines:
            m = scanner.search(l)
            if m is None:
                # Line at the end, "Finished handling signal", ignore
                pass
            else:
                for stat in m.groups():
                    if stat < minimum:
                        minimum = stat
                    if stat > maximun:
                        maximun = stat
        self.verify(maximun - minimum <= minimum *
                    0.3, "Too wide variation in queue stats")

    def Npools_128queues(self, npools):
        """
        MAX queues is 128
        queues/pools = 128/npools
        """

        self.current_frame_size = self.default_framesize

        self.dut_ports = self.dut.get_ports(self.nic)

        core_list = self.dut.get_core_list("1S/4C/1T", socket=self.ports_socket)
        core_mask = dts.create_mask(core_list)

        port_mask = dts.create_mask([self.dut_ports[0], self.dut_ports[1]])
        # Run the application
        out = self.dut.send_expect("./examples/vmdq/build/vmdq_app -n 4 -c %s -- -p %s --nb-pools %s&" %
                                   (core_mask, port_mask, str(npools)), "reading queues", 120)

        # Transmit traffic
        tx_port = self.tester.get_local_port(self.dut_ports[0])
        rx_port = self.tester.get_local_port(self.dut_ports[1])
        tx_mac = self.tester.get_mac(tx_port)
        
        self.vlan_repeat = npools
        self.da_repeat = npools
        tgen_input = []
        for p in range(8):
            self.tester.scapy_append('dmac="%s"' % self.destmac_port0)
            self.tester.scapy_append('smac="%s"' % tx_mac)
            self.tester.scapy_append(
                'flows = [Ether(src=smac, dst=dmac)/Dot1Q(vlan=0,prio=%d)]'%p)
            self.tester.scapy_append('wrpcap("test%d.pcap", flows)' %p)
            self.tester.scapy_execute()
            tgen_input.append((tx_port, rx_port, "test%d.pcap" %p))

        loss, _, _ = self.tester.traffic_generator_loss(tgen_input, 10)
        print "loss is %s !" % loss

        # Verify the accurate
        self.verify(loss < 0.001, "Excessive packet loss")
        self.validateApproxEqual(out.split("\r\n"))

    def set_up(self):
        """
        Run before each test case.
        """
        self.dut.kill_all()

    def test_perf_vmdq_64pools_queues(self):
        """
        This function call " Npools_128queues" with differen number
        of pools. Details see below. if not sure, set it as 8 pools.
        """
        if self.nic in ("niantic", "springfountain"):
            self.Npools_128queues(64)
        elif self.nic in ("fortville_spirit", "fortville_spirit_single"):
            self.Npools_128queues(63)
        elif self.nic in ("fortville_eagle"):
            self.Npools_128queues(34)
        else: 
            self.Npools_128queues(8)

    def test_perf_vmdq_performance(self):
        """
        Try  different configuration and different packe size
        """

        self.tester.get_interface(
            self.tester.get_local_port(self.dut_ports[0]))

        frame_sizes = [64, 128, 256, 512, 1024, 1280, 1518]
        for config in self.core_configs:

            print dts.BLUE(config["cores"])
            self.dut.kill_all()

            core_config = config['cores']
            core_list = self.dut.get_core_list(core_config,socket=self.ports_socket)
            core_mask = dts.create_mask(core_list)
            portmask = dts.create_mask(self.dut.get_ports())
            if self.nic in ("niantic", "springfountain"):
                self.queues = 64
                self.dut.send_expect(
                    "examples/vmdq/build/vmdq_app -n %d -c %s -- -p %s --nb-pools 64&" %
                    (self.dut.get_memory_channels(), core_mask, portmask), "reading queues", 30)
            elif self.nic in ("fortville_spirit", "fortville_spirit_single"):
                self.queues = 63
                self.dut.send_expect(
                    "examples/vmdq/build/vmdq_app -n %d -c %s -- -p %s --nb-pools 63&" %
                    (self.dut.get_memory_channels(), core_mask, portmask), "reading queues", 30)
            elif self.nic in ("fortville_eagle"):
                self.queues = 34
                self.dut.send_expect(
                    "examples/vmdq/build/vmdq_app -n %d -c %s -- -p %s --nb-pools 34&" %
                    (self.dut.get_memory_channels(), core_mask, portmask), "reading queues", 30)
            else:
                self.queues = 8
                self.dut.send_expect(
                    "examples/vmdq/build/vmdq_app -n %d -c %s -- -p %s --nb-pools 8&" %
                    (self.dut.get_memory_channels(), core_mask, portmask), "reading queues", 30)

            tx_port = self.tester.get_local_port(self.dut_ports[0])
            rx_port = self.tester.get_local_port(self.dut_ports[1])

            print dts.GREEN("Waiting for application to initialize")
            sleep(5)

            for frame_size in frame_sizes:

                TestVmdq.current_frame_size = frame_size

                print dts.BLUE(str(frame_size))

                self.tester.scapy_append('dstmac="%s"' % self.destmac_port0)
                tx_mac = self.tester.get_mac(tx_port)
                self.tester.scapy_append('srcmac="%s"' % tx_mac)
                self.tester.scapy_append(
                        'flows = [Ether(src=srcmac,dst=dstmac)/Dot1Q(vlan=0)/("X"*%d)]' %
                        (frame_size - TestVmdq.ip_dot1q_header_size))
                self.tester.scapy_append('wrpcap("test1.pcap", flows)')
                self.tester.scapy_execute()

                self.tester.scapy_append('dstmac="%s"' % self.destmac_port1)
                tx_mac = self.tester.get_mac(rx_port)
                self.tester.scapy_append('srcmac="%s"' % tx_mac)
                self.tester.scapy_append(
                        'flows = [Ether(src=srcmac,dst=dstmac)/Dot1Q(vlan=0)/("X"*%d)]' %
                        (frame_size - TestVmdq.ip_dot1q_header_size))
                self.tester.scapy_append('wrpcap("test2.pcap", flows)')
                self.tester.scapy_execute()
                   
                self.vlan_repeat = self.queues
                self.da_repeat = self.queues

                tgen_input = []
                tgen_input.append((tx_port, rx_port, "test1.pcap"))
                tgen_input.append((rx_port, tx_port, "test2.pcap"))
                _, pps = self.tester.traffic_generator_throughput(tgen_input)
                config['mpps'][frame_size] = pps/1000000.0

        for n in range(len(self.core_configs)):
            for size in frame_sizes:
                self.verify(
                    self.core_configs[n]['mpps'][size] is not 0, "No traffic detected")

        # Print results
        dts.results_table_add_header(
            ['Frame size'] + [n['cores'] for n in self.core_configs])

        for size in frame_sizes:
            dts.results_table_add_row(
                [size] + [n['mpps'][size] for n in self.core_configs])

        dts.results_table_print()

    # Override etgen.dot1q function
    def dot1q(self, port, prio, id, vlan, type):
        """
        Change Ixia configuration
        """

        self.add_tcl_cmd("vlan config -mode vIncrement")
        self.add_tcl_cmd("vlan config -step 1")
        self.add_tcl_cmd("vlan config -repeat %d" % self.vlan_repeat)
        self.add_tcl_cmd("stream config -framesize %d" %
                         TestVmdq.current_frame_size)
        super(TestVmdq, self).dot1q(port, prio, id, vlan, type)

    def ether(self, port, src, dst, type):
        """
        Configure Ether protocal.
        """
        self.add_tcl_cmd("protocol config -ethernetType ethernetII")
        self.add_tcl_cmd('stream config -sa "%s"' % self.macToTclFormat(src))
        self.add_tcl_cmd('stream config -da "%s"' % self.macToTclFormat(dst))
        self.add_tcl_cmd('stream config -daRepeatCounter increment')
        self.add_tcl_cmd('stream config -daStep 1')
        self.add_tcl_cmd('stream config -numDA %d' % self.da_repeat)


