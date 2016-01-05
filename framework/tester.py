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

"""
Interface for bulk traffic generators.
"""

import re
from time import sleep
from settings import NICS
from crb import Crb
from net_device import NetDevice
from etgen import IxiaPacketGenerator, SoftwarePacketGenerator
from settings import IXIA
import random


class Tester(Crb):

    """
    Start the DPDK traffic generator on the machine `target`.
    A config file and pcap file must have previously been copied
    to this machine.
    """
    PORT_INFO_CACHE_KEY = 'tester_port_info'
    CORE_LIST_CACHE_KEY = 'tester_core_list'
    NUMBER_CORES_CACHE_KEY = 'tester_number_cores'
    PCI_DEV_CACHE_KEY = 'tester_pci_dev_info'

    def __init__(self, crb, serializer):
        self.NAME = 'tester'
        super(Tester, self).__init__(crb, serializer, self.NAME)

        self.bgProcIsRunning = False
        self.dut = None
        self.inBg = 0
        self.scapyCmds = []
        self.bgCmds = []
        self.bgItf = ''

    def init_ext_gen(self):
        """
        Initialize tester packet generator object.
        """
        if self.it_uses_external_generator():
            self.ixia_packet_gen = IxiaPacketGenerator(self)
        self.packet_gen = SoftwarePacketGenerator(self)

    def get_ip_address(self):
        """
        Get ip address of tester CRB.
        """
        return self.crb['tester IP']

    def get_password(self):
        """
        Get tester login password of tester CRB.
        """
        return self.crb['tester pass']

    def has_external_traffic_generator(self):
        """
        Check whether performance test will base on IXIA equipment.
        """
        try:
            if self.crb[IXIA] is not None:
                return True
        except Exception as e:
            return False

        return False

    def get_external_traffic_generator(self):
        """
        Return IXIA object.
        """
        return self.crb[IXIA]

    def it_uses_external_generator(self):
        """
        Check whether IXIA generator is ready for performance test.
        """
        return self.want_perf_tests and self.has_external_traffic_generator()

    def tester_prerequisites(self):
        """
        Prerequest function should be called before execute any test case.
        Will call function to scan all lcore's information which on Tester.
        Then call pci scan function to collect nic device information.
        Then discovery the network topology and save it into cache file.
        At last setup DUT' environment for validation.
        """
        self.init_core_list()
        self.pci_devices_information()
        self.restore_interfaces()
        self.scan_ports()

    def get_local_port(self, remotePort):
        """
        Return tester local port connect to specified dut port.
        """
        return self.dut.ports_map[remotePort]

    def get_local_port_type(self, remotePort):
        """
        Return tester local port type connect to specified dut port.
        """
        return self.ports_info[self.get_local_port(remotePort)]['type']

    def get_local_index(self, pci):
        """
        Return tester local port index by pci id
        """
        index = -1
        for port in self.ports_info:
            index += 1
            if pci == port['pci']:
                return index
        return -1

    def get_pci(self, localPort):
        """
        Return tester local port pci id.
        """
        return self.ports_info[localPort]['pci']

    def get_interface(self, localPort):
        """
        Return tester local port interface name.
        """
        if 'intf' not in self.ports_info[localPort]:
            return 'N/A'

        return self.ports_info[localPort]['intf']

    def get_mac(self, localPort):
        """
        Return tester local port mac address.
        """
        if self.ports_info[localPort]['type'] == 'ixia':
            return "00:00:00:00:00:01"
        else:
            return self.ports_info[localPort]['mac']

    def get_port_status(self, port):
        """
        Return link status of ethernet.
        """
        eth = self.ports_info[port]['intf']
        out = self.send_expect("ethtool %s" % eth, "# ")

        status = re.search(r"Link detected:\s+(yes|no)", out)
        if not status:
            self.logger.error("ERROR: unexpected output")

        if status.group(1) == 'yes':
            return 'up'
        else:
            return 'down'

    def restore_interfaces(self):
        """
        Restore Linux interfaces.
        """
        if self.skip_setup:
            return

        self.send_expect("modprobe igb", "# ", 20)
        self.send_expect("modprobe ixgbe", "# ", 20)
        self.send_expect("modprobe e1000e", "# ", 20)
        self.send_expect("modprobe e1000", "# ", 20)

        try:
            for (pci_bus, pci_id) in self.pci_devices_info:
                addr_array = pci_bus.split(':')
                port = NetDevice(self, addr_array[0], addr_array[1])
                itf = port.get_interface_name()
                self.enable_ipv6(itf)
                self.send_expect("ifconfig %s up" % itf, "# ")

        except Exception as e:
            self.logger.error("   !!! Restore ITF: " + e.message)

        sleep(2)

    def set_promisc(self):
        try:
            for (pci_bus, pci_id) in self.pci_devices_info:
                addr_array = pci_bus.split(':')
                port = NetDevice(self, addr_array[0], addr_array[1])
                itf = port.get_interface_name()
                self.enable_promisc(itf)
        except Exception as e:
            pass


    def load_serializer_ports(self):
        cached_ports_info = self.serializer.load(self.PORT_INFO_CACHE_KEY)
        if cached_ports_info is None:
            return

        # now not save netdev object, will implemented later
        self.ports_info = cached_ports_info

    def save_serializer_ports(self):
        cached_ports_info = []
        for port in self.ports_info:
            port_info = {}
            for key in port.keys():
                if type(port[key]) is str:
                    port_info[key] = port[key]
                # need save netdev objects
            cached_ports_info.append(port_info)
        self.serializer.save(self.PORT_INFO_CACHE_KEY, cached_ports_info)

    def scan_ports(self):
        """
        Scan all ports on tester and save port's pci/mac/interface.
        """
        if self.read_cache:
            self.load_serializer_ports()
            self.scan_ports_cached()

        if not self.read_cache or self.ports_info is None:
            self.scan_ports_uncached()
            if self.it_uses_external_generator():
                self.ports_info.extend(self.ixia_packet_gen.get_ports())
            self.save_serializer_ports()

        for port_info in self.ports_info:
            self.logger.info(port_info)

    def scan_ports_cached(self):
        if self.ports_info is None:
            return

        for port_info in self.ports_info:
            if port_info['type'] == 'ixia':
                continue

            port = NetDevice(self, port_info['pci'], port_info['type'])
            intf = port.get_interface_name()

            self.logger.info("Tester cached: [000:%s %s] %s" % (
                             port_info['pci'], port_info['type'], intf))
            port_info['port'] = port

    def scan_ports_uncached(self):
        """
        Return tester port pci/mac/interface information.
        """
        self.ports_info = []

        for (pci_bus, pci_id) in self.pci_devices_info:
            # ignore unknown card types
            if pci_id not in NICS.values():
                self.logger.info("Tester: [000:%s %s] %s" % (pci_bus, pci_id,
                                                             "unknow_nic"))
                continue

            addr_array = pci_bus.split(':')
            bus_id = addr_array[0]
            devfun_id = addr_array[1]

            port = NetDevice(self, bus_id, devfun_id)
            intf = port.get_interface_name()

            if "No such file" in intf:
                self.logger.info("Tester: [000:%s %s] %s" % (pci_bus, pci_id,
                                                             "unknow_interface"))
                continue

            self.logger.info("Tester: [000:%s %s] %s" % (pci_bus, pci_id, intf))
            macaddr = port.get_mac_addr()

            ipv6 = port.get_ipv6_addr()

            # store the port info to port mapping
            self.ports_info.append({'port': port,
                                    'pci': pci_bus,
                                    'type': pci_id,
                                    'intf': intf,
                                    'mac': macaddr,
                                    'ipv6': ipv6})

    def send_ping6(self, localPort, ipv6, mac):
        """
        Send ping6 packet from local port with destination ipv6 address.
        """
        if self.ports_info[localPort]['type'] == 'ixia':
            return self.ixia_packet_gen.send_ping6(self.ports_info[localPort]['pci'], mac, ipv6)
        else:
            return self.send_expect("ping6 -w 5 -c 5 -A -I %s %s" % (self.ports_info[localPort]['intf'], ipv6), "# ", 10)

    def get_port_numa(self, port):
        """
        Return tester local port numa.
        """
        pci = self.ports_info[port]['pci']
        out = self.send_expect("cat /sys/bus/pci/devices/0000:%s/numa_node" % pci, "#")
        return int(out)

    def check_port_list(self, portList, ftype='normal'):
        """
        Check specified port is IXIA port or normal port.
        """
        dtype = None
        plist = set()
        for txPort, rxPort, _ in portList:
            plist.add(txPort)
            plist.add(rxPort)

        plist = list(plist)
        if len(plist) > 0:
            dtype = self.ports_info[plist[0]]['type']

        for port in plist[1:]:
            if dtype != self.ports_info[port]['type']:
                return False

        if ftype == 'ixia' and dtype != ftype:
            return False

        return True

    def scapy_append(self, cmd):
        """
        Append command into scapy command list.
        """
        self.scapyCmds.append(cmd)

    def scapy_execute(self, timeout=60):
        """
        Execute scapy command list.
        """
        self.kill_all()

        self.send_expect("scapy", ">>> ")
        if self.bgProcIsRunning:
            self.send_expect('subprocess.call("scapy -c sniff.py &", shell=True)', ">>> ")
            self.bgProcIsRunning = False
        sleep(2)

        for cmd in self.scapyCmds:
            self.send_expect(cmd, ">>> ", timeout)

        sleep(2)
        self.scapyCmds = []
        self.send_expect("exit()", "# ")

    def scapy_background(self):
        """
        Configure scapy running in backgroud mode which mainly purpose is
        that save RESULT into scapyResult.txt.
        """
        self.inBg = True

    def scapy_foreground(self):
        """
        Running backgroup scapy and convert to foregroup mode.
        """
        self.send_expect("echo -n '' >  scapyResult.txt", "# ")
        if self.inBg:
            self.scapyCmds.append('f = open(\'scapyResult.txt\',\'w\')')
            self.scapyCmds.append('f.write(RESULT)')
            self.scapyCmds.append('f.close()')
            self.scapyCmds.append('exit()')

            outContents = "import os\n" + \
                'conf.color_theme=NoTheme()\n' + 'RESULT=""\n' + \
                "\n".join(self.scapyCmds) + "\n"
            self.create_file(outContents, 'sniff.py')

            self.logger.info('SCAPY Receive setup:\n' + outContents)

            self.bgProcIsRunning = True
            self.scapyCmds = []
        self.inBg = False

    def scapy_get_result(self):
        """
        Return RESULT which saved in scapyResult.txt.
        """
        out = self.send_expect("cat scapyResult.txt", "# ")
        self.logger.info('SCAPY Result:\n' + out + '\n\n\n')

        return out.rpartition('[')[0]

    def traffic_generator_throughput(self, portList, rate_percent=100, delay=5):
        """
        Run throughput performance test on specified ports.
        """
        if self.check_port_list(portList, 'ixia'):
            return self.ixia_packet_gen.throughput(portList, rate_percent, delay)
        if not self.check_port_list(portList):
            self.logger.warning("exception by mixed port types")
            return None
        return self.packet_gen.throughput(portList, rate_percent)

    def run_rfc2544(self, portlist, delay=120):
        """
        zero_rate: dpdk will not lost packet in this line rate.
        loss_rate: dpdk will loss packet in this line rate.
        test_rate: the line rate we are going to test.
        """
        zero_rate = 0.0
        loss_rate = 100.0
        test_rate = 100.0

        while (loss_rate - zero_rate) > 0.002:
                self.logger.info("test rate: %f " % test_rate)
                if test_rate == 100:
                        lost, tx_num, rx_num = self.traffic_generator_loss(portlist, test_rate, delay)
                else:
                        lost, _, _ = self.traffic_generator_loss(portlist, test_rate, delay)
                if lost != 0:
                        loss_rate = test_rate
                        test_rate = (test_rate + zero_rate)/2
                else:
                        zero_rate = test_rate
                        test_rate = (test_rate + loss_rate)/2

        self.logger.info("zero loss rate is %s" % test_rate)
        return test_rate, tx_num, rx_num

    def traffic_generator_loss(self, portList, ratePercent, delay=60):
        """
        Run loss performance test on specified ports.
        """
        if self.check_port_list(portList, 'ixia'):
            return self.ixia_packet_gen.loss(portList, ratePercent, delay)
        elif not self.check_port_list(portList):
            self.logger.warning("exception by mixed port types")
            return None
        return self.packet_gen.loss(portList, ratePercenti, delay)

    def traffic_generator_latency(self, portList, ratePercent=100, delay=5):
        """
        Run latency performance test on specified ports.
        """
        if self.check_port_list(portList, 'ixia'):
            return self.ixia_packet_gen.latency(portList, ratePercent, delay)
        else:
            return None

    def check_random_pkts(self, portList, pktnum=2000, interval=0.01, allow_miss=True, params=None):
        """
        Send several random packets and check rx packets matched
        """
        # load functions in packet module
        module = __import__("packet")
        pkt_c = getattr(module, "Packet")
        send_f = getattr(module, "send_packets")
        sniff_f = getattr(module, "sniff_packets")
        load_f = getattr(module, "load_sniff_packets")
        compare_f = getattr(module, "compare_pktload")
        pkts = []
        # packet type random between tcp/udp/ipv6
        random_type = ['TCP', 'UDP', 'IPv6_TCP', 'IPv6_UDP']
        # at least wait 2 seconds
        timeout = int(pktnum * (interval + 0.01)) + 2
        for txport, rxport in portList:
            txIntf = self.get_interface(txport)
            rxIntf = self.get_interface(rxport)
            for num in range(pktnum):
                # chose random packet
                pkt_type = random.choice(random_type)
                pkt = pkt_c(pkt_type=pkt_type,
                            pkt_len=random.randint(64, 1514),
                            ran_payload=True)
                # config packet if has parameters
                if params and len(portList) == len(params):
                    for param in params:
                        layer, config = param
                        pkt.config_layer(layer, config)
                # sequence saved in layer4 source port
                if "TCP" in pkt_type:
                    pkt.config_layer('tcp', {'src': num % 65536})
                else:
                    pkt.config_layer('udp', {'src': num % 65536})
                pkts.append(pkt)

            # send and sniff packets
            inst = sniff_f(intf=rxIntf, count=pktnum, timeout=timeout)
            send_f(intf=txIntf, pkts=pkts, interval=interval)
            recv_pkts = load_f(inst)

            # only report when recevied number not matched
            if len(pkts) != len(recv_pkts):
                print "Pkt number not matched,%d sent and %d received\n" \
                       % (len(pkts), len(recv_pkts))
                if allow_miss is False:
                    return False

            # check each received packet content
            for idx in range(len(recv_pkts)):
                t_idx = recv_pkts[idx].strip_element_layer4('src')
                if compare_f(pkts[t_idx], recv_pkts[idx], "L4") is False:
                    print "Pkt recevied index %d not match original " \
                          "index %d" % (idx, t_idx)
                    return False

        return True

    def extend_external_packet_generator(self, clazz, instance):
        """
        Update packet generator function, will implement later.
        """
        if self.it_uses_external_generator():
            self.ixia_packet_gen.__class__ = clazz
            current_attrs = instance.__dict__
            instance.__dict__ = self.ixia_packet_gen.__dict__
            instance.__dict__.update(current_attrs)

    def kill_all(self, killall=False):
        """
        Kill all scapy process or DPDK application on tester.
        """
        if not self.has_external_traffic_generator():
            self.alt_session.send_expect('killall scapy 2>/dev/null; echo tester', '# ', 5)
        if killall:
            super(Tester, self).kill_all()

    def close(self):
        """
        Close ssh session and IXIA tcl session.
        """
        if self.session:
            self.session.close()
            self.session = None
        if self.alt_session:
            self.alt_session.close()
            self.alt_session = None
        if self.it_uses_external_generator():
            self.ixia_packet_gen.close()

    def crb_exit(self):
        """
        Close all resource before crb exit
        """
        self.logger.logger_exit()
        self.close()
