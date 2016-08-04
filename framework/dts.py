# BSD LICENSE
#
# Copyright(c) 2010-2016 Intel Corporation. All rights reserved.
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

import re           # regular expressions module
import ConfigParser  # config parse module
import os           # operation system module
import texttable    # text format
import traceback    # exception traceback
import inspect      # load attribute
import atexit       # register callback when exit
import json         # json format
import signal       # signal module for debug mode
import time         # time module for unique output folder
import copy         # copy module for duplicate variable

import rst          # rst file support
import sys          # system module
import settings     # dts settings
from tester import Tester
from dut import Dut
from serializer import Serializer
from test_case import TestCase
from test_result import Result
from stats_reporter import StatsReporter
from excel_reporter import ExcelReporter
import utils
from exception import TimeoutException, ConfigParseException, VerifyFailure
from logger import getLogger
import logger
import debugger
from config import CrbsConf
from checkCase import parse_file, check_case_skip, check_case_support
from utils import get_subclasses, copy_instance_attr
import sys
reload(sys)
sys.setdefaultencoding('UTF8')


config = None
requested_tests = None
result = None
excel_report = None
stats_report = None
log_handler = None


def dts_parse_param(section):
    """
    Parse execution file parameters.
    """
    # default value
    performance = False
    functional = False
    # Set parameters
    parameters = config.get(section, 'parameters').split(':')
    drivername = config.get(section, 'drivername').split('=')[-1]

    settings.save_global_setting(settings.HOST_DRIVER_SETTING, drivername)

    paramDict = dict()
    for param in parameters:
        (key, _, value) = param.partition('=')
        paramDict[key] = value

    if 'perf' in paramDict and paramDict['perf'] == 'true':
        performance = True
    if 'func' in paramDict and paramDict['func'] == 'true':
        functional = True

    if 'nic_type' not in paramDict:
        paramDict['nic_type'] = 'any'

    settings.save_global_setting(settings.HOST_NIC_SETTING, paramDict['nic_type'])

    # save perf/funtion setting in enviornment
    if performance:
        settings.save_global_setting(settings.PERF_SETTING, 'yes')
    else:
        settings.save_global_setting(settings.PERF_SETTING, 'no')

    if functional:
        settings.save_global_setting(settings.FUNC_SETTING, 'yes')
    else:
        settings.save_global_setting(settings.FUNC_SETTING, 'no')


def dts_parse_config(section):
    """
    Parse execution file configuration.
    """
    duts = [dut_.strip() for dut_ in config.get(section,
                                                'crbs').split(',')]
    targets = [target.strip()
               for target in config.get(section, 'targets').split(',')]
    test_suites = [suite.strip()
                   for suite in config.get(section, 'test_suites').split(',')]
    try:
        rx_mode = config.get(section, 'rx_mode').strip()
    except:
        rx_mode = 'default'

    settings.save_global_setting(settings.DPDK_RXMODE_SETTING, rx_mode)

    for suite in test_suites:
        if suite == '':
            test_suites.remove(suite)

    return duts, targets, test_suites


def dts_parse_commands(commands):
    """
    Parse command information from dts arguments
    """
    dts_commands = []

    if commands is None:
        return dts_commands

    args_format = {"shell": 0,
                   "crb": 1,
                   "stage": 2,
                   "check": 3,
                   "max_num": 4}
    cmd_fmt = r"\[(.*)\]"

    for command in commands:
        args = command.split(':')
        if len(args) != args_format['max_num']:
            log_handler.error("Command [%s] is lack of arguments" % command)
            raise VerifyFailure("commands input is not corrected")
            continue
        dts_command = {}

        m = re.match(cmd_fmt, args[0])
        if m:
            cmds = m.group(1).split(',')
            shell_cmd = ""
            for cmd in cmds:
                shell_cmd += cmd
                shell_cmd += ' '
            dts_command['command'] = shell_cmd[:-1]
        else:
            dts_command['command'] = args[0]
        if args[1] == "tester":
            dts_command['host'] = "tester"
        else:
            dts_command['host'] = "dut"
        if args[2] == "post-init":
            dts_command['stage'] = "post-init"
        else:
            dts_command['stage'] = "pre-init"
        if args[3] == "ignore":
            dts_command["verify"] = False
        else:
            dts_command["verify"] = True

        dts_commands.append(dts_command)

    return dts_commands


