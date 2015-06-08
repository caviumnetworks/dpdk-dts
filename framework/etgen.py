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

import re
import string
import time
import dts
import ixiacfg
from ssh_connection import SSHConnection
from settings import SCAPY2IXIA
from logger import getLogger
from exception import VerifyFailure


class SoftwarePacketGenerator():
    """
    Software WindRiver packet generator for performance measurement.
    """
    def __init__(self, tester):
        self.tester = tester

    def packet_generator(self, portList, rate_percent):
        # bind ports
        self.tester.send_expect("insmod igb_uio.ko", "#")

        bind_cmd = ""
        ports = []
        tx_ports = []
        for (tx_port, rx_port, pcap_file) in portList:
            if tx_port not in ports:
                ports.append(tx_port)
                tx_ports.append(tx_port)
            if rx_port not in ports:
                ports.append(rx_port)

        for port in ports:
            bind_cmd += " %s" % self.tester.ports_info[port]['pci']

        self.tester.send_expect("./dpdk_nic_bind.py --bind=igb_uio %s" % bind_cmd, "#")

        # assgin core for ports
        map_cmd = ""
        port_index = range(len(ports))
        port_map = dict(zip(ports, port_index))
        self.tester.init_reserved_core()
        for port in ports:
            numa = self.tester.get_port_numa(port)
            cores = self.tester.get_reserved_core("2C", socket=numa)

            if len(cores) < 2:
                raise VerifyFailure("Not enough cores for performance!!!")

            map_cmd += "[%s:%s].%d, " % (cores[0], cores[1], port_map[port])

        # create pcap for every port
        pcap_cmd = ""
        for (tx_port, rx_port, pcap_file) in portList:
            pcap_cmd += " -s %d:%s" % (port_map[tx_port], pcap_file)

        # Selected 2 for -n to optimize results on Burage
        cores_mask = dts.create_mask(self.tester.get_core_list("all"))

        self.tester.send_expect("./pktgen -n 2 -c %s --proc-type auto --socket-mem 256,256 -- -P -m \"%s\" %s"
                                % (cores_mask, map_cmd, pcap_cmd), "Pktgen >", 100)

        if rate_percent != 100:
            self.tester.send_expect("set all rate %s" % rate_percent, "Pktgen>")
        else:
            self.tester.send_expect("set all rate 100", "Pktgen>")

        self.tester.send_expect("start all", "Pktgen>")
        time.sleep(10)
        out = self.tester.send_expect("clr", "Pktgen>")

        match = r"Bits per second: (\d+)+/(\d+)"
        m = re.search(match, out)

        match = r"Packets per second: (\d+)+/(\d+)"
        n = re.search(match, out)

        rx_bps = int(m.group(1))
        rx_pps = int(n.group(1))
        tx_bps = int(m.group(2))

        self.tester.send_expect("stop all", "Pktgen>")
        self.tester.send_expect("quit", "# ")
        self.tester.kill_all(killall=True)
        self.tester.restore_interfaces()

        return rx_bps, tx_bps, rx_pps

    def throughput(self, portList, rate_percent=100):
        (bps_rx, _, pps_rx) = self.packet_generator(portList, rate_percent)
        return bps_rx, pps_rx

    def loss(self, portList, ratePercent):
        (bps_rx, bps_tx, _) = self.packet_generator(portList, ratePercent)
        assert bps_tx != 0
        return (float(bps_tx) - float(bps_rx)) / float(bps_tx)


