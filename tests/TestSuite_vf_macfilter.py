# <COPYRIGHT_TAG>

import re
import time

import dts
from qemu_kvm import QEMUKvm
from test_case import TestCase
from pmd_output import PmdOutput

VM_CORES_MASK = 'all'


class TestVfMacFilter(TestCase):

    def set_up_all(self):
        self.dut_ports = self.dut.get_ports(self.nic)
        self.verify(len(self.dut_ports) > 1, "Insufficient ports")
        self.vm0 = None
        self.pf0_vf0_mac = "00:12:34:56:78:01"
        self.iplinkset = True

    def set_up(self):

        self.setup_2pf_2vf_1vm_env_flag = 0

    def setup_2pf_2vf_1vm_env(self, driver='default'):

        self.used_dut_port_0 = self.dut_ports[0]
        self.dut.generate_sriov_vfs_by_port(self.used_dut_port_0, 1, driver=driver)
        self.sriov_vfs_port_0 = self.dut.ports_info[self.used_dut_port_0]['vfs_port']
        pf_intf0 = self.dut.ports_info[0]['port'].get_interface_name()
        
        if self.iplinkset: 
            self.dut.send_expect("ip link set %s vf 0 mac %s" %(pf_intf0, self.pf0_vf0_mac), "#")
       
        self.used_dut_port_1 = self.dut_ports[1]
        self.dut.generate_sriov_vfs_by_port(self.used_dut_port_1, 1, driver=driver)
        self.sriov_vfs_port_1 = self.dut.ports_info[self.used_dut_port_1]['vfs_port']


        try:

            for port in self.sriov_vfs_port_0:
                port.bind_driver('pci-stub')

            for port in self.sriov_vfs_port_1:
                port.bind_driver('pci-stub')

            time.sleep(1)
            vf0_prop = {'opt_host': self.sriov_vfs_port_0[0].pci}
            vf1_prop = {'opt_host': self.sriov_vfs_port_1[0].pci}

            if driver == 'igb_uio':
                # start testpmd without the two VFs on the host
                self.host_testpmd = PmdOutput(self.dut)
                eal_param = '-b %(vf0)s -b %(vf1)s' % {'vf0': self.sriov_vfs_port_0[0].pci,
                                                       'vf1': self.sriov_vfs_port_1[0].pci}
                self.host_testpmd.start_testpmd("1S/2C/2T", eal_param=eal_param)

            # set up VM0 ENV
            self.vm0 = QEMUKvm(self.dut, 'vm0', 'vf_macfilter')
            self.vm0.set_vm_device(driver='pci-assign', **vf0_prop)
            self.vm0.set_vm_device(driver='pci-assign', **vf1_prop)
            self.vm_dut_0 = self.vm0.start()
            if self.vm_dut_0 is None:
                raise Exception("Set up VM0 ENV failed!")

            self.setup_2pf_2vf_1vm_env_flag = 1
        except Exception as e:
            self.destroy_2pf_2vf_1vm_env()
            raise Exception(e)

    def destroy_2pf_2vf_1vm_env(self):
        if getattr(self, 'vm0', None):
            #destroy testpmd in vm0
            self.vm0_testpmd.execute_cmd('stop')
            self.vm0_testpmd.execute_cmd('quit', '# ')
            self.vm0_testpmd = None
            self.vm0_dut_ports = None
            #destroy vm0
            self.vm0.stop()
            self.vm0 = None

        if getattr(self, 'host_testpmd', None):
            self.host_testpmd.execute_cmd('quit', '# ')
            self.host_testpmd = None

        if getattr(self, 'used_dut_port_0', None):
            self.dut.destroy_sriov_vfs_by_port(self.used_dut_port_0)
            port = self.dut.ports_info[self.used_dut_port_0]['port']
            port.bind_driver()
            self.used_dut_port_0 = None

        if getattr(self, 'used_dut_port_1', None):
            self.dut.destroy_sriov_vfs_by_port(self.used_dut_port_1)
            port = self.dut.ports_info[self.used_dut_port_1]['port']
            port.bind_driver()
            self.used_dut_port_1 = None

        for port_id in self.dut_ports:
            port = self.dut.ports_info[port_id]['port']
            port.bind_driver()

        self.setup_2pf_2vf_1vm_env_flag = 0

