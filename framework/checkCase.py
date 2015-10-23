import xlrd

from settings import nic_name_from_type

filter_file = r'./conf/dpdk_test_case_checklist.xls'
filter_case = []
check_function_dict = {}
support_file = r'./conf/dpdk_support_test_case.xls'
support_case = []
support_function_dict = {}


class parse_file():

    def __init__(self):
        try:
            self.book = xlrd.open_workbook(filter_file)
            self.sheet = self.book.sheet_by_index(0)
            self.support_book = xlrd.open_workbook(support_file)
            self.support_sheet = self.support_book.sheet_by_index(0)
            self.init_check_function_dict()
            self.init_support_function_dict()
        except:
            pass

    def init_check_function_dict(self):
        '''
        init check case functio, and skip case message.
        '''
        row_data = self.sheet.row_values(0)
        for i in range(1, len(row_data)):
            if row_data[i].lower() in ['wq number', 'comments']:
                if 'message' not in check_function_dict:
                    check_function_dict['message'] = [i]
                else:
                    check_function_dict['message'].append(i)
            else:
                check_function_dict[row_data[i].lower()] = i

    def init_support_function_dict(self):
        '''
        init support case function, and skip case message.
        '''
        row_data = self.support_sheet.row_values(0)
        for i in range(1, len(row_data)):
            if row_data[i].lower() in ['wq number', 'comments']:
                if 'message' not in support_function_dict:
                    support_function_dict['message'] = [i]
                else:
                    support_function_dict['message'].append(i)
            else:
                support_function_dict[row_data[i].lower()] = i

    def set_filter_case(self):
        for row in range(self.sheet.nrows):
            row_data = self.sheet.row_values(row)
            # add case name
            tmp_filter = [row_data[0]]
            for i in range(1, len(row_data) - 2):
                tmp_filter.append(row_data[i].split(','))

            tmp_filter.append(row_data[-2])
            tmp_filter.append(row_data[-1])

            filter_case.append(tmp_filter)

    def set_support_case(self):
        for row in range(self.support_sheet.nrows):
            row_data = self.support_sheet.row_values(row)
            # add case name
            tmp_filter = [row_data[0]]
            for i in range(1, len(row_data) - 2):
                tmp_filter.append(row_data[i].split(','))

            tmp_filter.append(row_data[-2])
            tmp_filter.append(row_data[-1])

            support_case.append(tmp_filter)


class check_case_skip():

    def __init__(self, Dut):
        self.dut = Dut
        self.comments = ''

    def check_os(self, os_type):
        if 'all' == os_type[0].lower():
            return True
        dut_os_type = self.dut.get_os_type()
        if dut_os_type in os_type:
            return True
        else:
            return False

    def check_nic(self, nic_type):
        if 'all' == nic_type[0].lower():
            return True
        dut_nic_type = nic_name_from_type(self.dut.ports_info[0]['type'])
        if dut_nic_type in nic_type:
            return True
        else:
            return False

    def check_target(self, target):
        if 'all' == target[0].lower():
            return True
        if self.dut.target in target:
            return True
        else:
            return False

    def case_skip(self, case_name):
        skip_flage = False
        for rule in filter_case[1:]:
            # check case name
            if case_name == rule[0]:
                for key in check_function_dict.keys():
                    try:
                        if 'message' == key:
                            continue
                        check_function = getattr(self, 'check_%s' % key)
                    except:
                        print "can't check %s type" % key
                    if check_function(rule[check_function_dict[key]]):
                        skip_flage = True
                    else:
                        skip_flage = False
                        break

                if skip_flage:
                    if 'message' in check_function_dict:
                        for i in check_function_dict['message']:
                            self.comments += '%s,' % rule[i]
                    return skip_flage

        return skip_flage


class check_case_support(check_case_skip):

    def __init__(self, Dut):
        self.dut = Dut
        self.comments = ''

    def case_support(self, case_name):
        support_flag = True
        for rule in support_case[1:]:
            # check case name
            if case_name == rule[0]:
                for key in support_function_dict.keys():
                    try:
                        if 'message' == key:
                            continue
                        check_function = getattr(self, 'check_%s' % key)
                    except:
                        print "can't check %s type" % key
                    if check_function(rule[support_function_dict[key]]):
                        support_flag = True
                    else:
                        support_flag = False
                        break

                if support_flag is False:
                    # empty last skip case comments
                    self.comments = ''
                    if 'message' in support_function_dict:
                        for i in support_function_dict['message']:
                            self.comments += '%s,' % rule[i]
                    return support_flag

        return support_flag


class simple_dut(object):

    def __init__(self, os='', target='', nic=''):
        self.ports_info = [{}]
        self.os = os
        self.target = target
        self.ports_info[0]['type'] = nic

    def get_os_type(self):
        return self.os

if __name__ == "__main__":
    dut = simple_dut(
        os="linux", target='x86_64-native-linuxapp-gcc', nic='8086:1572')
    check_case = parse_file()
    check_case.set_filter_case()
    check_case.set_support_case()
    check_case_inst = check_case_skip(dut)
    support_case_inst = check_case_support(dut)
    print support_case_inst.case_support("l2pkt_detect")
    print support_case_inst.comments
