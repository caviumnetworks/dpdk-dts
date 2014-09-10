# <COPYRIGHT_TAG>
import logging
import os
import sys
import inspect
import re

"""
DCTS logger module with several log level. DCTS framwork and TestSuite log
will saved into different log files.
"""
logging.DCTS_DUT_CMD = logging.INFO + 1
logging.DCTS_DUT_OUTPUT = logging.DEBUG + 1
logging.DCTS_DUT_RESULT = logging.WARNING + 1

logging.DCTS_TESTER_CMD = logging.INFO + 2
logging.DCTS_TESTER_OUTPUT = logging.DEBUG + 2
logging.DCTS_TESTER_RESULT = logging.WARNING + 2

logging.SUITE_DUT_CMD = logging.INFO + 3
logging.SUITE_DUT_OUTPUT = logging.DEBUG + 3

logging.SUITE_TESTER_CMD = logging.INFO + 4
logging.SUITE_TESTER_OUTPUT = logging.DEBUG + 4

logging.DCTS_IXIA_CMD = logging.INFO + 5
logging.DCTS_IXIA_OUTPUT = logging.DEBUG + 5

logging.addLevelName(logging.DCTS_DUT_CMD, 'DCTS_DUT_CMD')
logging.addLevelName(logging.DCTS_DUT_OUTPUT, 'DCTS_DUT_OUTPUT')
logging.addLevelName(logging.DCTS_DUT_RESULT, 'DCTS_DUT_RESUTL')

logging.addLevelName(logging.DCTS_TESTER_CMD, 'DCTS_TESTER_CMD')
logging.addLevelName(logging.DCTS_TESTER_OUTPUT, 'DCTS_TESTER_OUTPUT')
logging.addLevelName(logging.DCTS_TESTER_RESULT, 'DCTS_TESTER_RESULT')

logging.addLevelName(logging.SUITE_DUT_CMD, 'SUITE_DUT_CMD')
logging.addLevelName(logging.SUITE_DUT_OUTPUT, 'SUITE_DUT_OUTPUT')

logging.addLevelName(logging.SUITE_TESTER_CMD, 'SUITE_TESTER_CMD')
logging.addLevelName(logging.SUITE_TESTER_OUTPUT, 'SUITE_TESTER_OUTPUT')

logging.addLevelName(logging.DCTS_IXIA_CMD, 'DCTS_IXIA_CMD')
logging.addLevelName(logging.DCTS_IXIA_OUTPUT, 'DCTS_IXIA_OUTPUT')

message_fmt = '%(asctime)s %(levelname)20s: %(message)s'
date_fmt = '%d/%m/%Y %H:%M:%S'
RESET_COLOR = '\033[0m'
stream_fmt = '%(color)s%(levelname)20s: %(message)s' + RESET_COLOR
log_dir = None


def RED(text):
    return "\x1B[" + "31;1m" + text + "\x1B[" + "0m"


class BaseLoggerAdapter(logging.LoggerAdapter):

    def dcts_dut_cmd(self, msg, *args, **kwargs):
        self.log(logging.DCTS_DUT_CMD, msg, *args, **kwargs)

    def dcts_dut_output(self, msg, *args, **kwargs):
        self.log(logging.DCTS_DUT_OUTPUT, msg, *args, **kwargs)

    def dcts_dut_result(self, msg, *args, **kwargs):
        self.log(logging.DCTS_DUT_RESULT, msg, *args, **kwargs)

    def dcts_tester_cmd(self, msg, *args, **kwargs):
        self.log(logging.DCTS_TESTER_CMD, msg, *args, **kwargs)

    def dcts_tester_output(self, msg, *args, **kwargs):
        self.log(logging.DCTS_TESTER_CMD, msg, *args, **kwargs)

    def dcts_tester_result(self, msg, *args, **kwargs):
        self.log(logging.DCTS_TESTER_RESULT, msg, *args, **kwargs)

    def suite_dut_cmd(self, msg, *args, **kwargs):
        self.log(logging.SUITE_DUT_CMD, msg, *args, **kwargs)

    def suite_dut_output(self, msg, *args, **kwargs):
        self.log(logging.SUITE_DUT_OUTPUT, msg, *args, **kwargs)

    def suite_tester_cmd(self, msg, *args, **kwargs):
        self.log(logging.SUITE_TESTER_CMD, msg, *args, **kwargs)

    def suite_tester_output(self, msg, *args, **kwargs):
        self.log(logging.SUITE_TESTER_OUTPUT, msg, *args, **kwargs)

    def dcts_ixia_cmd(self, msg, *args, **kwargs):
        self.log(logging.DCTS_IXIA_CMD, msg, *args, **kwargs)

    def dcts_ixia_output(self, msg, *args, **kwargs):
        self.log(logging.DCTS_IXIA_OUTPUT, msg, *args, **kwargs)


