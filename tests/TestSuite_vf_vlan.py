# <COPYRIGHT_TAG>

import re
import time

import dts
from qemu_kvm import QEMUKvm
from test_case import TestCase
from pmd_output import PmdOutput
from packet import Packet, sniff_packets, load_sniff_packets
from settings import get_nic_name
import random

VM_CORES_MASK = 'all'
MAX_VLAN = 4095


class TestVfVlan(TestCase):

    def set_up_all(self):

        self.dut_ports = self.dut.get_ports(self.nic)
        self.verify(len(self.dut_ports) > 1, "Insufficient ports")
        self.vm0 = None
        self.env_done = False

    def set_up(self):
        self.setup_vm_env()

    def bind_nic_driver(self, ports, driver=""):
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

    def setup_vm_env(self, driver='default'):
        """
        Create testing environment with 2VFs generated from 2PFs
        """
        if self.env_done:
            return

        # bind to default driver
        self.bind_nic_driver(self.dut_ports[:2], driver="")

        self.used_dut_port_0 = self.dut_ports[0]
        self.host_intf0 = self.dut.ports_info[self.used_dut_port_0]['intf']
        tester_port = self.tester.get_local_port(self.used_dut_port_0)
        self.tester_intf0 = self.tester.get_interface(tester_port)

        self.dut.generate_sriov_vfs_by_port(
            self.used_dut_port_0, 1, driver=driver)
        self.sriov_vfs_port_0 = self.dut.ports_info[
            self.used_dut_port_0]['vfs_port']
        self.vf0_mac = "00:10:00:00:00:00"
        self.dut.send_expect("ip link set %s vf 0 mac %s" %
                             (self.host_intf0, self.vf0_mac), "# ")

        self.used_dut_port_1 = self.dut_ports[1]
        self.host_intf1 = self.dut.ports_info[self.used_dut_port_1]['intf']
        self.dut.generate_sriov_vfs_by_port(
            self.used_dut_port_1, 1, driver=driver)
        self.sriov_vfs_port_1 = self.dut.ports_info[
            self.used_dut_port_1]['vfs_port']
        tester_port = self.tester.get_local_port(self.used_dut_port_1)
        self.tester_intf1 = self.tester.get_interface(tester_port)

        self.vf1_mac = "00:20:00:00:00:00"
        self.dut.send_expect("ip link set %s vf 0 mac %s" %
                             (self.host_intf1, self.vf1_mac), "# ")

        try:

            for port in self.sriov_vfs_port_0:
                port.bind_driver('pci-stub')

            for port in self.sriov_vfs_port_1:
                port.bind_driver('pci-stub')

            time.sleep(1)
            vf0_prop = {'opt_host': self.sriov_vfs_port_0[0].pci}
            vf1_prop = {'opt_host': self.sriov_vfs_port_1[0].pci}

            # set up VM0 ENV
            self.vm0 = QEMUKvm(self.dut, 'vm0', 'vf_vlan')
            self.vm0.set_vm_device(driver='pci-assign', **vf0_prop)
            self.vm0.set_vm_device(driver='pci-assign', **vf1_prop)
            self.vm_dut_0 = self.vm0.start()
            if self.vm_dut_0 is None:
                raise Exception("Set up VM0 ENV failed!")

        except Exception as e:
            self.destroy_vm_env()
            raise Exception(e)

        self.env_done = True

    def destroy_vm_env(self):
        if getattr(self, 'vm0', None):
            self.vm_dut_0.kill_all()
            self.vm0_testpmd = None
            self.vm0_dut_ports = None
            # destroy vm0
            self.vm0.stop()
            self.vm0 = None

        if getattr(self, 'used_dut_port_0', None):
            self.dut.destroy_sriov_vfs_by_port(self.used_dut_port_0)
            port = self.dut.ports_info[self.used_dut_port_0]['port']
            self.used_dut_port_0 = None

        if getattr(self, 'used_dut_port_1', None):
            self.dut.destroy_sriov_vfs_by_port(self.used_dut_port_1)
            port = self.dut.ports_info[self.used_dut_port_1]['port']
            self.used_dut_port_1 = None

        self.bind_nic_driver(self.dut_ports[:2], driver="igb_uio")

        self.env_done = False

    def test_pvid_vf_tx(self):
        """
        Add port based vlan on vf device and check vlan tx work
        """
        random_vlan = random.randint(1, MAX_VLAN)

        self.dut.send_expect(
            "ip link set %s vf 0 vlan %d" % (self.host_intf0, random_vlan), "# ")
        out = self.dut.send_expect("ip link show %s" % self.host_intf0, "# ")
        self.verify("vlan %d" %
                    random_vlan in out, "Failed to add pvid on VF0")

        self.vm0_dut_ports = self.vm_dut_0.get_ports('any')

        self.vm0_testpmd = PmdOutput(self.vm_dut_0)
        self.vm0_testpmd.start_testpmd(VM_CORES_MASK)
        self.vm0_testpmd.execute_cmd('set fwd mac')
        self.vm0_testpmd.execute_cmd('start')

        pkt = Packet(pkt_type='UDP')
        pkt.config_layer('ether', {'dst': self.vf1_mac})
        inst = sniff_packets(self.tester_intf0, timeout=5)
        pkt.send_pkt(tx_port=self.tester_intf1)
        pkts = load_sniff_packets(inst)

        self.verify(len(pkts), "Not receive expected packet")
        self.vm0_testpmd.quit()

        # disable pvid
        self.dut.send_expect(
            "ip link set %s vf 0 vlan 0" % (self.host_intf0), "# ")

    def send_and_getout(self, vlan=0, pkt_type="UDP"):

        if pkt_type == "UDP":
            pkt = Packet(pkt_type='UDP')
            pkt.config_layer('ether', {'dst': self.vf0_mac})
        elif pkt_type == "VLAN_UDP":
            pkt = Packet(pkt_type='VLAN_UDP')
            pkt.config_layer('dot1q', {'vlan': vlan})
            pkt.config_layer('ether', {'dst': self.vf0_mac})

        pkt.send_pkt(tx_port=self.tester_intf0)
        out = self.vm_dut_0.get_session_output(timeout=2)

        return out

    def test_add_pvid_vf(self):
        random_vlan = random.randint(1, MAX_VLAN)

        self.dut.send_expect(
            "ip link set %s vf 0 vlan %d" % (self.host_intf0, random_vlan), "# ")
        out = self.dut.send_expect("ip link show %s" % self.host_intf0, "# ")
        self.verify("vlan %d" %
                    random_vlan in out, "Failed to add pvid on VF0")

        # start testpmd in VM
        self.vm0_dut_ports = self.vm_dut_0.get_ports('any')

        self.vm0_testpmd = PmdOutput(self.vm_dut_0)
        self.vm0_testpmd.start_testpmd(VM_CORES_MASK)
        self.vm0_testpmd.execute_cmd('set fwd rxonly')
        self.vm0_testpmd.execute_cmd('set verbose 1')
        self.vm0_testpmd.execute_cmd('start')

        out = self.send_and_getout(vlan=random_vlan, pkt_type="VLAN_UDP")
        self.verify("received" in out, "Failed to received vlan packet!!!")

        # send packet without vlan
        out = self.send_and_getout(pkt_type="UDP")
        self.verify("received" not in out, "Received packet without vlan!!!")

        # send packet with vlan not matched
        wrong_vlan = (random_vlan + 1) % 4096
        out = self.send_and_getout(vlan=wrong_vlan, pkt_type="VLAN_UDP")
        self.verify(
            "received" not in out, "Received pacekt with wrong vlan!!!")

        # remove vlan
        self.dut.send_expect(
            "ip link set %s vf 0 vlan 0" % self.host_intf0, "# ")

        # send packet with vlan
        out = self.send_and_getout(vlan=random_vlan, pkt_type="VLAN_UDP")
        self.verify(
            "received" not in out, "Received vlan packet without pvid!!!")

        # send packe with vlan 0
        out = self.send_and_getout(vlan=0, pkt_type="VLAN_UDP")
        self.verify(
            "received" in out, "Not recevied packet with vlan 0!!!")

        # send packet without vlan
        out = self.send_and_getout(vlan=0, pkt_type="UDP")
        self.verify("received" in out, "Not received packet without vlan!!!")

        self.vm0_testpmd.quit()

        # disable pvid
        self.dut.send_expect(
            "ip link set %s vf 0 vlan 0" % (self.host_intf0), "# ")

    def tx_and_check(self, tx_vlan=1):
        inst = sniff_packets(self.tester_intf0, timeout=5)
        self.vm0_testpmd.execute_cmd('set burst 1')
        self.vm0_testpmd.execute_cmd('start tx_first')
        self.vm0_testpmd.execute_cmd('stop')

        # strip sniffered vlans
        pkts = load_sniff_packets(inst)
        vlans = []
        for pkt in pkts:
            vlan = pkt.strip_element_dot1q("vlan")
            vlans.append(vlan)

        self.verify(
            tx_vlan in vlans, "Tx packet with vlan not received!!!")

    def test_vf_vlan_tx(self):
        random_vlan = random.randint(1, MAX_VLAN)
        tx_vlans = [1, random_vlan, MAX_VLAN]
        # start testpmd in VM
        self.vm0_dut_ports = self.vm_dut_0.get_ports('any')

        self.vm0_testpmd = PmdOutput(self.vm_dut_0)
        self.vm0_testpmd.start_testpmd(VM_CORES_MASK)
        self.vm0_testpmd.execute_cmd('set verbose 1')

        for tx_vlan in tx_vlans:
            # for fortville ,
            # if you want insert tx_vlan,
            # please enable rx_vlan at the same time
            if self.kdriver == "i40e":
                self.vm0_testpmd.execute_cmd('rx_vlan add %d 0' % tx_vlan)
            self.vm0_testpmd.execute_cmd('tx_vlan set 0 %d' % tx_vlan)
            self.tx_and_check(tx_vlan=tx_vlan)

        self.vm0_testpmd.quit()

    def test_vf_vlan_rx(self):
        random_vlan = random.randint(1, MAX_VLAN - 1)
        rx_vlans = [1, random_vlan, MAX_VLAN]
        # start testpmd in VM
        self.vm0_dut_ports = self.vm_dut_0.get_ports('any')

        self.vm0_testpmd = PmdOutput(self.vm_dut_0)
        self.vm0_testpmd.start_testpmd(VM_CORES_MASK)
        self.vm0_testpmd.execute_cmd('set fwd rxonly')
        self.vm0_testpmd.execute_cmd('set verbose 1')
        self.vm0_testpmd.execute_cmd('vlan set strip on 0')
        self.vm0_testpmd.execute_cmd('start')

        # send packet without vlan
        out = self.send_and_getout(vlan=0, pkt_type="UDP")
        self.verify(
            "received 1 packets" in out, "Not received normal packet as default!!!")

        # send packet with vlan 0
        out = self.send_and_getout(vlan=0, pkt_type="VLAN_UDP")
        self.verify("VLAN tci=0x0"
                    in out, "Not received vlan 0 packet as default!!!")

        for rx_vlan in rx_vlans:
            self.vm0_testpmd.execute_cmd('rx_vlan add %d 0' % rx_vlan)
            time.sleep(1)
            # send packet with same vlan
            out = self.send_and_getout(vlan=rx_vlan, pkt_type="VLAN_UDP")
            vlan_hex = hex(rx_vlan)
            self.verify("VLAN tci=%s" %
                        vlan_hex in out, "Not received expected vlan packet!!!")

            pkt = Packet(pkt_type='VLAN_UDP')
            if rx_vlan == MAX_VLAN:
                continue
            wrong_vlan = (rx_vlan + 1) % 4096

            # send packet with wrong vlan
            out = self.send_and_getout(vlan=wrong_vlan, pkt_type="VLAN_UDP")
            self.verify(
                "received 1 packets" not in out, "Received filtered vlan packet!!!")

        for rx_vlan in rx_vlans:
            self.vm0_testpmd.execute_cmd('rx_vlan rm %d 0' % rx_vlan)

        # send packet with vlan 0
        out = self.send_and_getout(vlan=0, pkt_type="VLAN_UDP")
        self.verify("VLAN tci=0x0"
                    in out, "Not received vlan 0 packet as default!!!")

        # send packet without vlan
        out = self.send_and_getout(pkt_type="UDP")
        self.verify("received 1 packets" in out,
                    "Not received normal packet after remove vlan filter!!!")

        # send packet with vlan
        out = self.send_and_getout(vlan=random_vlan, pkt_type="VLAN_UDP")
        self.verify(
            "received 1 packets" in out, "Not received vlan packet without vlan filter!!!")

        self.vm0_testpmd.quit()

    def test_vf_vlan_strip(self):
        random_vlan = random.randint(1, MAX_VLAN - 1)
        rx_vlans = [1, random_vlan, MAX_VLAN]
        # start testpmd in VM
        self.vm0_dut_ports = self.vm_dut_0.get_ports('any')

        self.vm0_testpmd = PmdOutput(self.vm_dut_0)
        self.vm0_testpmd.start_testpmd(VM_CORES_MASK)
        self.vm0_testpmd.execute_cmd('set fwd rxonly')
        self.vm0_testpmd.execute_cmd('set verbose 1')
        self.vm0_testpmd.execute_cmd('start')

        for rx_vlan in rx_vlans:
            self.vm0_testpmd.execute_cmd('vlan set strip on 0')
            self.vm0_testpmd.execute_cmd('rx_vlan add %d 0' % rx_vlan)
            time.sleep(1)
            out = self.send_and_getout(vlan=rx_vlan, pkt_type="VLAN_UDP")
            # enable strip, vlan will be in mbuf
            vlan_hex = hex(rx_vlan)
            self.verify("VLAN tci=%s" %
                        vlan_hex in out, "Failed to strip vlan packet!!!")

            self.vm0_testpmd.execute_cmd('vlan set strip off 0')

            out = self.send_and_getout(vlan=rx_vlan, pkt_type="VLAN_UDP")
            self.verify(
                "received 1 packets" in out, "Not received vlan packet as expected!!!")
            nic_type = self.vm_dut_0.ports_info[0]['type']
            nic_name = get_nic_name(nic_type)
            if nic_name in ['fvl10g_vf']:
                self.verify("VLAN tci=%s" %
                            vlan_hex in out, "Failed to disable strip vlan!!!")
            else:
                self.verify(
                    "VLAN tci=0x0" in out, "Failed to disable strip vlan!!!")

        self.vm0_testpmd.quit()

    def tear_down(self):
        self.vm_dut_0.kill_all()
        pass

    def tear_down_all(self):
        self.destroy_vm_env()
        pass
