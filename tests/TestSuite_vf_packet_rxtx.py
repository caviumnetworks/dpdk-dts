# <COPYRIGHT_TAG>

import re
import time

from qemu_kvm import QEMUKvm
from test_case import TestCase
from pmd_output import PmdOutput

VM_CORES_MASK = 'all'


class TestVfPacketRxtx(TestCase):

    def set_up_all(self):

        self.dut_ports = self.dut.get_ports(self.nic)
        self.verify(len(self.dut_ports) > 1, "Insufficient ports")
        self.vm0 = None
        self.vm1 = None

    def set_up(self):

        self.setup_2pf_2vf_1vm_env_flag = 0
        self.setup_3vf_2vm_env_flag = 0

    def setup_2pf_2vf_1vm_env(self, driver='default'):

        self.used_dut_port_0 = self.dut_ports[0]
        self.dut.generate_sriov_vfs_by_port(self.used_dut_port_0, 1, driver=driver)
        self.sriov_vfs_port_0 = self.dut.ports_info[self.used_dut_port_0]['vfs_port']

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
                self.host_testpmd.start_testpmd("1S/2C/2T", "--crc-strip", eal_param=eal_param)

            # set up VM0 ENV
            self.vm0 = QEMUKvm(self.dut, 'vm0', 'vf_packet_rxtx')
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
            if getattr(self, 'vm0_testpmd', None):
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

        self.dut.virt_exit()

        if getattr(self, 'used_dut_port_0', None) != None:
            self.dut.destroy_sriov_vfs_by_port(self.used_dut_port_0)
            port = self.dut.ports_info[self.used_dut_port_0]['port']
            port.bind_driver()
            self.used_dut_port_0 = None

        if getattr(self, 'used_dut_port_1', None) != None:
            self.dut.destroy_sriov_vfs_by_port(self.used_dut_port_1)
            port = self.dut.ports_info[self.used_dut_port_1]['port']
            port.bind_driver()
            self.used_dut_port_1 = None

        for port_id in self.dut_ports:
            port = self.dut.ports_info[port_id]['port']
            port.bind_driver()

        self.setup_2pf_2vf_1vm_env_flag = 0


    def packet_rx_tx(self, driver='default'):

        if driver == 'igb_uio':
            self.setup_2pf_2vf_1vm_env(driver='igb_uio')
        else:
            self.setup_2pf_2vf_1vm_env(driver='')

        self.vm0_dut_ports = self.vm_dut_0.get_ports('any')
        port_id_0 = 0
        self.vm0_testpmd = PmdOutput(self.vm_dut_0)
        self.vm0_testpmd.start_testpmd(VM_CORES_MASK, '--crc-strip')
        pmd_vf0_mac = self.vm0_testpmd.get_port_mac(port_id_0)
        self.vm0_testpmd.execute_cmd('set fwd mac')
        self.vm0_testpmd.execute_cmd('start')

        time.sleep(2)

        tgen_ports = []
        tx_port = self.tester.get_local_port(self.dut_ports[0])
        rx_port = self.tester.get_local_port(self.dut_ports[1])
        tgen_ports.append((tx_port, rx_port))

        dst_mac = pmd_vf0_mac
        src_mac = self.tester.get_mac(tx_port)

        pkt_param=[("ether", {'dst': dst_mac, 'src': src_mac})]

        result = self.tester.check_random_pkts(tgen_ports, allow_miss=False, params=pkt_param)
        self.verify(result != False, "VF0 failed to forward packets to VF1")


######1. test case for kernel pf and dpdk vf 2pf_2vf_1vm scenario packet rx tx.
    def test_kernel_2pf_2vf_1vm(self):

        self.packet_rx_tx(driver='')

