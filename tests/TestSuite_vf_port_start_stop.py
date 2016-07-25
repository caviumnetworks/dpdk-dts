# <COPYRIGHT_TAG>

import re
import time

import dts
from qemu_kvm import QEMUKvm
from test_case import TestCase
from pmd_output import PmdOutput
from utils import RED, GREEN
from net_device import NetDevice
from crb import Crb
from scapy.all import *
VM_CORES_MASK = 'all'

class TestVfPortStartStop(TestCase):

    def set_up_all(self):

        self.dut_ports = self.dut.get_ports(self.nic)
        self.verify(len(self.dut_ports) >= 1, "Insufficient ports")
        self.vm0 = None
        self.filename = "/tmp/vf.pcap"

    def set_up(self):

        self.setup_1pf_2vf_1vm_env_flag = 0

    def pktgen_prerequisites(self):
        """
        igb_uio.ko should be put in ~ before you using pktgen
        """
        out = self.tester.send_expect("ls", "#")
        self.verify("igb_uio.ko" in out, "No file igb_uio.ko, please add it in ~")
        self.tester.send_expect("modprobe uio", "#", 70)
        out = self.tester.send_expect("lsmod | grep igb_uio", "#")
        if "igb_uio" in out:
            self.tester.send_expect("rmmod -f igb_uio", "#", 70)
        self.tester.send_expect("insmod ~/igb_uio.ko", "#", 60)
        out = self.tester.send_expect("lsmod | grep igb_uio", "#")
        assert ("igb_uio" in out), "Failed to insmod igb_uio"

        total_huge_pages = self.tester.get_total_huge_pages()
        if total_huge_pages == 0:
            self.tester.mount_huge_pages()
            self.tester.set_huge_pages(2048)

    def pktgen_kill(self):
        """
        Kill all pktgen on tester.
        """
        pids = []
        pid_reg = r'p(\d+)'
        out = self.tester.alt_session.send_expect("lsof -Fp /var/run/.pg_config", "#", 20)
        if len(out):
            lines = out.split('\r\n')
            for line in lines:
                m = re.match(pid_reg, line)
                if m:
                    pids.append(m.group(1))
        for pid in pids:
            self.tester.alt_session.send_expect('kill -9 %s' % pid, '# ', 20)

    def send_and_verify(self, dst_mac, testpmd):
        """
        Generates packets by pktgen
        """
        self.testpmd_reset_status(testpmd)

        self.pktgen_prerequisites()
        # bind ports
        self.tester_tx_port = self.tester.get_local_port(self.dut_ports[0])
        self.tester_tx_pci = self.tester.ports_info[self.tester_tx_port]['pci']
        port = self.tester.ports_info[self.tester_tx_port]['port']
        self.tester_port_driver = port.get_nic_driver()
        self.tester.send_expect("./dpdk-devbind.py --bind=igb_uio %s" % self.tester_tx_pci, "#")

        src_mac = self.tester.get_mac(self.tester_tx_port) 
        if src_mac == 'N/A':
            src_mac = "02:00:00:00:01"

        self.create_pcap_file(self.filename, dst_mac, src_mac)

        self.tester.send_expect("./pktgen -c 0x1f -n 2  --proc-type auto --socket-mem 128,128 --file-prefix pg -- -P -T -m '1.0' -s 0:%s" % self.filename, "Pktgen >", 100)
        time.sleep(1)
        self.tester.send_expect("start all", "Pktgen>")
        time.sleep(1)
        self.check_port_start_stop(testpmd)
        # quit pktgen
        self.tester.send_expect("stop all", "Pktgen>")
        self.tester.send_expect("quit", "# ")

    def create_pcap_file(self, filename, dst_mac, src_mac):
        """
        Generates a valid PCAP file with the given configuration.
        """
        def_pkts = {'IP/UDP': Ether(dst="%s" % dst_mac, src="%s" % src_mac)/IP(src="127.0.0.2")/UDP()/("X"*46),
                    'IP/TCP': Ether(dst="%s" % dst_mac, src="%s" % src_mac)/IP(src="127.0.0.2")/TCP()/("X"*46),
                    'IP/SCTP': Ether(dst="%s" % dst_mac, src="%s" % src_mac)/IP(src="127.0.0.2")/SCTP()/("X"*48),
                    'IPv6/UDP': Ether(dst="%s" % dst_mac, src="%s" % src_mac)/IPv6(src="::2")/UDP()/("X"*46),
                    'IPv6/TCP': Ether(dst="%s" % dst_mac, src="%s" % src_mac)/IPv6(src="::2")/TCP()/("X"*46),}

        pkts = []
        for key in def_pkts.keys():
            pkts.append(def_pkts[key])

        wrpcap(filename, pkts)

    def testpmd_reset_status(self, testpmd):
        """
        Reset testpmd :stop forword & stop port
        """
        testpmd.execute_cmd('stop')
        testpmd.execute_cmd('port stop all')
        testpmd.execute_cmd('clear port stats all')

    def check_port_start_stop(self, testpmd, times=10):
        """
        VF port start/stop several times , check if it work well.
        """
        for i in range(times):
            out = testpmd.execute_cmd('port start all')
            self.verify("Checking link statuses" in out, "ERROR: port start all")
            testpmd.execute_cmd('start')
            time.sleep(.5)
            testpmd.execute_cmd('stop')
            out = testpmd.execute_cmd('port stop all')
            self.verify("Checking link statuses" in out, "ERROR: port stop all")

        port_id_0 = 0
        port_id_1 = 1
        vf0_stats = self.vm0_testpmd.get_pmd_stats(port_id_0)
        vf1_stats = self.vm0_testpmd.get_pmd_stats(port_id_1)

        vf0_rx_cnt = vf0_stats['RX-packets']
        self.verify(vf0_rx_cnt != 0, "no packet was received by vm0_VF0")

        vf0_rx_err = vf0_stats['RX-errors']
        self.verify(vf0_rx_err == 0, "vm0_VF0 rx-errors")
    
        vf1_tx_cnt = vf1_stats['TX-packets']
        self.verify(vf1_tx_cnt != 0, "no packet was transmitted by vm0_VF1")

        vf1_tx_err = vf1_stats['TX-errors']
        self.verify(vf1_tx_err == 0, "vm0_VF0 tx-errors")

    def setup_1pf_2vf_1vm_env(self, driver='default'):

        self.used_dut_port = self.dut_ports[0]
        self.dut.generate_sriov_vfs_by_port(self.used_dut_port, 2, driver=driver)
        self.sriov_vfs_port = self.dut.ports_info[self.used_dut_port]['vfs_port']

        try:

            for port in self.sriov_vfs_port:
                port.bind_driver('pci-stub')

            time.sleep(1)

            vf0_prop = {'opt_host': self.sriov_vfs_port[0].pci}
            vf1_prop = {'opt_host': self.sriov_vfs_port[1].pci}

            if driver == 'igb_uio':
                # start testpmd without the two VFs on the host
                self.host_testpmd = PmdOutput(self.dut)
                eal_param = '-b %(vf0)s -b %(vf1)s' % {'vf0': self.sriov_vfs_port[0].pci,
                                                       'vf1': self.sriov_vfs_port[1].pci}
                self.host_testpmd.start_testpmd("1S/2C/2T", eal_param=eal_param)

            # set up VM0 ENV
            self.vm0 = QEMUKvm(self.dut, 'vm0', 'vf_port_start_stop')
            self.vm0.set_vm_device(driver='pci-assign', **vf0_prop)
            self.vm0.set_vm_device(driver='pci-assign', **vf1_prop)
            self.vm_dut_0 = self.vm0.start()
            if self.vm_dut_0 is None:
                raise Exception("Set up VM0 ENV failed!")

            self.setup_1pf_2vf_1vm_env_flag = 1
        except Exception as e:
            self.destroy_1pf_2vf_1vm_env()
            raise Exception(e)

    def destroy_1pf_2vf_1vm_env(self):
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

        if getattr(self, 'used_dut_port', None):
            self.dut.destroy_sriov_vfs_by_port(self.used_dut_port)
            port = self.dut.ports_info[self.used_dut_port]['port']
            port.bind_driver()
            self.used_dut_port = None

        for port_id in self.dut_ports:
            port = self.dut.ports_info[port_id]['port']
            port.bind_driver()

        self.setup_1pf_2vf_1vm_env_flag = 0

    def test_start_stop_with_kernel_1pf_2vf_1vm(self):

        self.setup_1pf_2vf_1vm_env(driver='')

        self.vm0_dut_ports = self.vm_dut_0.get_ports('any')

        self.vm0_testpmd = PmdOutput(self.vm_dut_0)
        if self.kdriver == "i40e":
            self.vm0_testpmd.start_testpmd(VM_CORES_MASK, '--crc-strip')
        else:
            self.vm0_testpmd.start_testpmd(VM_CORES_MASK)
        self.vm0_testpmd.execute_cmd('set fwd mac')

        time.sleep(2)

        dst_mac = self.vm_dut_0.get_mac_address(self.vm0_dut_ports[0])
        self.send_and_verify(dst_mac, self.vm0_testpmd) 

    def tear_down(self):

        if self.setup_1pf_2vf_1vm_env_flag == 1:
            self.destroy_1pf_2vf_1vm_env()

    def tear_down_all(self):

        self.pktgen_kill()
        self.tester.send_expect("./dpdk-devbind.py --bind=%s %s" %(self.tester_port_driver, self.tester_tx_pci), "#")

        if getattr(self, 'vm0', None):
            self.vm0.stop()

        for port_id in self.dut_ports:
            self.dut.destroy_sriov_vfs_by_port(port_id)
