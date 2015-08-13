## This file is part of Scapy
## 
## Copyright (C) Min Cao <min.cao@intel.com>

"""
NVGRE (Network Virtual GRE).
"""

from scapy.packet import *
from scapy.fields import *
from scapy.layers.inet import UDP,IP
from scapy.layers.l2 import Ether

IPPROTO_NVGRE=47

class NVGRE(Packet):
    name = "Network Virtual GRE"
    fields_desc = [BitField("c", 0, 1),
                   BitField("r", 0, 1),
                   BitField("k", 1, 1),
                   BitField("s", 0, 1),
                   BitField("reserved0", 0, 9),
                   BitField("ver", 0, 3),
                   XShortField("protocoltype", 0x6558),
                   X3BytesField("TNI", 1),
                   ByteField("reserved1", 0)]
    def mysummary(self):          
        return self.sprintf("NVGRE (tni=%NVGRE.tni%)") 


bind_layers(IP, NVGRE, proto=IPPROTO_NVGRE)
bind_layers(NVGRE, Ether)

