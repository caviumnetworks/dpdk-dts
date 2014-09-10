import os
import re


class PmdOutput():

    """
    Module for get all statics value by port in testpmd
    """

    def __init__(self, dut):
        self.dut = dut
        self.rx_pkts_prefix = "RX-packets:"
        self.rx_missed_prefix = "RX-missed:"
        self.rx_bytes_prefix = "RX-bytes:"
        self.rx_badcrc_prefix = "RX-badcrc:"
        self.rx_badlen_prefix = "RX-badlen:"
        self.rx_error_prefix = "RX-errors:"
        self.rx_nombuf_prefix = "RX-nombuf:"
        self.tx_pkts_prefix = "TX-packets:"
        self.tx_error_prefix = "TX-errors:"
        self.tx_bytes_prefix = "TX-bytes:"

    def get_pmd_value(self, prefix, out):
        pattern = re.compile(prefix + "(\s+)([0-9]+)")
        m = pattern.search(out)
        if m is None:
            return None
        else:
            return int(m.group(2))

    def get_pmd_stats(self, portid):
        stats = {}
        out = self.dut.send_expect("show port stats %d" % portid, "testpmd> ")
        stats["RX-packets"] = self.get_pmd_value(self.rx_pkts_prefix, out)
        stats["RX-missed"] = self.get_pmd_value(self.rx_missed_prefix, out)
        stats["RX-bytes"] = self.get_pmd_value(self.rx_bytes_prefix, out)

        stats["RX-badcrc"] = self.get_pmd_value(self.rx_badcrc_prefix, out)
        stats["RX-badlen"] = self.get_pmd_value(self.rx_badlen_prefix, out)
        stats["RX-errors"] = self.get_pmd_value(self.rx_error_prefix, out)
        stats["RX-nombuf"] = self.get_pmd_value(self.rx_nombuf_prefix, out)
        stats["TX-packets"] = self.get_pmd_value(self.tx_pkts_prefix, out)
        stats["TX-errors"] = self.get_pmd_value(self.tx_error_prefix, out)
        stats["TX-bytes"] = self.get_pmd_value(self.tx_bytes_prefix, out)
        return stats
