# -*-coding:utf-8 -*-
from __future__ import unicode_literals

import base64
import datetime
import json
import re
import shutil
import traceback
import os
import rsa
from django.core import serializers
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from Draw_Process.models import Actions
from Draw_Process.models import ProcessCopy
from Draw_Process.models import Packages
from Draw_Process.models import Store
from Draw_Process.models import TaskInformation
from Draw_Process.models import SelectInformation
from Draw_Process.models import TaskResult
from Draw_Process.models import Folder
from Draw_Process.models import AuthMessage
from Python_Platform import settings
import time
from django.utils.translation import gettext
import logging
from Draw_Process.utils import get_tasklist
from Draw_Process import transMeaning
from Draw_Process import encryption

logger = logging.getLogger('log')
pc_names = {}

#set logging format
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%m/%d/%Y %H:%M:%S %p"
fp = logging.FileHandler('log.txt', encoding='utf-8')
fs = logging.StreamHandler()
logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT, datefmt=DATE_FORMAT, handlers=[fp, fs])

def setPc(value):
    global pc_names
    pc_names = value

def xstr(s):
    if s is None:
        return ''
    else:
        return s


def excute(path,filename):
    try:
        ls = os.listdir(path)
    except Exception as e:
        logging.error(repr(e))


def generateProcessCode(username, connections, type):
    """sun13 2021-01-03
    根据用户前台定义的流程顺序及参数，生成机器人客户端执行所需要的python代码
    :param username:
    :param connections: 含流程块DIV 和 node_no
    :param type:        判断是代码视图还是直接运行的代码
    :return: 正确时返回result = {'code'="",'result'="",'username'=""}， 异常时返回result
    """
    connections = json.loads(connections)
    list = []
    step_list = []
    list2 = []
    result = {}

    try:
        num = int(connections['length'])
        startID = connections['startID']
        try:
            tab = int(connections['tab'])
        except:
            tab = None
        div_ids = {}
        for i in range(num):
            nextID = connections[startID]
            process = connections[startID + "text"]
            nodeNo = int(connections[startID + "nodeNo"])
            div_name = connections[startID + "div_name"]
            if div_name != "":
                steps = Actions.objects.filter(create_by=username, node_no=nodeNo, group=div_name,
                                                          tab=tab).exclude(function="Start").exclude(
                    function="End").values('node_no', 'function', 'variant', 'div_id', 'group', 'group_id',
                                           'group_node_no').order_by('node_no', 'group_node_no')
                for j in range(len(steps)):
                    step = steps[j]
                    div_id = step['div_id']
                    function = step['function']
                    node_no = str(step['node_no']) + "-" + str(step['group_node_no'])
                    div_ids[node_no] = div_id
                    if j == 0:
                        step_list.append(nodeNo)
                    list.append(node_no)
                    list2.append(function)
                startID = nextID
            else:
                if process == "Start":
                    startID = nextID
                    continue
                if process == "End":
                    break
                div_ids[str(nodeNo)] = startID
                step_list.append(int(nodeNo))
                list.append(str(nodeNo))
                list2.append(process)
                startID = nextID
    except Exception as e:
        logging.error(repr(e))
        exstr = str(repr(e)).replace('\n', '<br>')
        result["result"] = "error"
        result["step"] = ""
        result["msg"] = gettext("Process Error!")
        result["conso"] = exstr
        result["action"] = "run"
        result["username"] = username
        return result
    try:
        """
        增加根据node_no排序
        """
        actions = Actions.objects.filter(create_by=username, node_no__in=step_list, tab=tab).exclude(
            function="Start").exclude(function="End").values('div_id', 'node_no', 'function', 'variant', 'input',
                                                             'output', 'group', 'group_id', 'group_node_no',
                                                             'name').order_by('node_no', 'group_node_no')

        robot_execute_codes = generateRobotExecuteCode(actions,type)
        # 提取数据显示log解析器上
        # processes_dict = {}
        # num = 1
        # # process_str = ""
        # data = robot_execute_codes[::2]
        # for i in data:
        #     prcoess_dict = {}
        #     function_name = i.get('function')
        #     parameters_name = i.get('parameters')
        #     if function_name is None or parameters_name is None:
        #         continue
        #     prcoess_dict[function_name] = parameters_name
        #     processes_dict[str(num)] = prcoess_dict
        #     num +=1
        # process_str = json.dumps(processes_dict)
        # log_run_nodes = "2004>" + json.dumps(robot_execute_codes) + "<2004"
        # logging.info(log_run_nodes)

    except Exception as e:
        logging.error(repr(e))
        exstr = str(repr(e)).replace('\n', '<br>')
        result["result"] = "error"
        result["step"] = ""
        result["msg"] = gettext("Get Process Variants Error!")
        result["conso"] = exstr
        result["action"] = "run"
        result["username"] = username
        return result

    result['code'] = robot_execute_codes
    result['result'] = 'success'
    result['username'] = username
    return result


def generateRobotExecuteCode(actions,type):
    """sun13 2021-01-04
    新生成代码的逻辑, 把每行代码归集在数组中，{"line_number":0, "div_id":"", "code":""}
    """
    robot_execute_codes = []
    line_number = 0
    # 若有流程，则先生成py文件基本内容，导包及UTF-8,通过package.json去导
    with open("Draw_Process/packages.json", 'r') as load_f:
        package_dict = json.load(load_f)
        print(package_dict)
    packages = package_dict["packages"]

    # 获取functions对应包名
    with open("Draw_Process/functions.json", 'r') as load_f:
        functions = json.load(load_f)
        print(functions)

    # 判断是否views视图，如果是不显示import的包
    if type != "view":
        # import packages 完成
        for package in packages:
            line_number = line_number + 1
            robot_execute_code = {"line_number": line_number, "div_id": "", "code": package + "\n"}
            robot_execute_codes.append(robot_execute_code)
    blank_space_num = 0  # py文件空格的占位符
    for action in actions:
        # 保证各种情况流程都能保存
        try:
            print(action)
            # 获取 div_id, function, variant, output
            robot_div_id = action["div_id"]
            robot_function = action["function"]
            robot_output = action["output"]
            # 保存时空值带来的问题，先做法是忽略
            robot_group_id = action["group_id"]
            try:
                robot_variant_dict = json.loads(action["variant"])
                robot_variant_dict["divId"] = '"' + robot_div_id + '"'
                if robot_group_id:
                    robot_variant_dict["groupId"] = '"' + robot_group_id + '"'
                else:
                    robot_variant_dict["groupId"] = '"' + '"'
            except Exception as e:
                continue
            robot_node_no = action["node_no"]
            step_description = action["name"]
            if step_description is None:
                step_description = ""

            blank_space_str = get_blank_space(blank_space_num)
            # 定义单行代码内容
            one_line_code = ""

            """
            增加代码注释，逻辑是功能块名称和步骤名称,退格提前判断
            """
            function_array = ["End_If", "Exit_W", "Exit_For", "Else_If", "Else"]
            if robot_group_id is not None:
                robot_index = "Sub process no: " + str(robot_node_no) + " "
            else:
                robot_group_id = ""
                robot_index = "node_no: " + str(robot_node_no) + " "
            # 如果是代码视图，注释更改颜色
            if robot_function in function_array:
                comments = get_blank_space(blank_space_num - 4) + "# " + robot_index + gettext(
                    robot_function) + ": " + step_description + "\n"
            else:
                comments = blank_space_str + "# " + robot_index + gettext(
                    robot_function) + ": " + step_description + "\n"
            if type == "view":
                comments = "<span style='color:#708090'>" + comments + "</span>"
            line_number = line_number + 1
            robot_execute_comments = {"line_number": line_number, "div_id": robot_div_id, "code": comments,
                                      "function": robot_function, "parameters": robot_variant_dict,
                                      "group_id": robot_group_id}
            robot_execute_codes.append(robot_execute_comments)

            # robot_function 获取功能模块类
            model_name = functions[robot_function]

            if robot_function == "Print_Variant":
                self_variant = robot_variant_dict["self_variant"]
                self_variant = transMeaning.trans_slash(self_variant, "yes")
                if type != "view":
                    one_line_code = blank_space_str + "exec(General_Module.Print_Variant(divId=" + '"' + robot_div_id + '"' + ",groupId=" + '"' + robot_group_id + '"' + ",self_variant='" + str(self_variant) + ": '+str(" + str(self_variant) + ")))\n"
                else:
                    one_line_code = blank_space_str + "General_Module.Print_Variant(<span style='color:#D2691E'>" + self_variant + "</span>)\n"

            if robot_function == "Custom_Variant":
                self_variant = robot_variant_dict["self_variant"]
                self_variant = transMeaning.trans_slash(self_variant, "yes")
                if type != "view":
                    one_line_code = blank_space_str + "exec(General_Module.CustomVariant(divId=" + '"' + robot_div_id + '"' + ",groupId=" + '"' + robot_group_id + '"' + ",self_variant=" + 'r\"\"\"' + str(self_variant) + ' \"\"\"' + "))\n"
                    # one_line_code = blank_space_str + "exec(General_Module.CustomVariant(divId=" + '"' + robot_div_id + '"' + ",groupId=" + '"' + robot_group_id + '"' + ",self_variant=" + 'r\"\"\"' + str(self_variant) + ' \"\"\"' + "))\n"
                else:
                    one_line_code = blank_space_str + "<span style='color:#D2691E'>" + self_variant + "</span>\n"

            if robot_function == "Set_Password":
                if type != "view":
                    one_line_code = blank_space_str + robot_output + " = " + "General_Module.SetPassword(divId=" + '"' + robot_div_id + '"' + ",groupId=" + '"' + robot_group_id + '"' + ",choclead_p=" + "\"" + robot_variant_dict["choclead_p"] + "\"" + ")\n"
                else:
                    pwd = ""
                    for i in range(len(robot_variant_dict["choclead_p"])):
                        pwd = pwd + "*"
                    one_line_code = blank_space_str + "<span style='color:#D2691E'>" + robot_output + " = " + pwd + "</span>\n"

            # 增加引号，考虑换行符的问题
            if robot_function == "Python_Code":
                self_code = robot_variant_dict["self_code"].replace("\n","\\n")
                if type != "view":
                    one_line_code = blank_space_str + "SelfDevelopment_Module.Python_Code(divId=" + '"' + robot_div_id + '"' + ",groupId=" + '"' + robot_group_id + '"' + ",self_code=" + "\"" + self_code + "\"" + ")\n"
                else:
                    one_line_code = blank_space_str + "SelfDevelopment_Module.Python_Code(<span style='color:#FFA500'>self_code</span>=" + "\"" + self_code + "\"" + ")\n"
            """
            py文件增加空格的情况, 一般用于代码语法结构
            TODO try / except / continue
            """
            if robot_function == "If":
                if type != "view":
                    one_line_code = blank_space_str + "if eval(MainFunction_Module.CustomIf(divId=" + '"' + robot_div_id + '"' + ",groupId=" + '"' + robot_group_id + '"' + ",condition=" + '\"\"\" ' + \
                                    robot_variant_dict["if_condition"] + ' \"\"\"' + ")):\n"
                # 代码视图将变量更改颜色
                else:
                    one_line_code = blank_space_str + "if eval(MainFunction_Module.CustomIf(" + "<span style='color:#D2691E'>" + \
                                    robot_variant_dict["if_condition"] + "</span>" + ")):\n"
                blank_space_num = blank_space_num + 4
            if robot_function == "Else_If":
                blank_space_num = blank_space_num - 4
                blank_space_str = get_blank_space(blank_space_num)
                if type != "view":
                    one_line_code = blank_space_str + "elif eval(MainFunction_Module.CustomElseIf(divId=" + '"' + robot_div_id + '"' + ",groupId=" + '"' + robot_group_id + '"' + ",condition=" + '\"\"\" ' + \
                                    robot_variant_dict["if_condition"] + ' \"\"\"' + ")):\n"
                # 代码视图将变量更改颜色
                else:
                    one_line_code = blank_space_str + "elif eval(MainFunction_Module.CustomElseIf(" + "<span style='color:#D2691E'>" + \
                                    robot_variant_dict["if_condition"] + "</span>" + ")):\n"
                blank_space_num = blank_space_num + 4
            if robot_function == "Else":
                blank_space_num = blank_space_num - 4
                blank_space_str = get_blank_space(blank_space_num)
                one_line_code = blank_space_str + "else:\n"
                blank_space_num = blank_space_num + 4
            if robot_function == "For":
                for_range = robot_variant_dict["for_range"]
                for_variant = robot_variant_dict["for_variant"]
                try:
                    for_range = eval(for_range)
                except Exception as e:
                    print("Can not eval")
                initial_value = robot_variant_dict["initial_value"]
                for_step = robot_variant_dict["for_step"]
                # 拼接案例：s3 = 'Hello {name1}! My name is {name2}.'.format(name1='World', name2='Python猫')
                # 如果是代码视图则不转换变量，否则进行转换，防止客户端语法错误无法传输id等参数
                if type != "view":
                    initial_value = '\"\"\" ' + str(initial_value) + ' \"\"\"'
                    for_range = '\"\"\" ' + str(for_range) + ' \"\"\"'
                    for_step = '\"\"\" ' + str(for_step) + ' \"\"\"'
                    one_line_code = blank_space_str + "for {for_variant} in ".format(for_variant=for_variant) + "eval(MainFunction_Module.CustomFor(divId=" + '"' + robot_div_id + '"' + ",groupId=" + '"' + robot_group_id + '"' + ",initial_value=" + str(initial_value) + ",for_range=" + str(for_range) + ",for_step=" + str(for_step) + ")):\n"
                # 代码视图调整参数颜色
                else:
                    one_line_code = blank_space_str + "for {for_variant} in ".format(for_variant=for_variant) + "eval(MainFunction_Module.CustomFor(<span style='color:#FFA500'>initial_value</span>=" + "<span style='color:#D2691E'>" + str(initial_value) + "</span>,<span style='color:#FFA500'>for_range</span>=" + "<span style='color:#D2691E'>" + str(for_range) + "</span>,<span style='color:#FFA500'>for_step</span>=" + "<span style='color:#D2691E'>" + str(for_step) + "</span>)):\n"
                blank_space_num = blank_space_num + 4
            if robot_function == "While":
                if type != "view":
                    if robot_group_id == None:
                        robot_group_id = ""
                    one_line_code = blank_space_str + "while eval(MainFunction_Module.CustomWhile(divId=" + '"' + robot_div_id + '"' + ",groupId=" + '"' + robot_group_id + '"' + ",condition=" + '\"\"\" ' + robot_variant_dict["while_condition"] + ' \"\"\"' + ")):\n"
                # 代码视图将变量更改颜色
                else:
                    one_line_code = blank_space_str + "while eval(MainFunction_Module.CustomWhile(<span style='color:#FFA500'>" + robot_variant_dict["while_condition"] + "</span>" + ")):\n"
                blank_space_num = blank_space_num + 4
            if robot_function == "End_If" or robot_function == "Exit_W" or robot_function == "Exit_For" or robot_function == "End_Try":
                blank_space_num = blank_space_num - 4
                one_line_code = "\n"
            if robot_function == "Break":
                one_line_code = blank_space_str + "break\n"
            if robot_function == "Continue":
                one_line_code = blank_space_str + "continue\n"
            if robot_function == "Try":
                blank_space_str = get_blank_space(blank_space_num)
                one_line_code = blank_space_str + "try:\n"
                blank_space_num = blank_space_num + 4
            if robot_function == "Except":
                blank_space_num = blank_space_num - 4
                blank_space_str = get_blank_space(blank_space_num)
                one_line_code = blank_space_str + "except:\n"
                blank_space_num = blank_space_num + 4
            if robot_function == "Finally":
                blank_space_num = blank_space_num - 4
                blank_space_str = get_blank_space(blank_space_num)
                one_line_code = blank_space_str + "finally:\n"
                blank_space_num = blank_space_num + 4
            """
            通用模块功能：
            """
            if one_line_code == "":
                one_line_code = generateOneLineProcessCode(model_name, robot_function, robot_variant_dict, type)
                # 含output逻辑
                if robot_output is not None:
                    if robot_output != "":
                        one_line_code = blank_space_str + robot_output + " = " + one_line_code
                    else:
                        one_line_code = blank_space_str + one_line_code
                else:
                    one_line_code = blank_space_str + one_line_code
                if "?" in robot_function:
                    if_function = robot_function.replace("?", "")
                    one_line_code = one_line_code.replace(robot_function, if_function)
                    # one_line_code = "if " + one_line_code.replace("\n", ":\n")
                    # blank_space_num = blank_space_num + 4
            line_number = line_number + 1
            robot_execute_code = {"line_number": line_number, "div_id": robot_div_id, "code": one_line_code,
                                  "function": robot_function, "parameters": robot_variant_dict, "group_id": robot_group_id}
            robot_execute_codes.append(robot_execute_code)
        except Exception as e:
            print(str(e))
            continue

    return robot_execute_codes


def generateOneLineProcessCode(model_name="", robot_function="", robot_variant_dict={}, type=""):
    """sun13 2021-01-04
    根据用户前台定义的单个流程块的功能及参数，生成一行执行代码
    决定尊重原著，取消（）是变量的概念
    :param model_name: (String) 例：SAP_Model/EXCEL_Model
    :param robot_function: (String) 流程块功能
    :param robot_variant_dict: (Dict) 参数字典
    :param type: 判断是代码视图还是运行代码
    :return one_line_code (String)
    """
    one_line_code = model_name + "." + robot_function + "("
    items = robot_variant_dict.items()
    for key, value in items:
        # excel图表更新数据源下拉选项仅用于储存，不做传输
        if key == "chart_series_options":
            continue
        elif key == "pivot_options":
            continue
        # 批量替换转义
        # value 如果是数组的情况，目前只有SAP_TEXT,SAP_PRESS
        if isinstance(value, list):
            temp_value = ""
            for i in range(0, len(value)):
                if i == len(value) - 1:
                    temp_value = temp_value + value[i]
                    break
                temp_value = temp_value + value[i] + ","
                print(temp_value)
            value = "[{temp_value}]".format(temp_value=temp_value)
            print(value)
        # General动作如果是control_handle/control_h_show参数不走\逻辑
        if key == "control_handle" or key == "control_h_show":
            if "General_Click" in robot_function or "General_Input" in robot_function or "General_Exist" in robot_function or "General_GetText" in robot_function:
                pass
            else:
                value = str(transMeaning.trans_slash(str(value), "yes"))
        elif key == "shot_coordinate_base64" or key == "shot_coordinate_base64_show":
            if "Picture_Shot_Coordinate" in robot_function in robot_function:
                pass
            else:
                value = str(transMeaning.trans_slash(str(value), "yes"))
        else:
            value = str(transMeaning.trans_slash(str(value), "yes"))
        # 代码视图增加颜色
        if type == "view":
            if key != "divId" and key != "groupId":
                one_line_code = one_line_code + "<span style='color:#FFA500'>" + key + "</span>" + "=" + "<span style='color:#D2691E'>" + value + "</span>" + ","
        else:
            one_line_code = one_line_code + key + "=" + value + ","
        #one_line_code = one_line_code + key + "=" + value + ","
    one_line_code = one_line_code + ")" + "\n"
    return one_line_code


def count_char(string):
    """
    计算字符出现的次数，主要用于统计()用
    :param string:
    :return:
    """
    char_count_dict = {}
    for i in string:
        char_count_dict[i] = char_count_dict.get(i, 0) + 1
    return char_count_dict


def get_blank_space(num=4):
    """
    空格占位符的计算
    :param num: 空格的个数
    :return:
    """
    blank_space_str = ""
    if num > 0:
        for i in range(0, num):
            blank_space_str = blank_space_str + " "
    return blank_space_str


def generateViewCode(username, connections):
    """
    调用生成代码的逻辑，显示代码视图
    :param username:
    :param connections:
    :return: 返回前台代码文本
    """
    updated_table_action(username, connections)
    code = ""
    result = generateProcessCode(username, connections, "view")
    # 如果generateProcessCode报错了，直接返回同样的错误
    if result["result"] == "error":
        return result
    codes = result['code']
    for single in codes:
        # 为了在前台显示空格，因为是四个空格缩进
        code = code + single["code"].replace("    ", "\t")
    view_code = {"code": code, "result": "success", "username": username}
    return view_code


def updated_table_action(username, connections):
    try:
        connections = json.loads(connections)
        num = int(connections['length'])
        startID = connections['startID']
        try:
            tab = int(connections['tab'])
        except:
            tab = None
        ids = []
        for i in range(num):
            try:
                nextID = connections[startID]
                process = connections[nextID + "text"]
                nodeNo = int(connections[nextID + "nodeNo"])
                if process == "End":
                    break
                Actions.objects.filter(div_id=nextID, create_by=username.lower(), tab=tab).update(node_no=nodeNo)
                Actions.objects.filter(group_id=nextID, create_by=username.lower(), tab=tab).update(node_no=nodeNo)
                ids.append(nextID)
                startID = nextID
            except:
                continue
        ids_sql = Actions.objects.filter(create_by=username.lower(), tab=tab).values('div_id', 'group_id')
        for id_json in ids_sql:
            id = id_json['div_id']
            group_id = id_json['group_id']
            if id not in ids:
                if group_id not in ids:
                    Actions.objects.filter(div_id=id, tab=tab).update(node_no=None)
        result = {}
        result["result"] = "success"
    except:
        result["result"] = "failed"

