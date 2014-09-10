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

==================
HelloWorld example
==================

This example is one of the most simple RTE application that can be
done. The program will just print a "helloworld" message on every
enabled lcore.

Command Usage::

  ./helloworld -c COREMASK [-m NB] [-r NUM] [-n NUM]

    EAL option list:
      -c COREMASK: hexadecimal bitmask of cores we are running on
      -m MB      : memory to allocate (default = size of hugemem)
      -n NUM     : force number of memory channels (don't detect)
      -r NUM     : force number of memory ranks (don't detect)
      --huge-file: base filename for hugetlbfs entries
    debug options:
      --no-huge  : use malloc instead of hugetlbfs
      --no-pci   : disable pci
      --no-hpet  : disable hpet
      --no-shconf: no shared config (mmap'd files)


Prerequisites
=============

Support igb_uio and vfio driver, if used vfio, kernel need 3.6+ and enable vt-d in bios.
When used vfio , used "modprobe vfio" and "modprobe vfio-pci" insmod vfiod driver, then used
"./tools/dpdk_nic_bind.py --bind=vfio-pci device_bus_id" to bind vfio driver to test driver.

To find out the mapping of lcores (processor) to core id and socket (physical
id), the command below can be used::

  $ grep "processor\|physical id\|core id\|^$" /proc/cpuinfo

The total logical core number will be used as ``helloworld`` input parameters.


Test Case: run hello world on single lcores
===========================================

To run example in singel lcore ::
        
  $ ./helloworld -c 1
    hello from core 0

Check the output is exact the lcore 0


Test Case: run hello world on every lcores
==========================================

To run the example in all the enabled lcore ::
        
  $ ./helloworld -cffffff
    hello from core 1
    hello from core 2
    hello from core 3
           ...
           ...
    hello from core 0

Verify the output of according to all the core masks.