class IxiaPacketGenerator(SSHConnection):

    """
    IXIA packet generator for performance measurement.
    """

    def __init__(self, tester):
        self.tester = tester
        self.NAME = 'ixia'
        self.logger = getLogger(self.NAME)
        super(IxiaPacketGenerator, self).__init__(self.get_ip_address(),
                                                  self.NAME,
                                                  self.get_password())
        super(IxiaPacketGenerator, self).init_log(self.logger)

        self.tcl_cmds = []
        self.chasId = None
        self.conRelation = {}

        ixiaRef = self.tester.get_external_traffic_generator()
        if ixiaRef is None or ixiaRef not in ixiacfg.ixiaPorts:
            return

        self.ixiaVersion = ixiacfg.ixiaPorts[ixiaRef]["Version"]
        self.ports = ixiacfg.ixiaPorts[ixiaRef]["Ports"]

        self.logger.info(self.ixiaVersion)
        self.logger.info(self.ports)

        self.tclServerIP = ixiacfg.ixiaPorts[ixiaRef]["IP"]

        # prepare tcl shell and ixia library
        self.send_expect("tclsh", "% ")
        self.send_expect("source ./IxiaWish.tcl", "% ")
        self.send_expect("set ::env(IXIA_VERSION) %s" % self.ixiaVersion, "% ")
        out = self.send_expect("package req IxTclHal", "% ")
        self.logger.debug("package req IxTclHal return:" + out)
        if self.ixiaVersion in out:
            if not self.tcl_server_login():
                self.close()
                self.session = None

    def get_ip_address(self):
        return self.tester.get_ip_address()

    def get_password(self):
        return self.tester.get_password()

    def add_tcl_cmd(self, cmd):
        """
        Add one tcl command into command list.
        """
        self.tcl_cmds.append(cmd)

    def clean(self):
        """
        Clean ownership of IXIA devices and logout tcl session.
        """
        self.close()
        self.send_expect("clearOwnershipAndLogout", "% ")

    def parse_pcap(self, fpcap):
        dump_str1 = "cmds = []\n"
        dump_str2 = "for i in rdpcap('%s', -1):\n" % fpcap
        dump_str3 = "    if 'Vxlan' in i.command():\n" + \
                    "        vxlan_str = ''\n" + \
                    "        l = len(i[Vxlan])\n" + \
                    "        vxlan = str(i[Vxlan])\n" + \
                    "        first = True\n" + \
                    "        for j in range(l):\n" + \
                    "            if first:\n" + \
                    "                vxlan_str += \"Vxlan(hexval='%02X\" %ord(vxlan[j])\n" + \
                    "                first = False\n" + \
                    "            else:\n" + \
                    "                vxlan_str += \" %02X\" %ord(vxlan[j])\n" + \
                    "        vxlan_str += \"\')\"\n" + \
                    "        command = re.sub(r\"Vxlan(.*)\", vxlan_str, i.command())\n" + \
                    "    else:\n" + \
                    "        command = i.command()\n" + \
                    "    cmds.append(command)\n" + \
                    "print cmds\n" + \
                    "exit()"

        f = open("dumppcap.py", "w")
        f.write(dump_str1)
        f.write(dump_str2)
        f.write(dump_str3)
        f.close()

        self.session.copy_file_to("dumppcap.py")
        out = self.send_expect("scapy -c dumppcap.py 2>/dev/null", "% ", 120)
        flows = eval(out)
        return flows

    def ether(self, port, src, dst, type):
        """
        Configure Ether protocal.
        """
        self.add_tcl_cmd("protocol config -ethernetType ethernetII")
        self.add_tcl_cmd('stream config -sa "%s"' % self.macToTclFormat(src))
        self.add_tcl_cmd('stream config -da "%s"' % self.macToTclFormat(dst))

    def ip(self, port, frag, src, proto, tos, dst, chksum, len, version, flags, ihl, ttl, id, options=None):
        """
        Configure IP protocal.
        """
        self.add_tcl_cmd("protocol config -name ip")
        self.add_tcl_cmd('ip config -sourceIpAddr "%s"' % src)
        self.add_tcl_cmd('ip config -destIpAddr "%s"' % dst)
        self.add_tcl_cmd("ip config -ttl %d" % ttl)
        self.add_tcl_cmd("ip config -totalLength %d" % len)
        self.add_tcl_cmd("ip config -fragment %d" % frag)
        self.add_tcl_cmd("ip config -ipProtocol %d" % proto)
        self.add_tcl_cmd("ip config -identifier %d" % id)
        self.add_tcl_cmd("stream config -framesize %d" % (len + 18))
        self.add_tcl_cmd("ip set %d %d %d" % (self.chasId, port['card'], port['port']))

    def macToTclFormat(self, macAddr):
        """
        Convert normal mac adress format into IXIA's format.
        """
        macAddr = macAddr.upper()
        return "%s %s %s %s %s %s" % (macAddr[:2], macAddr[3:5], macAddr[6:8], macAddr[9:11], macAddr[12:14], macAddr[15:17])

    def ipv6(self, port, version, tc, fl, plen, nh, hlim, src, dst):
        """
        Configure IPv6 protocal.
        """
        self.add_tcl_cmd("protocol config -name ipV6")
        self.add_tcl_cmd('ipV6 setDefault')
        self.add_tcl_cmd('ipV6 config -destAddr "%s"' % self.ipv6_to_tcl_format(dst))
        self.add_tcl_cmd('ipV6 config -sourceAddr "%s"' % self.ipv6_to_tcl_format(src))
        self.add_tcl_cmd('ipV6 config -flowLabel %d' % fl)
        self.add_tcl_cmd('ipV6 config -nextHeader %d' % nh)
        self.add_tcl_cmd('ipV6 config -hopLimit %d' % hlim)
        self.add_tcl_cmd('ipV6 config -trafficClass %d' % tc)
        self.add_tcl_cmd("ipV6 clearAllExtensionHeaders")
        self.add_tcl_cmd("ipV6 addExtensionHeader %d" % nh)

        self.add_tcl_cmd("stream config -framesize %d" % (plen + 40 + 18))
        self.add_tcl_cmd("ipV6 set %d %d %d" % (self.chasId, port['card'], port['port']))

    def udp(self, port, dport, sport, len, chksum):
        """
        Configure UDP protocal.
        """
        self.add_tcl_cmd("udp setDefault")
        self.add_tcl_cmd("udp config -sourcePort %d" % sport)
        self.add_tcl_cmd("udp config -destPort %d" % dport)
        self.add_tcl_cmd("udp config -length %d" % len)
        self.add_tcl_cmd("udp set %d %d %d" %
                         (self.chasId, port['card'], port['port']))

    def vxlan(self, port, hexval):
        self.add_tcl_cmd("protocolPad setDefault")
        self.add_tcl_cmd("protocol config -enableProtocolPad true")
        self.add_tcl_cmd("protocolPad config -dataBytes \"%s\"" % hexval)
        self.add_tcl_cmd("protocolPad set %d %d %d" %
                         (self.chasId, port['card'], port['port']))

    def tcp(self, port, sport, dport, seq, ack, dataofs, reserved, flags, window, chksum, urgptr, options=None):
        """
        Configure TCP protocal.
        """
        self.add_tcl_cmd("tcp setDefault")
        self.add_tcl_cmd("tcp config -sourcePort %d" % sport)
        self.add_tcl_cmd("tcp config -destPort %d" % dport)
        self.add_tcl_cmd("tcp set %d %d %d" % (self.chasId, port['card'], port['port']))

    def sctp(self, port, sport, dport, tag, chksum):
        """
        Configure SCTP protocal.
        """
        self.add_tcl_cmd("tcp config -sourcePort %d" % sport)
        self.add_tcl_cmd("tcp config -destPort %d" % dport)
        self.add_tcl_cmd("tcp set %d %d %d" % (self.chasId, port['card'], port['port']))

    def dot1q(self, port, prio, id, vlan, type):
        """
        Configure 8021Q protocal.
        """
        self.add_tcl_cmd("protocol config -enable802dot1qTag true")
        self.add_tcl_cmd("vlan config -vlanID %d" % vlan)
        self.add_tcl_cmd("vlan config -userPriority %d" % prio)
        self.add_tcl_cmd("vlan set %d %d %d" % (self.chasId, port['card'], port['port']))

    def config_stream(self, fpcap, txport, rate_percent, stream_id=1, latency=False):
        """
        Configure IXIA stream and enable mutliple flows.
        """
        flows = self.parse_pcap(fpcap)

        self.add_tcl_cmd("ixGlobalSetDefault")
        self.config_ixia_stream(rate_percent, flows, latency)

        pat = re.compile(r"(\w+)\((.*)\)")
        for flow in flows:
            for header in flow.split('/'):
                match = pat.match(header)
                params = eval('dict(%s)' % match.group(2))
                method_name = match.group(1)
                if method_name == 'Vxlan':
                    method = getattr(self, method_name.lower())
                    method(txport, **params)
                    break
                if method_name in SCAPY2IXIA:
                    method = getattr(self, method_name.lower())
                    method(txport, **params)

            self.add_tcl_cmd("stream set %d %d %d %d" % (self.chasId, txport[
                                                         'card'], txport['port'], stream_id))
            stream_id += 1

        if len(flows) > 1:
            stream_id -= 1
            self.add_tcl_cmd("stream config -dma gotoFirst")
            self.add_tcl_cmd("stream set %d %d %d %d" %
                             (self.chasId, txport['card'], txport['port'], stream_id))

    def config_ixia_stream(self, rate_percent, flows, latency):
        """
        Configure IXIA stream with rate and latency.
        Override this method if you want to add custom stream configuration.
        """
        self.add_tcl_cmd("stream config -rateMode usePercentRate")
        self.add_tcl_cmd("stream config -percentPacketRate %s" % rate_percent)
        self.add_tcl_cmd("stream config -numFrames 1")
        if len(flows) == 1:
            self.add_tcl_cmd("stream config -dma contPacket")
        else:
            self.add_tcl_cmd("stream config -dma advance")
        # request by packet Group
        if latency is not False:
            self.add_tcl_cmd("stream config -fir true")

    def tcl_server_login(self):
        """
        Connect to tcl server and take ownership of all the ports needed.
        """
        out = self.send_expect("ixConnectToTclServer %s" % self.tclServerIP, "% ", 30)
        self.logger.debug("ixConnectToTclServer return:" + out)
        if out.strip()[-1] != '0':
            return False

        self.send_expect("ixLogin IxiaTclUser", "% ")

        out = self.send_expect("ixConnectToChassis %s" % self.tclServerIP, "% ", 30)
        if out.strip()[-1] != '0':
            return False

        out = self.send_expect("set chasId [ixGetChassisID %s]" % self.tclServerIP, "% ")
        self.chasId = int(out.strip())

        self.send_expect("ixClearOwnership [list %s]" % string.join(
            ['[list %d %d %d]' % (self.chasId, item['card'], item['port']) for item in self.ports], ' '), "% ", 10)
        self.send_expect("ixTakeOwnership [list %s] force" % string.join(
            ['[list %d %d %d]' % (self.chasId, item['card'], item['port']) for item in self.ports], ' '), "% ", 10)

        return True

    def tcl_server_logout(self):
        """
        Disconnect to tcl server and make sure has been logged out.
        """
        self.send_expect("ixDisconnectFromChassis %s" % self.tclServerIP, "%")
        self.send_expect("ixLogout", "%")
        self.send_expect("ixDisconnectTclServer %s" % self.tclServerIP, "%")

    def config_port(self, pList):
        """
        Configure ports and make them ready for performance validation.
        """
        pl = list()
        for item in pList:
            self.add_tcl_cmd("port setFactoryDefaults chasId %d %d" % (
                item['card'], item['port']))

            pl.append('[list %d %d %d]' % (self.chasId, item['card'], item['port']))

        self.add_tcl_cmd("set portList [list %s]" % string.join(pl, ' '))

        self.add_tcl_cmd("ixClearTimeStamp portList")
        self.add_tcl_cmd("ixWritePortsToHardware portList")
        self.add_tcl_cmd("ixCheckLinkState portList")

    def set_ixia_port_list(self, pList):
        """
        Implement ports/streams configuration on specified ports.
        """
        self.add_tcl_cmd("set portList [list %s]" %
                         string.join(['[list %d %d %d]' %
                                      (self.chasId, item['card'], item['port']) for item in pList], ' '))

    def send_ping6(self, pci, mac, ipv6):
        """
        Send ping6 packet from IXIA ports.
        """
        self.send_expect("source ./ixTcl1.0/ixiaPing6.tcl", "% ")
        out = self.send_expect('ping6 "%s" "%s" %d %d %d' %
                               (self.ipv6_to_tcl_format(ipv6), self.macToTclFormat(mac), self.chasId, self.pci_to_port(pci)['card'], self.pci_to_port(pci)['port']), "% ", 90)
        return out

    def ipv6_to_tcl_format(self, ipv6):
        """
        Convert normal IPv6 address to IXIA format.
        """
        ipv6 = ipv6.upper()
        singleAddr = ipv6.split(":")
        if '' == singleAddr[0]:
            singleAddr = singleAddr[1:]
        if '' in singleAddr:
            tclFormatAddr = ''
            addStr = '0:' * (8 - len(singleAddr)) + '0'
            for i in range(len(singleAddr)):
                if singleAddr[i] == '':
                    tclFormatAddr += addStr + ":"
                else:
                    tclFormatAddr += singleAddr[i] + ":"
            tclFormatAddr = tclFormatAddr[0:len(tclFormatAddr) - 1]
            return tclFormatAddr
        else:
            return ipv6

    def get_ports(self):
        """
        API to get ixia ports
        """
        plist = list()
        if self.session is None:
            return plist

        for p in self.ports:
            plist.append({'type': 'ixia', 'pci': 'IXIA:%d.%d' % (p['card'], p['port'])})
        return plist

    def pci_to_port(self, pci):
        """
        Convert IXIA fake pci to IXIA port.
        """
        ixia_pci_regex = "IXIA:(\d*).(\d*)"
        m = re.match(ixia_pci_regex, pci)
        if m is None:
            return {'card': -1, 'port': -1}

        return {'card': int(m.group(1)), 'port': int(m.group(2))}

    def loss(self, portList, ratePercent):
        """
        Run loss performance test and return loss rate.
        """
        rxPortlist, txPortlist = self._configure_everything(portList, ratePercent)
        return self.get_loss_packet_rate(rxPortlist, txPortlist)

    def get_loss_packet_rate(self, rxPortlist, txPortlist):
        """
        Get RX/TX packet statistics and calculate loss rate.
        """
        time.sleep(3)

        self.send_expect("ixStopTransmit portList", "%", 10)
        time.sleep(2)
        sendNumber = 0
        for port in txPortlist:
            self.stat_get_stat_all_stats(port)
            sendNumber += self.get_frames_sent()
            time.sleep(0.5)

        self.logger.info("send :%f" % sendNumber)

        assert sendNumber != 0

        revNumber = 0
        for port in rxPortlist:
            self.stat_get_stat_all_stats(port)
            revNumber += self.get_frames_received()
        self.logger.info("rev  :%f" % revNumber)

        return float(sendNumber - revNumber) / sendNumber

    def latency(self, portList, ratePercent, delay=5):
        """
        Run latency performance test and return latency statistics.
        """
        rxPortlist, txPortlist = self._configure_everything(portList, ratePercent, True)
        return self.get_packet_latency(rxPortlist)

    def get_packet_latency(self, rxPortlist):
        """
        Stop IXIA transmit and return latency statistics.
        """
        latencyList = []
        time.sleep(10)
        self.send_expect("ixStopTransmit portList", "%", 10)
        for rx_port in rxPortlist:
            self.pktGroup_get_stat_all_stats(rx_port)
            latency = {"port": rx_port,
                       "min": self.get_min_latency(),
                       "max": self.get_max_latency(),
                       "average": self.get_average_latency()}
            latencyList.append(latency)
        return latencyList

    def throughput(self, port_list, rate_percent=100, delay=5):
        """
        Run throughput performance test and return throughput statistics.
        """
        rxPortlist, txPortlist = self._configure_everything(port_list, rate_percent)
        return self.get_transmission_results(rxPortlist, txPortlist, delay)

    def _configure_everything(self, port_list, rate_percent, latency=False):
        """
        Prepare and configure IXIA ports for performance test.
        """
        rxPortlist, txPortlist = self.prepare_port_list(port_list, rate_percent, latency)
        self.prepare_ixia_for_transmission(txPortlist, rxPortlist)
        self.configure_transmission()
        self.start_transmission()
        self.clear_tcl_commands()
        return rxPortlist, txPortlist

    def clear_tcl_commands(self):
        """
        Clear all commands in command list.
        """
        del self.tcl_cmds[:]

    def start_transmission(self):
        """
        Run commands in command list.
        """
        fileContent = "\n".join(self.tcl_cmds) + "\n"
        self.tester.create_file(fileContent, 'ixiaConfig.tcl')
        self.send_expect("source ixiaConfig.tcl", "% ", 75)

    def configure_transmission(self, latency=False):
        """
        Start IXIA ports transmition.
        """
        self.add_tcl_cmd("ixStartTransmit portList")

    def prepare_port_list(self, portList, rate_percent=100, latency=False):
        """
        Configure stream and flow on every IXIA ports.
        """
        txPortlist = set()
        rxPortlist = set()

        for (txPort, rxPort, pcapFile) in portList:
            txPortlist.add(txPort)
            rxPortlist.add(rxPort)

        # port init
        self.config_port([self.pci_to_port(
            self.tester.get_pci(port)) for port in txPortlist.union(rxPortlist)])

        # stream/flow setting
        for (txPort, rxPort, pcapFile) in portList:
            self.config_stream(pcapFile, self.pci_to_port(self.tester.get_pci(txPort)), rate_percent, 1, latency)

        # config stream before packetGroup
        if latency is not False:
            for (txPort, rxPort, pcapFile) in portList:
                flow_num = len(self.parse_pcap(pcapFile))
                self.config_pktGroup_rx(self.pci_to_port(self.tester.get_pci(rxPort)))
                self.config_pktGroup_tx(self.pci_to_port(self.tester.get_pci(txPort)))
        return rxPortlist, txPortlist

    def prepare_ixia_for_transmission(self, txPortlist, rxPortlist):
        """
        Clear all statistics and implement configuration to IXIA hareware.
        """
        self.add_tcl_cmd("ixClearStats portList")
        self.set_ixia_port_list([self.pci_to_port(self.tester.get_pci(port)) for port in txPortlist])
        self.add_tcl_cmd("ixWriteConfigToHardware portList")
        for port in txPortlist:
            self.start_pktGroup(self.pci_to_port(self.tester.get_pci(port)))
        for port in rxPortlist:
            self.start_pktGroup(self.pci_to_port(self.tester.get_pci(port)))

    def get_transmission_results(self, rx_port_list, tx_port_list, delay=5):
        """
        Override this method if you want to change the way of getting results
        back from IXIA.
        """
        time.sleep(delay)
        bpsRate = 0
        rate = 0
        oversize = 0
        for port in rx_port_list:
            self.stat_get_rate_stat_all_stats(port)
            out = self.send_expect("stat cget -framesReceived", '%', 10)
            rate += int(out.strip())
            out = self.send_expect("stat cget -bitsReceived", '% ', 10)
            self.logger.debug("port %d bits rate:" % (port) + out)
            bpsRate += int(out.strip())
            out = self.send_expect("stat cget -oversize", '%', 10)
            oversize += int(out.strip())

        self.logger.info("Rate: %f Mpps" % (rate * 1.0 / 1000000))
        self.logger.info("Mbps rate: %f Mbps" % (bpsRate * 1.0 / 1000000))

        self.send_expect("ixStopTransmit portList", "%", 30)

        if rate == 0 and oversize > 0:
            return (bpsRate, oversize)
        else:
            return (bpsRate, rate)

    def config_ixia_dcb_init(self, rxPort, txPort):
        """
        Configure Ixia for DCB.
        """
        self.send_expect("source ./ixTcl1.0/ixiaDCB.tcl", "% ")
        self.send_expect("configIxia %d %s" % (self.chasId, string.join(["%s" % (
            repr(self.conRelation[port][n])) for port in [rxPort, txPort] for n in range(3)])), "% ", 100)

    def config_port_dcb(self, direction, tc):
        """
        Configure Port for DCB.
        """
        self.send_expect("configPort %s %s" % (direction, tc), "% ", 100)

    def cfgStreamDcb(self, stream, rate, prio, types):
        """
        Configure Stream for DCB.
        """
        self.send_expect("configStream %s %s %s %s" % (stream, rate, prio, types), "% ", 100)

    def get_connection_relation(self, dutPorts):
        """
        Get the connect relations between DUT and Ixia.
        """
        for port in dutPorts:
            info = self.tester.get_pci(self.tester.get_local_port(port)).split('.')
            self.conRelation[port] = [int(info[0]), int(info[1]), repr(self.tester.dut.get_mac_address(port).replace(':', ' ').upper())]
        return self.conRelation

    def config_pktGroup_rx(self, rxport):
        """
        Sets the transmit Packet Group configuration of the stream
        Default streamID is 1
        """
        self.add_tcl_cmd("port config -receiveMode $::portRxModeWidePacketGroup")
        self.add_tcl_cmd("port set %d %d %d" % (self.chasId, rxport['card'], rxport['port']))
        self.add_tcl_cmd("packetGroup setDefault")
        self.add_tcl_cmd("packetGroup config -latencyControl cutThrough")
        self.add_tcl_cmd("packetGroup setRx %d %d %d" % (self.chasId, rxport['card'], rxport['port']))
        self.add_tcl_cmd("packetGroup setTx %d %d %d 1" % (self.chasId, rxport['card'], rxport['port']))

    def config_pktGroup_tx(self, txport):
        """
        Configure tx port pktGroup for latency.
        """
        self.add_tcl_cmd("packetGroup setDefault")
        self.add_tcl_cmd("packetGroup config -insertSignature true")
        self.add_tcl_cmd("packetGroup setTx %d %d %d 1" % (self.chasId,
                                                           txport['card'], txport['port']))

    def start_pktGroup(self, port):
        """
        Start tx port pktGroup for latency.
        """
        self.add_tcl_cmd("ixStartPortPacketGroups %d %d %d" % (self.chasId,
                                                               port['card'], port['port']))

    def pktGroup_get_stat_all_stats(self, port_number):
        """
        Stop Packet Group operation on port and get current Packet Group
        statistics on port.
        """
        port = self.pci_to_port(self.tester.get_pci(port_number))
        self.send_expect("ixStopPortPacketGroups %d %d %d" % (self.chasId, port['card'], port['port']), "%", 100)
        self.send_expect("packetGroupStats get %d %d %d 0 16384" % (self.chasId, port['card'], port['port']), "%", 100)
        self.send_expect("packetGroupStats getGroup 0", "%", 100)

    def close(self):
        """
        We first close the tclsh session opened at the beggining,
        then the SSH session.
        """
        if self.isalive():
            self.send_expect('exit', '# ')
            super(IxiaPacketGenerator, self).close()

    def stat_get_stat_all_stats(self, port_number):
        """
        Sends a IXIA TCL command to obtain all the stat values on a given port.
        """
        port = self.pci_to_port(self.tester.get_pci(port_number))
        command = 'stat get statAllStats {0} {1} {2}'
        command = command.format(self.chasId, port['card'], port['port'])
        self.send_expect(command, '% ', 10)

    def prepare_ixia_internal_buffers(self, port_number):
        """
        Tells IXIA to prepare the internal buffers were the frames were captured.
        """
        port = self.pci_to_port(self.tester.get_pci(port_number))
        command = 'capture get {0} {1} {2}'
        command = command.format(self.chasId, port['card'], port['port'])
        self.send_expect(command, '% ', 30)

    def stat_get_rate_stat_all_stats(self, port_number):
        """
        All statistics of specified IXIA port.
        """
        port = self.pci_to_port(self.tester.get_pci(port_number))
        command = 'stat getRate statAllStats {0} {1} {2}'
        command = command.format(self.chasId, port['card'], port['port'])
        self.send_expect(command, '% ', 30)
        out = self.send_expect(command, '% ', 30)

    def ixia_capture_buffer(self, port_number, first_frame, last_frame):
        """
        Tells IXIA to load the captured frames into the internal buffers.
        """
        port = self.pci_to_port(self.tester.get_pci(port_number))
        command = 'captureBuffer get {0} {1} {2} {3} {4}'
        command = command.format(self.chasId, port['card'], port['port'],
                                 first_frame, last_frame)
        self.send_expect(command, '%', 60)

    def ixia_export_buffer_to_file(self, frames_filename):
        """
        Tells IXIA to dump the frames it has loaded in its internal buffer to a
        text file.
        """
        command = 'captureBuffer export %s' % frames_filename
        self.send_expect(command, '%', 30)

    def _stat_cget_value(self, requested_value):
        """
        Sends a IXIA TCL command to obtain a given stat value.
        """
        command = "stat cget -" + requested_value
        result = self.send_expect(command, '%', 10)
        return int(result.strip())

    def _capture_cget_value(self, requested_value):
        """
        Sends a IXIA TCL command to capture certain number of packets.
        """
        command = "capture cget -" + requested_value
        result = self.send_expect(command, '%', 10)
        return int(result.strip())

    def _packetgroup_cget_value(self, requested_value):
        """
        Sends a IXIA TCL command to get pktGroup stat value.
        """
        command = "packetGroupStats cget -" + requested_value
        result = self.send_expect(command, '%', 10)
        return int(result.strip())

    def number_of_captured_packets(self):
        """
        Returns the number of packets captured by IXIA on a previously set
        port. Call self.stat_get_stat_all_stats(port) before.
        """
        return self._capture_cget_value('nPackets')

    def get_frames_received(self):
        """
        Returns the number of packets captured by IXIA on a previously set
        port. Call self.stat_get_stat_all_stats(port) before.
        """
        return self._stat_cget_value('framesReceived')

    def get_flow_control_frames(self):
        """
        Returns the number of control frames captured by IXIA on a
        previously set port. Call self.stat_get_stat_all_stats(port) before.
        """
        return self._stat_cget_value('flowControlFrames')

    def get_frames_sent(self):
        """
        Returns the number of packets sent by IXIA on a previously set
        port. Call self.stat_get_stat_all_stats(port) before.
        """
        return self._stat_cget_value('framesSent')

    def get_transmit_duration(self):
        """
        Returns the duration in nanosecs of the last transmission on a
        previously set port. Call self.stat_get_stat_all_stats(port) before.
        """
        return self._stat_cget_value('transmitDuration')

    def get_min_latency(self):
        """
        Returns the minimum latency in nanoseconds of the frames in the
        retrieved capture buffer. Call packetGroupStats get before.
        """
        return self._packetgroup_cget_value('minLatency')

    def get_max_latency(self):
        """
        Returns the maximum latency in nanoseconds of the frames in the
        retrieved capture buffer. Call packetGroupStats get before.
        """
        return self._packetgroup_cget_value('maxLatency')

    def get_average_latency(self):
        """
        Returns the average latency in nanoseconds of the frames in the
        retrieved capture buffer. Call packetGroupStats get before.
        """
        return self._packetgroup_cget_value('averageLatency')
