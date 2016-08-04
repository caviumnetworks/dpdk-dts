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
DPDK Test suite.


Test userland 10Gb PMD.

"""

import time
import re
import random
from socket import htons, htonl
from functools import wraps

import utils
from test_case import TestCase
from exception import TimeoutException
from settings import TIMEOUT
from pmd_output import PmdOutput

SOCKET_0 = 0
SOCKET_1 = 1

MODE_ROUND_ROBIN = 0
MODE_ACTIVE_BACKUP = 1
MODE_XOR_BALANCE = 2
MODE_BROADCAST = 3
MODE_LACP = 4
MODE_TLB_BALANCE = 5
MODE_ALB_BALANCE = 6

FRAME_SIZE_64 = 64
FRAME_SIZE_65 = 65
FRAME_SIZE_128 = 128
FRAME_SIZE_256 = 256
FRAME_SIZE_512 = 512
FRAME_SIZE_1024 = 1024
FRAME_SIZE_1280 = 1280
FRAME_SIZE_1518 = 1518

S_MAC_IP_PORT = [('52:00:00:00:00:00', '10.239.129.65', 61),
                 ('52:00:00:00:00:01', '10.239.129.66', 62),
                 ('52:00:00:00:00:02', '10.239.129.67', 63)]

D_MAC_IP_PORT = []
LACP_MESSAGE_SIZE = 128


class TestPmdBonded(TestCase):

    def get_stats(self, portid, rx_tx):
        """
        Get packets number from port statistic
        """

        out = self.dut.send_expect("show port stats %d" % portid, "testpmd> ")

        if rx_tx == "rx":
            result_scanner = r"RX-packets: ([0-9]+)\s*RX-missed: ([0-9]+)\s*RX-bytes:  ([0-9]+)"
        elif rx_tx == "tx":
            result_scanner = r"TX-packets: ([0-9]+)\s*TX-errors: ([0-9]+)\s*TX-bytes:  ([0-9]+)"
        else:
            return None

        scanner = re.compile(result_scanner, re.DOTALL)
        m = scanner.search(out)

        return m.groups()

    def parse_ether_ip(self, dest_port, **ether_ip):
        """
        ether_ip:
            'ether':
                {
                    'dest_mac':False
                    'src_mac':"52:00:00:00:00:00"
                }
            'dot1q':
                {
                    'vlan':1
                }
            'ip':
                {
                    'dest_ip':"10.239.129.88"
                    'src_ip':"10.239.129.65"
                }
            'udp':
                {
                    'dest_port':53
                    'src_port':53
                }
        """
        ret_ether_ip = {}
        ether = {}
        dot1q = {}
        ip = {}
        udp = {}

        try:
            dut_dest_port = self.dut_ports[dest_port]
        except Exception, e:
            dut_dest_port = dest_port

        if not ether_ip.get('ether'):
            ether['dest_mac'] = self.dut.get_mac_address(dut_dest_port)
            ether['src_mac'] = "52:00:00:00:00:00"
        else:
            if not ether_ip['ether'].get('dest_mac'):
                ether['dest_mac'] = self.dut.get_mac_address(dut_dest_port)
            else:
                ether['dest_mac'] = ether_ip['ether']['dest_mac']
            if not ether_ip['ether'].get('src_mac'):
                ether['src_mac'] = "52:00:00:00:00:00"
            else:
                ether['src_mac'] = ether_ip["ether"]["src_mac"]

        if not ether_ip.get('dot1q'):
            pass
        else:
            if not ether_ip['dot1q'].get('vlan'):
                dot1q['vlan'] = '1'
            else:
                dot1q['vlan'] = ether_ip['dot1q']['vlan']

        if not ether_ip.get('ip'):
            ip['dest_ip'] = "10.239.129.88"
            ip['src_ip'] = "10.239.129.65"
        else:
            if not ether_ip['ip'].get('dest_ip'):
                ip['dest_ip'] = "10.239.129.88"
            else:
                ip['dest_ip'] = ether_ip['ip']['dest_ip']
            if not ether_ip['ip'].get('src_ip'):
                ip['src_ip'] = "10.239.129.65"
            else:
                ip['src_ip'] = ether_ip['ip']['src_ip']

        if not ether_ip.get('udp'):
            udp['dest_port'] = 53
            udp['src_port'] = 53
        else:
            if not ether_ip['udp'].get('dest_port'):
                udp['dest_port'] = 53
            else:
                udp['dest_port'] = ether_ip['udp']['dest_port']
            if not ether_ip['udp'].get('src_port'):
                udp['src_port'] = 53
            else:
                udp['src_port'] = ether_ip['udp']['src_port']

        ret_ether_ip['ether'] = ether
        ret_ether_ip['dot1q'] = dot1q
        ret_ether_ip['ip'] = ip
        ret_ether_ip['udp'] = udp

        return ret_ether_ip

    def send_packet(self,
                    dest_port,
                    src_port=False,
                    frame_size=FRAME_SIZE_64,
                    count=1,
                    invert_verify=False,
                    **ether_ip):
        """
        Send count packet to portid
        count: 1 or 2 or 3 or ... or 'MANY'
               if count is 'MANY', then set count=1000,
               send packets during 5 seconds.
        ether_ip:
            'ether':
                {
                    'dest_mac':False
                    'src_mac':"52:00:00:00:00:00"
                }
            'dot1q':
                {
                    'vlan':1
                }
            'ip':
                {
                    'dest_ip':"10.239.129.88"
                    'src_ip':"10.239.129.65"
                }
            'udp':
                {
                    'dest_port':53
                    'src_port':53
                }
        """
        during = 0
        loop = 0
        try:
            count = int(count)
        except ValueError as e:
            if count == 'MANY':
                during = 5
                count = 1000
            else:
                raise e

        if not src_port:
            gp0rx_pkts, gp0rx_err, gp0rx_bytes = [int(_) for _ in self.get_stats(self.dut_ports[dest_port], "rx")]
            itf = self.tester.get_interface(self.tester.get_local_port(self.dut_ports[dest_port]))
        else:
            gp0rx_pkts, gp0rx_err, gp0rx_bytes = [int(_) for _ in self.get_stats(dest_port, "rx")]
            itf = src_port

        ret_ether_ip = self.parse_ether_ip(dest_port, **ether_ip)

        pktlen = frame_size - 18
        padding = pktlen - 20

        start = time.time()
        while True:
            self.tester.scapy_foreground()
            self.tester.scapy_append('nutmac="%s"' % ret_ether_ip['ether']['dest_mac'])
            self.tester.scapy_append('srcmac="%s"' % ret_ether_ip['ether']['src_mac'])

            if ether_ip.get('dot1q'):
                self.tester.scapy_append('vlanvalue=%d' % ret_ether_ip['dot1q']['vlan'])
            self.tester.scapy_append('destip="%s"' % ret_ether_ip['ip']['dest_ip'])
            self.tester.scapy_append('srcip="%s"' % ret_ether_ip['ip']['src_ip'])
            self.tester.scapy_append('destport=%d' % ret_ether_ip['udp']['dest_port'])
            self.tester.scapy_append('srcport=%d' % ret_ether_ip['udp']['src_port'])
            if not ret_ether_ip.get('dot1q'):
                self.tester.scapy_append('sendp([Ether(dst=nutmac, src=srcmac)/IP(dst=destip, src=srcip, len=%s)/\
UDP(sport=srcport, dport=destport)/Raw(load="\x50"*%s)], iface="%s", count=%d)' % (pktlen, padding, itf, count))
            else:
                self.tester.scapy_append('sendp([Ether(dst=nutmac, src=srcmac)/Dot1Q(vlan=vlanvalue)/IP(dst=destip, src=srcip, len=%s)/\
UDP(sport=srcport, dport=destport)/Raw(load="\x50"*%s)], iface="%s", count=%d)' % (pktlen, padding, itf, count))

            self.tester.scapy_execute()
            loop += 1

            now = time.time()
            if (now - start) >= during:
                break
        time.sleep(.5)

        if not src_port:
            p0rx_pkts, p0rx_err, p0rx_bytes = [int(_) for _ in self.get_stats(self.dut_ports[dest_port], "rx")]
        else:
            p0rx_pkts, p0rx_err, p0rx_bytes = [int(_) for _ in self.get_stats(dest_port, "rx")]

        p0rx_pkts -= gp0rx_pkts
        p0rx_bytes -= gp0rx_bytes

        if not invert_verify:
            self.verify(p0rx_pkts >= count * loop,
                        "Data not received by port")
        else:
            global LACP_MESSAGE_SIZE
            self.verify(p0rx_pkts == 0 or
                        p0rx_bytes / p0rx_pkts == LACP_MESSAGE_SIZE,
                        "Data received by port, but should not.")
        return count * loop

    def blank_enter(self):
        """
        Just enter blank for the prompt 'testpmd> '
        """
        time.sleep(2)
        self.dut.send_expect(" ", "testpmd> ")

    def dummy_timeout(func):
        """
        There are multiple threads, so maybe you can`t wait for the 'testpmd>',
        if raising TIMEOUT, we will try to expect one more time.
        """
        @wraps(func)
        def ack_timeout(*args, **kwargs):
            pmd_bond_instance = args[0]
            try:
                return func(*args, **kwargs)
            except TimeoutException:
                return pmd_bond_instance.blank_enter()
        return ack_timeout

    @dummy_timeout
    def __send_expect(self, cmds, expected, timeout=TIMEOUT, alt_session=False):
        """
        Encapsulate private expect function because multiple threads printing issue.
        """
        return self.dut.send_expect(cmds, expected, timeout, alt_session)

    def get_value_from_str(self, key_str, regx_str, string):
        """
        Get some values from the given string by the regular expression.
        """
        pattern = r"(?<=%s)%s" % (key_str, regx_str)
        s = re.compile(pattern)
        res = s.search(string)
        if type(res).__name__ == 'NoneType':
            return ' '
        else:
            return res.group(0)

    def get_detail_from_port_info(self, key_str, regx_str, port):
        """
        Get the detail info from the output of pmd cmd 'show port info <port num>'.
        """
        out = self.dut.send_expect("show port info %d" % port, "testpmd> ")
        find_value = self.get_value_from_str(key_str, regx_str, out)
        return find_value

    def get_port_mac(self, port_id):
        """
        Get the specified port MAC.
        """
        return self.get_detail_from_port_info("MAC address: ", "([0-9A-F]{2}:){5}[0-9A-F]{2}", port_id)

    def get_port_connect_socket(self, port_id):
        """
        Get the socket id which the specified port is connectting with.
        """
        return self.get_detail_from_port_info("Connect to socket: ", "\d+", port_id)

    def get_port_memory_socket(self, port_id):
        """
        Get the socket id which the specified port memory is allocated on.
        """
        return self.get_detail_from_port_info("memory allocation on the socket: ", "\d+", port_id)

    def get_port_link_status(self, port_id):
        """
        Get the specified port link status now.
        """
        return self.get_detail_from_port_info("Link status: ", "\d+", port_id)

    def get_port_link_speed(self, port_id):
        """
        Get the specified port link speed now.
        """
        return self.get_detail_from_port_info("Link speed: ", "\d+", port_id)

    def get_port_link_duplex(self, port_id):
        """
        Get the specified port link mode, duplex or siplex.
        """
        return self.get_detail_from_port_info("Link duplex: ", "\S+", port_id)

    def get_port_promiscuous_mode(self, port_id):
        """
        Get the promiscuous mode of port.
        """
        return self.get_detail_from_port_info("Promiscuous mode: ", "\S+", port_id)

    def get_port_allmulticast_mode(self, port_id):
        """
        Get the allmulticast mode of port.
        """
        return self.get_detail_from_port_info("Allmulticast mode: ", "\S+", port_id)

    def get_port_vlan_offload(self, port_id):
        """
        Function: get the port vlan settting info.
        return value:
            'strip':'on'
            'filter':'on'
            'qinq':'off'
        """
        vlan_info = {}
        vlan_info['strip'] = self.get_detail_from_port_info("strip ", '\S+', port_id)
        vlan_info['filter'] = self.get_detail_from_port_info('filter', '\S+', port_id)
        vlan_info['qinq'] = self.get_detail_from_port_info('qinq\(extend\) ', '\S+', port_id)
        return vlan_info

    def get_info_from_bond_config(self, key_str, regx_str, bond_port):
        """
        Get info by executing the command "show bonding config".
        """
        out = self.dut.send_expect("show bonding config %d" % bond_port, "testpmd> ")
        find_value = self.get_value_from_str(key_str, regx_str, out)
        return find_value

    def get_bond_mode(self, bond_port):
        """
        Get the  mode of the bonding device  which you choose.
        """
        return self.get_info_from_bond_config("Bonding mode: ", "\d*", bond_port)

    def get_bond_balance_policy(self, bond_port):
        """
        Get the balance transmit policy of bonding device.
        """
        return self.get_info_from_bond_config("Balance Xmit Policy: ", "\S+", bond_port)

    def get_bond_slaves(self, bond_port):
        """
        Get all the slaves of the bonding device which you choose.
        """
        try:
            return self.get_info_from_bond_config("Slaves \(\d\): \[", "\d*( \d*)*", bond_port)
        except Exception as e:
            return self.get_info_from_bond_config("Slaves: \[", "\d*( \d*)*", bond_port)

    def get_bond_active_slaves(self, bond_port):
        """
        Get the active slaves of the bonding device which you choose.
        """
        try:
            return self.get_info_from_bond_config("Active Slaves \(\d\): \[", "\d*( \d*)*", bond_port)
        except Exception as e:
            return self.get_info_from_bond_config("Acitve Slaves: \[", "\d*( \d*)*", bond_port)

    def get_bond_primary(self, bond_port):
        """
        Get the primary slave of the bonding device which you choose.
        """
        return self.get_info_from_bond_config("Primary: \[", "\d*", bond_port)

    def launch_app(self, pmd_param=" "):
        """
        Launch the testpmd app with the command parameters.
        """
        self.pmdout.start_testpmd("all", param=pmd_param)

    def create_bonded_device(self, mode=0, socket=0, verify_detail=False):
        """
        Create a bonding device with the parameters you specified.
        """
        out = self.dut.send_expect("create bonded device %d %d" % (mode, socket), "testpmd> ")
        self.verify("Created new bonded device" in out,
                    "Create bonded device on mode [%d] socket [%d] failed" % (mode, socket))
        bond_port = self.get_value_from_str("Created new bonded device eth_bond_testpmd_[\d] on \(port ",
                                            "\d+",
                                            out)
        bond_port = int(bond_port)

        if verify_detail:
            out = self.dut.send_expect("show bonding config %d" % bond_port, "testpmd> ")
            self.verify("Bonding mode: %d" % mode in out,
                        "Bonding mode display error when create bonded device")
            self.verify("Slaves: []" in out,
                        "Slaves display error when create bonded device")
            self.verify("Active Slaves: []" in out,
                        "Active Slaves display error when create bonded device")
            self.verify("Primary: []" not in out,
                        "Primary display error when create bonded device")

            out = self.dut.send_expect("show port info %d" % bond_port, "testpmd> ")
            self.verify("Connect to socket: %d" % socket in out,
                        "Bonding port connect socket error")
            self.verify("Link status: down" in out,
                        "Bonding port default link status error")
            self.verify("Link speed: 0 Mbps" in out,
                        "Bonding port default link speed error")

        return bond_port

    def start_all_ports(self):
        """
        Start all the ports which the testpmd can see.
        """
        self.start_port("all")

    def start_port(self, port):
        """
        Start a port which the testpmd can see.
        """
        self.__send_expect("port start %s" % str(port), "testpmd> ")
        time.sleep(3)

    def add_slave_to_bonding_device(self, bond_port, invert_verify=False, *slave_port):
        """
        Add the ports into the bonding device as slaves.
        """
        if len(slave_port) <= 0:
            utils.RED("No port exist when add slave to bonded device")
        for slave_id in slave_port:
            self.__send_expect("add bonding slave %d %d" % (slave_id, bond_port), "testpmd> ")

            slaves = self.get_info_from_bond_config("Slaves \(\d\): \[", "\d*( \d*)*", bond_port)
            if not invert_verify:
                self.verify(str(slave_id) in slaves,
                            "Add port as bonding slave failed")
            else:
                self.verify(str(slave_id) not in slaves,
                            "Add port as bonding slave successfully,should fail")

    def remove_slave_from_bonding_device(self, bond_port, invert_verify=False, *slave_port):
        """
        Remove the specified slave port from the bonding device.
        """
        if len(slave_port) <= 0:
            utils.RED("No port exist when remove slave from bonded device")
        for slave_id in slave_port:
            self.dut.send_expect("remove bonding slave %d %d" % (int(slave_id), bond_port), "testpmd> ")
            out = self.get_info_from_bond_config("Slaves: \[", "\d*( \d*)*", bond_port)
            if not invert_verify:
                self.verify(str(slave_id) not in out,
                            "Remove slave to fail from bonding device")
            else:
                self.verify(str(slave_id) in out,
                            "Remove slave successfully from bonding device,should be failed")

    def remove_all_slaves(self, bond_port):
        """
        Remove all slaves of specified bound device.
        """
        all_slaves = self.get_bond_slaves(bond_port)
        all_slaves = all_slaves.split()
        if len(all_slaves) == 0:
            pass
        else:
            self.remove_slave_from_bonding_device(bond_port, False, *all_slaves)

    def set_primary_for_bonding_device(self, bond_port, slave_port, invert_verify=False):
        """
        Set the primary slave for the bonding device.
        """
        self.dut.send_expect("set bonding primary %d %d" % (slave_port, bond_port), "testpmd> ")
        out = self.get_info_from_bond_config("Primary: \[", "\d*", bond_port)
        if not invert_verify:
            self.verify(str(slave_port) in out,
                        "Set bonding primary port failed")
        else:
            self.verify(str(slave_port) not in out,
                        "Set bonding primary port successfully,should not success")

    def set_mode_for_bonding_device(self, bond_port, mode):
        """
        Set the mode for the bonding device.
        """
        self.dut.send_expect("set bonding mode %d %d" % (mode, bond_port), "testpmd> ")
        mode_value = self.get_bond_mode(bond_port)
        self.verify(str(mode) in mode_value, "Set bonding mode failed")

    def set_mac_for_bonding_device(self, bond_port, mac):
        """
        Set the MAC for the bonding device.
        """
        self.dut.send_expect("set bonding mac_addr %s %s" % (bond_port, mac), "testpmd> ")
        new_mac = self.get_port_mac(bond_port)
        self.verify(new_mac == mac, "Set bonding mac failed")

    def set_balance_policy_for_bonding_device(self, bond_port, policy):
        """
        Set the balance transmit policy for the bonding device.
        """
        self.dut.send_expect("set bonding balance_xmit_policy %d %s" % (bond_port, policy), "testpmd> ")
        new_policy = self.get_bond_balance_policy(bond_port)
        policy = "BALANCE_XMIT_POLICY_LAYER" + policy.lstrip('l')
        self.verify(new_policy == policy, "Set bonding balance policy failed")

    def send_default_packet_to_slave(self, unbound_port, bond_port, pkt_count=100, **slaves):
        """
        Send packets to the slaves and calculate the slave`s RX packets
        and unbond port TX packets.
        Parameters:
        *** unbound_port: the unbonded port id
        *** bond_port: the bonded device port id
        *** slaves:
        ******* 'active'=[]
        ******* 'inactive'=[]
        """
        pkt_orig = {}
        pkt_now = {}
        temp_count = 0
        summary = 0

        # send to slave ports
        pkt_orig = self.get_all_stats(unbound_port, 'tx', bond_port, **slaves)
        for slave in slaves['active']:
            temp_count = self.send_packet(self.dut_ports[slave], False, FRAME_SIZE_64, pkt_count)
            summary += temp_count
        for slave in slaves['inactive']:
            self.send_packet(self.dut_ports[slave], False, FRAME_SIZE_64, pkt_count, True)
        pkt_now = self.get_all_stats(unbound_port, 'tx', bond_port, **slaves)

        for key in pkt_now:
            for num in [0, 1, 2]:
                pkt_now[key][num] -= pkt_orig[key][num]

        return pkt_now, summary

    def send_customized_packet_to_slave(self, unbound_port, bond_port, *pkt_info, **slaves):
        """
        Send packets to the slaves and calculate the slave`s RX packets
        and unbond port TX packets.
        Parameters:
        *** unbound_port: the unbonded port id
        *** bond_port: the bonded device port id
        *** pkt_info: the first is necessary which will describe the packet,
                      the second is optional which will describe the params of
                      the function send_packet
        *** slaves:
        ******* 'active'=[]
        ******* 'inactive'=[]
        """
        pkt_orig = {}
        pkt_now = {}
        temp_count = 0
        summary = 0

        pkt_info_len = len(pkt_info)
        if pkt_info_len < 1:
            self.verify(False, "At least one members for pkt_info!")

        ether_ip = pkt_info[0]
        if pkt_info_len > 1:
            pkt_size = pkt_info[1].get('frame_size', FRAME_SIZE_64)
            pkt_count = pkt_info[1].get('pkt_count', 1)
            invert_verify = pkt_info[1].get('verify', False)
        else:
            pkt_size = FRAME_SIZE_64
            pkt_count = 1
            invert_verify = False

        # send to slave ports
        pkt_orig = self.get_all_stats(unbound_port, 'tx', bond_port, **slaves)
        for slave in slaves['active']:
            temp_count = self.send_packet(self.dut_ports[slave], False, pkt_size, pkt_count, invert_verify, **ether_ip)
            summary += temp_count
        for slave in slaves['inactive']:
            self.send_packet(self.dut_ports[slave], False, FRAME_SIZE_64, pkt_count, True)
        pkt_now = self.get_all_stats(unbound_port, 'tx', bond_port, **slaves)

        for key in pkt_now:
            for num in [0, 1, 2]:
                pkt_now[key][num] -= pkt_orig[key][num]

        return pkt_now, summary

    def send_customized_packet_to_bond_port(self, dut_unbound_port, dut_bond_port, tester_bond_port, pkt_count=100, **slaves):
        pkt_orig = {}
        pkt_now = {}
        temp_count = 0
        summary = 0

        # send to bond_port
        pkt_orig = self.get_all_stats(dut_unbound_port, 'tx', dut_bond_port, **slaves)

        if len(slaves['active']) != 0:
            invert_verify = False
        else:
            invert_verify = True

        dest_mac = self.get_port_mac(dut_bond_port)

        ether_ip = {}
        ether = {}
        ether['src_mac'] = ''
        ether['dest_mac'] = dest_mac
        ether_ip['ether'] = ether

        global S_MAC_IP_PORT
        source = S_MAC_IP_PORT

        for src_mac, src_ip, src_port in source:
            ether_ip['ether']['src_mac'] = src_mac
            temp_count = self.send_packet(dut_bond_port, tester_bond_port, FRAME_SIZE_64, pkt_count, invert_verify, **ether_ip)
            summary += temp_count
        pkt_now = self.get_all_stats(dut_unbound_port, 'tx', dut_bond_port, **slaves)

        for key in pkt_now:
            for num in [0, 1, 2]:
                pkt_now[key][num] -= pkt_orig[key][num]

        return pkt_now, summary

    def send_default_packet_to_unbound_port(self, unbound_port, bond_port, pkt_count=300, **slaves):
        """
        Send packets to the unbound port and calculate unbound port RX packets
        and the slave`s TX packets.
        Parameters:
        *** unbound_port: the unbonded port id
        *** bond_port: the bonded device port id
        *** slaves:
        ******* 'actvie':[]
        ******* 'inactive':[]
        """
        pkt_orig = {}
        pkt_now = {}
        summary = 0

        # send to unbonded device
        pkt_orig = self.get_all_stats(unbound_port, 'rx', bond_port, **slaves)
        summary = self.send_packet(unbound_port, False, FRAME_SIZE_64, pkt_count)
        pkt_now = self.get_all_stats(unbound_port, 'rx', bond_port, **slaves)

        for key in pkt_now:
            for num in [0, 1, 2]:
                pkt_now[key][num] -= pkt_orig[key][num]

        return pkt_now, summary

    def send_customized_packet_to_unbound_port(self, unbound_port, bond_port, policy, vlan_tag=False, pkt_count=100, **slaves):
        """
        Verify that transmitting the packets correctly in the XOR mode.
        Parameters:
        *** unbound_port: the unbonded port id
        *** bond_port: the bonded device port id
        *** policy:'L2' , 'L23' or 'L34'
        *** vlan_tag:False or True
        *** slaves:
        ******* 'active'=[]
        ******* 'inactive'=[]
        """
        pkt_orig = {}
        pkt_now = {}
        summary = 0
        temp_count = 0

        # send to unbound_port
        pkt_orig = self.get_all_stats(unbound_port, 'rx', bond_port, **slaves)

        dest_mac = self.dut.get_mac_address(self.dut_ports[unbound_port])
        dest_ip = "10.239.129.88"
        dest_port = 53

        global D_MAC_IP_PORT
        D_MAC_IP_PORT = [dest_mac, dest_ip, dest_port]

        ether_ip = {}
        ether = {}
        ip = {}
        udp = {}

        ether['dest_mac'] = False
        ip['dest_ip'] = dest_ip
        udp['dest_port'] = 53
        if vlan_tag:
            dot1q = {}
            dot1q['vlan'] = random.randint(1, 50)
            ether_ip['dot1q'] = dot1q

        ether_ip['ether'] = ether
        ether_ip['ip'] = ip
        ether_ip['udp'] = udp

        global S_MAC_IP_PORT
        source = S_MAC_IP_PORT

        for src_mac, src_ip, src_port in source:
            ether_ip['ether']['src_mac'] = src_mac
            ether_ip['ip']['src_ip'] = src_ip
            ether_ip['udp']['src_port'] = src_port
            temp_count = self.send_packet(unbound_port, False, FRAME_SIZE_64, pkt_count, False, **ether_ip)
            summary += temp_count
        pkt_now = self.get_all_stats(unbound_port, 'rx', bond_port, **slaves)

        for key in pkt_now:
            for num in [0, 1, 2]:
                pkt_now[key][num] -= pkt_orig[key][num]

        return pkt_now, summary

    #
    # Test cases.
    #
    def set_up_all(self):
        """
        Run before each test suite
        """
        self.verify('bsdapp' not in self.target, "Bonding not support freebsd")
        self.frame_sizes = [64, 65, 128, 256, 512, 1024, 1280, 1518]

        self.eth_head_size = 18
        self.ip_head_size = 20
        self.udp_header_size = 8

        self.dut_ports = self.dut.get_ports()

        self.port_mask = utils.create_mask(self.dut_ports)

        self.verify(len(self.dut_ports) >= 4, "Insufficient ports")

        self.ports_socket = self.dut.get_numa_id(self.dut_ports[0])

        self.all_cores_mask = utils.create_mask(self.dut.get_core_list("all"))

        self.pmdout = PmdOutput(self.dut)

        self.tester_bond = "bond0"

    def set_up(self):
        """
        Run before each test case.
        """
        if self._enable_perf:
            pmd_param = "--burst=32 --rxfreet=32 --mbcache=250 --txpt=32 \
--rxht=8 --rxwt=0 --txfreet=32 --txrst=32 --txqflags=0xf01"
            self.launch_app(pmd_param)
        else:
            self.launch_app()

    def verify_bound_basic_opt(self, mode_set):
        """
        Do some basic operations to bonded devices and slaves,
        such as adding, removing, setting primary or setting mode.
        """
        bond_port_0 = self.create_bonded_device(mode_set, SOCKET_0, True)
        self.add_slave_to_bonding_device(bond_port_0, False, self.dut_ports[1])

        mode_value = self.get_bond_mode(bond_port_0)
        self.verify('%d' % mode_set in mode_value,
                    "Setting bonding mode error")

        bond_port_1 = self.create_bonded_device(mode_set, SOCKET_0)
        self.add_slave_to_bonding_device(bond_port_0, False, self.dut_ports[0])
        self.add_slave_to_bonding_device(bond_port_1, True, self.dut_ports[0])

        OTHER_MODE = mode_set + 1 if not mode_set else mode_set - 1
        self.set_mode_for_bonding_device(bond_port_0, OTHER_MODE)
        self.set_mode_for_bonding_device(bond_port_0, mode_set)

        self.add_slave_to_bonding_device(bond_port_0, False, self.dut_ports[2])
        time.sleep(5)
        self.set_primary_for_bonding_device(bond_port_0, self.dut_ports[2])

        self.remove_slave_from_bonding_device(bond_port_0, False, self.dut_ports[2])
        primary_now = self.get_bond_primary(bond_port_0)
        self.verify(int(primary_now) == self.dut_ports[1],
                    "Reset primary slave failed after removing primary slave")

        for bond_port in [bond_port_0, bond_port_1]:
            self.remove_all_slaves(bond_port)

        self.dut.send_expect("quit", "# ")
        self.launch_app()

    def verify_bound_mac_opt(self, mode_set):
        """
        Create bonded device, add one slave,
        verify bonded device MAC action varies with the mode.
        """
        mac_address_0_orig = self.get_port_mac(self.dut_ports[0])
        mac_address_1_orig = self.get_port_mac(self.dut_ports[1])
        mac_address_2_orig = self.get_port_mac(self.dut_ports[2])
        mac_address_3_orig = self.get_port_mac(self.dut_ports[3])

        bond_port = self.create_bonded_device(mode_set, SOCKET_1)
        self.add_slave_to_bonding_device(bond_port, False, self.dut_ports[1])

        mac_address_bond_orig = self.get_port_mac(bond_port)
        self.verify(mac_address_1_orig == mac_address_bond_orig,
                    "Bonded device MAC address not same with first slave MAC")

        self.add_slave_to_bonding_device(bond_port, False, self.dut_ports[2])
        mac_address_2_now = self.get_port_mac(self.dut_ports[2])
        mac_address_bond_now = self.get_port_mac(bond_port)
        if mode_set in [MODE_ROUND_ROBIN, MODE_XOR_BALANCE, MODE_BROADCAST]:
            self.verify(mac_address_1_orig == mac_address_bond_now and
                        mac_address_bond_now == mac_address_2_now,
                        "NOT all slaves MAC address same with bonding device in mode %d" % mode_set)
        else:
            self.verify(mac_address_1_orig == mac_address_bond_now and
                        mac_address_bond_now != mac_address_2_now,
                        "All slaves should not be the same in mode %d"
                        % mode_set)

        new_mac = "00:11:22:00:33:44"
        self.set_mac_for_bonding_device(bond_port, new_mac)
        self.start_port(bond_port)
        mac_address_1_now = self.get_port_mac(self.dut_ports[1])
        mac_address_2_now = self.get_port_mac(self.dut_ports[2])
        mac_address_bond_now = self.get_port_mac(bond_port)
        if mode_set in [MODE_ROUND_ROBIN, MODE_XOR_BALANCE, MODE_BROADCAST]:
            self.verify(mac_address_1_now == mac_address_2_now == mac_address_bond_now == new_mac,
                        "Set mac failed for bonding device in mode %d" % mode_set)
        elif mode_set == MODE_LACP:
            self.verify(mac_address_bond_now == new_mac and
                        mac_address_1_now != new_mac and
                        mac_address_2_now != new_mac and
                        mac_address_1_now != mac_address_2_now,
                        "Set mac failed for bonding device in mode %d" % mode_set)
        elif mode_set in [MODE_ACTIVE_BACKUP, MODE_TLB_BALANCE]:
            self.verify(mac_address_bond_now == new_mac and
                        mac_address_1_now == new_mac and
                        mac_address_bond_now != mac_address_2_now,
                        "Set mac failed for bonding device in mode %d" % mode_set)

        self.set_primary_for_bonding_device(bond_port, self.dut_ports[2], False)
        mac_address_1_now = self.get_port_mac(self.dut_ports[1])
        mac_address_2_now = self.get_port_mac(self.dut_ports[2])
        mac_address_bond_now = self.get_port_mac(bond_port)
        self.verify(mac_address_bond_now == new_mac,
                    "Slave MAC changed when set primary slave")

        mac_address_1_orig = mac_address_1_now
        self.remove_slave_from_bonding_device(bond_port, False, self.dut_ports[2])
        mac_address_2_now = self.get_port_mac(self.dut_ports[2])
        self.verify(mac_address_2_now == mac_address_2_orig,
                    "MAC not back to original after removing the port")

        mac_address_1_now = self.get_port_mac(self.dut_ports[1])
        mac_address_bond_now = self.get_port_mac(bond_port)
        self.verify(mac_address_bond_now == new_mac and
                    mac_address_1_now == mac_address_1_orig,
                    "Bonding device or slave MAC changed after removing the primary slave")

        self.remove_all_slaves(bond_port)
        self.dut.send_expect("quit", "# ")
        self.launch_app()

    def verify_bound_promisc_opt(self, mode_set):
        """
        Set promiscuous mode on bonded device, verify bonded device and all slaves
        have different actions by the different modes.
        """
        unbound_port = self.dut_ports[3]
        bond_port = self.create_bonded_device(mode_set, SOCKET_0)
        self.add_slave_to_bonding_device(bond_port,
                                         False,
                                         self.dut_ports[0],
                                         self.dut_ports[1],
                                         self.dut_ports[2])
        self.dut.send_expect("set portlist %d,%d" % (unbound_port, bond_port), "testpmd> ")
        self.start_port(bond_port)
        self.dut.send_expect("start", "testpmd> ")

        port_disabled_num = 0
        testpmd_all_ports = self.dut_ports
        testpmd_all_ports.append(bond_port)
        for port_id in testpmd_all_ports:
            value = self.get_detail_from_port_info("Promiscuous mode: ", "enabled", port_id)
            if not value:
                port_disabled_num += 1
        self.verify(port_disabled_num == 0,
                    "Not all slaves of bonded device turn promiscuous mode on by default.")

        ether_ip = {}
        ether = {}
        ether['dest_mac'] = "00:11:22:33:44:55"
        ether_ip['ether'] = ether

        send_param = {}
        pkt_count = 1
        send_param['pkt_count'] = pkt_count
        pkt_info = [ether_ip, send_param]

        slaves = {}
        slaves['active'] = [self.dut_ports[0]]
        slaves['inactive'] = []

        pkt_now, summary = self.send_customized_packet_to_slave(unbound_port, bond_port, *pkt_info, **slaves)
        if mode_set == MODE_LACP:
            do_transmit = False
            pkt_size = 0
            if pkt_now[unbound_port][0]:
                do_transmit = True
                pkt_size = pkt_now[unbound_port][2] / pkt_now[unbound_port][0]
            self.verify(do_transmit and pkt_size != LACP_MESSAGE_SIZE,
                        "Data not received by slave or bonding device when promiscuous enabled")
        else:
            self.verify(pkt_now[self.dut_ports[0]][0] == pkt_now[bond_port][0] and
                        pkt_now[bond_port][0] == pkt_count,
                        "Data not received by slave or bonding device when promiscuous enabled")

        self.dut.send_expect("set promisc %s off" % bond_port, "testpmd> ")
        port_disabled_num = 0
        testpmd_all_ports = [self.dut_ports[0], self.dut_ports[1], self.dut_ports[2], bond_port]
        for port_id in testpmd_all_ports:
            value = self.get_detail_from_port_info('Promiscuous mode: ', 'disabled', port_id)
            if value == 'disabled':
                port_disabled_num += 1
        if mode_set in [MODE_ROUND_ROBIN, MODE_XOR_BALANCE, MODE_BROADCAST]:
            self.verify(port_disabled_num == 4,
                        "Not all slaves of bonded device turn promiscuous mode off in mode %d." % mode_set)
        elif mode_set == MODE_LACP:
            self.verify(port_disabled_num == 1,
                        "Not only turn bound device promiscuous mode off in mode %d" % mode_set)
        else:
            self.verify(port_disabled_num == 2,
                        "Not only the primary slave turn promiscous mode off in mode %d, " % mode_set +
                        " when bonded device  promiscous disabled.")

        if mode_set != MODE_LACP:
            send_param['verify'] = True
        pkt_now, summary = self.send_customized_packet_to_slave(unbound_port, bond_port, *pkt_info, **slaves)
        if mode_set == MODE_LACP:
            do_transmit = False
            pkt_size = 0
            if pkt_now[unbound_port][0]:
                do_transmit = True
                pkt_size = pkt_now[unbound_port][2] / pkt_now[unbound_port][0]
            self.verify(not do_transmit or
                        pkt_size == LACP_MESSAGE_SIZE,
                        "Data received by slave or bonding device when promiscuous disabled")
        else:
            self.verify(pkt_now[self.dut_ports[0]][0] == 0 and
                        pkt_now[bond_port][0] == 0,
                        "Data received by slave or bonding device when promiscuous disabled")

        pkt_now, summary = self.send_default_packet_to_slave(self.dut_ports[3], bond_port, pkt_count, **slaves)
        if mode_set == MODE_LACP:
            do_transmit = False
            pkt_size = 0
            if pkt_now[unbound_port][0]:
                do_transmit = True
                pkt_size = pkt_now[unbound_port][2] / pkt_now[unbound_port][0]
            self.verify(not do_transmit or
                        pkt_size != LACP_MESSAGE_SIZE,
                        "RX or TX packet number not correct when promiscuous disabled")
        else:
            self.verify(pkt_now[self.dut_ports[0]][0] == pkt_now[bond_port][0] and
                        pkt_now[self.dut_ports[3]][0] == pkt_now[bond_port][0] and
                        pkt_now[bond_port][0] == pkt_count,
                        "RX or TX packet number not correct when promiscuous disabled")

        self.remove_all_slaves(bond_port)
        self.dut.send_expect("quit", "# ")
        self.launch_app()

    def test_bound_basic_opt(self):
        self.verify_bound_basic_opt(MODE_ACTIVE_BACKUP)

    def test_bound_mac_opt(self):
        self.verify_bound_mac_opt(MODE_BROADCAST)

    def test_bound_promisc_opt(self):
        self.verify_bound_promisc_opt(MODE_BROADCAST)

    def admin_tester_port(self, local_port, status):
        """
        Do some operations to the network interface port, such as "up" or "down".
        """
        if self.tester.get_os_type() == 'freebsd':
            self.tester.admin_ports(local_port, status)
        else:
            eth = self.tester.get_interface(local_port)
            self.tester.admin_ports_linux(eth, status)
        time.sleep(5)

    def verify_round_robin_rx(self, unbound_port, bond_port, **slaves):
        """
        Verify the receiving packet are all correct in the round robin mode.
            slaves:
                'active' = []
                'inactive' = []
        """
        pkt_count = 100
        pkt_now = {}
        pkt_now, summary = self.send_default_packet_to_slave(unbound_port, bond_port, pkt_count=pkt_count, **slaves)

        self.verify(pkt_now[unbound_port][0] == pkt_count * slaves['active'].__len__(), "Unbonded port has error TX pkt count in mode 0")
        self.verify(pkt_now[bond_port][0] == pkt_count * slaves['active'].__len__(), "Bonding port has error RX pkt count in mode 0")

    def verify_round_robin_tx(self, unbound_port, bond_port, **slaves):
        """
        Verify the transmitting packet are all correct in the round robin mode.
            slaves:
                'active' = []
                'inactive' = []
        """
        pkt_count = 300
        pkt_now = {}
        pkt_now, summary = self.send_default_packet_to_unbound_port(unbound_port, bond_port, pkt_count=pkt_count, **slaves)

        if slaves['active'].__len__() == 0:
            self.verify(pkt_now[bond_port][0] == 0, "Bonding port should not have TX pkt in mode 0 when all slaves down")
        else:
            self.verify(pkt_now[bond_port][0] == pkt_count, "Bonding port has error TX pkt count in mode 0")
        for slave in slaves['active']:
            self.verify(pkt_now[slave][0] == pkt_count / slaves['active'].__len__(), "Active slave has error TX pkt count in mode 0")
        for slave in slaves['inactive']:
            self.verify(pkt_now[slave][0] == 0, "Inactive slave has error TX pkt count in mode 0")

    def test_round_robin_rx_tx(self):
        """
        Verify that receiving and transmitting the packets correctly in the round robin mode.
        """
        bond_port = self.create_bonded_device(MODE_ROUND_ROBIN, SOCKET_0)
        self.add_slave_to_bonding_device(bond_port, False, self.dut_ports[0], self.dut_ports[1], self.dut_ports[2])
        self.dut.send_expect("set portlist %d,%d" % (self.dut_ports[3], bond_port), "testpmd> ")
        self.start_all_ports()
        self.dut.send_expect("start", "testpmd> ")

        slaves = {}
        slaves['active'] = [self.dut_ports[0], self.dut_ports[1], self.dut_ports[2]]
        slaves['inactive'] = []
        self.verify_round_robin_rx(self.dut_ports[3], bond_port, **slaves)
        self.verify_round_robin_tx(self.dut_ports[3], bond_port, **slaves)

    def test_round_robin_one_slave_down(self):
        """
        Verify that receiving and transmitting the packets correctly in the round robin mode,
        when bringing any one slave of the bonding device link down.
        """
        bond_port = self.create_bonded_device(MODE_ROUND_ROBIN, SOCKET_0)
        self.add_slave_to_bonding_device(bond_port, False, self.dut_ports[0], self.dut_ports[1], self.dut_ports[2])
        self.dut.send_expect("set portlist %d,%d" % (self.dut_ports[3], bond_port), "testpmd> ")
        self.start_all_ports()
        self.dut.send_expect("start", "testpmd> ")
        self.admin_tester_port(self.tester.get_local_port(self.dut_ports[0]), "down")

        stat = self.tester.get_port_status(self.tester.get_local_port(self.dut_ports[0]))
        self.dut.send_expect("show bonding config %d" % bond_port, "testpmd> ")
        self.dut.send_expect("show port info all", "testpmd> ")

        try:
            slaves = {}
            slaves['active'] = [self.dut_ports[1], self.dut_ports[2]]
            slaves['inactive'] = [self.dut_ports[0]]
            self.verify_round_robin_rx(self.dut_ports[3], bond_port, **slaves)
            self.verify_round_robin_tx(self.dut_ports[3], bond_port, **slaves)
        finally:
            self.admin_tester_port(self.tester.get_local_port(self.dut_ports[0]), "up")

    def test_round_robin_all_slaves_down(self):
        """
        Verify that receiving and transmitting the packets correctly in the round robin mode,
        when bringing all slaves of the bonding device link down.
        """
        bond_port = self.create_bonded_device(MODE_ROUND_ROBIN, SOCKET_0)
        self.add_slave_to_bonding_device(bond_port, False, self.dut_ports[0], self.dut_ports[1], self.dut_ports[2])
        self.dut.send_expect("set portlist %d,%d" % (self.dut_ports[3], bond_port), "testpmd> ")
        self.start_all_ports()
        self.dut.send_expect("start", "testpmd> ")

        self.admin_tester_port(self.tester.get_local_port(self.dut_ports[0]), "down")
        self.admin_tester_port(self.tester.get_local_port(self.dut_ports[1]), "down")
        self.admin_tester_port(self.tester.get_local_port(self.dut_ports[2]), "down")

        try:
            slaves = {}
            slaves['active'] = []
            slaves['inactive'] = [self.dut_ports[0], self.dut_ports[1], self.dut_ports[2]]
            self.verify_round_robin_rx(self.dut_ports[3], bond_port, **slaves)
            self.verify_round_robin_tx(self.dut_ports[3], bond_port, **slaves)
        finally:
            self.admin_tester_port(self.tester.get_local_port(self.dut_ports[0]), "up")
            self.admin_tester_port(self.tester.get_local_port(self.dut_ports[1]), "up")
            self.admin_tester_port(self.tester.get_local_port(self.dut_ports[2]), "up")

    def get_all_stats(self, unbound_port, rx_tx, bond_port, **slaves):
        """
        Get all the port stats which the testpmd can dicover.
        Parameters:
        *** unbound_port: pmd port id
        *** rx_tx: unbond port stat 'rx' or 'tx'
        *** bond_port: bonding port
        *** slaves:
        ******** 'active' = []
        ******** 'inactive' = []
        """
        pkt_now = {}

        if rx_tx == 'rx':
            bond_stat = 'tx'
        else:
            bond_stat = 'rx'

        pkt_now[unbound_port] = [int(_) for _ in self.get_stats(unbound_port, rx_tx)]
        pkt_now[bond_port] = [int(_) for _ in self.get_stats(bond_port, bond_stat)]
        for slave in slaves['active']:
            pkt_now[slave] = [int(_) for _ in self.get_stats(slave, bond_stat)]
        for slave in slaves['inactive']:
            pkt_now[slave] = [int(_) for _ in self.get_stats(slave, bond_stat)]

        return pkt_now

    def verify_active_backup_rx(self, unbound_port, bond_port, **slaves):
        """
        Verify the RX packets are all correct in the active-backup mode.
        Parameters:
        *** slaves:
        ******* 'active' = []
        ******* 'inactive' = []
        """
        pkt_count = 100
        pkt_now = {}

        slave_num = slaves['active'].__len__()
        if slave_num != 0:
            active_flag = 1
        else:
            active_flag = 0

        pkt_now, summary = self.send_default_packet_to_slave(unbound_port, bond_port, pkt_count=pkt_count, **slaves)

        self.verify(pkt_now[bond_port][0] == pkt_count * slave_num, "Not correct RX pkt on bond port in mode 1")
        self.verify(pkt_now[unbound_port][0] == pkt_count * active_flag, "Not correct TX pkt on unbound port in mode 1")
        for slave in slaves['inactive']:
            self.verify(pkt_now[slave][0] == 0, "Not correct RX pkt on inactive port in mode 1")
        for slave in slaves['active']:
            self.verify(pkt_now[slave][0] == pkt_count, "Not correct RX pkt on active port in mode 1")

    def verify_active_backup_tx(self, unbound_port, bond_port, **slaves):
        """
        Verify the TX packets are all correct in the active-backup mode.
        Parameters:
        *** slaves:
        ******* 'active' = []
        ******* 'inactive' = []
        """
        pkt_count = 0
        pkt_now = {}

        if slaves['active'].__len__() != 0:
            primary_port = slaves['active'][0]
            active_flag = 1
        else:
            active_flag = 0

        pkt_now, summary = self.send_default_packet_to_unbound_port(unbound_port, bond_port, pkt_count=pkt_count, **slaves)

        self.verify(pkt_now[bond_port][0] == pkt_count * active_flag, "Not correct RX pkt on bond port in mode 1")
        if active_flag == 1:
            self.verify(pkt_now[primary_port][0] == pkt_count, "Not correct TX pkt on primary port in mode 1")
        for slave in slaves['inactive']:
            self.verify(pkt_now[slave][0] == 0, "Not correct TX pkt on inactive port in mode 1")
        for slave in [slave for slave in slaves['active'] if slave != primary_port]:
            self.verify(pkt_now[slave][0] == 0, "Not correct TX pkt on backup port in mode 1")

    def test_active_backup_rx_tx(self):
        """
        Verify receiving and transmitting the packets correctly in the active-backup mode.
        """
        bond_port = self.create_bonded_device(MODE_ACTIVE_BACKUP, SOCKET_0)
        self.add_slave_to_bonding_device(bond_port, False, self.dut_ports[0], self.dut_ports[1], self.dut_ports[2])
        self.dut.send_expect("set portlist %d,%d" % (self.dut_ports[3], bond_port), "testpmd> ")
        self.start_all_ports()
        self.dut.send_expect("start", "testpmd> ")
        time.sleep(5)

        slaves = {}
        slaves['active'] = [self.dut_ports[0], self.dut_ports[1], self.dut_ports[2]]
        slaves['inactive'] = []
        self.verify_active_backup_rx(self.dut_ports[3], bond_port, **slaves)
        self.verify_active_backup_tx(self.dut_ports[3], bond_port, **slaves)

    def test_active_backup_change_primary(self):
        """
        Verify that receiving and transmitting the packets correctly in the active-backup mode,
        when you change the primary slave.
        """
        bond_port = self.create_bonded_device(MODE_ACTIVE_BACKUP, SOCKET_0)
        self.add_slave_to_bonding_device(bond_port, False, self.dut_ports[0], self.dut_ports[1], self.dut_ports[2])
        self.dut.send_expect("set portlist %d,%d" % (self.dut_ports[3], bond_port), "testpmd> ")
        self.start_all_ports()
        self.dut.send_expect("start", "testpmd> ")
        self.set_primary_for_bonding_device(bond_port, self.dut_ports[1])
        time.sleep(5)

        slaves = {}
        slaves['active'] = [self.dut_ports[1], self.dut_ports[0], self.dut_ports[2]]
        slaves['inactive'] = []
        self.verify_active_backup_rx(self.dut_ports[3], bond_port, **slaves)
        self.verify_active_backup_tx(self.dut_ports[3], bond_port, **slaves)

    def test_active_backup_one_slave_down(self):
        """
        Verify that receiving and transmitting the pcakets correctly in the active-backup mode,
        when bringing any one slave of the bonding device link down.
        """
        bond_port = self.create_bonded_device(MODE_ACTIVE_BACKUP, SOCKET_0)
        self.add_slave_to_bonding_device(bond_port, False, self.dut_ports[0], self.dut_ports[1], self.dut_ports[2])
        self.dut.send_expect("set portlist %d,%d" % (self.dut_ports[3], bond_port), "testpmd> ")
        self.start_all_ports()
        self.dut.send_expect("start", "testpmd> ")
        self.admin_tester_port(self.tester.get_local_port(self.dut_ports[0]), "down")
        primary_port = int(self.get_bond_primary(bond_port))

        try:
            slaves = {}
            active_slaves = [self.dut_ports[1], self.dut_ports[2]]
            active_slaves.remove(primary_port)
            slaves['active'] = [primary_port]
            slaves['active'].extend(active_slaves)
            slaves['inactive'] = [self.dut_ports[0]]
            self.verify_active_backup_rx(self.dut_ports[3], bond_port, **slaves)
            self.verify_active_backup_tx(self.dut_ports[3], bond_port, **slaves)
        finally:
            self.admin_tester_port(self.tester.get_local_port(self.dut_ports[0]), "up")

    def test_active_backup_all_slaves_down(self):
        """
        Verify that receiving and transmitting that packets correctly in the active-backup mode,
        when bringing all slaves of the bonding device link down.
        """
        bond_port = self.create_bonded_device(MODE_ACTIVE_BACKUP, SOCKET_0)
        self.add_slave_to_bonding_device(bond_port, False, self.dut_ports[0], self.dut_ports[1], self.dut_ports[2])
        self.dut.send_expect("set portlist %d,%d" % (self.dut_ports[3], bond_port), "testpmd> ")
        self.start_all_ports()
        self.dut.send_expect("start", "testpmd> ")
        self.admin_tester_port(self.tester.get_local_port(self.dut_ports[0]), "down")
        self.admin_tester_port(self.tester.get_local_port(self.dut_ports[1]), "down")
        self.admin_tester_port(self.tester.get_local_port(self.dut_ports[2]), "down")

        try:
            slaves = {}
            slaves['active'] = []
            slaves['inactive'] = [self.dut_ports[0], self.dut_ports[1], self.dut_ports[2]]
            self.verify_active_backup_rx(self.dut_ports[3], bond_port, **slaves)
            self.verify_active_backup_tx(self.dut_ports[3], bond_port, **slaves)
        finally:
            self.admin_tester_port(self.tester.get_local_port(self.dut_ports[0]), "up")
            self.admin_tester_port(self.tester.get_local_port(self.dut_ports[1]), "up")
            self.admin_tester_port(self.tester.get_local_port(self.dut_ports[2]), "up")

    def translate_mac_str_into_int(self, mac_str):
        """
        Translate the MAC type from the string into the int.
        """
        mac_hex = '0x'
        for mac_part in mac_str.split(':'):
            mac_hex += mac_part
        return int(mac_hex, 16)

    def mac_hash(self, dest_mac, src_mac):
        """
        Generate the hash value with the source and destination MAC.
        """
        dest_port_mac = self.translate_mac_str_into_int(dest_mac)
        src_port_mac = self.translate_mac_str_into_int(src_mac)
        src_xor_dest = dest_port_mac ^ src_port_mac
        xor_value_1 = src_xor_dest >> 32
        xor_value_2 = (src_xor_dest >> 16) ^ (xor_value_1 << 16)
        xor_value_3 = src_xor_dest ^ (xor_value_1 << 32) ^ (xor_value_2 << 16)
        return htons(xor_value_1 ^ xor_value_2 ^ xor_value_3)

    def translate_ip_str_into_int(self, ip_str):
        """
        Translate the IP type from the string into the int.
        """
        ip_part_list = ip_str.split('.')
        ip_part_list.reverse()
        num = 0
        ip_int = 0
        for ip_part in ip_part_list:
            ip_part_int = int(ip_part) << (num * 8)
            ip_int += ip_part_int
            num += 1
        return ip_int

    def ipv4_hash(self, dest_ip, src_ip):
        """
        Generate the hash value with the source and destination IP.
        """
        dest_ip_int = self.translate_ip_str_into_int(dest_ip)
        src_ip_int = self.translate_ip_str_into_int(src_ip)
        return htonl(dest_ip_int ^ src_ip_int)

    def udp_hash(self, dest_port, src_port):
        """
        Generate the hash value with the source and destination port.
        """
        return htons(dest_port ^ src_port)

    def policy_and_slave_hash(self, policy, **slaves):
        """
        Generate the hash value by the policy and active slave number.
        *** policy:'L2' , 'L23' or 'L34'
        *** slaves:
        ******* 'active'=[]
        ******* 'inactive'=[]
        """
        global S_MAC_IP_PORT
        source = S_MAC_IP_PORT

        global D_MAC_IP_PORT
        dest_mac = D_MAC_IP_PORT[0]
        dest_ip = D_MAC_IP_PORT[1]
        dest_port = D_MAC_IP_PORT[2]

        hash_values = []
        if len(slaves['active']) != 0:
            for src_mac, src_ip, src_port in source:
                if policy == "L2":
                    hash_value = self.mac_hash(dest_mac, src_mac)
                elif policy == "L23":
                    hash_value = self.mac_hash(dest_mac, src_mac) ^ self.ipv4_hash(dest_ip, src_ip)
                else:
                    hash_value = self.ipv4_hash(dest_ip, src_ip) ^ self.udp_hash(dest_port, src_port)

                if policy in ("L23", "L34"):
                    hash_value ^= hash_value >> 16
                hash_value ^= hash_value >> 8
                hash_value = hash_value % len(slaves['active'])
                hash_values.append(hash_value)

        return hash_values

    def slave_map_hash(self, port, order_ports):
        """
        Find the hash value by the given slave port id.
        """
        if len(order_ports) == 0:
            return None
        else:
            order_ports = order_ports.split()
            return order_ports.index(str(port))

    def verify_xor_rx(self, unbound_port, bond_port, **slaves):
        """
        Verify receiving the pcakets correctly in the XOR mode.
        Parameters:
        *** unbound_port: the unbonded port id
        *** bond_port: the bonded device port id
        *** slaves:
        ******* 'active'=[]
        ******* 'inactive'=[]
        """
        pkt_count = 100
        pkt_now = {}

        pkt_now, summary = self.send_default_packet_to_slave(unbound_port, bond_port, pkt_count=pkt_count, **slaves)

        for slave in slaves['active']:
            self.verify(pkt_now[slave][0] == pkt_count, "Slave have error RX packet in XOR")
        for slave in slaves['inactive']:
            self.verify(pkt_now[slave][0] == 0, "Slave have error RX packet in XOR")
        self.verify(pkt_now[unbound_port][0] == pkt_count * len(slaves['active']), "Unbonded device have error TX packet in XOR")

    def verify_xor_tx(self, unbound_port, bond_port, policy, vlan_tag=False, **slaves):
        """
        Verify that transmitting the packets correctly in the XOR mode.
        Parameters:
        *** unbound_port: the unbonded port id
        *** bond_port: the bonded device port id
        *** policy:'L2' , 'L23' or 'L34'
        *** vlan_tag:False or True
        *** slaves:
        ******* 'active'=[]
        ******* 'inactive'=[]
        """
        pkt_count = 100
        pkt_now = {}

        pkt_now, summary = self.send_customized_packet_to_unbound_port(unbound_port, bond_port, policy, vlan_tag=False, pkt_count=pkt_count, **slaves)

        hash_values = []
        hash_values = self.policy_and_slave_hash(policy, **slaves)

        order_ports = self.get_bond_active_slaves(bond_port)
        for slave in slaves['active']:
            slave_map_hash = self.slave_map_hash(slave, order_ports)
            self.verify(pkt_now[slave][0] == pkt_count * hash_values.count(slave_map_hash),
                        "XOR load balance transmit error on the link up port")
        for slave in slaves['inactive']:
            self.verify(pkt_now[slave][0] == 0,
                        "XOR load balance transmit error on the link down port")

    def test_xor_tx(self):
        """
        Verify that transmitting packets correctly in the XOR mode.
        """
        bond_port = self.create_bonded_device(MODE_XOR_BALANCE, SOCKET_0)
        self.add_slave_to_bonding_device(bond_port, False, self.dut_ports[0], self.dut_ports[1], self.dut_ports[2])
        self.dut.send_expect("set portlist %d,%d" % (self.dut_ports[3], bond_port), "testpmd> ")
        self.start_all_ports()
        self.dut.send_expect("start", "testpmd> ")

        slaves = {}
        slaves['active'] = [self.dut_ports[0], self.dut_ports[1], self.dut_ports[2]]
        slaves['inactive'] = []

        self.verify_xor_tx(self.dut_ports[3], bond_port, "L2", False, **slaves)

    def test_xor_tx_one_slave_down(self):
        """
        Verify that transmitting packets correctly in the XOR mode,
        when bringing any one slave of the bonding device link down.
        """
        bond_port = self.create_bonded_device(MODE_XOR_BALANCE, SOCKET_0)
        self.add_slave_to_bonding_device(bond_port, False, self.dut_ports[0], self.dut_ports[2], self.dut_ports[1])
        self.dut.send_expect("set portlist %d,%d" % (self.dut_ports[3], bond_port), "testpmd> ")
        self.start_all_ports()
        self.dut.send_expect("start", "testpmd> ")
        self.admin_tester_port(self.tester.get_local_port(self.dut_ports[0]), "down")

        try:
            slaves = {}
            slaves['active'] = [self.dut_ports[1], self.dut_ports[2]]
            slaves['inactive'] = [self.dut_ports[0]]

            self.verify_xor_tx(self.dut_ports[3], bond_port, "L2", False, **slaves)
        finally:
            self.admin_tester_port(self.tester.get_local_port(self.dut_ports[0]), "up")

    def test_xor_tx_all_slaves_down(self):
        """
        Verify that transmitting packets correctly in the XOR mode,
        when bringing all slaves of the bonding device link down.
        """
        bond_port = self.create_bonded_device(MODE_XOR_BALANCE, SOCKET_0)
        self.add_slave_to_bonding_device(bond_port, False, self.dut_ports[0], self.dut_ports[1], self.dut_ports[2])
        self.dut.send_expect("set portlist %d,%d" % (self.dut_ports[3], bond_port), "testpmd> ")
        self.start_all_ports()
        self.dut.send_expect("start", "testpmd> ")
        self.admin_tester_port(self.tester.get_local_port(self.dut_ports[0]), "down")
        self.admin_tester_port(self.tester.get_local_port(self.dut_ports[1]), "down")
        self.admin_tester_port(self.tester.get_local_port(self.dut_ports[2]), "down")

        try:
            slaves = {}
            slaves['active'] = []
            slaves['inactive'] = [self.dut_ports[0], self.dut_ports[1], self.dut_ports[2]]

            self.verify_xor_tx(self.dut_ports[3], bond_port, "L2", False, **slaves)
        finally:
            self.admin_tester_port(self.tester.get_local_port(self.dut_ports[0]), "up")
            self.admin_tester_port(self.tester.get_local_port(self.dut_ports[1]), "up")
            self.admin_tester_port(self.tester.get_local_port(self.dut_ports[2]), "up")

    def vlan_strip_and_filter(self, action='off', *ports):
        """
        Open or shutdown the vlan strip and filter option of specified port.
        """
        for port_id in ports:
            self.dut.send_expect("vlan set strip %s %d" % (action, port_id), "testpmd> ")
            self.dut.send_expect("vlan set filter %s %d" % (action, port_id), "testpmd> ")

    def test_xor_l34_forward(self):
        """
        Verify that transmitting packets correctly in the XOR mode,
        when choosing the l34 as the load balance policy.
        """
        bond_port = self.create_bonded_device(MODE_XOR_BALANCE, SOCKET_0)
        self.add_slave_to_bonding_device(bond_port, False, self.dut_ports[0], self.dut_ports[1], self.dut_ports[2])
        self.dut.send_expect("set portlist %d,%d" % (self.dut_ports[3], bond_port), "testpmd> ")
        self.set_balance_policy_for_bonding_device(bond_port, "l34")
        self.start_all_ports()
        self.dut.send_expect("start", "testpmd> ")

        slaves = {}
        slaves['active'] = [self.dut_ports[0], self.dut_ports[1], self.dut_ports[2]]
        slaves['inactive'] = []

        self.verify_xor_tx(self.dut_ports[3], bond_port, "L34", False, **slaves)
        self.vlan_strip_and_filter('off', self.dut_ports[0], self.dut_ports[1], self.dut_ports[2], self.dut_ports[3], bond_port)
        self.verify_xor_tx(self.dut_ports[3], bond_port, "L34", True, **slaves)

    def test_xor_rx(self):
        """
        Verify that receiving packets correctly in the XOR mode.
        """
        bond_port = self.create_bonded_device(MODE_XOR_BALANCE, SOCKET_0)
        self.add_slave_to_bonding_device(bond_port, False, self.dut_ports[0], self.dut_ports[1], self.dut_ports[2])
        self.dut.send_expect("set portlist %d,%d" % (self.dut_ports[3], bond_port), "testpmd> ")
        self.start_all_ports()
        self.dut.send_expect("start", "testpmd> ")

        slaves = {}
        slaves['active'] = [self.dut_ports[0], self.dut_ports[1], self.dut_ports[2]]
        slaves['inactive'] = []

        self.verify_xor_rx(self.dut_ports[3], bond_port, **slaves)

    def verify_broadcast_rx(self, unbound_port, bond_port, **slaves):
        """
        Verify that receiving packets correctly in the broadcast mode.
        Parameters:
        *** unbound_port: the unbonded port id
        *** bond_port: the bonded device port id
        *** slaves:
        ******* 'active':[]
        ******* 'inactive':[]
        """
        pkt_count = 100
        pkt_now = {}

        pkt_now, summary = self.send_default_packet_to_slave(unbound_port, bond_port, pkt_count=pkt_count, **slaves)

        for slave in slaves['active']:
            self.verify(pkt_now[slave][0] == pkt_count, "Slave RX packet not correct in mode 3")
        for slave in slaves['inactive']:
            self.verify(pkt_now[slave][0] == 0, "Slave RX packet not correct in mode 3")
        self.verify(pkt_now[unbound_port][0] == pkt_count * len(slaves['active']),
                    "Unbonded port TX packet not correct in mode 3")
        self.verify(pkt_now[bond_port][0] == pkt_count * len(slaves['active']),
                    "Bonded device RX packet not correct in mode 3")

    def verify_broadcast_tx(self, unbound_port, bond_port, **slaves):
        """
        Verify that transmitting packets correctly in the broadcast mode.
        Parameters:
        *** unbound_port: the unbonded port id
        *** bond_port: the bonded device port id
        *** slaves:
        ******* 'actvie':[]
        ******* 'inactive':[]
        """
        pkt_count = 100
        pkt_now = {}

        pkt_now, summary = self.send_default_packet_to_unbound_port(unbound_port, bond_port, pkt_count=pkt_count, **slaves)

        for slave in slaves['active']:
            self.verify(pkt_now[slave][0] == pkt_count, "Slave TX packet not correct in mode 3")
        for slave in slaves['inactive']:
            self.verify(pkt_now[slave][0] == 0, "Slave TX packet not correct in mode 3")
        self.verify(pkt_now[unbound_port][0] == pkt_count, "Unbonded port RX packet not correct in mode 3")
        self.verify(pkt_now[bond_port][0] == pkt_count * len(slaves['active']),
                    "Bonded device TX packet not correct in mode 3")

    def test_broadcast_rx_tx(self):
        """
        Verify receiving and transmitting packets correctly in the broadcast mode.
        """
        bond_port = self.create_bonded_device(MODE_BROADCAST, SOCKET_0)
        self.add_slave_to_bonding_device(bond_port, False, self.dut_ports[0], self.dut_ports[1], self.dut_ports[2])
        self.dut.send_expect("set portlist %d,%d" % (self.dut_ports[3], bond_port), "testpmd> ")
        self.start_all_ports()
        self.dut.send_expect("start", "testpmd> ")

        slaves = {}
        slaves['active'] = [self.dut_ports[0], self.dut_ports[1], self.dut_ports[2]]
        slaves['inactive'] = []

        self.verify_broadcast_rx(self.dut_ports[3], bond_port, **slaves)
        self.verify_broadcast_tx(self.dut_ports[3], bond_port, **slaves)

    def test_broadcast_tx_one_slave_down(self):
        """
        Verify that transmitting packets correctly in the broadcast mode,
        when bringing any one slave of the bonding device link down.
        """
        bond_port = self.create_bonded_device(MODE_BROADCAST, SOCKET_0)
        self.add_slave_to_bonding_device(bond_port, False, self.dut_ports[0], self.dut_ports[1], self.dut_ports[2])
        self.dut.send_expect("set portlist %d,%d" % (self.dut_ports[3], bond_port), "testpmd> ")
        self.start_all_ports()
        self.dut.send_expect("start", "testpmd> ")
        self.admin_tester_port(self.tester.get_local_port(self.dut_ports[0]), "down")

        try:
            slaves = {}
            slaves['active'] = [self.dut_ports[1], self.dut_ports[2]]
            slaves['inactive'] = [self.dut_ports[0]]

            self.verify_broadcast_tx(self.dut_ports[3], bond_port, **slaves)
        finally:
            self.admin_tester_port(self.tester.get_local_port(self.dut_ports[0]), "up")

    def test_broadcast_tx_all_slaves_down(self):
        """
        Verify that transmitting packets correctly in the broadcast mode,
        when bringing all slaves of the bonding device link down.
        """
        bond_port = self.create_bonded_device(MODE_BROADCAST, SOCKET_0)
        self.add_slave_to_bonding_device(bond_port, False, self.dut_ports[0], self.dut_ports[1], self.dut_ports[2])
        self.dut.send_expect("set portlist %d,%d" % (self.dut_ports[3], bond_port), "testpmd> ")
        self.start_all_ports()
        self.dut.send_expect("start", "testpmd> ")
        self.admin_tester_port(self.tester.get_local_port(self.dut_ports[0]), "down")
        self.admin_tester_port(self.tester.get_local_port(self.dut_ports[1]), "down")
        self.admin_tester_port(self.tester.get_local_port(self.dut_ports[2]), "down")

        try:
            slaves = {}
            slaves['active'] = []
            slaves['inactive'] = [self.dut_ports[0], self.dut_ports[1], self.dut_ports[2]]

            self.verify_broadcast_tx(self.dut_ports[3], bond_port, **slaves)
        finally:
            self.admin_tester_port(self.tester.get_local_port(self.dut_ports[0]), "up")
            self.admin_tester_port(self.tester.get_local_port(self.dut_ports[1]), "up")
            self.admin_tester_port(self.tester.get_local_port(self.dut_ports[2]), "up")

    def verify_lacp_rx(self, unbound_port, bond_port, **slaves):
        """
        Verify that receiving packets correctly in the mode 4.
        Parameters:
        *** unbound_port: the unbonded port id
        *** bond_port: the bonded device port id
        *** slaves:
        ******* 'active':[]
        ******* 'inactive':[]
        """
        pkt_count = 100
        pkt_now = {}
        summary = 0

        if len(slaves['active']):
            active_flag = 1
        else:
            active_flag = 0

        pkt_now, summary = self.send_customized_packet_to_bond_port(unbound_port, bond_port, self.tester_bond, pkt_count, **slaves)

        active_summary = 0
        for slave in slaves['active']:
            active_summary += pkt_now[slave][0]
        self.verify(active_summary >= summary * active_flag,
                    "Active slave have incorrect RX packet number in LACP")
        for slave in slaves['inactive']:
            self.verify(pkt_now[slave][0] == 0,
                        "Inactive slave have incorrect RX packet number in LACP")
        self.dut.send_expect("show port info %d" % self.dut_ports[3], "testpmd> ")
        self.verify(pkt_now[unbound_port][0] == summary * active_flag,
                    "Unbonded device has incorrect TX packet number in LACP")

    def verify_lacp_tx(self, unbound_port, bond_port, policy, vlan_tag=False, **slaves):
        """
        Verify that transmitting the packets correctly in the XOR mode.
        Parameters:
        *** unbound_port: the unbonded port id
        *** bond_port: the bonded device port id
        *** policy:'L2' , 'L23' or 'L34'
        *** vlan_tag:False or True
        *** slaves:
        ******* 'active'=[]
        ******* 'inactive'=[]
        """
        pkt_count = 100
        pkt_now = {}

        pkt_now, summary = self.send_customized_packet_to_unbound_port(unbound_port, bond_port, policy, vlan_tag=False, pkt_count=pkt_count, **slaves)

        hash_values = []
        hash_values = self.policy_and_slave_hash(policy, **slaves)

        order_ports = self.get_bond_active_slaves(bond_port)
        for slave in slaves['active']:
            slave_map_hash = self.slave_map_hash(slave, order_ports)
            self.verify(pkt_now[slave][0] >= pkt_count * hash_values.count(slave_map_hash),
                        "LACP load balance transmit incorrectly on the link up port")
        for slave in slaves['inactive']:
            self.verify(pkt_now[slave][0] == 0,
                        "LACP load balance transmit incorrectly on the link down port")
        self.verify(pkt_now[unbound_port][0] == summary,
                    "LACP load balance receive incorrectly on the unbound port")

    def add_linux_bond_device(self, bond_mode, bond_name='bond0', *tester_local_ports):
        if self.tester.get_os_type() == "linux":
            self.tester.send_expect("modprobe bonding mode=%d miimon=100" %
                                    int(bond_mode), "# ")
            self.tester.send_expect("ifconfig %s up" % bond_name, "# ")

            tester_bond_intfs = [self.tester.get_interface(port) for port in tester_local_ports]
            for intf in tester_bond_intfs:
                self.tester.send_expect("ifenslave -f %s %s" %
                                        (bond_name, intf), "# ")
                if not self.slave_is_here_linux(bond_name, intf):
                    self.verify(False, "Add linux bond device failed")
            for port in tester_local_ports:
                self.admin_tester_port(port, "up")
        else:
            self.verify(False,
                        "Not support to verify LACP on OS %s" % self.tester.get_os_type())

    def detach_linux_bond_device(self, bond_name='bond0', *tester_local_ports):
        tester_bond_intf = [self.tester.get_interface(port) for port in tester_local_ports]
        if self.tester.get_os_type() == "linux":
            for intf in tester_bond_intf:
                if self.slave_is_here_linux(bond_name, intf):
                    self.tester.send_expect("ifenslave -d %s %s" % (bond_name, intf),
                                            "# ")
                if self.slave_is_here_linux(bond_name, intf):
                    self.verify(False, "Delete linux bond device failed")
            for port in tester_local_ports:
                self.admin_tester_port(port, "up")
        else:
            self.verify(False,
                        "Not support to verify LACP on OS %s" % self.tester.get_os_type())

    def slave_is_here_linux(self, bond_name="bond0", *interfaces):
        out = self.tester.send_expect("cat /proc/net/bonding/%s" % bond_name,
                                      "# ")
        for intf in interfaces:
            if re.search(intf, out):
                return True
            else:
                return False

    def setup_and_clear_lacp(func):
        """
        Setting lacp test environment on tester.
        """
        @wraps(func)
        def test_env(*args, **kwargs):
            pmd_bond_instance = args[0]
            try:
                dut_ports = [pmd_bond_instance.dut_ports[port] for port in [0, 1, 2]]
                tester = pmd_bond_instance.tester
                tester_local_ports = [tester.get_local_port(port) for port in dut_ports]

                pmd_bond_instance.add_linux_bond_device(MODE_LACP,
                                                        pmd_bond_instance.tester_bond,
                                                        *tester_local_ports)

                func(*args, **kwargs)
            finally:
                pmd_bond_instance.detach_linux_bond_device(pmd_bond_instance.tester_bond,
                                                           *tester_local_ports)

        return test_env

    def just_clear_lacp(func):
        """

        """
        @wraps(func)
        def clear_env(*args, **kwargs):
            pmd_bond_instance = args[0]
            try:
                dut_ports = [pmd_bond_instance.dut_ports[port] for port in [0, 1, 2]]
                tester = pmd_bond_instance.tester
                tester_local_ports = [tester.get_local_port(port) for port in dut_ports]

                func(*args, **kwargs)
            finally:
                pmd_bond_instance.detach_linux_bond_device(pmd_bond_instance.tester_bond,
                                                           *tester_local_ports)
        return clear_env

    def verify_tlb_rx(self, unbound_port, bond_port, **slaves):
        """
        Verify that receiving packets correctly in the mode 4.
        Parameters:
        *** unbound_port: the unbonded port id
        *** bond_port: the bonded device port id
        *** slaves:
        ******* 'active':[]
        ******* 'inactive':[]
        """
        pkt_count = 100
        pkt_now = {}

        slave_num = slaves['active'].__len__()
        if slave_num != 0:
            active_flag = 1
        else:
            active_flag = 0

        pkt_now, summary = self.send_default_packet_to_slave(unbound_port, bond_port, pkt_count=pkt_count, **slaves)

        self.verify(pkt_now[unbound_port][0] == pkt_count * active_flag, "Unbonded device has error TX packet in TLB")
        self.verify(pkt_now[bond_port][0] == pkt_count * slave_num, "Bounded device has error RX packet in TLB")
        for slave in slaves['inactive']:
            self.verify(pkt_now[slave][0] == 0, "Inactive slave has error RX packet in TLB")
        for slave in slaves['active']:
            self.verify(pkt_now[slave][0] == pkt_count, "Active slave has error RX packet in TLB")

    def verify_tlb_tx(self, unbound_port, bond_port, **slaves):
        """
        Verify that transmitting packets correctly in the broadcast mode.
        Parameters:
        *** unbound_port: the unbonded port id
        *** bond_port: the bonded device port id
        *** slaves:
        ******* 'actvie':[]
        ******* 'inactive':[]
        """
        pkt_count = 'MANY'
        pkt_now = {}

        # send to unbonded device
        pkt_now, summary = self.send_default_packet_to_unbound_port(unbound_port, bond_port, pkt_count=pkt_count, **slaves)

        active_slaves = len(slaves['active'])
        if active_slaves:
            mean = float(summary) / float(active_slaves)
            active_flag = 1
        else:
            active_flag = 0

        for slave in slaves['active']:
            self.verify(pkt_now[slave][0] > mean * 0.9 and
                        pkt_now[slave][0] < mean * 1.1,
                        "Slave TX packet not correct in mode 5")
        for slave in slaves['inactive']:
            self.verify(pkt_now[slave][0] == 0, "Slave TX packet not correct in mode 5")
        self.verify(pkt_now[unbound_port][0] == summary,
                    "Unbonded port RX packet not correct in TLB")
        self.verify(pkt_now[bond_port][0] == summary * active_flag,
                    "Bonded device TX packet not correct in TLB")

    def test_tlb_basic(self):
        self.verify_bound_basic_opt(MODE_TLB_BALANCE)
        self.verify_bound_mac_opt(MODE_TLB_BALANCE)
        self.verify_bound_promisc_opt(MODE_TLB_BALANCE)

    def test_tlb_rx_tx(self):
        bond_port = self.create_bonded_device(MODE_TLB_BALANCE, SOCKET_0)
        self.add_slave_to_bonding_device(bond_port, False,
                                         self.dut_ports[0],
                                         self.dut_ports[1],
                                         self.dut_ports[2])
        self.dut.send_expect("set portlist %d,%d" % (self.dut_ports[3], bond_port), "testpmd> ")
        self.start_all_ports()
        self.dut.send_expect("start", "testpmd> ")

        slaves = {}
        slaves['active'] = [self.dut_ports[0], self.dut_ports[1], self.dut_ports[2]]
        slaves['inactive'] = []

        self.verify_tlb_rx(self.dut_ports[3], bond_port, **slaves)
        self.verify_tlb_tx(self.dut_ports[3], bond_port, **slaves)

    def test_tlb_one_slave_dwon(self):
        bond_port = self.create_bonded_device(MODE_TLB_BALANCE, SOCKET_0)
        self.add_slave_to_bonding_device(bond_port, False,
                                         self.dut_ports[0],
                                         self.dut_ports[1],
                                         self.dut_ports[2])
        self.dut.send_expect("set portlist %d,%d" % (self.dut_ports[3], bond_port), "testpmd> ")
        self.start_all_ports()
        self.dut.send_expect("start", "testpmd> ")
        self.admin_tester_port(self.tester.get_local_port(self.dut_ports[0]), "down")

        try:
            slaves = {}
            slaves['active'] = [self.dut_ports[1], self.dut_ports[2]]
            slaves['inactive'] = [self.dut_ports[0]]

            self.verify_tlb_rx(self.dut_ports[3], bond_port, **slaves)
            self.verify_tlb_tx(self.dut_ports[3], bond_port, **slaves)
        finally:
            self.admin_tester_port(self.tester.get_local_port(self.dut_ports[0]), "up")

    def test_tlb_all_slaves_down(self):
        bond_port = self.create_bonded_device(MODE_TLB_BALANCE, SOCKET_0)
        self.add_slave_to_bonding_device(bond_port, False,
                                         self.dut_ports[0],
                                         self.dut_ports[1],
                                         self.dut_ports[2])
        self.dut.send_expect("set portlist %d,%d" % (self.dut_ports[3], bond_port), "testpmd> ")
        self.start_all_ports()
        self.dut.send_expect("start", "testpmd> ")
        self.admin_tester_port(self.tester.get_local_port(self.dut_ports[0]), "down")
        self.admin_tester_port(self.tester.get_local_port(self.dut_ports[1]), "down")
        self.admin_tester_port(self.tester.get_local_port(self.dut_ports[2]), "down")

        try:
            slaves = {}
            slaves['active'] = []
            slaves['inactive'] = [self.dut_ports[0], self.dut_ports[1], self.dut_ports[2]]

            self.verify_tlb_rx(self.dut_ports[3], bond_port, **slaves)
            self.verify_tlb_tx(self.dut_ports[3], bond_port, **slaves)
        finally:
            self.admin_tester_port(self.tester.get_local_port(self.dut_ports[0]), "up")
            self.admin_tester_port(self.tester.get_local_port(self.dut_ports[1]), "up")
            self.admin_tester_port(self.tester.get_local_port(self.dut_ports[2]), "up")

    def tear_down(self):
        """
        Run after each test case.
        """
        self.dut.send_expect("quit", "# ")

    def tear_down_all(self):
        """
        Run after each test suite.
        """
        pass