class ColorHandler(logging.StreamHandler):
    LEVEL_COLORS = {
        logging.DEBUG: '',  # SYSTEM
        logging.DCTS_DUT_OUTPUT: '\033[00;37m',  # WHITE
        logging.DCTS_TESTER_OUTPUT: '\033[00;37m',  # WHITE
        logging.SUITE_DUT_OUTPUT: '\033[00;37m',  # WHITE
        logging.SUITE_TESTER_OUTPUT: '\033[00;37m',  # WHITE
        logging.INFO: '\033[00;36m',  # CYAN
        logging.DCTS_DUT_CMD: '',  # SYSTEM
        logging.DCTS_TESTER_CMD: '',  # SYSTEM
        logging.SUITE_DUT_CMD: '',  # SYSTEM
        logging.SUITE_TESTER_CMD: '',  # SYSTEM
        logging.DCTS_IXIA_CMD: '',  # SYSTEM
        logging.DCTS_IXIA_OUTPUT: '',  # SYSTEM
        logging.WARN: '\033[01;33m',  # BOLD YELLOW
        logging.DCTS_DUT_RESULT: '\033[01;34m',  # BOLD BLUE
        logging.DCTS_TESTER_RESULT: '\033[01;34m',  # BOLD BLUE
        logging.ERROR: '\033[01;31m',  # BOLD RED
        logging.CRITICAL: '\033[01;31m',  # BOLD RED
    }

    def format(self, record):
        record.__dict__['color'] = self.LEVEL_COLORS[record.levelno]
        return logging.StreamHandler.format(self, record)


class DCTSLOG(BaseLoggerAdapter):

    """
    dcts log class for framework and testsuite
    """

    def __init__(self, logger, crb="suite"):
        global log_dir
        filename = inspect.stack()[1][1][:-3]
        self.name = filename.split('/')[-1]

        self.error_lvl = logging.ERROR
        self.warn_lvl = logging.WARNING
        self.info_lvl = logging.INFO
        self.debug_lvl = logging.DEBUG

        if log_dir is None:
            self.log_path = os.getcwd() + "/../output"
        else:
            self.log_path = log_dir    # log dir should contain tag/crb global value and mod in dcts
        self.dcts_log = "dcts.log"

        self.logger = logger
        self.logger.setLevel(logging.DEBUG)

        self.crb = crb
        super(DCTSLOG, self).__init__(self.logger, dict(crb=self.crb))

        self.fh = None
        self.ch = None

    def __log_hander(self, fh, ch):
        fh.setFormatter(logging.Formatter(message_fmt, date_fmt))
        ch.setFormatter(logging.Formatter(stream_fmt, date_fmt))

        fh.setLevel(logging.DEBUG)   # file hander default level
        ch.setLevel(logging.INFO)    # console handler default level
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)

        if self.fh is not None:
            self.logger.removeHandler(self.fh)
        if self.ch is not None:
            self.logger.removeHandler(self.ch)

        self.fh = fh
        self.ch = ch

    def warning(self, message):
        self.logger.log(self.warn_lvl, message)

    def info(self, message):
        self.logger.log(self.info_lvl, message)

    def error(self, message):
        self.logger.log(self.error_lvl, message)

    def debug(self, message):
        self.logger.log(self.debug_lvl, message)

    def set_logfile_path(self, path):
        self.log_path = path

    def set_stream_level(self, lvl):
        self.ch.setLevel(lvl)

    def set_logfile_level(self, lvl):
        self.fh.setLevel(lvl)

    def config_execution(self, crb):
        log_file = self.log_path + '/' + self.dcts_log
        fh = logging.FileHandler(log_file)
        ch = ColorHandler()
        self.__log_hander(fh, ch)

        if crb == "dut":
            self.info_lvl = logging.DCTS_DUT_CMD
            self.debug_lvl = logging.DCTS_DUT_OUTPUT
            self.warn_lvl = logging.DCTS_DUT_RESULT
        elif crb == "tester":
            self.info_lvl = logging.DCTS_TESTER_CMD
            self.debug_lvl = logging.DCTS_TESTER_OUTPUT
            self.warn_lvl = logging.DCTS_TESTER_RESULT
        elif crb == "ixia":
            self.info_lvl = logging.DCTS_IXIA_CMD
            self.debug_lvl = logging.DCTS_IXIA_OUTPUT
        else:
            self.error_lvl = logging.ERROR
            self.warn_lvl = logging.WARNING
            self.info_lvl = logging.INFO
            self.debug_lvl = logging.DEBUG

    def config_suite(self, suitename, crb=None):
        log_file = self.log_path + '/' + suitename + '.log'
        fh = logging.FileHandler(log_file)
        ch = ColorHandler()
        self.__log_hander(fh, ch)

        if crb == "dut":
            self.info_lvl = logging.SUITE_DUT_CMD
            self.debug_lvl = logging.SUITE_DUT_OUTPUT
        elif crb == "tester":
            self.info_lvl = logging.SUITE_TESTER_CMD
            self.debug_lvl = logging.SUITE_TESTER_OUTPUT
        elif crb == "ixia":
            self.info_lvl = logging.DCTS_IXIA_CMD
            self.debug_lvl = logging.DCTS_IXIA_OUTPUT

    def logger_exit(self):
        if self.fh is not None:
            self.logger.removeHandler(self.fh)
        if self.ch is not None:
            self.logger.removeHandler(self.ch)


