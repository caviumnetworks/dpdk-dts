"""
DPDK Test suite.

Test Cloud Filters features in DPDK.

"""

import string
import re
import time
import os
from test_case import TestCase
from pmd_output import PmdOutput
from settings import HEADER_SIZE
from packet import Packet, load_pcapfile

from scapy.layers.inet import UDP, IP
from scapy.packet import split_layers, bind_layers

from vxlan import Vxlan
from vxlan import VXLAN_PORT

CLOUD_PORT = 8472
split_layers(UDP, Vxlan, dport=VXLAN_PORT)
bind_layers(UDP, Vxlan, dport=CLOUD_PORT)

#
#
# Test class.
#


class CloudFilterConfig(object):

    """
    Module for config/verify cloud filter rule
    """

    RULE_TYPE = [
        'iip', 'imac', 'omac+imac+vni', 'imac+ivlan+vni', 'imac+ivlan']

    def __init__(self, test_case, pf_intf=""):
        self.case = test_case
        # make sure pf existed
        out = self.case.dut.send_expect(
            'ifconfig %s' % pf_intf, "#", alt_session=True)
        self.case.verify("Device not found" not in out,
                         "Cloud filter need PF interface!!!")
        self.pf_intf = pf_intf
        self.pkt = Packet()

    def config_rule(self, **kwargs):
        """
        Configure cloud filter rule settings, must check rule format
        """
        self.rule_idx = 1
        self.case.verify(
            'type' in kwargs, "Cloud filter rule must configure filter type")
        rule_type = kwargs['type']
        self.case.verify(
            rule_type in self.RULE_TYPE, "Cloud filter rule type not correct")
        self.case.verify(
            'vf' in kwargs, "Cloud filter rule must configure device!!!")
        self.case.verify(
            'queue' in kwargs, "Cloud filter rule must configure queue index")
        if 'loc' in kwargs:
            self.rule_idx = kwargs['loc']

        self.cf_rule = {}
        self.cf_rule['type'] = rule_type
        self.cf_rule['vf'] = kwargs['vf']
        self.cf_rule['queue'] = kwargs['queue']

        required_args = rule_type.split('+')
        for required_arg in required_args:
            self.case.verify(required_arg in kwargs,
                             "Argument for [%s] missing!!!" % required_arg)
            self.cf_rule[required_arg] = kwargs[required_arg]

        if 'ivlan' in self.cf_rule:
            self.pkt.assign_layers(['ether', 'ipv4', 'udp',
                                    'vxlan', 'inner_mac', 'inner_vlan',
                                    'inner_ipv4', 'inner_tcp', 'raw'])
        else:
            self.pkt.assign_layers(['ether', 'ipv4', 'udp',
                                    'vxlan', 'inner_mac',
                                    'inner_ipv4', 'inner_tcp', 'raw'])

    def ethtool_add(self):
        """
        Add cloud filter rule by ethtool and return rule index
        """
        ip_fmt = "ethtool -N %(PF)s flow-type ip4 dst-ip %(IP)s user-def " + \
            "%(VNI_VF)s action %(QUEUE)d loc %(ID)d"
        ether_fmt = "ethtool -N %(PF)s flow-type ether dst %(OMAC)s m " + \
            "%(OMASK)s src %(IMAC)s m %(IMASK)s user-def %(VNI_VF)s " + \
            "action %(QUEUE)d loc %(ID)d"
        ether_vlan_fmt = "ethtool -N %(PF)s flow-type ether dst %(OMAC)s m " + \
            "%(OMASK)s src %(IMAC)s m %(IMASK)s vlan %(VLAN)d " + \
            "user-def %(VNI_VF)s action %(QUEUE)d loc %(ID)d"


        # generate user define field
        vni_vf = '0x'
        if 'vni' in self.cf_rule:
            vni_str = hex(self.cf_rule['vni'])[2:]
        else:
            vni_str = 'ffffffff'  # without vni
        vni_vf += vni_str
        vf_str = "%08x" % self.cf_rule['vf']
        vni_vf += vf_str

        if 'omac' in self.cf_rule:
            omac_str = self.cf_rule['omac']
            omac_mask = '00:00:00:00:00:00'
        else:
            omac_str = '00:00:00:00:00:00'
            omac_mask = 'ff:ff:ff:ff:ff:ff'

        if 'imac' in self.cf_rule:
            imac_str = self.cf_rule['imac']
            imac_mask = '00:00:00:00:00:00'
        else:
            imac_str = '00:00:00:00:00:00'
            imac_mask = 'ff:ff:ff:ff:ff:ff'

        if 'iip' in self.cf_rule:
            ip_str = self.cf_rule['iip']

        if self.cf_rule['type'] == 'iip':
            ethtool_cmd = ip_fmt % {'PF': self.pf_intf,
                                    'IP': ip_str,
                                    'VNI_VF': vni_vf,
                                    'QUEUE': self.cf_rule['queue'],
                                    'ID': self.rule_idx}
        elif 'ivlan' in self.cf_rule:
            ethtool_cmd = ether_vlan_fmt % {'PF': self.pf_intf,
                                       'OMAC': omac_str,
                                       'OMASK': omac_mask,
                                       'IMAC': imac_str,
                                       'IMASK': imac_mask,
                                       'VLAN': self.cf_rule['ivlan'],
                                       'VNI_VF': vni_vf,
                                       'QUEUE': self.cf_rule['queue'],
                                       'ID': self.rule_idx}
        else:
            ethtool_cmd = ether_fmt % {'PF': self.pf_intf,
                                       'OMAC': omac_str,
                                       'OMASK': omac_mask,
                                       'IMAC': imac_str,
                                       'IMASK': imac_mask,
                                       'VNI_VF': vni_vf,
                                       'QUEUE': self.cf_rule['queue'],
                                       'ID': self.rule_idx}

        print ethtool_cmd
        out = self.case.dut.send_expect(ethtool_cmd, "# ", alt_session=True)
        self.case.verify("ethtool" not in out, "Add cloud filter failed!!!")

        return self.rule_idx

    def ethtool_delete(self):
        """
        Delete cloud filter rule by index and return whether success
        """
        self.case.dut.send_expect("ethtool -N %s delete %d" % (self.pf_intf,
                                                               self.rule_idx),
                                  "# ", alt_session=True)

    def ethtool_dumprule(self):
        """
        Dump cloud filter rule according to index value
        """
        pass

    def transmit_packet(self, match=True):
        """
        Send packet match or not matched cloud filter rules
        """
        ether_cfg = {'src': self.case.tester_mac}
        if match:
            if 'iip' in self.cf_rule.keys():
                self.pkt.config_layer(
                    'inner_ipv4', {'dst': self.cf_rule['iip']})
            if 'imac' in self.cf_rule.keys():
                self.pkt.config_layer(
                    'inner_mac', {'dst': self.cf_rule['imac']})
            if 'omac' in self.cf_rule.keys():
                ether_cfg['dst'] = self.cf_rule['omac']
            if 'ivlan' in self.cf_rule.keys():
                self.pkt.config_layer(
                    'inner_vlan', {'vlan': self.cf_rule['ivlan']})
            if 'vni' in self.cf_rule.keys():
                self.pkt.config_layer('vxlan', {'vni': self.cf_rule['vni']})

        self.pkt.config_layer('ether', ether_cfg)
        self.pkt.config_layer('raw', {'payload': ['01'] * 18})
        self.pkt.send_pkt(tx_port=self.case.tester_intf)