def dts_run_commands(crb, dts_commands):
    """
    Run dts input commands
    """
    for dts_command in dts_commands:
        command = dts_command['command']
        if crb.NAME == dts_command['host']:
            if crb.stage == dts_command['stage']:
                ret = crb.send_expect(command, expected="# ", verify=True)
                if type(ret) is int:
                    log_handler.error("[%s] return failure" % command)
                    if dts_command['verify'] is True:
                        raise VerifyFailure("Command execution failed")


def get_project_obj(project_name, super_class, crbInst, serializer):
    """
    Load project module and return crb instance.
    """
    project_obj = None
    PROJECT_MODULE_PREFIX = 'project_'
    try:
        project_module = __import__(PROJECT_MODULE_PREFIX + project_name)

        for project_subclassname, project_subclass in get_subclasses(project_module, super_class):
            project_obj = project_subclass(crbInst, serializer)
        if project_obj is None:
            project_obj = super_class(crbInst, serializer)
    except Exception as e:
        log_handler.info("LOAD PROJECT MODULE INFO: " + str(e))
        project_obj = super_class(crbInst, serializer)

    return project_obj


def dts_log_testsuite(duts, tester, suite_obj, log_handler, test_classname):
    """
    Change to SUITE self logger handler.
    """
    log_handler.config_suite(test_classname, 'dts')
    tester.logger.config_suite(test_classname, 'tester')

    for dutobj in duts:
        dutobj.logger.config_suite(test_classname, 'dut')
        dutobj.test_classname = test_classname

    try:
        if tester.it_uses_external_generator():
            getattr(tester, 'ixia_packet_gen')
            tester.ixia_packet_gen.logger.config_suite(test_classname, 'ixia')
    except Exception as ex:
        pass


def dts_log_execution(duts, tester, log_handler):
    """
    Change to DTS default logger handler.
    """
    log_handler.config_execution('dts')
    tester.logger.config_execution('tester')

    for dutobj in duts:
        dutobj.logger.config_execution('dut' + settings.LOG_NAME_SEP + '%s' % dutobj.crb['My IP'])

    try:
        if tester.it_uses_external_generator():
            getattr(tester, 'ixia_packet_gen')
            tester.ixia_packet_gen.logger.config_execution('ixia')
    except Exception as ex:
        pass


def dts_crbs_init(crbInsts, skip_setup, read_cache, project, base_dir, serializer, virttype):
    """
    Create dts dut/tester instance and initialize them.
    """
    duts = []

    serializer.set_serialized_filename(settings.FOLDERS['Output'] +
                                       '/.%s.cache' % crbInsts[0]['IP'])
    serializer.load_from_file()

    testInst = copy.copy(crbInsts[0])
    testInst['My IP'] = crbInsts[0]['tester IP']
    tester = get_project_obj(project, Tester, testInst, serializer)

    for crbInst in crbInsts:
        dutInst = copy.copy(crbInst)
        dutInst['My IP'] = crbInst['IP']
        dutobj = get_project_obj(project, Dut, dutInst, serializer)
        duts.append(dutobj)

    dts_log_execution(duts, tester, log_handler)

    tester.duts = duts
    show_speedup_options_messages(read_cache, skip_setup)
    tester.set_speedup_options(read_cache, skip_setup)
    tester.init_ext_gen()

    nic = settings.load_global_setting(settings.HOST_NIC_SETTING)
    for dutobj in duts:
        dutobj.tester = tester
        dutobj.set_virttype(virttype)
        dutobj.set_speedup_options(read_cache, skip_setup)
        dutobj.set_directory(base_dir)
        # save execution nic setting
        dutobj.set_nic_type(nic)

    return duts, tester