def getLogger(name, crb="suite"):
    logger = DCTSLOG(logging.getLogger(name), crb)
    return logger


_TESTSUITE_NAME_FORMAT_PATTERN = r'TEST SUITE : (.*)'
_TESTSUITE_ENDED_FORMAT_PATTERN = r'TEST SUITE ENDED: (.*)'
_TESTCASE_NAME_FORMAT_PATTERN = r'Test Case (.*) Begin'
_TESTCASE_RESULT_FORMAT_PATTERN = r'Test Case (.*) Result (.*):'


class LogParser(object):

    def __init__(self, log_path):
        self.log_path = log_path

        try:
            self.log_handler = open(self.log_path, 'r')
        except:
            print RED("Failed to logfile %s" % log_path)
            return None

        self.suite_pattern = re.compile(_TESTSUITE_NAME_FORMAT_PATTERN)
        self.end_pattern = re.compile(_TESTSUITE_ENDED_FORMAT_PATTERN)
        self.case_pattern = re.compile(_TESTCASE_NAME_FORMAT_PATTERN)
        self.result_pattern = re.compile(_TESTCASE_RESULT_FORMAT_PATTERN)

        self.loglist = self.parse_logfile()
        self.log_handler.close()

    def locate_suite(self, suite_name=None):
        begin = 0
        end = len(self.loglist)
        for line in self.loglist:
            m = self.suite_pattern.match(line.values()[0])
            if m:
                if suite_name is None:
                    begin = self.loglist.index(line)
                elif suite_name == m.group(1):
                    begin = self.loglist.index(line)

        for line in self.loglist[begin:]:
            m = self.end_pattern.match(line.values()[0])
            if m:
                if suite_name is None:
                    end = self.loglist.index(line)
                elif suite_name == m.group(1):
                    end = self.loglist.index(line)

        return self.loglist[begin:end + 1]

    def locate_case(self, case_name=None):
        begin = 0
        end = len(self.loglist)
        for line in self.loglist:
            # only handle case log
            m = self.case_pattern.match(line.values()[0])
            if m:
                # not determine case will start from begining
                if case_name is None:
                    begin = self.loglist.index(line)
                # start from the determined case
                elif case_name == m.group(1):
                    begin = self.loglist.index(line)

        for line in self.loglist[begin:]:
            m = self.result_pattern.match(line.values()[0])
            if m:
                # not determine case will stop to the end
                if case_name is None:
                    end = self.loglist.index(line)
                # stop to the determined case
                elif case_name == m.group(1):
                    end = self.loglist.index(line)

        return self.loglist[begin:end + 1]

    def __dict_log(self, lvl_name, msg):
        tmp = {}
        if lvl_name is not '':
            tmp[lvl_name] = msg
        return tmp

    def parse_logfile(self):
        loglist = []

        out_type = 'DCTS_DUT_OUTPUT'
        for line in self.log_handler:
            tmp = {}
            line = line.replace('\n', '')
            line = line.replace('^M', '')
            m = re.match("(\d{2}/\d{2}/\d{4}) (\d{2}:\d{2}:\d{2}) (.{20}): (.*)", line)
            if m:
                lvl_name = m.group(3).strip()
                tmp = self.__dict_log(lvl_name, m.group(4))
                if "OUTPUT" in lvl_name:
                    out_type = lvl_name
            else:
                tmp[out_type] = line

            loglist.append(tmp)

        return loglist