class TestCloudFilter(TestCase):

    def set_up_all(self):
        """
        vxlan Prerequisites
        """
        # this feature only enable in FVL now
        self.verify(self.nic in ["fortville_eagle", "fortville_spirit",
                                 "fortville_spirit_single"],
                    "Cloud filter only supported by Fortville")
        # Based on h/w type, choose how many ports to use
        self.dut_ports = self.dut.get_ports()

        # Verify that enough ports are available
        self.verify(len(self.dut_ports) >= 1, "Insufficient ports for testing")

        # required setting test environment
        self.env_done = False
        self.vf_queues = 4

    def setup_vf_env(self):
        """
        Create testing environment with 2VFs generated from PF
        """
        if self.env_done:
            return

        # get PF interface name and opposite tester interface name
        self.pf_port = self.dut_ports[0]
        self.bind_nics_driver([self.pf_port], driver="i40e")
        self.pf_intf = self.dut.ports_info[self.pf_port]['intf']
        tester_port = self.tester.get_local_port(self.pf_port)
        self.tester_intf = self.tester.get_interface(tester_port)
        self.tester_mac = self.tester.get_mac(tester_port)
        pf_numa = self.dut.get_numa_id(self.pf_port)

        self.dut.generate_sriov_vfs_by_port(self.pf_port, 2, driver="default")

        # enable vxlan on PF
        self.dut.send_expect("ip li add vxlan0 type vxlan id 1 group " +
                             "239.1.1.1 local 127.0.0.1 dev %s" % self.pf_intf,
                             "# ")
        self.dut.send_expect("ifconfig vxlan0 up", "# ")

        self.vf_port0 = self.dut.ports_info[self.pf_port]['vfs_port'][0]
        self.vf_port1 = self.dut.ports_info[self.pf_port]['vfs_port'][1]

        # bind one vf device to dpdk
        self.vf_port0.bind_driver(driver='igb_uio')
        self.vf_port1.bind_driver(driver='i40evf')
        self.vf_intf = self.vf_port1.intf_name

        # bind vf0 to igb_uio and start testpmd
        core_num = self.vf_queues + 1
        cores = "1S/%dC/1T" % core_num

        self.pmdout = PmdOutput(self.dut)
        self.pmdout.start_testpmd(
            cores, "--rxq=%d --txq=%d --portmask=0x1 --enable-rx-cksum" %
            (self.vf_queues, self.vf_queues), socket=pf_numa)

        # rxonly and verbose enabled
        self.pmdout.execute_cmd("set nbcore %d" % self.vf_queues)
        self.pmdout.execute_cmd("set fwd rxonly")
        self.pmdout.execute_cmd("set verbose 1")
        self.pmdout.execute_cmd("start")

        self.env_done = True

    def destroy_vf_env(self):

        if getattr(self, 'pmd_output', None):
            self.dut.kill_all()

        if getattr(self, 'pf_port', None):
            self.dut.destroy_sriov_vfs_by_port(self.pf_port)
            self.bind_nics_driver([self.pf_port], driver="igb_uio")

        self.env_done = False

    def bind_nics_driver(self, ports, driver=""):
        # modprobe vfio driver
        if driver == "vfio-pci":
            for port in ports:
                netdev = self.dut.ports_info[port]['port']
                driver = netdev.get_nic_driver()
                if driver != 'vfio-pci':
                    netdev.bind_driver(driver='vfio-pci')

        elif driver == "igb_uio":
            # igb_uio should insmod as default, no need to check
            for port in ports:
                netdev = self.dut.ports_info[port]['port']
                driver = netdev.get_nic_driver()
                if driver != 'igb_uio':
                    netdev.bind_driver(driver='igb_uio')
        else:
            for port in ports:
                netdev = self.dut.ports_info[port]['port']
                driver_now = netdev.get_nic_driver()
                if driver == "":
                    driver = netdev.default_driver
                if driver != driver_now:
                    netdev.bind_driver(driver=driver)

    def send_and_verify(self, cloud_cfg=None, dpdk=True):
        """
        Send packet match cloud filter rule and verify packet received
        """
        self.logger.info("Verifying vxlan %s filter" % cloud_cfg.cf_rule['type'])
        if dpdk:
            cloud_cfg.transmit_packet()
            out = self.pmdout.get_output()
            print out
            queue = cloud_cfg.cf_rule['queue']
            self.verify("queue %d" %
                        queue in out, "Vxlan not received in queue %d" % queue)
            self.verify("VXLAN packet" in out, "Vxlan packet not detected")
            self.verify("Inner L4 type: TCP" in out,
                        "Vxlan inner L4 type not detected")
            if 'vni' in cloud_cfg.cf_rule.keys():
                vni = cloud_cfg.cf_rule['vni']
                self.verify("VNI = %d" %
                            vni in out, "Vxlan vni value not correct")
            if 'ivlan' in cloud_cfg.cf_rule.keys():
                self.verify("Inner L2 type: ETHER_VLAN" in out,
                            "Vxlan inner vlan not detected")
        else:
            # packet recevied on dut VF device
            tmp_file = '/tmp/cloud_filter_%s.pcap' % self.vf_intf
            sniff_cmd = ('tcpdump -w ' + tmp_file +
                         ' -i {0} 2>tcpdump_{0}.out &').format(self.vf_intf)
            rm_cmd = 'rm -f ' + tmp_file
            self.dut.send_expect(rm_cmd, '#', alt_session=True)
            self.dut.send_expect(sniff_cmd, '#', alt_session=True)
            # wait for interface promisc enable
            time.sleep(2)
            cloud_cfg.transmit_packet()
            self.dut.send_expect('killall tcpdump', '#', alt_session=True)
            # wait for pcap file saved
            time.sleep(2)
            # copy pcap to tester and then analyze
            self.dut.session.copy_file_from(tmp_file)
            pkts = load_pcapfile(
                filename="cloud_filter_%s.pcap" % self.vf_intf)
            self.verify(
                len(pkts) == 1, "%d packet recevied on kernel VF" % len(pkts))
            cap_pkt = pkts[0].pktgen.pkt
            try:
                dport = cap_pkt[UDP].dport
                self.verify(dport == CLOUD_PORT,
                            "Captured packet is not vxlan packet")
                inner_ip = cap_pkt[Vxlan][IP].dst
                self.verify(inner_ip == cloud_cfg.cf_rule['iip'],
                            "Inner ip not matched")
            except:
                print "Kernel VF captured packet not match rule"
                raise

        self.logger.info("Verified vxlan %s filter pass" % cloud_cfg.cf_rule['type'])

    def test_cloud_filter(self):
        """
        Verify dpdk work with linux driver added cloud filter rule
        """
        # setting for cloud filter rule
        queue = self.vf_queues - 1
        vni = 1
        vlan = 1
        # add cloud filter rule
        rules = [
            {'type': 'iip', 'iip': '192.168.1.1',
             'vf': 0, 'queue': queue, 'loc': 1},
            {'type': 'imac', 'imac': '00:00:00:00:09:00',
             'vf': 0, 'queue': queue, 'loc': 1},
            {'type': 'omac+imac+vni', 'omac': '00:00:00:00:10:00',
             'imac': '00:00:00:00:09:00', 'vni': vni, 'vf': 0, 'queue': queue,
             'loc': 1},
            {'type': 'imac+ivlan+vni', 'imac': '00:00:00:00:09:00',
             'ivlan': vlan, 'vni': vni, 'vf': 0, 'queue': queue, 'loc': 1},
            {'type': 'imac+ivlan', 'imac': '00:00:00:00:09:00',
             'ivlan': vlan, 'vf': 0, 'queue': queue, 'loc': 1},
        ]
        cf_cfg = CloudFilterConfig(self, self.pf_intf)
        for rule in rules:
            cf_cfg.config_rule(**rule)
            cf_cfg.ethtool_add()

            self.send_and_verify(cf_cfg)

            cf_cfg.ethtool_delete()

    def test_bifurcated_driver(self):
        """
        Verify bifurcated driver work with dpdk VF and kernel VF
        """
        rules = [
            {'type': 'iip', 'iip': '192.168.1.1', 'vf': 0,
             'queue': self.vf_queues - 1, 'loc': 1},
            {'type': 'iip', 'iip': '192.168.2.1', 'vf': 1, 'queue': 0,
             'loc': 2}]

        dpdk_cfg = CloudFilterConfig(self, self.pf_intf)
        # fdir rule for dpdk VF
        dpdk_cfg.config_rule(**rules[0])
        dpdk_cfg.ethtool_add()
        self.send_and_verify(dpdk_cfg)
        # fdir rule for kernel VF
        kernel_cfg = CloudFilterConfig(self, self.pf_intf)
        kernel_cfg.config_rule(**rules[1])
        kernel_cfg.ethtool_add()
        self.send_and_verify(kernel_cfg, dpdk=False)

        pass

    def set_up(self):
        """
        Run before each test case.
        """
        self.setup_vf_env()
        pass

    def tear_down(self):
        """
        Run after each test case.
        """
        pass

    def tear_down_all(self):
        """
        Run after each test suite.
        """
        self.destroy_vf_env()
        pass