# def generateProcessCode(username,connections):
#     connections = json.loads(connections)
#     list = []
#     step_list = []
#     list2 = []
#     action_json = {}
#     result = {}
#     try:
#         num = int(connections['length'])
#         startID = connections['startID']
#         try:
#             tab = int(connections['tab'])
#         except:
#             tab = None
#         div_ids = {}
#         div_names = {}
#         for i in range(num):
#             nextID = connections[startID]
#             process = connections[startID + "text"]
#             nodeNo = int(connections[startID + "nodeNo"])
#             div_name = connections[startID + "div_name"]
#             if div_name != "":
#                 steps = Actions.objects.distinct().filter(create_by=username, node_no=nodeNo, group=div_name,
#                                                           tab=tab).exclude(function="Start").exclude(
#                     function="End").values('node_no', 'function', 'variant', 'div_id', 'group', 'group_id',
#                                            'group_node_no').order_by('node_no', 'group_node_no')
#                 for j in range(len(steps)):
#                     step = steps[j]
#                     div_id = step['div_id']
#                     function = step['function']
#                     node_no = str(step['node_no']) + "-" + str(step['group_node_no'])
#                     div_ids[node_no] = div_id
#                     if j == 0:
#                         step_list.append(nodeNo)
#                     list.append(node_no)
#                     list2.append(function)
#                 startID = nextID
#             else:
#                 if process == "Start":
#                     startID = nextID
#                     continue
#                 if process == "End":
#                     break
#                 div_ids[str(nodeNo)] = startID
#                 step_list.append(int(nodeNo))
#                 list.append(str(nodeNo))
#                 list2.append(process)
#                 startID = nextID
#     except Exception as e:
#         logging.error(repr(e))
#         exstr = str(repr(e)).replace('\n', '<br>')
#         result["result"] = "error"
#         result["step"] = ""
#         result["msg"] = gettext("Process Error!")
#         result["conso"] = exstr
#         result["action"] = "run"
#         result["username"] = username
#         return result
#     try:
#         actions = Actions.objects.distinct().filter(create_by=username, node_no__in=step_list, tab=tab).exclude(
#             function="Start").exclude(function="End").values('node_no', 'function', 'variant', 'input', 'output',
#                                                              'group', 'group_id', 'group_node_no')
#         for action in actions:
#             function_json = {}
#             nodeNo = str(action['node_no'])
#             function = action['function']
#             variants_json = action['variant']
#             input = action['input']
#             output = action['output']
#             group = action['group']
#             groupID = action['group_id']
#             groupNodeNo = action['group_node_no']
#             if group is not None and group != "":
#                 nodeNo = str(nodeNo) + "-" + str(groupNodeNo)
#             function_json['function'] = function
#             function_json['input'] = input
#             function_json['output'] = output
#             function_json['divID'] = div_ids[str(nodeNo)]
#             try:
#                 variants = json.loads(variants_json)
#             except:
#                 variants = {}
#             items = variants.items()
#             for key, value in items:
#                 function_json[str(key)] = str(value)
#             action_json[nodeNo] = function_json
#         mappings = Packages.objects.distinct().filter(function__in=list2)
#         mappings_list = serializers.serialize('json', mappings)
#         mappings_array = json.loads(mappings_list)
#         filter_result = []
#         now = str(int(time.time()))
#         replace_variant = "no"
#         for_variant2str = ""
#         for_repalce_variant = ""
#         robot_code = ""
#     except Exception as e:
#         logging.error(repr(e))
#         exstr = str(repr(e)).replace('\n', '<br>')
#         result["result"] = "error"
#         result["step"] = ""
#         result["msg"] = gettext("Get Process Variants Error!")
#         result["conso"] = exstr
#         result["action"] = "run"
#         result["username"] = username
#         return result
#     try:
#         reuse_browser = 'no'
#         import_packages = []
#         start = "\t"
#         robot_code = robot_code + "#coding:utf-8" + '\n'
#         for mapping in mappings_array:
#             packages = mapping['fields']['package']
#             function = mapping['fields']['function']
#             if function == "Reuse_Browser":
#                 reuse_browser = 'yes'
#             packages_array = packages.split(";")
#             for package in packages_array:
#                 if package != "" and package not in import_packages:
#                     robot_code = robot_code + package + '\n'
#                     import_packages.append(package)
#         robot_code = robot_code + 'import win32gui' + '\n'
#         robot_code = robot_code + 'import traceback' + '\n'
#         robot_code = robot_code + 'import json' + '\n'
#         robot_code = robot_code + 'from Lbt.ChocLeadException.Error import CustomError as CustomError' + '\n'
#         robot_code = robot_code + 'from Lbt.ChocLeadException import getId as getId' + '\n'
#         robot_code = robot_code + '\n'
#         if reuse_browser == 'yes':
#             robot_code = robot_code + 'class ReuseChrome(Remote):' + '\n'
#             robot_code = robot_code + '\t' + "def __init__(self, command_executor, session_id):" + '\n'
#             robot_code = robot_code + '\t\t' + "self.r_session_id = session_id" + '\n'
#             robot_code = robot_code + '\t\t' + "Remote.__init__(self, command_executor=command_executor, desired_capabilities={})" + '\n\n'
#             robot_code = robot_code + '\t' + "def start_session(self, capabilities, browser_profile=None):" + '\n'
#             robot_code = robot_code + '\t\t' + "if not isinstance(capabilities, dict):" + '\n'
#             robot_code = robot_code + '\t\t\t' + "raise InvalidArgumentException('Capabilities must be a dictionary')" + '\n'
#             robot_code = robot_code + '\t\t' + "if browser_profile:" + '\n'
#             robot_code = robot_code + '\t\t\t' + "if 'moz:firefoxOptions' in capabilities:" + '\n'
#             robot_code = robot_code + '\t\t\t\t' + 'capabilities["moz:firefoxOptions"]["profile"] = browser_profile.encoded' + '\n'
#             robot_code = robot_code + '\t\t\t' + "else:" + '\n'
#             robot_code = robot_code + '\t\t\t\t' + "capabilities.update({'firefox_profile': browser_profile.encoded})" + '\n\n'
#             robot_code = robot_code + '\t\t' + "self.capabilities = options.Options().to_capabilities()" + '\n'
#             robot_code = robot_code + '\t\t' + "self.session_id = self.r_session_id" + '\n'
#             robot_code = robot_code + '\t\t' + "self.w3c = False" + '\n\n'
#         robot_code = robot_code + 'class test():' + '\n'
#         robot_code = robot_code + '\t' + "def __init__(self):" + '\n'
#         robot_code = robot_code + '\t\t' + "self.hwnd_title = dict()" + '\n\n'
#         robot_code = robot_code + '\t' + "def get_all_hwnd(self,hwnd,mouse):" + '\n'
#         robot_code = robot_code + '\t\t' + "if win32gui.IsWindow(hwnd) and win32gui.IsWindowEnabled(hwnd) and win32gui.IsWindowVisible(hwnd):" + '\n'
#         robot_code = robot_code + '\t\t\t' + "self.hwnd_title.update({hwnd:win32gui.GetWindowText(hwnd)})" + '\n\n'
#         robot_code = robot_code + '\t' + 'def get_hwnd(self,title):' + '\n'
#         robot_code = robot_code + '\t\t' + "win32gui.EnumWindows(self.get_all_hwnd, 0)" + '\n'
#         robot_code = robot_code + '\t\t' + "for h, t in self.hwnd_title.items():" + '\n'
#         robot_code = robot_code + '\t\t\t' + "if t is not '':" + '\n'
#         robot_code = robot_code + '\t\t\t\t' + "if title in t:" + '\n'
#         robot_code = robot_code + '\t\t\t\t\t' + "try:" + '\n'
#         robot_code = robot_code + '\t\t\t\t\t\t' + "left, top, right, bottom = win32gui.GetWindowRect(h)" + '\n'
#         robot_code = robot_code + '\t\t\t\t\t\t' + "return h" + '\n'
#         robot_code = robot_code + '\t\t\t\t\t' + "except:" + '\n'
#         robot_code = robot_code + '\t\t\t\t\t\t' + "continue" + '\n\n'
#         robot_code = robot_code + '\t' + 'def column_to_name(self,num):' + '\n'
#         robot_code = robot_code + '\t\t' + "if not isinstance(num, int):" + '\n'
#         robot_code = robot_code + '\t\t\t' + "return num" + '\n'
#         robot_code = robot_code + '\t\t' + "tStr = str()" + '\n'
#         robot_code = robot_code + '\t\t' + "while num != 0:" + '\n'
#         robot_code = robot_code + '\t\t\t' + "res = num % 26" + '\n'
#         robot_code = robot_code + '\t\t\t' + "if res == 0:" + '\n'
#         robot_code = robot_code + '\t\t\t\t' + "res = 26" + '\n'
#         robot_code = robot_code + '\t\t\t\t' + "num -= 26" + '\n'
#         robot_code = robot_code + '\t\t\t' + "tStr = chr(ord('A') + res - 1) + tStr" + '\n'
#         robot_code = robot_code + '\t\t\t' + "num = num // 26" + '\n'
#         robot_code = robot_code + '\t\t' + "return tStr" + '\n\n'
#         packages_json = {}
#         get_all_hwnd = "no"
#         for mapping in mappings_array:
#             function = mapping['fields']['function']
#             if function == "Excel_Format":
#                 robot_code = robot_code + '\t' + 'def rgb_to_hex(self,r,g,b):' + '\n'
#                 robot_code = robot_code + '\t\t' + "bgr = (b,g,r)" + '\n'
#                 robot_code = robot_code + '\t\t' + "strValue = '%02x%02x%02x' % bgr" + '\n'
#                 robot_code = robot_code + '\t\t' + "iValue = int(strValue, 16)" + '\n'
#                 robot_code = robot_code + '\t\t' + "return iValue" + '\n'
#                 robot_code = robot_code + '\n'
#             elif function == "Web_StartBrowser":
#                 robot_code = robot_code + '\t' + "def close_alert_and_get_its_text(self):" + '\n'
#                 robot_code = robot_code + '\t\t' + "try:" + '\n'
#                 robot_code = robot_code + '\t\t\t' + "alert = self.driver.switch_to_alert()" + '\n'
#                 robot_code = robot_code + '\t\t\t' + "alert_text = alert.text" + '\n'
#                 robot_code = robot_code + '\t\t\t' + "if self.accept_next_alert:" + '\n'
#                 robot_code = robot_code + '\t\t\t\t' + "alert.accept()" + '\n'
#                 robot_code = robot_code + '\t\t\t' + "else:" + '\n'
#                 robot_code = robot_code + '\t\t\t\t' + "alert.dismiss()" + '\n'
#                 robot_code = robot_code + '\t\t\t' + "return alert_text" + '\n'
#                 robot_code = robot_code + '\t\t' + "finally: self.accept_next_alert = True" + '\n\n'
#                 robot_code = robot_code + '\t' + 'def tearDown(self):' + '\n'
#                 robot_code = robot_code + '\t\t' + 'self.driver.quit()' + '\n'
#                 robot_code = robot_code + '\t\t' + 'self.assertEqual([], self.verificationErrors)' + '\n\n'
#             elif function == "Screen_Shot":
#                 if get_all_hwnd == "no":
#                     robot_code = robot_code + '\t' + "def __init__(self):" + '\n'
#                     robot_code = robot_code + '\t\t' + "self.hwnd_title = dict()" + '\n\n'
#                     robot_code = robot_code + '\t' + "def get_all_hwnd(self,hwnd,mouse):" + '\n'
#                     robot_code = robot_code + '\t\t' + "if win32gui.IsWindow(hwnd) and win32gui.IsWindowEnabled(hwnd) and win32gui.IsWindowVisible(hwnd):" + '\n'
#                     robot_code = robot_code + '\t\t\t' + "self.hwnd_title.update({hwnd:win32gui.GetWindowText(hwnd)})" + '\n\n'
#                 robot_code = robot_code + '\t' + "def window_capture(self,hwnd,filename):" + '\n'
#                 robot_code = robot_code + '\t\t' + "hwndDC = win32gui.GetWindowDC(hwnd)" + '\n'
#                 robot_code = robot_code + '\t\t' + "mfcDC = win32ui.CreateDCFromHandle(hwndDC)" + '\n'
#                 robot_code = robot_code + '\t\t' + "saveDC = mfcDC.CreateCompatibleDC()" + '\n'
#                 robot_code = robot_code + '\t\t' + "saveBitMap = win32ui.CreateBitmap()" + '\n'
#                 robot_code = robot_code + '\t\t' + "MoniterDev = win32api.EnumDisplayMonitors(None, None)" + '\n'
#                 robot_code = robot_code + '\t\t' + "w = MoniterDev[0][2][2]" + '\n'
#                 robot_code = robot_code + '\t\t' + "h = MoniterDev[0][2][3]" + '\n'
#                 robot_code = robot_code + '\t\t' + "saveBitMap.CreateCompatibleBitmap(mfcDC, w, h)" + '\n'
#                 robot_code = robot_code + '\t\t' + "saveDC.SelectObject(saveBitMap)" + '\n'
#                 robot_code = robot_code + '\t\t' + "saveDC.BitBlt((0, 0), (w, h), mfcDC, (0, 0), win32con.SRCCOPY)" + '\n'
#                 robot_code = robot_code + '\t\t' + "saveBitMap.SaveBitmapFile(saveDC, filename)" + '\n'
#                 robot_code = robot_code + '\t\t' + "win32gui.DeleteObject(saveBitMap.GetHandle())" + '\n'
#                 robot_code = robot_code + '\t\t' + "saveDC.DeleteDC()" + '\n'
#                 robot_code = robot_code + '\t\t' + "mfcDC.DeleteDC()" + '\n'
#                 robot_code = robot_code + '\t\t' + "win32gui.ReleaseDC(hwnd, hwndDC)" + '\n\n'
#                 get_all_hwnd = "yes"
#         for mapping in mappings_array:
#             function = mapping['fields']['function']
#             codes = mapping['fields']['codes'] + mapping['fields']['codes_1'] + mapping['fields']['codes_2'] + \
#                     mapping['fields']['codes_3'] + mapping['fields']['codes_4'] + mapping['fields']['codes_5'] + \
#                     mapping['fields']['codes_6']
#             packages_json[function] = codes
#         run_function = []
#         startdef = "no"
#         for i in range(len(list)):
#             nodeNo = str(list[i])
#             function = action_json[nodeNo]['function']
#             if function != "Define" and startdef == "no":
#                 robot_code = robot_code + '\t' + 'def run(self):' + '\n'
#                 startdef = "yes"
#                 robot_code = robot_code + '\t\t' + 'try:' + '\n'
#                 start = "\t\t\t"
#             elif function == "End_Def":
#                 startdef = "no"
#             elif function == "Define":
#                 startdef = "yes"
#             if function == "Excel_Filter":
#                 column_num = action_json[nodeNo]['column_num']
#                 filter_condition = action_json[nodeNo]['filter_condition']
#                 filter_column = 0
#                 for j in range(len(column_num)):
#                     character = column_num[j]
#                     filter_column = filter_column + (ord(character) - 64) * (
#                             26 ** (len(column_num) - j - 1))
#                 condition = "Field=" + str(filter_column) + ","
#                 num = 1
#                 if "and" in filter_condition:
#                     strs = filter_condition.split("and")
#                     for m in range(len(strs)):
#                         str_and = strs[m]
#                         if "or" in str_and:
#                             strs_or = str_and.split("or")
#                             for n in range(len(strs_or)):
#                                 str_or = strs_or[n]
#                                 cri = "Criteria" + str(num)
#                                 num += 1
#                                 if n == len(strs_or) - 1:
#                                     condition = condition + cri + "=" + '"' + str_or.replace(" ", "") + '"'
#                                 else:
#                                     condition = condition + cri + "=" + '"' + str_or.replace(" ",
#                                                                                              "") + '"' + "," + 'Operator=2' + ","
#                         else:
#                             cri = "Criteria" + str(num)
#                             num += 1
#                             if m == len(strs) - 1:
#                                 condition = condition + cri + "=" + '"' + str_and.replace(" ", "") + '"'
#                             else:
#                                 condition = condition + cri + "=" + '"' + str_and.replace(" ",
#                                                                                           "") + '"' + "," + 'Operator=1' + ","
#                 elif "or" in filter_condition:
#                     strs = filter_condition.split("or")
#                     for x in range(len(strs)):
#                         str_or = strs[x]
#                         cri = "Criteria" + str(num)
#                         num += 1
#                         if x == len(strs) - 1:
#                             condition = condition + cri + "=" + '"' + str_or.replace(" ", "") + '"'
#                         else:
#                             condition = condition + cri + "=" + '"' + str_or.replace(" ",
#                                                                                      "") + '"' + "," + 'Operator=2' + ","
#                 else:
#                     try:
#                         filter_type = eval(action_json[nodeNo]['filter_type'])
#                     except:
#                         filter_type = 7
#                     if filter_type == 7:
#                         if "," in filter_condition:
#                             filter_condition_list = filter_condition.split(",")
#                             filter_condition_2_str = "["
#                             for filter_i in range(len(filter_condition_list)):
#                                 if filter_i == len(filter_condition_list) - 1:
#                                     filter_condition_2_str = filter_condition_2_str + "'" + \
#                                                              filter_condition_list[filter_i] + "'"
#                                 else:
#                                     filter_condition_2_str = filter_condition_2_str + "'" + \
#                                                              filter_condition_list[filter_i] + "'" + ","
#                             filter_condition_2_str = filter_condition_2_str + "]"
#                             condition = condition + "Criteria1" + "=" + filter_condition_2_str + ",Operator = 7"
#                         else:
#                             condition = condition + "Criteria1" + "=" + '"' + filter_condition + '"'
#                     else:
#                         try:
#                             filter_type = eval(action_json[nodeNo]['filter_type'])
#                         except:
#                             filter_type = 7
#                         if filter_type == 7:
#                             condition = condition + "Criteria1" + "=" + '"' + filter_condition + '"'
#                         else:
#                             condition = condition + "Criteria1" + "=" + filter_condition + ",Operator = " + str(
#                                 filter_type)
#                 action_json[nodeNo]['condition'] = condition
#             elif function == "Excel_Top10":
#                 column_num = action_json[nodeNo]['column_num']
#                 filter_column = 0
#                 for j in range(len(column_num)):
#                     character = column_num[j]
#                     filter_column = filter_column + (ord(character) - 64) * (26 ** (len(column_num) - j - 1))
#                 action_json[nodeNo]['column_num'] = filter_column
#             codes = packages_json[function]
#             if function == "For":
#                 replace_variant = "yes"
#                 for_variant2json = action_json[nodeNo]
#                 for_variant = for_variant2json['for_variant']
#                 for_type = for_variant2json['for_type']
#                 if for_type == "string":
#                     for_variant2str = '" + str(' + for_variant + ') + "'
#                 else:
#                     for_variant2str = for_variant
#                 for_repalce_variant = "(" + for_variant + ")"
#             elif function == "Exit_For":
#                 replace_variant = "no"
#             if function == "Excle_Filter" and function in run_function:
#                 codes = codes.replace("workbook.AutoFilter = False;", "")
#             run_function.append(function)
#             if function == "Send_Mail":
#                 codes = codes.replace('if ";"', 'if ","')
#                 codes = codes.replace("split(';')", "split(',')")
#             codes_array = codes.split(";")
#             items = action_json[nodeNo].items()
#             try:
#                 replace_slash = action_json[nodeNo]['replace_slash']
#             except:
#                 replace_slash = "yes"
#             for code in codes_array:
#                 if "SQL" in function:
#                     if "Microsoft Access Driver (*.mdb,*.accdb)}-DBQ=" in code:
#                         code = code.replace("-", ";")
#                 if function == "Send_Mail":
#                     code = code.replace('if ","', 'if ";"')
#                     code = code.replace("split(',')", "split(';')")
#                 if "endif" in code or "endwhile" in code or "endfor" in code or "endwith" in code or "endtry" in code:
#                     start = start.replace('\t', '', 1)
#                     continue
#                 elif "elif" in code or "else" in code or "except" in code:
#                     start = start.replace('\t', '', 1)
#                 elif code == "":
#                     continue
#                 for key, value in items:
#                     if key == "output" and value == "":
#                         value = "output"
#                     if key in code:  # 代码串中含有参数数据的键，就把代码表中的键换成参数数据的值
#                         code = code.replace(key, str(value))
#                         if replace_slash == "yes":
#                             if "path" in key:
#                                 if "\\" not in key:
#                                     code = code.replace('/', '\\')
#                                     code = code.replace('\\', '\\\\')
#                             elif "content =" in code and "\\" not in code:
#                                 code = code.replace('/', '\\')
#                                 code = code.replace('\\', '\\\\')
#                             elif "content =" in code and "\\" in code and "content = r" not in code:
#                                 code = code.replace('content = ', 'content = r')
#                             elif "send_var =" in code and "\\" not in code:
#                                 code = code.replace('/', '\\')
#                                 code = code.replace('\\', '\\\\')
#                             elif "send_var =" in code and "\\" in code and "send_var = r" not in code:
#                                 code = code.replace('send_var = ', 'send_var = r')
#                             elif "send_var =" in code and "\\" in code and "send_var = r" not in code:
#                                 code = code.replace('send_var = ', 'send_var = r')
#                             #break
#                 code = code.replace('blank', '\t')
#                 if function == "Define" and ",fun_variant" in code:
#                     code = code.replace(",fun_variant", "")
#                 if replace_variant == "yes" and function != "For":
#                     if for_repalce_variant in code:
#                         code = code.replace(for_repalce_variant, for_variant2str)
#                     else:
#                         try:
#                             replace_for = "(" + str(for_variant)
#                             position = code.find(replace_for)
#                             string2 = code[position:]
#                             string3 = string2.replace(replace_for, "")
#                             if string3[0:1] == " " or string3[0:1] == "+" or string3[0:1] == "-" or string3[
#                                                                                                     0:1] == "*" or string3[
#                                                                                                                    0:1] == "//":
#                                 position2 = string2.find(")")
#                                 string4 = string2[0:position2 + 1]
#                                 string5 = string2[0:position2].replace(replace_for, "")
#                                 code = code.replace(string4, '" + str(' + for_variant + string5 + ') + "')
#                         except Exception:
#                             code = code.replace(for_repalce_variant, for_variant2str)
#                 robot_code = robot_code + start + code + '\n'
#                 code_check = code[0:6]
#                 if "if" in code_check or "while" in code_check or "for" in code_check or "elif" in code_check or "else" in code_check or "try" in code_check or "except" in code_check or "with" in code_check:
#                     start = start + '\t'
#         robot_code = robot_code + '\t\t\t' + 'return {"result":"success"}' + '\n'
#         robot_code = robot_code + '\t\t' + 'except CustomError as e:' + '\n'
#         robot_code = robot_code + '\t\t\t' + """error_msg = e.errorInfo.replace("'", '"')""" + '\n'
#         robot_code = robot_code + '\t\t\t' + 'error_json = json.loads(error_msg)' + '\n'
#         robot_code = robot_code + '\t\t\t' + 'return error_json' + '\n'
#         robot_code = robot_code + '\t\t' + 'except Exception as e:' + '\n'
#         robot_code = robot_code + '\t\t\t' + 'lineNum = e.__traceback__.tb_lineno' + '\n'
#         robot_code = robot_code + '\t\t\t' + 'try:' + '\n'
#         robot_code = robot_code + '\t\t\t\t' + 'divId = getId()' + '\n'
#         robot_code = robot_code + '\t\t\t' + 'except:' + '\n'
#         robot_code = robot_code + '\t\t\t\t' + 'divId = ""' + '\n'
#         robot_code = robot_code + '\t\t\t' + 'return {"result": "error", "step":divId, "msg":"", "lineNum": lineNum, "conso": str(e)}'
#         result['code'] = robot_code
#         result['result'] = 'success'
#         result['username'] = username
#     except Exception as e:
#         logging.error(repr(e))
#         exstr = str(repr(e)).replace('\n', '<br>')
#         result["result"] = "error"
#         result["step"] = ""
#         result["msg"] = gettext("Generate Codes Error!")
#         result["conso"] = exstr
#         result["action"] = "run"
#         result['username'] = username
#         return result
#     return result
#
# def generateViewCode(username,connections):
#     connections = json.loads(connections)
#     list = []
#     step_list = []
#     step_json = {}
#     list2 = []
#     action_json = {}
#     result = {}
#     try:
#         num = int(connections['length'])
#         startID = connections['startID']
#         try:
#             tab = int(connections['tab'])
#         except:
#             tab = None
#         div_ids = {}
#         div_names = {}
#         node_sequecne = 1
#         for i in range(num):
#             nextID = connections[startID]
#             process = connections[startID + "text"]
#             nodeNo = int(connections[startID + "nodeNo"])
#             div_name = connections[startID + "div_name"]
#             if div_name != "":
#                 steps = Actions.objects.distinct().filter(create_by=username, group_id=startID, group=div_name,
#                                                           tab=tab).exclude(function="Start").exclude(
#                     function="End").values('node_no', 'function', 'variant', 'div_id', 'group', 'group_id',
#                                            'group_node_no').order_by('node_no', 'group_node_no')
#                 for j in range(len(steps)):
#                     step = steps[j]
#                     div_id = step['div_id']
#                     step_list.append(div_id)
#                     function = step['function']
#                     group_node_no = step['node_no']
#                     if group_node_no == "" or group_node_no == None or nodeNo == 'None':
#                         group_node_no = node_sequecne
#                     node_no = str(group_node_no) + "-" + str(step['group_node_no'])
#                     step_json[div_id] = node_no
#                     div_ids[node_no] = div_id
#                     list.append(node_no)
#                     list2.append(function)
#                 startID = nextID
#             else:
#                 if process == "Start":
#                     startID = nextID
#                     node_sequecne += 1
#                     continue
#                 if process == "End":
#                     break
#                 step_json[startID] = nodeNo
#                 div_ids[str(nodeNo)] = startID
#                 step_list.append(startID)
#                 list.append(str(nodeNo))
#                 list2.append(process)
#                 startID = nextID
#                 node_sequecne += 1
#     except Exception as e:
#         logging.error(repr(e))
#         exstr = str(repr(e)).replace('\n', '<br>')
#         result["result"] = "error"
#         result["step"] = ""
#         result["msg"] = gettext("Process Error!")
#         result["conso"] = exstr
#         result["username"] = username
#         return JsonResponse(result)
#     try:
#         actions = Actions.objects.distinct().filter(create_by=username, div_id__in=step_list, tab=tab).exclude(
#             function="Start").exclude(function="End").values('div_id', 'node_no', 'function', 'variant', 'input', 'output',
#                                                              'group', 'group_id', 'group_node_no')
#         for action in actions:
#             function_json = {}
#             divId = str(action['div_id'])
#             nodeNo = str(action['node_no'])
#             if nodeNo == "" or nodeNo == None or nodeNo == 'None':
#                 nodeNo = step_json[divId]
#             function = action['function']
#             variants_json = action['variant']
#             input = action['input']
#             output = action['output']
#             function_json['function'] = function
#             function_json['input'] = input
#             function_json['output'] = output
#             function_json['divID'] = div_ids[str(nodeNo)]
#             try:
#                 variants = json.loads(variants_json)
#             except:
#                 variants = {}
#             items = variants.items()
#             for key, value in items:
#                 function_json[str(key)] = str(value)
#             action_json[str(nodeNo)] = function_json
#         replace_variant = "no"
#         for_variant2str = ""
#         for_repalce_variant = ""
#         robot_code = ""
#     except Exception as e:
#         logging.error(repr(e))
#         exstr = str(repr(e)).replace('\n', '<br>')
#         result["result"] = "error"
#         result["step"] = ""
#         result["msg"] = gettext("Get Process Variants Error!")
#         result["conso"] = exstr
#         result["username"] = username
#         return result
#     try:
#         start = "\t"
#         robot_code = "<font color='blue'>#The following code is not complete and is for reference only</font>" + '\n\n'
#         codefile = os.path.dirname(os.path.realpath(__file__)) + "\\code.json"
#         with open(codefile,'r', encoding='utf-8') as f:
#             data = f.readlines()
#         code_text = ""
#         for line in data:
#             code_text+=line
#         code_json = json.loads(code_text)
#         run_function = []
#         startdef = "no"
#         for i in range(len(list)):
#             nodeNo = str(list[i])
#             function = action_json[nodeNo]['function']
#             if function != "Define" and startdef == "no":
#                 robot_code = robot_code + 'def run():' + '\n'
#                 startdef = "yes"
#                 start = "\t"
#             elif function == "End_Def":
#                 startdef = "no"
#             elif function == "Define":
#                 startdef = "yes"
#             codes = code_json[function]
#             if function == "For":
#                 replace_variant = "yes"
#                 for_variant2json = action_json[nodeNo]
#                 for_variant = for_variant2json['for_variant']
#                 for_type = for_variant2json['for_type']
#                 if for_type == "string":
#                     for_variant2str = '" + str(' + for_variant + ') + "'
#                 else:
#                     for_variant2str = for_variant
#                 for_repalce_variant = "(" + for_variant + ")"
#             elif function == "Exit_For":
#                 replace_variant = "no"
#             if function == "Excel_Filter" and function in run_function:
#                 codes = codes.replace("workbook.AutoFilter = False;", "")
#             run_function.append(function)
#             if function == "Send_Mail":
#                 codes = codes.replace('if ";"', 'if ","')
#                 codes = codes.replace("split(';')", "split(',')")
#             codes_array = codes.split(";")
#             items = action_json[nodeNo].items()
#             try:
#                 replace_slash = action_json[nodeNo]['replace_slash']
#             except:
#                 replace_slash = "yes"
#             for code in codes_array:
#                 if "SQL" in function:
#                     if "Microsoft Access Driver (*.mdb,*.accdb)}-DBQ=" in code:
#                         code = code.replace("-", ";")
#                 if function == "Send_Mail":
#                     code = code.replace('if ","', 'if ";"')
#                     code = code.replace("split(',')", "split(';')")
#                 if "endif" in code or "endwhile" in code or "endfor" in code or "endwith" in code or "endtry" in code:
#                     start = start.replace('\t', '', 1)
#                     continue
#                 elif "elif" in code or "else" in code or "except" in code:
#                     start = start.replace('\t', '', 1)
#                 elif code == "":
#                     continue
#                 for key, value in items:
#                     if key == "output" and value == "":
#                         value = "output"
#                     if key in code:  # 代码串中含有参数数据的键，就把代码表中的键换成参数数据的值
#                         code = code.replace(key, '<font color="blue">' + str(value) + '</font>')
#                 code = code.replace('blank', '\t')
#                 if function == "Define" and ",fun_variant" in code:
#                     code = code.replace(",fun_variant", "")
#                 if replace_variant == "yes" and function != "For":
#                     if for_repalce_variant in code:
#                         code = code.replace(for_repalce_variant, for_variant2str)
#                     else:
#                         try:
#                             replace_for = "(" + str(for_variant)
#                             position = code.find(replace_for)
#                             string2 = code[position:]
#                             string3 = string2.replace(replace_for, "")
#                             if string3[0:1] == " " or string3[0:1] == "+" or string3[0:1] == "-" or string3[
#                                                                                                     0:1] == "*" or string3[
#                                                                                                                    0:1] == "//":
#                                 position2 = string2.find(")")
#                                 string4 = string2[0:position2 + 1]
#                                 string5 = string2[0:position2].replace(replace_for, "")
#                                 code = code.replace(string4, '" + str(' + for_variant + string5 + ') + "')
#                         except Exception:
#                             code = code.replace(for_repalce_variant, for_variant2str)
#                 robot_code = robot_code + start + code + '\n'
#                 code_check = code[0:6]
#                 if "if" in code_check or "while" in code_check or "for" in code_check or "elif" in code_check or "else" in code_check or "try" in code_check or "except" in code_check or "with" in code_check:
#                     start = start + '\t'
#         robot_code = robot_code + '\t' + 'return {"result":"success"}'
#         result['code'] = robot_code
#         result['result'] = 'success'
#         result['username'] = username
#     except Exception as e:
#         logging.error(repr(e))
#         exstr = str(repr(e)).replace('\n', '<br>')
#         result["result"] = "error"
#         result["step"] = ""
#         result["msg"] = gettext("Generate Codes Error!")
#         result["conso"] = exstr
#         result['username'] = username
#         return result
#     return result

