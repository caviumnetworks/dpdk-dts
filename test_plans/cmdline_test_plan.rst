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

===============
Cmdline example
===============

The cmdline example is a demo example of command line interface in RTE. 
This library is a readline-like interface that can be used to debug your 
RTE application.

It supports some features of GNU readline like completion, cut/paste,
and some other special bindings that makes configuration and debug
faster and easier.

This demo shows how rte_cmdline library can be extended to handle a
list of objects. There are 3 simple commands:

- ``add obj_name IP``: add a new object with an IP/IPv6 address
  associated to it.

- ``del obj_name``: del the specified object.

- ``show obj_name``: show the IP associated with the specified object.

Refer to programmer's guide in ``${RTE_SDK}/doc/rst`` for details.


Prerequisites
=============

Support igb_uio and vfio driver, if used vfio, kernel need 3.6+ and enable vt-d in bios.
When used vfio , used "modprobe vfio" and "modprobe vfio-pci" insmod vfiod driver, then used
"./tools/dpdk_nic_bind.py --bind=vfio-pci device_bus_id" to bind vfio driver to test driver.

Launch the ``cmdline`` with 24 logical cores in linuxapp environment::

  $ ./build/app/cmdline -cffffff

Test the 3 simple commands in below prompt ::
  
  example>


Test Case: cmdline sample commands test
=======================================

Add a test object with an IP address associated to it::
    
  example>add objtest 192.168.0.1
    Object objtest added, ip=192.168.0.1 

Verify the object existance::
        
  example>add objtest 192.168.0.1
    Object objtest already exist

Show the object result by ``show`` command::
  
  example>show objtest
    Object objtest, ip=192.168.0.1

Verify the output matchs the confiuration.

Delete the object in cmdline and show the result again::
        
  example>del objtest
    Object objtest removed, ip=192.168.0.1

Double delete the object to verify the correctness::
  
  example>del objtest
    Bad arguments

Verify no such object exist now.::

  example>show objtest
    Bad arguments

Verify the hidden command ? and help command::
       
  example>help
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

  example>?
    show [Mul-choice STRING]: Show/del an object
    del [Mul-choice STRING]: Show/del an object
    add [Fixed STRING]: Add an object (name, val)
    help [Fixed STRING]: show help

Test Case: cmdline exit test
============================

To verify exit cmdline process::
        
  example>^D

.. there should be an ``quit`` command instead of ^D, 
   or a hint make the user know how to exit.





