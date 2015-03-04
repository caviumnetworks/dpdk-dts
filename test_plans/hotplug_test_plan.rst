.. Copyright (c) <2015>, Intel Corporation
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

======================================
DPDK Hotplug API Feature Tests
======================================

This test for Hotplug API feature can be run on linux userspace. It
will check if NIC port can be attached and detached without exiting the
application process. Furthermore, it will check if it can reconfigure
new configurations for a port after the port is stopped, and if it is
able to restart with those new configurations. It is based on testpmd
application.

The test is performed by running the testpmd application and using a
traffic generator. Port configurations can be set interactively,
and still be set at the command line when launching the application in
order to be compatible with previous test framework.

Prerequisites
-------------
Assume DPDK managed at least one device for physical or none for virtual.
This feature only supports igb_uio now, for uio_pci_generic is
on the way, will test it after enabled.

To run the testpmd application in linuxapp environment with 4 lcores,
4 channels with other default parameters in interactive mode.

        $ ./testpmd -c 0xf -n 4 -- -i

Test ENV:

All test cases can be run in 32bit and 64bit platform.

OS support: Fedora, Ubuntu, RHEL, SUSE, but freebsd will not be
included as hotplug has no plan to support that platform

All kernel version(from 2.6) can be support, for vfio need kernel
        version greater than 3.6.

Virtualization support: KVM/VMware/Xen, container is in the roadmap

-------------------------------------------------------------------------------
Test Case 1: port detach & attach for physical devices with igb_uio
-------------------------------------------------------------------------------

1. Start testpmd
    $ ./testpmd -c 0xf -n 4 -- -i

2. Bind new physical port to igb_uio(assume BDF 0000:02:00.0)
    # ./tools/dpdk_nic_bind -b igb_uio 0000:02:00.0


3. Attach port 0
    run "port attach 0000:02:00.0"

    run "port start 0"

    run "show port info 0", check port 0 info display.

4. Check package forwarding when startup

    run "start", then "show port stats 0" check forwarding packages start.

    run "port detach 0", check the error message of port not stopped.

    run "stop", then "show port stats 0", check forwarding packages stopped.

5. Detach port 0 after port closed
    run "port stop 0"

    run "port close 0".

    run "port detach 0", check port detached successful.

6. Re-attach port 0(assume BDF 0000:02:00.0)
    run "port attach 0000:02:00.0",

    run "port start 0".

    run "show port info 0", check port 0 info display.

7. Check package forwarding after re-attach
    run "start", then "show port stats 0" check forwarding packages start.

    run "port detach 0", check the error message of port not stopped.

    run "stop", then "show port stats 0", check forwarding packages stopped.

-------------------------------------------------------------------------------
Test Case 2: port dettach & attach for physical devices with vfio
-------------------------------------------------------------------------------

1. Start testpmd
    $ ./testpmd -c 0xf -n 4 -- -i

2. Bind new physical port to igb_uio(assume BDF 0000:02:00.0)
    # ./tools/dpdk_nic_bind -b vfio-pci 0000:02:00.0

3. Attach port 0(assume BDF 0000:02:00.0)
    run "port attach 0000:02:00.0"

    run "port start 0"

    run "show port info 0", check port 0 info display.

4. Detach port 0 after port closed
    run "port stop 0", then "show port stats 0", check port stopped.

    run "port close 0".

    run "port detach 0", check detach status(should fail as no detach
                         support at the moment for vfio).

-------------------------------------------------------------------------------
Test Case 3: port detach & attach for physical devices with uio_pci_generic
             This case should be enabled after uio_pci_generic enabled for DPDK
-------------------------------------------------------------------------------

1. Start testpmd
    $ ./testpmd -c 0xf -n 4 -- -i

2. Bind new physical port to igb_uio(assume BDF 0000:02:00.0)
    # ./tools/dpdk_nic_bind -b uio_pci_generic 0000:02:00.0

3. Attach port 0(assume BDF 0000:02:00.0)
    run "port attach 0000:02:00.0"

    run "port start 0"

    run "show port info 0", check port 0 info display.

