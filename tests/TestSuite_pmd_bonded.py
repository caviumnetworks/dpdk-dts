# <COPYRIGHT_TAG>

"""
DPDK Test suite.


Test userland 10Gb PMD.

"""

import time
import re
import random
from socket import htons, htonl
import pdb

import dcts
from test_case import TestCase

#
#
# Test class.
#


class TestPmdBonded(TestCase):

    #
    #
    # Utility methods and other non-test code.
    #
    # Insert or move non-test functions here.

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

    def send_packet(self, port_id, frame_size=64, count=1, reverse_verify=False, **ether_ip):
        """
        Send count packet to portid
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

        gp0rx_pkts, gp0rx_err, gp0rx_bytes = [int(_) for _ in self.get_stats(self.dut_ports[port_id], "rx")]

        itf = self.tester.get_interface(self.tester.get_local_port(self.dut_ports[port_id]))

        if not ether_ip.get('ether'):
            dest_mac = self.dut.get_mac_address(self.dut_ports[port_id])
            src_mac = "52:00:00:00:00:00"
        else:
            if not ether_ip['ether'].get('dest_mac'):
                dest_mac = self.dut.get_mac_address(self.dut_ports[port_id])
            else:
                dest_mac = ether_ip['ether']['dest_mac']
            if not ether_ip['ether'].get('src_mac'):
                src_mac = "52:00:00:00:00:00"
            else:
                src_mac = ether_ip["ether"]["src_mac"]

        if not ether_ip.get('dot1q'):
            pass
        else:
            if not ether_ip['dot1q'].get('vlan'):
                vlan = '1'
            else:
                vlan = ether_ip['dot1q']['vlan']

        if not ether_ip.get('ip'):
            dest_ip = "10.239.129.88"
            src_ip = "10.239.129.65"
        else:
            if not ether_ip['ip'].get('dest_ip'):
                dest_ip = "10.239.129.88"
            else:
                dest_ip = ether_ip['ip']['dest_ip']
            if not ether_ip['ip'].get('src_ip'):
                src_ip = "10.239.129.65"
            else:
                src_ip = ether_ip['ip']['src_ip']

        if not ether_ip.get('udp'):
            dest_port = 53
            src_port = 53
        else:
            if not ether_ip['udp'].get('dest_port'):
                dest_port = 53
            else:
                dest_port = ether_ip['udp']['dest_port']
            if not ether_ip['udp'].get('src_port'):
                src_port = 53
            else:
                src_port = ether_ip['udp']['src_port']

        pktlen = frame_size - 18
        padding = pktlen - 20

        self.tester.scapy_foreground()
        self.tester.scapy_append('nutmac="%s"' % dest_mac)
        self.tester.scapy_append('srcmac="%s"' % src_mac)

        if ether_ip.get('dot1q'):
            self.tester.scapy_append('vlanvalue=%d' % vlan)
        self.tester.scapy_append('destip="%s"' % dest_ip)
        self.tester.scapy_append('srcip="%s"' % src_ip)
        self.tester.scapy_append('destport=%d' % dest_port)
        self.tester.scapy_append('srcport=%d' % src_port)
        if not ether_ip.get('dot1q'):
            self.tester.scapy_append('sendp([Ether(dst=nutmac, src=srcmac)/IP(dst=destip, src=srcip, len=%s)/\
UDP(sport=srcport, dport=destport)/Raw(load="\x50"*%s)], iface="%s", count=%d)' % (pktlen, padding, itf, count))
        else:
            self.tester.scapy_append('sendp([Ether(dst=nutmac, src=srcmac)/Dot1Q(vlan=vlanvalue)/IP(dst=destip, src=srcip, len=%s)/\
UDP(sport=srcport, dport=destport)/Raw(load="\x50"*%s)], iface="%s", count=%d)' % (pktlen, padding, itf, count))

        out = self.tester.scapy_execute()
        time.sleep(.5)

        p0rx_pkts, p0rx_err, p0rx_bytes = [int(_) for _ in self.get_stats(self.dut_ports[port_id], "rx")]

        p0rx_pkts -= gp0rx_pkts

        if not reverse_verify:
            self.verify(p0rx_pkts == count, "Data not received by port")
        else:
            self.verify(p0rx_pkts == 0, "Data received by port,should not received")
        return out

    #
    #
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

        self.dut_ports = self.dut.get_ports(self.nic)

        self.port_mask = dcts.create_mask(self.dut_ports)

        self.verify(len(self.dut_ports) >= 4, "Insufficient ports")

        self.ports_socket = self.dut.get_numa_id(self.dut_ports[0])

        self.all_cores_mask = dcts.create_mask(self.dut.get_core_list("all"))

    def set_up(self):
        """
        Run before each test case.
        """
        pass

    def get_value_from_str(self, key_str, regx_str, string):
        pattern = r"(?<=%s)%s" % (key_str, regx_str)
        s = re.compile(pattern)
        res = s.search(string)
        if type(res).__name__ == 'NoneType':
            return ' '
        else:
            return res.group(0)

    def get_detail_from_port_info(self, key_str, regx_str, port):
        out = self.dut.send_expect("show port info %d" % port, "testpmd> ")
        find_value = self.get_value_from_str(key_str, regx_str, out)
        return find_value

    def get_port_mac(self, port_id):
        return self.get_detail_from_port_info("MAC address: ", "([0-9A-F]{2}:){5}[0-9A-F]{2}", port_id)

    def get_port_connect_socket(self, port_id):
        return self.get_detail_from_port_info("Connect to socket: ", "\d+", port_id)

    def get_port_memory_socket(self, port_id):
        return self.get_detail_from_port_info("memory allocation on the socket: ", "\d+", port_id)

    def get_port_link_status(self, port_id):
        return self.get_detail_from_port_info("Link status: ", "\d+", port_id)

    def get_port_link_speed(self, port_id):
        return self.get_detail_from_port_info("Link speed: ", "\d+", port_id)

    def get_port_link_duplex(self, port_id):
        return self.get_detail_from_port_info("Link duplex: ", "\S+", port_id)

    def get_port_promiscuous_mode(self, port_id):
        return self.get_detail_from_port_info("Promiscuous mode: ", "\S+", port_id)

    def get_port_allmulticast_mode(self, port_id):
        return self.get_detail_from_port_info("Allmulticast mode: ", "\S+", port_id)

    def get_port_vlan_offload(self, port_id):
        """
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
        out = self.dut.send_expect("show bonding config %d" % bond_port, "testpmd> ")
        find_value = self.get_value_from_str(key_str, regx_str, out)
        return find_value

    def get_bond_mode(self, bond_port):
        return self.get_info_from_bond_config("Bonding mode: ", "\d*", bond_port)

    def get_bond_balance_policy(self, bond_port):
        return self.get_info_from_bond_config("Balance Xmit Policy: ", "\S+", bond_port)

    def get_bond_slaves(self, bond_port):
        try:
            return self.get_info_from_bond_config("Slaves \(\d\): \[", "\d*( \d*)*", bond_port)
        except Exception as e:
            return self.get_info_from_bond_config("Slaves: \[", "\d*( \d*)*", bond_port)

    def get_bond_active_slaves(self, bond_port):
        try:
            return self.get_info_from_bond_config("Active Slaves \(\d\): \[", "\d*( \d*)*", bond_port)
        except Exception as e:
            return self.get_info_from_bond_config("Acitve Slaves: \[", "\d*( \d*)*", bond_port)

    def get_bond_primary(self, bond_port):
        return self.get_info_from_bond_config("Primary: \[", "\d*", bond_port)

    def launch_app(self, cmd_param="-c 0xf -n 4 -- -i"):
        app_path = "./%s/app/testpmd" % self.target
        self.dut.send_expect(app_path + ' ' + cmd_param, "testpmd> ", 120)

    def create_bonded_device(self, mode=0, socket=0, verify_detail=False):
        out = self.dut.send_expect("create bonded device %d %d" % (mode, socket), "testpmd> ")
        self.verify("Created new bonded device" in out, "Create bonded device on mode [%d] socket [%d] failed" % (mode, socket))
        bond_port = self.get_value_from_str("Created new bonded device eth_bond_testpmd_[\d] on \(port ", "\d+", out)
        bond_port = int(bond_port)

        if verify_detail:
            out = self.dut.send_expect("show bonding config %d" % bond_port, "testpmd> ")
            self.verify("Bonding mode: %d" % mode in out, "Bonding mode display error when create bonded device")
            self.verify("Slaves: []" in out, "Slaves display error when create bonded device")
            self.verify("Active Slaves: []" in out, "Active Slaves display error when create bonded device")
            self.verify("Primary: []" not in out, "Primary display error when create bonded device")

            out = self.dut.send_expect("show port info %d" % bond_port, "testpmd> ")
            self.verify("Connect to socket: %d" % socket in out, "Bonding port connect socket error")
            self.verify("Link status: down" in out, "Bonding port default link status error")
            self.verify("Link speed: 0 Mbps" in out, "Bonding port default link speed error")

        return bond_port

    def start_all_ports(self):
        self.dut.send_expect("port start all", "testpmd> ")
        time.sleep(5)

    def add_slave_to_bonding_device(self, bond_port, reverse_verify=False, *slave_port):
        if len(slave_port) <= 0:
            dcts.RED("No port exist when add slave to bonded device")
        for slave_id in slave_port:
            self.dut.send_expect("add bonding slave %d %d" % (slave_id, bond_port), "testpmd> ")

            slaves = self.get_info_from_bond_config("Slaves \(\d\): \[", "\d*( \d*)*", bond_port)
            if not reverse_verify:
                self.verify(str(slave_id) in slaves, "Add port as bonding slave failed")
            else:
                self.verify(str(slave_id) not in slaves, "Add port as bonding slave successfully,should fail")

    def remove_slave_from_bonding_device(self, bond_port, reverse_verify=False, *slave_port):
        if len(slave_port) <= 0:
            dcts.RED("No port exist when remove slave from bonded device")
        for slave_id in slave_port:
            self.dut.send_expect("remove bonding slave %d %d" % (slave_id, bond_port), "testpmd> ")
            out = self.get_info_from_bond_config("Slaves: \[", "\d*( \d*)*", bond_port)
            if not reverse_verify:
                self.verify(str(slave_id) not in out, "Remove slave to fail from bonding device")
            else:
                self.verify(str(slave_id) in out, "Remove slave successfully from bonding device,should be failed")

    def set_primary_for_bonding_device(self, bond_port, slave_port, reverse_verify=False):
        self.dut.send_expect("set bonding primary %d %d" % (slave_port, bond_port), "testpmd> ")
        out = self.get_info_from_bond_config("Primary: \[", "\d*", bond_port)
        if not reverse_verify:
            self.verify(str(slave_port) in out, "Set bonding primary port failed")
        else:
            self.verify(str(slave_port) not in out, "Set bonding primary port successfully,should not success")

    def set_mode_for_bonding_device(self, bond_port, mode):
        self.dut.send_expect("set bonding mode %d %d" % (mode, bond_port), "testpmd> ")
        mode_value = self.get_bond_mode(bond_port)
        self.verify(str(mode) in mode_value, "Set bonding mode failed")

    def set_mac_for_bonding_device(self, bond_port, mac):
        self.dut.send_expect("set bonding mac_addr %s %s" % (bond_port, mac), "testpmd> ")
        new_mac = self.get_port_mac(bond_port)
        self.verify(new_mac == mac, "Set bonding mac failed")

    def set_balance_policy_for_bonding_device(self, bond_port, policy):
        self.dut.send_expect("set bonding balance_xmit_policy %d %s" % (bond_port, policy), "testpmd> ")
        new_policy = self.get_bond_balance_policy(bond_port)
        policy = "BALANCE_XMIT_POLICY_LAYER" + policy.lstrip('l')
        self.verify(new_policy == policy, "Set bonding balance policy failed")

    def test_create_bonded_devices_and_slaves(self):
        """
        Create bonded devices and slaves.
        """
        self.launch_app()
        bond_port_0 = self.create_bonded_device(1, 0, True)
        self.add_slave_to_bonding_device(bond_port_0, False, self.dut_ports[1])
        self.start_all_ports()
        mode_value = self.get_bond_mode(bond_port_0)
        self.verify('1' in mode_value, "Bonding mode show error")
        slaves = self.get_bond_slaves(bond_port_0)
        self.verify(str(self.dut_ports[1]) in slaves, "Bonding slaves show error")
        primary = self.get_bond_primary(bond_port_0)
        self.verify(str(self.dut_ports[1]) in primary, "Bonding primary show error")

        bond_port_1 = self.create_bonded_device(1, 0)
        self.add_slave_to_bonding_device(bond_port_0, False, self.dut_ports[0])
        self.add_slave_to_bonding_device(bond_port_1, True, self.dut_ports[0])

        self.set_mode_for_bonding_device(bond_port_0, 3)
        self.add_slave_to_bonding_device(bond_port_0, False, self.dut_ports[2])
        time.sleep(5)
        self.set_primary_for_bonding_device(bond_port_0, self.dut_ports[2])

        self.remove_slave_from_bonding_device(bond_port_0, False, self.dut_ports[1])
        self.remove_slave_from_bonding_device(bond_port_0, False, self.dut_ports[0])
        self.remove_slave_from_bonding_device(bond_port_0, False, self.dut_ports[2])

    def test_bonded_mac_address(self):
        """
        Create bonded device, add one slave, verify bonded device MAC address is the slave's MAC.
        """
        self.launch_app()
        bond_port = self.create_bonded_device(3, 1)
        self.add_slave_to_bonding_device(bond_port, False, self.dut_ports[1])
        mac_address_0_orig = self.get_port_mac(self.dut_ports[0])
        mac_address_1_orig = self.get_port_mac(self.dut_ports[1])
        mac_address_2_orig = self.get_port_mac(self.dut_ports[2])
        mac_address_3_orig = self.get_port_mac(self.dut_ports[3])
        mac_address_bond_orig = self.get_port_mac(bond_port)
        self.verify(mac_address_1_orig == mac_address_bond_orig, "Bonded device MAC address not same with first slave MAC")

        self.add_slave_to_bonding_device(bond_port, False, self.dut_ports[2])
        mac_address_2_now = self.get_port_mac(self.dut_ports[2])
        mac_address_bond_now = self.get_port_mac(bond_port)
        self.verify(mac_address_1_orig == mac_address_bond_now and mac_address_bond_now == mac_address_2_now,
                    "NOT all slaves MAC address same with bonding device")

        new_mac = "00:11:22:00:33:44"
        self.set_mac_for_bonding_device(bond_port, new_mac)
        mac_address_1_now = self.get_port_mac(self.dut_ports[1])
        mac_address_2_now = self.get_port_mac(self.dut_ports[2])
        mac_address_bond_now = self.get_port_mac(bond_port)
        self.verify(mac_address_1_now == mac_address_2_now == mac_address_bond_now == new_mac,
                    "Set mac failed for bonding device")

        self.dut.send_expect("port start %d" % bond_port, "testpmd> ")
        time.sleep(5)
        self.set_primary_for_bonding_device(bond_port, self.dut_ports[2], False)
        mac_address_1_now = self.get_port_mac(self.dut_ports[1])
        mac_address_2_now = self.get_port_mac(self.dut_ports[2])
        mac_address_bond_now = self.get_port_mac(bond_port)
        self.verify(mac_address_1_now == mac_address_2_now == mac_address_bond_now == new_mac,
                    "Slave MAC changed when set primary slave")
        self.remove_slave_from_bonding_device(bond_port, False, self.dut_ports[2])
        primary_now = self.get_bond_primary(bond_port)
        self.verify(int(primary_now) == self.dut_ports[1], "Reset primary slave failed after removing primary slave")
        mac_address_2_now = self.get_port_mac(self.dut_ports[2])
        self.verify(mac_address_2_now == mac_address_2_orig, "MAC not back to original after removing the port")
        mac_address_1_now = self.get_port_mac(self.dut_ports[1])
        mac_address_bond_now = self.get_port_mac(bond_port)
        self.verify(mac_address_1_now == mac_address_bond_now == new_mac,
                    "Bonding device and slave MAC changed after removing the primary slave")

        self.add_slave_to_bonding_device(bond_port, False, self.dut_ports[3])
        self.remove_slave_from_bonding_device(bond_port, False, self.dut_ports[3])
        mac_address_3_now = self.get_port_mac(self.dut_ports[3])
        self.verify(mac_address_3_now == mac_address_3_orig, "Slave MAC not back to original after removing it")

    def test_device_promiscuous_mode(self):
        self.launch_app()
        bond_port = self.create_bonded_device(3, 0)
        self.add_slave_to_bonding_device(bond_port, False, self.dut_ports[0], self.dut_ports[1], self.dut_ports[2])
        port_enabled_num = 0
        for port_id in [0, 1, 2, 4]:
            value = self.get_detail_from_port_info("Promiscuous mode: ", "enabled", port_id)
            if value:
                port_enabled_num += 1
        self.verify(port_enabled_num == 4, "Not all slaves of bonded device changed to promiscuous mode.")

        ether_ip = {}
        ether = {}
        ether['dest_mac'] = "00:11:22:33:44:55"
        ether_ip['ether'] = ether

        pkt_count = 1

        self.dut.send_expect("set portlist %d,%d" % (self.dut_ports[3], bond_port), "testpmd> ")
        self.start_all_ports()
        self.dut.send_expect("start", "testpmd> ")
        gp0rx_pkts, gp0rx_err, gp0rx_bytes = [int(_) for _ in self.get_stats(self.dut_ports[0], "rx")]
        gp4rx_pkts, gp4rx_err, gp4rx_bytes = [int(_) for _ in self.get_stats(bond_port, "rx")]
        self.send_packet(self.dut_ports[0], 64, pkt_count, False, **ether_ip)
        p0rx_pkts, p0rx_err, p0rx_bytes = [int(_) for _ in self.get_stats(self.dut_ports[0], "rx")]
        p4rx_pkts, p4rx_err, p4rx_bytes = [int(_) for _ in self.get_stats(bond_port, "rx")]
        p0rx_pkts -= gp0rx_pkts
        p4rx_pkts -= gp4rx_pkts
        self.verify(p0rx_pkts == pkt_count and p4rx_pkts == pkt_count, "Data not received by slave or bonding device when promiscuous state")

        self.dut.send_expect("set promisc 4 off", "testpmd> ")
        port_disabled_num = 0
        for port_id in [0, 1, 2, 4]:
            value = self.get_detail_from_port_info('Promiscuous mode: ', 'disabled', port_id)
            if value:
                port_disabled_num += 1
        self.verify(port_disabled_num == 4, "Not all slaves of bonded device make promiscuous mode disabled.")

        gp0rx_pkts, gp0rx_err, gp0rx_bytes = [int(_) for _ in self.get_stats(self.dut_ports[0], "rx")]
        gp4rx_pkts, gp4rx_err, gp4rx_bytes = [int(_) for _ in self.get_stats(bond_port, "rx")]
        self.send_packet(self.dut_ports[0], 64, pkt_count, True, **ether_ip)
        p0rx_pkts, p0rx_err, p0rx_bytes = [int(_) for _ in self.get_stats(self.dut_ports[0], "rx")]
        p4rx_pkts, p4rx_err, p4rx_bytes = [int(_) for _ in self.get_stats(bond_port, "rx")]
        p0rx_pkts -= gp0rx_pkts
        p4rx_pkts -= gp4rx_pkts
        self.verify(p0rx_pkts == 0 and p4rx_pkts == 0, "Data received by slave or bonding device when promiscuous disabled")

        gp0rx_pkts, gp0rx_err, gp0rx_bytes = [int(_) for _ in self.get_stats(self.dut_ports[0], "rx")]
        gp3tx_pkts, gp3tx_err, gp3tx_bytes = [int(_) for _ in self.get_stats(self.dut_ports[3], "tx")]
        gp4rx_pkts, gp4rx_err, gp4rx_bytes = [int(_) for _ in self.get_stats(bond_port, "rx")]
        self.send_packet(self.dut_ports[0], 64, pkt_count)
        p0rx_pkts, p0rx_err, p0rx_bytes = [int(_) for _ in self.get_stats(self.dut_ports[0], "rx")]
        p3tx_pkts, p3tx_err, p3tx_bytes = [int(_) for _ in self.get_stats(self.dut_ports[3], "tx")]
        p4rx_pkts, p4rx_err, p4rx_bytes = [int(_) for _ in self.get_stats(bond_port, "rx")]
        p0rx_pkts -= gp0rx_pkts
        p3tx_pkts -= gp3tx_pkts
        p4rx_pkts -= gp4rx_pkts
        self.verify(p0rx_pkts == p4rx_pkts == p3tx_pkts == pkt_count, "RX or TX packet number not correct when promiscuous disabled")

    def admin_tester_port(self, local_port, status):
        if self.tester.get_os_type() == 'freebsd':
            self.tester.admin_ports(local_port, status)
        else:
            eth = self.tester.get_interface(local_port)
            self.tester.admin_ports_linux(eth, status)
        time.sleep(5)

    def verify_round_robin_rx_tx(self, unbond_port, bond_port, **slaves):
        """
            slaves:
                'active' = []
                'inactive' = []
        """
        pkt_count = 300
        tx_pkt_orig = {}
        tx_pkt_now = {}

        # send to unbonding port
        for slave in slaves['active']:
            tx_pkt_orig[slave] = [int(_) for _ in self.get_stats(slave, "tx")]
        for slave in slaves['inactive']:
            tx_pkt_orig[slave] = [int(_) for _ in self.get_stats(slave, "tx")]
        tx_pkt_orig[bond_port] = [int(_) for _ in self.get_stats(bond_port, "tx")]

        self.send_packet(unbond_port, 64, pkt_count)

        for slave in slaves['active']:
            tx_pkt_now[slave] = [int(_) for _ in self.get_stats(slave, "tx")]
            tx_pkt_now[slave][0] -= tx_pkt_orig[slave][0]
        for slave in slaves['inactive']:
            tx_pkt_now[slave] = [int(_) for _ in self.get_stats(slave, "tx")]
            tx_pkt_now[slave][0] -= tx_pkt_orig[slave][0]
        tx_pkt_now[bond_port] = [int(_) for _ in self.get_stats(bond_port, "tx")]
        tx_pkt_now[bond_port][0] -= tx_pkt_orig[bond_port][0]

        if slaves['active'].__len__() == 0:
            self.verify(tx_pkt_now[bond_port][0] == 0, "Bonding port should not have TX pkt in mode 0 when all slaves down")
        else:
            self.verify(tx_pkt_now[bond_port][0] == pkt_count, "Bonding port has error TX pkt count in mode 0")
        for slave in slaves['active']:
            self.verify(tx_pkt_now[slave][0] == pkt_count / slaves['active'].__len__(), "Active slave has error TX pkt count in mode 0")
        for slave in slaves['inactive']:
            self.verify(tx_pkt_now[slave][0] == 0, "Inactive slave has error TX pkt count in mode 0")

        # send to bonding slaves
        pkt_orig = {}
        pkt_now = {}
        pkt_orig[unbond_port] = [int(_) for _ in self.get_stats(unbond_port, "tx")]
        pkt_orig[bond_port] = [int(_) for _ in self.get_stats(bond_port, "rx")]

        for slave in slaves['active']:
            self.send_packet(slave, 64, pkt_count)
        for slave in slaves['inactive']:
            self.send_packet(slave, 64, pkt_count, True)

        pkt_now[unbond_port] = [int(_) for _ in self.get_stats(unbond_port, "tx")]
        pkt_now[bond_port] = [int(_) for _ in self.get_stats(bond_port, "rx")]
        pkt_now[unbond_port][0] -= pkt_orig[unbond_port][0]
        pkt_now[bond_port][0] -= pkt_orig[bond_port][0]

        self.verify(pkt_now[unbond_port][0] == pkt_count * slaves['active'].__len__(), "Unbonded port has error TX pkt count in mode 0")
        self.verify(pkt_now[bond_port][0] == pkt_count * slaves['active'].__len__(), "Bonding port has error RX pkt count in mode 0")

    def test_round_robin_rx_tx(self):
        self.launch_app()
        bond_port = self.create_bonded_device(0, 0)
        self.add_slave_to_bonding_device(bond_port, False, self.dut_ports[0], self.dut_ports[1], self.dut_ports[2])
        self.dut.send_expect("set portlist %d,%d" % (self.dut_ports[3], bond_port), "testpmd> ")
        self.start_all_ports()
        self.dut.send_expect("start", "testpmd> ")

        slaves = {}
        slaves['active'] = [self.dut_ports[0], self.dut_ports[1], self.dut_ports[2]]
        slaves['inactive'] = []
        self.verify_round_robin_rx_tx(self.dut_ports[3], bond_port, **slaves)

    def test_round_robin_one_slave_down(self):
        self.launch_app()
        bond_port = self.create_bonded_device(0, 0)
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
            self.verify_round_robin_rx_tx(self.dut_ports[3], bond_port, **slaves)
        finally:
            self.admin_tester_port(self.tester.get_local_port(self.dut_ports[0]), "up")

    def test_round_robin_all_slave_down(self):
        self.launch_app()
        bond_port = self.create_bonded_device(0, 0)
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
            self.verify_round_robin_rx_tx(self.dut_ports[3], bond_port, **slaves)
        finally:
            self.admin_tester_port(self.tester.get_local_port(self.dut_ports[0]), "up")
            self.admin_tester_port(self.tester.get_local_port(self.dut_ports[1]), "up")
            self.admin_tester_port(self.tester.get_local_port(self.dut_ports[2]), "up")

    def get_all_stats(self, unbond_port, rx_tx, bond_port, **slaves):
        """
            unbond_port: pmd port id
            rx_tx: 'rx' or 'tx'
            bond_port: bonding port
            slaves:
                'active' = []
                'inactive' = []
        """
        pkt_now = {}

        if rx_tx == 'rx':
            bond_stat = 'tx'
        else:
            bond_stat = 'rx'

        pkt_now[unbond_port] = [int(_) for _ in self.get_stats(unbond_port, rx_tx)]
        pkt_now[bond_port] = [int(_) for _ in self.get_stats(bond_port, bond_stat)]
        for slave in slaves['active']:
            pkt_now[slave] = [int(_) for _ in self.get_stats(slave, bond_stat)]
        for slave in slaves['inactive']:
            pkt_now[slave] = [int(_) for _ in self.get_stats(slave, bond_stat)]

        return pkt_now

    def verify_active_backup_rx_tx(self, unbond_port, bond_port, **slaves):
        """
            slaves:
                'active' = []
                'inactive' = []
        """
        pkt_count = 100
        pkt_orig = {}
        pkt_now = {}

        if slaves['active'].__len__() != 0:
            primary_port = slaves['active'][0]
            active_flag = 1
        else:
            reverse_verify = True
            active_flag = 0

        # send to unbond port
        pkt_orig = self.get_all_stats(unbond_port, 'rx', bond_port, **slaves)
        self.send_packet(unbond_port, 64, pkt_count)
        pkt_now = self.get_all_stats(unbond_port, 'rx', bond_port, **slaves)

        for key in pkt_now:
            for num in [0, 1, 2]:
                pkt_now[key][num] -= pkt_orig[key][num]

        if active_flag == 1:
            self.verify(pkt_now[primary_port][0] == pkt_count, "Active port not correct TX pkt in mode 1")
        self.verify(pkt_now[bond_port][0] == pkt_count * active_flag, "Bond port not correct TX pkt in mode 1")
        for slave in slaves['inactive']:
            self.verify(pkt_now[slave][0] == 0, "Backup port not correct TX pkt in mode 1")

        # send to primary slave
        if active_flag == 1:
            pkt_orig = self.get_all_stats(unbond_port, 'tx', bond_port, **slaves)
            self.send_packet(primary_port, 64, pkt_count)
            pkt_now = self.get_all_stats(unbond_port, 'tx', bond_port, **slaves)

            pkt_now[bond_port][0] -= pkt_orig[bond_port][0]
            pkt_now[unbond_port][0] -= pkt_orig[bond_port][0]
            for key in pkt_now:
                for num in [0, 1, 2]:
                    pkt_now[key][num] -= pkt_orig[key][num]

            self.verify(pkt_now[bond_port][0] == pkt_count, "Bond port not correct RX pkt in mode 1")
            self.verify(pkt_now[unbond_port][0] == pkt_count, "Unbond port not correct TX pkt in mode 1")
            for slave in slaves['inactive']:
                self.verify(pkt_now[slave][0] == 0, "Backup port not correct RX pkt in mode 1")

    def test_active_backup_rx_tx(self):
        self.launch_app()
        bond_port = self.create_bonded_device(1, 0)
        self.add_slave_to_bonding_device(bond_port, False, self.dut_ports[0], self.dut_ports[1], self.dut_ports[2])
        self.dut.send_expect("set portlist %d,%d" % (self.dut_ports[3], bond_port), "testpmd> ")
        self.start_all_ports()
        self.dut.send_expect("start", "testpmd> ")
        time.sleep(5)

        slaves = {}
        slaves['active'] = [self.dut_ports[0]]
        slaves['inactive'] = [self.dut_ports[1], self.dut_ports[2]]
        self.verify_active_backup_rx_tx(self.dut_ports[3], bond_port, **slaves)

    def test_active_backup_change_primary(self):
        self.launch_app()
        bond_port = self.create_bonded_device(1, 0)
        self.add_slave_to_bonding_device(bond_port, False, self.dut_ports[0], self.dut_ports[1], self.dut_ports[2])
        self.dut.send_expect("set portlist %d,%d" % (self.dut_ports[3], bond_port), "testpmd> ")
        self.start_all_ports()
        self.dut.send_expect("start", "testpmd> ")
        self.set_primary_for_bonding_device(bond_port, self.dut_ports[1])
        time.sleep(5)

        slaves = {}
        slaves['active'] = [self.dut_ports[1]]
        slaves['inactive'] = [self.dut_ports[0], self.dut_ports[2]]
        self.verify_active_backup_rx_tx(self.dut_ports[3], bond_port, **slaves)

    def test_active_backup_one_slave_down(self):
        self.launch_app()
        bond_port = self.create_bonded_device(1, 0)
        self.add_slave_to_bonding_device(bond_port, False, self.dut_ports[0], self.dut_ports[1], self.dut_ports[2])
        self.dut.send_expect("set portlist %d,%d" % (self.dut_ports[3], bond_port), "testpmd> ")
        self.start_all_ports()
        self.dut.send_expect("start", "testpmd> ")
        self.admin_tester_port(self.tester.get_local_port(self.dut_ports[0]), "down")
        primary_port = int(self.get_bond_primary(bond_port))

        try:
            slaves = {}
            slaves['active'] = [primary_port]
            slaves['inactive'] = [self.dut_ports[0], self.dut_ports[1], self.dut_ports[2]]
            slaves['inactive'].remove(primary_port)
            self.verify_active_backup_rx_tx(self.dut_ports[3], bond_port, **slaves)
        finally:
            self.admin_tester_port(self.tester.get_local_port(self.dut_ports[0]), "up")

    def test_active_backup_all_slave_down(self):
        self.launch_app()
        bond_port = self.create_bonded_device(1, 0)
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
            self.verify_active_backup_rx_tx(self.dut_ports[3], bond_port, **slaves)
        finally:
            self.admin_tester_port(self.tester.get_local_port(self.dut_ports[0]), "up")
            self.admin_tester_port(self.tester.get_local_port(self.dut_ports[1]), "up")
            self.admin_tester_port(self.tester.get_local_port(self.dut_ports[2]), "up")

    def translate_mac_str_into_int(self, mac_str):
        mac_hex = '0x'
        for mac_part in mac_str.split(':'):
            mac_hex += mac_part
        return int(mac_hex, 16)

    def mac_hash(self, dest_mac, src_mac):
        dest_port_mac = self.translate_mac_str_into_int(dest_mac)
        src_port_mac = self.translate_mac_str_into_int(src_mac)
        src_xor_dest = dest_port_mac ^ src_port_mac
        xor_value_1 = src_xor_dest >> 32
        xor_value_2 = (src_xor_dest >> 16) ^ (xor_value_1 << 16)
        xor_value_3 = src_xor_dest ^ (xor_value_1 << 32) ^ (xor_value_2 << 16)
        return htons(xor_value_1 ^ xor_value_2 ^ xor_value_3)

    def translate_ip_str_into_int(self, ip_str):
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
        dest_ip_int = self.translate_ip_str_into_int(dest_ip)
        src_ip_int = self.translate_ip_str_into_int(src_ip)
        return htonl(dest_ip_int ^ src_ip_int)

    def udp_hash(self, dest_port, src_port):
        return htons(dest_port ^ src_port)

    def slave_map_hash(self, port, order_ports):
        if len(order_ports) == 0:
            return None
        else:
            order_ports = order_ports.split()
            return order_ports.index(str(port))

    def verify_xor_rx(self, unbond_port, bond_port, **slaves):
        """
            slaves:
                'active'=[]
                'inactive'=[]
        """
        pkt_count = 100
        pkt_orig = {}
        pkt_now = {}

        # send to slave ports
        pkt_orig = self.get_all_stats(unbond_port, 'tx', bond_port, **slaves)
        for slave in slaves['active']:
            self.send_packet(self.dut_ports[slave], 64, pkt_count)
        pkt_now = self.get_all_stats(unbond_port, 'tx', bond_port, **slaves)

        for key in pkt_now:
            for num in [0, 1, 2]:
                pkt_now[key][num] -= pkt_orig[key][num]

        for slave in slaves['active']:
            self.verify(pkt_now[slave][0] == pkt_count, "Slave have error RX packet in XOR")
        for slave in slaves['inactive']:
            self.verify(pkt_now[slave][0] == 0, "Slave have error RX packet in XOR")
        self.verify(pkt_now[unbond_port][0] == pkt_count * len(slaves['active']), "Unbonded device have error TX packet in XOR")

    def verify_xor_tx(self, unbond_port, bond_port, policy, vlan_tag=False, **slaves):
        """
            vlan_tag:False or True
            policy:'L2' , 'L23' or 'L34'
            slaves:
                'active'=[]
                'inactive'=[]
        """
        pkt_count = 100
        pkt_orig = {}
        pkt_now = {}

        # send to unbond_port
        pkt_orig = self.get_all_stats(unbond_port, 'rx', bond_port, **slaves)

        dest_mac = self.dut.get_mac_address(self.dut_ports[unbond_port])
        dest_ip = "10.239.129.88"
        dest_port = 53

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

        source = [('52:00:00:00:00:00', '10.239.129.65', 61),
                  ('52:00:00:00:00:01', '10.239.129.66', 62),
                  ('52:00:00:00:00:02', '10.239.129.67', 63)]

        for src_mac, src_ip, src_port in source:
            ether_ip['ether']['src_mac'] = src_mac
            ether_ip['ip']['src_ip'] = src_ip
            ether_ip['udp']['src_port'] = src_port
            self.send_packet(unbond_port, 64, pkt_count, False, **ether_ip)
        pkt_now = self.get_all_stats(unbond_port, 'rx', bond_port, **slaves)

        for key in pkt_now:
            for num in [0, 1, 2]:
                pkt_now[key][num] -= pkt_orig[key][num]

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

        order_ports = self.get_bond_active_slaves(bond_port)
        for slave in slaves['active']:
            slave_map_hash = self.slave_map_hash(slave, order_ports)
            self.verify(pkt_now[slave][0] == pkt_count * hash_values.count(slave_map_hash), "XOR load balance transmit error on the link up port")
        for slave in slaves['inactive']:
            self.verify(pkt_now[slave][0] == 0, "XOR load balance transmit error on the link down port")

    def test_xor_tx(self):
        self.launch_app()
        bond_port = self.create_bonded_device(2, 0)
        self.add_slave_to_bonding_device(bond_port, False, self.dut_ports[0], self.dut_ports[1], self.dut_ports[2])
        self.dut.send_expect("set portlist %d,%d" % (self.dut_ports[3], bond_port), "testpmd> ")
        self.start_all_ports()
        self.dut.send_expect("start", "testpmd> ")

        slaves = {}
        slaves['active'] = [self.dut_ports[0], self.dut_ports[1], self.dut_ports[2]]
        slaves['inactive'] = []

        self.verify_xor_tx(self.dut_ports[3], bond_port, "L2", False, **slaves)

    def test_xor_tx_one_slave_down(self):
        self.launch_app()
        bond_port = self.create_bonded_device(2, 0)
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

    def test_xor_tx_all_slave_down(self):
        self.launch_app()
        bond_port = self.create_bonded_device(2, 0)
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
        for port_id in ports:
            self.dut.send_expect("vlan set strip %s %d" % (action, port_id), "testpmd> ")
            self.dut.send_expect("vlan set filter %s %d" % (action, port_id), "testpmd> ")

    def test_xor_l34_forward(self):
        self.launch_app()
        bond_port = self.create_bonded_device(2, 0)
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
        self.launch_app()
        bond_port = self.create_bonded_device(2, 0)
        self.add_slave_to_bonding_device(bond_port, False, self.dut_ports[0], self.dut_ports[1], self.dut_ports[2])
        self.dut.send_expect("set portlist %d,%d" % (self.dut_ports[3], bond_port), "testpmd> ")
        self.start_all_ports()
        self.dut.send_expect("start", "testpmd> ")

        slaves = {}
        slaves['active'] = [self.dut_ports[0], self.dut_ports[1], self.dut_ports[2]]
        slaves['inactive'] = []

        self.verify_xor_rx(self.dut_ports[3], bond_port, **slaves)

    def verify_broadcast_bonded_rx(self, unbond_port, bond_port, **slaves):
        """
        slaves:
            'active':[]
            'inactive':[]
        """
        pkt_count = 100
        pkt_orig = {}
        pkt_now = {}

        pkt_orig = self.get_all_stats(unbond_port, 'tx', bond_port, **slaves)
        for slave in slaves['active']:
            self.send_packet(slave, 64, pkt_count)
        pkt_now = self.get_all_stats(unbond_port, 'tx', bond_port, **slaves)

        for key in pkt_now:
            for num in [0, 1, 2]:
                pkt_now[key][num] -= pkt_orig[key][num]

        for slave in slaves['active']:
            self.verify(pkt_now[slave][0] == pkt_count, "Slave RX packet not correct in mode 3")
        for slave in slaves['inactive']:
            self.verify(pkt_now[slave][0] == 0, "Slave RX packet not correct in mode 3")
        self.verify(pkt_now[unbond_port][0] == pkt_count * len(slaves['active']),
                    "Unbonded port TX packet not correct in mode 3")
        self.verify(pkt_now[bond_port][0] == pkt_count * len(slaves['active']),
                    "Bonded device RX packet not correct in mode 3")

    def verify_broadcast_bonded_tx(self, unbond_port, bond_port, **slaves):
        """
        slaves:
            'actvie':[]
            'inactive':[]
        """
        pkt_count = 100
        pkt_orig = {}
        pkt_now = {}

        # send to unbonded device
        pkt_orig = self.get_all_stats(unbond_port, 'rx', bond_port, **slaves)
        self.send_packet(unbond_port, 64, pkt_count)
        pkt_now = self.get_all_stats(unbond_port, 'rx', bond_port, **slaves)

        for key in pkt_now:
            for num in [0, 1, 2]:
                pkt_now[key][num] -= pkt_orig[key][num]

        for slave in slaves['active']:
            self.verify(pkt_now[slave][0] == pkt_count, "Slave TX packet not correct in mode 3")
        for slave in slaves['inactive']:
            self.verify(pkt_now[slave][0] == 0, "Slave TX packet not correct in mode 3")
        self.verify(pkt_now[unbond_port][0] == pkt_count, "Unbonded port RX packet not correct in mode 3")
        self.verify(pkt_now[bond_port][0] == pkt_count * len(slaves['active']),
                    "Bonded device TX packet not correct in mode 3")

    def test_broadcast_rx_tx(self):
        self.launch_app()
        bond_port = self.create_bonded_device(3, 0)
        self.add_slave_to_bonding_device(bond_port, False, self.dut_ports[0], self.dut_ports[1], self.dut_ports[2])
        self.dut.send_expect("set portlist %d,%d" % (self.dut_ports[3], bond_port), "testpmd> ")
        self.start_all_ports()
        self.dut.send_expect("start", "testpmd> ")

        slaves = {}
        slaves['active'] = [self.dut_ports[0], self.dut_ports[1], self.dut_ports[2]]
        slaves['inactive'] = []

        self.verify_broadcast_bonded_rx(self.dut_ports[3], bond_port, **slaves)
        self.verify_broadcast_bonded_tx(self.dut_ports[3], bond_port, **slaves)

    def test_broadcast_tx_one_slave_down(self):
        self.launch_app()
        bond_port = self.create_bonded_device(3, 0)
        self.add_slave_to_bonding_device(bond_port, False, self.dut_ports[0], self.dut_ports[1], self.dut_ports[2])
        self.dut.send_expect("set portlist %d,%d" % (self.dut_ports[3], bond_port), "testpmd> ")
        self.start_all_ports()
        self.dut.send_expect("start", "testpmd> ")
        self.admin_tester_port(self.tester.get_local_port(self.dut_ports[0]), "down")

        try:
            slaves = {}
            slaves['active'] = [self.dut_ports[1], self.dut_ports[2]]
            slaves['inactive'] = [self.dut_ports[0]]

            self.verify_broadcast_bonded_tx(self.dut_ports[3], bond_port, **slaves)
        finally:
            self.admin_tester_port(self.tester.get_local_port(self.dut_ports[0]), "up")

    def test_broadcast_tx_all_slave_down(self):
        self.launch_app()
        bond_port = self.create_bonded_device(3, 0)
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

            self.verify_broadcast_bonded_tx(self.dut_ports[3], bond_port, **slaves)
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