def licenseCheck(request):
    if 'username' in request.session and 'password' in request.session:
        try:
            username = request.session['username']
            pemPath = ""
            timePath = ""
            setting_file = settings.File_Root + "\\Draw_Process" + "\\setting.txt"
            with open(setting_file, 'r', encoding='utf-8') as ff:
                setting_content = ff.readlines()
                for i in range(len(setting_content)):
                    setting_list = setting_content[i].rstrip("\n").split("=")
                    if 'pem' in setting_list[0]:
                        pemPath = settings.File_Root + "\\Draw_Process\\" + setting_list[1].replace(" ", "")
                    elif 'time' in setting_list[0]:
                        timePath = settings.File_Root + "\\Draw_Process\\" + setting_list[1].replace(" ", "")
            if pemPath != "" and timePath != "":
                with open(pemPath, 'rb') as privatefile:
                    p = privatefile.read()
                privkey = rsa.PrivateKey.load_pkcs1(p)
                with open(timePath, 'rb') as ff:
                    content = ff.read()
                nowtime = datetime.datetime.now()
                message1 = base64.b64decode(content)
                message2 = rsa.decrypt(message1, privkey)
                message3 = str(message2, encoding="utf-8")
                message_list = message3.split(",")
                end_time_str = message_list[2].replace("Endtime:", "")
                end_time = datetime.datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S")
                # 检查用户账号的license date
                try:
                    licence_date = AuthMessage.objects.filter(username=username).values("licence_date")[0][
                        "licence_date"]
                    if licence_date:
                        licence_date_time = datetime.datetime.strptime(str(licence_date) + " 00:00:00",
                                                                       "%Y-%m-%d %H:%M:%S")
                        if licence_date_time < end_time:
                            end_time = licence_date_time
                except Exception:
                    pass
                diff_days = (end_time - nowtime).days
                if diff_days < 0:
                    msg = gettext("Your software has expired, please contact your administrator!")
                    logging.warning(msg)
                    request.session.flush()
            else:
                msg = gettext("Lost encrypted file, please contact your administrator!")
                logging.warning(msg)
                request.session.flush()
        except Exception as e:
            logging.error(str(e))
            msg = gettext("Lost encrypted file, please contact your administrator!")
            logging.warning(msg)
            request.session.flush()
    else:
        request.session.flush()

@csrf_exempt
def getalerts(request):
    if 'username' in request.session and 'password' in request.session:
        username = request.session['username']
        booked_tasks = TaskInformation.objects.all().filter(create_by=username).values('pc_name','task_name','duration','booked_time').order_by('booked_time')
        booked_tasks_list = []
        for i in range(len(booked_tasks)):
            booked_json = {}
            booked_json['pc_name'] = booked_tasks[i]['pc_name']
            booked_json['task_name'] = booked_tasks[i]['task_name']
            duration = booked_tasks[i]['duration']
            h = int(duration.split(":")[0])
            m = int(duration.split(":")[1])
            s = int(duration.split(":")[2])
            if h > 0:
                if m > 0:
                    duration = str(h + round(m / 60, 2)) + "h"
                else:
                    duration = str(h) + "h"
            else:
                if m > 0:
                    if s > 0:
                        duration = str(m + round(s / 60, 2)) + "min"
                    else:
                        duration = str(m) + "min"
                else:
                    duration = str(s) + "s"
            booked_json['duration'] = duration
            booked_json['booked_time'] = booked_tasks[i]['booked_time'].strftime("%Y-%m-%d %H:%M:%S")
            booked_tasks_list.append(booked_json)
        finished_tasks = TaskResult.objects.all().filter(create_by=username,status='unread').values('id','task_name','result','end_time').order_by('end_time')
        finished_tasks_list = []
        for j in range(len(finished_tasks)):
            finished_json = {}
            finished_json['id'] = finished_tasks[j]['id']
            finished_json['task_name'] = finished_tasks[j]['task_name']
            finished_json['result'] = finished_tasks[j]['result']
            finished_json['end_time1'] = finished_tasks[j]['end_time'].strftime("%H:%M")
            finished_json['end_time2'] = finished_tasks[j]['end_time'].strftime("%Y-%m-%d %H:%M")
            finished_tasks_list.append(finished_json)
        return JsonResponse({"booked_tasks": booked_tasks_list,"finished_tasks": finished_tasks_list})
    else:
        return render(request, "login.html")





#expire
@csrf_exempt
def before(request):
    if 'username' in request.session and 'password' in request.session:
        if request.method == 'POST':
            username = request.session['username']
            inputs = request.POST.getlist('browser_input[]')
            result = {}
            rows = []
            if inputs is not None:
                for i in range(len(inputs)):
                    input_json = {}
                    input = inputs[i]
                    actions = Actions.objects.filter(create_by=username, div_id=input).values('variant')
                    for action in actions:
                        variants = action['variant']
                        variants_json = json.loads(variants)
                        items = variants_json.items()
                        for key, value in items:
                            input_json[str(key)] = str(value)
                        input_json['id'] = str(input)
                    rows.append(input_json)
            result["rows"] = rows
            return JsonResponse(result)
    else:
        return render(request, "login.html")

#get code of view code page
@csrf_exempt
def getCodes(request):
    path = os.path.dirname(os.path.realpath(__file__)) + "\\temporary\\"
    if 'username' in request.session and 'password' in request.session:
        result_json = {}
        result = []
        try:
            username = request.session['username']
            connections = request.POST.get('connections')
            general_result = generateViewCode(username, connections)
            status = general_result['result']
            if status == 'success':
                codes = general_result['code']
                data = codes.split("\n")
                ini_line = 1
                for content in data:
                    content_json = {}
                    content_json['id'] = ini_line
                    con_adj = content.replace('\t', '&nbsp;&nbsp;&nbsp;&nbsp;').replace('\n', '')
                    #去掉最后一个空行
                    if con_adj:
                        content_json['code'] = con_adj
                        result.append(content_json)
                        ini_line += 1
                result_json['code'] = 0
                result_json['msg'] = ''
                result_json['count'] = ini_line
                result_json['data'] = result
            else:
                content_json = {}
                content_json['id'] = 1
                try:
                    step = general_result['step']
                except:
                    step = ""
                content_json['code'] = "Error Step: " + step
                result.append(content_json)
                ini_line = 2
                try:
                    conso = general_result['conso']
                except:
                    conso = ""
                conso_list = conso.split("\n")
                for content in conso_list:
                    conso_content_json = {}
                    conso_content_json['id'] = ini_line
                    con_adj = content.replace('\t', '&nbsp;&nbsp;&nbsp;&nbsp;').replace('\n', '')
                    conso_content_json['code'] = con_adj
                    result.append(conso_content_json)
                    ini_line += 1
                result_json['code'] = 0
                result_json['msg'] = ''
                result_json['count'] = ini_line
                result_json['data'] = result
        except Exception as e:
            logging.error(repr(e))
            content_list = str(repr(e)).split("\n")
            ini_line = 1
            for content in content_list:
                content_json = {}
                content_json['id'] = ini_line
                con_adj = content.replace('\t', '&nbsp;&nbsp;&nbsp;&nbsp;').replace('\n', '')
                content_json['code'] = con_adj
                result.append(content_json)
                ini_line += 1
            result_json['code'] = 0
            result_json['msg'] = ''
            result_json['count'] = ini_line
            result_json['data'] = result
        return JsonResponse(result_json)
    else:
        return render(request, "login.html")

#get user_input function and organize variable descriptions and variable names
@csrf_exempt
def getvars(request):
    if 'username' in request.session and 'password' in request.session:
        if request.method == 'POST':
            username = request.session['username']
            variants = request.POST.getlist('variant[]')
            var_length = 0
            var_max_length = 0
            for i in range(len(variants)):
                variant = variants[i]
                variant_json2 = {}
                variant_json2['variant_value'] = request.POST.get(variant)
                actions = Actions.objects.filter(create_by=username, div_id=variant).values('variant')
                for action in actions:
                    variants_json = action['variant']
                    variants2 = json.loads(variants_json)
                    items = variants2.items()
                    for key, value in items:
                        if key == "input_name":
                            if "," in value:
                                values = value.split(",")
                                var_length += len(values)
                                for s in values:
                                    if var_max_length < len(s):
                                        var_max_length = len(s)
                                else:
                                    pass
                            else:
                                var_length += 1
                                var_max_length = len(value)
            return JsonResponse({"vars":var_length,"var_max_length":var_max_length})
    else:
        return render(request, "login.html")

#update the result of user_input to database
@csrf_exempt
def changevariant(request):
    if 'username' in request.session and 'password' in request.session:
        if request.method == 'POST':
            username = request.session['username']
            variants = request.POST.getlist('variant[]')
            for i in range(len(variants)):
                variant = variants[i]
                variant_json2 = {}
                value_list = []
                variant_json2['variant_value'] = request.POST.get(variant)
                actions = Actions.objects.filter(create_by=username, div_id=variant).values('output','variant')
                for action in actions:
                    output = action['output']
                    variants_json = action['variant']
                    variants2 = json.loads(variants_json)
                    items = variants2.items()
                    for key, value in items:
                        if str(key) != "variant_value":
                            variant_json2[str(key)] = str(value)
                if len(variant_json2['variant_value'].split(",")) <= 1:
                    pass
                else:
                    for j in variant_json2['variant_value'].split(","):
                            value_list.append(j)
                            variant_json2['variant_value'] = value_list
                variant_json_2_str = json.dumps(variant_json2)
                Actions.objects.filter(create_by=username, div_id=variant).update(variant=variant_json_2_str,output=output)
            result = {}
            result["result"] = "success"
            return JsonResponse(result)
    else:
        return render(request, "login.html")

#save current process and adjust the correct sequecne
@csrf_exempt
def saveConnection(request):
    licenseCheck(request)
    if 'username' in request.session and 'password' in request.session:
        if request.method == 'POST':
            try:
                username = request.session['username']
                num = int(request.POST.get('length'))
                startID = request.POST.get('startID')
                try:
                    tab = int(request.POST.get('tab'))
                except:
                    tab = None
                ids = []
                for i in range(num):
                    try:
                        nextID = request.POST.get(startID)
                        process = request.POST.get(nextID + "text")
                        nodeNo = int(request.POST.get(nextID + "nodeNo"))
                        if process == "End":
                            break
                        Actions.objects.filter(div_id=nextID, create_by=username.lower(), tab=tab).update(node_no=nodeNo)
                        Actions.objects.filter(group_id=nextID, create_by=username.lower(), tab=tab).update(node_no=nodeNo)
                        ids.append(nextID)
                        startID = nextID
                    except:
                        continue
                ids_sql = Actions.objects.filter(create_by=username.lower(), tab=tab).values('div_id', 'group_id')
                for id_json in ids_sql:
                    id = id_json['div_id']
                    group_id = id_json['group_id']
                    if id not in ids:
                        if group_id not in ids:
                            Actions.objects.filter(div_id=id, tab=tab).update(node_no=None)
                result = {}
                result["result"] = "success"
            except:
                result["result"] = "failed"
            return JsonResponse(result)
    else:
        return HttpResponse("\"system exit\"")



#organize the python code from packages table based on the process
@csrf_exempt
def getRobotCode(request):
    if 'username' in request.session and 'password' in request.session:
        if request.method == 'POST':
            username = request.session['username']
            connections = request.POST.get('connections')
            result = generateProcessCode(username,connections,"run")
            return JsonResponse(result)
    else:
        return render(request, "login.html")

@csrf_exempt
def createFolder(request):
    if 'username' in request.session and 'password' in request.session:
        if request.method == 'POST':
            json = {}
            username = request.session['username']
            fileName = request.POST.get("name")
            judge = os.path.exists(os.path.dirname(os.path.realpath(__file__)) + "\\pyfile\\" + fileName)
            if judge == False:
                try:
                    filePath = os.path.dirname(os.path.realpath(__file__)) + "\\pyfile\\" + fileName
                    os.mkdir(filePath)
                    now_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    Folder.objects.create(folder=fileName, create_on=now_time, create_by=username)
                    json['result'] = "success"
                except Exception as e:
                    json['result'] = "failed"
                    json['msg'] = str(e)
            else:
                json['result'] = "failed"
                json['msg'] = gettext("This folder already exists!")
            return JsonResponse(json)
    else:
        return render(request, "login.html")

#judge if the file exists, if so, return overwrite reminder. Otherwise, create the file
@csrf_exempt
def fileJudge(request):
    if 'username' in request.session and 'password' in request.session:
        if request.method == 'POST':
            json = {}
            username = request.session['username']
            language = request.session['language']
            fileName = request.POST.get("name")
            type = request.POST.get("type")
            try:
                tab = int(request.POST.get("tab"))
            except:
                tab = None
            try:
                mode = request.POST.get("mode")
            except:
                mode = ""
            judge = os.path.exists(os.path.dirname(os.path.realpath(__file__)) + "\\pyfile\\" + fileName)
            if type == "folder" and judge == False:
                try:
                    filePath = os.path.dirname(os.path.realpath(__file__)) + "\\pyfile\\" + fileName
                    os.mkdir(filePath)
                    now_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    Folder.objects.create(folder=fileName, create_on=now_time, create_by=username)
                    json['operation'] = "success"
                except Exception:
                    json['operation'] = "failed"
            creater = ""
            creaters = Store.objects.distinct().filter(file_name=fileName).values('create_by')
            for i in range(len(creaters)):
                creater = creaters[i]['create_by']
                break
            if creater != "" and creater.lower() != username.lower():
                json['msg'] = gettext("You can not overwrite other's process!")
            else:
                if mode == "":
                    try:
                        num = int(request.POST.get('length'))
                        startID = request.POST.get('startID')
                        ids = []
                        for i in range(num):
                            try:
                                nextID = request.POST.get(startID)
                                process = request.POST.get(nextID + "text")
                                nodeNo = int(request.POST.get(nextID + "nodeNo"))
                                if process == "End":
                                    break
                                Actions.objects.filter(div_id=nextID, create_by=username.lower(), tab=tab).update(node_no=nodeNo)
                                Actions.objects.filter(group_id=nextID, create_by=username.lower(), tab=tab).update(node_no=nodeNo)
                                ids.append(nextID)
                                startID = nextID
                            except:
                                continue
                        ids_sql = Actions.objects.filter(create_by=username.lower(),tab=tab).values('div_id', 'group_id')
                        for id_json in ids_sql:
                            id = id_json['div_id']
                            group_id = id_json['group_id']
                            if id not in ids:
                                if group_id not in ids:
                                    Actions.objects.filter(div_id=id).update(node_no=None)
                        json['msg'] = "success"
                    except Exception:
                        json['msg'] = "success"
                else:
                    json['msg'] = "success"
            json['result'] = judge
            return JsonResponse(json)
    else:
        return render(request, "login.html")

@csrf_exempt
def releaseJudge(request):
    if 'username' in request.session and 'password' in request.session:
        if request.method == 'POST':
            json = {}
            username = request.session['username']
            type = request.POST.get("type")
            fileName = request.POST.get("name")
            filePath = os.path.dirname(os.path.realpath(__file__))+ "\\pyfile\\"
            file_name = filePath + fileName
            judge = os.path.exists(file_name)
            if type == "folder" and judge == False:
                try:
                    os.mkdir(file_name)
                    now_time = datetime.datetime.now()
                    Folder.objects.create(folder=fileName, create_on=now_time, create_by=username)
                    json['operation'] = "success"
                except Exception:
                    json['operation'] = "failed"
            json['result'] = judge
            return JsonResponse(json)
    else:
        return render(request, "login.html")

#copy the public data from store table to relase data in store table and copy the public file to the released path
@csrf_exempt
def releaseCopy(request):
    if 'username' in request.session and 'password' in request.session:
        if request.method == 'POST':
            username = request.session['username']
            org_file = request.POST.get("org_file")
            new_folder = request.POST.get("new_folder")
            copy_file = request.POST.get("copy_file").replace("\\\\","\\")
            copy = request.POST.get("copy")
            # 日志埋点
            log_release = {}
            log_release["action"] = "release process"
            try:
                log_release["computer name"] = pc_names[username.lower()]
            except:
                pass
            log_release_username =username
            log_release_time =time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
            log_release_org_file = org_file
            log_release_copy_file = copy_file
            log_release["username"] = log_release_username
            log_release["time"] = log_release_time
            log_release["original path"] = log_release_org_file
            log_release["release path"] = log_release_copy_file
            log_release_json = "360>" + json.dumps(log_release)
            logger.info(log_release_json)
            if copy == "yes":
                Store.objects.filter(file_name=copy_file).delete()
            org_dict = Store.objects.all().filter(file_name=org_file)
            org_array = []
            org_array = serializers.serialize('json', org_dict)
            org_list = json.loads(org_array)
            workList = []
            for i in range(len(org_list)):
                mapping = org_list[i]['fields']
                type = 'release'
                file_name = copy_file
                node_no = mapping["node_no"]
                source_id = mapping["source_id"]
                target_id = mapping["target_id"]
                source_type = mapping["source_type"]
                target_type = mapping["target_type"]
                jnode_class = mapping["jnode_class"]
                jnode = mapping["jnode"]
                jnode_html = mapping["jnode_html"]
                left = mapping["left"]
                top = mapping["top"]
                name = mapping["name"]
                input = mapping["input"]
                output = mapping["output"]
                variant = mapping["variant"]
                public_variant = mapping["public_variant"]
                create_on = datetime.datetime.now()
                create_by = username
                group = mapping["group"]
                group_id = mapping["group_id"]
                group_node_no = mapping["group_node_no"]
                group_node_name = mapping["group_node_name"]
                group_source_type = mapping["group_source_type"]
                group_target_type = mapping["group_target_type"]
                group_left = mapping["group_left"]
                group_top = mapping["group_top"]
                version = mapping["version"]
                status = mapping["status"]
                workList.append(
                    Store(type=type, file_name=file_name, node_no=node_no, source_id=source_id, target_id=target_id,
                            source_type=source_type, target_type=target_type, jnode_class=jnode_class,
                            jnode=jnode, jnode_html=jnode_html, left=left, top=top, name=name,input=input, output=output,
                            variant=variant, public_variant=public_variant, create_on=create_on, create_by=create_by,
                            group=group, group_id=group_id, group_node_no=group_node_no, group_node_name=group_node_name,
                            group_source_type=group_source_type, group_target_type=group_target_type,
                            group_left=group_left, group_top=group_top, version=version, status=status))
            Store.objects.bulk_create(workList)
            if copy == "no":
                copy_file = os.path.dirname(os.path.realpath(__file__)) + "\\pyfile\\" + copy_file
                if os.path.exists(copy_file):
                    return JsonResponse({"result":True})
                else:
                    result = {"result": False}
                    try:
                        org_file = os.path.dirname(os.path.realpath(__file__)) + "\\pyfile\\" + org_file
                        new_folder = os.path.dirname(os.path.realpath(__file__)) + "\\pyfile\\" + new_folder
                        shutil.copy(org_file, new_folder)
                        result['operation'] = "success"
                    except:
                        result['operation'] = "failed"
            else:
                result = {"result":False}
                try:
                    org_file = os.path.dirname(os.path.realpath(__file__)) + "\\pyfile\\" + org_file
                    new_folder = os.path.dirname(os.path.realpath(__file__)) + "\\pyfile\\" + new_folder
                    shutil.copy(org_file, new_folder)
                    result['operation'] = "success"
                except:
                    result['operation'] = "failed"
            return JsonResponse(result)
    else:
        return render(request, "login.html")

