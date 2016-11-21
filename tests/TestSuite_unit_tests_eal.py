# <COPYRIGHT_TAG>

"""
DPDK Test suite.

EAL autotest.

"""

import utils


from test_case import TestCase

#
#
# Test class.
#


class TestUnitTestsEal(TestCase):

    #
    #
    #
    # Test cases.
    #

    def set_up_all(self):
        """
        Run at the start of each test suite.
        """
        # icc compilation cost long long time.
        [arch, machine, self.env, toolchain] = self.target.split('-')
        self.start_test_time = 60
        self.run_cmd_time = 180
        self.test_app_cmdline = "./%s/app/test -n 1 -c f" % self.target

    def set_up(self):
        """
        Run before each test case.
        """
        pass

    def test_version(self):
        """
        Run version autotest.
        """

        self.dut.send_expect(self.dut.taskset(1) + ' ' + self.test_app_cmdline,
                             "R.*T.*E.*>.*>", self.start_test_time)
        out = self.dut.send_expect("version_autotest", "RTE>>", self.run_cmd_time)
        self.dut.send_expect("quit", "# ")
        self.verify("Test OK" in out, "Test failed")

    def test_memcopy(self):
        """
        Run memcopy autotest.
        """

        self.dut.send_expect(self.dut.taskset(1) + ' ' +  self.test_app_cmdline,
                             "R.*T.*E.*>.*>", self.start_test_time)
        out = self.dut.send_expect("memcpy_autotest", "RTE>>", self.run_cmd_time)
        self.dut.send_expect("quit", "# ")
        self.verify("Test OK" in out, "Test failed")

    def test_common(self):
        """
        Run common autotest.
        """

        self.dut.send_expect(self.dut.taskset(1) + ' ' + self.test_app_cmdline,
                             "R.*T.*E.*>.*>", self.start_test_time)
        out = self.dut.send_expect("common_autotest", "RTE>>", self.run_cmd_time)
        self.dut.send_expect("quit", "# ")
        self.verify("Test OK" in out, "Test failed")

    def test_eal_fs(self):
        """
        Run memcopy autotest.
        """

        self.dut.send_expect(self.dut.taskset(1) + ' ' + self.test_app_cmdline,
                             "R.*T.*E.*>.*>", self.start_test_time)
        out = self.dut.send_expect("eal_fs_autotest", "RTE>>", self.run_cmd_time)
        self.dut.send_expect("quit", "# ")
        self.verify("Test OK" in out, "Test failed")

    def test_memcpy(self):
        """
        Run memcopy autotest.
        """

        self.dut.send_expect(self.dut.taskset(1) + ' ' + self.test_app_cmdline,
                             "R.*T.*E.*>.*>", self.start_test_time)
        out = self.dut.send_expect("memcpy_autotest", "RTE>>", self.run_cmd_time)
        self.dut.send_expect("quit", "# ")
        self.verify("Test OK" in out, "Test failed")

    def test_memcpy_perf(self):
        """
        Run memcopy performance autotest.
        """
        self.dut.send_expect(self.dut.taskset(1) + ' ' + self.test_app_cmdline,
                             "R.*T.*E.*>.*>", self.start_test_time)
        out = self.dut.send_expect("memcpy_perf_autotest", "RTE>>", self.run_cmd_time * 15)
        self.dut.send_expect("quit", "# ")
        self.verify("Test OK" in out, "Test failed")

    def test_hash(self):
        """
        Run hash autotest.
        """

        self.dut.send_expect(self.test_app_cmdline, "R.*T.*E.*>.*>", self.start_test_time)
        out = self.dut.send_expect("hash_autotest", "RTE>>", self.run_cmd_time)
        self.dut.send_expect("quit", "# ")
        self.verify("Test OK" in out, "Test failed")

    def test_hash_perf(self):
        """
        Run has performance autotest.
        """

        self.dut.send_expect(self.test_app_cmdline,
                             "R.*T.*E.*>.*>", self.start_test_time)
        out = self.dut.send_expect("hash_perf_autotest", "RTE>>", self.run_cmd_time * 10)
        self.dut.send_expect("quit", "# ")
        self.verify("Test OK" in out, "Test failed")

    def test_malloc(self):
        """
        Run malloc autotest.
        """

        self.dut.send_expect(self.test_app_cmdline, "R.*T.*E.*>.*>", self.start_test_time)
        out = self.dut.send_expect("malloc_autotest", "RTE>>", self.run_cmd_time)
        self.dut.send_expect("quit", "# ")
        self.verify("Test OK" in out, "Test failed")

    def test_func_reentrancy(self):
        """
        Run function reentrancy autotest.
        """

        if self.dut.architecture == "x86_64":
            cmdline = self.test_app_cmdline
        else:
            # mask cores only on socket 0
            cmdline = "%s ./%s/app/test -n 1 -c 5" % (self.dut.taskset(1), self.target)
        self.dut.send_expect(cmdline, "R.*T.*E.*>.*>", self.start_test_time)
        out = self.dut.send_expect("func_reentrancy_autotest", "RTE>>", self.run_cmd_time)
        self.dut.send_expect("quit", "# ")
        self.verify("Test OK" in out, "Test failed")

    def test_pci(self):
        """
        Run pci autotest.
        """
        # should re-compile test app, this is only a demo. will implementation after framework support
        self.dut.send_expect("./%s/app/test_pci -n 1 -c f" % self.target, "R.*T.*E.*>.*>" , self.start_test_time)
        out = self.dut.send_expect("pci_autotest", "RTE>>", self.run_cmd_time)
        self.dut.send_expect("quit", "# ")
        self.verify("Test OK" in out, "Test failed")

    def test_atomic(self):
        """
        Run atomic autotest.
        """

        self.dut.send_expect(self.test_app_cmdline, "R.*T.*E.*>.*>", self.start_test_time)
        out = self.dut.send_expect("atomic_autotest", "RTE>>", self.run_cmd_time)
        self.dut.send_expect("quit", "# ")
        self.verify("Test OK" in out, "Test failed")

    def test_memory(self):
        """
        Run memory autotest.
        """

        self.dut.send_expect(self.test_app_cmdline, "R.*T.*E.*>.*>", self.start_test_time)
        out = self.dut.send_expect('memory_autotest', "RTE>>", self.run_cmd_time * 5)
        regexp = "phys:0x[0-9a-f]*, len:([0-9a-f]*), virt:0x[0-9a-f]*, socket_id:[0-9]*"
        match = utils.regexp(out, regexp)
        size = int(match, 16)
        self.verify(size > 0, "bad size")
        self.dut.send_expect("quit", "# ")

    def test_lcore_launch(self):
        """
        Run lcore autotest.
        """

        self.dut.send_expect(self.test_app_cmdline, "R.*T.*E.*>.*>", self.start_test_time)
        out = self.dut.send_expect("per_lcore_autotest", "RTE>>", self.run_cmd_time)
        self.dut.send_expect("quit", "# ")
        self.verify("Test OK" in out, "Test failed")

    def test_spinlock(self):
        """
        Run spinlock autotest.
        """

        self.dut.send_expect(self.test_app_cmdline, "R.*T.*E.*>.*>", self.start_test_time)
        out = self.dut.send_expect("spinlock_autotest", "RTE>>", self.run_cmd_time * 2)
        self.dut.send_expect("quit", "# ")
        self.verify("Test OK" in out, "Test failed")

    def test_rwlock(self):
        """
        Run rwlock autotest.
        """

        self.dut.send_expect(self.test_app_cmdline, "R.*T.*E.*>.*>", self.start_test_time)
        out = self.dut.send_expect("rwlock_autotest", "RTE>>", self.run_cmd_time)
        self.dut.send_expect("quit", "# ")
        self.verify("Test OK" in out, "Test failed")

    def test_prefetch(self):
        """
        Run prefetch autotest.
        """

        self.dut.send_expect(self.test_app_cmdline, "R.*T.*E.*>.*>", self.start_test_time)
        out = self.dut.send_expect("prefetch_autotest", "RTE>>", self.run_cmd_time)
        self.dut.send_expect("quit", "# ")
        self.verify("Test OK" in out, "Test failed")

    def test_byteorder(self):
        """
        Run byte order autotest.
        """

        self.dut.send_expect(self.test_app_cmdline, "R.*T.*E.*>.*>", self.start_test_time)
        out = self.dut.send_expect("byteorder_autotest", "RTE>>", self.run_cmd_time)
        self.dut.send_expect("quit", "# ")
        self.verify("Test OK" in out, "Test failed")

    def test_cycles(self):
        """
        Run cycles autotest.
        """

        self.dut.send_expect(self.test_app_cmdline, "R.*T.*E.*>.*>", self.start_test_time)
        out = self.dut.send_expect("cycles_autotest", "RTE>>", self.run_cmd_time)
        self.dut.send_expect("quit", "# ")
        self.verify("Test OK" in out, "Test failed")

    def test_logs(self):
        """
        Run logs autotest.
        """

        self.dut.send_expect(self.test_app_cmdline, "R.*T.*E.*>.*>", self.start_test_time)
        out = self.dut.send_expect("logs_autotest", "RTE>>", self.run_cmd_time)
        self.dut.send_expect("quit", "# ")
        self.verify("Test OK" in out, "Test failed")

    def test_memzone(self):
        """
        Run memzone autotest.
        """

        self.dut.send_expect(self.test_app_cmdline, "R.*T.*E.*>.*>", self.start_test_time)
        out = self.dut.send_expect("memzone_autotest", "RTE>>", self.run_cmd_time)
        self.dut.send_expect("quit", "# ")
        self.verify("Test OK" in out, "Test failed")

    def test_debug(self):
        """
        Run debug autotest.
        """

        self.dut.send_expect(self.test_app_cmdline, "R.*T.*E.*>.*>", self.start_test_time)
        out = self.dut.send_expect("debug_autotest", "RTE>>", self.run_cmd_time)
        self.dut.send_expect("quit", "# ")
        self.verify("Test OK" in out, "Test failed")

    def test_flags(self):
        """
        Run eal flags autotest.
        """

        self.dut.send_expect(self.test_app_cmdline + ' -m 64', "R.*T.*E.*>.*>", self.start_test_time)
        out = self.dut.send_expect("eal_flags_autotest", "RTE>>", self.run_cmd_time)
        self.dut.send_expect("quit", "# ")
        self.verify("Test OK" in out, "Test failed")

    def test_alarm(self):
        """
        Run alarm autotest.
        """

        self.verify(self.env == "linuxapp", "Alarm only supported in linux env")
        self.dut.send_expect(self.test_app_cmdline, "R.*T.*E.*>.*>", self.start_test_time)
        out = self.dut.send_expect("alarm_autotest", "RTE>>", self.run_cmd_time)
        self.dut.send_expect("quit", "# ")
        self.verify("Test OK" in out, "Test failed")

    def test_cpuflags(self):
        """
        Run CPU flags autotest.
        """

        self.dut.send_expect(self.test_app_cmdline, "R.*T.*E.*>.*>", self.start_test_time)
        out = self.dut.send_expect("cpuflags_autotest", "RTE>>", self.run_cmd_time)
        self.dut.send_expect("quit", "# ")
        self.verify("Test OK" in out, "Test failed")

    def test_errno(self):
        """
        Run errno autotest.
        """

        self.dut.send_expect(self.test_app_cmdline, "R.*TE>>|RT.*E>>|RTE.*>>|RTE>.*>", self.start_test_time)
        out = self.dut.send_expect("errno_autotest", "RTE>>", self.run_cmd_time)
        self.dut.send_expect("quit", "# ")
        self.verify("Test OK" in out, "Test failed")

    def test_interrupts(self):
        """
        Run interrupt autotest.
        """

        self.verify(self.env == "linuxapp", "Interrupt only supported in linux env")
        self.dut.send_expect(self.test_app_cmdline, "R.*TE>>|RT.*E>>|RTE.*>>|RTE>.*>", self.start_test_time)
        out = self.dut.send_expect("interrupt_autotest", "RTE>>", self.run_cmd_time)
        self.dut.send_expect("quit", "# ")
        self.verify("Test OK" in out, "Test failed")

    def test_multiprocess(self):
        """
        Run multiprocess autotest.
        """

        self.dut.send_expect(self.test_app_cmdline + ' -m 64', "R.*T.*E.*>.*>", self.start_test_time)
        out = self.dut.send_expect("multiprocess_autotest", "RTE>>", self.run_cmd_time)
        self.dut.send_expect("quit", "# ")
        self.verify("Test OK" in out, "Test failed")

    def test_string(self):
        """
        Run string autotest.
        """

        self.dut.send_expect(self.test_app_cmdline, "R.*T.*E.*>.*>", self.start_test_time)
        out = self.dut.send_expect("string_autotest", "RTE>>", self.run_cmd_time)
        self.dut.send_expect("quit", "# ")
        self.verify("Test OK" in out, "Test failed")

    def test_tailq(self):
        """
        Run tailq autotest.
        """

        self.dut.send_expect(self.test_app_cmdline, "R.*T.*E.*>.*>", self.start_test_time)
        out = self.dut.send_expect("tailq_autotest", "RTE>>", self.run_cmd_time)
        self.dut.send_expect("quit", "# ")
        self.verify("Test OK" in out, "Test failed")

    def test_devargs(self):
        """
        Run devargs autotest.
        """

        self.dut.send_expect(self.test_app_cmdline, "R.*T.*E.*>.*>", self.start_test_time)
        out = self.dut.send_expect("devargs_autotest", "RTE>>", self.run_cmd_time)
        self.dut.send_expect("quit", "# ")
        self.verify("Test OK" in out, "Test failed")

    def test_kvargs(self):
        """
        Run kvargs autotest.
        """

        self.dut.send_expect(self.test_app_cmdline, "R.*T.*E.*>.*>", self.start_test_time)
        out = self.dut.send_expect("kvargs_autotest", "RTE>>", self.run_cmd_time)
        self.dut.send_expect("quit", "# ")
        self.verify("Test OK" in out, "Test failed")

    def test_acl(self):
        """
        Run acl autotest.
        """

        self.dut.send_expect(self.test_app_cmdline, "R.*T.*E.*>.*>", self.start_test_time)
        out = self.dut.send_expect("acl_autotest", "RTE>>", self.run_cmd_time)
        self.dut.send_expect("quit", "# ")
        self.verify("Test OK" in out, "Test failed")

    def test_link_bonding(self):
        """
        Run acl autotest.
        """

        self.dut.send_expect(self.test_app_cmdline, "R.*T.*E.*>.*>", self.start_test_time)
        out = self.dut.send_expect("link_bonding_autotest", "RTE>>", self.run_cmd_time)
        self.dut.send_expect("quit", "# ")
        self.verify("Test OK" in out, "Test failed")

    def test_link_bonding_rssconf(self):
        """
        """
        self.dut.send_expect(self.test_app_cmdline, "R.*T.*E.*>.*>", self.start_test_time)
        out = self.dut.send_expect("link_bonding_rssconf_autotest", "RTE>>", self.run_cmd_time)
        self.dut.send_expect("quit", "# ")
        self.verify("Test OK" in out, "Test failed")

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
