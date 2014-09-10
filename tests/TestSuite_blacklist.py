# <COPYRIGHT_TAG>

"""
DPDK Test suite.

Test device blacklisting.

"""

import dcts


from test_case import TestCase


#
#
# Test class.
#
class TestBlacklist(TestCase):

    #
    #
    #
    # Test cases.
    #

    def set_up_all(self):
        """
        Run at the start of each test suite.

        Blacklist Prerequisites.
        Requirements:
            Two Ports
        """

        self.ports = self.dut.get_ports(self.nic)
        self.verify(len(self.ports) >= 2, "Insufficient ports for testing")
        self.regexp_blacklisted_port = "EAL: PCI device 0000:%s on NUMA socket [-0-9]+[^\n]*\nEAL:   probe driver[^\n]*\nEAL:   Device is blacklisted, not initializing"

    def set_up(self):
        """
        Run before each test case.
        Nothing to do.
        """
        pass

    def check_blacklisted_ports(self, output, ports, blacklisted=False):
        """
        Check if any of the ports in `ports` have been blacklisted, if so, raise
        exception.
        If `blacklisted` is True, then raise an exception if any of the ports
        in `ports` have not been blacklisted.
        """
        for port in ports:

            # Look for the PCI ID of each card followed by
            # "Device is blacklisted, not initializing" but avoid to consume more
            # than one device.
            regexp_blacklisted_port = self.regexp_blacklisted_port % self.dut.ports_info[port]['pci']

            matching_ports = dcts.regexp(output, regexp_blacklisted_port, True)

            if blacklisted:
                self.verify(len(matching_ports) == 1,
                            "Blacklisted port is being initialized")
            else:
                self.verify(len(matching_ports) == 0,
                            "Not blacklisted port is being blacklisted")

    def test_bl_noblacklisted(self):
        """
        Run testpmd with no blacklisted device.
        """

        cmdline = r"./%s/build/app/test-pmd/testpmd -n 1 -c 3 -- -i" % self.target
        out = self.dut.send_expect(cmdline, "testpmd> ", 120)
        rexp = r"Link"
        match_status = dcts.regexp(out, rexp, True)

        self.check_blacklisted_ports(out, self.ports)

    def test_bl_oneportblacklisted(self):
        """
        Run testpmd with one port blacklisted.
        """
        self.dut.kill_all()

        cmdline = r"./%s/build/app/test-pmd/testpmd -n 1 -c 3 -b 0000:%s -- -i" % (self.target, self.dut.ports_info[0]['pci'])
        out = self.dut.send_expect(cmdline, "testpmd> ", 120)

        self.check_blacklisted_ports(out, self.ports[1:])

    def test_bl_allbutoneportblacklisted(self):
        """
        Run testpmd with all but one port blacklisted.
        """
        self.dut.kill_all()

        ports_to_blacklist = self.ports[:-1]

        cmdline = "./%s/build/app/test-pmd/testpmd -n 1 -c 3" % self.target
        for port in ports_to_blacklist:
            cmdline += " -b 0000:%s" % self.dut.ports_info[port]['pci']

        cmdline += " -- -i"
        out = self.dut.send_expect(cmdline, "testpmd> ", 180)

        blacklisted_ports = self.check_blacklisted_ports(out,
                                                         ports_to_blacklist,
                                                         True)

    def tear_down(self):
        """
        Run after each test case.
        Quit testpmd.
        """
        self.dut.send_expect("quit", "# ", 10)

    def tear_down_all(self):
        """
        Run after each test suite.
        Nothing to do.
        """
        pass
