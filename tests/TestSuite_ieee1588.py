# <COPYRIGHT_TAG>

"""
DPDK Test suite.

Test support of IEEE1588 Precise Time Protocol.
"""

import dcts
import time


from test_case import TestCase

#
#
# Test class.
#


class TestIeee1588(TestCase):

    #
    #
    #
    # Test cases.
    #

    def set_up_all(self):
        """
        Run at the start of each test suite.


        IEEE1588 Prerequisites
        """

        dutPorts = self.dut.get_ports(self.nic)
        self.verify(len(dutPorts) > 0, "No ports found for " + self.nic)

        # Change the config file to support IEEE1588 and recompile the package.
        if "bsdapp" in self.target:
            self.dut.send_expect("sed -i -e 's/IEEE1588=n$/IEEE1588=y/' config/common_bsdapp", "# ", 30)
        else:
            self.dut.send_expect("sed -i -e 's/IEEE1588=n$/IEEE1588=y/' config/common_linuxapp", "# ", 30)
        self.dut.skip_setup = False
        self.dut.build_install_dpdk(self.target)

        self.dut.send_expect("./%s/app/testpmd -c ffffff -n 3 -- -i --rxpt=0 --rxht=0 --rxwt=0 --txpt=39 --txht=0 --txwt=0" % self.target,
                             "testpmd> ", 100)

    def set_up(self):
        """
        Run before each test case.
        """
        pass

    def test_ieee1588_enable(self):
        """
        IEEE1588 Enable test case.
        """

        self.dut.send_expect("set fwd ieee1588", "testpmd> ")
        self.dut.send_expect("start", ">", 5)  # Waiting for 'testpmd> ' Fails due to log messages, "Received non PTP packet", in the output
        time.sleep(1)  # Allow the output from the "start" command to finish before looking for a regexp in expect

        # use the first port on that self.nic
        dutPorts = self.dut.get_ports(self.nic)
        port = self.tester.get_local_port(dutPorts[0])
        itf = self.tester.get_interface(port)

        self.tester.scapy_background()
        self.tester.scapy_append('p = sniff(iface="%s", count=2)' % itf)
        self.tester.scapy_append('RESULT = p[1].summary()')

        # this is the output of sniff
        # [<Ether  dst=01:1b:19:00:00:00 src=00:00:00:00:00:00 type=0x88f7 |<Raw  load='\x00\x02' |>>]

        self.tester.scapy_foreground()
        self.tester.scapy_append('nutmac="01:1b:19:00:00:00"')
        self.tester.scapy_append('sendp([Ether(dst=nutmac,type=0x88f7)/"\\x00\\x02"], iface="%s")' % itf)
        self.tester.scapy_append('time.sleep(1)')

        self.tester.scapy_execute()
        out = self.tester.scapy_get_result()
        self.verify("0x88f7" in out, "Ether type is not PTP")
        # self.verify("\\x00\\x02" in out, "Payload wrong in PTP")

        time.sleep(1)
        out = self.dut.send_expect("stop", "testpmd> ")

        text = dcts.regexp(out, "(.*) by hardware")
        self.verify("IEEE1588 PTP V2 SYNC" in text, "Not filtered " + text)

        rx_time = dcts.regexp(out, "RX timestamp value (0x[0-9a-fA-F]+)")
        tx_time = dcts.regexp(out, "TX timestamp value (0x[0-9a-fA-F]+)")

        self.verify(rx_time is not None, "RX timestamp error ")
        self.verify(tx_time is not None, "TX timestamp error ")
        self.verify(int(tx_time, 16) > int(rx_time, 16), "Timestamp mismatch")

    def test_ieee1588_disable(self):
        """
        IEEE1588 Disable test case.
        """

        self.dut.send_expect("stop", "testpmd> ")
        time.sleep(3)

        # use the first port on that self.nic
        dutPorts = self.dut.get_ports(self.nic)
        port = self.tester.get_local_port(dutPorts[0])
        itf = self.tester.get_interface(port)

        self.tester.scapy_background()
        self.tester.scapy_append('p = sniff(iface="%s", count=2, timeout=1)' % itf)
        self.tester.scapy_append('RESULT = p[1].summary()')

        self.tester.scapy_foreground()
        self.tester.scapy_append('nutmac="01:1b:19:00:00:00"')
        self.tester.scapy_append('sendp([Ether(dst=nutmac,type=0x88f7)/"\\x00\\x02"], iface="%s")' % itf)

        self.tester.scapy_execute()
        time.sleep(2)

        out = self.tester.scapy_get_result()
        self.verify("Ether" not in out, "Ether type is not PTP")

    def tear_down(self):
        """
        Run after each test case.
        """
        pass

    def tear_down_all(self):
        """
        Run after each test suite.
        """
        self.dut.send_expect("quit", "# ", 30)

        # Restore the config file and recompile the package.
        if "bsdapp" in self.target:
            self.dut.send_expect("sed -i -e 's/IEEE1588=y$/IEEE1588=n/' config/common_bsdapp", "# ", 30)
        else:
            self.dut.send_expect("sed -i -e 's/IEEE1588=y$/IEEE1588=n/' config/common_linuxapp", "# ", 30)
        self.dut.build_install_dpdk(self.target)
