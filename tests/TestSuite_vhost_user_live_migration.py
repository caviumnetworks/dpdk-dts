# <COPYRIGHT_TAG>

import re
import time

from qemu_kvm import QEMUKvm
from test_case import TestCase
from exception import VirtDutInitException


class TestVhostUserLiveMigration(TestCase):

    def set_up_all(self):
        # verify at least two duts
        self.verify(len(self.duts) >= 2, "Insufficient duts for live migration!!!")

        # each dut required one ports
        self.dut_ports = self.dut.get_ports()
        # Verify that enough ports are available
        self.verify(len(self.dut_ports) >= 1, "Insufficient ports for testing")
        self.dut_port = self.dut_ports[0]
        dut_ip = self.dut.crb['My IP']
        self.host_tport = self.tester.get_local_port_bydut(self.dut_port, dut_ip)
        self.host_tintf = self.tester.get_interface(self.host_tport)

        self.backup_ports = self.duts[1].get_ports()
        # Verify that enough ports are available
        self.verify(len(self.backup_ports) >= 1, "Insufficient ports for testing")
        self.backup_port = self.backup_ports[0]
        # backup host ip will be used in migrate command
        self.backup_dutip = self.duts[1].crb['My IP']
        self.backup_tport = self.tester.get_local_port_bydut(self.backup_port, self.backup_dutip)
        self.backup_tintf = self.tester.get_interface(self.backup_tport)

        # build backup vhost-switch
        out = self.duts[0].send_expect("make -C examples/vhost", "# ")
        self.verify("Error" not in out, "compilation error 1")
        self.verify("No such file" not in out, "compilation error 2")

        # build backup vhost-switch
        out = self.duts[1].send_expect("make -C examples/vhost", "# ")
        self.verify("Error" not in out, "compilation error 1")
        self.verify("No such file" not in out, "compilation error 2")

        self.vhost = "./examples/vhost/build/app/vhost-switch"
        self.vm_testpmd = "./%s/app/testpmd -c 0x3 -n 4 -- -i" % self.target
        self.virio_mac = "00:00:00:00:00:01"

        # flag for environment
        self.env_done = False

    def set_up(self):
        self.setup_vm_env()
        pass

    def bind_nic_driver(self, crb,  ports, driver=""):
        # modprobe vfio driver
        if driver == "vfio-pci":
            for port in ports:
                netdev = crb.ports_info[port]['port']
                driver = netdev.get_nic_driver()
                if driver != 'vfio-pci':
                    netdev.bind_driver(driver='vfio-pci')

        elif driver == "igb_uio":
            # igb_uio should insmod as default, no need to check
            for port in ports:
                netdev = crb.ports_info[port]['port']
                driver = netdev.get_nic_driver()
                if driver != 'igb_uio':
                    netdev.bind_driver(driver='igb_uio')
        else:
            for port in ports:
                netdev = crb.ports_info[port]['port']
                driver_now = netdev.get_nic_driver()
                if driver == "":
                    driver = netdev.default_driver
                if driver != driver_now:
                    netdev.bind_driver(driver=driver)

    def setup_vm_env(self, driver='default'):
        """
        Create testing environment on Host and Backup
        """
        if self.env_done:
            return

        # start vhost-switch on host and backup machines
        self.logger.info("Start vhost on host and backup host")
        for crb in self.duts[:2]:
            self.bind_nic_driver(crb, [crb.get_ports()[0]], driver="igb_uio")
            # start vhost-switch, predict hugepage on both sockets
            base_dir = crb.base_dir.replace('~', '/root')
            crb.send_expect("rm -f %s/vhost-net" % base_dir, "# ")
            crb.send_expect("%s -c f -n 4 --socket-mem 1024 -- -p 0x1" % self.vhost, "bind to vhost-net")

        try:
            # set up host virtual machine
            self.host_vm = QEMUKvm(self.duts[0], 'host', 'vhost_user_live_migration')
            vhost_params = {}
            vhost_params['driver'] = 'vhost-user'
            # qemu command can't use ~
            base_dir = self.dut.base_dir.replace('~', '/root')
            vhost_params['opt_path'] = base_dir + '/vhost-net'
            vhost_params['opt_mac'] = self.virio_mac
            self.host_vm.set_vm_device(**vhost_params)

            self.logger.info("Start virtual machine on host")
            self.vm_host = self.host_vm.start()

            if self.vm_host is None:
                raise Exception("Set up host VM ENV failed!")

            self.host_serial = self.host_vm.connect_serial_port(name='vhost_user_live_migration')
            if self.host_serial is None:
                raise Exception("Connect host serial port failed!")

            self.logger.info("Start virtual machine on backup host")
            # set up backup virtual machine
            self.backup_vm = QEMUKvm(self.duts[1], 'backup', 'vhost_user_live_migration')
            vhost_params = {}
            vhost_params['driver'] = 'vhost-user'
            # qemu command can't use ~
            base_dir = self.dut.base_dir.replace('~', '/root')
            vhost_params['opt_path'] = base_dir + '/vhost-net'
            vhost_params['opt_mac'] = self.virio_mac
            self.backup_vm.set_vm_device(**vhost_params)

            # start qemu command
            self.backup_vm.start()

        except Exception as ex:
            if ex is VirtDutInitException:
                self.host_vm.stop()
                self.host_vm = None
                # no session created yet, call internal stop function
                self.backup_vm._stop_vm()
                self.backup_vm = None
            else:
                self.destroy_vm_env()
                raise Exception(ex)

        self.env_done = True

    def destroy_vm_env(self):
        # if environment has been destroyed, just skip
        if self.env_done is False:
            return

        if getattr(self, 'host_serial', None):
            if self.host_vm is not None:
                self.host_vm.close_serial_port()

        if getattr(self, 'backup_serial', None):
            if self.backup_serial is not None and self.backup_vm is not None:
                self.backup_vm.close_serial_port()

        self.logger.info("Stop virtual machine on host")
        if getattr(self, 'vm_host', None):
            if self.vm_host is not None:
                self.host_vm.stop()
                self.host_vm = None

        self.logger.info("Stop virtual machine on backup host")
        if getattr(self, 'vm_backup', None):
            if self.vm_backup is not None:
                self.vm_backup.kill_all()
                # backup vm dut has been initialized, destroy backup vm
                self.backup_vm.stop()
                self.backup_vm = None

        if getattr(self, 'backup_vm', None):
            # only qemu start, no session created
            if self.backup_vm is not None:
                self.backup_vm.stop()
                self.backup_vm = None

        # after vm stopped, stop vhost-switch
        for crb in self.duts[:2]:
            crb.kill_all()

        for crb in self.duts[:2]:
            self.bind_nic_driver(crb, [crb.get_ports()[0]], driver="igb_uio")

        self.env_done = False

    def send_pkts(self, intf, number=0):
        """
        send packet from tester
        """
        sendp_fmt = "sendp([Ether(dst='%(DMAC)s')/Dot1Q(vlan=1000)/IP()/UDP()/Raw('x'*18)], iface='%(INTF)s', count=%(COUNT)d)"
        sendp_cmd = sendp_fmt % {'DMAC': self.virio_mac, 'INTF': intf, 'COUNT': number}
        self.tester.scapy_append(sendp_cmd)
        self.tester.scapy_execute()
        # sleep 10 seconds for heavy load with backup host
        time.sleep(10)

    def verify_dpdk(self, tester_port, serial_session):
        num_pkts = 10

        stats_pat = re.compile("RX-packets: (\d+)")
        intf = self.tester.get_interface(tester_port)
        serial_session.send_expect("stop", "testpmd> ")
        serial_session.send_expect("set fwd rxonly", "testpmd> ")
        serial_session.send_expect("clear port stats all", "testpmd> ")
        serial_session.send_expect("start tx_first", "testpmd> ")

        # send packets from tester
        self.send_pkts(intf, number=num_pkts)

        out = serial_session.send_expect("show port stats 0", "testpmd> ")
        m = stats_pat.search(out)
        if m:
            num_received = int(m.group(1))
        else:
            num_received = 0

        self.verify(num_received >= num_pkts, "Not receive packets as expected!!!")
        self.logger.info("Verified %s packets recevied" % num_received)

    def verify_kernel(self, tester_port, vm_dut):
        """
        Function to verify packets received by virtIO
        """
        intf = self.tester.get_interface(tester_port)
        num_pkts = 10

        # get host interface
        vm_intf = vm_dut.ports_info[0]['port'].get_interface_name()
        # start tcpdump the interface
        vm_dut.send_expect("ifconfig %s up" % vm_intf, "# ")
        vm_dut.send_expect("tcpdump -i %s -P in -v" % vm_intf, "listening on")
        # wait for promisc on
        time.sleep(3)
        # send packets from tester
        self.send_pkts(intf, number=num_pkts)

        # killall tcpdump and verify packet received
        out = vm_dut.get_session_output(timeout=1)
        vm_dut.send_expect("^C", "# ")
        num = out.count('UDP')
        self.verify(num == num_pkts, "Not receive packets as expected!!!")
        self.logger.info("Verified %s packets recevied" % num_pkts)

    def test_migrate_with_kernel(self):
        """
        Verify migrate virtIO device from host to backup host,
        Verify before/in/after migration, device with kernel driver can receive packets
        """
        # bind virtio-net back to virtio-pci
        self.bind_nic_driver(self.vm_host, [self.vm_host.get_ports()[0]], driver="")
        # verify host virtio-net work fine
        self.verify_kernel(self.host_tport, self.vm_host)

        self.logger.info("Migrate host VM to backup host")
        # start live migration
        self.host_vm.start_migration(self.backup_dutip, self.backup_vm.migrate_port)

        # make sure still can receive packets in migration process
        self.verify_kernel(self.host_tport, self.vm_host)

        self.logger.info("Waiting migration process done")
        # wait live migration done
        self.host_vm.wait_migration_done()

        # check vhost-switch log after migration
        out = self.duts[0].get_session_output(timeout=1)
        self.verify("device has been removed" in out, "Device not removed for host")
        out = self.duts[1].get_session_output(timeout=1)
        self.verify("virtio is now ready" in out, "Device not ready on backup host")

        self.logger.info("Migration process done, init backup VM")
        # connected backup VM
        self.vm_backup = self.backup_vm.migrated_start()

        # make sure still can receive packets
        self.verify_kernel(self.backup_tport, self.vm_backup)

    def test_migrate_with_dpdk(self):
        # bind virtio-net to igb_uio
        self.bind_nic_driver(self.vm_host, [self.vm_host.get_ports()[0]], driver="igb_uio")

        # start testpmd on host vm
        base_dir = self.vm_host.base_dir.replace('~', '/root')
        self.host_serial.send_expect('cd %s' % base_dir, "# ")
        self.host_serial.send_expect(self.vm_testpmd, "testpmd> ")

        # verify testpmd receive packets
        self.verify_dpdk(self.host_tport, self.host_serial)

        self.logger.info("Migrate host VM to backup host")
        # start live migration
        self.host_vm.start_migration(self.backup_dutip, self.backup_vm.migrate_port)

        # make sure still can receive packets in migration process
        self.verify_dpdk(self.host_tport, self.host_serial)

        self.logger.info("Waiting migration process done")
        # wait live migration done
        self.host_vm.wait_migration_done()

        # check vhost-switch log after migration
        out = self.duts[0].get_session_output(timeout=1)
        self.verify("device has been removed" in out, "Device not removed for host")
        out = self.duts[1].get_session_output(timeout=1)
        self.verify("virtio is now ready" in out, "Device not ready on backup host")

        self.logger.info("Migration process done, init backup VM")
        time.sleep(5)

        # make sure still can receive packets
        self.backup_serial = self.backup_vm.connect_serial_port(name='vhost_user_live_migration', first=False)
        if self.backup_serial is None:
            raise Exception("Connect backup host serial port failed!")

        self.verify_dpdk(self.backup_tport, self.backup_serial)

        # quit testpmd
        self.backup_serial.send_expect("quit", "# ")

    def tear_down(self):
        self.destroy_vm_env()
        pass

    def tear_down_all(self):
        pass