######2. test case for dpdk pf and dpdk vf 2pf_2vf_1vm scenario packet rx tx.
    def test_dpdk_2pf_2vf_1vm(self):

        self.packet_rx_tx(driver='igb_uio')

    def setup_3vf_2vm_env(self, driver='default'):

        self.used_dut_port = self.dut_ports[0]
        self.dut.generate_sriov_vfs_by_port(self.used_dut_port, 3, driver=driver)
        self.sriov_vfs_port = self.dut.ports_info[self.used_dut_port]['vfs_port']

        try:

            for port in self.sriov_vfs_port:
                print port.pci
                port.bind_driver('pci-stub')

            time.sleep(1)
            vf0_prop = {'opt_host': self.sriov_vfs_port[0].pci}
            vf1_prop = {'opt_host': self.sriov_vfs_port[1].pci}
            vf2_prop = {'opt_host': self.sriov_vfs_port[2].pci}

            for port_id in self.dut_ports:
                if port_id == self.used_dut_port:
                    continue
                port = self.dut.ports_info[port_id]['port']
                port.bind_driver()

            if driver == 'igb_uio':
                self.host_testpmd = PmdOutput(self.dut)
                eal_param = '-b %(vf0)s -b %(vf1)s -b %(vf2)s' % {'vf0': self.sriov_vfs_port[0].pci,
                                                                  'vf1': self.sriov_vfs_port[1].pci,
                                                                  'vf2': self.sriov_vfs_port[2].pci}
                self.host_testpmd.start_testpmd("1S/2C/2T", eal_param=eal_param)

            # set up VM0 ENV
            self.vm0 = QEMUKvm(self.dut, 'vm0', 'vf_packet_rxtx')
            self.vm0.set_vm_device(driver='pci-assign', **vf0_prop)
            self.vm0.set_vm_device(driver='pci-assign', **vf1_prop)
            self.vm_dut_0 = self.vm0.start()
            if self.vm_dut_0 is None:
                raise Exception("Set up VM0 ENV failed!")
            # set up VM1 ENV
            self.vm1 = QEMUKvm(self.dut, 'vm1', 'vf_packet_rxtx')
            self.vm1.set_vm_device(driver='pci-assign', **vf2_prop)
            self.vm_dut_1 = self.vm1.start()
            if self.vm_dut_1 is None:
                raise Exception("Set up VM1 ENV failed!")

            self.setup_3vf_2vm_env_flag = 1
        except Exception as e:
            self.destroy_3vf_2vm_env()
            raise Exception(e)

    def destroy_3vf_2vm_env(self):
        if getattr(self, 'vm0', None):
            if getattr(self, 'vm0_testpmd', None):
                self.vm0_testpmd.execute_cmd('stop')
                self.vm0_testpmd.execute_cmd('quit', '# ')
            self.vm0_testpmd = None
            self.vm0_dut_ports = None
            self.vm_dut_0 = None
            self.vm0.stop()
            self.vm0 = None

        if getattr(self, 'vm1', None):
            if getattr(self, 'vm1_testpmd', None):
                self.vm1_testpmd.execute_cmd('stop')
                self.vm1_testpmd.execute_cmd('quit', '# ')
            self.vm1_testpmd = None
            self.vm1_dut_ports = None
            self.vm_dut_1 = None
            self.vm1.stop()
            self.vm1 = None

        self.dut.virt_exit()

        if getattr(self, 'host_testpmd', None) != None:
            self.host_testpmd.execute_cmd('quit', '# ')
            self.host_testpmd = None

        if getattr(self, 'used_dut_port', None) != None:
            self.dut.destroy_sriov_vfs_by_port(self.used_dut_port)
            port = self.dut.ports_info[self.used_dut_port]['port']
            port.bind_driver()
            self.used_dut_port = None

        for port_id in self.dut_ports:
            port = self.dut.ports_info[port_id]['port']
            port.bind_driver()

        self.setup_3vf_2vm_env_flag = 0

    def test_vf_reset(self):

        self.setup_3vf_2vm_env(driver='')

        self.vm0_dut_ports = self.vm_dut_0.get_ports('any')
        self.vm1_dut_ports = self.vm_dut_1.get_ports('any')

        port_id_0 = 0
        port_id_1 = 1

        self.vm0_testpmd = PmdOutput(self.vm_dut_0)
        self.vm0_testpmd.start_testpmd(VM_CORES_MASK, '--crc-strip')
        self.vm0_testpmd.execute_cmd('show port info all')
        pmd0_vf0_mac = self.vm0_testpmd.get_port_mac(port_id_0)
        self.vm0_testpmd.execute_cmd('set fwd mac')
        self.vm0_testpmd.execute_cmd('start')

        time.sleep(2)

        self.vm1_testpmd = PmdOutput(self.vm_dut_1)
        self.vm1_testpmd.start_testpmd(VM_CORES_MASK, '--crc-strip')
        self.vm1_testpmd.execute_cmd('show port info all')

        tx_port = self.tester.get_local_port(self.dut_ports[0])
        rx_port = tx_port

        dst_mac = pmd0_vf0_mac
        self.tester.sendpkt_bg(tx_port, dst_mac)

        #vf port stop/start can trigger reset action
        for num in range(1000):
            self.vm1_testpmd.execute_cmd('port stop all')
            time.sleep(0.1)
            self.vm1_testpmd.execute_cmd('port start all')
            time.sleep(0.1)

        self.tester.stop_sendpkt_bg()

        pmd0_vf0_stats = self.vm0_testpmd.get_pmd_stats(port_id_0)
        pmd0_vf1_stats = self.vm0_testpmd.get_pmd_stats(port_id_1)

        vf0_rx_cnt = pmd0_vf0_stats['RX-packets']
        self.verify(vf0_rx_cnt != 0, "no packet was received by vm0_VF0")
    
        vf0_rx_err = pmd0_vf0_stats['RX-errors']
        self.verify(vf0_rx_err == 0, "vm0_VF0 rx-errors")
    
        vf1_tx_cnt = pmd0_vf1_stats['TX-packets']
        self.verify(vf1_tx_cnt != 0, "no packet was transmitted by vm0_VF1")

        vf1_tx_err = pmd0_vf1_stats['TX-errors']
        self.verify(vf1_tx_err == 0, "vm0_VF0 tx-errors")

        self.verify(vf0_rx_cnt == vf1_tx_cnt, "vm0_VF0 failed to forward packets to vm0_VF1 when reset vm1_VF0 frequently")

    def tear_down(self):

        if self.setup_2pf_2vf_1vm_env_flag == 1:
            self.destroy_2pf_2vf_1vm_env()
        if self.setup_3vf_2vm_env_flag == 1:
            self.destroy_3vf_2vm_env()

        if getattr(self, 'vm0', None):
            self.vm0.stop()

        if getattr(self, 'vm1', None):
            self.vm1.stop()

        self.dut.virt_exit()

        for port_id in self.dut_ports:
            self.dut.destroy_sriov_vfs_by_port(port_id)

    def tear_down_all(self):
        pass

