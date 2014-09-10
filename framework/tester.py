# <COPYRIGHT_TAG>

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

"""
Start the DPDK traffic generator on the machine `target`.
A config file and pcap file must have previously been copied
to this machine.
"""


class Tester(Crb):
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
        if self.it_uses_external_generator():
            self.ixia_packet_gen = IxiaPacketGenerator(self)
        self.packet_gen = SoftwarePacketGenerator(self)

    def get_ip_address(self):
        return self.crb['tester IP']

    def it_uses_external_generator(self):
        return self.want_perf_tests and self.has_external_traffic_generator()

    def tester_prerequisites(self):
        self.init_core_list()
        self.pci_devices_information()
        self.restore_interfaces()
        self.scan_ports()
        self.map_available_ports()
        assert len(self.ports_map) > 0

    def get_local_port(self, remotePort):
        return self.ports_map[remotePort]

    def get_local_port_type(self, remotePort):
        return self.ports_info[self.get_local_port(remotePort)]['type']

    def get_interface(self, localPort):
        return self.ports_info[localPort]['intf']

    def get_mac(self, localPort):
        if self.ports_info[localPort]['type'] == 'ixia':
            return "00:00:00:00:00:01"
        else:
            return self.ports_info[localPort]['mac']

    def get_port_status(self, port):
        """
        return link status of eth
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
        if self.read_cache:
            self.ports_info = self.serializer.load(self.PORT_INFO_CACHE_KEY)

        if not self.read_cache or self.ports_info is None:
            self.scan_ports_uncached()
            if self.it_uses_external_generator():
                self.ports_info.extend(self.ixia_packet_gen.get_ports())
            self.serializer.save(self.PORT_INFO_CACHE_KEY, self.ports_info)

        self.logger.info(self.ports_info)

    def scan_ports_uncached(self):
        self.ports_info = []

        self.logger.warning("Skipped: Unknown kernel interface")
        self.logger.warning("Skipped: Unknown NIC")

        for (pci_bus, pci_id) in self.pci_devices_info:
            # ignore unknown card types
            if pci_id not in NICS.values():
                self.logger.info("Tester: [000:%s %s] %s" % (pci_bus, pci_id,
                                                             unknow_nic))
                continue

            addr_array = pci_bus.split(':')
            bus_id = addr_array[0]
            devfun_id = addr_array[1]

            intf = self.get_interface_name(bus_id, devfun_id)

            if "No such file" in intf:
                self.logger.info("Tester: [000:%s %s] %s" % (pci_bus, pci_id,
                                                             unknow_interface))
                continue

            self.logger.info("Tester: [000:%s %s] %s" % (pci_bus, pci_id, intf))
            macaddr = self.get_mac_addr(intf, bus_id, devfun_id)

            # store the port info to port mapping
            self.ports_info.append({'pci': pci_bus,
                                    'type': pci_id,
                                    'intf': intf,
                                    'mac': macaddr})

    def send_ping6(self, localPort, ipv6, mac):
        if self.ports_info[localPort]['type'] == 'ixia':
            return self.ixia_packet_gen.send_ping6(self.ports_info[localPort]['intf'], mac, ipv6)
        else:
            return self.send_expect("ping6 -w 5 -c 5 -A -I %s %s" % (self.ports_info[localPort]['intf'], ipv6), "# ", 10)

    def map_available_ports(self):
        if self.read_cache:
            self.ports_map = self.serializer.load(self.PORT_MAP_CACHE_KEY)

        if not self.read_cache or self.ports_map is None:
            self.map_available_ports_uncached()
            self.serializer.save(self.PORT_MAP_CACHE_KEY, self.ports_map)
            self.logger.warning("DUT PORT MAP: " + str(self.ports_map))

    def map_available_ports_uncached(self):

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
        pci = self.ports_info[port]['pci']
        out = self.send_expect("cat /sys/bus/pci/devices/0000:%s/numa_node" % pci, "#")
        return int(out)

    def check_port_list(self, portList, ftype='normal'):
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
        self.scapyCmds.append(cmd)

    def scapy_execute(self, timeout=60):
        self.kill_all()

        self.send_expect("scapy", ">>> ")
        if self.bgProcIsRunning:
            self.send_expect('subprocess.call("scapy -c sniff.py &", shell=True)', ">>> ")
            self.bgProcIsRunning = False
        sleep(1)

        for cmd in self.scapyCmds:
            self.send_expect(cmd, ">>> ", timeout)

        sleep(1)
        self.scapyCmds = []
        self.send_expect("exit()", "# ")

    def scapy_background(self):
        self.inBg = True

    def scapy_foreground(self):
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
        out = self.send_expect("cat scapyResult.txt", "# ")
        self.logger.info('SCAPY Result:\n' + out + '\n\n\n')

        return out.rpartition('[')[0]

    def traffic_generator_throughput(self, portList, rate_percent=100, delay=5):
        if self.check_port_list(portList, 'ixia'):
            return self.ixia_packet_gen.throughput(portList, rate_percent, delay)
        if not self.check_port_list(portList):
            self.logger.warning("exception by mixed port types")
            return None
        return self.packet_gen.throughput(portList, rate_percent)

    def traffic_generator_loss(self, portList, ratePercent):
        if self.check_port_list(portList, 'ixia'):
            return self.ixia_packet_gen.loss(portList, ratePercent)
        elif not self.check_port_list(portList):
            self.logger.warning("exception by mixed port types")
            return None
        return self.packet_gen.loss(portList, ratePercent)

    def traffic_generator_latency(self, portList, ratePercent=100, delay=5):
        if self.check_port_list(portList, 'ixia'):
            return self.ixia_packet_gen.latency(portList, ratePercent, delay)
        else:
            return None

    def extend_external_packet_generator(self, clazz, instance):
        if self.it_uses_external_generator():
            self.ixia_packet_gen.__class__ = clazz
            current_attrs = instance.__dict__
            instance.__dict__ = self.ixia_packet_gen.__dict__
            instance.__dict__.update(current_attrs)

    def kill_all(self):
        if not self.has_external_traffic_generator():
            self.alt_session.send_expect('killall scapy 2>/dev/null; echo tester', '# ', 5)
            super(Tester, self).kill_all()

    def close(self):
        super(Tester, self).close()
        if self.it_uses_external_generator():
            self.ixia_packet_gen.close()
