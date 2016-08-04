# <COPYRIGHT_TAG>

import re
import time

import utils
from qemu_kvm import QEMUKvm
from test_case import TestCase
from pmd_output import PmdOutput
from settings import HEADER_SIZE
from packet import Packet
from utils import RED

VM_CORES_MASK = 'all'

ETHER_STANDARD_MTU = 1518
ETHER_JUMBO_FRAME_MTU = 9000


class TestVfJumboFrame(TestCase):

    def set_up_all(self):

        self.dut_ports = self.dut.get_ports(self.nic)
        self.verify(len(self.dut_ports) >= 1, "Insufficient ports")
        self.vm0 = None
        self.env_done = False

        self.port = self.dut_ports[0]
        self.vm_port = 0
        cores = self.dut.get_core_list("1S/1C/1T")
        self.port_mask = utils.create_mask([self.port])
        
        # enable tester mtu
        tester_port = self.tester.get_local_port(self.port)
        self.netobj = self.tester.ports_info[tester_port]['port']
        self.netobj.enable_jumbo(framesize=ETHER_JUMBO_FRAME_MTU + 100)


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
        Create testing environment with 1VF generated from 1PF
        """
        if self.env_done:
            return

        # bind to default driver
        self.bind_nic_driver(self.dut_ports[:1], driver="")

        self.used_dut_port = self.dut_ports[0]
        self.host_intf = self.dut.ports_info[self.used_dut_port]['intf']
        tester_port = self.tester.get_local_port(self.used_dut_port)
        self.tester_intf = self.tester.get_interface(tester_port)

        self.dut.generate_sriov_vfs_by_port(
            self.used_dut_port, 1, driver=driver)
        self.sriov_vfs_port = self.dut.ports_info[
            self.used_dut_port]['vfs_port']
        self.vf_mac = "00:10:00:00:00:00"
        self.dut.send_expect("ip link set %s vf 0 mac %s" %
                             (self.host_intf, self.vf_mac), "# ")

        try:

            for port in self.sriov_vfs_port:
                port.bind_driver('pci-stub')

            time.sleep(1)
            vf_popt = {'opt_host': self.sriov_vfs_port[0].pci}

            # set up VM ENV
            self.vm = QEMUKvm(self.dut, 'vm0', 'vf_jumboframe')
            self.vm.set_vm_device(driver='pci-assign', **vf_popt)
            self.vm_dut = self.vm.start()
            if self.vm_dut is None:
                raise Exception("Set up VM ENV failed!")

            TESTPMD_MAIN = "app/test-pmd/testpmd.c"
            if self.kdriver == "ixgbe":
                self.vm_dut.send_expect("sed -i -e 's/.jumbo_frame    = .*$/.jumbo_frame = 1,/g' %s" % TESTPMD_MAIN, "# ")
                self.vm_dut.build_install_dpdk(self.target)

            self.vm_testpmd = PmdOutput(self.vm_dut)

        except Exception as e:
            self.destroy_vm_env()
            raise Exception(e)

        self.env_done = True

    def destroy_vm_env(self):
        if getattr(self, 'vm', None):
            self.vm_dut.kill_all()
            self.vm_testpmd = None
            self.vm_dut_ports = None
            # destroy vm0
            self.vm.stop()
            self.vm = None

        if getattr(self, 'used_dut_port', None):
            self.dut.destroy_sriov_vfs_by_port(self.used_dut_port)
            self.used_dut_port = None

        self.bind_nic_driver(self.dut_ports[:1], driver="igb_uio")

        self.env_done = False


    def jumboframes_get_stat(self, portid, rx_tx):
        """
        Get packets number from port statistic
        """
        stats = self.vm_testpmd.get_pmd_stats(portid)
        if rx_tx == "rx":
            return [stats['RX-packets'], stats['RX-errors'], stats['RX-bytes']]
        elif rx_tx == "tx":
            return [stats['TX-packets'], stats['TX-errors'], stats['TX-bytes']]
        else:
            return None

    def jumboframes_send_packet(self, pktsize, received=True):
        """
        Send 1 packet to portid
        """
        tx_pkts_ori, _, tx_bytes_ori = [int(_) for _ in self.jumboframes_get_stat(self.vm_port, "tx")]
        rx_pkts_ori, rx_err_ori, rx_bytes_ori = [int(_) for _ in self.jumboframes_get_stat(self.vm_port, "rx")]

        mac = self.vm_dut.get_mac_address(self.vm_port)

        pkt = Packet(pkt_type='UDP', pkt_len=pktsize)
        pkt.config_layer('ether', {'dst': mac})
        pkt.send_pkt(tx_port=self.tester_intf)

        time.sleep(1)

        tx_pkts, _, tx_bytes = [int(_) for _ in self.jumboframes_get_stat(self.port, "tx")]
        rx_pkts, rx_err, rx_bytes = [int(_) for _ in self.jumboframes_get_stat(self.vm_port, "rx")]

        tx_pkts -= tx_pkts_ori
        tx_bytes -= tx_bytes_ori
        rx_pkts -= rx_pkts_ori
        rx_bytes -= rx_bytes_ori
        rx_err -= rx_err_ori

        if received:
            self.verify((rx_pkts == 1) and (tx_pkts == 1), "Packet forward assert error")
            if self.kdriver == "ixgbe":
                self.verify((rx_bytes + 4) == pktsize, "Rx packet size should be packet size - 4")
            else:
                self.verify(rx_bytes == pktsize, "Tx packet size should be equal to packet size")
            self.verify((tx_bytes + 4) == pktsize, "Tx packet size should be packet size - 4")
        else:
            self.verify(rx_err == 1 or tx_pkts == 0, "Packet drop assert error")

    def test_vf_normal_nojumbo(self):
        """
        This case aims to test transmitting normal size packet without jumbo enable
        """
        # should enable jumbo on host
        if self.kdriver == "ixgbe":
            self.dutobj = self.dut.ports_info[self.port]['port']
            self.dutobj.enable_jumbo(framesize=ETHER_STANDARD_MTU)
            time.sleep(2)

        if self.kdriver == "i40e":
            self.vm_testpmd.start_testpmd("Default", "--max-pkt-len=%d --port-topology=loop --crc-strip --txqflags=0x0" % (ETHER_STANDARD_MTU))
        else:
            self.vm_testpmd.start_testpmd("Default", "--max-pkt-len=%d --port-topology=loop --txqflags=0x0" % (ETHER_STANDARD_MTU))

        self.vm_testpmd.execute_cmd("set fwd mac")
        self.vm_testpmd.execute_cmd("start")

        self.jumboframes_send_packet(ETHER_STANDARD_MTU - 1)
        self.jumboframes_send_packet(ETHER_STANDARD_MTU)

        self.vm_testpmd.execute_cmd("stop")
        self.vm_testpmd.quit()

    def test_vf_normal_withjumbo(self):
        """
        When jumbo frame supported, this case is to verify that the normal size
        packet forwrding should be support correct.
        """
        # should enable jumbo on host
        if self.kdriver == "ixgbe":
            self.dutobj = self.dut.ports_info[self.port]['port']
            self.dutobj.enable_jumbo(framesize=ETHER_JUMBO_FRAME_MTU)
            time.sleep(2)

        if self.kdriver == "i40e":
            self.vm_testpmd.start_testpmd("Default", "--max-pkt-len=%d --port-topology=loop --crc-strip --txqflags=0x0" % (ETHER_JUMBO_FRAME_MTU))
        else:
            self.vm_testpmd.start_testpmd("Default", "--max-pkt-len=%s --port-topology=loop --txqflags=0x0" % (ETHER_JUMBO_FRAME_MTU))

        self.vm_testpmd.execute_cmd("set fwd mac")
        self.vm_testpmd.execute_cmd("start")

        self.jumboframes_send_packet(ETHER_STANDARD_MTU - 1)
        self.jumboframes_send_packet(ETHER_STANDARD_MTU)

        self.vm_testpmd.execute_cmd("stop")
        self.vm_testpmd.quit()

    def test_vf_jumbo_nojumbo(self):
        """
        This case aims to test transmitting jumbo frame packet on testpmd without
        jumbo frame support.
        """
        # should enable jumbo on host
        if self.kdriver == "ixgbe":
            self.dutobj = self.dut.ports_info[self.port]['port']
            self.dutobj.enable_jumbo(framesize=ETHER_STANDARD_MTU)
            time.sleep(2)

        if self.kdriver == "i40e":
            self.vm_testpmd.start_testpmd("Default", "--port-topology=loop --crc-strip --txqflags=0x0" )
        else:
            self.vm_testpmd.start_testpmd("Default", "--port-topology=loop --txqflags=0x0")

        self.vm_testpmd.execute_cmd("set fwd mac")
        self.vm_testpmd.execute_cmd("start")

        self.jumboframes_send_packet(ETHER_STANDARD_MTU + 1, False)

        self.vm_testpmd.execute_cmd("stop")
        self.vm_testpmd.quit()

    def test_vf_jumbo_withjumbo(self):
        """
        When jumbo frame supported, this case is to verify that jumbo frame
        packet can be forwarded correct.
        """
        # should enable jumbo on host
        if self.kdriver == "ixgbe":
            self.dutobj = self.dut.ports_info[self.port]['port']
            self.dutobj.enable_jumbo(framesize=ETHER_JUMBO_FRAME_MTU)
            time.sleep(2)

        if self.kdriver == "i40e":
            self.vm_testpmd.start_testpmd("Default", "--max-pkt-len=%d --port-topology=loop --crc-strip --txqflags=0x0" % (ETHER_JUMBO_FRAME_MTU))
        else:
            self.vm_testpmd.start_testpmd("Default", "--max-pkt-len=%s --port-topology=loop --txqflags=0x0" % (ETHER_JUMBO_FRAME_MTU))

        self.vm_testpmd.execute_cmd("set fwd mac")
        self.vm_testpmd.execute_cmd("start")

        self.jumboframes_send_packet(ETHER_STANDARD_MTU + 1)
        self.jumboframes_send_packet(ETHER_JUMBO_FRAME_MTU - 1)
        self.jumboframes_send_packet(ETHER_JUMBO_FRAME_MTU)

        self.vm_testpmd.execute_cmd("stop")
        self.vm_testpmd.quit()

    def test_vf_jumbo_overjumbo(self):
        """
        When the jubmo frame MTU set as 9000, this case is to verify that the
        packet which the length bigger than MTU can not be forwarded.
        """
        # should enable jumbo on host
        if self.kdriver == "ixgbe":
            self.dutobj = self.dut.ports_info[self.port]['port']
            self.dutobj.enable_jumbo(framesize=ETHER_JUMBO_FRAME_MTU)
            time.sleep(2)

        if self.kdriver == "i40e":
            self.vm_testpmd.start_testpmd("Default", "--max-pkt-len=%d --port-topology=loop --crc-strip --txqflags=0x0" % (ETHER_JUMBO_FRAME_MTU))
        else:
            self.vm_testpmd.start_testpmd("Default", "--max-pkt-len=%s --port-topology=loop --txqflags=0x0" % (ETHER_JUMBO_FRAME_MTU))

        self.vm_testpmd.execute_cmd("set fwd mac")
        self.vm_testpmd.execute_cmd("start")

        self.jumboframes_send_packet(ETHER_JUMBO_FRAME_MTU + 1, False)

        self.vm_testpmd.execute_cmd("stop")
        self.vm_testpmd.quit()

    def tear_down(self):
        """
        Run after each test case.
        """
        self.vm_dut.kill_all()
        pass

    def tear_down_all(self):
        """
        When the case of this test suite finished, the enviroment should
        clear up.
        """
        self.destroy_vm_env()
        self.netobj.enable_jumbo(framesize=ETHER_STANDARD_MTU)
