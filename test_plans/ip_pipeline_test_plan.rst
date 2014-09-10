.. Copyright (c) <2010>, Intel Corporation
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

=======================
Ip_pipeline application
=======================

The ``ip_pipeline application`` is the main DPDK Packet Framework (PFW)
application.

The application allows setting of a pipeline through the PFW. Currently the
application set a pipeline using 2 main features, routing and flow control
and, in addition, ARP is used.

The application has an interactive session when started to allow in-app
configuration.

This application uses 5 CPU cores, reception, flow control, routing and
transmission.

The traffic will pass through the pipeline if meets the following conditions:

  - If ``flow add all`` is used in the setup then:

    - TCP/IPv4
    - IP destination = A.B.C.D with A = 0 and B,C,D random
    - IP source = 0.0.0.0
    - TCP destination port = 0
    - TCP source port = 0

  - If ``flow add all`` is not used then there is no restrictions.

Prerequisites
=============

Launch the ``ip_pipeline`` app with 5 lcores and two ports::

  $ examples/ip_pipeline/build/ip_pipeline -c 0x3e -n <memory channels> -- -p
  <ports mask>

The expected prompt is::

  pipeline>


The selected ports will be called 0 and 1 in the following instructions.

Tcpdump is used in test as a traffic sniffer unless otherwise stated. Tcpdump
is set in both ports to check that traffic is sent and forwarded, or not
forwarded.

Scapy is used in test as traffic generator unless otherwise stated.

The PCAP driver is used in some tests as a traffic generator and sniffer.

NOTE: ``ip_pipeline`` is currently hardcoded to start the reception from ports
automatically. Prior to running the test described in this document this
behaviour has to be modified by commenting out the following lines in
``examples/ip_pipeline/pipeline_rx.c``::

    /* Enable input ports */
    for (i = 0; i < app.n_ports; i ++) {
            if (rte_pipeline_port_in_enable(p, port_in_id[i])) {
                    rte_panic("Unable to enable input port %u\n", port_in_id[i]);
            }
    }


Test Case: test_incremental_ip
==============================

Create a PCAP file containing permutations of the following parameters:

 - TCP/IPv4.
 - 64B size.
 - Number of frames sent. 1, 3, 63, 64, 65, 127, 128.
 - Interval between frames. 0s, 0.7s.
 - Incremental destination IP address. 1 by 1 increment on every frame.
 - Maximum IP address 255.128.0.0.

Start the ``ip_pipeline`` application as described in prerequisites. Run the
default config script::

  pipeline> run examples/ip_pipeline/ip_pipeline.sh

Start port reception::

  link 0 up link 1 up

Send the generated PCAP file from port 1 to 0, check that all frames are
forwarded to port 0. Send the generated PCAP file from port 0 to 1, check that
all frames are forwarded to port 0.

Stop port reception::

  link 0 down link 1 down

Test Case: test_frame_sizes
===========================

Create a PCAP file containing permutations of the following parameters:

 - TCP/IPv4.
 - Frame size 64, 65, 128.
 - 100 frames.
 - 0.5s interval between frames.
 - Incremental destination IP address. 1 by 1 increment on every frame.
 - Maximum IP address 255.128.0.0.

Start the ``ip_pipeline`` application as described in prerequisites. Run the
default config script::

  pipeline> run examples/ip_pipeline/ip_pipeline.sh

Start port reception::

  link 0 up link 1 up

Send the generated PCAP file from port 1 to 0, check that all frames are
forwarded to port 0. Send the generated PCAP file from port 0 to 1, check that
all frames are forwarded to port 0.

Stop port reception::

  link 0 down link 1 down

Test Case: test_pcap_incremental_ip
===================================

Compile the DPDK to use the PCAP driver. Modify the target config file to allow
PCAP driver::

    sed -i 's/CONFIG_RTE_LIBRTE_PMD_PCAP=n$/CONFIG_RTE_LIBRTE_PMD_PCAP=y/' config/defconfig_<target>

Create a PCAP file containing permutations of the following parameters:

 - TCP/IPv4.
 - 64B size.
 - Number of frames sent. 1, 3, 63, 64, 65, 127, 128.
 - Incremental destination IP address. 1 by 1 increment on every frame.
 - Maximum IP address 255.128.0.0.

Start the ``ip_pipeline`` application using pcap devices::

    $ ./examples/ip_pipeline/build/ip_pipeline -c <core mask> -n <mem channels> --use-device <pcap devices> -- -p 0x3

    <pcap devices>: 'eth_pcap0;rx_pcap=/root/<input pcap file 0>;tx_pcap=/tmp/port0out.pcap,eth_pcap1;rx_pcap=/root/<input pcap file 1>;tx_pcap=/tmp/port1out.pcap'

Run the default config script::

  pipeline> run examples/ip_pipeline/ip_pipeline.sh

As the traffic is sent and received by PCAP devices the traffic flow is
triggered by enabling the ports::

  link 0 up link 1 up

