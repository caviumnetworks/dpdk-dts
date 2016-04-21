#!/usr/bin/env python
## This file is part of Scapy
## See http://www.secdev.org/projects/scapy for more informations
## Copyright (C) Philippe Biondi <phil@secdev.org>
## This program is published under a GPLv2 license

## Copyright (c) 2016 Marvin liu <yong.liu@intel.com>

"""
VBPE (virtual brige port extenstion)
"""

from scapy.packet import *
from scapy.fields import *
from scapy.layers.l2 import Ether

class Dot1BR(Packet):
    name = "802.1BR"
    aliastypes = [ Ether ]
    fields_desc =  [ 
                     BitField("EPCP", 0, 3),
                     BitField("EEDI", 0, 1),
                     BitField("IngressECIDbase", 0, 12),
                     BitField("Reserverd", 0, 2),
                     BitField("GRP", 0, 2),
                     BitField("ECIDbase", 0, 12),
                     BitField("IngressECIDext", 0, 8),
                     BitField("ECIDext", 0, 8),
                     XShortEnumField("type", 0x0000, ETHER_TYPES) ]
    def mysummary(self):
        return self.sprintf("802.1BR E-CID %Ingress_E-CID_base%")

bind_layers(Ether, Dot1BR, type=0x893F)
