..  BSD LICENSE
    Copyright(c) 2010-2016 Intel Corporation. All rights reserved.
    All rights reserved.

    Redistribution and use in source and binary forms, with or without
    modification, are permitted provided that the following conditions
    are met:

    * Redistributions of source code must retain the above copyright
    notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
    notice, this list of conditions and the following disclaimer in
    the documentation and/or other materials provided with the
    distribution.
    * Neither the name of Intel Corporation nor the names of its
    contributors may be used to endorse or promote products derived
    from this software without specific prior written permission.

    THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
    "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
    LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
    A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
    OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
    SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
    LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
    DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
    THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
    (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
    OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


Netmap Compatibility Sample Application
=======================================

Introduction
------------

The Netmap compatibility library provides a minimal set of APIs to give programs written against the Netmap APIs
the ability to be run, with minimal changes to their source code, using the DPDK to perform the actual packet I/O.

Since Netmap applications use regular system calls, like ``open()``, ``ioctl()`` and
``mmap()`` to communicate with the Netmap kernel module performing the packet I/O,
the ``compat_netmap`` library provides a set of similar APIs to use in place of those system calls,
effectively turning a Netmap application into a DPDK application.

The provided library is currently minimal and doesn't support all the features that Netmap supports,
but is enough to run simple applications, such as the bridge example detailed below.

Knowledge of Netmap is required to understand the rest of this section.
Please refer to the Netmap distribution for details about Netmap.

Running the "bridge" Sample Application
---------------------------------------

The application requires a single command line option:

    ./build/bridge [EAL options] -- -i INTERFACE_A [-i INTERFACE_B]

where,

*   ``-i INTERFACE``: Interface (DPDK port number) to use.

    If a single ``-i`` parameter is given, the interface will send back all the traffic it receives.
    If two ``-i`` parameters are given, the two interfaces form a bridge,
    where traffic received on one interface is replicated and sent to the other interface.

For example, to run the application in a linuxapp environment using port 0 and 2:

    ./build/bridge [EAL options] -- -i 0 -i 2

Refer to the *DPDK Getting Started Guide for Linux* for general information on running applications and
the Environment Abstraction Layer (EAL) options.

Test Case1: netmap compat with one port 
=======================================
Run bridge with one port::
        ./examples/netmap_compat/build/bridge -c 0x1e -n 4 -- -i 0
waked up :
        Port 0 now in Netmap mode
        Bridge up and running!

Send one packet on Port0,check this port receive packet. 
It receive one packet that it send.

Test Case2: netmap compat with two port
=======================================
Run bridge with one port::
        ./examples/netmap_compat/build/bridge -c 0x1e -n 4 -- -i 0 -i 1
waked up :
        Port 0 now in Netmap mode
        Port 1 now in Netmap mode
        Bridge up and running!

Send one packet on Port0,check the port1 receive packet.
It receive one packet that the port0 send.

