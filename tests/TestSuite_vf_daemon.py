# <COPYRIGHT_TAG>

import time
import sys
import utils 
from scapy.utils import rdpcap

from qemu_kvm import QEMUKvm
from test_case import TestCase
from pmd_output import PmdOutput
from packet import Packet, sniff_packets, load_sniff_packets
from settings import get_nic_name
import random

VM_CORES_MASK = 'all'
MAX_VLAN = 4095


class Testvf_daemon(TestCase):

    def set_up_all(self):

        self.dut_ports = self.dut.get_ports(self.nic)
        self.verify(len(self.dut_ports) >= 1, "Insufficient ports")
        self.vm0 = None
        self.vm1 = None
        self.env_done = False


    def set_up(self):
        self.setup_vm_env()

    def bind_nic_driver(self, ports, driver=""):
        if driver == "igb_uio":
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


    def setup_vm_env(self, driver='igb_uio'):
        """
        Create testing environment with 2VFs generated from 1PF
        """
        if self.env_done:
            return

        self.bind_nic_driver(self.dut_ports[:1], driver="igb_uio")
        self.used_dut_port = self.dut_ports[0]
        tester_port = self.tester.get_local_port(self.used_dut_port)
        self.tester_intf = self.tester.get_interface(tester_port)
         
        self.dut.generate_sriov_vfs_by_port(
            self.used_dut_port, 2, driver=driver)
        self.sriov_vfs_port = self.dut.ports_info[
            self.used_dut_port]['vfs_port']
        for port in self.sriov_vfs_port:
                port.bind_driver('pci-stub')
        time.sleep(1)
        self.dut_testpmd = PmdOutput(self.dut)
        time.sleep(1)
        vf0_prop = {'opt_host': self.sriov_vfs_port[0].pci}
        
        # set up VM0 ENV
        self.vm0 = QEMUKvm(self.dut, 'vm0', 'vf_daemon')
        self.vm0.set_vm_device(driver='pci-assign', **vf0_prop)
        try:
            self.vm0_dut = self.vm0.start()
            if self.vm0_dut is None:
                raise Exception("Set up VM0 ENV failed!")
        except Exception as e:
            self.destroy_vm_env()
            raise Exception(e)
        
        self.vm0_dut_ports = self.vm0_dut.get_ports('any')
        self.vm0_testpmd = PmdOutput(self.vm0_dut)

        vf1_prop = {'opt_host': self.sriov_vfs_port[1].pci}
        self.vm1 = QEMUKvm(self.dut, 'vm1', 'vf_daemon')
        self.vm1.set_vm_device(driver='pci-assign', **vf1_prop)
        try:
            self.vm1_dut = self.vm1.start()
            if self.vm1_dut is None:
                raise Exception("Set up VM1 ENV failed!")
        except Exception as e:
            self.destroy_vm_env()
            raise Exception(e)
        self.vm1_dut_ports = self.vm1_dut.get_ports('any')
        self.vm1_testpmd = PmdOutput(self.vm1_dut)
        
        self.env_done = True

    def destroy_vm_env(self):
        
        if getattr(self, 'vm0', None):
            self.vm0_dut.kill_all()
            self.vm0_testpmd = None
            self.vm0_dut_ports = None
            # destroy vm0
            self.vm0.stop()
            self.vm0 = None

        if getattr(self, 'vm1', None):
            self.vm1_dut.kill_all()
            self.vm1_testpmd = None
            self.vm1_dut_ports = None
            # destroy vm1
            self.vm1.stop()
            self.vm1 = None

        if getattr(self, 'used_dut_port', None):
            self.dut.destroy_sriov_vfs_by_port(self.used_dut_port)
            port = self.dut.ports_info[self.used_dut_port]['port']
            self.used_dut_port = None

        self.env_done = False
    

    def send_packet(self, dst_mac, vlan_id, pktsize, num):
        """
        Generate packets and send them to dut 
        """
        if vlan_id == 0:
            pkt = Packet(pkt_type='UDP', pkt_len = pktsize)
        else:
            pkt = Packet(pkt_type='VLAN_UDP', pkt_len = pktsize)
            pkt.config_layer('vlan', {'vlan': vlan_id})
        pkt.config_layer('ether', {'dst': dst_mac})
        inst = sniff_packets(self.tester_intf, timeout=5)
        pkt.send_pkt(tx_port=self.tester_intf, count=num)
        return inst

    def strip_mac(self, inst, element = "src"):     
        """
        Load sniff packets, strip and return mac address from dump message
        """
        pkts = load_sniff_packets(inst)
        macs = []
        for pkt in pkts:
            mac = pkt.strip_element_layer2(element)
            macs.append(mac)
        return macs

    def strip_vlan(self, inst):
        """
        Load sniff packets, strip and return vlan id from dump message
        """
        pkts = load_sniff_packets(inst)
        vlans = []
        for pkt in pkts:
            vlan = pkt.strip_element_vlan("vlan")
            vlans.append(vlan)
        return vlans
        

    def send_and_pmdout(self, dst_mac, vlan_id = 0, pktsize = 64 , num = 1):
        """
        Send packets to dut and return testpmd output message
        Input: dst_mac, vlan_id, packet size, packet number
        Output: testpmd output message
        """
        inst = self.send_packet(dst_mac, vlan_id , pktsize, num)
        out = self.vm0_dut.get_session_output(timeout=2)
        return out

    def send_and_vlanstrip(self, dst_mac, vlan_id = 0, pktsize = 64, num = 1):
        """
        Send packets to dut, strip and return vlan id from dump message
        Input: dst_mac, vlan_id, packet size, packet number
        Output: vlan id stripped from dump message
        """
        inst = self.send_packet(dst_mac, vlan_id , pktsize, num)
        vlans = self.strip_vlan(inst)
        return vlans

    def send_and_macstrip(self, dst_mac, vlan_id = 0, pktsize = 64, num = 1):
        """
        Send packets to dut, strip and return src/dst mac from dump message
        Input: dst_mac, vlan_id, packet size, packet number
        Output: src/dst mac stripped from dump message
        """
        inst = self.send_packet(dst_mac, vlan_id , pktsize, num)
        macs = self.strip_mac(inst)
        return macs
        
    
    def test_vlan_insert(self):
        """
        Insert a vlan id for a VF from PF
        If insert vlan id as 0, means disabling vlan id insertion 
        If insert vlan id as 1~4095, means enabling vlan id insertion and 
        vlan id as configured value
        """
        self.dut_testpmd.start_testpmd("Default", "--port-topology=chained")
        self.vm0_testpmd.start_testpmd(VM_CORES_MASK, '--port-topology=chained')

        self.vf0_mac = self.vm0_testpmd.get_port_mac(0)

        self.vm0_testpmd.execute_cmd('set fwd mac')
        self.vm0_testpmd.execute_cmd('set verbose 1')
        self.vm0_testpmd.execute_cmd('start')
        #Disable vlan insert which means insert vlan id as 0
        rx_vlan = 0
        self.dut_testpmd.execute_cmd('set vf vlan insert 0 0 %s' % rx_vlan)
        time.sleep(1)
        vlans = self.send_and_vlanstrip(self.vf0_mac)
        self.verify(rx_vlan not in vlans, 
            "Failed to disable vlan insert!!!")

        #Enable vlan insert which means insert vlan id as 1~4095
        random_vlan = random.randint(1, MAX_VLAN - 1)
        rx_vlans = [1, random_vlan, MAX_VLAN]
        for rx_vlan in rx_vlans:
            self.dut_testpmd.execute_cmd('set vf vlan insert 0 0 %s'% rx_vlan)
            time.sleep(1)
            vlans = self.send_and_vlanstrip(self.vf0_mac)
            self.verify(rx_vlan in vlans,"Failed to enable vlan insert packet!!!")

        self.vm0_testpmd.quit()
        self.dut_testpmd.quit()
        

    def test_multicast_mode(self):
        """
        Enable/disable multicast promiscuous mode for a VF from PF
        """
        self.dut_testpmd.start_testpmd("Default", "--port-topology=chained")
        self.vm0_testpmd.start_testpmd(VM_CORES_MASK, '--port-topology=chained')

        self.vf0_mac = self.vm0_testpmd.get_port_mac(0)

        self.vm0_testpmd.execute_cmd('set fwd rxonly')
        self.vm0_testpmd.execute_cmd('set verbose 1')
        self.vm0_testpmd.execute_cmd('start')
        self.dut_testpmd.execute_cmd('set vf promisc 0 0 off')  
        self.dut_testpmd.execute_cmd('set vf allmulti 0 0 off')  
        multi_mac = 'F3:00:33:22:11:00'
        out = self.send_and_pmdout(multi_mac)
        self.verify("received" not in out, 
            "Failed to disable vf multicast mode!!!")
        
        out = self.send_and_pmdout(self.vf0_mac)
        self.verify("received" in out, "Failed to disable vf multicast mode!!!")
        self.verify("dst=%s" % self.vf0_mac in out, 
            "Failed to disable vf multicast mode!!!")
        
        self.dut_testpmd.execute_cmd('set vf allmulti 0 0 on')
        out = self.send_and_pmdout(multi_mac)
        self.verify("received" in out, "Failed to enable vf multicast mode!!!")
        self.verify("dst=%s" % multi_mac in out, 
            "Failed to enable vf multicast mode!!!")
        
        out = self.send_and_pmdout(self.vf0_mac)
        self.verify("received" in out, "Failed to enable vf multicast mode!!!")
        self.verify("dst=%s" % self.vf0_mac in out, 
            "Failed to enable vf multicast mode!!!")
        
        self.vm0_testpmd.quit()
        self.dut_testpmd.quit()
    
        
    def test_promisc_mode(self):
        """
        Enable/disable promiscuous mode for a VF from PF
        """
        self.dut_testpmd.start_testpmd("Default", "--port-topology=chained")
        self.vm0_testpmd.start_testpmd(VM_CORES_MASK, '--port-topology=chained')

        self.vf0_mac = self.vm0_testpmd.get_port_mac(0)

        self.vm0_testpmd.execute_cmd('set fwd rxonly')
        self.vm0_testpmd.execute_cmd('set verbose 1')
        self.vm0_testpmd.execute_cmd('start')
        self.dut_testpmd.execute_cmd('set vf promisc 0 0 off')

        wrong_mac = '9E:AC:72:49:43:11'
        out = self.send_and_pmdout(wrong_mac)
        self.verify("received" not in out, 
            "Failed to disable vf promisc mode!!!")
        
        out = self.send_and_pmdout(self.vf0_mac)
        self.verify("received" in out, "Failed to disable vf promisc mode!!!")
        self.verify("dst=%s" % self.vf0_mac in out, 
            "Failed to disable vf promisc mode!!!") 
        
        self.dut_testpmd.execute_cmd('set vf promisc 0 0 on')
        out = self.send_and_pmdout(wrong_mac)
        self.verify("received" in out, "Failed to enable vf promisc mode!!!")
        self.verify("dst=%s" % wrong_mac in out, 
            "Failed to enable vf promisc mode!!!")
        
        out = self.send_and_pmdout(self.vf0_mac)
        self.verify("received" in out, "Failed to enable vf promisc mode!!!")
        self.verify("dst=%s" % self.vf0_mac in out, 
            "Failed to enable vf promisc mode!!!")
        
        self.vm0_testpmd.quit()
        self.dut_testpmd.quit()
       
    
    def test_broadcast_mode(self):
        """
        Enable/disable broadcast mode for a VF from PF
        """
        self.dut_testpmd.start_testpmd("Default", "--port-topology=chained")
        self.vm0_testpmd.start_testpmd(VM_CORES_MASK, '--port-topology=chained')

        self.vf0_mac = self.vm0_testpmd.get_port_mac(0)

        self.vm0_testpmd.execute_cmd('set fwd rxonly')
        self.vm0_testpmd.execute_cmd('set verbose 1')
        self.vm0_testpmd.execute_cmd('start')
        self.dut_testpmd.execute_cmd('set vf broadcast 0 0 off')

        dst_mac = 'FF:FF:FF:FF:FF:FF'
        out = self.send_and_pmdout(dst_mac)
        self.verify("received" not in out, 
            "Failed to disable vf broadcast mode!!!")
        
        self.dut_testpmd.execute_cmd('set vf broadcast 0 0 on')
        out = self.send_and_pmdout(dst_mac)
        self.verify("received" in out, "Failed to enable vf broadcast mode!!!")
        self.verify("dst=%s" % dst_mac in out, 
            "Failed to enable vf broadcast mode!!!")

        self.vm0_testpmd.quit()
        self.dut_testpmd.quit()
    

    def test_vf_mtu(self):
        """
        Enable VF MTU change        
        """
        self.dut.send_expect("ifconfig %s mtu 9000" % self.tester_intf, "#")
        self.dut_testpmd.start_testpmd("Default", "--port-topology=chained")
        self.vm0_testpmd.start_testpmd(VM_CORES_MASK, '--port-topology=chained')

        self.vf0_mac = self.vm0_testpmd.get_port_mac(0)

        self.vm0_testpmd.execute_cmd('set fwd mac')
        self.vm0_testpmd.execute_cmd('set verbose 1')
        self.vm0_testpmd.execute_cmd('start')
        pktsize = random.randint(1500, 9000)
        out = self.send_and_macstrip(self.vf0_mac, 0, pktsize)
        self.vm0_testpmd.execute_cmd('stop')
        self.verify(self.vf0_mac.lower() not in out, 
            "Failed to receive and forward this length packet!!!")
        
        self.vm0_testpmd.execute_cmd('port stop all')
        self.vm0_testpmd.execute_cmd('port config mtu 0 %s' % (pktsize+100))
        self.vm0_testpmd.execute_cmd('port start all')
        self.vm0_testpmd.execute_cmd('start')
        out = self.send_and_macstrip(self.vf0_mac, 0, pktsize)
        self.vm0_testpmd.execute_cmd('stop')
        self.verify(self.vf0_mac.lower() in out, 
            "Failed to receive and forward this length packet!!!")
        
        self.vm0_testpmd.quit()
        self.dut_testpmd.quit()
        self.dut.send_expect("ifconfig %s mtu 1500" % self.tester_intf, "#")

    
    def test_vlan_tag(self):
        """
        Enable/disable vlan tag for a VF from PF
        """
        self.dut_testpmd.start_testpmd("Default", "--port-topology=chained")
        self.vm0_testpmd.start_testpmd(VM_CORES_MASK, '--port-topology=chained')

        self.vf0_mac = self.vm0_testpmd.get_port_mac(0)

        random_vlan = random.randint(1, MAX_VLAN - 1)
        rx_vlans = [1, random_vlan, MAX_VLAN]
        self.vm0_testpmd.execute_cmd('set fwd mac')
        self.vm0_testpmd.execute_cmd('set verbose 1')
        self.vm0_testpmd.execute_cmd('start')
        for rx_vlan in rx_vlans:
            self.vm0_testpmd.execute_cmd('rx_vlan add %s 0' % rx_vlan)
            self.dut_testpmd.execute_cmd('set vf vlan tag 0 0 off')
            time.sleep(1)
            out = self.send_and_macstrip(self.vf0_mac, rx_vlan)
            self.verify(self.vf0_mac.lower() not in out,
                "Failed to disable vlan tag!!!")

            self.dut_testpmd.execute_cmd('set vf vlan tag 0 0 on')
            time.sleep(1)
            out = self.send_and_macstrip(self.vf0_mac, rx_vlan)
            self.verify(self.vf0_mac.lower() in out,
                "Failed to enable vlan tag!!!")

        self.vm0_testpmd.quit()
        self.dut_testpmd.quit()

    
    def test_tx_loopback(self):
        """
        Enable/disable TX loopback from PF
        """
        self.dut_testpmd.start_testpmd("Default", "--port-topology=chained")
        self.vm0_testpmd.start_testpmd(VM_CORES_MASK, '--port-topology=chained')
        self.vf0_mac = self.vm0_testpmd.get_port_mac(0)
        self.vm1_testpmd.start_testpmd(VM_CORES_MASK, 
                '--port-topology=chained --eth-peer=0,%s' % self.vf0_mac)

        self.vm0_testpmd.execute_cmd('set fwd rxonly')
        self.vm0_testpmd.execute_cmd('set verbose 1')
        self.vm0_testpmd.execute_cmd('start')
        self.dut_testpmd.execute_cmd('set tx loopback 0 off')

        inst = sniff_packets(self.tester_intf, timeout=5)

        self.vm1_testpmd.execute_cmd('set burst 5')
        self.vm1_testpmd.execute_cmd('start tx_first')
         
        dumpout = self.strip_mac(inst, "dst")
        out = self.vm0_testpmd.execute_cmd('stop')
        self.verify(self.vf0_mac.lower() in dumpout, 
            "Failed to disable tx loopback!!!")
        self.verify("RX-packets: 0" in out, 
            "Failed to disable tx loopback!!!")

        self.vm0_testpmd.execute_cmd('start')
        self.dut_testpmd.execute_cmd('set tx loopback 0 on')

        inst = sniff_packets(self.tester_intf, timeout=5)

        self.vm1_testpmd.execute_cmd('stop')
        self.vm1_testpmd.execute_cmd('start tx_first')
        dumpout = self.strip_mac(inst, "dst")
        out = self.vm0_testpmd.execute_cmd('stop')
        self.verify(self.vf0_mac.lower() not in dumpout, 
            "Failed to enable tx loopback!!!")
        self.verify("RX-packets: 5" in out, "Failed to enable tx loopback!!!")

        self.vm0_testpmd.quit()
        self.vm1_testpmd.quit()
        self.dut_testpmd.quit()

    
    def test_all_queues_drop(self):
        """
        Enable/disable drop enable bit for all queues from PF
        """
        self.dut_testpmd.start_testpmd("Default", "--port-topology=chained")
        self.vm0_testpmd.start_testpmd(VM_CORES_MASK, '--port-topology=chained')
        self.vm1_testpmd.start_testpmd(VM_CORES_MASK, '--port-topology=chained')

        self.vm0_testpmd.execute_cmd('set fwd rxonly')
        self.vm0_testpmd.execute_cmd('set verbose 1')
        self.vm0_testpmd.execute_cmd('start')
        self.dut_testpmd.execute_cmd('set all queues drop 0 off')
        self.vf0_mac = self.vm0_testpmd.get_port_mac(0)
        self.vf1_mac = self.vm1_testpmd.get_port_mac(0)
        out = self.send_and_pmdout(self.vf1_mac, 0, 64, 200)
        out = self.vm1_testpmd.execute_cmd('show port stats 0')
        self.verify("RX-packets: 127" in out, 
            "Failed to let vf1 full of queues!!!")
        out = self.send_and_pmdout(self.vf0_mac, 0, 64, 20)
        out = self.vm0_testpmd.execute_cmd('show port stats 0')
        self.verify("RX-packets: 0" in out, 
            "Failed to disable all queues drop!!!")
        self.dut_testpmd.execute_cmd('set all queues drop 0 on')
        out = self.vm0_testpmd.execute_cmd('show port stats 0')
        self.verify("RX-packets: 20" in out, 
            "Failed to enable all queues drop!!!")
        out = self.send_and_pmdout(self.vf0_mac, 0, 64, 20)
        out = self.vm0_testpmd.execute_cmd('show port stats 0')
        self.verify("RX-packets: 40" in out, 
            "Failed to enable all queues drop!!!")

        self.vm0_testpmd.quit()
        self.vm1_testpmd.quit()
        self.dut_testpmd.quit()
    

    def test_mac_antispoof(self):
        """
        Enable/disable mac anti-spoof for a VF from PF
        """
        fake_mac = '00:11:22:33:44:55'
        self.vm0_dut.send_expect("sed -i -e '/uint64_t ol_flags = 0;/a " +\
            "\struct ether_addr fake_mac = {.addr_bytes = {0x00, 0x11, 0x22, 0x33, 0x44, 0x55},};'" +\
            " app/test-pmd/macswap.c", "# ", 30)
        self.vm0_dut.send_expect("sed -i -e '/ether_addr_copy(&addr, &eth_hdr->s_addr);/d' " +\
            " app/test-pmd/macswap.c", "# ", 30)
        self.vm0_dut.send_expect("sed -i -e '/ether_addr_copy(&eth_hdr->s_addr, &eth_hdr->d_addr);/a " +\
            "\ether_addr_copy(&fake_mac, &eth_hdr->s_addr);' app/test-pmd/macswap.c", "# ", 30)
        self.vm0_dut.build_install_dpdk(self.target) 
        self.dut_testpmd.start_testpmd("Default", "--port-topology=chained")
        self.vm0_testpmd.start_testpmd(VM_CORES_MASK, '--port-topology=chained')
        self.vf0_mac = self.vm0_testpmd.get_port_mac(0)

        self.vm0_testpmd.execute_cmd('set fwd macswap')
        self.dut_testpmd.execute_cmd('set vf mac antispoof 0 0 off')
        self.vm0_testpmd.execute_cmd('start')
        dumpout = self.send_and_macstrip(self.vf0_mac)
        out = self.vm0_testpmd.execute_cmd('stop')
        self.verify(fake_mac in dumpout, 
            "Failed to disable vf mac anspoof!!!")
        self.verify("RX-packets: 1" in out, "Failed to receive packet!!!")
        self.verify("TX-packets: 1" in out, 
            "Failed to disable mac antispoof!!!")

        self.dut_testpmd.execute_cmd('set vf mac antispoof 0 0 on')
        out = self.vm0_testpmd.execute_cmd('start')
        dumpout = self.send_and_macstrip(self.vf0_mac)
        out = self.vm0_testpmd.execute_cmd('stop')
        self.verify(fake_mac not in dumpout, "Failed to enable vf mac anspoof!!!")
        self.verify("RX-packets: 1" in out, "Failed to receive packet!!!")
        self.verify("TX-packets: 0" in out, "Failed to enable mac antispoof!!!")

        self.vm0_testpmd.quit()
        self.dut_testpmd.quit()
        self.vm0_dut.send_expect("sed -i '/struct ether_addr fake_mac = {.addr_bytes = " +\
            "{0x00, 0x11, 0x22, 0x33, 0x44, 0x55},};/d' app/test-pmd/macswap.c", "# ", 30)
        self.vm0_dut.send_expect("sed -i '/ether_addr_copy(&fake_mac, &eth_hdr->s_addr);/d' " +\
            "app/test-pmd/macswap.c", "# ", 30)
        self.vm0_dut.send_expect("sed -i '/ether_addr_copy(&eth_hdr->s_addr, &eth_hdr->d_addr);/a " +\
            "\ether_addr_copy(&addr, &eth_hdr->s_addr);' app/test-pmd/macswap.c", "# ", 30)
        self.vm0_dut.build_install_dpdk(self.target)
    
     
    def test_vf_mac_set(self):
        """
        Set MAC address for a VF from PF
        """
        expect_mac = 'A2:22:33:44:55:66'
        self.dut_testpmd.start_testpmd("Default", "--port-topology=chained")
        self.dut_testpmd.execute_cmd('set vf mac addr 0 0 %s' % expect_mac)
        out = self.vm0_testpmd.start_testpmd(
            VM_CORES_MASK, '--port-topology=chained')
        self.verify("%s" % expect_mac in out, "Failed to set vf mac!!!")
        self.vf0_mac = self.vm0_testpmd.get_port_mac(0)

        self.vm0_testpmd.execute_cmd('set fwd mac')
        self.vm0_testpmd.execute_cmd('start')
        out = self.send_and_macstrip(self.vf0_mac)
        self.verify(expect_mac.lower() in out, 
            "Failed to receive packet on setted vf mac!!!")
        
        self.vm0_testpmd.quit()
        self.dut_testpmd.quit()
 

    def test_vlan_antispoof(self):
        """
        Enable/disable vlan antispoof for a VF from PF 
        """
        self.dut_testpmd.start_testpmd("Default", "--port-topology=chained")
        self.vm0_testpmd.start_testpmd(VM_CORES_MASK, '--port-topology=chained')

        self.vf0_mac = self.vm0_testpmd.get_port_mac(0)
        vf0_mac_lower = self.vf0_mac.lower()
        random_vlan = random.randint(1, MAX_VLAN)
        match_vlan = random_vlan
        unmatch_vlan = (random_vlan + 2) % 4096
        self.vm0_testpmd.execute_cmd('set fwd mac')
        self.vm0_testpmd.execute_cmd('start')
        self.dut_testpmd.execute_cmd('rx_vlan add %d port 0 vf 1' % match_vlan)
        if self.kdriver == "i40e":
            self.dut_testpmd.execute_cmd('set vf vlan stripq 0 0 off')
        else:
            self.dut_testpmd.execute_cmd('vlan set filter off 0')
            self.dut_testpmd.execute_cmd('vlan set strip off 0')
            self.vm0_testpmd.execute_cmd('vlan set strip off 0')
 
        self.dut_testpmd.execute_cmd('set vf vlan antispoof 0 0 off')
        time.sleep(1)
        out = self.send_and_macstrip(self.vf0_mac,match_vlan)
        self.verify(vf0_mac_lower in out, 
            "Failed to disable vlan antispoof with match vlan!!!")
        out = self.send_and_macstrip(self.vf0_mac,unmatch_vlan)
        self.verify(vf0_mac_lower in out, 
            "Failed to disable vlan antispoof with unmatch vlan!!!")
        out = self.send_and_macstrip(self.vf0_mac)
        self.verify(vf0_mac_lower in out, 
            "Failed to disable vlan antispoof with no vlan!!!")
        
        if self.kdriver == "ixgbe":
            self.dut_testpmd.execute_cmd('set vf mac antispoof 0 0 on')
        self.dut_testpmd.execute_cmd('set vf vlan antispoof 0 0 on')
        time.sleep(1)
        
        out = self.send_and_macstrip(self.vf0_mac,match_vlan)
        self.verify(vf0_mac_lower in out, 
            "Failed to enable vlan antispoof with match vlan!!!")
        
        out = self.send_and_macstrip(self.vf0_mac,unmatch_vlan)
        self.verify(vf0_mac_lower not in out, 
            "Failed to enable vlan antispoof with unmatch vlan!!!")
        
        out = self.send_and_macstrip(self.vf0_mac)
        self.verify(vf0_mac_lower not in out, 
            "Failed to enable vlan antispoof with no vlan!!!")

        self.vm0_testpmd.quit()
        self.dut_testpmd.quit()
    
    
    def test_vlan_strip(self): 
        """
        Enable/disable the VLAN strip for all queues in a pool for a VF from PF
        """
        self.dut_testpmd.start_testpmd("Default", "--port-topology=chained")
        self.vm0_testpmd.start_testpmd(VM_CORES_MASK, '--port-topology=chained')

        self.vf0_mac = self.vm0_testpmd.get_port_mac(0)

        random_vlan = random.randint(1, MAX_VLAN - 1) 
        rx_vlans = [1, random_vlan, MAX_VLAN]
        self.vm0_testpmd.execute_cmd('set fwd mac')
        self.vm0_testpmd.execute_cmd('set verbose 1')  
        self.vm0_testpmd.execute_cmd('start')
        for rx_vlan in rx_vlans:  
            self.vm0_testpmd.execute_cmd('rx_vlan add %s 0' % rx_vlan)
            self.dut_testpmd.execute_cmd('set vf vlan stripq 0 0 off')
            time.sleep(1)
            out = self.send_and_vlanstrip(self.vf0_mac,rx_vlan)   
            self.verify(rx_vlan in out, "Failed to disable strip vlan!!!")
        
            self.dut_testpmd.execute_cmd('set vf vlan stripq 0 0 on')
            time.sleep(1)
            out = self.send_and_vlanstrip(self.vf0_mac,rx_vlan)
            self.verify(rx_vlan not in out, "Failed to disable strip vlan!!!")

        self.vm0_testpmd.quit()
        self.dut_testpmd.quit()


    def tear_down(self):
        self.vm0_dut.kill_all()
        self.vm1_dut.kill_all()
        pass


    def tear_down_all(self):
        self.destroy_vm_env()
        pass
