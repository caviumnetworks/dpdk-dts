# BSD LICENSE
#
# Copyright(c) 2010-2014 Intel Corporation. All rights reserved.
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
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import json         # json format
import re


def RED(text):
    return "\x1B[" + "31;1m" + str(text) + "\x1B[" + "0m"


def BLUE(text):
    return "\x1B[" + "36;1m" + str(text) + "\x1B[" + "0m"


def GREEN(text):
    return "\x1B[" + "32;1m" + str(text) + "\x1B[" + "0m"


def pprint(some_dict):
    """
    Print JSON format dictionary object.
    """
    return json.dumps(some_dict, sort_keys=True, indent=4)


def regexp(s, to_match, allString=False):
    """
    Ensure that the re `to_match' only has one group in it.
    """

    scanner = re.compile(to_match, re.DOTALL)
    if allString:
        return scanner.findall(s)
    m = scanner.search(s)
    if m is None:
        print RED("Failed to match " + to_match + " in the string " + s)
        return None
    return m.group(1)


def get_obj_funcs(obj, func_name_regex):
    """
    Return function list which name matched regex.
    """
    for func_name in dir(obj):
        func = getattr(obj, func_name)
        if callable(func) and re.match(func_name_regex, func.__name__):
            yield func


def remove_old_rsa_key(crb, ip):
    """
    Remove the old RSA key of specified IP on crb.
    """
    if ':' not in ip:
        ip = ip.strip()
        port = ''
    else:
        addr = ip.split(':')
        ip = addr[0].strip()
        port = addr[1].strip()

    rsa_key_path = "~/.ssh/known_hosts"
    if port:
        remove_rsa_key_cmd = "sed -i '/^\[%s\]:%d/d' %s" % \
            (ip.strip(), int(
             port), rsa_key_path)
    else:
        remove_rsa_key_cmd = "sed -i '/^%s/d' %s" % \
            (ip.strip(), rsa_key_path)
    crb.send_expect(remove_rsa_key_cmd, "# ")