#expire
@csrf_exempt
def showVariant(request):
    if 'username' in request.session and 'password' in request.session:
        if request.method == 'POST':
            result = {}
            username = request.session['username']
            nodeName = request.POST.get("function")
            nodeNo = request.POST.get("nodeNo")
            id = request.POST.get("id")
            type = request.POST.get("type")
            groupID = request.POST.get("groupID")
            groupName = request.POST.get("groupName")
            processName = request.POST.get("processName")
            selectInformations = SelectInformation.objects.distinct().filter(choose=1).values('function','variant','value')
            information_json = {}
            infromation_list = []
            for selectInformation in selectInformations:
                function = selectInformation['function']
                variant = selectInformation['variant']
                value = selectInformation['value']
                information_json[function+"-"+variant]=value
                infromation_list.append(function+"-"+variant)
            if type == "1":
                sql_result = Store.objects.filter(file_name=groupName,source_id=id).values('jnode_html', 'public_variant', 'variant', 'input', 'output', 'name', 'create_by')
            elif type == "2":
                sql_result = Store.objects.filter(file_name=processName,source_id=groupID,group_id=id).values('jnode_html', 'public_variant', 'variant', 'input', 'output', 'name', 'create_by')
            else:
                sql_result = Actions.objects.filter(div_id=id,group_id=groupID,create_by=username).values('function', 'public_variant', 'variant', 'input', 'output', 'name', 'create_by')
            try:
                result['input'] = sql_result[0]['input']
                result['output'] = sql_result[0]['output']
                result['name'] = sql_result[0]['name']
                create_by = sql_result[0]['create_by']
                try:
                    function = sql_result[0]['function']
                except:
                    try:
                        function = sql_result[0]["jnode_html"].split(">")[1]
                        function = function.split("<")[0]
                    except:
                        function = sql_result[0]["jnode_html"].replace("<span>", "").replace("</span>", "")
                list = []
                public_variant = sql_result[0]['public_variant']
                public_variants = json.loads(public_variant)
                items = public_variants.items()
                for key, value in items:
                    list.append(key)
                result['list'] = list
                variant = sql_result[0]['variant']
                variants = json.loads(variant)
                items = variants.items()
                for key, value in items:
                    if create_by.lower() != username.lower():
                        if key in list:
                            select_inf = function + "-" + str(key)
                            if select_inf in infromation_list:
                                result[str(key)] = information_json[select_inf]
                            else:
                                result[str(key)] = ""
                        else:
                            result[str(key)] = str(value)
                    else:
                        result[str(key)] = str(value)
            except:
                result['input'] = ""
                result['output'] = ""
                result['variant'] = ""
                result['name'] = ""
                result['list'] = ""
            return JsonResponse(result)
    else:
        return render(request, "login.html")

#显示节点的属性
@csrf_exempt
def sortVariant(request):
    licenseCheck(request)
    if 'username' in request.session and 'password' in request.session:
        if request.method == 'POST':
            result = {}
            username = request.session['username']
            nodeName = request.POST.get("function")
            nodeNo = request.POST.get("nodeNo")
            id = request.POST.get("id")
            sql_result = Actions.objects.filter(div_id=id,function=nodeName,create_by=username).values('public_variant','variant','input','output','name')
            try:
                result['input'] = sql_result[0]['input']
                result['output'] = sql_result[0]['output']
                result['name'] = sql_result[0]['name']
                variant = sql_result[0]['variant']
                print(str(variant))
                variants = json.loads(variant)
                items = variants.items()
                for key, value in items:
                    result[str(key)] = str(value)
                list = []
                public_variant = sql_result[0]['public_variant']
                public_variants = json.loads(public_variant)
                items = public_variants.items()
                for key, value in items:
                    list.append(key)
                result['list'] = list
            except:
                result['input'] = ""
                result['output'] = ""
                result['variant'] = ""
                # 之前能获取到name，这里又清空掉了，增加了判断，有内容就不清空了
                if "name" in result.keys():
                    pass
                else:
                    result['name'] = ""
                result['list'] = ""
            return JsonResponse(result)
    else:
        return HttpResponse("\"system exit\"")


#delete node of process
@csrf_exempt
def deleteVariant(request):
    if 'username' in request.session and 'password' in request.session:
        if request.method == 'POST':
            username = request.session['username']
            nodeName = request.POST.get("name")
            nodeNo = request.POST.get("nodeNo")
            id = request.POST.get("divId")
            if id is None:
                Actions.objects.filter(node_no=nodeNo, create_by=username).delete()
                return render(request, "index.html")
            else:
                Actions.objects.filter(div_id=id,create_by=username).delete()
                Actions.objects.filter(group_id=id,create_by=username).delete()
            return render(request, "index.html")
    else:
        return render(request, "login.html")

#delete node of process
@csrf_exempt
def batchDelete(request):
    if 'username' in request.session and 'password' in request.session:
        if request.method == 'POST':
            try:
                username = request.session['username']
                delete_list = request.POST.get('delete_list')
                tab = int(request.POST.get('tab'))
                try:
                    list = json.loads(delete_list)
                except:
                    list = []
                Actions.objects.filter(div_id__in=list,create_by=username,tab=tab).delete()
                result = {"result": "success"}
            except Exception as e:
                logging.error(str(e))
                result = {"result":"error","msg":str(e)}
            return JsonResponse(result)
    else:
        return render(request, "login.html")

#delete temporary db of process(delete user's rows in db action table)
@csrf_exempt
def deleteAction(request):
    if 'username' in request.session and 'password' in request.session:
        if request.method == 'POST':
            username = request.session['username']
            try:
                tab = int(request.POST.get('tab'))
            except:
                tab = None
            Actions.objects.filter(create_by=username,tab=tab).delete()
            return JsonResponse({"result":"success"})
    else:
        return render(request, "login.html")

#copy nodes of process
@csrf_exempt
def createDiv(request):
    if 'username' in request.session and 'password' in request.session:
        if request.method == 'POST':
            username = request.session['username']
            copy_list = request.POST.get('copy_list')
            result = {}
            try:
                list = json.loads(copy_list)
            except:
                list = []
                result['result'] = "failed"
            try:
                tab = int(request.POST.get('tab'))
            except:
                tab = None
            copy_mode = request.POST.get('copy_mode')
            ids = []
            list2 = []
            for i in range(len(list)):
                copy_json = json.loads(list[i])
                list2.append(copy_json)
                try:
                    items = copy_json.items()
                except:
                    items = {}
                for key, value in items:
                    ids.append(value)
            action_json = {}
            # if copy_mode != "yes":取消ctrlC
            actions = Actions.objects.filter(create_by=username, div_id__in=ids).values('div_id', 'function', 'input', 'output', 'variant', 'public_variant','name','status')
            # else:
                # actions = ProcessCopy.objects.distinct().filter(create_by=username).values('div_id', 'function', 'input', 'output', 'variant', 'public_variant','name','status')
            for action in actions:
                div_id = action['div_id']
                action_json[div_id + "function"] = action['function']
                action_json[div_id + "input"] = action['input']
                action_json[div_id + "output"] = action['output']
                action_json[div_id + "variant"] = action['variant']
                action_json[div_id + "public_variant"] = action['public_variant']
                action_json[div_id + "name"] = action['name']
                action_json[div_id + "status"] = action['status']
            worklist = []
            try:
                now_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                for i in range(len(list2)):
                    copy_json = list2[i]
                    try:
                        items = copy_json.items()
                    except:
                        items = {}
                    for key, value in items:
                        if actions.exists():
                            function = action_json[value + "function"]
                            input = action_json[value + "input"]
                            output = action_json[value + "output"]
                            variant = action_json[value + "variant"]
                            public_variant = action_json[value + "public_variant"]
                            name = action_json[value + "name"]
                            status = action_json[value + "status"]
                            worklist.append(
                                Actions(div_id=key, function=function, input=input, output=output, variant=variant,
                                        public_variant=public_variant, name=name, status=status, create_on=now_time, create_by=username, tab=tab))
                if len(worklist) > 0:
                    Actions.objects.bulk_create(worklist)
                ProcessCopy.objects.filter(create_by=username).delete()
                result['result'] = "success"
            except Exception:
                result['result'] = "failed"
            return JsonResponse(result)
    else:
        return render(request, "login.html")

#copy nodes of process to db table process_copy(?)ctrlC按键，保存待复制模块至ProcessCopy表
@csrf_exempt
def saveDiv(request):
    if 'username' in request.session and 'password' in request.session:
        if request.method == 'POST':
            username = request.session['username']
            copy_list = request.POST.get('copy_list')
            list = json.loads(copy_list)
            worklist = []
            ids = []
            try:
                for i in range(len(list)):
                    ids.append(list[i])
                actions = Actions.objects.filter(create_by=username,div_id__in=ids).values('div_id', 'function','input','output','variant','public_variant','name','status')
                result = {}
                now_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                for action in actions:
                    worklist.append(
                        ProcessCopy(div_id=action['div_id'], function=action['function'], input=action['input'], output=action['output'], variant=action['variant'],
                                public_variant=action['public_variant'], create_on=now_time, create_by=username))
                ProcessCopy.objects.filter(create_by=username).delete()
                ProcessCopy.objects.bulk_create(worklist)
                result['result'] = "success"
            except:
                result['result'] = "failed"
            return JsonResponse(result)
    else:
        return render(request, "login.html")

#expire
@csrf_exempt
def searchDiv(request):
    if 'username' in request.session and 'password' in request.session:
        if request.method == 'POST':
            username = request.session['username']
            ids = []
            result = {}
            try:
                steps = ProcessCopy.objects.filter(create_by=username).values('div_id', 'function','input','output','variant','public_variant')
                for step in steps:
                    div_id = step['div_id']
                    ids.append(div_id)
                    result[div_id + 'function'] = step['function']
                    result[div_id + 'input'] = step['input']
                    result[div_id + 'output'] = step['output']
                    result[div_id + 'variant'] = step['variant']
                    result[div_id + 'public_variant'] = step['public_variant']
                result['result'] = "success"
            except:
                result['result'] = "failed"
            return JsonResponse(result)
    else:
        return render(request, "login.html")

#syntax checking
def correctChecking(value):
    try:
        code3 = ""
        if isinstance(value, str):
            if "=" not in value:
                code1 = "choclead_test_var=" + value
                code2 = "choclead_test_var=" + value.replace("\\", "\\\\")
                code3 = value
            else:
                code1 = value
                code2 = value.replace("\\", "\\\\")
        else:
            code1 = "choclead_test_var=" + str(value)
            code2 = "choclead_test_var=" + str(value).replace("\\", "\\\\")
        error = ""
        try:
            exec(code1)
        except:
            if code3:
                try:
                    exec(code2)
                except Exception as e:
                    error = str(e)
                    exec(code3)
            else:
                exec(code2)
        return ""
    except Exception as e:
        if "is not defined" not in str(e) and "is not defined" not in str(error):
            if "'int' object" in str(error) or "'str' object" in str(error) or "'str' object" in str(e) or "'int' object" in str(e):
                return ""
            else:
                return str(e)
        else:
            #如果有未定义变量，则不检查
            return ""
            # error = str(e)
            # while "is not defined" in error:
            #     replace_var = str(e).split(" is")[0]
            #     if replace_var[:5] == "name ":
            #         replace_var = replace_var.replace("name ","").replace("\'","")
            #     value1 = replace_var + "=1" + "\n" + value
            #     value2 = replace_var + "='choclead'" + "\n" + value
            #     error1 = correctChecking(value1)
            #     error2 = correctChecking(value2)
            #     if error1 == "" or error2 == "":
            #         error = ""
            #     else:
            #         if "out of range" in error1 or "out of range" in error2:
            #             error = ""
            #         else:
            #             error = error1
            # return error


def saveVariantForSetPassword(request, password_secret_key):
    if 'username' in request.session and 'password' in request.session:
        if request.method == 'POST':
            try:
                result = {}
                username = request.session['username']
                nodeName = request.POST.get("function")
                name = request.POST.get("name")
                nodeNo = request.POST.get("nodeNo")
                lastNode = request.POST.get("lastNode")
                nextNode = request.POST.get("nextNode")
                divID = request.POST.get("divID")
                variant = request.POST.get("variant")
                # print(variant)
                try:
                    tab = int(request.POST.get("tab"))
                except:
                    tab = None
                variant_json = json.loads(variant.replace(u"\u202a", ""))
                # SetPassword 提前加双引号保存,通过保存的检查
                if "choclead_p" in variant_json and nodeName == "Set_Password":
                    # password 加密
                    is_encrypt = encryption.is_encrypt(variant_json["choclead_p"])
                    if not is_encrypt:
                        temp_password = encryption.aes_encode_by_key(variant_json["choclead_p"], password_secret_key)
                        variant_2_json = json.loads(variant)
                        variant_2_json["choclead_p"] = temp_password
                        variant = json.dumps(variant_2_json)
                        #variant = variant.replace('"choclead_p":"' + variant_json["choclead_p"], '"choclead_p":"' + temp_password)
                #检查输入的变量是否存在语法问题
                try:
                    items = variant_json.items()
                except:
                    items = {}
                for key, value in items:
                    # 加密后的字符与检查变量冲突，估是密码的话跳过检查
                    if "choclead_p" in variant_json and nodeName == "Set_Password":
                        continue
                    error = correctChecking(value)
                    if error != "":
                        result['result'] = gettext("Node No: ") + str(nodeNo) + "<br>" + gettext("Node Name: ") + str(
                            nodeName) + "<br>" + gettext("Error Variant: ") + str(value) + "<br>" + gettext("Error Message: ") + str(
                            error)
                        return JsonResponse(result)
                if "mail_content" in variant_json:
                    variant_json['mail_content'] = variant_json['mail_content'].replace("\n","<br>")
                    variant_json['mail_signature'] = variant_json['mail_signature'].replace("\n", "<br>")
                    variant = json.dumps(variant_json)
                public_variant = request.POST.get("public_variant")
                input = request.POST.get("input")
                output = request.POST.get("output")
                now_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                Actions.objects.filter(div_id=divID,create_by=username.lower(),tab=tab).delete()
                #insert saved variant
                try:
                    Actions.objects.create(div_id=divID, node_no=nodeNo, function=nodeName, name=name,
                                           last_node=lastNode,
                                           next_node=nextNode, variant=variant.replace(u"\u202a",""), public_variant=public_variant,
                                           input=input, output=output, status='saved',
                                           create_on=now_time, create_by=username.lower(), tab=tab)
                except:
                    Actions.objects.create(div_id=divID, function=nodeName, name=name,
                                           last_node=lastNode,
                                           next_node=nextNode, variant=variant.replace(u"\u202a",""), public_variant=public_variant,
                                           input=input, output=output, status='saved',
                                           create_on=now_time, create_by=username.lower(), tab=tab)
                num = int(request.POST.get('length'))
                startID = request.POST.get('startID')
                ids = []
                #adjust the process sequence
                for i in range(num):
                    try:
                        nextID = request.POST.get(startID)
                        process = request.POST.get(nextID + "text")
                        nodeNo = int(request.POST.get(nextID + "nodeNo"))
                        if process == "End":
                            break
                        Actions.objects.filter(div_id=nextID, create_by=username.lower(), tab=tab).update(node_no=nodeNo)
                        Actions.objects.filter(group_id=nextID, create_by=username.lower(), tab=tab).update(node_no=nodeNo)
                        ids.append(nextID)
                        startID = nextID
                    except:
                        continue
                ids_sql = Actions.objects.filter(create_by=username.lower(), tab=tab).values('div_id','group_id')
                for id_json in ids_sql:
                    id = id_json['div_id']
                    group_id = id_json['group_id']
                    if id not in ids:
                        if group_id not in ids:
                            Actions.objects.filter(div_id=id, tab=tab).update(node_no=None)
                result['result'] = "success"
            except Exception as e:
                logger.error(repr(e))
                result['result'] = str(repr(e)).replace("\n","<br>")
            return JsonResponse(result)
    else:
        return render(request, "login.html")

#save current node property of process to action
@csrf_exempt
def saveVariant(request):
    if 'username' in request.session and 'password' in request.session:
        if request.method == 'POST':
            try:
                result = {}
                username = request.session['username']
                nodeName = request.POST.get("function")
                name = request.POST.get("name")
                nodeNo = request.POST.get("nodeNo")
                lastNode = request.POST.get("lastNode")
                nextNode = request.POST.get("nextNode")
                divID = request.POST.get("divID")
                variant = request.POST.get("variant")
                # print(variant)
                try:
                    tab = int(request.POST.get("tab"))
                except:
                    tab = None
                variant_json = json.loads(variant.replace(u"\u202a",""))
                # SetPassword 提前加双引号保存,通过保存的检查
                if "password" in variant_json and nodeName == "Set_Password":
                    variant_json["password"] = "\"" + variant_json["password"] + "\""
                #检查输入的变量是否存在语法问题
                try:
                    items = variant_json.items()
                except:
                    items = {}
                for key, value in items:
                    if nodeName =="Send_Mail" and "\n" in value:#Send_Mail内容&签名支持换行符
                        value = value.replace("\n","<br>")
                    error = correctChecking(value)
                    if error != "":
                        result['result'] = gettext("Node No: ") + str(nodeNo) + "<br>" + gettext("Node Name: ") + str(
                            nodeName) + "<br>" + gettext("Error Variant: ") + str(value) + "<br>" + gettext("Error Message: ") + str(
                            error)
                        return JsonResponse(result)
                if "mail_content" in variant_json:
                    variant_json['mail_content'] = variant_json['mail_content'].replace("\n","<br>")
                    variant_json['mail_signature'] = variant_json['mail_signature'].replace("\n", "<br>")
                    variant = json.dumps(variant_json)
                public_variant = request.POST.get("public_variant")
                input = request.POST.get("input")
                output = request.POST.get("output")
                now_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                Actions.objects.filter(div_id=divID,create_by=username.lower(),tab=tab).delete()
                #insert saved variant
                try:
                    Actions.objects.create(div_id=divID, node_no=nodeNo, function=nodeName, name=name,
                                           last_node=lastNode,
                                           next_node=nextNode, variant=variant.replace(u"\u202a",""), public_variant=public_variant,
                                           input=input, output=output, status='saved',
                                           create_on=now_time, create_by=username.lower(), tab=tab)
                except:
                    Actions.objects.create(div_id=divID, function=nodeName, name=name,
                                           last_node=lastNode,
                                           next_node=nextNode, variant=variant.replace(u"\u202a",""), public_variant=public_variant,
                                           input=input, output=output, status='saved',
                                           create_on=now_time, create_by=username.lower(), tab=tab)
                num = int(request.POST.get('length'))
                startID = request.POST.get('startID')
                ids = []
                #adjust the process sequence
                for i in range(num):
                    try:
                        nextID = request.POST.get(startID)
                        process = request.POST.get(nextID + "text")
                        nodeNo = int(request.POST.get(nextID + "nodeNo"))
                        if process == "End":
                            break
                        Actions.objects.filter(div_id=nextID, create_by=username.lower(), tab=tab).update(node_no=nodeNo)
                        Actions.objects.filter(group_id=nextID, create_by=username.lower(), tab=tab).update(node_no=nodeNo)
                        ids.append(nextID)
                        startID = nextID
                    except:
                        continue
                ids_sql = Actions.objects.filter(create_by=username.lower(), tab=tab).values('div_id','group_id')
                for id_json in ids_sql:
                    id = id_json['div_id']
                    group_id = id_json['group_id']
                    if id not in ids:
                        if group_id not in ids:
                            Actions.objects.filter(div_id=id, tab=tab).update(node_no=None)
                result['result'] = "success"
            except Exception as e:
                logging.error(repr(e))
                result['result'] = str(repr(e)).replace("\n","<br>")
            return JsonResponse(result)
    else:
        return render(request, "login.html")

#save sub-process nodes to action
@csrf_exempt
def saveProcessVariant(request):
    if 'username' in request.session and 'password' in request.session:
        result = {}
        try:
            username = request.session['username']
            useranme = username.lower()
            variant_list = request.POST.get("list")
            public_variant = request.POST.get("list2")
            list = json.loads(variant_list)
            list2 = json.loads(public_variant)
            try:
                groupNodeNo = int(request.POST.get("nodeNo"))
            except:
                groupNodeNo = request.POST.get("nodeNo")
            process_id = request.POST.get("id")
            group = request.POST.get("group")
            try:
                tab = int(request.POST.get("tab"))
            except:
                tab = None
            json1 = {}
            now_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            steps = Actions.objects.distinct().filter(create_by=username, node_no=groupNodeNo, group_id=process_id, tab=tab).values('div_id')
            Actions.objects.distinct().filter(create_by=username, div_id=process_id, tab=tab).delete()
            if len(steps) > 0:
                for i in range(len(list2)):
                    mapping = json.loads(list2[i])
                    sourceId = mapping["source_id"]
                    variant = mapping["variant"]
                    Actions.objects.filter(create_by=username, node_no=groupNodeNo, group_id=process_id, div_id=sourceId, tab=tab).update(variant=variant)
            else:
                for j in range(len(steps)):
                    step = steps[j]
                    div_id = step['div_id']
                    function = step['function']
                for i in range(len(list)):
                    public_json = json.loads(list[i])
                    nodeNo = public_json["node_no"]
                    try:
                        function = public_json["jnode_html"].split(">")[1]
                        function = function.split("<")[0]
                    except:
                        function = public_json["jnode_html"].replace("<span>", "").replace("</span>", "")
                    try:
                        json1[int(nodeNo)] = function
                    except:
                        continue
                worklist = []
                for i in range(len(list)):
                    mapping = json.loads(list[i])
                    sourceId = mapping["source_id"]
                    try:
                        nodeNo = int(mapping["node_no"])
                    except:
                        continue
                    try:
                        function = mapping["jnode_html"].split("id=")[1]
                        function = function.split("class=")[0].replace(" ", "").replace('"', "")
                    except:
                        function = mapping["jnode_html"].split(">")[1].split("<")[0]
                    name = mapping["name"]
                    input = mapping["input"]
                    output = mapping["output"]
                    variant = mapping["variant"]
                    publicVariant = mapping["public_variant"]
                    source_type = mapping["source_type"]
                    target_type = mapping["target_type"]
                    left = mapping["left"]
                    top = mapping["top"]
                    try:
                        lastNode = json1[int(nodeNo) - 1]
                    except:
                        lastNode = ""
                    try:
                        nextNode = json1[int(nodeNo) - 1]
                    except:
                        nextNode = ""
                    worklist.append(
                        Actions(div_id=sourceId, node_no=groupNodeNo, function=function, name=name, last_node=lastNode,
                                next_node=nextNode, input=input, output=output, variant=variant,
                                public_variant=publicVariant,
                                create_on=now_time, create_by=username, group=group, group_id=process_id, tab=tab,
                                group_node_no=nodeNo, group_source_type=source_type, group_target_type=target_type, group_left=left, group_top=top))
                Actions.objects.filter(create_by=username,group_id=process_id,tab=tab).delete()
                Actions.objects.filter(create_by=username,node_no=groupNodeNo,tab=tab).update(node_no=None)
                Actions.objects.bulk_create(worklist)
            num = int(request.POST.get('length'))
            startID = request.POST.get('startID')
            ids = []
            for i in range(num):
                try:
                    nextID = request.POST.get(startID)
                    process = request.POST.get(nextID + "text")
                    nodeNo = int(request.POST.get(nextID + "nodeNo"))
                    if process == "End":
                        break
                    Actions.objects.filter(div_id=nextID, create_by=username.lower(), tab=tab).update(node_no=nodeNo)
                    Actions.objects.filter(group_id=nextID, create_by=username.lower(), tab=tab).update(node_no=nodeNo)
                    ids.append(nextID)
                    startID = nextID
                except:
                    continue
            ids_sql = Actions.objects.filter(create_by=username.lower(), tab=tab).values('div_id', 'group_id')
            for id_json in ids_sql:
                id = id_json['div_id']
                group_id = id_json['group_id']
                if id not in ids:
                    if group_id not in ids:
                        Actions.objects.filter(div_id=id, tab=tab).update(node_no=None)
            result['result'] = "success"
            result['result'] = "success"
        except Exception:
            print(Exception)
            result['result'] = "failed"
        return JsonResponse(result)
    else:
        return render(request, "login.html")

