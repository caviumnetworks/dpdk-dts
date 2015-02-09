#!/usr/bin/python
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

"""
A test framework for testing DPDK.
"""

import os
import argparse
import dts


def git_build_package(gitLabel, gitPkg, output):
    """
    generate package from git
    run bash shell
    """
    gitURL = r"http://dpdk.org/git/dpdk"
    gitPrefix = r"dpdk/"
    print "git clone %s %s/%s" % (gitURL, output, gitPrefix)
    os.system("git clone %s output/%s" % (gitURL, gitPrefix))
    print "git archive --format=tar.gz --prefix=%s %s -o %s" % (gitPrefix, gitLabel, gitPkg)
    os.system("cd output/%s && git archive --format=tar.gz --prefix=%s %s -o %s" % (gitPrefix, gitPrefix, gitLabel, gitPkg))

#
# Main program begins here
#


# Read cmd-line args
parser = argparse.ArgumentParser(description='DPDK test framework.')

parser.add_argument('--config-file',
                    default='execution.cfg',
                    help='configuration file that describes the test ' +
                    'cases, DUTs and targets')

parser.add_argument('--git',
                    help='git label to use as input')

parser.add_argument('--patch',
                    action='append',
                    help='apply a patch to the package under test')

parser.add_argument('--snapshot',
                    default='dpdk.tar.gz',
                    help='snapshot .tgz file to use as input')

parser.add_argument('--output',
                    default='output',
                    help='Output directory where dts log and result saved')

parser.add_argument('-s', '--skip-setup',
                    action='store_true',
                    help='skips all possible setup steps done on both DUT' +
                    ' and tester boards.')

parser.add_argument('-r', '--read-cache',
                    action='store_true',
                    help='reads the DUT configuration from a cache. If not ' +
                    'specified, the DUT configuration will be calculated ' +
                    'as usual and cached.')

parser.add_argument('-p', '--project',
                    default='dpdk',
                    help='specify that which project will be tested')

parser.add_argument('--suite-dir',
                    default='tests',
                    help='Test suite directory where test suites will be imported')

parser.add_argument('-t', '--test-cases',
                    nargs='+',
                    help='executes only the followings test cases')

parser.add_argument('-d', '--dir',
                    default='dpdk',
                    help='Output directory where dpdk package is extracted')

parser.add_argument('-v', '--verbose',
                    action='store_true',
                    help='enable verbose output, all message output on screen')

args = parser.parse_args()


# prepare DPDK source test package
if args.git is not None:
    git_build_package(args.git, args.snapshot, args.output)

dts.run_all(args.config_file, args.snapshot, args.git,
            args.patch, args.skip_setup, args.read_cache,
            args.project, args.suite_dir, args.test_cases,
            args.dir, args.output, args.verbose)
