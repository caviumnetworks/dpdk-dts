# <COPYRIGHT_TAG>

"""
A base class for creating DTF test cases.
"""

from exception import VerifyFailure
from settings import DRIVERS


class TestCase(object):

    def __init__(self, dut, tester, target, nic):
        self.dut = dut
        self.tester = tester
        self.target = target
        self.nic = nic

    def set_up_all(self):
        pass

    def set_up(self):
        pass

    def tear_down(self):
        pass

    def tear_down_all(self):
        pass

    def verify(self, passed, description):
        if not passed:
            raise VerifyFailure(description)

    def get_nic_driver(self, nic_name):
        if nic_name in DRIVERS.keys():
            return DRIVERS[nic_name]

        raise ValueError(nic_name)

    def wirespeed(self, nic, frame_size, num_ports):
        """
        Calculate bit rate. It is depended for NICs
        """
        bitrate = 1000.0  # 1Gb ('.0' forces to operate as float)
        if self.get_nic_driver(self.nic) == "ixgbe":
            bitrate *= 10  # 10 Gb NICs
        elif self.nic == "avoton2c5":
            bitrate *= 2.5  # 2.5 Gb NICs

        return bitrate * num_ports / 8 / (frame_size + 20)
