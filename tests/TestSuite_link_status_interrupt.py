# <COPYRIGHT_TAG>

"""
DPDK Test suite.

Link Status Detection

"""

# NOTE: These tests generally won't work in automated mode since the
# link doesn't stay down unless the cable is actually removed. The code
# is left here for legacy reasons.


import dts
import re

testPorts = []
intr_mode = ['"intr_mode=random"',
             '"intr_mode=msix"', '"intr_mode=legacy"', '']
intr_mode_output = ['Error: bad parameter - random', 'Use MSIX interrupt',
                    'Use legacy interrupt', 'Use MSIX interrupt by default']


from test_case import TestCase

#
#
# Test class.
#


class TestLinkStatusInterrupt(TestCase):

    #
    #
    #
    # Test cases.
    #

    def set_up_all(self):
        """
        Run at the start of each test suite.


        Link Status Interrupt Prerequisites
        """

        dutPorts = self.dut.get_ports(self.nic)
        self.verify(len(dutPorts) > 1, "Insufficient ports for " + self.nic)
        for n in range(2):
            testPorts.append(dutPorts[n])
            inter = self.tester.get_interface(
                self.tester.get_local_port(testPorts[n]))
            self.tester.send_expect("ifconfig %s up" % inter, "# ", 5)
        out = self.dut.send_expect(
            "make -C examples/link_status_interrupt", "# ")
        self.verify("Error" not in out, "Compilation error 1")
        self.verify("No such file" not in out, "Compilation error 2")

    def set_link_status_and_verify(self, dutPort, status):
        """
        In registered callback...
        Event type: LSC interrupt
        Port 0 Link Up - speed 10000 Mbps - full-duplex

        In registered callback...
        Event type: LSC interrupt
        Port 0 Link Down
        """

        inter = self.tester.get_interface(self.tester.get_local_port(dutPort))
        self.tester.send_expect("ifconfig %s %s" % (inter, status), "# ", 10)
        self.dut.send_expect("", "Port %s Link %s" %
                             (dutPort, status.capitalize()), 60)
        out = self.dut.send_expect("", "Aggregate statistics", 60)
        exp = r"Statistics for port (\d+) -+\r\n" + \
            "Link status:\s+Link (up|down)\r\n"
        pattern = re.compile(exp)
        info = pattern.findall(out)
        if info[0][0] == repr(dutPort):
            self.verify(info[0][1] == status, "Link status change port error")
        else:
            self.verify(info[1][1] == status, "Link status change hello error")

    def set_up(self):
        """
        Run before each test case.
        """
        pass

    def test_link_status_interrupt_change(self):
        """
        Link status change.
        """

        memChannel = self.dut.get_memory_channels()
        portMask = dts.create_mask(testPorts)
        if dts.drivername in ["igb_uio"]:
            cmdline = "./examples/link_status_interrupt/build/link_status_interrupt -c f -n %s -- -q 2 -p %s" % (
                memChannel, portMask)
        elif dts.drivername in ["vfio-pci"]:
            cmdline = "./examples/link_status_interrupt/build/link_status_interrupt -c f -n %s --vfio-intr=intx  -- -q 2 -p %s" % (
                memChannel, portMask)
        else:
            print "unknow driver"
        for n in range(len(intr_mode)):
            if dts.drivername in ["igb_uio"]:
                self.dut.send_expect("rmmod igb_uio", "# ")
                self.dut.send_expect(
                    "insmod %s/kmod/igb_uio.ko %s" % (self.target, intr_mode[n]), "# ")
                self.dut.send_expect("tools/dpdk-devbind.py --bind=igb_uio 03:00.0 03:00.1", "# ")
                out = self.dut.send_expect(
                    "dmesg -c | grep '\<%s\>'" % (intr_mode_output[n]), "# ")
                self.verify(
                    intr_mode_output[n] in out, "Fail to insmod igb_uio " + intr_mode[n])
                if n == 0:
                    continue
            self.dut.send_expect(cmdline, "Aggregate statistics", 605)
            self.dut.send_expect(
                "", "Port %s Link Up.+\r\n" % (testPorts[1]), 5)
            self.set_link_status_and_verify(testPorts[0], 'down')
            self.set_link_status_and_verify(testPorts[0], 'up')
            self.set_link_status_and_verify(testPorts[1], 'down')
            self.set_link_status_and_verify(testPorts[1], 'up')
            self.dut.send_expect("^C", "# ")

    def FAILING_test_link_status_interrupt_port_available(self):
        """
        Port available.
        """

        memChannel = self.dut.get_memory_channels()
        portMask = dts.create_mask(testPorts)
        if dts.drivername in ["igb_uio"]:
            cmdline = "./examples/link_status_interrupt/build/link_status_interrupt -c f -n %s -- -q 2 -p %s" % (
                memChannel, portMask)
        elif dts.drivername in ["vfio-pci"]:
            cmdline = "./examples/link_status_interrupt/build/link_status_interrupt -c f -n %s --vfio-intr=intx -- -q 2 -p %s " % (
                memChannel, portMask)
        else:
            print "unknow driver"
        for n in range(1, len(intr_mode)):
            if dts.drivername in ["igb_uio"]:
                self.dut.send_expect("rmmod igb_uio", "# ")
                self.dut.send_expect(
                    "insmod %s/kmod/igb_uio.ko %s" % (self.target, intr_mode[n]), "# ")
                out = self.dut.send_expect(
                    "dmesg -c | grep '\<%s\>'" % (intr_mode_output[n]), "# ")
                self.verify(
                    intr_mode_output[n] in out, "Fail to insmod igb_uio " + intr_mode[n])
            self.dut.send_expect(cmdline, "Aggregate statistics", 60)
            self.dut.send_expect(
                "", "Port %s Link Up.+\r\n" % (testPorts[1]), 5)
            self.set_link_status_and_verify(testPorts[0], 'down')
            self.set_link_status_and_verify(testPorts[1], 'down')
            self.set_link_status_and_verify(testPorts[0], 'up')
            self.set_link_status_and_verify(testPorts[1], 'up')
            for m in [0, 1]:
                txPort = self.tester.get_local_port(testPorts[m])
                rxPort = self.tester.get_local_port(testPorts[1 - m])
                txItf = self.tester.get_interface(txPort)
                rxItf = self.tester.get_interface(rxPort)
                self.tester.scapy_background()
                self.tester.scapy_append(
                    'p = sniff(iface="%s", count=1)' % rxItf)
                self.tester.scapy_append('nr_packets=len(p)')
                self.tester.scapy_append('RESULT = str(nr_packets)')
                self.tester.scapy_foreground()
                self.tester.scapy_append(
                    'sendp([Ether()/IP()/UDP()/("X"*46)], iface="%s")' % txItf)
                self.tester.scapy_execute()
                nr_packets = self.tester.scapy_get_result()
                self.verify(nr_packets == "1", "Fail to switch L2 frame")
            self.dut.send_expect("^C", "# ")

    def test_link_status_interrupt_recovery(self):
        """
        Recovery.
        """
        if dts.drivername in ["igb_uio"]:
            self.dut.send_expect("^C", "# ")
            self.dut.send_expect("rmmod igb_uio", "# ")
            self.dut.send_expect(
                "insmod %s/kmod/igb_uio.ko" % (self.target), "# ")
            out = self.dut.send_expect(
                "dmesg -c | grep '\<Use MSIX interrupt by default\>'", "# ")
            self.verify(
                'Use MSIX interrupt by default' in out, "Fail to recovery default igb_uio")
        elif dts.drivername in ["vfio-pci"]:
            self.verify(Ture, "not need run this case, when used vfio driver")
        else:
            print "unknow driver"

    def tear_down(self):
        """
        Run after each test case.
        """
        pass

    def tear_down_all(self):
        """
        Run after each test suite.
        """
        pass
