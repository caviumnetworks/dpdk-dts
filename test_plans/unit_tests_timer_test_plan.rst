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
Timer Autotests
===============

This section describes the test plan for the timer library.

Description
===========

#. Stress tests.

   The objective of the timer stress tests is to check that there are no
   race conditions in list and status management. This test launches,
   resets and stops the timer very often on many cores at the same
   time.

   - Only one timer is used for this test.
   - On each core, the rte_timer_manage() function is called from the main loop
     every 3 microseconds.
   - In the main loop, the timer may be reset (randomly, with a
     probability of 0.5 %) 100 microseconds later on a random core, or
     stopped (with a probability of 0.5 % also).
   - In callback, the timer is can be reset (randomly, with a
     probability of 0.5 %) 100 microseconds later on the same core or
     on another core (same probability), or stopped (same
     probability).

#. Basic test.

   This test performs basic functional checks of the timers. The test
   uses four different timers that are loaded and stopped under
   specific conditions in specific contexts.

   - Four timers are used for this test.
   - On each core, the rte_timer_manage() function is called from main loop
     every 3 microseconds.

   The autotest python script checks that the behavior is correct:

   - timer0

     - At initialization, timer0 is loaded by the master core, on master core in
       "single" mode (time = 1 second).
     - In the first 19 callbacks, timer0 is reloaded on the same core,
       then, it is explicitly stopped at the 20th call.
     - At t=25s, timer0 is reloaded once by timer2.

   - timer1

     - At initialization, timer1 is loaded by the master core, on the
       master core in "single" mode (time = 2 seconds).
     - In the first 9 callbacks, timer1 is reloaded on another
       core. After the 10th callback, timer1 is not reloaded anymore.

   - timer2

     - At initialization, timer2 is loaded by the master core, on the
       master core in "periodical" mode (time = 1 second).
     - In the callback, when t=25s, it stops timer3 and reloads timer0
       on the current core.

   - timer3

     - At initialization, timer3 is loaded by the master core, on
       another core in "periodical" mode (time = 1 second).
     - It is stopped at t=25s by timer2.
