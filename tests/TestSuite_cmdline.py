# <COPYRIGHT_TAG>

"""
DPDK Test suite.

Test cmdline.

"""

import dcts


from test_case import TestCase

#
#
# Test class.
#


class TestCmdline(TestCase):

    #
    #
    #
    # Test cases.
    #

    def set_up_all(self):
        """
        Run at the start of each test suite.

        Cmdline Prerequisites:
            cmdline build pass
            At least one core in DUT
        """
        out = self.dut.build_dpdk_apps('examples/cmdline')
        self.verify('make: Leaving directory' in out, "Compilation failed")
        self.verify("Error" not in out, "compilation error 1")
        self.verify("No such file" not in out, "compilation error 2")

        # Run cmdline app
        cores = self.dut.get_core_list('1S/1C/1T')
        coreMask = dcts.create_mask(cores)
        self.dut.send_expect("./examples/cmdline/build/app/cmdline -n 1 -c " + coreMask, "> ", 5)

    def set_up(self):
        """
        Run before each test case.
        Nothing to do.
        """
        pass

    def test_cmdline_sample_commands(self):
        """
        Sample commands test.
        """

        # add a test object with an IP address associated
        out = self.dut.send_expect("add objtest 192.168.0.1", "example> ")
        self.verify("Object objtest added, ip=192.168.0.1" in out, "add command error")

        # verify the object existance
        out = self.dut.send_expect("add objtest 192.168.0.1", "example> ")
        self.verify("Object objtest already exist" in out, "double add command error")

        # show the object result by 'show' command
        out = self.dut.send_expect("show objtest", "example> ")
        self.verify("Object objtest, ip=192.168.0.1" in out, "show command error")

        # delete the object in cmdline
        out = self.dut.send_expect("del objtest", "example> ")
        self.verify("Object objtest removed, ip=192.168.0.1" in out, "del command error")

        # double delete the object to verify the correctness
        out = self.dut.send_expect("del objtest", "example> ", 1)
        self.verify("Bad arguments" in out, "double del command error")

        # verify no such object anymore
        out = self.dut.send_expect("show objtest", "example> ", 1)
        self.verify("Bad arguments" in out, "final show command error")

        # verify the help command
        out = self.dut.send_expect("help", "example> ", 1)

        """
        Demo example of command line interface in RTE

        This is a readline-like interface that can be used to
        debug your RTE application. It supports some features
        of GNU readline like completion, cut/paste, and some
        other special bindings.

        This demo shows how rte_cmdline library can be
        extended to handle a list of objects. There are
        3 commands:
        - add obj_name IP
        - del obj_name
        - show obj_name
        """
        self.verify(" " in out, "help command error")

        out = self.dut.send_expect("?", "example> ", 1)
        """
        show [Mul-choice STRING]: Show/del an object
        del [Mul-choice STRING]: Show/del an object
        add [Fixed STRING]: Add an object (name, val)
        help [Fixed STRING]: show help
        """
        self.verify(" " in out, "? command error")

    def tear_down(self):
        """
        Run after each test case.
        Nothing to do.
        """
        pass

    def tear_down_all(self):
        """
        Run after each test suite.
        Stop cmdline app.
        """
        self.dut.kill_all()
