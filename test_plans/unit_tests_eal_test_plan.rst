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

=============
EAL Autotests
=============

This section describes the tests that are done to validate the EAL. Each
test can be launched independently using the command line
interface. These tests are implemented as a linuxapp environment
application.

The complete test suite is launched automatically using a python-expect
script (launched using ``make test``) that sends commands to
the application and checks the results. A test report is displayed on
stdout.

Version
=======

To Be Filled


Common
=======

To Be Filled

Eal_fs
======

To Be Filled

Memory
======

- Dump the mapped memory. The python-expect script checks that at
  least one line is dumped.

- Check that memory size is different than 0.

- Try to read all memory; it should not segfault.

PCI
===

- Register a driver with a ``devinit()`` function.

- Dump all PCI devices.

- Check that the ``devinit()`` function is called at least once.

Per-lcore Variables and lcore Launch
====================================

- Use ``rte_eal_mp_remote_launch()`` to call ``assign_vars()`` on
  every available lcore. In this function, a per-lcore variable is
  assigned to the lcore_id.

- Use ``rte_eal_mp_remote_launch()`` to call ``display_vars()`` on
  every available lcore. The function checks that the variable is
  correctly set, or returns -1.

- If at least one per-core variable was not correct, the test function
  returns -1.

Spinlock
========

- There is a global spinlock and a table of spinlocks (one per lcore).

- The test function takes all of these locks and launches the
  ``test_spinlock_per_core()`` function on each core (except the master).

  - The function takes the global lock, displays something, then releases
    the global lock.
  - The function takes the per-lcore lock, displays something, then releases
    the per-core lock.

- The main function unlocks the per-lcore locks sequentially and
  waits between each lock. This triggers the display of a message
  for each core, in the correct order. The autotest script checks that
  this order is correct.

Rwlock
======

- There is a global rwlock and a table of rwlocks (one per lcore).

- The test function takes all of these locks and launches the
  ``test_rwlock_per_core()`` function on each core (except the master).

  - The function takes the global write lock, display something,
    then releases the global lock.
  - Then, it takes the per-lcore write lock, display something, and
    releases the per-core lock.
  - Finally, a read lock is taken during 100 ms, then released.

- The main function unlocks the per-lcore locks sequentially and
  waits between each lock. This triggers the display of a message
  for each core, in the correct order.

  Then, it tries to take the global write lock and display the last
  message. The autotest script checks that the message order is correct.

Atomic Variables
================

- The main test function performs three subtests. The first test
  checks that the usual inc/dec/add/sub functions are working
  correctly:

  - Initialize 32-bit and 64-bit atomic variables to specific
    values.

  - These variables are incremented and decremented on each core at
    the same time in ``test_atomic_usual()``.

  - The function checks that once all lcores finish their function,
    the value of the atomic variables are still the same.

- The second test verifies the behavior of "test and set" functions.

  - Initialize 32-bit and 64-bit atomic variables to zero.

  - Invoke ``test_atomic_tas()`` on each lcore before doing anything
    else. The cores are awaiting synchronizatioin using the ``while
    (rte_atomic32_read(&val) == 0)`` statement which is triggered by the
    main test function. Then all cores do an
    ``rte_atomicXX_test_and_set()`` at the same time. If it is successful,
    it increments another atomic counter.

  - The main function checks that the atomic counter was incremented
    twice only (one for 32-bit and one for 64-bit values).

- Test "add/sub and return"

  - Initialize 32-bit and 64-bit atomic variables to zero.

  - Invoke ``test_atomic_addsub_return()`` on each lcore. Before doing
    anything else, the cores are waiting a synchro. Each lcore does
    this operation several times::
      
      tmp = atomic_add_return(&a, 1);
      atomic_add(&count, tmp);
      tmp = atomic_sub_return(&a, 1);
      atomic_sub(&count, tmp+1);

  - At the end of the test, the *count* value must be 0.

Prefetch
========

Just test that the macro can be called and validate the compilation.
The test always return success.

Byteorder functions
===================

Check the result of optimized byte swap functions for each size (16-,
32- and 64-bit).

Cycles Test
===========

- Loop N times and check that the timer alway increments and
  never decrements during this loop.

- Wait one second using rte_usleep() and check that the increment
  of cycles is correct with regard to the frequency of the timer.

Logs
====

- Enable log types.
- Set log level.
- Execute logging functions with different types and levels; some should
  not be displayed.

Memzone
=======

- Search for three reserved zones or reserve them if they do not exist:

  - One is on any socket id.
  - The second is on socket 0.
  - The last one is on socket 1 (if socket 1 exists).

- Check that the zones exist.

- Check that the zones are cache-aligned.

- Check that zones do not overlap.

- Check that the zones are on the correct socket id.

- Check that a lookup of the first zone returns the same pointer.

- Check that it is not possible to create another zone with the
  same name as an existing zone.

Memcpy
======

Create two buffers, and initialise one with random values. These are copied
to the second buffer and then compared to see if the copy was successfull.
The bytes outside the copied area are also checked to make sure they were not
changed.

This is repeated for a number of different sizes and offsets, with
the second buffer being cleared before each test.

Debug test
==========

- Call rte_dump_stack() and rte_dump_registers().

Alarm
=====

- Check that the callback for the alarm can to be called.
- Check that it is not possible to set alarm with invalid time value.
- Check that it is not possible to set alarm without a callback.
- Check that it is not possible to cancel alarm without a callback pointer.
- Check that multiple callbacks for the alarm can be called.
- Check that the number of removed and unremoved alarms are correct.
- Check that no callback is called if all alarm removed.
- Check that it is not possible to cancel an alarm within the callback itself.
- Check that the callback which is the head of all is able to be removed.
- Check that all alarms for the same callback can be cancelled.


CPU flags
=========

- Using the rte_cpu_get_flag_enabled() checks for CPU features from different CPUID tables
- Checks if rte_cpu_get_flag_enabled() properly fails on trying to check for invalid feature


Errno
=====

Performs validation on the error message strings provided by the rte_strerror() call, to ensure that suitable strings are returned for the rte-specific error codes, as well as ensuring that for standard error codes the correct error message is returned.

Interrupts
==========
- Check that the callback for the specific interrupt can be called.
- Check that it is not possible to register a callback to an invalid interrupt handle.
- Check that it is not possible to register no callback to an interrupt handle.
- Check that it is not possible to unregister a callback to an invalid interrupt handle.
- Check that multiple callbacks are registered to the same interrupt handle.
- Check that it is not possible to unregister a callback with invalid parameter.
- Check that it is not possible to enable an interrupt with invalid handle or wrong handle type.
- Check that it is not possible to disable an interrupt with invalid handle or wrong handle type.


Multiprocess
============

Validates that a secondary Intel DPDK instance can be run alongside a primary when the appropriate EAL command-line flags are passed. Also validates that secondary processes cannot interfere with primary processes by creating memory objects, such as mempools or rings.

String
======

Performs validation on the new string functions provided in rte_string_fns.h, ensuring that all values returned are NULL terminated, and that suitable errors are returned when called with invalid parameters.

Tailq
=====

Validates that we can create and perform lookups on named tail queues within the EAL for various object types. Also ensures appropriate error codes are returned from the functions if invalid parameters are passed.

Devargs
=======
To Be Filled

Kvargs
======
To Be Filled

Acl
===
To Be Filled

Link_bonding
============
To Be Filled
