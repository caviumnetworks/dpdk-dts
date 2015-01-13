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
from ssh_connection import SSHConnection
from crb import Crb
from etgen import IxiaPacketGenerator, SoftwarePacketGenerator
from logger import getLogger
from settings import IXIA


class Tester(Crb):

    """
    Start the DPDK traffic generator on the machine `target`.
    A config file and pcap file must have previously been copied
    to this machine.
    """
    PORT_MAP_CACHE_KEY = 'tester_port_map'
    PORT_INFO_CACHE_KEY = 'tester_port_info'
    CORE_LIST_CACHE_KEY = 'tester_core_list'
    NUMBER_CORES_CACHE_KEY = 'tester_number_cores'
    PCI_DEV_CACHE_KEY = 'tester_pci_dev_info'

    def __init__(self, crb, serializer):
        super(Tester, self).__init__(crb, serializer)
        self.NAME = 'tester'

        self.logger = getLogger(self.NAME)
        self.session = SSHConnection(self.get_ip_address(), self.NAME)
        self.session.init_log(self.logger)
        self.alt_session = SSHConnection(self.get_ip_address(), self.NAME)
        self.alt_session.init_log(self.logger)

        self.ports_map = []
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
        self.map_available_ports()
        if self.ports_map == None or len(self.ports_map) == 0:
            raise ValueError("ports_map should not be empty, please check all links")

    def get_local_port(self, remotePort):
        """
        Return tester local port connect to specified dut port.
        """
        return self.ports_map[remotePort]

    def get_local_port_type(self, remotePort):
        """
        Return tester local port type connect to specified dut port.
        """
        return self.ports_info[self.get_local_port(remotePort)]['type']

    def get_interface(self, localPort):
        """
        Return tester local port interface name.
        """
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

    def scan_ports(self):
        """
        Scan all ports on tester and save port's pci/mac/interface.
        """
        if self.read_cache:
            self.ports_info = self.serializer.load(self.PORT_INFO_CACHE_KEY)

        if not self.read_cache or self.ports_info is None:
            self.scan_ports_uncached()
            if self.it_uses_external_generator():
                self.ports_info.extend(self.ixia_packet_gen.get_ports())
            self.serializer.save(self.PORT_INFO_CACHE_KEY, self.ports_info)

        self.logger.info(self.ports_info)

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

            intf = self.get_interface_name(bus_id, devfun_id)

            if "No such file" in intf:
                self.logger.info("Tester: [000:%s %s] %s" % (pci_bus, pci_id,
                                                             "unknow_interface"))
                continue

            self.logger.info("Tester: [000:%s %s] %s" % (pci_bus, pci_id, intf))
            macaddr = self.get_mac_addr(intf, bus_id, devfun_id)

            # store the port info to port mapping
            self.ports_info.append({'pci': pci_bus,
                                    'type': pci_id,
                                    'intf': intf,
                                    'mac': macaddr})

    def send_ping6(self, localPort, ipv6, mac):
        """
        Send ping6 packet from local port with destination ipv6 address.
        """
        if self.ports_info[localPort]['type'] == 'ixia':
            return self.ixia_packet_gen.send_ping6(self.ports_info[localPort]['intf'], mac, ipv6)
        else:
            return self.send_expect("ping6 -w 5 -c 5 -A -I %s %s" % (self.ports_info[localPort]['intf'], ipv6), "# ", 10)

    def map_available_ports(self):
        """
        Load or generate network connection mapping list.
        """
        if self.read_cache:
            self.ports_map = self.serializer.load(self.PORT_MAP_CACHE_KEY)

        if not self.read_cache or self.ports_map is None:
            self.map_available_ports_uncached()
            self.serializer.save(self.PORT_MAP_CACHE_KEY, self.ports_map)
            self.logger.warning("DUT PORT MAP: " + str(self.ports_map))

    def map_available_ports_uncached(self):
        """
        Generate network connection mapping list.
        """

        nrPorts = len(self.dut.ports_info)
        if nrPorts == 0:
            return

        self.ports_map = [-1] * nrPorts

        hits = [False] * len(self.ports_info)

        for dutPort in range(nrPorts):
            for localPort in range(len(self.ports_info)):
                if hits[localPort]:
                    continue

                ipv6 = self.dut.get_ipv6_address(dutPort)
                if ipv6 == "Not connected":
                    continue

                out = self.send_ping6(localPort, ipv6, self.dut.get_mac_address(dutPort))

                if ('64 bytes from' in out):
                    self.logger.info("PORT MAP: [local %d: dut %d]" % (localPort, dutPort))
                    hits[localPort] = True
                    self.ports_map[dutPort] = localPort
                    break

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

    def traffic_generator_loss(self, portList, ratePercent):
        """
        Run loss performance test on specified ports.
        """
        if self.check_port_list(portList, 'ixia'):
            return self.ixia_packet_gen.loss(portList, ratePercent)
        elif not self.check_port_list(portList):
            self.logger.warning("exception by mixed port types")
            return None
        return self.packet_gen.loss(portList, ratePercent)

    def traffic_generator_latency(self, portList, ratePercent=100, delay=5):
        """
        Run latency performance test on specified ports.
        """
        if self.check_port_list(portList, 'ixia'):
            return self.ixia_packet_gen.latency(portList, ratePercent, delay)
        else:
            return None

    def extend_external_packet_generator(self, clazz, instance):
        """
        Update packet generator function, will implement later.
        """
        if self.it_uses_external_generator():
            self.ixia_packet_gen.__class__ = clazz
            current_attrs = instance.__dict__
            instance.__dict__ = self.ixia_packet_gen.__dict__
            instance.__dict__.update(current_attrs)

    def kill_all(self):
        """
        Kill all scapy process and DPDK applications on tester.
        """
        if not self.has_external_traffic_generator():
            self.alt_session.send_expect('killall scapy 2>/dev/null; echo tester', '# ', 5)
            super(Tester, self).kill_all()

    def close(self):
        """
        Close ssh session and IXIA tcl session.
        """
        super(Tester, self).close()
        if self.it_uses_external_generator():
            self.ixia_packet_gen.close()