4. Check package forwarding when startup

    run "start", then "show port stats 0" check forwarding packages start.

    run "port detach 0", check the error message of port not stopped.

    run "stop", then "show port stats 0", check forwarding packages stopped.

5. Detach port 0 after port closed
    run "port stop 0"

    run "port close 0".

    run "port detach 0", check port detached successful.

6. Re-attach port 0(assume BDF is 0000:02:00.0)
    run "port attach 0000:02:00.0",

    run "port start 0".

    run "show port info 0", check port 0 info display.

7. Check package forwarding after re-attach
    run "start", then "show port stats 0" check forwarding packages start.

    run "port detach 0", check the error message of not stopped.

    run "stop", then "show port stats 0", check forwarding packages stopped.

-------------------------------------------------------------------------------
Test Case 4: port detach & attach for physical devices with igb_uio
             Bind driver before testpmd started, port will start automatically
-------------------------------------------------------------------------------

1. Bind new physical port to igb_uio(assume BDF 0000:02:00.0)
    # ./tools/dpdk_nic_bind -b uio_pci_generic 0000:02:00.0

2. Start testpmd
    $ ./testpmd -c 0xf -n 4 -- -i

3. Check package forwarding when startup

    run "start", then "show port stats 0" check forwarding packages start.

    run "port detach 0", check the error message of port not stopped.

    run "stop", then "show port stats 0", check forwarding packages stopped.

4. Detach port 0 after port closed
    run "port stop 0"

    run "port close 0".

    run "port detach 0", check port detached successful.

5. Re-attach port 0(assume BDF 0000:02:00.0)
    run "port attach 0000:02:00.0",

    run "port start 0".

    run "show port info 0", check port 0 info display.

6. Check package forwarding after re-attach
    run "start", then "show port stats 0" check forwarding packages start.

    run "port detach 0", check the error message of port not stopped.

    run "stop", then "show port stats 0", check forwarding packages stopped.

-------------------------------------------------------------------------------
Test Case 5: port detach & attach for virtual devices
-------------------------------------------------------------------------------

1. Start testpmd
    $ ./testpmd -c 0xf -n 4 -- -i

2. Attach virtual device as port 0
    run "port attach eth_pcap0,iface=xxxx", where "xxxx" is one workable ifname.

    run "port start 0".

    run "show port info 0", check port 0 info display correctly.

3. Check package forwarding after port start

    run "start", then "show port stats 0" check forwarding packages start.

    run "port detach 0", check the error message of port not stopped.

    run "stop", then "show port stats 0", check forwarding packages stopped.

4. Detach port 0 after port closed

    run "port stop 0".

    run "port close 0".

    run "port detach 0", check port detached successful.

5. Re-attach port 0

    run "port attach eth_pcap0,iface=xxxx", where "xxxx" is one workable ifname.

    run "port start 0".

    run "show port info 0", check port 0 info display correctly.

6. Check package forwarding after port start

    run "start", then "show port stats 0" check forwarding packages start.

    run "port detach 0", check the error message of port not stopped.

    run "stop", then "show port stats 0", check forwarding packages stopped.

-------------------------------------------------------------------------------
Test Case 6: port detach & attach for virtual devices, with "--vdev"
-------------------------------------------------------------------------------

1. Start testpmd, ""xxxx" is one workable ifname
    $ ./testpmd -c 0xf -n 4 --vdev "eth_pcap0,iface=xxxx" -- -i

2. Check package forwarding after port start

    run "start", then "show port stats 0" check forwarding packages start.

    run "port detach 0", check the error message of port not stopped.

    run "stop", then "show port stats 0", check forwarding packages stopped.

3. Detach port 0 after port closed

    run "port stop 0".

    run "port close 0".

    run "port detach 0", check port detached successful.

4. Re-attach port 0

    run "port attach eth_pcap0,iface=xxxx", where "xxxx" is one workable ifname.

    run "port start 0".

    run "show port info 0", check port 0 info display correctly.

5. Check package forwarding after port start

    run "start", then "show port stats 0" check forwarding packages start.

    run "port detach 0", check the error message of port not stopped.

    run "stop", then "show port stats 0", check forwarding packages stopped.

successfully