#update sub-process nodes if it changed
@csrf_exempt
def updateProcessVariant(request):
    if 'username' in request.session and 'password' in request.session:
        result = {}
        try:
            username = request.session['username']
            variant_list = request.POST.get("list")
            list = json.loads(variant_list)
            groupNodeNo = request.POST.get("nodeNo")
            process_id = request.POST.get("id")
            group = request.POST.get("group")
            json1 = {}
            now_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            for i in range(len(list)):
                public_json = json.loads(list[i])
                nodeNo = public_json["node_no"]
                try:
                    function = public_json["jnode_html"].split(">")[1]
                    function = function.split("<")[0]
                except:
                    function = public_json["jnode_html"].replace("<span>", "").replace("</span>", "")
                # 更新嵌入流程时，如果有空的流程块就跳过
                try:
                    json1[int(nodeNo)] = function
                except:
                    continue
            worklist = []
            result_list = []
            for i in range(len(list)):
                mapping = json.loads(list[i])
                sourceId = mapping["source_id"]
                # 更新嵌入流程时，如果有空的流程块就跳过
                try:
                    nodeNo = int(mapping["node_no"])
                except:
                    continue
                stepNo = nodeNo
                try:
                    function = mapping["jnode_html"].split("id=")[1]
                    function = function.split("class=")[0].replace(" ", "").replace('"', "")
                except:
                    function = mapping["jnode_html"].split(">")[1].split("<")[0]
                name = mapping["name"]
                input = mapping["input"]
                output = mapping["output"]
                variant = mapping["variant"]
                publicVariant = mapping["public_variant"]
                source_type = mapping["source_type"]
                target_type = mapping["target_type"]
                left = mapping["left"]
                top = mapping["top"]
                result_list.append(sourceId)
                try:
                    lastNode = json1[int(nodeNo) - 1]
                except:
                    lastNode = ""
                try:
                    nextNode = json1[int(nodeNo) - 1]
                except:
                    nextNode = ""
                worklist.append(
                    Actions(div_id=sourceId, node_no=groupNodeNo, function=function, name=name, last_node=lastNode,
                            next_node=nextNode, input=input, output=output, variant=variant,
                            public_variant=publicVariant,
                            create_on=now_time, create_by=username, group=group, group_id=process_id,
                            group_node_no=nodeNo, group_source_type=source_type, group_target_type=target_type,
                            group_left=left, group_top=top))
            Actions.objects.filter(create_by=username,group_id=process_id).delete()
            Actions.objects.filter(create_by=username,node_no=groupNodeNo).update(node_no=None)
            Actions.objects.bulk_create(worklist)
            result['result'] = "success"
            result['list'] = result_list
        except Exception:
            print(Exception)
            result['result'] = "failed"
        return JsonResponse(result)
    else:
        return render(request, "login.html")

#get one node description
@csrf_exempt
def getName(request):
    if 'username' in request.session and 'password' in request.session:
        if request.method == 'POST':
            try:
                result = {}
                username = request.session['username']
                divID = request.POST.get("divID")
                names = Actions.objects.filter(div_id=divID,create_by=username).values('name')
                for div_name in names:
                    name = div_name['name']
                result['name'] = name
            except Exception as e:
                result['name'] = ''
            return JsonResponse(result)
    else:
        return render(request, "login.html")

#get all nodes description of one process(rearrangement all nodes)
@csrf_exempt
def processNames(request):
    if 'username' in request.session and 'password' in request.session:
        if request.method == 'POST':
            try:
                result = {}
                username = request.session['username']
                selections = Actions.objects.filter(create_by=username).values('div_id','name')
                selections_list = []
                for i in range(len(selections)):
                    selection = selections[i]
                    selection_json = {}
                    selection_json['id'] = selection['div_id']
                    name = selection['name']
                    if name != "":
                        selection_json['name'] = selection['name']
                        selections_list.append(selection_json)
                result['list'] = selections_list
            except Exception as e:
                print(e)
                result['list'] = []
            return JsonResponse(result)
    else:
        return render(request, "login.html")

