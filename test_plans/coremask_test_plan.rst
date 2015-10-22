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

Prerequisites
=============

This test will run in any machine able to run ``test``. No traffic will be sent.
No extra needs for ports.


Test Case: individual coremask
==============================

Launch ``test`` once per core, set the core mask for the core::

    ./x86_64-default-linuxapp-gcc/app/test -c <One core mask> -n 4


Verify: every time the application is launched the core is properly detected 
and used.

Stop ``test``.


Test Case: big coremask
=======================

Launch ``test`` with a mask bigger than the available cores::

    ./x86_64-default-linuxapp-gcc/app/test -c <128 bits mask> -n 4


Verify: the application handles the mask properly and all the available cores 
are detected and used.

Stop ``test``.

Test Case: all cores
====================

Launch ``test`` with all the available cores::

    ./x86_64-default-linuxapp-gcc/app/test -c <All cores mask> -n 4


Verify: all the cores have been detected and used by the application.

Stop ``test``.

Test Case: wrong coremask
=========================

Launch ``test`` with several wrong masks::

    ./x86_64-default-linuxapp-gcc/app/test -c <Wrong mask> -n 4


Verify: the application complains about the mask and does not start.

Stop ``test``.
