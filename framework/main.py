#!/usr/bin/python

# <COPYRIGHT_TAG>

"""
A test framework for testing DPDK.
"""

import os
import argparse
import dcts


def git_build_package(gitLabel, gitPkg, output):
    """
    generate package from git
    run bash shell
    """
    gitURL = r"http://dpdk.org/git/dpdk"
    gitPrefix = r"dpdk/"
    print "git clone %s %s/%s" % (gitURL, output, gitPrefix)
    os.system("git clone %s ../output/%s" % (gitURL, gitPrefix))
    print "git archive --format=tar.gz --prefix=%s %s -o ../%s" % (gitPrefix, gitLabel, gitPkg)
    os.system("cd ../output/%s && git archive --format=tar.gz --prefix=%s %s -o ../%s" % (gitPrefix, gitPrefix, gitLabel, gitPkg))

#
# Main program begins here
#


# Read cmd-line args
parser = argparse.ArgumentParser(description='DPDK test framework.')

parser.add_argument('--config-file',
                    default='../execution.cfg',
                    help='configuration file that describes the test ' +
                    'cases, DUTs and targets')

parser.add_argument('--git',
                    help='git label to use as input')

parser.add_argument('--patch',
                    action='append',
                    help='apply a patch to the package under test')

parser.add_argument('--snapshot',
                    default='../dpdk.tar.gz',
                    help='snapshot .tgz file to use as input')

parser.add_argument('--output',
                    default='../output',
                    help='Output directory where dcts log and result saved')

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
                    default='../tests',
                    help='Test suite directory where test suites will be imported')

parser.add_argument('-t', '--test-cases',
                    nargs='+',
                    help='executes only the followings test cases')

parser.add_argument('-d', '--dir',
                    default='dpdk',
                    help='Output directory where dpdk package is extracted')


args = parser.parse_args()


# prepare DPDK source test package
if args.git is not None:
    git_build_package(args.git, args.snapshot, args.output)

dcts.run_all(args.config_file, args.snapshot, args.git,
             args.patch, args.skip_setup, args.read_cache,
             args.project, args.suite_dir, args.test_cases,
             args.dir, args.output)
