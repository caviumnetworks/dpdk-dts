# BSD LICENSE
#
# Copyright(c) 2010-2015 Intel Corporation. All rights reserved.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#   * Redistributions of source code must retain the above copyright
#     notice, this list of conditions and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright
#     notice, this list of conditions and the following disclaimer in
#     the documentation and/or other materials provided with the
#     distribution.
#   * Neither the name of Intel Corporation nor the names of its
#     contributors may be used to endorse or promote products derived
#     from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT

import sys
import os
import signal
import code
import time
import dts


console = None  # global console object
debug_cmd = ''  # global debug state


def help_command():
    console.push('print \'Help on debug module\'')
    console.push('print \'DESCRIPTION\'')
    console.push('print \'DTS debug module support few debug commands\'')
    console.push('print \'  - help: help messages\'')
    console.push('print \'  - list: list all connections\'')
    console.push('print \'  - connect: bind to specified connection\'')
    console.push('print \'  -        : connect(\"dut\")\'')
    console.push('print \'  - quit: quit debug module\'')
    console.push('print \'  - exit: exit processing procedure\'')
    console.push('print \'  - debug: call python debug module for further debug\'')


def list_command():
    """
    List all connection sessions and can be reference of connect command.
    """
    index = 0
    from ssh_connection import CONNECTIONS
    for connection in CONNECTIONS:
        for name, session in connection.items():
            console.push('print \'connect %d: %10s\'' % (index, name))
            index += 1


def connect_command(connect):
    """
    Connect to ssh session and give control to user.
    """
    from ssh_connection import CONNECTIONS
    for connection in CONNECTIONS:
        for name, session in connection.items():
            if name == connect:
                session.session.interact()


def exit_command():
    """
    Exit dts framework.
    """
    global debug_cmd
    debug_cmd = 'exit'
    sys.exit(0)


def debug_command():
    """
    Give control to python debugger pdb.
    """
    global debug_cmd
    debug_cmd = 'debug'
    sys.exit(0)


def capture_handle(signum, frame):
    """
    Capture keyboard interrupt in the process of send_expect.
    """
    global debug_cmd
    debug_cmd = 'waiting'


def keyboard_handle(signum, frame):
    """
    Interrupt handler for SIGINT and call code module create python interpreter.
    """
    global console
    console = code.InteractiveConsole()
    command = {}
    command['list'] = list_command
    command['exit'] = exit_command
    command['debug'] = debug_command
    command['help'] = help_command
    command['connect'] = connect_command
    console.push('print \"Use help command for detail information\"')
    try:
        code.interact(local=command)
    except SystemExit:
        # reopen sys.stdin for after exit function stdin will be closed
        fd = os.open('/dev/stdin', 600)
        sys.stdin = os.fdopen(fd, 'r')

    global debug_cmd
    if debug_cmd == 'debug':
        # call pyton debugger
        import pdb
        pdb.set_trace()
    elif debug_cmd == 'exit':
        sys.exit(0)

    debug_cmd = ''


def ignore_keyintr():
    """
    Temporary disable interrupt handler.
    """
    global debug_cmd
    signal.siginterrupt(signal.SIGINT, True)
    # if there's waiting request, first handler it
    if debug_cmd == 'waiting':
        keyboard_handle(signal.SIGINT, None)

    return signal.signal(signal.SIGINT, capture_handle)


def aware_keyintr():
    """
    Reenable interrupt handler.
    """
    return signal.signal(signal.SIGINT, keyboard_handle)
