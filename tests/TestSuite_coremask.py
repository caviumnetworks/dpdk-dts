# <COPYRIGHT_TAG>

"""
DPDK Test suite.

Test coremask parsing in DPDK.

"""

import utils

from exception import VerifyFailure
from test_case import TestCase

#
#
# Test class.
#

command_line = """./%s/app/test -c %s -n %d --log-level 8"""


class TestCoremask(TestCase):

    #
    #
    #
    # Test cases.
    #

    def set_up_all(self):
        """
        Run at the start of each test suite.

        Coremask Prerequisites.
        """

        self.port_mask = utils.create_mask(self.dut.get_ports(self.nic))
        self.mem_channel = self.dut.get_memory_channels()

        self.all_cores = self.dut.get_core_list("all")
        self.dut.send_expect("sed -i -e 's/CONFIG_RTE_LOG_LEVEL=.*$/"
                          + "CONFIG_RTE_LOG_LEVEL=RTE_LOG_DEBUG/' config/common_base", "# ", 30)

        self.dut.skip_setup = False
        self.dut.build_install_dpdk(self.target)

    def set_up(self):
        """
        Run before each test case.
        """
        pass

    def test_individual_coremask(self):
        """
        Check coremask parsing for all the available cores one by one.
        """

        for core in self.all_cores:

            core_mask = utils.create_mask([core])

            command = command_line % (self.target, core_mask,
                                      self.mem_channel)

            out = self.dut.send_expect(command, "RTE>>", 10)

            self.verify("EAL: Detected lcore %s as core" % core in out,
                        "Core %s not detected" % core)

            self.verify("EAL: Master lcore %s is ready" % core in out,
                        "Core %s not ready" % core)

            self.dut.send_expect("quit", "# ", 10)

    def test_all_cores_coremask(self):
        """
        Check coremask parsing for all the cores at once.
        """

        core_mask = utils.create_mask(self.all_cores)

        command = command_line % (self.target, core_mask, self.mem_channel)

        out = self.dut.send_expect(command, "RTE>>", 10)

        self.verify("EAL: Master lcore 1 is ready" in out,
                    "Core 1 not ready")

        self.verify("EAL: Detected lcore 1 as core" in out,
                    "Core 1 not detected")

        for core in self.all_cores[1:]:
            self.verify("EAL: lcore %s is ready" % core in out,
                        "Core %s not ready" % core)

            self.verify("EAL: Detected lcore %s as core" % core in out,
                        "Core %s not detected" % core)

        self.dut.send_expect("quit", "# ", 10)

    def test_big_coremask(self):
        """
        Check coremask parsing for more cores than available.
        """

        command_line = """./%s/app/test -c %s -n %d --log-level 8 2>&1 |tee out"""

        # Default big coremask value 128
        big_coremask_size = 128

        try:
            out = self.dut.send_expect("cat config/defconfig_%s" % self.target, "]# ", 10)
            start_position = out.find('CONFIG_RTE_MAX_LCORE=')

            if start_position > -1:
                end_position = out.find('\n', start_position)
                big_coremask_size = int(out[start_position + 21:end_position])

                print "Detected CONFIG_RTE_MAX_LCORE=%d" % big_coremask_size
        except:
            print "Using default big coremask %d" % big_coremask_size

        # Create a extremely big coremask
        big_coremask = "0x"
        for _ in range(0, big_coremask_size, 4):
            big_coremask += "F"

        command = command_line % (self.target, big_coremask, self.mem_channel)
        try:
            self.dut.send_expect(command, "RTE>>", 10)
        except:
            out = self.dut.send_expect("cat out", "# ")

            self.verify("EAL: invalid coremask" in out,
                    "Small core mask set")

        self.verify("EAL: Detected lcore 0 as core" in out,
                    "Core 0 not detected")

        for core in self.all_cores[1:]:

            self.verify("EAL: Detected lcore %s as core" % core in out,
                        "Core %s not detected" % core)

        self.dut.send_expect("quit", "# ", 10)

    def test_wrong_coremask(self):
        """
        Check coremask parsing for wrong coremasks.
        """

        wrong_coremasks = ["GARBAGE", "0xJF", "0xFJF", "0xFFJ",
                           "0xJ11", "0x1J1", "0x11J",
                           "JF", "FJF", "FFJ",
                           "J11", "1J1", "11J",
                           "jf", "fjf", "ffj",
                           "FF0x", "ff0x", "", "0x", "0"]

        for coremask in wrong_coremasks:

            command = command_line % (self.target, coremask, self.mem_channel)
            try:
                out = self.dut.send_expect(command, "# ", 5)
                self.verify("EAL: invalid coremask" in out,
                            "Wrong core mask (%s) accepted" % coremask)
            except:
                self.dut.send_expect("quit", "# ", 5)
                raise VerifyFailure("Wrong core mask (%s) accepted" % coremask)

    def tear_down(self):
        """
        Run after each test case.
        """
        self.dut.kill_all()

    def tear_down_all(self):
        """
        Run after each test suite.
        """
        self.dut.send_expect("sed -i -e 's/CONFIG_RTE_LOG_LEVEL=.*$/"
                          + "CONFIG_RTE_LOG_LEVEL=RTE_LOG_INFO/' config/common_base", "# ", 30)

        #self.dut.skip_setup = False
        self.dut.build_install_dpdk(self.target)