def dts_crbs_exit(duts, tester):
    """
    Call dut and tester exit function after execution finished
    """
    for dutobj in duts:
        dutobj.crb_exit()

    tester.crb_exit()


def dts_run_prerequisties(duts, tester, pkgName, patch, dts_commands, serializer):
    """
    Run dts prerequisties function.
    """
    try:
        dts_run_commands(tester, dts_commands)
        tester.prerequisites()
        dts_run_commands(tester, dts_commands)
        for dutobj in duts:
            dutobj.set_package(pkgName, patch)
            dutobj.prerequisites()
            dts_run_commands(dutobj, dts_commands)

        serializer.save_to_file()
    except Exception as ex:
        log_handler.error(" PREREQ EXCEPTION " + traceback.format_exc())
        result.add_failed_dut(duts[0], str(ex))
        log_handler.info('CACHE: Discarding cache.')
        serializer.discard_cache()
        return False


def dts_run_target(duts, tester, targets, test_suites):
    """
    Run each target in execution targets.
    """
    for target in targets:
        log_handler.info("\nTARGET " + target)
        result.target = target

        try:
            drivername = settings.load_global_setting(settings.HOST_DRIVER_SETTING)
            if drivername == "":
                for dutobj in duts:
                    dutobj.set_target(target, bind_dev=False)
            else:
                for dutobj in duts:
                    dutobj.set_target(target)
        except AssertionError as ex:
            log_handler.error(" TARGET ERROR: " + str(ex))
            result.add_failed_target(result.dut, target, str(ex))
            continue
        except Exception as ex:
            log_handler.error(" !!! DEBUG IT: " + traceback.format_exc())
            result.add_failed_target(result.dut, target, str(ex))
            continue

        dts_run_suite(duts, tester, test_suites, target)

    tester.restore_interfaces()

    for dutobj in duts:
        dutobj.stop_ports()
        dutobj.restore_interfaces()


def dts_run_suite(duts, tester, test_suites, target):
    """
    Run each suite in test suite list.
    """
    try:
        for suite_name in test_suites:
            result.test_suite = suite_name
            suite_module = __import__('TestSuite_' + suite_name)
            for test_classname, test_class in get_subclasses(suite_module, TestCase):

                suite_obj = test_class(duts, tester, target, suite_name)
                suite_obj.set_requested_cases(requested_tests)
                suite_obj.set_check_inst(check=check_case_inst, support=support_case_inst)
                result.nic = suite_obj.nic

                dts_log_testsuite(duts, tester, suite_obj, log_handler, test_classname)

                log_handler.info("\nTEST SUITE : " + test_classname)
                log_handler.info("NIC :        " + result.nic)

                if suite_obj.execute_setup_all():
                    suite_obj.execute_test_cases()
                    suite_obj.execute_tear_downall()

                # save suite cases result
                result.copy_suite(suite_obj.get_result())
                save_all_results()

                log_handler.info("\nTEST SUITE ENDED: " + test_classname)
                dts_log_execution(duts, tester, log_handler)
    except VerifyFailure:
        log_handler.error(" !!! DEBUG IT: " + traceback.format_exc())
    except KeyboardInterrupt:
        log_handler.error(" !!! STOPPING DCTS")
    except Exception as e:
        log_handler.error(str(e))
    finally:
        suite_obj.execute_tear_downall()


