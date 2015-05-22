# <COPYRIGHT_TAG>

"""
DPDK Test suite.


Test userland 10Gb PMD.

"""

import re
import pdb
import time

import dts
from qemu_kvm import QEMUKvm
from test_case import TestCase

from pmd_output import PmdOutput

FRAME_SIZE_64 = 64
VM_CORES_MASK = 'all'


class TestSriovKvm(TestCase):

    def set_up_all(self):
        # port_mirror_ref = {port_id: rule_id_list}
        # rule_id should be integer, and should be increased based on
        # the most rule_id when add a rule for a port successfully,
        # case should not be operate it directly
        # example:
        #          port_mirror_ref = {0: 1, 1: 3}
        self.port_mirror_ref = {}
        self.dut_ports = self.dut.get_ports(self.nic)
        self.verify(len(self.dut_ports) >= 1, "Insufficient ports")

        self.vm0 = None
        self.vm1 = None
        self.vm2 = None
        self.vm3 = None

    def set_up(self):
        self.setup_2vm_2pf_env_flag = 0

        self.setup_2vm_2vf_env_flag = 0
        self.setup_2vm_prerequisite_flag = 0

        self.setup_4vm_4vf_env_flag = 0
        self.setup_4vm_prerequisite_flag = 0

    def get_stats(self, dut, portid, rx_tx):
        """
        Get packets number from port statistic
        """

        stats = dut.testpmd.get_pmd_stats(portid)

        if rx_tx == "rx":
            stats_result = [
                stats['RX-packets'], stats['RX-missed'], stats['RX-bytes']]
        elif rx_tx == "tx":
            stats_result = [
                stats['TX-packets'], stats['TX-errors'], stats['TX-bytes']]
        else:
            return None

        return stats_result

    def parse_ether_ip(self, dut, dut_ports, dest_port, **ether_ip):
        """
        dut: which you want to send packet to
        dest_port: the port num must be the index of dut.get_ports()
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
            dut_dest_port = dut_ports[dest_port]
        except Exception as e:
            print e

        tester_port = dut.ports_map[dut_dest_port]
        if not ether_ip.get('ether'):
            ether['dest_mac'] = dut.get_mac_address(dut_dest_port)
            ether['src_mac'] = dut.tester.get_mac(tester_port)
        else:
            if not ether_ip['ether'].get('dest_mac'):
                ether['dest_mac'] = dut.get_mac_address(dut_dest_port)
            else:
                ether['dest_mac'] = ether_ip['ether']['dest_mac']
            if not ether_ip['ether'].get('src_mac'):
                ether['src_mac'] = dut.tester.get_mac(tester_port)
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
                    dut,
                    dut_ports,
                    dest_port,
                    src_port=False,
                    frame_size=FRAME_SIZE_64,
                    count=1,
                    invert_verify=False,
                    **ether_ip):
        """
        Send count packet to portid
        dut: which you want to send packet to
        dest_port: the port num must be the index of dut.get_ports()
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
                during = 20
                count = 1000 * 10
            else:
                raise e

        gp0rx_pkts, gp0rx_err, gp0rx_bytes = [int(_)
                                              for _ in self.get_stats(dut, dest_port, "rx")]
        if not src_port:
            itf = self.tester.get_interface(
                dut.ports_map[dut_ports[dest_port]])
        else:
            itf = src_port

        ret_ether_ip = self.parse_ether_ip(
            dut,
            dut_ports,
            dest_port,
            **ether_ip)

        pktlen = frame_size - 18
        padding = pktlen - 20

        start = time.time()
        while True:
            self.tester.scapy_foreground()
            self.tester.scapy_append(
                'nutmac="%s"' % ret_ether_ip['ether']['dest_mac'])
            self.tester.scapy_append(
                'srcmac="%s"' % ret_ether_ip['ether']['src_mac'])

            if ether_ip.get('dot1q'):
                self.tester.scapy_append(
                    'vlanvalue=%d' % int(ret_ether_ip['dot1q']['vlan']))
            self.tester.scapy_append(
                'destip="%s"' % ret_ether_ip['ip']['dest_ip'])
            self.tester.scapy_append(
                'srcip="%s"' % ret_ether_ip['ip']['src_ip'])
            self.tester.scapy_append(
                'destport=%d' % ret_ether_ip['udp']['dest_port'])
            self.tester.scapy_append(
                'srcport=%d' % ret_ether_ip['udp']['src_port'])
            if not ret_ether_ip.get('dot1q'):
                send_cmd = 'sendp([Ether(dst=nutmac, src=srcmac)/' + \
                    'IP(dst=destip, src=srcip, len=%s)/' % pktlen + \
                    'UDP(sport=srcport, dport=destport)/' + \
                    'Raw(load="\x50"*%s)], ' % padding + \
                    'iface="%s", count=%d)' % (itf, count)
            else:
                send_cmd = 'sendp([Ether(dst=nutmac, src=srcmac)/Dot1Q(vlan=vlanvalue)/' + \
                           'IP(dst=destip, src=srcip, len=%s)/' % pktlen + \
                           'UDP(sport=srcport, dport=destport)/' + \
                           'Raw(load="\x50"*%s)], iface="%s", count=%d)' % (
                               padding, itf, count)
            self.tester.scapy_append(send_cmd)

            self.tester.scapy_execute()
            loop += 1

            now = time.time()
            if (now - start) >= during:
                break
        time.sleep(.5)

        p0rx_pkts, p0rx_err, p0rx_bytes = [int(_)
                                           for _ in self.get_stats(dut, dest_port, "rx")]

        p0rx_pkts -= gp0rx_pkts
        p0rx_bytes -= gp0rx_bytes

        if not invert_verify:
            self.verify(p0rx_pkts >= count * loop,
                        "Data not received by port")
        else:
            self.verify(p0rx_pkts == 0 or
                        p0rx_pkts < count * loop,
                        "Data received by port, but should not.")
        return count * loop

    def setup_2vm_2pf_env(self):
        p0 = self.dut_ports[0]
        p1 = self.dut_ports[1]

        self.port0 = self.dut.ports_info[p0]['port']
        self.port0.unbind_driver()
        self.port0_pci = self.dut.ports_info[p0]['pci']

        self.port1 = self.dut.ports_info[p1]['port']
        self.port1.unbind_driver()
        self.port1_pci = self.dut.ports_info[p1]['pci']

        vf0_prop = {'prop_host': self.port0_pci}
        vf1_prop = {'prop_host': self.port1_pci}

        # set up VM0 ENV
        self.vm0 = QEMUKvm(self.dut, 'vm0', 'sriov_kvm')
        self.vm0.set_vm_device(driver='pci-assign', **vf0_prop)
        self.vm_dut_0 = self.vm0.start()

        # set up VM1 ENV
        self.vm1 = QEMUKvm(self.dut, 'vm1', 'sriov_kvm')
        self.vm1.set_vm_device(driver='pci-assign', **vf1_prop)
        self.vm_dut_1 = self.vm1.start()

        self.setup_2vm_2vf_env_flag = 1

    def destroy_2vm_2pf_env(self):
        self.vm_dut_0.close()
        self.vm_dut_0.logger.logger_exit()
        self.vm0.stop()
        self.port0.bind_driver('igb_uio')
        self.vm0 = None

        self.vm_dut_1.close()
        self.vm_dut_1.logger.logger_exit()
        self.vm1.stop()
        self.port1.bind_driver('igb_uio')
        self.vm1 = None

        self.setup_2vm_2vf_env_flag = 0

    def setup_2vm_2vf_env(self, driver='igb_uio'):
        self.used_dut_port = self.dut_ports[0]

        self.dut.generate_sriov_vfs_by_port(
            self.used_dut_port, 2, driver=driver)
        self.sriov_vfs_port = self.dut.ports_info[
            self.used_dut_port]['vfs_port']

        try:

            for port in self.sriov_vfs_port:
                port.bind_driver('pci-stub')

            time.sleep(1)

            vf0_prop = {'prop_host': self.sriov_vfs_port[0].pci}
            vf1_prop = {'prop_host': self.sriov_vfs_port[1].pci}

            for port_id in self.dut_ports:
                if port_id == self.used_dut_port:
                    continue
                port = self.dut.ports_info[port_id]['port']
                port.bind_driver()

            if driver == 'igb_uio':
                # start testpmd with the two VFs on the host
                self.host_testpmd = PmdOutput(self.dut)
                eal_param = '-b %(vf0)s -b %(vf1)s' % {'vf0': self.sriov_vfs_port[0].pci,
                                                       'vf1': self.sriov_vfs_port[1].pci}
                self.host_testpmd.start_testpmd(
                    "1S/2C/2T", eal_param=eal_param)

            # set up VM0 ENV
            self.vm0 = QEMUKvm(self.dut, 'vm0', 'sriov_kvm')
            self.vm0.set_vm_device(driver='pci-assign', **vf0_prop)
            self.vm_dut_0 = self.vm0.start()
            if self.vm_dut_0 is None:
                raise Exception("Set up VM0 ENV failed!")

            # set up VM1 ENV
            self.vm1 = QEMUKvm(self.dut, 'vm1', 'sriov_kvm')
            self.vm1.set_vm_device(driver='pci-assign', **vf1_prop)
            self.vm_dut_1 = self.vm1.start()
            if self.vm_dut_1 is None:
                raise Exception("Set up VM1 ENV failed!")

            self.setup_2vm_2vf_env_flag = 1
        except Exception as e:
            self.destroy_2vm_2vf_env()
            raise Exception(e)

    def destroy_2vm_2vf_env(self):
        if getattr(self, 'vm_dut_0', None):
            self.vm_dut_0.close()
            self.vm_dut_0.logger.logger_exit()
        if getattr(self, 'vm0', None):
            self.vm0.stop()
            self.vm0 = None

        if getattr(self, 'vm_dut_1', None):
            self.vm_dut_1.close()
            self.vm_dut_1.logger.logger_exit()
        if getattr(self, 'vm1', None):
            self.vm1.stop()
            self.vm1 = None

        if getattr(self, 'host_testpmd', None):
            self.host_testpmd.execute_cmd('quit', '# ')
            self.host_testpmd = None

        if getattr(self, 'used_dut_port', None):
            self.dut.destroy_sriov_vfs_by_port(self.used_dut_port)
            port = self.dut.ports_info[self.used_dut_port]['port']
            port.bind_driver('igb_uio')
            self.used_dut_port = None

        for port_id in self.dut_ports:
            port = self.dut.ports_info[port_id]['port']
            port.bind_driver('igb_uio')

        self.setup_2vm_2vf_env_flag = 0

    def setup_4vm_4vf_env(self, driver='igb_uio'):
        self.used_dut_port = self.dut_ports[0]

        self.dut.generate_sriov_vfs_by_port(
            self.used_dut_port, 4, driver=driver)
        self.sriov_vfs_port = self.dut.ports_info[self.used_dut_port]['port']

        try:
            for port in self.sriov_vfs_port:
                port.bind_driver('pci-stub')

            time.sleep(1)

            vf0_prop = {'prop_host': self.sriov_vfs_port[0].pci}
            vf1_prop = {'prop_host': self.sriov_vfs_port[1].pci}
            vf2_prop = {'prop_host': self.sriov_vfs_port[2].pci}
            vf3_prop = {'prop_host': self.sriov_vfs_port[3].pci}

            for port_id in self.dut_ports:
                if port_id == self.used_dut_port:
                    continue
                port = self.dut.ports_info[port_id]['port']
                port.bind_driver()

            if driver == 'igb_uio':
                # start testpmd with the four VFs on the host
                self.host_testpmd = PmdOutput(self.dut)
                eal_param = '-b %(vf0) -b %(vf1)s -b %(vf2)s -b %(vf3)s' % \
                    {'vf0': self.sriov_vfs_pci[0],
                     'vf1': self.sriov_vfs_pci[1],
                     'vf2': self.sriov_vfs_pci[2],
                     'vf3': self.sriov_vfs_pci[3]}
                self.host_testpmd.start_testpmd(
                    "1S/2C/2T", eal_param=eal_param)

            self.vm0 = QEMUKvm(self.dut, 'vm0', 'sriov_kvm')
            self.vm0.set_vm_device(driver='pci-assign', **vf0_prop)
            self.vm_dut_0 = self.vm0.start()
            if self.vm_dut_0 is None:
                raise Exception("Set up VM0 ENV failed!")

            self.vm1 = QEMUKvm(self.dut, 'vm1', 'sriov_kvm')
            self.vm1.set_vm_device(driver='pci-assign', **vf1_prop)
            self.vm_dut_1 = self.vm1.start()
            if self.vm_dut_1 is None:
                raise Exception("Set up VM1 ENV failed!")

            self.vm2 = QEMUKvm(self.dut, 'vm2', 'sriov_kvm')
            self.vm2.set_vm_device(driver='pci-assign', **vf2_prop)
            self.vm_dut_2 = self.vm1.start()
            if self.vm_dut_2 is None:
                raise Exception("Set up VM2 ENV failed!")

            self.vm3 = QEMUKvm(self.dut, 'vm3', 'sriov_kvm')
            self.vm3.set_vm_device(driver='pci-assign', **vf3_prop)
            self.vm_dut_3 = self.vm3.start()
            if self.vm_dut_3 is None:
                raise Exception("Set up VM3 ENV failed!")

            self.setup_4vm_4vf_env_flag = 1
        except Exception as e:
            self.destroy_4vm_4vf_env()
            raise Exception(e)

    def destroy_4vm_4vf_env(self):
        if getattr(self, 'vm_dut_0', None):
            self.vm_dut_0.close()
            self.vm_dut_0.logger.logger_exit()
        if getattr(self, 'vm0', None):
            self.vm0.stop()
            self.vm0 = None

        if getattr(self, 'vm_dut_1', None):
            self.vm_dut_1.close()
            self.vm_dut_1.logger.logger_exit()
        if getattr(self, 'vm1', None):
            self.vm1.stop()
            self.vm1 = None

        if getattr(self, 'vm_dut_2', None):
            self.vm_dut_2.close()
            self.vm_dut_2.logger.logger_exit()
        if getattr(self, 'vm2', None):
            self.vm2.stop()
            self.vm2 = None

        if getattr(self, 'vm_dut_3', None):
            self.vm_dut_3.close()
            self.vm_dut_3.logger.logger_exit()
        if getattr(slef, 'vm3', None):
            self.vm3.stop()
            self.vm3 = None

        if getattr(self, 'host_testpmd', None):
            self.host_testpmd.execute_cmd('stop')
            self.host_testpmd.execute_cmd('quit', '# ')
            self.host_testpmd = None

        if getattr(self, 'used_dut_port', None):
            self.dut.destroy_sriov_vfs_by_port(self.used_dut_port)
            port = self.ports_info[self.used_dut_port]['port']
            port.bind_driver('igb_uio')
            slef.used_dut_port = None

        for port_id in self.dut_ports:
            port = self.dut.ports_info[port_id]['port']
            port.bind_driver('igb_uio')

        self.setup_4vm_4vf_env_flag = 0

    def transform_integer(self, value):
        try:
            value = int(value)
        except ValueError as e:
            raise Exception("Value not integer,but is " + type(value))
        return value

    def make_port_new_ruleid(self, port):
        port = self.transform_integer(port)
        if port not in self.port_mirror_ref.keys():
            max_rule_id = 0
        else:
            rule_ids = sorted(self.port_mirror_ref[port])
            if rule_ids:
                max_rule_id = rule_ids[-1] + 1
            else:
                max_rule_id = 0
        return max_rule_id

    def add_port_ruleid(self, port, rule_id):
        port = self.transform_integer(port)
        rule_id = self.transform_integer(rule_id)

        if port not in self.port_mirror_ref.keys():
            self.port_mirror_ref[port] = [rule_id]
        else:
            self.verify(rule_id not in self.port_mirror_ref[port],
                        "Rule id [%d] has been repeated, please check!" % rule_id)
            self.port_mirror_ref[port].append(rule_id)

    def remove_port_ruleid(self, port, rule_id):
        port = self.transform_integer(port)
        rule_id = self.transform_integer(rule_id)
        if port not in self.port_mirror_ref.keys():
            pass
        else:
            if rule_id not in self.port_mirror_ref[port]:
                pass
            else:
                self.port_mirror_ref[port].remove(rule_id)
            if not self.port_mirror_ref[port]:
                self.port_mirror_ref.pop(port)

    def set_port_mirror_rule(self, port, mirror_name, rule_detail):
        """
        Set the mirror rule for specified port.
        """
        port = self.transform_integer(port)

        rule_id = self.make_port_new_ruleid(port)

        mirror_rule_cmd = "set port %d mirror-rule %d %s %s" % \
            (port, rule_id, mirror_name, rule_detail)
        out = self.dut.send_expect("%s" % mirror_rule_cmd, "testpmd> ")
        self.verify('Bad arguments' not in out, "Set port %d %s failed!" %
                    (port, mirror_name))

        self.add_port_ruleid(port, rule_id)
        return rule_id

    def set_port_pool_mirror(self, port, pool_mirror_rule):
        """
        Set the pool mirror for specified port.
        """
        return self.set_port_mirror_rule(port, 'pool-mirror-up', pool_mirror_rule)

    def set_port_vlan_mirror(self, port, vlan_mirror_rule):
        """
        Set the vlan mirror for specified port.
        """
        return self.set_port_mirror_rule(port, 'vlan-mirror', vlan_mirror_rule)

    def set_port_uplink_mirror(self, port, uplink_mirror_rule):
        """
        Set the uplink mirror for specified port.
        """
        return self.set_port_mirror_rule(port, 'uplink-mirror', uplink_mirror_rule)

    def set_port_downlink_mirror(self, port, downlink_mirror_rule):
        """
        Set the downlink mirror for specified port.
        """
        return self.set_port_mirror_rule(port, 'downlink-mirror', downlink_mirror_rule)

    def reset_port_mirror_rule(self, port, rule_id):
        """
        Reset the pool mirror for specified port.
        """
        port = self.transform_integer(port)
        rule_id = self.transform_integer(rule_id)

        mirror_rule_cmd = "reset port %d mirror-rule %d" % (port, rule_id)
        out = self.dut.send_expect("%s" % mirror_rule_cmd, "testpmd> ")
        self.verify("Bad arguments" not in out,
                    "Reset port %d mirror rule failed!")

        self.remove_port_ruleid(port, rule_id)

    def reset_port_all_mirror_rule(self, port):
        """
        Reset all mirror rules of specified port.
        """
        port = self.transform_integer(port)

        if port not in self.port_mirror_ref.keys():
            pass
        else:
            for rule_id in self.port_mirror_ref[port]:
                self.reset_port_mirror_rule(port, rule_id)

    def setup_two_vm_common_prerequisite(self):
        self.vm0_dut_ports = self.vm_dut_0.get_ports('any')
        self.vm0_testpmd = PmdOutput(self.vm_dut_0)
        self.vm0_testpmd.start_testpmd(VM_CORES_MASK)
        self.vm0_testpmd.execute_cmd('set fwd rxonly')
        self.vm0_testpmd.execute_cmd('start')

        self.vm1_dut_ports = self.vm_dut_1.get_ports('any')
        self.vm1_testpmd = PmdOutput(self.vm_dut_1)
        self.vm1_testpmd.start_testpmd(VM_CORES_MASK)
        self.vm1_testpmd.execute_cmd('set fwd mac')
        self.vm1_testpmd.execute_cmd('start')

        self.setup_2vm_prerequisite_flag = 1

    def destroy_two_vm_common_prerequisite(self):
        self.vm0_testpmd.execute_cmd('stop')
        self.vm0_testpmd.execute_cmd('quit', '# ')
        self.vm0_testpmd = None
        self.vm0_dut_ports = None

        self.vm1_testpmd.execute_cmd('stop')
        self.vm1_testpmd.execute_cmd('quit', '# ')
        self.vm0_testpmd = None
        self.vm1_dut_ports = None

        self.setup_2vm_prerequisite_flag = 0

    def stop_test_setup_two_vm_pf_env(self):
        self.setup_2vm_2pf_env()

        out = self.vm_dut_0.send_expect("ifconfig", '# ')
        print out
        out = self.vm_dut_0.send_expect("lspci -nn | grep -i eth", '# ')
        print out

        out = self.vm_dut_1.send_expect("ifconfig", '# ')
        print out
        out = self.vm_dut_1.send_expect("lspci -nn | grep -i eth", '# ')
        print out

        self.destroy_2vm_2pf_env()

    def test_two_vms_intervm_communication(self):
        self.setup_2vm_2vf_env()

        self.vm0_dut_ports = self.vm_dut_0.get_ports('any')
        self.vm1_dut_ports = self.vm_dut_1.get_ports('any')
        port_id_0 = 0
        packet_num = 10

        self.vm1_testpmd = PmdOutput(self.vm_dut_1)
        self.vm1_testpmd.start_testpmd(VM_CORES_MASK)
        vf1_mac = self.vm1_testpmd.get_port_mac(port_id_0)
        self.vm1_testpmd.execute_cmd('set fwd mac')
        self.vm1_testpmd.execute_cmd('start')

        self.vm0_testpmd = PmdOutput(self.vm_dut_0)
        self.vm0_testpmd.start_testpmd(
            VM_CORES_MASK, "--eth-peer=0,%s" % vf1_mac)
        vf0_mac = self.vm0_testpmd.get_port_mac(port_id_0)
        self.vm0_testpmd.execute_cmd('set fwd mac')
        self.vm0_testpmd.execute_cmd('start')

        self.setup_2vm_prerequisite_flag = 1
        time.sleep(2)

        vm1_start_stats = self.vm1_testpmd.get_pmd_stats(port_id_0)
        self.send_packet(
            self.vm_dut_0, self.vm0_dut_ports, port_id_0, count=packet_num)
        vm1_end_stats = self.vm1_testpmd.get_pmd_stats(port_id_0)

        self.verify(
            vm1_end_stats["TX-packets"] - vm1_start_stats["TX-packets"] == packet_num,
            "VM1 transmit packets failed when sending packets to VM0")

    def calculate_stats(self, start_stats, end_stats):
        ret_stats = {}
        for key in start_stats.keys():
            try:
                start_stats[key] = int(start_stats[key])
                end_stats[key] = int(end_stats[key])
            except TypeError:
                ret_stats[key] = end_stats[key]
                continue
            ret_stats[key] = end_stats[key] - start_stats[key]
        return ret_stats

    def test_two_vms_pool_mirror(self):
        self.setup_2vm_2vf_env()
        self.setup_two_vm_common_prerequisite()

        port_id_0 = 0
        packet_num = 10

        rule_id = self.set_port_pool_mirror(port_id_0, '0x1 dst-pool 1 on')
        vm1_start_stats = self.vm1_testpmd.get_pmd_stats(port_id_0)
        self.send_packet(
            self.vm_dut_0, self.vm0_dut_ports, port_id_0, count=packet_num)
        vm1_end_stats = self.vm1_testpmd.get_pmd_stats(port_id_0)

        vm1_ret_stats = self.calculate_stats(vm1_start_stats, vm1_end_stats)

        self.verify(vm1_ret_stats['RX-packets'] == packet_num and
                    vm1_ret_stats['TX-packets'] == packet_num,
                    "Pool mirror failed between VM0 and VM1!")

        self.reset_port_mirror_rule(port_id_0, rule_id)

    def test_two_vms_uplink_mirror(self):
        self.setup_2vm_2vf_env()
        self.setup_two_vm_common_prerequisite()

        port_id_0 = 0
        packet_num = 10

        rule_id = self.set_port_uplink_mirror(port_id_0, 'dst-pool 1 on')
        vm1_start_stats = self.vm1_testpmd.get_pmd_stats(port_id_0)
        self.send_packet(
            self.vm_dut_0, self.vm0_dut_ports, port_id_0, count=packet_num)
        vm1_end_stats = self.vm1_testpmd.get_pmd_stats(port_id_0)

        vm1_ret_stats = self.calculate_stats(vm1_start_stats, vm1_end_stats)

        self.verify(vm1_ret_stats['RX-packets'] == packet_num and
                    vm1_ret_stats['TX-packets'] == packet_num,
                    "Uplink mirror failed between VM0 and VM1!")

        self.reset_port_mirror_rule(port_id_0, rule_id)

    def test_two_vms_downlink_mirror(self):
        self.setup_2vm_2vf_env()
        self.setup_two_vm_common_prerequisite()

        self.vm0_testpmd.execute_cmd('stop')
        self.vm1_testpmd.execute_cmd('stop')

        port_id_0 = 0

        rule_id = self.set_port_downlink_mirror(port_id_0, 'dst-pool 1 on')

        self.vm1_testpmd.execute_cmd('set fwd rxonly')
        self.vm1_testpmd.execute_cmd('start')
        vm1_start_stats = self.vm1_testpmd.get_pmd_stats(port_id_0)
        vm0_start_stats = self.vm0_testpmd.get_pmd_stats(port_id_0)
        self.vm0_testpmd.execute_cmd('start tx_first')
        vm0_end_stats = self.vm0_testpmd.get_pmd_stats(port_id_0)
        vm1_end_stats = self.vm1_testpmd.get_pmd_stats(port_id_0)

        vm0_ret_stats = self.calculate_stats(vm0_start_stats, vm0_end_stats)
        vm1_ret_stats = self.calculate_stats(vm1_start_stats, vm1_end_stats)

        self.verify(vm1_ret_stats['RX-packets'] == vm0_ret_stats['TX-packets'],
                    "Downlink mirror failed between VM0 and VM1!")

        self.reset_port_mirror_rule(port_id_0, rule_id)

    def test_two_vms_vlan_mirror(self):
        self.setup_2vm_2vf_env()
        self.setup_two_vm_common_prerequisite()

        port_id_0 = 0
        vlan_id = 0
        vf_mask = '0x1'
        packet_num = 10

        self.host_testpmd.execute_cmd(
            'rx_vlan add %d port %d vf %s' % (vlan_id, port_id_0, vf_mask))
        rule_id = self.set_port_vlan_mirror(port_id_0, '0 dst-pool 1 on')

        vm1_start_stats = self.vm1_testpmd.get_pmd_stats(port_id_0)
        ether_ip = {}
        ether_ip['dot1q'] = {'vlan': '%d' % vlan_id}
        self.send_packet(
            self.vm_dut_0,
            self.vm0_dut_ports,
            port_id_0,
            count=packet_num,
            **ether_ip)
        vm1_end_stats = self.vm1_testpmd.get_pmd_stats(port_id_0)

        vm1_ret_stats = self.calculate_stats(vm1_start_stats, vm1_end_stats)

        self.verify(vm1_ret_stats['RX-packets'] == packet_num and
                    vm1_ret_stats['TX-packets'] == packet_num,
                    "Vlan mirror failed between VM0 and VM1!")

        self.reset_port_mirror_rule(port_id_0, rule_id)

    def test_two_vms_vlan_and_pool_mirror(self):
        self.setup_2vm_2vf_env()
        self.setup_two_vm_common_prerequisite()

        port_id_0 = 0
        vlan_id = 3
        vf_mask = '0x2'
        packet_num = 10

        self.host_testpmd.execute_cmd(
            'rx_vlan add %d port %d vf %s' % (vlan_id, port_id_0, vf_mask))
        self.set_port_pool_mirror(port_id_0, '0x1 dst-pool 1 on')
        self.set_port_vlan_mirror(port_id_0, '%d dst-pool 0 on' % vlan_id)

        vm1_start_stats = self.vm1_testpmd.get_pmd_stats(port_id_0)
        self.send_packet(
            self.vm_dut_0,
            self.vm0_dut_ports,
            port_id_0,
            count=packet_num)
        vm1_end_stats = self.vm1_testpmd.get_pmd_stats(port_id_0)

        vm1_ret_stats = self.calculate_stats(vm1_start_stats, vm1_end_stats)

        self.verify(vm1_ret_stats['RX-packets'] == packet_num and
                    vm1_ret_stats['TX-packets'] == packet_num,
                    "Pool mirror failed between VM0 and VM1 when set vlan and pool mirror!")

        vm0_start_stats = self.vm0_testpmd.get_pmd_stats(port_id_0)
        ether_ip = {}
        ether_ip['dot1q'] = {'vlan': '%d' % vlan_id}
        self.send_packet(
            self.vm_dut_1,
            self.vm1_dut_ports,
            port_id_0,
            count=10 *
            packet_num,
            **ether_ip)
        vm0_end_stats = self.vm0_testpmd.get_pmd_stats(port_id_0)

        vm0_ret_stats = self.calculate_stats(vm0_start_stats, vm0_end_stats)

        self.verify(vm0_ret_stats['RX-packets'] == 10 * packet_num,
                    "Vlan mirror failed between VM0 and VM1 when set vlan and pool mirror!")

        self.reset_port_all_mirror_rule(port_id_0)

    def test_two_vms_uplink_and_downlink_mirror(self):
        self.setup_2vm_2vf_env()
        self.setup_two_vm_common_prerequisite()

        self.vm0_testpmd.execute_cmd('stop')
        self.vm1_testpmd.execute_cmd('stop')

        port_id_0 = 0
        packet_num = 10

        self.set_port_downlink_mirror(port_id_0, 'dst-pool 1 on')
        self.set_port_uplink_mirror(port_id_0, 'dst-pool 1 on')

        self.vm1_testpmd.execute_cmd('set fwd rxonly')
        self.vm1_testpmd.execute_cmd('start')
        vm1_start_stats = self.vm1_testpmd.get_pmd_stats(port_id_0)
        vm0_start_stats = self.vm0_testpmd.get_pmd_stats(port_id_0)
        self.vm0_testpmd.execute_cmd('start tx_first')
        vm0_end_stats = self.vm0_testpmd.get_pmd_stats(port_id_0)
        vm1_end_stats = self.vm1_testpmd.get_pmd_stats(port_id_0)

        vm0_ret_stats = self.calculate_stats(vm0_start_stats, vm0_end_stats)
        vm1_ret_stats = self.calculate_stats(vm1_start_stats, vm1_end_stats)

        self.verify(vm1_ret_stats['RX-packets'] == vm0_ret_stats['TX-packets'],
                    "Downlink mirror failed between VM0 and VM1 " +
                    "when set uplink and downlink mirror!")

        self.vm0_testpmd.execute_cmd('stop')
        self.vm0_testpmd.execute_cmd('set fwd mac')
        self.vm0_testpmd.execute_cmd('start')

        vm1_start_stats = self.vm1_testpmd.get_pmd_stats(port_id_0)
        self.send_packet(
            self.vm_dut_0,
            self.vm0_dut_ports,
            port_id_0,
            count=packet_num)
        vm1_end_stats = self.vm1_testpmd.get_pmd_stats(port_id_0)

        vm1_ret_stats = self.calculate_stats(vm1_start_stats, vm1_end_stats)

        self.verify(vm1_ret_stats['RX-packets'] == 2 * packet_num,
                    "Uplink and down link mirror failed between VM0 and VM1 " +
                    "when set uplink and downlink mirror!")

        self.reset_port_all_mirror_rule(port_id_0)

    def test_two_vms_vlan_and_pool_and_uplink_and_downlink(self):
        self.setup_2vm_2vf_env()
        self.setup_two_vm_common_prerequisite()

        self.vm0_testpmd.execute_cmd('stop')
        self.vm1_testpmd.execute_cmd('stop')

        port_id_0 = 0
        vlan_id = 3
        vf_mask = '0x2'
        packet_num = 1

        self.set_port_downlink_mirror(port_id_0, 'dst-pool 1 on')
        self.set_port_uplink_mirror(port_id_0, 'dst-pool 1 on')
        self.host_testpmd.execute_cmd("rx_vlan add %d port %d vf %s" %
                                      (vlan_id, port_id_0, vf_mask))
        self.set_port_vlan_mirror(port_id_0, '%d dst-pool 0 on' % vlan_id)
        self.set_port_pool_mirror(port_id_0, '0x1 dst-pool 1 on')

        self.vm1_testpmd.execute_cmd('set fwd rxonly')
        self.vm1_testpmd.execute_cmd('start')
        vm1_start_stats = self.vm1_testpmd.get_pmd_stats(port_id_0)
        vm0_start_stats = self.vm0_testpmd.get_pmd_stats(port_id_0)
        self.vm0_testpmd.execute_cmd('start tx_first')
        vm0_end_stats = self.vm0_testpmd.get_pmd_stats(port_id_0)
        vm1_end_stats = self.vm1_testpmd.get_pmd_stats(port_id_0)

        vm0_ret_stats = self.calculate_stats(vm0_start_stats, vm0_end_stats)
        vm1_ret_stats = self.calculate_stats(vm1_start_stats, vm1_end_stats)

        self.verify(vm1_ret_stats['RX-packets'] == vm0_ret_stats['TX-packets'],
                    "Downlink mirror failed between VM0 and VM1 " +
                    "when set vlan, pool, uplink and downlink mirror!")

        self.vm0_testpmd.execute_cmd('stop')
        self.vm0_testpmd.execute_cmd('set fwd mac')
        self.vm0_testpmd.execute_cmd('start')
        vm0_start_stats = self.vm0_testpmd.get_pmd_stats(port_id_0)
        vm1_start_stats = self.vm1_testpmd.get_pmd_stats(port_id_0)
        self.send_packet(
            self.vm_dut_0,
            self.vm0_dut_ports,
            port_id_0,
            count=packet_num)
        vm0_end_stats = self.vm0_testpmd.get_pmd_stats(port_id_0)
        vm1_end_stats = self.vm1_testpmd.get_pmd_stats(port_id_0)

        vm0_ret_stats = self.calculate_stats(vm0_start_stats, vm0_end_stats)
        vm1_ret_stats = self.calculate_stats(vm1_start_stats, vm1_end_stats)

        self.verify(vm0_ret_stats['RX-packets'] == packet_num and
                    vm0_ret_stats['TX-packets'] == packet_num and
                    vm1_ret_stats['RX-packets'] == 2 * packet_num,
                    "Uplink and downlink mirror failed between VM0 and VM1 " +
                    "when set vlan, pool, uplink and downlink mirror!")

        self.vm0_testpmd.execute_cmd('stop')
        self.vm0_testpmd.execute_cmd('set fwd mac')
        self.vm0_testpmd.execute_cmd('start')

        ether_ip = {}
        ether_ip['dot1q'] = {'vlan': '%d' % vlan_id}
        vm1_start_stats = self.vm1_testpmd.get_pmd_stats(port_id_0)
        vm0_start_stats = self.vm0_testpmd.get_pmd_stats(port_id_0)
        self.send_packet(
            self.vm_dut_1,
            self.vm1_dut_ports,
            port_id_0,
            count=packet_num,
            **ether_ip)
        vm0_end_stats = self.vm0_testpmd.get_pmd_stats(port_id_0)
        vm1_end_stats = self.vm1_testpmd.get_pmd_stats(port_id_0)

        vm0_ret_stats = self.calculate_stats(vm0_start_stats, vm0_end_stats)
        vm1_ret_stats = self.calculate_stats(vm1_start_stats, vm1_end_stats)

        self.verify(vm0_ret_stats['RX-packets'] == packet_num and
                    vm0_ret_stats['TX-packets'] == packet_num and
                    vm1_ret_stats['RX-packets'] == 2 * packet_num,
                    "Vlan and downlink mirror failed between VM0 and VM1 " +
                    "when set vlan, pool, uplink and downlink mirror!")

        self.reset_port_all_mirror_rule(port_id_0)

    def test_two_vms_add_multi_exact_mac_on_vf(self):
        self.setup_2vm_2vf_env()
        self.setup_two_vm_common_prerequisite()

        port_id_0 = 0
        vf_num = 0
        packet_num = 10

        for vf_mac in ["00:11:22:33:44:55", "00:55:44:33:22:11"]:
            self.host_testpmd.execute_cmd("mac_addr add port %d vf %d %s" %
                                          (port_id_0, vf_num, vf_mac))

            vm0_start_stats = self.vm0_testpmd.get_pmd_stats(port_id_0)
            ether_ip = {}
            ether_ip['ether'] = {'dest_mac': '%s' % vf_mac}
            self.send_packet(
                self.vm_dut_0,
                self.vm0_dut_ports,
                port_id_0,
                count=packet_num,
                **ether_ip)
            vm0_end_stats = self.vm0_testpmd.get_pmd_stats(port_id_0)

            vm0_ret_stats = self.calculate_stats(
                vm0_start_stats, vm0_end_stats)

            self.verify(vm0_ret_stats['RX-packets'] == packet_num,
                        "Add exact MAC %s failed btween VF0 and VF1" % vf_mac +
                        "when add multi exact MAC address on VF!")

    def test_two_vms_enalbe_or_disable_one_uta_mac_on_vf(self):
        self.setup_2vm_2vf_env()
        self.setup_two_vm_common_prerequisite()

        port_id_0 = 0
        vf_mac = "00:11:22:33:44:55"
        packet_num = 10

        self.host_testpmd.execute_cmd('set promisc %d on' % port_id_0)
        self.host_testpmd.execute_cmd(
            'set port %d vf 0 rxmode ROPE on' % port_id_0)
        self.host_testpmd.execute_cmd(
            'set port %d vf 1 rxmode ROPE off' % port_id_0)
        self.host_testpmd.execute_cmd(
            'set port %d uta %s on' % (port_id_0, vf_mac))

        vm0_start_stats = self.vm0_testpmd.get_pmd_stats(port_id_0)
        ether_ip = {}
        ether_ip['ether'] = {'dest_mac': '%s' % vf_mac}
        self.send_packet(self.vm_dut_0, self.vm0_dut_ports, port_id_0,
                         count=packet_num, **ether_ip)
        vm0_end_stats = self.vm0_testpmd.get_pmd_stats(port_id_0)

        vm0_ret_stats = self.calculate_stats(vm0_start_stats, vm0_end_stats)

        self.verify(vm0_ret_stats['RX-packets'] == packet_num,
                    "Enable one uta MAC failed between VM0 and VM1 " +
                    "when enable or disable one uta MAC address on VF!")

        self.host_testpmd.execute_cmd('set promisc %d off' % port_id_0)
        self.host_testpmd.execute_cmd(
            'set port %d vf 0 rxmode ROPE off' % port_id_0)

        vm0_start_stats = self.vm0_testpmd.get_pmd_stats(port_id_0)
        ether_ip = {}
        ether_ip['ether'] = {'dest_mac': '%s' % vf_mac}
        self.send_packet(self.vm_dut_0, self.vm0_dut_ports, port_id_0,
                         count=packet_num, invert_verify=True, **ether_ip)
        vm0_end_stats = self.vm0_testpmd.get_pmd_stats(port_id_0)

        vm0_ret_stats = self.calculate_stats(vm0_start_stats, vm0_end_stats)

        self.verify(vm0_ret_stats['RX-packets'] == 0,
                    "Disable one uta MAC failed between VM0 and VM1 " +
                    "when enable or disable one uta MAC address on VF!")

    def test_two_vms_add_multi_uta_mac_on_vf(self):
        self.setup_2vm_2vf_env()
        self.setup_two_vm_common_prerequisite()

        port_id_0 = 0
        packet_num = 10

        for vf_mac in ["00:55:44:33:22:11", "00:55:44:33:22:66"]:
            self.host_testpmd.execute_cmd("set port %d uta %s on" %
                                          (port_id_0, vf_mac))
            self.host_testpmd.execute_cmd("set port %d uta %s on" %
                                          (port_id_0, vf_mac))

        for vf_mac in ["00:55:44:33:22:11", "00:55:44:33:22:66"]:
            vm0_start_stats = self.vm0_testpmd.get_pmd_stats(port_id_0)
            ether_ip = {}
            ether_ip['ether'] = {'dest_mac': '%s' % vf_mac}
            self.send_packet(self.vm_dut_0, self.vm0_dut_ports,
                             port_id_0, count=packet_num, **ether_ip)
            vm0_end_stats = self.vm0_testpmd.get_pmd_stats(port_id_0)

            vm0_ret_stats = self.calculate_stats(
                vm0_start_stats, vm0_end_stats)

            self.verify(vm0_ret_stats['RX-packets'] == packet_num,
                        "Add MULTI uta MAC %s failed between VM0 and VM1 " % vf_mac +
                        "when add multi uta MAC address on VF!")

    def test_two_vms_add_or_remove_uta_mac_on_vf(self):
        self.setup_2vm_2vf_env()
        self.setup_two_vm_common_prerequisite()

        port_id_0 = 0
        vf_mac = "00:55:44:33:22:11"
        packet_num = 10

        for switch in ['on', 'off', 'on']:
            self.host_testpmd.execute_cmd("set port %d uta %s %s" %
                                          (port_id_0, vf_mac, switch))

            vm0_start_stats = self.vm0_testpmd.get_pmd_stats(port_id_0)
            ether_ip = {}
            ether_ip['ether'] = {'dest_mac': '%s' % vf_mac}
            if switch == 'on':
                self.send_packet(self.vm_dut_0, self.vm0_dut_ports,
                                 port_id_0, count=packet_num, **ether_ip)
            else:
                self.send_packet(self.vm_dut_0, self.vm0_dut_ports, port_id_0,
                                 count=packet_num, invert_verify=True, **ether_ip)
            vm0_end_stats = self.vm0_testpmd.get_pmd_stats(port_id_0)

            vm0_ret_stats = self.calculate_stats(
                vm0_start_stats, vm0_end_stats)

            if switch == 'on':
                self.verify(vm0_ret_stats['RX-packets'] == packet_num,
                            "Add MULTI uta MAC %s failed between VM0 and VM1 " % vf_mac +
                            "when add or remove multi uta MAC address on VF!")
            else:
                self.verify(vm0_ret_stats['RX-packets'] == 0,
                            "Remove MULTI uta MAC %s failed between VM0 and VM1 " % vf_mac +
                            "when add or remove multi uta MAC address on VF!")

    def test_two_vms_pause_rx_queues(self):
        self.setup_2vm_2vf_env()
        self.setup_two_vm_common_prerequisite()

        port_id_0 = 0
        packet_num = 10

        for switch in ['on', 'off', 'on']:
            self.host_testpmd.execute_cmd("set port %d vf 0 rx %s" %
                                          (port_id_0, switch))

            vm0_start_stats = self.vm0_testpmd.get_pmd_stats(port_id_0)
            if switch == 'on':
                self.send_packet(self.vm_dut_0, self.vm0_dut_ports,
                                 port_id_0, count=packet_num)
            else:
                self.send_packet(self.vm_dut_0, self.vm0_dut_ports, port_id_0,
                                 count=packet_num, invert_verify=True)
            vm0_end_stats = self.vm0_testpmd.get_pmd_stats(port_id_0)

            vm0_ret_stats = self.calculate_stats(
                vm0_start_stats, vm0_end_stats)

            if switch == 'on':
                self.verify(vm0_ret_stats['RX-packets'] == packet_num,
                            "Enable RX queues failed between VM0 and VM1 " +
                            "when enable or pause RX queues on VF!")
            else:
                self.verify(vm0_ret_stats['RX-packets'] == 0,
                            "Pause RX queues failed between VM0 and VM1 " +
                            "when enable or pause RX queues on VF!")

    def test_two_vms_pause_tx_queuse(self):
        self.setup_2vm_2vf_env()
        self.setup_two_vm_common_prerequisite()

        self.vm0_testpmd.execute_cmd("stop")
        self.vm0_testpmd.execute_cmd("set fwd mac")
        self.vm0_testpmd.execute_cmd("start")

        port_id_0 = 0
        packet_num = 10

        for switch in ['on', 'off', 'on']:
            self.host_testpmd.execute_cmd("set port %d vf 0 tx %s" %
                                          (port_id_0, switch))

            vm0_start_stats = self.vm0_testpmd.get_pmd_stats(port_id_0)
            self.send_packet(
                self.vm_dut_0,
                self.vm0_dut_ports,
                port_id_0,
                count=packet_num)
            vm0_end_stats = self.vm0_testpmd.get_pmd_stats(port_id_0)

            vm0_ret_stats = self.calculate_stats(
                vm0_start_stats, vm0_end_stats)

            if switch == 'on':
                self.verify(vm0_ret_stats['TX-packets'] == packet_num,
                            "Enable TX queues failed between VM0 and VM1 " +
                            "when enable or pause TX queues on VF!")
            else:
                self.verify(vm0_ret_stats['TX-packets'] == 0,
                            "Pause TX queues failed between VM0 and VM1 " +
                            "when enable or pause TX queues on VF!")

    def test_two_vms_prevent_rx_broadcast_on_vf(self):
        self.setup_2vm_2vf_env()
        self.setup_two_vm_common_prerequisite()

        port_id_0 = 0
        vf_mac = "FF:FF:FF:FF:FF:FF"
        packet_num = 10

        for switch in ['on', 'off', 'on']:
            self.host_testpmd.execute_cmd("set port %d vf 0 rxmode BAM %s" %
                                          (port_id_0, switch))

            vm0_start_stats = self.vm0_testpmd.get_pmd_stats(port_id_0)
            ether_ip = {}
            ether_ip['ether'] = {'dest_mac': '%s' % vf_mac}
            if switch == 'on':
                self.send_packet(self.vm_dut_0, self.vm0_dut_ports, port_id_0,
                                 count=packet_num, **ether_ip)
            else:
                self.send_packet(self.vm_dut_0, self.vm0_dut_ports, port_id_0,
                                 count=packet_num, invert_verify=True, **ether_ip)
            vm0_end_stats = self.vm0_testpmd.get_pmd_stats(port_id_0)

            vm0_ret_stats = self.calculate_stats(
                vm0_start_stats, vm0_end_stats)

            if switch == 'on':
                self.verify(vm0_ret_stats['RX-packets'] == packet_num,
                            "Enable RX broadcast failed between VM0 and VM1 " +
                            "when enable or disable RX queues on VF!")
            else:
                self.verify(vm0_ret_stats['RX-packets'] == 0,
                            "Disable RX broadcast failed between VM0 and VM1 " +
                            "when enable or pause TX queues on VF!")

    def test_two_vms_negative_input_commands(self):
        self.setup_2vm_2vf_env()
        self.setup_two_vm_common_prerequisite()

        for command in ["set port 0 vf 65 tx on",
                        "set port 2 vf -1 tx off",
                        "set port 0 vf 0 rx oneee",
                        "set port 0 vf 0 rx offdd",
                        "set port 0 vf 64 rxmode BAM on",
                        "set port 0 vf 64 rxmode BAM off",
                        "set port 0 uta 00:11:22:33:44 on",
                        "set port 7 uta 00:55:44:33:22:11 off",
                        "set port 0 vf 34 rxmode ROPE on",
                        "mac_addr add port 0 vf 65 00:55:44:33:22:11",
                        "mac_addr add port 5 vf 0 00:55:44:88:22:11",
                        "set port 0 mirror-rule 0xf uplink-mirror dst-pool 1 on",
                        "set port 0 mirror-rule 2 vlan-mirror 9 dst-pool 1 on",
                        "set port 0 mirror-rule 0 downlink-mirror 0xf dst-pool 2 off",
                        "reset port 0 mirror-rule 4",
                        "reset port 0xff mirror-rule 0"]:
            output = self.host_testpmd.execute_cmd(command)
            error = False

            for error_regx in [r'Bad', r'bad', r'failed', r'-[0-9]+', r'error', r'Invalid']:
                ret_regx = re.search(error_regx, output)
                if ret_regx and ret_regx.group():
                    error = True
                    break
            self.verify(
                error, "Execute command '%s' successfully, it should be failed!" % command)

    def tear_down(self):
        if self.setup_2vm_prerequisite_flag == 1:
            self.destroy_two_vm_common_prerequisite()
        if self.setup_2vm_2vf_env_flag == 1:
            self.destroy_2vm_2vf_env()

        if self.setup_2vm_2pf_env_flag == 1:
            slef.destroy_2vm_2pf_env()

        if self.setup_4vm_prerequisite_flag == 1:
            self.destroy_four_vm_common_prerequisite()
        if self.setup_4vm_4vf_env_flag == 1:
            self.destroy_4vm_4vf_env()

    def tear_down_all(self):
        if getattr(self, 'vm0', None):
            self.vm0.stop()
        if getattr(self, 'vm1', None):
            self.vm1.stop()
        if getattr(self, 'vm2', None):
            self.vm2.stop()
        if getattr(self, 'vm3', None):
            self.vm3.stop()

        for port_id in self.dut_ports:
            self.dut.destroy_sriov_vfs_by_port(port_id)