#organize the code according to the process and write the code to created file, insert the process information to table store
@csrf_exempt
def saveProcess(request):
    if 'username' in request.session and 'password' in request.session:
        if request.method == 'POST':
            try:
                username = request.session['username']
                language = request.session['language']
                log_create_username = username
                log_create_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
                fileName = request.POST.get("name")
                type = request.POST.get("type")
                html = request.POST.getlist('html[]')
                try:
                    tab = int(request.POST.get("tab"))
                except:
                    tab = None
                try:
                    version = request.POST.get("version")
                except:
                    version = '1.0'
                # 提取数据库是否存在
                try:
                    data_store = Store.objects.filter(create_by=username, file_name=fileName, status="saved").values('source_id', 'name', 'node_no', 'jnode_html', 'variant', 'public_variant', 'input', 'output', 'group', 'group_id', 'group_node_no', 'status').order_by('node_no','group_node_no')
                    if len(data_store) > 0:
                        for i in range(len(data_store)):
                            data_store[i]["div_id"] = data_store[i]["source_id"]
                            try:
                                data_store[i]["function"] = data_store[i]["jnode_html"].split("id=")[1]
                                data_store[i]["function"] = data_store[i]["function"].split("class=")[0].replace(" ","").replace('"', "")
                            except:
                                data_store[i]["function"] = data_store[i]["jnode_html"].split(">")[1].split("<")[0]
                        robot_code = generateRobotExecuteCode(data_store,'run')
                        # nodes_dict = {}
                        # num = 1
                        # for i in data_store:
                        #     node_dict = {}
                        #     jnode_html = i.get('jnode_html')
                        #     data_search1 = re.search(r'id="(.*)" class',jnode_html,re.M | re.I)
                        #     jnode = data_search1.group(1)
                        #     variant = i.get('variant')
                        #     node_dict[jnode] = variant
                        #     nodes_dict[str(num)] = node_dict
                        #     num += 1
                        # nodes_json = json.dumps(nodes_dict)
                        # log_update_nodes = nodes_json
                        # 字典
                        log_update_nodes = []
                        for single in robot_code:
                            if "import " not in single["code"] and "# coding:utf-8" not in single["code"]:
                                log_update_nodes.append(single["code"])
                    else:
                        log_update_nodes = "None"
                except Exception:
                    pass
                list = []
                list2 = []
                list3 = []
                id_nodeNo = {}
                store_list = []
                action_json = {}
                result = {}
                num = int(request.POST.get('length'))
                startID = request.POST.get('startID')
                orgId = startID
                store_json = {}
                start_node = 1
                noneNodeNo = Actions.objects.distinct().filter(create_by=username, tab=tab, node_no=None).values('node_no')
                nodes = Actions.objects.filter(create_by=username, tab=tab, group_id=None).values()
                node_json = {}
                nodes_dict = {}
                num1 = 1
                for node in nodes:
                    node_dict = {}
                    divId = node['div_id']
                    nodeNo = node['node_no']
                    node_json[divId] = nodeNo
                    func_name = node.get("function")
                    condition = node.get("variant")
                    node_dict[func_name] = condition
                    nodes_dict[str(num1)] = node_dict
                    num1+=1
                nodes_json = json.dumps(nodes_dict)
                # # 日志流程节点埋点
                group_nodes = Actions.objects.distinct().filter(create_by=username, tab=tab).exclude(
                    group_id=None).values('group_id', 'node_no')
                for group_node in group_nodes:
                    groupId = group_node['group_id']
                    nodeNo = group_node['node_no']
                    node_json[groupId] = nodeNo
                nodeId = startID
                for i in range(num + 1):
                    div_name = request.POST.get(nodeId + "div_name")
                    processNo = i + 1
                    try:
                        nodeNo = node_json[nodeId]
                        if nodeNo is None or nodeNo == "" or nodeNo != processNo:
                            if div_name != "":
                                Actions.objects.distinct().filter(create_by=username, tab=tab, group_id=nodeId).update(
                                    node_no=processNo)
                            else:
                                Actions.objects.distinct().filter(create_by=username, tab=tab, div_id=nodeId).update(
                                    node_no=processNo)
                    except:
                        pass
                    nodeId = request.POST.get(nodeId)
                actions = Actions.objects.distinct().filter(create_by=username, tab=tab).exclude(group_id=None).values('node_no','group')
                group_node_list = []
                for action in actions:
                    nodeNo = action['node_no']
                    if nodeNo not in group_node_list:
                        group_node_list.append(str(nodeNo))
                    group = action['group']
                    if "public" in group and type == "private":
                        if "public" in group:
                            result["result"] = "error"
                            result["step"] = ""
                            result["msg"] = gettext("You can not insert public process to private file!")
                            return JsonResponse(result)
                    elif "public" not in group and type == "public":
                        if "private" in group:
                            result["result"] = "error"
                            result["step"] = ""
                            result["msg"] = gettext("You can not insert private process to public file!")
                            return JsonResponse(result)
                store_id_json = {}
                no = 0
                for i in range(num+1):
                    store_json[start_node] = startID
                    try:
                        nextID = request.POST.get(startID)
                    except:
                        nextID = ""
                    process = request.POST.get(startID + "text")
                    nodeNo = request.POST.get(startID + "nodeNo")
                    store_id_json[startID + 'groupNodeNo'] = nodeNo
                    if nodeNo in group_node_list:
                        list3.append(startID)
                        id_nodeNo[startID] = nodeNo
                        steps = Actions.objects.filter(create_by=username, node_no=nodeNo, tab=tab).values('node_no', 'function', 'variant', 'div_id', 'group', 'group_id', 'group_node_no', 'group_source_type', 'group_target_type', 'group_left', 'group_top', 'status').order_by('group_node_no')
                        for j in range(len(steps)):
                            step = steps[j]
                            div_id = step['div_id']
                            list3.append(div_id)
                            function = step['function']
                            group = step['group']
                            group_node_no = step['group_node_no']
                            node_no = str(step['node_no']) + "-" + str(step['group_node_no'])
                            if function != "Start" and function != "End":
                                list.append(node_no)
                                list2.append(function)
                            store_id_json[startID + "-" + str(no) + "-" + 'nodeNo'] = node_no
                            store_list.append(startID)
                            store_json[startID + "-" + node_no + "-" + "nodeNo"] = str(start_node)
                            store_json[startID + "-" + node_no + "-" + "targetID"] = nextID
                            store_json[startID + "-" + node_no + "-" + "sourceType"] = request.POST.get(startID + "source_type")
                            store_json[startID + "-" + node_no + "-" + "targetType"] = request.POST.get(startID + "target_type")
                            store_json[startID + "-" + node_no + "-" + "group"] = group
                            store_json[startID + "-" + node_no + "-" + "group_id"] = div_id
                            store_json[startID + "-" + node_no + "-" + "group_node_no"] = group_node_no
                            store_json[startID + "-" + node_no + "-" + "group_node_name"] = function
                            store_json[startID + "-" + node_no + "-" + "group_source_type"] = step['group_source_type']
                            store_json[startID + "-" + node_no + "-" + "group_target_type"] = step['group_target_type']
                            store_json[startID + "-" + node_no + "-" + "group_left"] = step['group_left']
                            store_json[startID + "-" + node_no + "-" + "group_top"] = step['group_top']
                            no += 1
                        startID = nextID
                        start_node += 1
                    else:
                        if process == "End":
                            store_id_json[startID + "-" + str(no) + "-" + 'nodeNo'] = nodeNo
                            store_list.append(startID)
                            break
                        else:
                            if process == "Start":
                                start_node += 1
                                store_list.append(startID)
                                store_id_json[startID + "-" + str(no) + "-" + 'nodeNo'] = nodeNo
                                store_json[startID + "-" + str(nodeNo) + "-" + "targetID"] = nextID
                                store_json[startID + "-" + str(nodeNo) + "-" + "sourceType"] = request.POST.get(startID + "source_type")
                                store_json[startID + "-" + str(nodeNo) + "-" + "targetType"] = request.POST.get(startID + "target_type")
                                startID = nextID
                                no+=1
                                continue
                            list3.append(startID)
                            id_nodeNo[startID] = nodeNo
                            store_json[startID + "-" + str(nodeNo) + "-" + "nodeNo"] = str(start_node)
                            store_json[startID + "-" + str(nodeNo) + "-" + "targetID"] = nextID
                            store_json[startID + "-" + str(nodeNo) + "-" + "sourceType"] = request.POST.get(startID + "source_type")
                            store_json[startID + "-" + str(nodeNo) + "-" + "targetType"] = request.POST.get(startID + "target_type")
                            store_json[startID + "-" + str(nodeNo) + "-" + "targetType"] = request.POST.get(
                                startID + "target_type")
                            list.append(nodeNo)
                            list2.append(process)
                            store_id_json[startID + "-" + str(no) + "-" + 'nodeNo'] = nodeNo
                            store_list.append(startID)
                            startID = nextID
                            start_node += 1
                            no += 1
                actions = Actions.objects.filter(create_by=username, div_id__in=list3, tab=tab).values('div_id', 'name', 'node_no', 'function', 'variant', 'public_variant', 'input', 'output', 'group', 'group_id', 'group_node_no', 'status').order_by('node_no','group_node_no')

                """
                sun13新方法的生成代码
                """
                robot_execute_codes = generateRobotExecuteCode(actions,"run")

                for action in actions:
                    function_json = {}
                    divId = action['div_id']
                    nodeNo = action['node_no']
                    if nodeNo is None:
                        nodeNo = id_nodeNo[divId]
                    # 保证可以保存上
                    try:
                        function_id = store_json[int(nodeNo)]
                    except Exception as e:
                        function_id = divId
                    groupNodeNo = action['group_node_no']
                    group_id = action['group_id']
                    status = action['status']
                    if group_id is not None and group_id != "" and group_id != "null":
                        nodeNo = str(nodeNo) + "-" + str(groupNodeNo)
                    function_id = function_id + "-" + str(nodeNo)
                    function = action['function']
                    variants_json = action['variant']
                    public_variants_json = action['public_variant']
                    store_json[function_id + "-" + "name"] = action['name']
                    try:
                        public_variants = json.loads(public_variants_json)
                    except:
                        public_variants = {}
                    try:
                        items = public_variants.items()
                    except:
                        items = {}
                    store_publicVariants_json = {}
                    for key, value in items:
                        # store_publicVariants_json[str(key)] = ""
                        store_publicVariants_json[str(key)] = str(value)
                    store_json[function_id + "-" + "publicVariants"] = json.dumps(store_publicVariants_json)
                    input = action['input']
                    output = action['output']
                    function_json['function'] = function
                    function_json['input'] = input
                    function_json['output'] = output
                    store_json[function_id + "-" + "status"] = action['status']
                    store_json[function_id + "-" + "input"] = input
                    store_json[function_id + "-" + "output"] = output
                    store_json[function_id + "-" + "status"] = status
                    if variants_json:
                        variants = json.loads(variants_json)
                    else:
                        variants = ""
                    if public_variants_json:
                        public_variants = json.loads(public_variants_json)
                    else:
                        public_variants = ""
                    try:
                        items = variants.items()
                    except:
                        items = {}
                    store_variants_json = {}
                    for key, value in items:
                        store_variants_json[str(key)] = value
                        function_json[str(key)] = value
                        # if key not in public_variants:
                        #     store_variants_json[str(key)] = str(value)
                        #     function_json[str(key)] = str(value)
                    store_json[function_id + "-" + "variants"] = json.dumps(store_variants_json)
                    action_json[str(nodeNo)] = function_json
                """
                保存时增加调整顺序
                """
                ids = []
                for i in range(num):
                    try:
                        nextID = request.POST.get(orgId)
                        process = request.POST.get(nextID + "text")
                        nodeNo = int(request.POST.get(nextID + "nodeNo"))
                        if process == "End":
                            break
                        Actions.objects.filter(div_id=nextID, create_by=username.lower(), tab=tab).update(node_no=nodeNo)
                        Actions.objects.filter(group_id=nextID, create_by=username.lower(), tab=tab).update(node_no=nodeNo)
                        ids.append(nextID)
                        orgId = nextID
                    except:
                        continue
                ids_sql = Actions.objects.filter(create_by=username.lower(), tab=tab).values('div_id','group_id')
                for id_json in ids_sql:
                    id = id_json['div_id']
                    group_id = id_json['group_id']
                    if id not in ids:
                        if group_id not in ids:
                            Actions.objects.filter(div_id=id, tab=tab).update(node_no=None)
                """>>>>>>>>>"""
                actions = Actions.objects.filter(create_by=username, node_no=None, tab=tab).values('div_id', 'name', 'variant', 'public_variant', 'input', 'output', 'status').order_by('node_no', 'group_node_no')
                for action in actions:
                    function_id = action['div_id']
                    store_json[function_id + "-0-" + "input"] = action['input']
                    store_json[function_id + "-0-" + "output"] = action['output']
                    store_json[function_id + "-0-" + "variants"] = action['variant']
                    store_json[function_id + "-0-" + "public_variants"] = action['public_variant']
                    store_json[function_id + "-0-" + "status"] = action['status']
                    store_json[function_id + "-0-" + "name"] = action['name']
                mappings = Packages.objects.distinct().filter(function__in=list2)
                mappings_list = serializers.serialize('json', mappings)
                mappings_array = json.loads(mappings_list)
                if type == "public":
                    store_type = type
                else:
                    store_type = username
                for i in range(len(html)):
                    html_json = json.loads(html[i])
                    html_id = html_json['id']
                    if html_id not in store_list:
                        store_list.append(html_id)
                    store_json[html_id + "jnodeClass"] = html_json['jnodeClass']
                    store_json[html_id + "jnode"] = html_json['jnode']
                    store_json[html_id + "jnodeHtml"] = html_json['jnodeHtml']
                    store_json[html_id + "left"] = str(html_json['left'])
                    store_json[html_id + "top"] = str(html_json['top'])
                current_function = ""
                Store.objects.filter(create_by=username,file_name=fileName).delete()
                file_name = fileName
                pyFile = os.path.dirname(os.path.realpath(__file__)) + "\\pyfile"
                if not os.path.exists(pyFile):
                    path1 = pyFile + "\\release"
                    path2 = pyFile + "\\public"
                    os.mkdir(pyFile)
                    os.mkdir(path1)
                    os.mkdir(path2)
                log_create_file_path = fileName.replace(".py","")
                fileName = os.path.dirname(os.path.realpath(__file__)) + "\\pyfile\\" + fileName
                fileNames = fileName.split("\\")
                for i in range(len(fileNames)):
                    if i == 0:
                        filePath = fileNames[i]
                    elif i == len(fileNames) - 1:
                        break
                    else:
                        filePath = filePath + "\\" + fileNames[i]
                if os.path.exists(filePath):
                    pass
                else:
                    os.mkdir(filePath)
                try:
                    """
                    sun13 更新生成逻辑
                    """
                    with open(fileName, mode='w', encoding='utf-8') as ff:
                        try:
                            code = ""
                            log_code = []
                            for single in robot_execute_codes:
                                if "import " not in single["code"] and "# coding:utf-8" not in single["code"]:
                                    log_code.append(single["code"])
                                code = code + single["code"]
                            ff.write(code)
                            result["result"] = "success"
                        except Exception as e:
                            exstr = traceback.format_exc()
                            logging.error(exstr)
                            result["result"] = "error"
                            result["step"] = ""
                            result["msg"] = gettext("Saved successfully,but some error with your process!")
                            result["error"] = str(e)
                            try:
                                os.remove(fileName)
                            except Exception as e:
                                print(str(e))
                        # 日志流程节点埋点
                        # 运行成功失败日志
                        log_create_file_result = result["result"]
                        # logging.info(repr(log_create_file_result))
                        log_save = {}
                        if log_update_nodes == "None":
                            log_save["action"] = "save process"
                        else:
                            log_save["action"] = "update process"
                        try:
                            log_save["computer name"] = pc_names[username.lower()]
                        except:
                            pass
                        log_save['username'] = log_create_username
                        log_save['time'] = log_create_time

                        # 字典
                        log_save['path'] = log_create_file_path
                        if log_update_nodes == "None":
                            log_save['new process nodes'] = log_code
                            log_save['result'] = log_create_file_result
                            log_save_json = "415>" + json.dumps(log_save)
                            logger.info(log_save_json)
                        else:
                            log_save['old process nodes'] = log_update_nodes
                            log_save['new process nodes'] = log_code
                            log_save['result'] = log_create_file_result
                            log_save_json = "425>" + json.dumps(log_save)
                            logger.info(log_save_json)
                    # replace_variant = "no"
                    # for_variant2str = ""
                    # for_repalce_variant = ""
                    # with open(fileName, mode='w',encoding='utf-8') as ff:
                    #     try:
                    #         reuse_browser = 'no'
                    #         import_packages = []
                    #         start = "\t"
                    #         ff.write("#coding:utf-8" + '\n')
                    #         for mapping in mappings_array:
                    #             packages = mapping['fields']['package']
                    #             function = mapping['fields']['function']
                    #             if function == "Reuse_Browser":
                    #                 reuse_browser = 'yes'
                    #             packages_array = packages.split(";")
                    #             for package in packages_array:
                    #                 if package != "" and package not in import_packages:
                    #                     ff.write(package + '\n')
                    #                     import_packages.append(package)
                    #         ff.write('import win32gui' + '\n')
                    #         ff.write('import traceback' + '\n')
                    #         ff.write('\n')
                    #         if reuse_browser == 'yes':
                    #             ff.write('class ReuseChrome(Remote):' + '\n')
                    #             ff.write('\t' + "def __init__(self, command_executor, session_id):" + '\n')
                    #             ff.write('\t\t' + "self.r_session_id = session_id" + '\n')
                    #             ff.write('\t\t' + "Remote.__init__(self, command_executor=command_executor, desired_capabilities={})" + '\n\n')
                    #             ff.write('\t' + "def start_session(self, capabilities, browser_profile=None):" + '\n')
                    #             ff.write('\t\t' + "if not isinstance(capabilities, dict):" + '\n')
                    #             ff.write('\t\t\t' + "raise InvalidArgumentException('Capabilities must be a dictionary')" + '\n')
                    #             ff.write('\t\t' + "if browser_profile:" + '\n')
                    #             ff.write('\t\t\t' + "if 'moz:firefoxOptions' in capabilities:" + '\n')
                    #             ff.write('\t\t\t\t' + 'capabilities["moz:firefoxOptions"]["profile"] = browser_profile.encoded' + '\n')
                    #             ff.write('\t\t\t' + "else:" + '\n')
                    #             ff.write('\t\t\t\t' + "capabilities.update({'firefox_profile': browser_profile.encoded})" + '\n\n')
                    #             ff.write('\t\t' + "self.capabilities = options.Options().to_capabilities()" + '\n')
                    #             ff.write('\t\t' + "self.session_id = self.r_session_id" + '\n')
                    #             ff.write('\t\t' + "self.w3c = False" + '\n\n')
                    #         ff.write('class test():' + '\n')
                    #         ff.write('\t' + "def __init__(self):" + '\n')
                    #         ff.write('\t\t' + "self.hwnd_title = dict()" + '\n\n')
                    #         ff.write('\t' + "def get_all_hwnd(self,hwnd,mouse):" + '\n')
                    #         ff.write('\t\t' + "if win32gui.IsWindow(hwnd) and win32gui.IsWindowEnabled(hwnd) and win32gui.IsWindowVisible(hwnd):" + '\n')
                    #         ff.write('\t\t\t' + "self.hwnd_title.update({hwnd:win32gui.GetWindowText(hwnd)})" + '\n\n')
                    #         ff.write('\t' + 'def get_hwnd(self,title):' + '\n')
                    #         ff.write('\t\t' + "win32gui.EnumWindows(self.get_all_hwnd, 0)" + '\n')
                    #         ff.write('\t\t' + "for h, t in self.hwnd_title.items():" + '\n')
                    #         ff.write('\t\t\t' + "if t is not '':" + '\n')
                    #         ff.write('\t\t\t\t' + "if title in t:" + '\n')
                    #         ff.write('\t\t\t\t\t' + "try:" + '\n')
                    #         ff.write('\t\t\t\t\t\t' + "left, top, right, bottom = win32gui.GetWindowRect(h)" + '\n')
                    #         ff.write('\t\t\t\t\t\t' + "return h" + '\n')
                    #         ff.write('\t\t\t\t\t' + "except:" + '\n')
                    #         ff.write('\t\t\t\t\t\t' + "continue" + '\n\n')
                    #         ff.write('\t' + 'def column_to_name(self,num):' + '\n')
                    #         ff.write('\t\t' + "if not isinstance(num, int):" + '\n')
                    #         ff.write('\t\t\t' + "return num" + '\n')
                    #         ff.write('\t\t' + "tStr = str()" + '\n')
                    #         ff.write('\t\t' + "while num != 0:" + '\n')
                    #         ff.write('\t\t\t' + "res = num % 26" + '\n')
                    #         ff.write('\t\t\t' + "if res == 0:" + '\n')
                    #         ff.write('\t\t\t\t' + "res = 26" + '\n')
                    #         ff.write('\t\t\t\t' + "num -= 26" + '\n')
                    #         ff.write('\t\t\t' + "tStr = chr(ord('A') + res - 1) + tStr" + '\n')
                    #         ff.write('\t\t\t' + "num = num // 26" + '\n')
                    #         ff.write('\t\t' + "return tStr" + '\n\n')
                    #         packages_json = {}
                    #         get_all_hwnd = "no"
                    #         for mapping in mappings_array:
                    #             function = mapping['fields']['function']
                    #             if function == "Excel_Format":
                    #                 ff.write('\t' + 'def rgb_to_hex(self,r,g,b):' + '\n')
                    #                 ff.write('\t\t' + "bgr = (b,g,r)" + '\n')
                    #                 ff.write('\t\t' + "strValue = '%02x%02x%02x' % bgr" + '\n')
                    #                 ff.write('\t\t' + "iValue = int(strValue, 16)" + '\n')
                    #                 ff.write('\t\t' + "return iValue" + '\n')
                    #                 ff.write('\n')
                    #             elif function == "Web_StartBrowser":
                    #                 ff.write('\t' + "def close_alert_and_get_its_text(self):" + '\n')
                    #                 ff.write('\t\t' + "try:" + '\n')
                    #                 ff.write('\t\t\t' + "alert = self.driver.switch_to_alert()" + '\n')
                    #                 ff.write('\t\t\t' + "alert_text = alert.text" + '\n')
                    #                 ff.write('\t\t\t' + "if self.accept_next_alert:" + '\n')
                    #                 ff.write('\t\t\t\t' + "alert.accept()" + '\n')
                    #                 ff.write('\t\t\t' + "else:" + '\n')
                    #                 ff.write('\t\t\t\t' + "alert.dismiss()" + '\n')
                    #                 ff.write('\t\t\t' + "return alert_text" + '\n')
                    #                 ff.write('\t\t' + "finally: self.accept_next_alert = True" + '\n\n')
                    #                 ff.write('\t' + 'def tearDown(self):' + '\n')
                    #                 ff.write('\t\t' + 'self.driver.quit()' + '\n')
                    #                 ff.write('\t\t' + 'self.assertEqual([], self.verificationErrors)' + '\n\n')
                    #             elif function == "Screen_Shot":
                    #                 if get_all_hwnd == "no":
                    #                     ff.write('\t' + "def __init__(self):" + '\n')
                    #                     ff.write('\t\t' + "self.hwnd_title = dict()" + '\n\n')
                    #                     ff.write('\t' + "def get_all_hwnd(self,hwnd,mouse):" + '\n')
                    #                     ff.write('\t\t' + "if win32gui.IsWindow(hwnd) and win32gui.IsWindowEnabled(hwnd) and win32gui.IsWindowVisible(hwnd):" + '\n')
                    #                     ff.write('\t\t\t' + "self.hwnd_title.update({hwnd:win32gui.GetWindowText(hwnd)})" + '\n\n')
                    #                 ff.write('\t' + "def window_capture(self,hwnd,filename):" + '\n')
                    #                 ff.write('\t\t' + "hwndDC = win32gui.GetWindowDC(hwnd)" + '\n')
                    #                 ff.write('\t\t' + "mfcDC = win32ui.CreateDCFromHandle(hwndDC)" + '\n')
                    #                 ff.write('\t\t' + "saveDC = mfcDC.CreateCompatibleDC()" + '\n')
                    #                 ff.write('\t\t' + "saveBitMap = win32ui.CreateBitmap()" + '\n')
                    #                 ff.write('\t\t' + "MoniterDev = win32api.EnumDisplayMonitors(None, None)" + '\n')
                    #                 ff.write('\t\t' + "w = MoniterDev[0][2][2]" + '\n')
                    #                 ff.write('\t\t' + "h = MoniterDev[0][2][3]" + '\n')
                    #                 ff.write('\t\t' + "saveBitMap.CreateCompatibleBitmap(mfcDC, w, h)" + '\n')
                    #                 ff.write('\t\t' + "saveDC.SelectObject(saveBitMap)" + '\n')
                    #                 ff.write('\t\t' + "saveDC.BitBlt((0, 0), (w, h), mfcDC, (0, 0), win32con.SRCCOPY)" + '\n')
                    #                 ff.write('\t\t' + "saveBitMap.SaveBitmapFile(saveDC, filename)" + '\n')
                    #                 ff.write('\t\t' + "win32gui.delete(saveBitMap.GetHandle())" + '\n')
                    #                 ff.write('\t\t' + "saveDC.DeleteDC()" + '\n')
                    #                 ff.write('\t\t' + "mfcDC.DeleteDC()" + '\n')
                    #                 ff.write('\t\t' + "win32gui.Release(hwnd, hwndDC)" + '\n\n')
                    #                 get_all_hwnd = "yes"
                    #         for mapping in mappings_array:
                    #             function = mapping['fields']['function']
                    #             codes = mapping['fields']['codes'] + mapping['fields']['codes_1'] + mapping['fields'][
                    #                 'codes_2'] + mapping['fields']['codes_3'] + mapping['fields']['codes_4'] + \
                    #                     mapping['fields']['codes_5'] + mapping['fields']['codes_6']
                    #             packages_json[function] = codes
                    #         run_function = []
                    #         startdef = "no"
                    #         for i in range(len(list)):
                    #             nodeNo = str(list[i])
                    #             function = action_json[nodeNo]['function']
                    #             if function != "Define" and startdef == "no":
                    #                 ff.write('\t' + 'def run(self):' + '\n')
                    #                 startdef = "yes"
                    #                 start = "\t\t"
                    #             elif function == "End_Def":
                    #                 startdef = "no"
                    #             elif function == "Define":
                    #                 startdef = "yes"
                    #             if function == "Excel_Filter":
                    #                 column_num = action_json[nodeNo]['column_num']
                    #                 filter_condition = action_json[nodeNo]['filter_condition']
                    #                 filter_column = 0
                    #                 for j in range(len(column_num)):
                    #                     character = column_num[j]
                    #                     filter_column = filter_column + (ord(character) - 64) * (
                    #                             26 ** (len(column_num) - j - 1))
                    #                 condition = "Field=" + str(filter_column) + ","
                    #                 num = 1
                    #                 if "and" in filter_condition:
                    #                     strs = filter_condition.split("and")
                    #                     for m in range(len(strs)):
                    #                         str_and = strs[m]
                    #                         if "or" in str_and:
                    #                             strs_or = str_and.split("or")
                    #                             for n in range(len(strs_or)):
                    #                                 str_or = strs_or[n]
                    #                                 cri = "Criteria" + str(num)
                    #                                 num += 1
                    #                                 if n == len(strs_or) - 1:
                    #                                     condition = condition + cri + "=" + '"' + str_or.replace(" ",
                    #                                                                                              "") + '"'
                    #                                 else:
                    #                                     condition = condition + cri + "=" + '"' + str_or.replace(" ",
                    #                                                                                              "") + '"' + "," + 'Operator=2' + ","
                    #                         else:
                    #                             cri = "Criteria" + str(num)
                    #                             num += 1
                    #                             if m == len(strs) - 1:
                    #                                 condition = condition + cri + "=" + '"' + str_and.replace(" ",
                    #                                                                                           "") + '"'
                    #                             else:
                    #                                 condition = condition + cri + "=" + '"' + str_and.replace(" ",
                    #                                                                                           "") + '"' + "," + 'Operator=1' + ","
                    #                 elif "or" in filter_condition:
                    #                     strs = filter_condition.split("or")
                    #                     for x in range(len(strs)):
                    #                         str_or = strs[x]
                    #                         cri = "Criteria" + str(num)
                    #                         num += 1
                    #                         if x == len(strs) - 1:
                    #                             condition = condition + cri + "=" + '"' + str_or.replace(" ", "") + '"'
                    #                         else:
                    #                             condition = condition + cri + "=" + '"' + str_or.replace(" ",
                    #                                                                                      "") + '"' + "," + 'Operator=2' + ","
                    #                 else:
                    #                     try:
                    #                         filter_type = eval(action_json[nodeNo]['filter_type'])
                    #                     except:
                    #                         filter_type = 7
                    #                     if filter_type == 7:
                    #                         if "," in filter_condition:
                    #                             filter_condition_list = filter_condition.split(",")
                    #                             filter_condition_2_str = "["
                    #                             for filter_i in range(len(filter_condition_list)):
                    #                                 if filter_i == len(filter_condition_list) - 1:
                    #                                     filter_condition_2_str = filter_condition_2_str + "'" + \
                    #                                                              filter_condition_list[filter_i] + "'"
                    #                                 else:
                    #                                     filter_condition_2_str = filter_condition_2_str + "'" + \
                    #                                                              filter_condition_list[
                    #                                                                  filter_i] + "'" + ","
                    #                             filter_condition_2_str = filter_condition_2_str + "]"
                    #                             condition = condition + "Criteria1" + "=" + filter_condition_2_str + ",Operator = 7"
                    #                         else:
                    #                             condition = condition + "Criteria1" + "=" + '"' + filter_condition + '"'
                    #                     else:
                    #                         try:
                    #                             filter_type = eval(action_json[nodeNo]['filter_type'])
                    #                         except:
                    #                             filter_type = 7
                    #                         if filter_type == 7:
                    #                             condition = condition + "Criteria1" + "=" + '"' + filter_condition + '"'
                    #                         else:
                    #                             condition = condition + "Criteria1" + "=" + filter_condition + ",Operator = " + str(
                    #                                 filter_type)
                    #                 action_json[nodeNo]['condition'] = condition
                    #             elif function == "Excel_Top10":
                    #                 column_num = action_json[nodeNo]['column_num']
                    #                 filter_column = 0
                    #                 for j in range(len(column_num)):
                    #                     character = column_num[j]
                    #                     filter_column = filter_column + (ord(character) - 64) * (
                    #                                 26 ** (len(column_num) - j - 1))
                    #                 action_json[nodeNo]['column_num'] = filter_column
                    #             codes = packages_json[function]
                    #             if function == "For":
                    #                 replace_variant = "yes"
                    #                 for_variant2json = action_json[nodeNo]
                    #                 for_variant = for_variant2json['for_variant']
                    #                 for_type = for_variant2json['for_type']
                    #                 if for_type == "string":
                    #                     for_variant2str = '" + str(' + for_variant + ') + "'
                    #                 else:
                    #                     for_variant2str = for_variant
                    #                 for_repalce_variant = "(" + for_variant + ")"
                    #             elif function == "Exit_For":
                    #                 replace_variant = "no"
                    #             if function == "Excel_Filter" and function in run_function:
                    #                 codes = codes.replace("workbook.AutoFilter = False;", "")
                    #             run_function.append(function)
                    #             if function == "Send_Mail":
                    #                 codes = codes.replace('if ";"', 'if ","')
                    #                 codes = codes.replace("split(';')", "split(',')")
                    #             codes_array = codes.split(";")
                    #             items = action_json[nodeNo].items()
                    #             try:
                    #                 replace_slash = action_json[nodeNo]['replace_slash']
                    #             except:
                    #                 replace_slash = "yes"
                    #             for code in codes_array:
                    #                 if "SQL" in function:
                    #                     if "Microsoft Access Driver (*.mdb,*.accdb)}-DBQ=" in code:
                    #                         code = code.replace("-", ";")
                    #                 if function == "Send_Mail":
                    #                     code = code.replace('if ","', 'if ";"')
                    #                     code = code.replace("split(',')", "split(';')")
                    #                 if "endif" in code or "endwhile" in code or "endfor" in code or "endwith" in code or "endtry" in code:
                    #                     start = start.replace('\t', '', 1)
                    #                     continue
                    #                 elif "elif" in code or "else" in code or "except" in code:
                    #                     start = start.replace('\t', '', 1)
                    #                 elif code == "":
                    #                     continue
                    #                 for key, value in items:
                    #                     if key == "output" and value == "":
                    #                         value = "output"
                    #                     code = code.replace(key, str(value))
                    #                     if replace_slash == "yes":
                    #                         if "path" in key:
                    #                             code = code.replace('/', '\\')
                    #                             code = code.replace('\\', '\\\\')
                    #                         elif "content =" in code and "\\" not in code:
                    #                             code = code.replace('/', '\\')
                    #                             code = code.replace('\\', '\\\\')
                    #                         elif "content =" in code and "\\" in code and "content = r" not in code:
                    #                             code = code.replace('content = ', 'content = r')
                    #                         elif "send_var =" in code and "\\" not in code:
                    #                             code = code.replace('/', '\\')
                    #                             code = code.replace('\\', '\\\\')
                    #                         elif "send_var =" in code and "\\" in code and "send_var = r" not in code:
                    #                             code = code.replace('send_var = ', 'send_var = r')
                    #                 code = code.replace('blank', '\t')
                    #                 if function == "Define" and ",fun_variant" in code:
                    #                     code = code.replace(",fun_variant", "")
                    #                 if replace_variant == "yes" and function != "For":
                    #                     if for_repalce_variant in code:
                    #                         code = code.replace(for_repalce_variant, for_variant2str)
                    #                     else:
                    #                         try:
                    #                             replace_for = "(" + str(for_variant)
                    #                             position = code.find(replace_for)
                    #                             string2 = code[position:]
                    #                             string3 = string2.replace(replace_for, "")
                    #                             if string3[0:1] == " " or string3[0:1] == "+" or string3[
                    #                                                                              0:1] == "-" or string3[
                    #                                                                                             0:1] == "*" or string3[
                    #                                                                                                            0:1] == "//":
                    #                                 position2 = string2.find(")")
                    #                                 string4 = string2[0:position2 + 1]
                    #                                 string5 = string2[0:position2].replace(replace_for, "")
                    #                                 code = code.replace(string4,
                    #                                                     '" + str(' + for_variant + string5 + ') + "')
                    #                         except Exception:
                    #                             code = code.replace(for_repalce_variant, for_variant2str)
                    #                 ff.write(start + code + '\n')
                    #                 code_check = code[0:6]
                    #                 if "if" in code_check or "while" in code_check or "for" in code_check or "elif" in code_check or "else" in code_check or "try" in code_check or "except" in code_check or "with" in code_check:
                    #                     start = start + '\t'
                    #         ff.write('\t\t' + 'return {"result":"success"}')
                    #         result["result"] = "success"
                    #     except Exception as e:
                    #         exstr = traceback.format_exc()
                    #         logging.error(exstr)
                    #         result["result"] = "error"
                    #         result["step"] = ""
                    #         result["msg"] = gettext("Saved successfully,but some error with your process!")
                    #         result["error"] = str(e)
                    #         try:
                    #             os.remove(fileName)
                    #         except Exception:
                    #             print(str(e))
                    queryset_list = []
                    now_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    for i in range(len(store_list)):
                        source_id = store_list[i]
                        try:
                            nodeNo = store_id_json[source_id + "-" + str(i) + "-" + 'nodeNo']
                        except:
                            nodeNo = 0
                        try:
                            groupNodeNo = store_id_json[source_id + 'groupNodeNo']
                        except:
                            groupNodeNo = ""
                        try:
                            target_id = store_json[source_id + "-" + str(nodeNo) + "-" + "targetID"]
                        except:
                            target_id = ""
                        try:
                            status = store_json[source_id + "-" + str(nodeNo) + "-" + "status"]
                        except:
                            status = ""
                        try:
                            source_type = store_json[source_id + "-" + str(nodeNo) + "-" + "sourceType"]
                        except:
                            source_type = ""
                        try:
                            target_type = store_json[source_id + "-" + str(nodeNo) + "-" + "targetType"]
                        except:
                            target_type = ""
                        try:
                            name = store_json[source_id + "-" + str(nodeNo) + "-" + "name"]
                        except:
                            try:
                                name = store_json[source_id + "-" + "name"]
                            except:
                                name = ""
                        try:
                            input = store_json[source_id + "-" + str(nodeNo) + "-" + "input"]
                        except:
                            try:
                                input = store_json[source_id + "-" + "input"]
                            except:
                                input = ""
                        try:
                            output = store_json[source_id + "-" + str(nodeNo) + "-" + "output"]
                        except:
                            try:
                                output = store_json[source_id + "-" + "output"]
                            except:
                                output = ""
                        try:
                            variant = store_json[source_id + "-" + str(nodeNo) + "-" + "variants"]
                        except:
                            try:
                                variant = store_json[source_id + "-" + "variant"]
                            except:
                                variant = ""
                        try:
                            public_variant = store_json[source_id + "-" + str(nodeNo) + "-" + "publicVariants"]
                        except:
                            try:
                                public_variant = store_json[source_id + "-" + "public_variant"]
                            except:
                                public_variant = ""
                        try:
                            group = store_json[source_id + "-" + str(nodeNo) + "-" + "group"]
                        except:
                            group = ""
                        try:
                            group_id = store_json[source_id + "-" + str(nodeNo) + "-" + "group_id"]
                        except:
                            group_id = ""
                        try:
                            group_node_no = store_json[source_id + "-" + str(nodeNo) + "-" + "group_node_no"]
                        except:
                            group_node_no = ""
                        try:
                            group_node_name = store_json[source_id + "-" + str(nodeNo) + "-" + "group_node_name"]
                        except:
                            group_node_name = ""
                        try:
                            group_source_type = store_json[source_id + "-" + str(nodeNo) + "-" + "group_source_type"]
                        except:
                            group_source_type = ""
                        try:
                            group_target_type = store_json[source_id + "-" + str(nodeNo) + "-" + "group_target_type"]
                        except:
                            group_target_type = ""
                        try:
                            group_left = store_json[source_id + "-" + str(nodeNo) + "-" + "group_left"]
                        except:
                            group_left = ""
                        try:
                            group_top = store_json[source_id + "-" + str(nodeNo) + "-" + "group_top"]
                        except:
                            group_top = ""
                        if nodeNo == 0:
                            queryset_list.append(
                                Store(type=store_type, file_name=file_name,
                                      source_id=source_id, target_id=target_id, source_type=source_type,
                                      target_type=target_type,
                                      jnode_class=store_json[source_id + "jnodeClass"],
                                      jnode=store_json[source_id + "jnode"],
                                      jnode_html=store_json[source_id + "jnodeHtml"],
                                      left=store_json[source_id + "left"], top=store_json[source_id + "top"], name=name,
                                      input=input, output=output,
                                      variant=variant, public_variant=public_variant, create_on=now_time,
                                      create_by=username, group_source_type=group_source_type, status=status, version=version,
                                      group_target_type=group_target_type, group_left=group_left, group_top=group_top))
                        else:
                            if group_node_no == "":
                                queryset_list.append(
                                    Store(node_no=groupNodeNo, type=store_type, file_name=file_name,
                                          source_id=source_id, target_id=target_id, source_type=source_type,
                                          target_type=target_type,
                                          jnode_class=store_json[source_id + "jnodeClass"],
                                          jnode=store_json[source_id + "jnode"],
                                          jnode_html=store_json[source_id + "jnodeHtml"],
                                          left=store_json[source_id + "left"], top=store_json[source_id + "top"], name=name,
                                          input=input, output=output,
                                          variant=variant, public_variant=public_variant, create_on=now_time, status=status, version=version,
                                          create_by=username, group_source_type=group_source_type, group_target_type=group_target_type, group_left=group_left, group_top=group_top))
                            else:
                                queryset_list.append(
                                    Store(node_no=groupNodeNo, type=store_type, file_name=file_name,
                                          source_id=source_id, target_id=target_id, source_type=source_type,
                                          target_type=target_type,
                                          jnode_class=store_json[source_id + "jnodeClass"],
                                          jnode=store_json[source_id + "jnode"],
                                          jnode_html=store_json[source_id + "jnodeHtml"],
                                          left=store_json[source_id + "left"], top=store_json[source_id + "top"], name=name,
                                          input=input, output=output,
                                          variant=variant, public_variant=public_variant, create_on=now_time, status=status, version=version,
                                          create_by=username, group=group, group_id=group_id, group_node_no=group_node_no, group_node_name=group_node_name,
                                          group_source_type=group_source_type, group_target_type=group_target_type, group_left=group_left, group_top=group_top))
                    Store.objects.bulk_create(queryset_list)
                except Exception as e:
                    exstr = traceback.format_exc()
                    logging.error(exstr)
                    result["result"] = "error"
                    result["error"] = str(e)
                    result["msg"] = exstr
                    queryset_list = []
                    now_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    for i in range(len(store_list)):
                        source_id = store_list[i]
                        try:
                            nodeNo = store_id_json[source_id + "-" + str(i) + "-" + 'nodeNo']
                        except:
                            nodeNo = 0
                        try:
                            groupNodeNo = store_id_json[source_id + 'groupNodeNo']
                        except:
                            groupNodeNo = ""
                        try:
                            target_id = store_json[source_id + "-" + str(nodeNo) + "-" + "targetID"]
                        except:
                            target_id = ""
                        try:
                            status = store_json[source_id + "-" + str(nodeNo) + "-" + "status"]
                        except:
                            status = ""
                        try:
                            source_type = store_json[source_id + "-" + str(nodeNo) + "-" + "sourceType"]
                        except:
                            source_type = ""
                        try:
                            target_type = store_json[source_id + "-" + str(nodeNo) + "-" + "targetType"]
                        except:
                            target_type = ""
                        try:
                            name = store_json[source_id + "-" + str(nodeNo) + "-" + "name"]
                        except:
                            try:
                                name = store_json[source_id + "-" + "name"]
                            except:
                                name = ""
                        try:
                            input = store_json[source_id + "-" + str(nodeNo) + "-" + "input"]
                        except:
                            try:
                                input = store_json[source_id + "-" + "input"]
                            except:
                                input = ""
                        try:
                            output = store_json[source_id + "-" + str(nodeNo) + "-" + "output"]
                        except:
                            try:
                                output = store_json[source_id + "-" + "output"]
                            except:
                                output = ""
                        try:
                            variant = store_json[source_id + "-" + str(nodeNo) + "-" + "variants"]
                        except:
                            try:
                                variant = store_json[source_id + "-" + "variant"]
                            except:
                                variant = ""
                        try:
                            public_variant = store_json[source_id + "-" + str(nodeNo) + "-" + "publicVariants"]
                        except:
                            try:
                                public_variant = store_json[source_id + "-" + "public_variant"]
                            except:
                                public_variant = ""
                        try:
                            group = store_json[source_id + "-" + str(nodeNo) + "-" + "group"]
                        except:
                            group = ""
                        try:
                            group_id = store_json[source_id + "-" + str(nodeNo) + "-" + "group_id"]
                        except:
                            group_id = ""
                        try:
                            group_node_no = store_json[source_id + "-" + str(nodeNo) + "-" + "group_node_no"]
                        except:
                            group_node_no = ""
                        try:
                            group_node_name = store_json[source_id + "-" + str(nodeNo) + "-" + "group_node_name"]
                        except:
                            group_node_name = ""
                        try:
                            group_source_type = store_json[source_id + "-" + str(nodeNo) + "-" + "group_source_type"]
                        except:
                            group_source_type = ""
                        try:
                            group_target_type = store_json[source_id + "-" + str(nodeNo) + "-" + "group_target_type"]
                        except:
                            group_target_type = ""
                        try:
                            group_left = store_json[source_id + "-" + str(nodeNo) + "-" + "group_left"]
                        except:
                            group_left = ""
                        try:
                            group_top = store_json[source_id + "-" + str(nodeNo) + "-" + "group_top"]
                        except:
                            group_top = ""
                        if nodeNo == 0:
                            queryset_list.append(
                                Store(type=store_type, file_name=file_name,
                                      source_id=source_id, target_id=target_id, source_type=source_type,
                                      target_type=target_type,
                                      jnode_class=store_json[source_id + "jnodeClass"],
                                      jnode=store_json[source_id + "jnode"],
                                      jnode_html=store_json[source_id + "jnodeHtml"],
                                      left=store_json[source_id + "left"], top=store_json[source_id + "top"], name=name,
                                      input=input, output=output,
                                      variant=variant, public_variant=public_variant, create_on=now_time, status=status, version=version,
                                      create_by=username, group_source_type=group_source_type,
                                      group_target_type=group_target_type, group_left=group_left, group_top=group_top))
                        else:
                            if group_node_no == "":
                                queryset_list.append(
                                    Store(node_no=groupNodeNo, type=store_type, file_name=file_name,
                                          source_id=source_id, target_id=target_id, source_type=source_type,
                                          target_type=target_type,
                                          jnode_class=store_json[source_id + "jnodeClass"],
                                          jnode=store_json[source_id + "jnode"],
                                          jnode_html=store_json[source_id + "jnodeHtml"],
                                          left=store_json[source_id + "left"], top=store_json[source_id + "top"], name=name,
                                          input=input, output=output,
                                          variant=variant, public_variant=public_variant, create_on=now_time, status=status, version=version,
                                          create_by=username, group_source_type=group_source_type,
                                          group_target_type=group_target_type, group_left=group_left, group_top=group_top))
                            else:
                                queryset_list.append(
                                    Store(node_no=groupNodeNo, type=store_type, file_name=file_name,
                                          source_id=source_id, target_id=target_id, source_type=source_type,
                                          target_type=target_type,
                                          jnode_class=store_json[source_id + "jnodeClass"],
                                          jnode=store_json[source_id + "jnode"],
                                          jnode_html=store_json[source_id + "jnodeHtml"],
                                          left=store_json[source_id + "left"], top=store_json[source_id + "top"], name=name,
                                          input=input, output=output,
                                          variant=variant, public_variant=public_variant, create_on=now_time, status=status, version=version,
                                          create_by=username, group=group, group_id=group_id, group_node_no=group_node_no,
                                          group_node_name=group_node_name,
                                          group_source_type=group_source_type, group_target_type=group_target_type,
                                          group_left=group_left, group_top=group_top))
                    Store.objects.bulk_create(queryset_list)
                    try:
                        os.remove(fileName)
                    except Exception:
                        print(Exception)
                used_list = []
                try:
                    used_process = Store.objects.distinct().filter(group=file_name).values('file_name')
                    for used in used_process:
                        used_file_name = used['file_name']
                        used_file_name = used_file_name.replace(".py","")
                        file_names = used_file_name.split("\\", 1)
                        if file_names[0] != "public" and file_names[0] != "release":
                            used_file_name = "Private" + "\\" + file_names[1]
                        elif file_names[0] == "public":
                            used_file_name = used_file_name.replace("public","Public")
                        elif file_names[0] == "release":
                            used_file_name = used_file_name.replace("Release","Public")
                        used_list.append(used_file_name)
                except Exception:
                    print(Exception)
                result['used_list'] = used_list
                return JsonResponse(result)
            except Exception as e:
                exstr = traceback.format_exc()
                logging.error(exstr)
                result["result"] = "error"
                result["step"] = ""
                result["msg"] = gettext("Please check your process!")
                result["error"] = str(e)
                return JsonResponse(result)
    else:
        return render(request, "login.html")