def run_all(config_file, pkgName, git, patch, skip_setup,
            read_cache, project, suite_dir, test_cases,
            base_dir, output_dir, verbose, virttype, debug,
            debugcase, commands):
    """
    Main process of DTS, it will run all test suites in the config file.
    """

    global config
    global requested_tests
    global result
    global excel_report
    global stats_report
    global log_handler
    global check_case_inst
    global support_case_inst

    # save global variable
    serializer = Serializer()

    # load check/support case lists
    check_case = parse_file()
    check_case.set_filter_case()
    check_case.set_support_case()

    # prepare the output folder
    if output_dir == '':
        output_dir = settings.FOLDERS['Output']

    if not os.path.exists(output_dir):
        os.mkdir(output_dir)

    # add python module search path
    sys.path.append(suite_dir)

    # enable debug mode
    if debug is True:
        setting.set_local_variable(settings.DEBUG_SETTING, 'yes')
    if debugcase is True:
        setting.set_local_variable(settings.DEBUG_CASE_SETTING, 'yes')

    # init log_handler handler
    if verbose is True:
        logger.set_verbose()

    logger.log_dir = output_dir
    log_handler = getLogger('dts')
    log_handler.config_execution('dts')

    # run designated test case
    requested_tests = test_cases

    # Read config file
    config = ConfigParser.SafeConfigParser()
    load_cfg = config.read(config_file)
    if len(load_cfg) == 0:
        raise ConfigParseException(config_file)

    # parse commands
    dts_commands = dts_parse_commands(commands)

    os.environ["TERM"] = "dumb"

    # change rst output folder
    rst.path2Result = output_dir

    # report objects
    excel_report = ExcelReporter(output_dir + '/test_results.xls')
    stats_report = StatsReporter(output_dir + '/statistics.txt')
    result = Result()

    crbInsts = []
    crbs_conf = CrbsConf()
    crbs = crbs_conf.load_crbs_config()

    # for all Exectuion sections
    for section in config.sections():
        dts_parse_param(section)

        # verify if the delimiter is good if the lists are vertical
        dutIPs, targets, test_suites = dts_parse_config(section)
        for dutIP in dutIPs:
            log_handler.info("\nDUT " + dutIP)

        # look up in crbs - to find the matching IP
        for dutIP in dutIPs:
            for crb in crbs:
                if crb['IP'] == dutIP:
                    crbInsts.append(crb)
                    break

        # only run on the dut in known crbs
        if len(crbInsts) == 0:
            log_handler.error(" SKIP UNKNOWN CRB")
            continue

        result.dut = dutIPs[0]

        # init dut, tester crb
        duts, tester = dts_crbs_init(crbInsts, skip_setup, read_cache, project, base_dir, serializer, virttype)

        # register exit action
        atexit.register(close_all_sessions, duts, tester)

        check_case_inst = check_case_skip(duts[0])
        support_case_inst = check_case_support(duts[0])

        # Run DUT prerequisites
        if dts_run_prerequisties(duts, tester, pkgName, patch, dts_commands, serializer) is False:
            dts_crbs_exit(duts, tester)
            continue

        dts_run_target(duts, tester, targets, test_suites)

        dts_crbs_exit(duts, tester)

    save_all_results()


def show_speedup_options_messages(read_cache, skip_setup):
    if read_cache:
        log_handler.info('CACHE: All configuration will be read from cache.')
    else:
        log_handler.info('CACHE: Cache will not be read.')

    if skip_setup:
        log_handler.info('SKIP: Skipping DPDK setup.')
    else:
        log_handler.info('SKIP: The DPDK setup steps will be executed.')


def save_all_results():
    """
    Save all result to files.
    """
    excel_report.save(result)
    stats_report.save(result)


def close_all_sessions(duts, tester):
    """
    Close session to DUT and tester.
    """
    # close all nics
    for dutobj in duts:
        if getattr(dutobj, 'ports_info', None) and dutobj.ports_info:
            for port_info in dutobj.ports_info:
                netdev = port_info['port']
                netdev.close()
        # close all session
        dutobj.close()
    if tester is not None:
        tester.close()
    log_handler.info("DTS ended")