Wait 1s to allow all frames to be sent and stop the ports::

  link 0 down link 1 down

Check the results PCAP files ``tmp/port0out.pcap`` and ``tmp/port1out.pcap``,
the frames must be received in port 0, ``tmp/port0out.pcap``.

Test Case: test_pcap_frame_sizes
================================

Compile DPDK to use PCAP driver. Modify the target config file to allow PCAP
driver:

    sed -i 's/CONFIG_RTE_LIBRTE_PMD_PCAP=n$/CONFIG_RTE_LIBRTE_PMD_PCAP=y/'
    config/defconfig_<target>

Create a PCAP file containing permutations of the following parameters:

 - TCP/IPv4.
 - Frame sizes 64, 65, 128.
 - Number of frames sent. 1, 3, 63, 64, 65, 127, 128.
 - Incremental destination IP address. 1 by 1 increment on every frame.
 - Maximum IP address 255.128.0.0.

Start the ``ip_pipeline`` application using pcap devices::

    $ ./examples/ip_pipeline/build/ip_pipeline -c <core mask> -n <mem channels> --use-device <pcap devices> -- -p 0x3

    <pcap devices>: 'eth_pcap0;rx_pcap=/root/<input pcap file 0>;tx_pcap=/tmp/port0out.pcap,eth_pcap1;rx_pcap=/root/<input pcap file 1>;tx_pcap=/tmp/port1out.pcap'

Run the default config script::

   pipeline> run examples/ip_pipeline/ip_pipeline.sh

As the traffic is sent and received by PCAP devices the traffic flow is
triggered by enabling the ports::

   link 0 up
   link 1 up

Wait 1s to allow all frames to be sent and stop the ports::

   link 0 down
   link 1 down


Check the results PCAP files ``tmp/port0out.pcap`` and ``tmp/port1out.pcap``,
the frames must be received in port 0, ``tmp/port0out.pcap``.

Test Case: test_flow_management
===============================

This test checks the flow addition and removal feature in the packet framework.

Create a PCAP file containing the following traffic:

 - TCP/IPv4.
 - Frame size 64.
 - Source IP address 0.0.0.0
 - Destination IP addresses: '0.0.0.0', '0.0.0.1', '0.0.0.127', '0.0.0.128',
   '0.0.0.255', '0.0.1.0', '0.0.127.0', '0.0.128.0', '0.0.129.0', '0.0.255.0',
   '0.127.0.0', '0.127.1.0', '0.127.127.0', '0.127.255.0', '0.127.255.255'

Start the ``ip_pipeline`` application as described in prerequisites and set up
the following configuration::

    pipeline> arp add 0 0.0.0.1 0a:0b:0c:0d:0e:0f
    pipeline> arp add 1 0.128.0.1 1a:1b:1c:1d:1e:1f
    pipeline> route add 0.0.0.0 9 0 0.0.0.1
    pipeline> route add 0.128.0.0 9 1 0.128.0.1

Start port reception::

  link 0 up link 1 up

1. Send the pcap file and check that the number of frames forwarded matches the
   number of flows added (starting at 0)

2. Add a new flow matching one of the IP address::

      pipeline> flow add 0.0.0.0 <dst IP> 0 0 0 <port>

3. Repeat Step 1 until all the frames pass

4. Remove a flow previously added::

      pipeline> flow del 0.0.0.0 <dst IP> 0 0 0

5. Check if a frames less is forwarded.

6. Repeat from step 4 until no frames are forwarded.

Test Case: test_route_management
================================

This test checks the route addition and removal feature in the packet framework.

Create a PCAP file containing the following traffic:

 - TCP/IPv4.
 - Frame size 64.
 - Source IP address 0.0.0.0
 - Destination IP addresses: '0.0.0.0', '0.0.0.1', '0.0.0.127', '0.0.0.128',
   '0.0.0.255', '0.0.1.0', '0.0.127.0', '0.0.128.0', '0.0.129.0', '0.0.255.0',
   '0.127.0.0', '0.127.1.0', '0.127.127.0', '0.127.255.0', '0.127.255.255'

Start the ``ip_pipeline`` application as described in prerequisites and set up
the following configuration::

    pipeline> arp add 0 0.0.0.1 0a:0b:0c:0d:0e:0f
    pipeline> arp add 1 0.128.0.1 1a:1b:1c:1d:1e:1f
    pipeline> flow add all

Start port reception::

  link 0 up link 1 up

1. Send the pcap file and check that the number of frames forwarded matches
   the number of routes added (starting at 0)

2. Add a new route matching one of the IP address::

      pipeline> route add <src IP> 32 <port> 0.0.0.1

3. Repeat Step 1 until all the frames pass

4. Remove a route previously added::

      pipeline> route del <dst IP> 32

5. Check if a frames less is forwarded.

6. Repeat from step 4 until no frames are forwarded.