#move file to target folder
@csrf_exempt
def movefile(request):
    if 'username' in request.session and 'password' in request.session:
        username = request.session['username']
        path1 = request.POST.get("path1")
        path2 = request.POST.get("path2")
        result = {}
        try:
            import shutil
            files = path2.split("\\")
            path3 = os.path.dirname(os.path.realpath(__file__)) + "\\pyfile\\" + path1 + "\\" + files[len(files) - 1]
            if os.path.exists(path3):
                result['result'] = "failed"
                result['reason'] = "exist"
            else:
                path4 = path1 + "\\" + files[len(files) - 1]
                Store.objects.filter(file_name=path2).update(file_name=path4)
                path2 = os.path.dirname(os.path.realpath(__file__)) + "\\pyfile\\" + path2
                path1 = os.path.dirname(os.path.realpath(__file__)) + "\\pyfile\\" + path1
                shutil.move(path2,path1)
                result['result'] = "success"
        except:
            result['result'] = "failed"
            result['reason'] = "error"
        return JsonResponse(result)
    else:
        return render(request, "login.html")

#open file list
@csrf_exempt
def openfile(request):
    licenseCheck(request)
    if 'username' in request.session and 'password' in request.session:
        username = request.session['username']
        type = request.GET['type']
        return render(request,'openfile.html',{"type":type,"username":username})
    else:
        return render(request, "login.html")

#open release file list
@csrf_exempt
def releasefile(request):
    if 'username' in request.session and 'password' in request.session:
        username = request.session['username']
        return render(request,'releasefile.html')
    else:
        return render(request, "login.html")




#property input page of user_input
@csrf_exempt
def browseradd(request):
    if 'username' in request.session and 'password' in request.session:
        username = request.session['username']
        return render(request,'browseradd.html')
    else:
        return render(request, "login.html")




#delete user own booked task
@csrf_exempt
def taskdelete(request):
    if 'username' in request.session and 'password' in request.session:
        username = request.session['username']
        language = request.session['language']
        task_id = request.POST.get("task_id")
        msg = ""
        try:
            mappings = TaskInformation.objects.distinct().filter(id=int(task_id)).values('create_by')
            create_by = ""
            try:
                for mapping in mappings:
                    create_by = mapping['create_by']
                if create_by == username:
                    TaskInformation.objects.distinct().filter(id=task_id).delete()
                    msg = gettext("Delete Sucessfully!")
                else:
                    if create_by != "":
                        msg = gettext("You can not delete other's task!")
                    else:
                        msg = gettext("This task is not in system!")
            except:
                msg = gettext("This task is not in system!")
        except:
            msg = gettext("Delete Failed!")
        return JsonResponse({"msg":msg})
    else:
        return render(request, "login.html")






#open user private variants of nodes
@csrf_exempt
def publicvariant(request):
    if 'username' in request.session and 'password' in request.session:
        username = request.session['username']
        type = request.GET['type']
        selectfile = request.GET['selectfile']
        selectfile = selectfile.replace("\\","/")
        return render(request,'publicvariant.html',{"type":type,"selectfile":selectfile})
    else:
        return render(request, "login.html")

#open user private variants of nodes for sub-process
@csrf_exempt
def processvariant(request):
    if 'username' in request.session and 'password' in request.session:
        username = request.session['username']
        selectfile = request.GET['selectfile']
        selectfile = selectfile.replace("\\","/")
        return render(request,'processvariant.html',{"selectfile":selectfile})
    else:
        return render(request, "login.html")

#get file list (menu File->open->public/private/release)
def get_filelist(username, dir, json):
    if os.path.isfile(dir):
        fileName = dir.split("\\")[len(dir.split("\\")) - 1]
        fileName = os.path.splitext(fileName)[0]
        folder = os.path.dirname(os.path.realpath(__file__)) + "\\pyfile\\"
        json['title'] = fileName
        json['text'] = fileName
        json['path'] = dir.replace(folder,"")
        return json
    elif os.path.isdir(dir):
        list = []
        folder = os.path.dirname(os.path.realpath(__file__)) + "\\pyfile\\"
        folder1 = os.path.dirname(os.path.realpath(__file__)) + "\\pyfile\\public"
        folder2 = os.path.dirname(os.path.realpath(__file__)) + "\\pyfile\\public\\"
        folder3 = os.path.dirname(os.path.realpath(__file__)) + "\\pyfile\\release"
        folder4 = os.path.dirname(os.path.realpath(__file__)) + "\\pyfile\\release\\"
        replace_dir = dir.replace(folder2,"").replace(folder1,"")
        replace_dir = replace_dir.replace(folder4, "").replace(folder3, "")
        type = dir.replace(folder, "").split("\\")[0]
        if type != 'release' and type != 'public':
            type = 'private'
        folder_path = dir.replace(folder,"")
        perm = "Draw_Process.views_folder_" + replace_dir
        user = AuthMessage.objects.get(username=username)
        folder_path_length = len(Folder.objects.filter(folder=folder_path).values('folder'))
        if user.has_perm(perm) or replace_dir == "" or folder_path_length == 1 or type == 'private':
            for s in os.listdir(dir):
                newDir = os.path.join(dir, s)
                if ".py" in newDir:
                    list.append(get_filelist(username, newDir, {}))
                else:
                    replace_dir = newDir.replace(folder2, "").replace(folder1, "")
                    replace_dir = replace_dir.replace(folder4, "").replace(folder3, "")
                    folder_path = newDir.replace(folder, "")
                    folder_path_length = len(Folder.objects.filter(folder=folder_path).values('folder'))
                    perm = "Draw_Process.views_folder_" + replace_dir
                    if user.has_perm(perm) or replace_dir == "" or folder_path_length == 1:
                        list.append(get_filelist(username, newDir, {}))
            fileName = dir.split("\\")[len(dir.split("\\")) - 1]
            fileName = os.path.splitext(fileName)[0]
            json['title'] = fileName
            json['text'] = fileName
            json['path'] = dir.replace(folder,"")
            if len(list) > 0:
                json['children'] = list
                json['state'] = "closed"
            else:
                json['children'] = list
                json['iconCls'] = "tree-icon tree-folder "
                json['state'] = "open"
        return json

#search file from file list
def get_filelist2(username, dir, Filelist, search):
    newDir = dir
    if os.path.isfile(dir):
        json = {}
        fileName = dir.split("\\")[len(dir.split("\\")) - 1]
        fileName = os.path.splitext(fileName)[0]
        folder = os.path.dirname(os.path.realpath(__file__)) + "\\pyfile\\"
        if search in fileName:
            json['text'] = fileName
            json['path'] = dir.replace(folder,"")
            Filelist.append(json)
    elif os.path.isdir(dir):
        for s in os.listdir(dir):
            newDir = os.path.join(dir, s)
            get_filelist2(username, newDir, Filelist, search)
        return Filelist

#get file list(menu File->Save->Release)
def get_filelist3(username, dir, json):
    if os.path.isfile(dir):
        fileName = dir.split("\\")[len(dir.split("\\")) - 1]
        fileName = os.path.splitext(fileName)[0]
        folder = os.path.dirname(os.path.realpath(__file__)) + "\\pyfile\\"
        json['title'] = fileName
        json['text'] = fileName
        json['path'] = dir.replace(folder,"")
        json['disabled'] = True
        return json
    elif os.path.isdir(dir):
        list = []
        folder = os.path.dirname(os.path.realpath(__file__)) + "\\pyfile\\"
        folder1 = os.path.dirname(os.path.realpath(__file__)) + "\\pyfile\\public"
        folder2 = os.path.dirname(os.path.realpath(__file__)) + "\\pyfile\\public\\"
        type = dir.replace(folder, "").split("\\")[0]
        if type != 'release' and type != 'public':
            type = 'private'
        folder_path = dir.replace(folder, "")
        folder3 = os.path.dirname(os.path.realpath(__file__)) + "\\pyfile\\release"
        folder4 = os.path.dirname(os.path.realpath(__file__)) + "\\pyfile\\release\\"
        replace_dir = dir.replace(folder2, "").replace(folder1, "")
        replace_dir = replace_dir.replace(folder4, "").replace(folder3, "")
        perm = "Draw_Process.views_folder_" + replace_dir
        user = AuthMessage.objects.get(username=username)
        folder_path_length = len(Folder.objects.filter(folder=folder_path).values('folder'))
        if user.has_perm(perm) or replace_dir == "" or folder_path_length == 1 or type == 'private':
            for s in os.listdir(dir):
                newDir = os.path.join(dir, s)
                if ".py" in newDir:
                    list.append(get_filelist(username, newDir, {}))
                else:
                    replace_dir = dir.replace(folder2, "").replace(folder1, "")
                    replace_dir = replace_dir.replace(folder4, "").replace(folder3, "")
                    folder_path_length = len(Folder.objects.filter(folder=folder_path).values('folder'))
                    perm = "Draw_Process.views_folder_" + replace_dir
                    if user.has_perm(perm) or replace_dir == "" or folder_path_length == 1:
                        list.append(get_filelist3(username, newDir, {}))
            fileName = dir.split("\\")[len(dir.split("\\")) - 1]
            fileName = os.path.splitext(fileName)[0]
            json['title'] = fileName
            json['text'] = fileName
            json['path'] = dir.replace(folder,"")
            if len(list) > 0:
                json['children'] = list
                json['state'] = "closed"
            else:
                json['children'] = list
                json['iconCls'] = "tree-icon tree-folder "
                json['state'] = "open"
        return json

#get file list (menu File->open->public/private/release)
@csrf_exempt
def datalist(request):
    if 'username' in request.session and 'password' in request.session:
        datalist = []
        try:
            username = request.session['username']
            search = request.GET["text"]
            type = request.GET["type"]
            folder = os.path.dirname(os.path.realpath(__file__)) + "\\pyfile\\"
            if type == "private":
                filepath = folder + str(username)
            elif type == "public":
                filepath = folder + "public"
            else:
                filepath = folder + "release"
            if search is None or search == "":
                file_json = get_filelist(username, filepath, {})
                try:
                    datalist = file_json['children']
                except:
                    datalist = []
            else:
                datalist = get_filelist2(username, filepath, [], search)
        except Exception:
            print(Exception)
        return JsonResponse({"rows":datalist})
    else:
        return render(request, "login.html")


#get file list (menu File->save->public/private/release)
@csrf_exempt
def datalist3(request):
    if 'username' in request.session and 'password' in request.session:
        data = []
        try:
            username = request.session['username']
            language = request.session['language']
            type = request.POST.get('type')
            folder = os.path.dirname(os.path.realpath(__file__)) + "\\pyfile"
            if type == "public":
                filepath = folder + "\\public\\"
                relativePath = "public"
                title = gettext("Public")
                file_json = get_tasklist(username, filepath, {})
            else:
                filepath = folder + "\\release\\"
                relativePath = "release"
                file_json = get_filelist3(username, filepath, {})
                title = gettext("Release")
            if file_json is not None:
                try:
                    children = file_json['children']
                    json = {}
                    json['title'] = title
                    json['children'] = children
                    json['path'] = relativePath
                    data.append(json)
                except:
                    children = []
                    json = {}
                    json['title'] = title
                    json['children'] = children
                    json['path'] = relativePath
                    data.append(json)
            else:
                children = []
                json = {}
                json['title'] = title
                json['children'] = children
                json['path'] = relativePath
                data.append(json)
        except Exception:
            print(Exception)
        return JsonResponse({"rows":data})
    else:
        return render(request, "login.html")

#delete process file or folder
@csrf_exempt
def deleteProcess(request):
    if 'username' in request.session and 'password' in request.session:
        try:
            username = request.session['username'].lower()
            language = request.session['language']
            selectfile = request.POST.get("selectfile")
            selectPath = os.path.dirname(os.path.realpath(__file__)) + "\\pyfile\\" + selectfile
            creaters = Store.objects.distinct().filter(file_name=selectfile).values('create_by')
            try:
                creater = creaters[0]['create_by']
                if creater.lower() != username:
                    msg = gettext("You can not delete other's process!")
                    result = {"result": "failed","msg":msg}
                    return JsonResponse(result)
            except:
                pass
            log_delete_username = username
            log_delete_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
            # 删除单个流程log日志
            if ".py" in selectfile:
                try:
                    data_store = Store.objects.filter(create_by=username, file_name=selectfile, status="saved").values(
                        'source_id', 'name', 'node_no', 'jnode_html', 'variant', 'public_variant', 'input', 'output',
                        'group', 'group_id', 'group_node_no', 'status').order_by('node_no', 'group_node_no')
                    if len(data_store) > 0:
                        log_delete_path = selectfile.replace(".py","")
                        for i in range(len(data_store)):
                            data_store[i]["div_id"] = data_store[i]["source_id"]
                            try:
                                data_store[i]["function"] = data_store[i]["jnode_html"].split("id=")[1]
                                data_store[i]["function"] = data_store[i]["function"].split("class=")[0].replace(" ","").replace('"', "")
                            except:
                                data_store[i]["function"] = data_store[i]["jnode_html"].split(">")[1].split("<")[0]
                        robot_code = generateRobotExecuteCode(data_store, 'run')
                        log_delete_nodes = []
                        for single in robot_code:
                            if "import " not in single["code"] and "# coding:utf-8" not in single["code"]:
                                log_delete_nodes.append(single["code"])
                        log_delete_result = "success"
                        log_delete = {}
                        log_delete["action"] = "delete process"
                        try:
                            log_delete["computer name"] = pc_names[username.lower()]
                        except:
                            pass
                        log_delete["username"] = log_delete_username
                        log_delete["time"] = log_delete_time
                        log_delete["path"] = log_delete_path
                        log_delete["process nodes"] = log_delete_nodes
                        log_delete["result"] = log_delete_result
                        log_delete_json = "345>" + json.dumps(log_delete)
                        logger.info(log_delete_json)
                except Exception:
                    pass
            Store.objects.filter(file_name=selectfile).delete()
            if ".py" not in selectfile:
                folder_creater_list = Folder.objects.filter(folder=selectfile).values('create_by')
                if len(folder_creater_list) > 0:
                    folder_creater = folder_creater_list[0]['create_by']
                    if folder_creater.lower() != username:
                        msg = gettext("You can not delete other's folder!")
                        result = {"result": "failed", "msg": msg}
                        return JsonResponse(result)
                    #删除多个流程日志埋点
                    else:
                        file_name_list = Store.objects.filter(create_by=username, file_name__icontains=selectfile+"\\", status="saved").values('file_name')
                        for file_name_dict in file_name_list:
                            try:
                                file_name = file_name_dict["file_name"]
                                data_store = Store.objects.filter(create_by=username, file_name=file_name, status="saved").values('source_id', 'name', 'node_no', 'jnode_html', 'variant', 'public_variant', 'input',
                                    'output','group', 'group_id', 'group_node_no', 'status').order_by('node_no', 'group_node_no')
                                if len(data_store) > 0:
                                    log_delete_path = file_name.replace(".py","")
                                    for i in range(len(data_store)):
                                        data_store[i]["div_id"] = data_store[i]["source_id"]
                                        try:
                                            data_store[i]["function"] = data_store[i]["jnode_html"].split("id=")[1]
                                            data_store[i]["function"] = data_store[i]["function"].split("class=")[0].replace(" ", "").replace('"', "")
                                        except:
                                            data_store[i]["function"] = data_store[i]["jnode_html"].split(">")[1].split("<")[0]
                                    robot_code = generateRobotExecuteCode(data_store, 'run')
                                    log_update_nodes = []
                                    for code_dict in robot_code:
                                        code = code_dict["code"]
                                        if "coding:utf-8" not in code and code[0:6] != "import":
                                            log_update_nodes.append(code)
                                    #logging.info(log_update_nodes)
                                    log_delete_result = "success"
                                    log_deletes = {}
                                    log_deletes["username"] = log_delete_username
                                    log_deletes["time"] = log_delete_time
                                    log_deletes["path"] = log_delete_path
                                    log_deletes["nodes"] = log_update_nodes
                                    log_deletes["result"] = log_delete_result
                                    log_delete_json = "345>" + json.dumps(log_deletes)
                                    logger.info(log_delete_json)
                                    Store.objects.filter(create_by=username, file_name=file_name).delete()
                            except Exception:
                                pass
                else:
                    msg = gettext("You can not delete system folder!")
                    result = {"result": "failed", "msg": msg}
                    return JsonResponse(result)
            Folder.objects.filter(folder=selectfile).delete()
            try:
                os.remove(selectPath)
            except:
                try:
                    os.rmdir(selectPath)
                except:
                    import shutil
                    shutil.rmtree(selectPath)
            result = {"result":"success"}
        except Exception:
            result = {"result":"failed","msg":str(Exception)}
        return JsonResponse(result)
    else:
        return render(request, "login.html")