######1. test case for kernel pf and dpdk vf 2pf_2vf_1vm MAC filter scenario
###### kernel pf will first run 'ip link set pf_interface vf 0 mac xx:xx:xx:xx:xx:xx, then 
###### in the vm, send packets with this MAC to VF, check if the MAC filter works. Also 
###### send the packets with wrong MAC address to VF, check if the VF will not RX the packets.
 
    def test_kernel_2pf_2vf_1vm_iplink_macfilter(self):

        self.setup_2pf_2vf_1vm_env(driver='')

        self.vm0_dut_ports = self.vm_dut_0.get_ports('any')
        self.vm0_testpmd = PmdOutput(self.vm_dut_0)
        self.vm0_testpmd.start_testpmd(VM_CORES_MASK)
        # Get VF's MAC
        pmd_vf0_mac = self.vm0_testpmd.get_port_mac(0)
        vf0_wrongmac = "00:11:22:33:48:55"
        self.vm0_testpmd.execute_cmd('port stop all')
        self.vm0_testpmd.execute_cmd('port config all crc-strip on')
        self.vm0_testpmd.execute_cmd('port start all')
        self.vm0_testpmd.execute_cmd('set promisc all off')
        self.vm0_testpmd.execute_cmd('set fwd mac')
        self.vm0_testpmd.execute_cmd('start')
              
        time.sleep(2)

        tgen_ports = []
        tx_port = self.tester.get_local_port(self.dut_ports[0])
        rx_port = self.tester.get_local_port(self.dut_ports[1])
        tgen_ports.append((tx_port, rx_port))
        dst_mac = self.pf0_vf0_mac
        src_mac = self.tester.get_mac(tx_port)
        pkt_param=[("ether", {'dst': dst_mac, 'src': src_mac})]
        
        print "\nfirst send packets to the kernel PF set MAC, expected result is RX packets=TX packets\n"
        result1 = self.tester.check_random_pkts(tgen_ports, pktnum=100, allow_miss=False, params=pkt_param)
	print "\nshow port stats in testpmd for double check: \n", self.vm0_testpmd.execute_cmd('show port stats all')   
        self.verify(result1 != False, "VF0 failed to forward packets to VF1")
        
        print "\nSecondly, negative test, send packets to a wrong MAC, expected result is RX packets=0\n"
        dst_mac = vf0_wrongmac
        pkt_param=[("ether", {'dst': dst_mac, 'src': src_mac})]
        result2 = self.tester.check_random_pkts(tgen_ports, pktnum=100, allow_miss=False, params=pkt_param)
        print "\nshow port stats in testpmd for double check: \n", self.vm0_testpmd.execute_cmd('show port stats all')
        self.verify(result2 != True, "VF0 failed to forward packets to VF1")

#######2. test case for kernel pf and dpdk vf 2pf_2vf_1vm MAC filter scenario.
####### kernel pf will not set MAC address and the VF will get a random generated MAC
####### in the testpmd in VM, and then add VF mac address in the testpmd,for example, VF_MAC1
####### then send packets to the VF with the random generated MAC and the new added VF_MAC1 
####### and the expected result is that all packets can be RXed and TXed. What's more, send
####### packets with a wrong MAC address to the VF will not received by the VF. 

    def test_kernel_2pf_2vf_1vm_mac_add_filter(self):

        self.iplinkset = False
        self.setup_2pf_2vf_1vm_env(driver='')

        self.vm0_dut_ports = self.vm_dut_0.get_ports('any')
        self.vm0_testpmd = PmdOutput(self.vm_dut_0)
        self.vm0_testpmd.start_testpmd(VM_CORES_MASK)
        
        # Get VF0 port MAC address
        pmd_vf0_mac = self.vm0_testpmd.get_port_mac(0)
        vf0_setmac = "00:11:22:33:44:55"
        vf0_wrongmac = "00:11:22:33:48:55"
        self.vm0_testpmd.execute_cmd('port stop all')
        self.vm0_testpmd.execute_cmd('port config all crc-strip on')
        self.vm0_testpmd.execute_cmd('port start all')
        self.vm0_testpmd.execute_cmd('set promisc all off')
        ret = self.vm0_testpmd.execute_cmd('mac_addr add 0 %s' %vf0_setmac)
        # check the operation is supported or not.
        print ret 
 
        self.vm0_testpmd.execute_cmd('set fwd mac')
        self.vm0_testpmd.execute_cmd('start')

        time.sleep(2)

        tgen_ports = []
        tx_port = self.tester.get_local_port(self.dut_ports[0])
        rx_port = self.tester.get_local_port(self.dut_ports[1])
        tgen_ports.append((tx_port, rx_port))
        src_mac = self.tester.get_mac(tx_port)
        dst_mac = pmd_vf0_mac
        pkt_param=[("ether", {'dst': dst_mac, 'src': src_mac})]
        
        print "\nfirst send packets to the random generated VF MAC, expected result is RX packets=TX packets\n"
        result1 = self.tester.check_random_pkts(tgen_ports, pktnum=100, allow_miss=False, params=pkt_param)
        print "\nshow port stats in testpmd for double check: \n", self.vm0_testpmd.execute_cmd('show port stats all')
        self.verify(result1 != False, "VF0 failed to forward packets to VF1")
        
        print "\nsecondly, send packets to the new added MAC, expected result is RX packets=TX packets\n"
        dst_mac = vf0_setmac
        pkt_param=[("ether", {'dst': dst_mac, 'src': src_mac})]
        result2 = self.tester.check_random_pkts(tgen_ports, pktnum=100, allow_miss=False, params=pkt_param)
        print "\nshow port stats in testpmd for double check: \n", self.vm0_testpmd.execute_cmd('show port stats all')
        self.verify(result2 != False, "VF0 failed to forward packets to VF1")

        print "\nThirdly, negative test, send packets to a wrong MAC, expected result is RX packets=0\n"
        dst_mac = vf0_wrongmac
        pkt_param=[("ether", {'dst': dst_mac, 'src': src_mac})]
        result3 = self.tester.check_random_pkts(tgen_ports, pktnum=100, allow_miss=False, params=pkt_param)
        print "\nshow port stats in testpmd for double check: \n", self.vm0_testpmd.execute_cmd('show port stats all')
        self.verify(result3 != True, "VF0 failed to forward packets to VF1")

 
    def tear_down(self):

        if self.setup_2pf_2vf_1vm_env_flag == 1:
            self.destroy_2pf_2vf_1vm_env()

    def tear_down_all(self):

        if getattr(self, 'vm0', None):
            self.vm0.stop()

        for port_id in self.dut_ports:
            self.dut.destroy_sriov_vfs_by_port(port_id)

