'''
Created on Jul 29, 2014

@author: yliu86
'''
from scapy.packet import *
from scapy.fields import *
from scapy.layers.inet import UDP, IP
from scapy.layers.dns import DNS
from scapy.layers.l2 import Ether

vxlanmagic = "0x8"


class Vxlan(Packet):
    name = "Virtual eXtensible Local Area Network"
    fields_desc = [ByteField("flag", 8),
                   X3BytesField("reserved1", 0),
                   X3BytesField("vni", 0),
                   ByteField("reserved2", 0)]

    def guess_payload_class(self, payload):
        if self.flag == vxlanmagic:
            return Vxlan
        else:
            return Packet.guess_payload_class(self, payload)

    def mysummary(self):
        return self.sprintf("VXLAN (vni=%VXLAN.vni%)")

split_layers(UDP, DNS, sport=53)
bind_layers(UDP, Vxlan, dport=4789)
bind_layers(Vxlan, Ether)
