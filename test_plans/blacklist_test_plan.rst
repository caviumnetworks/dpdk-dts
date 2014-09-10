.. Copyright (c) <2010,2011>, Intel Corporation
   All rights reserved.
   
   Redistribution and use in source and binary forms, with or without
   modification, are permitted provided that the following conditions
   are met:
   
   - Redistributions of source code must retain the above copyright
     notice, this list of conditions and the following disclaimer.
   
   - Redistributions in binary form must reproduce the above copyright
     notice, this list of conditions and the following disclaimer in
     the documentation and/or other materials provided with the
     distribution.
   
   - Neither the name of Intel Corporation nor the names of its
     contributors may be used to endorse or promote products derived
     from this software without specific prior written permission.
   
   THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
   "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
   LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
   FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
   COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
   INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
   (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
   SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
   HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
   STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
   ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED
   OF THE POSSIBILITY OF SUCH DAMAGE.

=========================
Support of port blacklist
=========================

Prerequisites
=============

Board with at least 2 DPDK supported NICs attached.

Support igb_uio and vfio driver, if used vfio, kernel need 3.6+ and enable vt-d in bios.
When used vfio , used "modprobe vfio" and "modprobe vfio-pci" insmod vfiod driver, then used
"./tools/dpdk_nic_bind.py --bind=vfio-pci device_bus_id" to bind vfio driver to test driver.

Test Case: Testpmd with no blacklisted device
=============================================

Run testpmd in interactive mode and ensure that at least 2 ports
are binded and available::

  build/testpmd -c 3 -- -i
  ....
  EAL: unbind kernel driver /sys/bus/pci/devices/0000:01:00.0/driver/unbind
  EAL: Core 1 is ready (tid=357fc700)
  EAL: bind PCI device 0000:01:00.0 to uio driver
  EAL: Device bound
  EAL: map PCI resource for device 0000:01:00.0
  EAL: PCI memory mapped at 0x7fe6b68c7000
  EAL: probe driver: 8086:10fb rte_niantic_pmd
  EAL: unbind kernel driver /sys/bus/pci/devices/0000:01:00.1/driver/unbind
  EAL: bind PCI device 0000:01:00.1 to uio driver
  EAL: Device bound
  EAL: map PCI resource for device 0000:01:00.1
  EAL: PCI memory mapped at 0x7fe6b6847000
  EAL: probe driver: 8086:10fb rte_niantic_pmd
  EAL: unbind kernel driver /sys/bus/pci/devices/0000:02:00.0/driver/unbind
  EAL: bind PCI device 0000:02:00.0 to uio driver
  EAL: Device bound
  EAL: map PCI resource for device 0000:02:00.0
  EAL: PCI memory mapped at 0x7fe6b6580000
  EAL: probe driver: 8086:10fb rte_niantic_pmd
  EAL: unbind kernel driver /sys/bus/pci/devices/0000:02:00.1/driver/unbind
  EAL: bind PCI device 0000:02:00.1 to uio driver
  EAL: Device bound
  EAL: map PCI resource for device 0000:02:00.1
  EAL: PCI memory mapped at 0x7fe6b6500000
  Interactive-mode selected
  Initializing port 0... done:  Link Up - speed 10000 Mbps - full-duplex
  Initializing port 1... done:  Link Up - speed 10000 Mbps - full-duplex
  Initializing port 2... done:  Link Up - speed 10000 Mbps - full-duplex
  Initializing port 3... done:  Link Up - speed 10000 Mbps - full-duplex


Test Case: Testpmd with one port blacklisted
============================================

Select first available port to be blacklisted and specify it with -b option. For the example above::

  build/testpmd -c 3 -b 0000:01:00.0 -- -i

Check that corresponding device is skipped for binding, and
only 3 ports are available now:::

  EAL: probe driver: 8086:10fb rte_niantic_pmd
  EAL: unbind kernel driver /sys/bus/pci/devices/0000:01:00.1/driver/unbind
  EAL: bind PCI device 0000:01:00.1 to uio driver
  EAL: Device bound
  EAL: map PCI resource for device 0000:01:00.1
  EAL: PCI memory mapped at 0x7f0037912000
  EAL: probe driver: 8086:10fb rte_niantic_pmd
  EAL: unbind kernel driver /sys/bus/pci/devices/0000:02:00.0/driver/unbind
  EAL: bind PCI device 0000:02:00.0 to uio driver
  EAL: Device bound
  EAL: map PCI resource for device 0000:02:00.0
  EAL: PCI memory mapped at 0x7f0037892000
  EAL: probe driver: 8086:10fb rte_niantic_pmd
  EAL: unbind kernel driver /sys/bus/pci/devices/0000:02:00.1/driver/unbind
  EAL: bind PCI device 0000:02:00.1 to uio driver
  EAL: Device bound
  EAL: map PCI resource for device 0000:02:00.1
  EAL: PCI memory mapped at 0x7f0037812000
  Interactive-mode selected
  Initializing port 0... done:  Link Up - speed 10000 Mbps - full-duplex
  Initializing port 1... done:  Link Up - speed 10000 Mbps - full-duplex
  Initializing port 2... done:  Link Up - speed 10000 Mbps - full-duplex


Test Case: Testpmd with all but one port blacklisted
====================================================

Blacklist all devices except the last one.
For the example above:::

  build/testpmd -c 3 -b 0000:01:00.0  -b 0000:01:00.0 -b 0000:02:00.0 -- -i

Check that 3 corresponding device is skipped for binding, and
only 1 ports is available now:::

  EAL: probe driver: 8086:10fb rte_niantic_pmd
  EAL: unbind kernel driver /sys/bus/pci/devices/0000:02:00.1/driver/unbind
  EAL: bind PCI device 0000:02:00.1 to uio driver
  EAL: Device bound
  EAL: map PCI resource for device 0000:02:00.1
  EAL: PCI memory mapped at 0x7f22e9aeb000
  Interactive-mode selected
  Initializing port 0... done:  Link Up - speed 10000 Mbps - full-duplex