#get process nodes and the position,variants... of each node from store table
@csrf_exempt
def drawProcess(request):
    if 'username' in request.session and 'password' in request.session:
        try:
            username = request.session['username']
            type = request.POST.get("type")
            selectfile = request.POST.get("selectfile")
            selectfile = selectfile.replace("/","\\")
            if type == "private":
                select_type = username
            else:
                select_type = type
            mappings = Store.objects.filter(file_name=selectfile).values('node_no','source_id','target_id','source_type','target_type','jnode_class','jnode','jnode_html','group','group_id','left','top','name','input','output','variant','public_variant','create_by','version','status')
            result = {}
            list = []
            condition_list = []
            selection_list = []
            node_list = []
            for mapping in mappings:
                nodeNo = mapping["node_no"]
                create_by = mapping["create_by"]
                if nodeNo in node_list:
                    continue
                try:
                    function = mapping["jnode_html"].split("id=")[1]
                    function = function.split("class=")[0].replace(" ", "").replace('"', "")
                except:
                    function = mapping["jnode_html"].split(">")[1].split("<")[0]
                condition_list.append(function)
                if nodeNo is not None and nodeNo != "None":
                    node_list.append(nodeNo)
            if create_by == username:
                extend = "no"
            else:
                extend = "yes"
            selections = SelectInformation.objects.distinct().filter(function__in=condition_list).values('function','variant','value','text','choose')
            for selection in selections:
                json2 = {}
                json2["function"] = selection["function"]
                json2["variant"] = selection["variant"]
                json2["value"] = selection["value"]
                json2["text"] = selection["text"]
                json2["choose"] = selection["choose"]
                selection_list.append(json2)
            node_list = []
            for mapping in mappings:
                nodeNo = mapping["node_no"]
                if nodeNo in node_list and nodeNo is not None and nodeNo != "None":
                    continue
                node_list.append(nodeNo)
                json1 = {}
                version = mapping["version"]
                json1["node_no"] = mapping["node_no"]
                json1["source_id"] = mapping["source_id"]
                json1["target_id"] = mapping["target_id"]
                json1["source_type"] = mapping["source_type"]
                json1["target_type"] = mapping["target_type"]
                json1["jnode_class"] = mapping["jnode_class"]
                json1["jnode"] = mapping["jnode"]
                span = mapping["jnode_html"]
                try:
                    text = span.split("id=")[1]
                    text = text.split("class=")[0].replace(" ", "").replace('"', "")
                    span = '<span id="' + text + '" class="flow-span" title="'+text+'">' + text + '</span>';
                except:
                    text = span.split(">")[1].split("<")[0]
                group = mapping["group"]
                if group:
                    if "\\" in group:
                        if len(Store.objects.distinct().filter(file_name=group, status=None).values("status")) == 0:
                            status = "saved"
                        else:
                            status = ""
                    else:
                        status = "saved"
                else:
                    status = mapping["status"]
                json1["jnode_html"] = span
                json1["left"] = str(int(mapping["left"]))
                json1["top"] = str(int(mapping["top"]))
                json1["name"] = mapping["name"]
                json1["input"] = mapping["input"]
                json1["output"] = mapping["output"]
                json1["variant"] = mapping["variant"]
                json1["status"] = mapping["status"]
                json1["public_variant"] = mapping["public_variant"]
                version = mapping["version"]
                if version != '2.0':
                    if text != 'Start' and text != 'End':
                        json1["status"] = 'saved'
                else:
                    json1["status"] = status
                list.append(json1)
            result['list'] = list
            result['selection_list'] = selection_list
            result['result'] = "success"
            result['extend'] = extend
        except Exception:
            print(Exception)
            result['result'] = "failed"
        return JsonResponse(result)
    else:
        return render(request, "login.html")

#insert-process variant setting,(input field and select field)
@csrf_exempt
def showProcess(request):
    if 'username' in request.session and 'password' in request.session:
        try:
            username = request.session['username']
            try:
                tab = request.POST.get("tab")
            except:
                tab = None
            selectfile = request.POST.get("selectfile")
            selectfile = selectfile.replace("/","\\")
            mappings = Store.objects.filter(file_name=selectfile).values('node_no','source_id','target_id','source_type','target_type','jnode_class','jnode','jnode_html','left','top','name','input','output','variant','public_variant','create_by','group_id','group_node_no')
            result = {}
            list = []
            condition_list = []
            selection_list = []
            create_by = ""
            for mapping in mappings:
                nodeNo = mapping["node_no"]
                create_by = mapping["create_by"]
                try:
                    function = mapping["jnode_html"].split("id=")[1]
                    function = function.split("class=")[0].replace(" ", "").replace('"', "")
                except:
                    function = mapping["jnode_html"].split(">")[1].split("<")[0]
                if function != "Start" and function != "End":
                    condition_list.append(function)
            if create_by.lower() == username.lower():
                default = "yes"
            else:
                default = "no"
            selections = SelectInformation.objects.distinct().filter(function__in=condition_list).values('function','variant','value','text','choose')
            for selection in selections:
                json2 = {}
                json2["function"] = selection["function"]
                json2["variant"] = selection["variant"]
                json2["value"] = selection["value"]
                json2["text"] = selection["text"]
                json2["choose"] = selection["choose"]
                selection_list.append(json2)
            action_variant_json = {}
            actions = Actions.objects.filter(create_by=username, tab=tab).values('div_id','node_no','variant','public_variant','group_id','group_node_no')
            for action in actions:
                div_id = action["div_id"]
                node_no = action['node_no']
                group_id = action['group_id']
                variant = action['variant']
                public_variant = action['public_variant']
                try:
                    variants = json.loads(variant)
                except:
                    variants = {}
                variants_json = {}
                try:
                    items = variants.items()
                except:
                    items = {}
                for key, value in items:
                    variants_json[str(key)] = str(value)
                try:
                    public_variants = json.loads(public_variant)
                except:
                    public_variants = {}
                public_variants_json = {}
                if str(public_variants) != "{}" and str(public_variants) != "":
                    try:
                        items2 = public_variants.items()
                    except:
                        items2 = {}
                    for key, value in items2:
                        try:
                            public_variants_json[str(key)] = variants_json[str(key)]
                        except:
                            public_variants_json[str(key)] = str(value)
                    action_variant_json[div_id] = json.dumps(public_variants_json)
            for mapping in mappings:
                json1 = {}
                node_no = mapping["node_no"]
                source_id = mapping["source_id"]
                json1["node_no"] = mapping["node_no"]
                json1["source_id"] = mapping["source_id"]
                json1["target_id"] = mapping["target_id"]
                json1["source_type"] = mapping["source_type"]
                json1["target_type"] = mapping["target_type"]
                json1["jnode_class"] = mapping["jnode_class"]
                json1["jnode"] = mapping["jnode"]
                json1["jnode_html"] = mapping["jnode_html"]
                json1["left"] = mapping["left"]
                json1["top"] = mapping["top"]
                json1["name"] = mapping["name"]
                json1["input"] = mapping["input"]
                json1["output"] = mapping["output"]
                json1["variant"] = mapping["variant"]
                public_variant = mapping["public_variant"]
                try:
                    json1["public_variant"] = action_variant_json[source_id]
                except:
                    if public_variant != "" and public_variant != "{}" and public_variant is not None and default == "yes":
                        variants = json.loads(mapping["variant"])
                        variants_json = {}
                        try:
                            items = variants.items()
                        except:
                            items = {}
                        for key, value in items:
                            variants_json[str(key)] = str(value)
                        public_variants = json.loads(public_variant)
                        public_variants_json = {}
                        try:
                            items2 = public_variants.items()
                        except:
                            items2 = {}
                        for key, value in items2:
                            try:
                                public_variants_json[str(key)] = variants_json[str(key)]
                            except:
                                public_variants_json[str(key)] = str(value)
                        json1["public_variant"] = json.dumps(public_variants_json)
                    else:
                        json1["public_variant"] = mapping["public_variant"]
                list.append(json1)
            result['list'] = list
            result['selection_list'] = selection_list
            result['result'] = "success"
            result['default'] = default
        except Exception:
            print(Exception)
            result['result'] = "failed"
        return JsonResponse(result)
    else:
        return render(request, "login.html")

@csrf_exempt
def transfervariant(request):
    if 'username' in request.session and 'password' in request.session:
        try:
            username = request.session['username']
            type = request.POST.get("type")
            selectfile = request.POST.get("selectfile")
            if type == "private":
                select_type = username
            else:
                select_type = type
            try:
                tab = int(request.POST.get("tab"))
            except:
                tab = None
            mappings = Store.objects.filter(file_name=selectfile).values('node_no','source_id','target_id','source_type','target_type','jnode_class','jnode','jnode_html','left','top','name','input','output','variant','public_variant','group','group_id','group_node_no','group_node_name','group_source_type','group_target_type','group_left','group_top','status').order_by('node_no','group_node_no')
            result = {}
            worklist = []
            now_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            json1 = {}
            list = []
            for mapping in mappings:
                try:
                    function = mapping["jnode_html"].split("id=")[1]
                    function = function.split("class=")[0].replace(" ","").replace('"',"")
                except:
                    function = mapping["jnode_html"].split(">")[1].split("<")[0]
                try:
                    nodeNo = mapping["node_no"]
                    json1[int(nodeNo)] = function
                    groupId = mapping['group_id']
                    if groupId is not None and groupId != "":
                        groupNodeNo = int(mapping['group_node_no'])
                        node_no = str(nodeNo) + "-" + str(groupNodeNo)
                        function = mapping['group_node_name']
                        json1[int(nodeNo)] = function
                except:
                    continue
            for mapping in mappings:
                groupId = mapping['group_id']
                try:
                    nodeNo = int(mapping["node_no"])
                    try:
                        function = mapping["jnode_html"].split("id=")[1]
                        function = function.split("class=")[0].replace(" ", "").replace('"', "")
                    except:
                        function = mapping["jnode_html"].split(">")[1].split("<")[0]
                    if groupId is not None and groupId != "":
                        groupNodeNo = int(mapping['group_node_no'])
                        last_nodeNo = int(nodeNo) - 1
                        node_no = str(nodeNo) + "-" + str(groupNodeNo)
                        last_node_no = str(nodeNo) + "-" + str(groupNodeNo - 1)
                        next_nodeNo = int(nodeNo) + 1
                        next_node_no = str(nodeNo) + "-" + str(groupNodeNo + 1)
                        function = mapping['group_node_name']
                        try:
                            json1[node_no + "lastFunction"] = json1[last_nodeNo]
                        except:
                            json1[node_no + "nextFunction"] = json1[last_node_no]
                        try:
                            json1[node_no + "nextFunction"] = json1[next_nodeNo]
                        except:
                            json1[node_no + "nextFunction"] = json1[next_node_no]
                except:
                    continue
            for mapping in mappings:
                groupId = mapping['group_id']
                nodeNo = str(mapping["node_no"])
                if nodeNo is None or nodeNo == "None":
                    nodeNo = ""
                    sourceId = mapping["source_id"]
                    try:
                        sourceId = request.POST.get(sourceId)
                        if sourceId is None or sourceId == "":
                            sourceId = mapping["source_id"]
                    except:
                        sourceId = mapping["source_id"]
                else:
                    sourceId = mapping["source_id"]
                    try:
                        sourceId = request.POST.get(sourceId)
                        if sourceId is None or sourceId == "":
                            sourceId = mapping["source_id"]
                    except:
                        sourceId = mapping["source_id"]
                    if groupId is not None and groupId != "":
                        try:
                            groupId = request.POST.get(mapping["source_id"])
                            if groupId is None or groupId == "":
                                groupId = mapping["source_id"]
                        except:
                            groupId = mapping["source_id"]
                        sourceId = mapping['group_id']
                        group = mapping["group"]
                        groupNodeNo = int(mapping['group_node_no'])
                        node_no = str(nodeNo) + "-" + str(groupNodeNo)
                    else:
                        sourceId = mapping["source_id"]
                        try:
                            sourceId = request.POST.get(sourceId)
                            if sourceId is None or sourceId == "":
                                sourceId = mapping["source_id"]
                        except:
                            sourceId = mapping["source_id"]
                        node_no = nodeNo
                try:
                    function = mapping["jnode_html"].split("id=")[1]
                    function = function.split("class=")[0].replace(" ", "").replace('"', "")
                except:
                    function = mapping["jnode_html"].split(">")[1].split("<")[0]
                name = mapping["name"]
                input = mapping["input"]
                output = mapping["output"]
                variant = mapping["variant"]
                publicVariant = mapping["public_variant"]
                group_source_type = mapping["group_source_type"]
                group_target_type = mapping["group_target_type"]
                group_left = mapping["group_left"]
                group_top = mapping["group_top"]
                status = mapping["status"]
                if function != "Start" and function != "End" and nodeNo != "":
                    try:
                        nextNode = json1[node_no + "nextFunction"]
                        lastNode = json1[node_no + "lastFunction"]
                    except:
                        # 部长搞的特别奇怪的流程，这里因为json没有对应的号码，所以会报错
                        try:
                            nextNode = json1[int(nodeNo) + 1]
                        except:
                            nextNode = ""
                        try:
                            lastNode = json1[int(nodeNo) - 1]
                        except:
                            lastNode = ""
                    if groupId is not None and groupId != "":
                        if groupId not in list:
                            list.append(groupId)
                        function = mapping["group_node_name"]
                        worklist.append(
                            Actions(div_id=sourceId, node_no=nodeNo, function=function, name=name, last_node=lastNode,
                                    next_node=nextNode, input=input, output=output, variant=variant, public_variant=publicVariant,
                                    create_on=now_time, create_by=username, group_id=groupId, group=group, group_node_no=groupNodeNo,
                                    group_source_type=group_source_type, group_target_type=group_target_type, group_left=group_left, group_top=group_top, tab=tab))
                    else:
                        list.append(sourceId)
                        worklist.append(
                            Actions(div_id=sourceId, node_no=nodeNo, function=function, name=name, last_node=lastNode, next_node=nextNode,
                                  input=input, output=output, variant=variant, public_variant=publicVariant, create_on=now_time, create_by=username, status=status, tab=tab))
                elif nodeNo == "":
                    worklist.append(
                        Actions(div_id=sourceId, function=function, name=name, last_node="",
                                next_node="",
                                input=input, output=output, variant=variant, public_variant=publicVariant,
                                create_on=now_time, create_by=username, status=status, tab=tab))
            Actions.objects.filter(create_by=username, tab=tab).delete()
            Actions.objects.bulk_create(worklist)
            result['result'] = "success"
            result['list'] = list
        except Exception:
            print(Exception)
            result['result'] = "failed"
        return JsonResponse(result)
    else:
        return render(request, "login.html")

@csrf_exempt
def publictransfer(request):
    if 'username' in request.session and 'password' in request.session:
        try:
            username = request.session['username']
            list = request.POST.getlist('list[]')
            try:
                tab = int(request.POST.get('tab'))
            except:
                tab = None
            json1 = {}
            now_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            selectInformations = SelectInformation.objects.distinct().filter(choose=1).values('function', 'variant', 'value')
            information_json = {}
            infromation_list = []
            for selectInformation in selectInformations:
                function = selectInformation['function']
                variant = selectInformation['variant']
                value = selectInformation['value']
                information_json[function + "-" + variant] = value
                infromation_list.append(function + "-" + variant)
            for i in range(len(list)):
                public_json = json.loads(list[i])
                nodeNo = public_json["node_no"]
                try:
                    function = public_json["jnode_html"].split(">")[1]
                    function = function.split("<")[0]
                except:
                    function = public_json["jnode_html"].replace("<span>", "").replace("</span>", "")
                json1[int(nodeNo)] = function
            worklist = []
            result = {}
            result_list = []
            for i in range(len(list)):
                mapping = json.loads(list[i])
                sourceId = request.POST.get(mapping["source_id"])
                nodeNo = mapping["node_no"]
                try:
                    function = mapping["jnode_html"].split("id=")[1]
                    function = function.split("class=")[0].replace(" ", "").replace('"', "")
                except:
                    function = mapping["jnode_html"].split(">")[1].split("<")[0]
                name = mapping["name"]
                input = mapping["input"]
                output = mapping["output"]
                variant = mapping["variant"]
                try:
                    variants = json.loads(variant)
                    items = variants.items()
                    variant_json = {}
                    for key, value in items:
                        select_inf = function + "-" + str(key)
                        if select_inf in infromation_list:
                            if value == "" or value is None:
                                variant_json[str(key)] = information_json[select_inf]
                            else:
                                variant_json[str(key)] = str(value)
                        else:
                            variant_json[str(key)] = str(value)
                    variant = json.dumps(variant_json)
                except:
                    variant = {}
                publicVariant = mapping["public_variant"]
                if function != "Start" and function != "End":
                    result_list.append(sourceId)
                    nextNode = json1[int(nodeNo) + 1]
                    lastNode = json1[int(nodeNo) - 1]
                    worklist.append(
                        Actions(div_id = sourceId, node_no = nodeNo, function = function, name = name, last_node = lastNode, next_node = nextNode,
                              input = input, output = output, variant = variant, public_variant = publicVariant, create_on = now_time, create_by=username, tab=tab))
            Actions.objects.filter(create_by=username,tab=tab).delete()
            Actions.objects.bulk_create(worklist)
            result['result'] = "success"
            result['list'] = result_list
        except Exception:
            print(Exception)
            result['result'] = "failed"
        return JsonResponse(result)
    else:
        return render(request, "login.html")

def export(request):
    if 'username' in request.session and 'password' in request.session:
        username = request.session['username']
        return render(request,'pyfile.html')
    else:
        return render(request, "login.html")

@csrf_exempt
def imageclip(request):
    if 'username' in request.session and 'password' in request.session:
        try:
            username = request.session['username']
            language = request.session['language']
            images = AuthMessage.objects.filter(username=username).values('sex','image_url')
            try:
                imageSrc = images[0]['image_url']
            except:
                imageSrc = '../static/images/user/user1.jpg'
            return render(request, 'imageclip.html', {"imageSrc": imageSrc, "language":language})
        except Exception as e:
            message = "Image load failed!" + str(e)
            return JsonResponse({"result": "false", "message": message})
    else:
        return render(request, "login.html")

@csrf_exempt
def time_sleep(request):
    if 'username' in request.session and 'password' in request.session:
        time.sleep(1)
        return HttpResponse("1")
    else:
        return render(request, "login.html")







import socket
import sys, time
import subprocess
import threading


@csrf_exempt
def getfilepath(request):
    if 'username' in request.session and 'password' in request.session:
        BUF_SIZE = 1024  # 设置缓冲区大小
        server_addr = ('127.0.0.1', 31500)  # IP和端口构成表示地址
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # 生成一个新的socket对象
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # 设置地址复用
        server.bind(server_addr)  # 绑定地址
        server.listen(5)  # 监听, 最大监听数为5

        result = {}
        result['result'] = 'success'
        path = settings.File_Root + "\\Draw_Process\\" +"filepathui.exe"
        #subprocess.Popen(r'D:\pyworksapce\OpenfileClient\dist\filepathui.exe')
        subprocess.Popen(path)
        client, client_addr = server.accept()  # 接收TCP连接, 并返回新的套接字和地址

        data = client.recv(BUF_SIZE)  # 从客户端接收数据
        result['filepath'] = bytes.decode(data,encoding='utf-8')
        server.close()

        return JsonResponse(result)
    else:
        return render(request, "login.html")

@csrf_exempt
def groupSteps(request):
    if 'username' in request.session and 'password' in request.session:
        try:
            username = request.session['username']
            steps = request.POST.getlist('steps[]')
            group = request.POST.get("group")
            groupId = request.POST.get("groupId")
            tab = int(request.POST.get("tab"))
            group_steps = Actions.objects.distinct().filter(create_by=username, div_id__in=steps, tab=tab).values('div_id','node_no','last_node','next_node').order_by('node_no')
            num = int(request.POST.get("length"))
            startID = request.POST.get('startID')
            ids = []
            # adjust the process sequence
            for i in range(num):
                try:
                    nextID = request.POST.get(startID)
                    process = request.POST.get(nextID+"text")
                    nodeNo = int(request.POST.get(nextID + "nodeNo"))
                    if process == "End":
                        break
                    Actions.objects.filter(div_id=nextID, create_by=username.lower(), tab=tab).update(node_no=nodeNo)
                    Actions.objects.filter(group_id=nextID, create_by=username.lower(), tab=tab).update(node_no=nodeNo)
                    ids.append(nextID)
                    startID = nextID
                except:
                    continue
            ids_sql = Actions.objects.filter(create_by=username.lower(), tab=tab).values('div_id', 'group_id')
            for id_json in ids_sql:
                id = id_json['div_id']
                group_id = id_json['group_id']
                if id not in ids:
                    if group_id not in ids:
                        Actions.objects.filter(div_id=id, tab=tab).update(node_no=None)
            for i in range(len(group_steps)):
                if i == 0:
                    start_node = group_steps[i]["node_no"]
                    last_node = group_steps[i]["last_node"]
                elif i == len(group_steps) - 1:
                    end_node = group_steps[i]["node_no"]
                    next_node = group_steps[i]["next_node"]
            for i in range(len(group_steps)):
                divId = group_steps[i]["div_id"]
                nodeNo = group_steps[i]["node_no"]
                Actions.objects.distinct().filter(create_by=username, tab=tab, div_id=divId).update(node_no=start_node,last_node=last_node,next_node=next_node,group=group,group_id=groupId,group_node_no=nodeNo,group_source_type=request.POST.get(divId+"-sourceType"),group_target_type=request.POST.get(divId+"-targetType"),group_left=request.POST.get(divId+"-left"),group_top=request.POST.get(divId+"-top"))
            gt_steps = Actions.objects.distinct().filter(create_by=username, tab=tab, node_no__gt=end_node).values('div_id','node_no')
            for gt_step in gt_steps:
                node_no = int(gt_step['node_no']) - len(steps) + 1
                div_id = gt_step['div_id']
                Actions.objects.distinct().filter(create_by=username, tab=tab, div_id=div_id).update(node_no=node_no)
            result = {"status":"success"}
        except Exception as e:
            result = {"status":"error","msg":str(e)}
        return JsonResponse(result)
    else:
        return render(request, "login.html")

@csrf_exempt
def breakUpSteps(request):
    if 'username' in request.session and 'password' in request.session:
        try:
            username = request.session["username"]
            id = request.POST.get("id")
            tab = int(request.POST.get("tab"))
            group_steps = Actions.objects.distinct().filter(create_by=username, group_id=id, tab=tab).values('div_id','function','node_no','name','group_source_type','group_target_type','group_left','group_top').order_by('group_node_no')
            group_list = []
            id_json = {}
            nodeNo = ""
            for group_step in group_steps:
                id = group_step["div_id"]
                nodeNo = group_step["node_no"]
                import uuid
                new_id = str(uuid.uuid1())
                Actions.objects.distinct().filter(create_by=username, div_id=id, tab=tab).update(div_id=new_id)
                id_json[id] = new_id
            if nodeNo:
                adj_nodes = Actions.objects.distinct().filter(create_by=username, node_no__gte=nodeNo, tab=tab).values('div_id','node_no','group_node_no')
                for adj_node in adj_nodes:
                    div_id = adj_node['div_id']
                    node_no = adj_node['node_no']
                    if node_no > nodeNo:
                        new_node_no = node_no + len(group_steps) - 1
                        Actions.objects.distinct().filter(create_by=username, div_id=div_id, tab=tab).update(node_no=new_node_no,group=None,group_id=None,group_node_no=None,group_source_type=None,group_target_type=None,group_left=None,group_top=None)
                    else:
                        group_node_no = adj_node['group_node_no']
                        Actions.objects.distinct().filter(create_by=username, div_id=div_id, tab=tab).update(node_no=group_node_no,group=None,group_id=None,group_node_no=None,group_source_type=None,group_target_type=None,group_left=None,group_top=None)
            for group_step in group_steps:
                group_json = {}
                group_json["id"] = id_json[group_step["div_id"]]
                group_json["orgId"] = group_step["div_id"]
                group_json["name"] = group_step["name"]
                group_json["functionName"] = group_step["function"]
                group_json["sourceType"] = group_step["group_source_type"]
                group_json["targetType"] = group_step["group_target_type"]
                group_json["left"] = group_step["group_left"]
                group_json["top"] = group_step["group_top"]
                group_list.append(group_json)
            result = {"status":"success","list":group_list}
        except Exception as e:
            result = {"status":"error","msg":str(e)}
        return JsonResponse(result)
    else:
        return render(request, "login.html")

#判断是否有子流程
@csrf_exempt
def judgeSubProcess(request):
    if 'username' in request.session and 'password' in request.session:
        try:
            filePath = request.POST.get("filePath")
            if len(Store.objects.filter(file_name=filePath).exclude(group=None).values("node_no")) > 0:
                return HttpResponse("true")
            else:
                return HttpResponse("false")
        except Exception as e:
            return HttpResponse("true")
    else:
        return render(request, "login.html")