# coding=utf-8
import socket
import time
import struct
import uuid as uid
import win32api
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from dwebsocket.decorators import accept_websocket
from django.contrib.auth import authenticate
from Draw_Process.models import RobotInfo
from Draw_Process.views import generateProcessCode, saveVariantForSetPassword
from Draw_Process.views import setPc
from Draw_Process.models import AuthMessage
from Draw_Process.models import TaskResult
from Draw_Process.models import TaskInformation
from Draw_Process.models import Department
from Draw_Process.models import Actions
import threading
import json
import logging
import os
from Python_Platform import settings
import datetime
from Timetasks import timetasksviews
from django.utils.translation import gettext
from Timetasks.timetasksviews import book_time_json
import hashlib

logger = logging.getLogger('log')

#initial all robot status
RobotInfo.objects.all().update(robot_status=1,file_path="")

# 存储连接websocket的用户
clients = {}
port = {}
pc_names = {}


def isMatch(s: str, p: str) -> bool:
    lp, ls = len(p), len(s)
    dp = [set() for _ in range(lp + 1)]
    dp[0].add(-1)
    for i in range(lp):
        if p[i] == '?':
            for x in dp[i]:
                if x + 1 < ls:
                    dp[i + 1].add(x + 1)
        elif p[i] == '*':
            minx = ls
            for x in dp[i]: minx = min(minx, x)
            while minx < ls:
                dp[i + 1].add(minx)
                minx += 1
        else:
            for x in dp[i]:
                if x + 1 < ls and s[x + 1] == p[i]:
                    dp[i + 1].add(x + 1)
    if ls - 1 in dp[-1]:
        return True
    return False


def xstr(s):
    if s is None:
        return ''
    else:
        return s

def returnCommanderResult(username,msg,status):
    if clients.__contains__(str(username) + "html"):  # 控制端的设计器和本地机器人
        if clients[str(username) + "html"] is not None:
            user_websocket = clients[str(username) + "html"]
            result = {"action": "commander", "msg": msg, "result":status}
            user_websocket.send(json.dumps(result))

@accept_websocket
def rpadesignstudio(request): #接收网页的消息，主要有连接，运行，target
    print('rpadesignstudio! (%s)' % threading.currentThread())
    try:
        username = request.session['username']
    except:
        pass
    try:
        if request.is_websocket():
            while 1:
                """
                大数据传输时，前台会自动分帧，后台要接收完整后才运行
                """
                message = request.websocket.wait()
                msg_test = str(message, encoding="utf-8")
                if msg_test != "":
                    try:
                        # 通过判断能否转成json，确定接收数据是否完整
                        json.loads(msg_test)
                    except Exception as e:
                        message_temp = ""
                        while message_temp is not None:
                            try:
                                message_temp = request.websocket.read()
                            except Exception as e:
                                # 'Unknown opcode 0(fin:0, data:b\'11eb-87a0-bd67436a5d\')'
                                remaining_message = str(e)
                                b = remaining_message.find('data:b\'') + len('data:')
                                c = remaining_message.rfind(')')
                                remaining_message = eval(str(remaining_message[b:c]))
                                message = message + remaining_message
                                continue
                print('while ----')
                if message:
                    msg_2_str = str(message, encoding="utf-8")
                    if msg_2_str != "":
                        msg_2_json = json.loads(msg_2_str)
                        action = msg_2_json['action']
                        if action == "quit":
                            if clients.__contains__(str(username) + "html"):
                                if clients[username + "html"] is not None:
                                    del clients[str(username) + "html"]
                            logger.info(username + "studio  design exit ----")
                            return request.websocket.close()
                        elif action == "connect":
                            clients[str(username) + "html"] = request.websocket  # 保存web 的websocket 的实例
                            logger.info(username + 'connect sucessfull ----')
                        elif action == "run":
                            try:
                                username = request.session['username']
                                selectfile = msg_2_json['selectfile']
                                try:  # commander直接执行其他用户机器人
                                    cmd_username = msg_2_json['username']
                                    try:
                                        if clients.__contains__(str(cmd_username)):  # 机器人是不是在线
                                            if clients[str(cmd_username)] is not None:
                                                robot_status = \
                                                RobotInfo.objects.filter(robot_name="robot_" + cmd_username).values(
                                                    "robot_status")[0]['robot_status']  # 获取机器人状态
                                                if robot_status == 1:
                                                    result = {"action": "get_connection", "result": "off-line"}
                                                    request.websocket.send(json.dumps(result))
                                                elif robot_status == 3:
                                                    result = {"action": "get_connection", "result": "busy"}
                                                    request.websocket.send(json.dumps(result))
                                                elif robot_status == 2:  # 判断机器人当前状态是否空闲
                                                    robotname = "robot_" + cmd_username
                                                    filepath = selectfile.split("\\")
                                                    if len(filepath) > 0:
                                                        fileName = filepath[len(filepath) - 1]
                                                    nowtime = datetime.datetime.now().replace(microsecond=0)
                                                    ip = request.session['ip']
                                                    TaskInformation.objects.create(pc_name=robotname, sequence=1.0,
                                                                                   create_by=username,
                                                                                   task_name="", file_path=selectfile,
                                                                                   file_name=fileName,
                                                                                   method="time", booked_time=nowtime,
                                                                                   create_on=nowtime,
                                                                                   start_time=nowtime, ip_address=ip,
                                                                                   status='running')
                                                    userid = \
                                                    AuthMessage.objects.filter(username=cmd_username).values('id')[0][
                                                        'id']
                                                    RobotInfo.objects.filter(user_id=userid).update(robot_status=3,
                                                                                                    file_path=selectfile)
                                                    path = settings.File_Root + "\\Draw_Process\\pyfile\\" + selectfile
                                                    result = {}
                                                    code = ""
                                                    with open(path, encoding='utf-8') as f:
                                                        data = f.readlines()
                                                    logger_code = ""
                                                    for i in range(len(data)):
                                                        code = code + data[i]
                                                        if "utf-8" not in data[i] and data[i][0:6] != "import":
                                                            logger_code+=data[i]
                                                    if logger_code[len(logger_code)-1:len(logger_code)] == "\n":
                                                        logger_code = logger_code[0:len(logger_code)-1]
                                                    #获取私钥
                                                    if "General_Module.SetPassword" in code  and os.path.exists(settings.File_Root + "\\Draw_Process\\pems\\" + str(cmd_username).lower() + ".pem"):
                                                        choclead_secret_key = ""
                                                        with open(settings.File_Root + "\\Draw_Process\\pems\\" + str(cmd_username).lower() + ".pem", "r") as f:
                                                            secret_key_data = f.readlines()
                                                            for content in secret_key_data:
                                                                choclead_secret_key += content.replace("\n", "")
                                                            result['choclead_secret_key'] = choclead_secret_key

                                                    result['code'] = code
                                                    result['result'] = 'success'
                                                    result['username'] = cmd_username
                                                    websocket = clients[cmd_username]
                                                    RobotInfo.objects.filter(user_id=userid).update(robot_status=3,
                                                                                                    file_path=selectfile)
                                                    user_websocket = clients[cmd_username]
                                                    result['action'] = action
                                                    result['commander'] = username
                                                    result['booked_time'] = nowtime.strftime("%Y-%m-%d %H:%M:%S")
                                                    result['selectfile'] = selectfile
                                                    msg = gettext("Relase task successfully!")
                                                    threads = [threading.Thread(target=returnCommanderResult,
                                                                                args=(username, msg, "success",))]
                                                    for t in threads:
                                                        t.start()
                                                    log_commander_json = {}
                                                    log_commander_json["action"] = "commander"
                                                    try:
                                                        log_commander_json["computer name"] = pc_names[username.lower()]
                                                    except:
                                                        pass
                                                    log_commander_json["username"] = username
                                                    log_commander_json["time"] = str(nowtime.strftime("%Y-%m-%d %H:%M:%S"))
                                                    log_commander_json["commander user"] = cmd_username
                                                    log_commander_json["commander time"] = str(nowtime.strftime("%Y-%m-%d %H:%M:%S"))
                                                    log_commander_json["process nodes"] = logger_code
                                                    logger.info("500>" + json.dumps(log_commander_json))
                                                    log_file_path = settings.File_Root + "\\logs\\info-" + str(nowtime.strftime("%Y-%m-%d")) + ".log"
                                                    log_folder_path = settings.File_Root + "\\logs"
                                                    if os.path.exists(log_folder_path):
                                                        if not os.path.exists(log_file_path):
                                                            with open(log_file_path, "w", encoding="utf-8"):
                                                                pass
                                                        with open(log_file_path, "r", encoding="utf-8") as f:
                                                            log_lines_num = len(f.readlines())
                                                        result['log_lines_num'] = log_lines_num
                                                    user_websocket.send(json.dumps(result))
                                            else:
                                                result = {"action": "get_connection", "result": "off-line"}
                                                request.websocket.send(json.dumps(result))
                                        else:
                                            result = {"action": "get_connection", "result": "off-line"}
                                            request.websocket.send(json.dumps(result))
                                    except Exception as e:
                                        logger.error(str(e))
                                        msg = gettext("Relase task failed!")
                                        threads = [threading.Thread(target=returnCommanderResult.start,
                                                                        args=(username, msg, "error",))]
                                        for t in threads:
                                            t.start()
                                except:
                                    robot_status = RobotInfo.objects.filter(robot_name="robot_" + username).values("robot_status")[0]['robot_status']  # 获取机器人状态
                                    if  robot_status != 3 :
                                        studioip = request.session['ip']  # studio 的IP
                                        userid = AuthMessage.objects.filter(username=username).values('id')[0]['id']
                                        userip = RobotInfo.objects.filter(user_id=userid).values('reverse1')[0]['reverse1']
                                        uuid = RobotInfo.objects.filter(user_id=userid).values('reverse2')[0]['reverse2']
                                        # 数据库
                                        mac = RobotInfo.objects.filter(user_id=userid).values('mac')[0]['mac']
                                        # 实际
                                        mc = msg_2_json['mc']
                                        studiouuid = msg_2_json['uuid']
                                        mac_true = False
                                        try:
                                            mac_list = []
                                            mac.split("_")
                                            for i in mac.split("_"):
                                                if "mac" in i or "amount" in i:
                                                    pass
                                                else:
                                                    mac_list.append(i)

                                            mc_list = []
                                            mc.split("_")
                                            for i in mc.split("_"):
                                                if "mac" in i or "amount" in i:
                                                    pass
                                                else:
                                                    mc_list.append(i)

                                            if len(mac) == len(mc):
                                                if mac == mc:
                                                    mac_true = True
                                            elif len(mac) > len(mc):
                                                mac_true = True
                                                for j in mc_list:
                                                    if j not in mac_list:
                                                        mac_true = False
                                                        break
                                            elif len(mac) < len(mc):
                                                mac_true = True
                                                for j in mac_list:
                                                    if j not in mc_list:
                                                        mac_true = False
                                                        break
                                        except:
                                            pass
                                        try:
                                            logger.info('Run-------' + " studioip:" + studioip +  " userip:" + userip + " mac:" +mac + " mc:"+ mc +" studiouuid:" + studiouuid + " uuid" + uuid)
                                        except:
                                            pass
                                        if studioip == userip or mac_true:
                                            username = request.session['username']
                                            connections = msg_2_json['connections']
                                            result = generateProcessCode(username, connections, "run")
                                            userid = AuthMessage.objects.filter(username=username).values('id')[0]['id']
                                            if clients.__contains__(username): #本地设计器和本地机器人
                                                if clients[str(username).lower()] is not None:
                                                    log_run = {}
                                                    log_run["action"] = "run process"
                                                    try:
                                                        log_run["computer name"] = pc_names[username.lower()]
                                                    except:
                                                        pass
                                                    log_run_username = username
                                                    log_run_time1 = time.strftime('%Y-%m-%d', time.localtime(time.time()))
                                                    log_run_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
                                                    log_run_path = selectfile
                                                    if len(log_run_path) > 7 and log_run_path[0:7] == "Private":
                                                        log_run_path = log_run_path.replace("Private",username.lower())
                                                    codeResult = result['result']
                                                    log_run_nodes = []
                                                    # 获取私钥
                                                    if "General_Module.SetPassword" in str(result["code"]) and os.path.exists(settings.File_Root + "\\Draw_Process\\pems\\" + str(username).lower() + ".pem"):
                                                        choclead_secret_key = ""
                                                        with open(settings.File_Root + "\\Draw_Process\\pems\\" + str(username).lower() + ".pem", "r") as f:
                                                            secret_key_data = f.readlines()
                                                            for content in secret_key_data:
                                                                choclead_secret_key += content.replace("\n", "")
                                                            result['choclead_secret_key'] = choclead_secret_key

                                                    for single in result["code"]:
                                                        if "import " not in single["code"] and "# coding:utf-8" not in single["code"]:
                                                            log_run_nodes.append(single["code"])
                                                    log_run["username"] = log_run_username
                                                    log_run["time"] = log_run_time
                                                    log_run["path"] = log_run_path
                                                    log_run["process nodes"] = log_run_nodes
                                                    log_run_json = "200>" + json.dumps(log_run)
                                                    logger.info(log_run_json)
                                                    # 获取行数
                                                    log_file_path = settings.File_Root + "\\logs\\info-" + str(log_run_time1) + ".log"
                                                    log_folder_path = settings.File_Root + "\\logs"
                                                    if os.path.exists(log_folder_path):
                                                        if not os.path.exists(log_file_path):
                                                            with open(log_file_path, "w", encoding="utf-8"):
                                                                pass
                                                        with open(log_file_path, "r", encoding="utf-8") as f:
                                                            log_lines_num = len(f.readlines())
                                                        result['log_lines_num'] = log_lines_num
                                                        result['log_run_time1'] = log_run_time1
                                                        result['log_run_time'] = log_run_time
                                                    if codeResult == "success":
                                                        RobotInfo.objects.filter(user_id=userid).update(robot_status=3,
                                                                                                        file_path=selectfile)
                                                        user_websocket = clients[str(username).lower()]
                                                        result['action'] = action
                                                        logger.info(' Send code to Robot--')
                                                        user_websocket.send(json.dumps(result))
                                                    else:
                                                        logger.info('Code has problem--')
                                                        request.websocket.send(json.dumps(result))
                                            else: #本地机器人也不在线
                                                logger.info(' owner robot do not online')
                                                result = {"action": "get_connection", "result": "error"}
                                                request.websocket.send(json.dumps(result))
                                        else:  #远程设计器不能运行机器人
                                            logger.info(' romote studio design can not run ')
                                            result = {"action": "get_connection", "result": "error"}
                                            request.websocket.send(json.dumps(result))
                                    else:
                                        print("robot_status is busy now")
                                        result_response = {"action": "run", "result": "busy", "msg":"The robot status is busy now<br>1.Please Input \"Esc\" to exit immediately!<br>2.Please Input \"Pause & Break\" to pause(Waiting for the previous step to complete, the next step will be paused to run) and exit later!<br>3.Please wait for the last process to finish running"}
                                        request.websocket.send(json.dumps(result_response))
                            except Exception:
                                username = msg_2_json['username']
                                RobotInfo.objects.filter(user_id=userid).update(robot_status=2, file_path="")
                                clients[str(username) + "html"].send(json.dumps(msg_2_json))
                        elif action == "sap_target":
                            try:
                                username = request.session['username']
                                try:
                                    user_websocket = clients[str(username).lower()]
                                    userid = AuthMessage.objects.filter(username=username).values('id')[0]['id']
                                    RobotInfo.objects.filter(user_id=userid).update(robot_status=3)
                                    result = {}
                                    result['username'] = username
                                    result['action'] = action
                                    user_websocket.send(json.dumps(result))
                                except:
                                    result = {"action": "get_connection", "result": "error"}
                                    request.websocket.send(json.dumps(result))
                            except Exception:
                                username = msg_2_json['username']
                                userid = AuthMessage.objects.filter(username=username).values('id')[0]['id']
                                RobotInfo.objects.filter(user_id=userid).update(robot_status=2)
                                clients[str(username) + ' html'].send(json.dumps(msg_2_json))
                        elif action == "web_target":
                            try:
                                username = request.session['username']
                                try:
                                    user_websocket = clients[str(username).lower()]
                                    userid = AuthMessage.objects.filter(username=username).values('id')[0]['id']
                                    RobotInfo.objects.filter(user_id=userid).update(robot_status=3)
                                    result = {}
                                    browser = msg_2_json['browser']
                                    result['username'] = username
                                    result['action'] = action
                                    result['browser'] = browser
                                    result['delay'] = msg_2_json['delay']
                                    user_websocket.send(json.dumps(result))
                                except:
                                    result = {"action": "get_connection", "result": "error"}
                                    request.websocket.send(json.dumps(result))
                            except Exception:
                                username = msg_2_json['username']
                                userid = AuthMessage.objects.filter(username=username).values('id')[0]['id']
                                RobotInfo.objects.filter(user_id=userid).update(robot_status=2)
                                clients[str(username) + ' html'].send(json.dumps(msg_2_json))
                        elif action == "sap_record":
                            try:
                                username = request.session['username']
                                try:
                                    user_websocket = clients[str(username).lower()]
                                    userid = AuthMessage.objects.filter(username=username).values('id')[0]['id']
                                    RobotInfo.objects.filter(user_id=userid).update(robot_status=3)
                                    result = {}
                                    result['username'] = username
                                    result['action'] = action
                                    result['record'] = msg_2_json['record']
                                    result['auto'] = msg_2_json['auto']
                                    if msg_2_json['record'] == 1:
                                        logger.info(str(username) + " 开启SAP录制")
                                    else:
                                        logger.info(str(username) + " 关闭SAP录制")
                                    user_websocket.send(json.dumps(result))
                                except:
                                    result = {"action": "get_connection", "result": "error"}
                                    request.websocket.send(json.dumps(result))
                            except Exception:
                                username = msg_2_json['username']
                                userid = AuthMessage.objects.filter(username=username).values('id')[0]['id']
                                RobotInfo.objects.filter(user_id=userid).update(robot_status=2)
                                clients[str(username) + ' html'].send(json.dumps(msg_2_json))
                        elif action == "chrome_record":
                            try:
                                username = request.session['username']
                                try:
                                    user_websocket = clients[str(username).lower()]
                                    userid = AuthMessage.objects.filter(username=username).values('id')[0]['id']
                                    RobotInfo.objects.filter(user_id=userid).update(robot_status=3)
                                    result = {}
                                    result['username'] = username
                                    result['action'] = action
                                    result['record'] = msg_2_json['record']
                                    result['auto'] = msg_2_json['auto']
                                    if msg_2_json['record'] == 1:
                                        logger.info(str(username) + " 开启Chrome录制")
                                    else:
                                        logger.info(str(username) + " 关闭Chrome录制")
                                    user_websocket.send(json.dumps(result))
                                except:
                                    result = {"action": "get_connection", "result": "error"}
                                    request.websocket.send(json.dumps(result))
                            except Exception:
                                username = msg_2_json['username']
                                userid = AuthMessage.objects.filter(username=username).values('id')[0]['id']
                                RobotInfo.objects.filter(user_id=userid).update(robot_status=2)
                                clients[str(username) + ' html'].send(json.dumps(msg_2_json))
                        elif action == "web_crawl":
                            try:
                                username = request.session['username']
                                try:
                                    user_websocket = clients[str(username).lower()]
                                    userid = AuthMessage.objects.filter(username=username).values('id')[0]['id']
                                    RobotInfo.objects.filter(user_id=userid).update(robot_status=3)
                                    result = {}
                                    result['username'] = username
                                    result['action'] = action
                                    result['browser'] = msg_2_json['browser']
                                    user_websocket.send(json.dumps(result))
                                except:
                                    result = {"action": "get_connection", "result": "error"}
                                    request.websocket.send(json.dumps(result))
                            except Exception:
                                username = msg_2_json['username']
                                userid = AuthMessage.objects.filter(username=username).values('id')[0]['id']
                                RobotInfo.objects.filter(user_id=userid).update(robot_status=2)
                                clients[str(username) + ' html'].send(json.dumps(msg_2_json))
                        elif action == "handle_target":
                            try:
                                username = request.session['username']
                                try:
                                    user_websocket = clients[str(username).lower()]
                                    userid = AuthMessage.objects.filter(username=username).values('id')[0]['id']
                                    RobotInfo.objects.filter(user_id=userid).update(robot_status=3)
                                    result = {}
                                    result['username'] = username
                                    result['action'] = action
                                    user_websocket.send(json.dumps(result))
                                except:
                                    result = {"action": "get_connection", "result": "error"}
                                    request.websocket.send(json.dumps(result))
                            except Exception:
                                username = msg_2_json['username']
                                userid = AuthMessage.objects.filter(username=username).values('id')[0]['id']
                                RobotInfo.objects.filter(user_id=userid).update(robot_status=2)
                                clients[str(username) + ' html'].send(json.dumps(msg_2_json))
                        elif action == "icon_target":
                            try:
                                username = request.session['username']
                                try:
                                    user_websocket = clients[str(username).lower()]
                                    userid = AuthMessage.objects.filter(username=username).values('id')[0]['id']
                                    RobotInfo.objects.filter(user_id=userid).update(robot_status=3)
                                    result = {}
                                    result['username'] = username
                                    result['action'] = action
                                    result['position'] = msg_2_json['position']
                                    result['delay'] = msg_2_json['delay']
                                    user_websocket.send(json.dumps(result))
                                except:
                                    result = {"action": "get_connection", "result": "error"}
                                    request.websocket.send(json.dumps(result))
                            except Exception:
                                username = msg_2_json['username']
                                userid = AuthMessage.objects.filter(username=username).values('id')[0]['id']
                                RobotInfo.objects.filter(user_id=userid).update(robot_status=2)
                                clients[str(username) + ' html'].send(json.dumps(msg_2_json))
                        elif action == "icon_coordinate_target":
                            try:
                                username = request.session['username']
                                try:
                                    user_websocket = clients[str(username).lower()]
                                    userid = AuthMessage.objects.filter(username=username).values('id')[0]['id']
                                    RobotInfo.objects.filter(user_id=userid).update(robot_status=3)
                                    result = {}
                                    result['username'] = username
                                    result['action'] = action
                                    result['delay'] = msg_2_json['delay']
                                    user_websocket.send(json.dumps(result))
                                except:
                                    result = {"action": "get_connection", "result": "error"}
                                    request.websocket.send(json.dumps(result))
                            except Exception:
                                username = msg_2_json['username']
                                userid = AuthMessage.objects.filter(username=username).values('id')[0]['id']
                                RobotInfo.objects.filter(user_id=userid).update(robot_status=2)
                                clients[str(username) + ' html'].send(json.dumps(msg_2_json))
                        elif action == "mouse_target":
                            try:
                                username = request.session['username']
                                try:
                                    user_websocket = clients[str(username).lower()]
                                    userid = AuthMessage.objects.filter(username=username).values('id')[0]['id']
                                    RobotInfo.objects.filter(user_id=userid).update(robot_status=3)
                                    result = {}
                                    result['username'] = username
                                    result['action'] = action
                                    result['method'] = msg_2_json['method']
                                    user_websocket.send(json.dumps(result))
                                except:
                                    result = {"action": "get_connection", "result": "error"}
                                    request.websocket.send(json.dumps(result))
                            except Exception:
                                username = msg_2_json['username']
                                userid = AuthMessage.objects.filter(username=username).values('id')[0]['id']
                                RobotInfo.objects.filter(user_id=userid).update(robot_status=2)
                                clients[str(username) + ' html'].send(json.dumps(msg_2_json))
                        elif action == "web_dragging_mouse_target":
                            try:
                                username = request.session['username']
                                try:
                                    user_websocket = clients[str(username).lower()]
                                    userid = AuthMessage.objects.filter(username=username).values('id')[0]['id']
                                    RobotInfo.objects.filter(user_id=userid).update(robot_status=3)
                                    result = {}
                                    result['username'] = username
                                    result['action'] = action
                                    result['method'] = msg_2_json['method']
                                    user_websocket.send(json.dumps(result))
                                except:
                                    result = {"action": "get_connection", "result": "error"}
                                    request.websocket.send(json.dumps(result))
                            except Exception:
                                username = msg_2_json['username']
                                userid = AuthMessage.objects.filter(username=username).values('id')[0]['id']
                                RobotInfo.objects.filter(user_id=userid).update(robot_status=2)
                                clients[str(username) + ' html'].send(json.dumps(msg_2_json))
    except Exception as a:
        b = str(a)
        username = request.session['username']
        userid = AuthMessage.objects.filter(username=username).values('id')[0]['id']
        userip = RobotInfo.objects.filter(user_id=userid).values('reverse1')[0]['reverse1']
        if clients.__contains__(str(username) + "html"):
            if clients[str(username) + "html"] is not None:
                del clients[str(username) + "html"]
        print(username + '浏览器异常退出了 ----')

password_secret_key = None

@accept_websocket
# 20210318：由于笔记本双网卡，新增uuid验证
# 20210329: UUID取消，修改get_macaddress写法
def websocketLink(request):
    print('websocketLink! (%s)' % threading.currentThread())
    if request.is_websocket:
        while 1:
            try:
                message = request.websocket.wait()
            except:
                return request.websocket.close()
            try:
                now_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                if message:
                    print(request.websocket, now_time, message)
                    msg_2_str = str(message, encoding="utf-8")
                    if msg_2_str != "":
                        msg_2_json = json.loads(msg_2_str)
                        action = msg_2_json['action']
                        if action == "secret_key_result":
                            password_result = msg_2_json['result']
                            global password_secret_key
                            if password_result == "success":
                                password_secret_key = msg_2_json['secret_key']
                            else:
                                password_secret_key = "error"
                        if action == "check_mac":
                            mac = msg_2_json['mac']
                            ip= msg_2_json['ip']
                            uuid = msg_2_json['uuid']
                            try:
                                new_path = settings.File_Root + "\\Client\\ChocLead.exe"
                                info = win32api.GetFileVersionInfo(new_path, os.sep)
                                ms = info['FileVersionMS']
                                ls = info['FileVersionLS']
                                version = '%d%d%d%d' % (win32api.HIWORD(ms), win32api.LOWORD(ms), win32api.HIWORD(ls), win32api.LOWORD(ls))
                                res_version = int(version)
                            except Exception as e:
                                res_version = 0
                            try:
                                # 双网卡，先通过mac地址查找user_id
                                try:
                                    user_id = RobotInfo.objects.filter(mac=mac).values('user_id')[0]['user_id']
                                    if len(RobotInfo.objects.filter(mac=mac).values('user_id')) >=2:
                                        request.websocket.send(json.dumps({"result":'duplicateMac',"versions":res_version}))
                                        break
                                except:
                                    user_id = None
                                # #双网卡，使用mac地址网卡二时，上述user_id查找不到，使用uuid查找user_id # 20210329: UUID取消，修改get_macaddress写法
                                # if user_id is None:
                                #     user_id = RobotInfo.objects.filter(reverse2=uuid).values('user_id')[0]['user_id']
                                #     if len(RobotInfo.objects.filter(reverse2=uuid).values('user_id')) >=2:
                                #         request.websocket.send('duplicateUuid')
                                #         break
                                # #mac_all虚拟网卡增加/减少的情况，找到匹配的user_id
                                mac_change = False
                                user_id_list = []
                                #新增设备/设备网卡变更(增删改),针对无法通过注册表获取mac(netifaces获取所有mac,含有标识mac_amount)
                                if user_id is None and "mac_amount" in mac:
                                    try:
                                        mac_list = []
                                        mac.split("_")
                                        for i in mac.split("_"):
                                            if "mac" in i or "amount" in i:
                                                pass
                                            else:
                                                mac_list.append(i)
                                    except:
                                        pass
                                    user_id_mac_all = RobotInfo.objects.filter(mac__isnull=False).values('user_id','mac')
                                    for i in user_id_mac_all:
                                        mac_true_login = False
                                        if i["mac"] != '' and "mac_amount" in i["mac"]:
                                            macdb_list = []
                                            i["mac"].split("_")
                                            for j in i["mac"].split("_"):
                                                if "mac" in j or "amount" in j:
                                                    pass
                                                else:
                                                    macdb_list.append(j)
                                            #减少网卡
                                            if len(i["mac"]) > len(mac):
                                                mac_true_login = True
                                                for k in mac_list:
                                                    if k not in macdb_list:
                                                        mac_true_login = False
                                                        break

                                            #新增网卡
                                            elif len(i["mac"]) < len(mac):
                                                mac_true_login = True
                                                for k in macdb_list:
                                                    if k not in mac_list:
                                                        mac_true_login = False
                                                        break
                                            #网卡变更(改)
                                            # TODO:网卡变更存在恶意篡改授权的漏洞,暂未支持网卡变更
                                            elif len(i["mac"]) == len(mac):
                                                if i["mac"] == mac:
                                                    mac_true_login = True
                                            if mac_true_login is True:
                                                user_id_list.append(i["user_id"])
                                    if len(user_id_list) == 1:
                                        mac_change = True
                                        user_id = user_id_list[0]
                                    elif len(user_id_list) >= 2:
                                        request.websocket.send(json.dumps({"result":'similarMac',"versions":res_version}))
                                        break
                                # 针对可以通过注册表获取mac(不含有标识mac_amount),此类mac更新覆盖原mac_amount写法
                                # 针对碧彩等客户数据库更新
                                elif user_id is None and "mac_amount" not in mac:
                                    user_id = RobotInfo.objects.filter(mac__icontains=mac).values('user_id')[0]['user_id']
                                    if len(RobotInfo.objects.filter(mac__icontains=mac).values('user_id')) == 1:
                                        mac_change = True
                                    if len(RobotInfo.objects.filter(mac__icontains=mac).values('user_id')) >= 2:
                                        request.websocket.send(json.dumps({"result":'similarMac',"versions":res_version}))
                                        break
                                username = AuthMessage.objects.filter(id=user_id).values('username')[0]['username']
                                clients[str(username).lower()] = request.websocket
                                # # 对于老用户，uuid为空，则更新相应uuid # 20210329: UUID取消，修改get_macaddress写法
                                # if  RobotInfo.objects.filter(user_id=user_id).values('reverse2')[0]['reverse2'] is None or RobotInfo.objects.filter(user_id=user_id).values('reverse2')[0]['reverse2'] == '':
                                #     RobotInfo.objects.filter(user_id=user_id).update(robot_status=2,reverse2=uuid, reverse1=ip)  # 机器人登录成功后，机器人在线空闲
                                #如果新增/减少虚拟网卡（网卡发生变更），则更新相应mac地址
                                if mac_change is True and user_id is not None:
                                    RobotInfo.objects.filter(user_id=user_id).update(robot_status=2, mac=mac,reverse1=ip)  # 机器人登录成功后，机器人在线空闲
                                    mac_change = False
                                # 如手动从数据库置空mac，mac为空，则更新相应mac
                                if  RobotInfo.objects.filter(user_id=user_id).values('mac')[0]['mac'] is None or RobotInfo.objects.filter(user_id=user_id).values('mac')[0]['mac'] == '':
                                    RobotInfo.objects.filter(user_id=user_id).update(robot_status=2,mac=mac, reverse1=ip)  # 机器人登录成功后，机器人在线空闲
                                else:
                                    # 双网卡，只更新ip，不更新mac
                                    RobotInfo.objects.filter(user_id=user_id).update(robot_status=2,
                                                                                     reverse1=ip)  # 机器人登录成功后，机器人在线空闲


                                port[username] = msg_2_json['port']
                                logger.info(username + '客服端登录成功' + "机器人空闲")
                                try:
                                    pc_names[username.lower()] = msg_2_json['hostname']
                                    setPc(pc_names)
                                except:
                                    pass
                                request.websocket.send(json.dumps({"result":str(username),"versions":res_version}))
                                timetasksviews.getexpiredesttask("robot_" + str(username))  # 过期最严重的任务
                            except Exception as e:
                                request.websocket.send(json.dumps({"result":'no',"versions":res_version}))
                            try:
                                custom_versions = msg_2_json["custom_versions"]
                            except:
                                custom_versions = 10000000
                            if custom_versions < res_version:
                                share_dir = settings.File_Root + "\\Client"
                                phone = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                                phone.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                                setting_file = settings.File_Root + "\\Draw_Process" + "\\setting.txt"
                                with open(setting_file, "r")as f:
                                    content = f.readline()
                                    index1 = content.find("//")
                                    index2 = content.rfind(":")
                                    address = content[index1 + 2:index2]
                                phone.bind((address, 9000))
                                phone.listen(5)
                                while True:
                                    conn, client_addr = phone.accept()
                                    while True:
                                        res = conn.recv(1024)
                                        if not res:
                                            continue
                                        cmds = res.decode('utf-8')  # ['get','1.mp4']
                                        if cmds:
                                            filename = "ChocLead.exe"  # '1.mp4'
                                            header_dic = {
                                                'filename': filename,
                                                'file_size': os.path.getsize('{}/{}'.format(share_dir, filename))
                                            }
                                            header_json = json.dumps(header_dic)  # 序列化为byte字节流类型
                                            header_bytes = header_json.encode('utf-8')  # 编码为utf-8（Mac系统）
                                            conn.send(struct.pack('i', len(header_bytes)))
                                            conn.send(header_bytes)
                                            with open('{}/{}'.format(share_dir, filename), 'rb') as f:
                                                for line in f:
                                                    conn.send(line)
                                            break
                                    phone.close()
                                    break
                                phone.close()
                        elif action == "check_user":
                            mac = msg_2_json['mac']
                            username = msg_2_json['username']
                            password = msg_2_json['password']
                            ip = msg_2_json['ip']
                            uuid = msg_2_json['uuid']
                            user = authenticate(request, username=username, password=password)
                            if user is not None:
                                try:
                                    user_id = user.id
                                    try:
                                        robot_info = user.robotinfo
                                        org_mac = robot_info.mac
                                        org_uuid = robot_info.reverse2
                                        # 数据库内的mac字段为空，则更新
                                        try:
                                            pc_names[username.lower()] = msg_2_json['hostname']
                                            setPc(pc_names)
                                        except:
                                            pass
                                        if org_mac == None or org_mac == '':
                                            RobotInfo.objects.filter(user_id=user_id).update(mac=mac, robot_status=2,reverse1=ip,reverse2=uuid)
                                            clients[str(username).lower()] = request.websocket
                                        else:
                                            # if mac == org_mac:
                                            #     clients[str(username)] = request.websocket
                                            #     port[username] = msg_2_json['port']
                                            #     request.websocket.send('success')
                                            #     RobotInfo.objects.filter(user_id=user_id).update(
                                            #         robot_status=2)  # 机器人登录成功后，机器人在线空闲
                                            #     logger.info(username + '客服端检查用户名' + "机器人空闲")
                                            # else:
                                            request.websocket.send('different')
                                    except Exception as e:
                                        logger.error(e)
                                        try:
                                            RobotInfo.objects.create(robot_name="robot_" + username, user_id=user_id,
                                                                     mac=mac, reverse2=uuid, robot_status=2)
                                        except:
                                            return
                                except Exception as e:
                                    logger.error(e)
                                request.websocket.send('success')
                            else:
                                check_time = msg_2_json['time']
                                if check_time == 3:
                                    error_msg = "exit"
                                else:
                                    remaining = 3 - int(check_time)
                                    if remaining == 1:
                                        error_msg = str(remaining) + " remaining time"
                                    else:
                                        error_msg = str(remaining) + " remaining times"
                                request.websocket.send(error_msg)
                        elif action == "run":

                            username = msg_2_json['username']
                            logger.info(username + ' robot runsult----' )
                            commander = msg_2_json['commander']
                            userid = AuthMessage.objects.filter(username=username).values('id')[0]['id']
                            RobotInfo.objects.filter(user_id=userid).update(robot_status=2, file_path="")
                            if commander != "":
                                booked_time_str = msg_2_json['booked_time']
                                booked_time = datetime.datetime.strptime(booked_time_str, "%Y-%m-%d %H:%M:%S")
                                task_information = TaskInformation.objects.filter(pc_name="robot_" + str(username),
                                                                                  create_by=commander,
                                                                                  booked_time=booked_time).values(
                                    "file_path", "file_name", "booked_time", "start_time", "create_on", "create_by",
                                    "ip_address")
                                if len(task_information) > 0:
                                    file_path = task_information[0]['file_path']
                                    file_name = task_information[0]['file_name']
                                    booked_time = task_information[0]['booked_time']
                                    start_time = task_information[0]['start_time']
                                    create_on = task_information[0]['create_on']
                                    create_by = task_information[0]['create_by']
                                    ip_address = task_information[0]['ip_address']
                                    result = msg_2_json['result']
                                    try:
                                        conso = msg_2_json['conso']
                                        msg = msg_2_json['msg']
                                        node = msg_2_json['node']
                                    except:
                                        conso = ""
                                        msg = ""
                                        node = ""
                                    try:
                                        log_lines_num = msg_2_json['log_lines_num']
                                    except:
                                        log_lines_num = ""
                                    if booked_time:
                                        log_file_path = settings.File_Root + "\\logs\\info-" + str(booked_time)[:10] + ".log"
                                        if os.path.exists(log_file_path) and log_lines_num:
                                            with open(log_file_path, "r", encoding="utf-8") as f:
                                                data_list = f.readlines()
                                                if int(log_lines_num) > 1:
                                                    if "500>" in data_list[int(log_lines_num) - 1] and str(booked_time) in data_list[int(log_lines_num) - 1] and str(username) in data_list[int(log_lines_num) - 1]:
                                                        index = data_list[int(log_lines_num) - 1].find("{")
                                                        log_info = data_list[int(log_lines_num) - 1][index::].replace(">", "")
                                                        log_info_2_json = json.loads(log_info)
                                                        log_info_exclude_info = data_list[int(log_lines_num) - 1][0:index]
                                                        log_info_2_json["result"] = result
                                                        if result != "success":
                                                            log_info_2_json["error step"] = msg
                                                            log_info_2_json["error node"] = node
                                                            log_info_2_json["error message"] = conso
                                                        data_list[int(log_lines_num) - 1] = log_info_exclude_info + json.dumps(log_info_2_json) + "\n"
                                                else:
                                                    for i, content in enumerate(data_list):
                                                        if "500>" in content and str(booked_time) in content and str(username) in content:
                                                            index = content.find("{")
                                                            log_info = content[index::].replace(">", "")
                                                            log_info_2_json = json.loads(log_info)
                                                            log_info_exclude_info = content[0:index]
                                                            log_info_2_json["result"] = result
                                                            if result != "success":
                                                                log_info_2_json["error step"] = msg
                                                                log_info_2_json["error node"] = node
                                                                log_info_2_json["error message"] = conso
                                                            data_list[i] = log_info_exclude_info + json.dumps(log_info_2_json) + "\n"
                                                            break
                                            with open(log_file_path, "w", encoding="utf-8") as ff:
                                                ff.writelines(data_list)
                                    TaskInformation.objects.filter(pc_name="robot_" + str(username),
                                                                   create_by=commander,
                                                                   booked_time=booked_time).delete()
                                    nowtime = datetime.datetime.now().replace(microsecond=0)
                                    TaskResult.objects.create(pc_name="robot_" + str(username), create_by=create_by,
                                                              task_name="", file_path=file_path, file_name=file_name,
                                                              result=result, status="unread", step=msg, message=conso,
                                                              start_time=start_time, end_time=nowtime,
                                                              create_on=create_on,
                                                              ip_address=ip_address)
                            else:
                                log_run_result = msg_2_json['result']
                                try:
                                    log_run_message = gettext(msg_2_json['conso'])
                                    log_run_step = gettext(msg_2_json['msg'])
                                    log_run_node = msg_2_json['node']
                                except:
                                    log_run_message = ""
                                    log_run_step = ""
                                    log_run_node = ""
                                try:
                                    log_lines_num = msg_2_json['log_lines_num']
                                    log_run_time1 = msg_2_json['log_run_time1']
                                    log_run_time = msg_2_json['log_run_time']
                                except:
                                    log_lines_num = ""
                                    log_run_time1 = ""
                                    log_run_time = ""
                                if log_run_time1 and log_run_time:
                                    log_file_path = settings.File_Root + "\\logs\\info-" + str(log_run_time1) + ".log"
                                    if os.path.exists(log_file_path) and log_lines_num:
                                        with open(log_file_path,"r",encoding="utf-8") as f:
                                            data_list = f.readlines()
                                            if int(log_lines_num) > 1:
                                                if "200>" in data_list[int(log_lines_num)-1] and str(log_run_time) in data_list[int(log_lines_num)-1] and str(username) in data_list[int(log_lines_num)-1]:
                                                    index = data_list[int(log_lines_num)-1].find("{")
                                                    log_info = data_list[int(log_lines_num)-1][index::].replace(">", "")
                                                    log_info_2_json = json.loads(log_info)
                                                    log_info_exclude_info = data_list[int(log_lines_num)-1][0:index]
                                                    log_info_2_json["result"] = log_run_result
                                                    if log_run_result != "success":
                                                        log_info_2_json["error step"] = log_run_step
                                                        log_info_2_json["error node"] = log_run_node
                                                        log_info_2_json["error message"] = log_run_message
                                                    data_list[int(log_lines_num)-1] = log_info_exclude_info + json.dumps(log_info_2_json) + "\n"
                                            else:
                                                for i, content in enumerate(data_list):
                                                    if "200>" in content and str(booked_time) in content and str(username) in content:
                                                        index = content.find("{")
                                                        log_info = content[index::].replace(">", "")
                                                        log_info_2_json = json.loads(log_info)
                                                        log_info_exclude_info = content[0:index]
                                                        log_info_2_json["result"] = result
                                                        if result != "success":
                                                            log_info_2_json["error step"] = log_run_step
                                                            log_info_2_json["error node"] = log_run_node
                                                            log_info_2_json["error message"] = log_run_message
                                                        data_list[i] = log_info_exclude_info + json.dumps(log_info_2_json) + "\n"
                                                        break
                                        with open(log_file_path,"w",encoding="utf-8") as ff:
                                            ff.writelines(data_list)
                                logger.info(username + 'robot runsult1----')
                                if clients.__contains__(str(username) + "html"):  # 设计器是不是在线
                                    logger.info(username + "html" + ' studio is online')
                                    if clients[str(username) + "html"] is not None:
                                        logger.info(username + "html" + ' send result to Studio result')
                                        clients[str(username) + "html"].send(json.dumps(msg_2_json))
                                else:
                                    logger.info(username + 'studio is not online----')
                        elif action == "run_result":  # 定时任务运行结果
                            try:
                                username = msg_2_json['username']
                                start_time = msg_2_json['start_time']
                                end_time = msg_2_json['end_time']
                                taskname = msg_2_json['taskname']
                                result = msg_2_json['result']
                                clientip = msg_2_json['runtaskoi']
                                try:
                                    step = msg_2_json['msg']
                                except:
                                    step = ""
                                try:
                                    msg = json.loads(msg_2_json['conso'])
                                    line = msg["line"]
                                    code = msg["code"]
                                    message = msg["conso"]
                                except:
                                    msg = ""
                                    line = ""
                                    code = ""
                                    message = ""
                                try:
                                    taskid = TaskInformation.objects.distinct().filter(task_name=taskname).values("id")[0]["id"]
                                    booked_time = TaskInformation.objects.distinct().filter(task_name=taskname).values("booked_time")[0]["booked_time"]
                                except Exception:
                                    taskid = ""
                                    booked_time = ""
                                try:
                                    booked_line = book_time_json[str(taskid)]
                                except:
                                    booked_line = ""
                                if taskid:
                                    log_file_path = settings.File_Root + "\\logs\\info-" + str(booked_time)[0:10] + ".log"
                                    if os.path.exists(log_file_path):
                                        with open(log_file_path,"r",encoding="utf-8") as f:
                                            data_list = f.readlines()
                                            if booked_line:
                                                if "400>" in data_list[booked_line] or "500>" in data_list[booked_line] and str(booked_time) in data_list[booked_line]:
                                                    index = data_list[booked_line].find("{")
                                                    log_info = data_list[booked_line][index::].replace(">", "")
                                                    log_info_2_json = json.loads(log_info)
                                                    log_info_exclude_info = data_list[booked_line][0:index]
                                                    log_info_2_json["result"] = result
                                                    if result != "success":
                                                        log_info_2_json["error step"] = step
                                                        log_info_2_json["error node"] = line
                                                        if code[len(code)-1:len(code)] == "\n":
                                                            code = code[0:len(code)-1]
                                                        log_info_2_json["error code"] = code
                                                        log_info_2_json["error message"] = message
                                                    data_list[booked_line] = log_info_exclude_info + json.dumps(log_info_2_json) + "\n"
                                            else:
                                                for i,content in enumerate(data_list):
                                                    if "400>" in content or "500>" in content and str(booked_time) in content and taskname in content:
                                                        index = content.find("{")
                                                        log_info = content[index::].replace(">", "")
                                                        log_info_2_json = json.loads(log_info)
                                                        log_info_exclude_info = content[0:index]
                                                        log_info_2_json["result"] = result
                                                        if result != "success":
                                                            log_info_2_json["error step"] = step
                                                            log_info_2_json["error node"] = line
                                                            if code[len(code) - 1:len(code)] == "\n":
                                                                code = code[0:len(code) - 1]
                                                            log_info_2_json["error code"] = code
                                                            log_info_2_json["error message"] = message
                                                        data_list[i] = log_info_exclude_info + json.dumps(log_info_2_json) + "\n"
                                                        break
                                        with open(log_file_path,"w",encoding="utf-8") as ff:
                                            ff.writelines(data_list)
                                logger.info('（6）------定时任务运行结果-----'+ username + "定时任务完成了，机器人空闲")
                                userid = AuthMessage.objects.filter(username=username).values('id')[0]['id']
                                RobotInfo.objects.filter(user_id=userid).update(robot_status=2)
                                timetasksviews.timetaskResult(username, "robot_" + str(username), taskname, result,
                                                              start_time, end_time, msg, clientip, step)
                                timetasksviews.getexpiredesttask("robot_" + str(username))  # 过期最严重的任务
                            except Exception as e:
                                userid = AuthMessage.objects.filter(username=username).values('id')[0]['id']
                                RobotInfo.objects.filter(user_id=userid).update(robot_status=2)
                                timetasksviews.getexpiredesttask("robot_" + str(username))  # 过期最严重的任务
                        elif action == "cycle_result":  # 循环任务运行结果
                            try:
                                username = msg_2_json['username']
                                start_time = msg_2_json['start_time']
                                end_time = msg_2_json['end_time']
                                taskname = msg_2_json['taskname']
                                result = msg_2_json['result']
                                clientip = msg_2_json['runtaskoi']
                                try:
                                    step = msg_2_json['msg']
                                except:
                                    step = ""
                                try:
                                    msg = json.loads(msg_2_json['conso'])
                                    line = msg["line"]
                                    code = msg["code"]
                                    message = msg["conso"]
                                except:
                                    msg = ""
                                    line = ""
                                    code = ""
                                    message = ""
                                logger.info(username + "循环任务完成了，机器人空闲")
                                try:
                                    taskid = TaskInformation.objects.distinct().filter(task_name=taskname).values("id")[0]["id"]
                                    booked_time = TaskInformation.objects.distinct().filter(task_name=taskname).values("booked_time")[0]["booked_time"]
                                except Exception:
                                    taskid = ""
                                    booked_time = ""
                                try:
                                    booked_line = book_time_json[str(taskid)]
                                except:
                                    booked_line = ""
                                if taskid:
                                    log_file_path = settings.File_Root + "\\logs\\info-" + str(booked_time)[0:10] + ".log"
                                    if os.path.exists(log_file_path):
                                        with open(log_file_path,"r",encoding="utf-8") as f:
                                            data_list = f.readlines()
                                            if booked_line:
                                                if "400>" in data_list[booked_line] or "500>" in data_list[booked_line] and str(booked_time) in data_list[booked_line]:
                                                    index = data_list[booked_line].find("{")
                                                    log_info = data_list[booked_line][index::].replace(">", "")
                                                    log_info_2_json = json.loads(log_info)
                                                    log_info_exclude_info = data_list[booked_line][0:index]
                                                    log_info_2_json[str(start_time) + " result"] = result
                                                    if result != "success":
                                                        log_info_2_json[str(start_time) + " error step"] = step
                                                        log_info_2_json[str(start_time) + " error node"] = line
                                                        if code[len(code)-1:len(code)] == "\n":
                                                            code = code[0:len(code)-1]
                                                        log_info_2_json[str(start_time) + " error code"] = code
                                                        log_info_2_json[str(start_time) + " error message"] = message
                                                    data_list[booked_line] = log_info_exclude_info + json.dumps(log_info_2_json) + "\n"
                                            else:
                                                for i,content in enumerate(data_list):
                                                    if "400>" in content or "500>" in content and str(booked_time) in content:
                                                        index = content.find("{")
                                                        log_info = content[index::].replace(">", "")
                                                        log_info_2_json = json.loads(log_info)
                                                        log_info_exclude_info = content[0:index]
                                                        log_info_2_json[str(start_time) + " result"] = result
                                                        if result != "success":
                                                            log_info_2_json[str(start_time) + " error step"] = step
                                                            log_info_2_json[str(start_time) + " error node"] = line
                                                            if code[len(code) - 1:len(code)] == "\n":
                                                                code = code[0:len(code) - 1]
                                                            log_info_2_json[str(start_time) + " error code"] = code
                                                            log_info_2_json[str(start_time) + " error message"] = message
                                                        data_list[i] = log_info_exclude_info + json.dumps(log_info_2_json) + "\n"
                                                        break
                                        with open(log_file_path,"w",encoding="utf-8") as ff:
                                            ff.writelines(data_list)
                                userid = AuthMessage.objects.filter(username=username).values('id')[0]['id']
                                RobotInfo.objects.filter(user_id=userid).update(robot_status=2)
                                timetasksviews.CycleTaskResult (username, "robot_" + str(username), taskname, result,
                                                              start_time, end_time, msg, clientip, step)

                            except Exception as e:
                               logger.error(username + "循环任务异常" + str(e))
                        elif action == "sap_target":
                            try:
                                username = request.session['username']
                                try:
                                    user_websocket = clients[str(username).lower()]
                                    userid = AuthMessage.objects.filter(username=username).values('id')[0]['id']
                                    RobotInfo.objects.filter(user_id=userid).update(robot_status=3)
                                    result = {}
                                    result['username'] = username
                                    result['action'] = action
                                    user_websocket.send(json.dumps(result))
                                except:
                                    result = {"action": "get_connection", "result": "error"}
                                    request.websocket.send(json.dumps(result))
                            except Exception:
                                username = msg_2_json['username']
                                userid = AuthMessage.objects.filter(username=username).values('id')[0]['id']
                                RobotInfo.objects.filter(user_id=userid).update(robot_status=2)
                                clients[str(username) + 'html'].send(json.dumps(msg_2_json))
                        elif action == "web_target":
                            try:
                                username = request.session['username']
                                try:
                                    user_websocket = clients[str(username).lower()]
                                    userid = AuthMessage.objects.filter(username=username).values('id')[0]['id']
                                    RobotInfo.objects.filter(user_id=userid).update(robot_status=3)
                                    result = {}
                                    result['username'] = username
                                    result['action'] = action
                                    user_websocket.send(json.dumps(result))
                                except:
                                    result = {"action": "get_connection", "result": "error"}
                                    request.websocket.send(json.dumps(result))
                            except Exception:
                                username = msg_2_json['username']
                                userid = AuthMessage.objects.filter(username=username).values('id')[0]['id']
                                RobotInfo.objects.filter(user_id=userid).update(robot_status=2)
                                clients[str(username) + 'html'].send(json.dumps(msg_2_json))
                        elif action == "sap_record":
                            try:
                                username = request.session['username']
                                try:
                                    user_websocket = clients[str(username).lower()]
                                    userid = AuthMessage.objects.filter(username=username).values('id')[0]['id']
                                    RobotInfo.objects.filter(user_id=userid).update(robot_status=3)
                                    result = {}
                                    result['username'] = username
                                    result['action'] = action
                                    user_websocket.send(json.dumps(result))
                                except:
                                    result = {"action": "get_connection", "result": "error"}
                                    request.websocket.send(json.dumps(result))
                            except Exception:
                                username = msg_2_json['username']
                                userid = AuthMessage.objects.filter(username=username).values('id')[0]['id']
                                RobotInfo.objects.filter(user_id=userid).update(robot_status=2)
                                result = msg_2_json['result']
                                if result == "success":
                                    auto = msg_2_json['auto']
                                    if auto == 1:
                                        # get sap record result
                                        record_code = msg_2_json['record_code']
                                        record_code_list = record_code.split("\n")
                                        path = os.path.dirname(os.path.dirname(os.path.realpath(__file__))) + "\\Draw_Process\\SAP_Action.json"
                                        sap_str = ""
                                        with open(path, encoding='utf-8') as f:
                                            data = f.readlines()
                                        for i in data:
                                            sap_str += i
                                        sap_json = json.loads(sap_str)
                                        items = sap_json.items()
                                        sap_list = []
                                        # mapping sap record result with sap template
                                        for i in range(len(record_code_list)):
                                            record_code = record_code_list[i]
                                            if record_code.replace('\x00', "") == '':
                                                continue
                                            sap_j = {}
                                            parameters = {}
                                            p1 = record_code.find("(", 0)
                                            p2 = -1
                                            while True:
                                                position = record_code.find(")", p2 + 1)
                                                if position == -1:
                                                    break
                                                p2 = position
                                            id = record_code[p1 + 2:p2 - 1].replace('\x00', "")
                                            parameters["element_name"] = id
                                            parameters["find_method"] = '"ID"'
                                            parameters["sap_active"] = '"yes"'
                                            record_code = record_code.replace(record_code[0:p2 + 3], "")
                                            record_code = record_code.replace('\x00', "")
                                            for key, value in items:
                                                find = isMatch(record_code, key)
                                                if find:
                                                    sap_j['action'] = value
                                                    if "*" in key:
                                                        p = key.find("*", 0)
                                                        parameter = record_code[p:p + len(record_code) - len(key) + 1]
                                                        sap_j['action'] = value.split(",")[0]
                                                        for j in range(1, len(value.split(","))):
                                                            parameters[value.split(",")[j]] = parameter.split(",")[j - 1]
                                                    else:
                                                        sap_j['action'] = value
                                                    sap_j['parameters'] = parameters
                                                    sap_list.append(sap_j)
                                                    break
                                            if not find and record_code:
                                                sap_j['action'] = "SAP_Custom"
                                                if " " in record_code:
                                                    parameters["parameters"] = "'" + record_code.split(" ", 1)[1].replace("false", "0") + "'"
                                                    parameters["sap_function"] = '"' + record_code.split(" ", 1)[0] + '"'
                                                else:
                                                    parameters["parameters"] = '""'
                                                    parameters["sap_function"] = '"' + record_code + '"'
                                                sap_j['parameters'] = parameters
                                                sap_list.append(sap_j)
                                        msg_2_json['record_code'] = sap_list
                                    else:
                                        record_code = msg_2_json['record_code']
                                        record_code_list = record_code.split("\n")
                                        msg_2_json['record_code'] = record_code_list
                                clients[str(username) + 'html'].send(json.dumps(msg_2_json))
                        elif action == "chrome_record":
                            try:
                                username = request.session['username']
                                try:
                                    user_websocket = clients[str(username).lower()]
                                    userid = AuthMessage.objects.filter(username=username).values('id')[0]['id']
                                    RobotInfo.objects.filter(user_id=userid).update(robot_status=3)
                                    result = {}
                                    result['username'] = username
                                    result['action'] = action
                                    user_websocket.send(json.dumps(result))
                                except:
                                    result = {"action": "get_connection", "result": "error"}
                                    request.websocket.send(json.dumps(result))
                            except Exception:
                                username = msg_2_json['username']
                                userid = AuthMessage.objects.filter(username=username).values('id')[0]['id']
                                RobotInfo.objects.filter(user_id=userid).update(robot_status=2)
                                result = msg_2_json['result']
                                if result == "success":
                                    auto = msg_2_json['auto']
                                    record_code = msg_2_json['record_code']
                                    if auto == 1:
                                        msg_2_json['record_code'] = record_code
                                    else:
                                        record_list = []
                                        for record in record_code:
                                            record_string = ""
                                            for record_step in record:
                                                if "Client_Trans: " in record_step:
                                                    record_step = record_step.replace('Client_Trans: ','')
                                                record_string = record_string + record_step + "__gettext_trans__"
                                            record_list.append(record_string)
                                        msg_2_json['record_code'] = record_list
                                clients[str(username) + 'html'].send(json.dumps(msg_2_json))
                        elif action == "web_crawl":
                            try:
                                username = request.session['username']
                                try:
                                    user_websocket = clients[str(username).lower()]
                                    userid = AuthMessage.objects.filter(username=username).values('id')[0]['id']
                                    RobotInfo.objects.filter(user_id=userid).update(robot_status=3)
                                    result = {}
                                    result['username'] = username
                                    result['action'] = action
                                    user_websocket.send(json.dumps(result))
                                except:
                                    result = {"action": "get_connection", "result": "error"}
                                    request.websocket.send(json.dumps(result))
                            except Exception:
                                username = msg_2_json['username']
                                userid = AuthMessage.objects.filter(username=username).values('id')[0]['id']
                                RobotInfo.objects.filter(user_id=userid).update(robot_status=2)
                                clients[str(username) + 'html'].send(json.dumps(msg_2_json))
                        elif action == "handle_target":
                            try:
                                username = request.session['username']
                                try:
                                    user_websocket = clients[str(username).lower()]
                                    userid = AuthMessage.objects.filter(username=username).values('id')[0]['id']
                                    RobotInfo.objects.filter(user_id=userid).update(robot_status=3)
                                    result = {}
                                    result['username'] = username
                                    result['action'] = action
                                    user_websocket.send(json.dumps(result))
                                except:
                                    result = {"action": "get_connection", "result": "error"}
                                    request.websocket.send(json.dumps(result))
                            except Exception:
                                username = msg_2_json['username']
                                userid = AuthMessage.objects.filter(username=username).values('id')[0]['id']
                                RobotInfo.objects.filter(user_id=userid).update(robot_status=2)
                                clients[str(username) + 'html'].send(json.dumps(msg_2_json))
                        elif action == "icon_target":
                            try:
                                username = request.session['username']
                                try:
                                    user_websocket = clients[str(username).lower()]
                                    userid = AuthMessage.objects.filter(username=username).values('id')[0]['id']
                                    RobotInfo.objects.filter(user_id=userid).update(robot_status=3)
                                    result = {}
                                    result['username'] = username
                                    result['action'] = action
                                    user_websocket.send(json.dumps(result))
                                except:
                                    result = {"action": "get_connection", "result": "error"}
                                    request.websocket.send(json.dumps(result))
                            except Exception:
                                username = msg_2_json['username']
                                userid = AuthMessage.objects.filter(username=username).values('id')[0]['id']
                                RobotInfo.objects.filter(user_id=userid).update(robot_status=2)
                                clients[str(username) + 'html'].send(json.dumps(msg_2_json))
                        elif action == "icon_coordinate_target":
                            try:
                                username = request.session['username']
                                try:
                                    user_websocket = clients[str(username).lower()]
                                    userid = AuthMessage.objects.filter(username=username).values('id')[0]['id']
                                    RobotInfo.objects.filter(user_id=userid).update(robot_status=3)
                                    result = {}
                                    result['username'] = username
                                    result['action'] = action
                                    user_websocket.send(json.dumps(result))
                                except:
                                    result = {"action": "get_connection", "result": "error"}
                                    request.websocket.send(json.dumps(result))
                            except Exception:
                                username = msg_2_json['username']
                                userid = AuthMessage.objects.filter(username=username).values('id')[0]['id']
                                RobotInfo.objects.filter(user_id=userid).update(robot_status=2)
                                clients[str(username) + 'html'].send(json.dumps(msg_2_json))
                        elif action == "mouse_target":
                            try:
                                username = request.session['username']
                                try:
                                    user_websocket = clients[str(username).lower()]
                                    userid = AuthMessage.objects.filter(username=username).values('id')[0]['id']
                                    RobotInfo.objects.filter(user_id=userid).update(robot_status=3)
                                    result = {}
                                    result['username'] = username
                                    result['action'] = action
                                    user_websocket.send(json.dumps(result))
                                except:
                                    result = {"action": "get_connection", "result": "error"}
                                    request.websocket.send(json.dumps(result))
                            except Exception:
                                username = msg_2_json['username']
                                userid = AuthMessage.objects.filter(username=username).values('id')[0]['id']
                                RobotInfo.objects.filter(user_id=userid).update(robot_status=2)
                                clients[str(username) + 'html'].send(json.dumps(msg_2_json))
                        elif action == "web_dragging_mouse_target":
                            try:
                                username = request.session['username']
                                try:
                                    user_websocket = clients[str(username).lower()]
                                    userid = AuthMessage.objects.filter(username=username).values('id')[0]['id']
                                    RobotInfo.objects.filter(user_id=userid).update(robot_status=3)
                                    result = {}
                                    result['username'] = username
                                    result['action'] = action
                                    user_websocket.send(json.dumps(result))
                                except:
                                    result = {"action": "get_connection", "result": "error"}
                                    request.websocket.send(json.dumps(result))
                            except Exception:
                                username = msg_2_json['username']
                                userid = AuthMessage.objects.filter(username=username).values('id')[0]['id']
                                RobotInfo.objects.filter(user_id=userid).update(robot_status=2)
                                clients[str(username) + 'html'].send(json.dumps(msg_2_json))
                        elif action == "exit":
                            username = msg_2_json['username']
                            if clients.__contains__(str(username)):
                                if clients[str(username).lower()] is not None:
                                    clients[str(username).lower()].close()
                                    del clients[str(username).lower()]
                                    userid = AuthMessage.objects.filter(username=username).values('id')[0]['id']
                                    RobotInfo.objects.filter(user_id=userid).update(robot_status=1, file_path="")
                            print("退出客服端的server while ")
                            break
                else:
                    if message != None:
                        try:
                            user_websocket = clients[str(username).lower()]
                        except:
                            result = {"action": "get_connection", "result": "error"}
                            request.websocket.send(json.dumps(result))
                    if clients.__contains__(str(username)):
                        if clients[str(username).lower()] is not None:
                            clients[str(username).lower()].close()
                            del clients[str(username).lower()]
                            userid = AuthMessage.objects.filter(username=username).values('id')[0]['id']
                            RobotInfo.objects.filter(user_id=userid).update(robot_status=1, file_path="")
                    print("退出客服端的server while ")
                    break
            except Exception as e:
                a = str(e)
                logger.error("发生异常了：" + a)
                username = ""
                for client in clients:
                    if clients[client] == request.websocket:
                        username = client
                        break
                if username:
                    clients[str(username).lower()].close()
                    del clients[str(username).lower()]
                    if "html" not in username:
                        userid = AuthMessage.objects.filter(username=username).values('id')[0]['id']
                        RobotInfo.objects.filter(user_id=userid).update(robot_status=1,file_path="")
                try:
                    request.websocket.close()
                except Exception as e:
                    logger.error(e)
    else:
        logger.error("no websocket connection")
        return HttpResponse('no connection')

#commander页面入口
@csrf_exempt
def commanderPage(request):
    if 'username' in request.session and 'password' in request.session:
        username = request.session['username']
        return render(request,'commander.html')
    else:
        return render(request, "login.html")

#显示机器人列表
@csrf_exempt
def commanderList(request):
    if 'username' in request.session and 'password' in request.session:
        username = request.session['username']
        if request.method == 'POST':
            page_No = request.POST.get("pageNo")
            page_Size = request.POST.get("pageSize")
            orderBy = request.POST.get("orderBy")
            # 筛选条件
            robotName = xstr(request.POST.get("robotName"))
            robotStatus = xstr(request.POST.get("robotStatus"))
            if "asc" in orderBy:
                order_condition = orderBy.split(" ")[0]
            elif orderBy == "":
                order_condition = ""
            else:
                order_condition = "-" + orderBy.split(" ")[0]
            if "nick_name" in order_condition:
                order_condition = order_condition.replace("nick_name","user__nickname")
            elif "organization" in order_condition:
                order_condition = order_condition.replace("organization","user__department__company__organization")
            elif "company" in order_condition:
                order_condition = order_condition.replace("company","user__department__company")
            elif "department" in order_condition:
                order_condition = order_condition.replace("department","user__department")
            if page_No == "":
                pageNo = 1
            else:
                pageNo = int(page_No)
            if page_Size == "":
                pageSize = 20
            else:
                pageSize = int(page_Size)
            user = AuthMessage.objects.get(username=username)
            perms = AuthMessage.get_all_permissions(user)
            username_list = []
            for perm in perms:
                if "Draw_Process.views_commander_" in perm and "_view_task" in perm:
                    username_code = perm.replace("Draw_Process.views_commander_","").replace("_view_task","")
                    username_list.append(username_code)
            userid_tupe = AuthMessage.objects.filter(username__in=username_list).values('id')
            userid_list = []
            for userid_code in userid_tupe:
                userid_list.append(userid_code['id'])
            try:
                if orderBy == "":
                    if robotStatus == '':
                        robot_array = RobotInfo.objects.all().filter(robot_name__icontains=robotName,user_id__in=userid_list).values('robot_name','robot_status','file_path','user_id')
                    else:
                        robot_array = RobotInfo.objects.all().filter(robot_name__icontains=robotName,user_id__in=userid_list,
                                                                     robot_status__icontains=robotStatus)
                else:
                    if robotStatus == '':
                        robot_array = RobotInfo.objects.all().filter(robot_name__icontains=robotName,user_id__in=userid_list).order_by(order_condition)
                    else:
                        robot_array = RobotInfo.objects.all().filter(robot_name__icontains=robotName,user_id__in=userid_list,
                                                                     robot_status__icontains=robotStatus).order_by(order_condition)
            except Exception as e:
                s = str(e)
                a = 'aa'
            robot_result = []
            count = len(robot_array)
            if (pageNo) * pageSize <= len(robot_array):
                startNo = (pageNo - 1) * pageSize
                endNo = (pageNo) * pageSize
            else:
                startNo = (pageNo - 1) * pageSize
                endNo = len(robot_array)
            for j in range(startNo, endNo):
                robot_json = {}
                field = robot_array[j]
                try:
                    robot_json["robot_name"] = field.robot_name
                    user_name_id = field.robot_name.replace("robot_","")
                    robot_status = int(field.robot_status)
                    if robot_status == 1:
                        robot_json["robot_status"] = gettext("off-line")
                    elif robot_status == 2:
                        robot_json["robot_status"] = gettext("idle")
                    elif robot_status == 3:
                        robot_json["robot_status"] = gettext("busy")
                    robot_json["file_path"] = field.file_path
                    robot_json["nick_name"] = field.user.nickname
                    robot_json["organization"] = field.user.department.company.organization.organization
                    robot_json["company"] = field.user.department.company.company
                    department_name = field.user.department.department_name
                    parent_code = user.department.parent_code
                    while parent_code != "0":
                        upperDepartment = Department.objects.filter(department_code=parent_code).values('parent_code', 'department_name')[0]
                        sub_department_name = upperDepartment['department_name']
                        parent_code = upperDepartment['parent_code']
                        department_name = sub_department_name + "\\" + department_name
                    robot_json["department"] = department_name
                    robot_json["finished_tasks"] = len(TaskResult.objects.filter(create_by=field.user.username).values('task_name'))
                    robot_json["booked_tasks"] = len(TaskInformation.objects.filter(create_by=field.user.username).values('task_name'))
                except:
                    robot_json["robot_name"] = field["robot_name"]
                    user_name_id = field["robot_name"].replace("robot_", "")
                    robot_status = int(field["robot_status"])
                    if robot_status == 1:
                        robot_json["robot_status"] = gettext("off-line")
                    elif robot_status == 2:
                        robot_json["robot_status"] = gettext("idle")
                    elif robot_status == 3:
                        robot_json["robot_status"] = gettext("busy")
                    robot_json["file_path"] = field["file_path"]
                    userid = field["user_id"]
                    user = AuthMessage.objects.get(id=userid)
                    robot_json["nick_name"] = user.nickname
                    robot_json["organization"] = user.department.company.organization.organization
                    robot_json["company"] = user.department.company.company
                    department_name = user.department.department_name
                    parent_code = user.department.parent_code
                    while parent_code != "0":
                        upperDepartment = Department.objects.filter(department_code=parent_code).values('parent_code','department_name')[0]
                        sub_department_name = upperDepartment['department_name']
                        parent_code = upperDepartment['parent_code']
                        department_name = sub_department_name + "\\" + department_name
                    robot_json["department"] = department_name
                    robot_json["finished_tasks"] = len(TaskResult.objects.filter(create_by=user.username).values('task_name'))
                    robot_json["booked_tasks"] = len(TaskInformation.objects.filter(create_by=user.username).values('task_name'))
                if "Draw_Process.views_commander_" + str(user_name_id) + "_assign_task" in perms:
                    robot_json["assign"] = 1
                else:
                    robot_json["assign"] = 0
                if "Draw_Process.views_commander_" + str(user_name_id) + "_schedule_task" in perms:
                    robot_json["schedule"] = 1
                else:
                    robot_json["schedule"] = 0
                robot_result.append(robot_json)
            account_json = {}
            if pageNo == 1:
                prevNo = 1
            else:
                prevNo = pageNo - 1
            total_page, i = divmod(count, pageSize)
            if i == 0:
                totalPage = total_page
            else:
                totalPage = total_page + 1
            if pageNo == totalPage:
                nextNo = pageNo
            else:
                nextNo = pageNo + 1
            account_json["prev"] = prevNo
            account_json["count"] = len(robot_array)
            account_json["first"] = 1
            account_json["next"] = nextNo
            account_json["pageNo"] = pageNo
            account_json["pageSize"] = pageSize
            account_json["last"] = totalPage
            account_json["list"] = robot_result
            return JsonResponse(account_json)
    else:
        return render(request, "login.html")


#保存录制变量
@csrf_exempt
def saveRecordVariant(request):
    if 'username' in request.session and 'password' in request.session:
        username = request.session['username']
        result = {}
        try:
            data = request.POST.getlist('data[]')
            tab = int(request.POST.get('tab'))
            workList = []
            now_time = datetime.datetime.now().replace(microsecond=0)
            for i in range(len(data)):
                action_json = json.loads(data[i])
                workList.append(Actions(div_id=action_json['div_id'], function=action_json['function'],
                            variant=json.dumps(action_json['variant']), status="saved",create_on=now_time, create_by=username, tab=tab))
            Actions.objects.bulk_create(workList)
            result["result"] = "success"
        except Exception as e:
            result["result"] = "error"
            result["msg"] = str(e)
        return JsonResponse(result)
    else:
        return render(request, "login.html")


# 获取用户秘钥
@csrf_exempt
def savePasswordVariant(request):
    if 'username' in request.session and 'password' in request.session:
        username = request.session['username']
        variant = request.POST.get("variant")
        variant_json = json.loads(variant.replace(u"\u202a", ""))
        user = AuthMessage.objects.get(username=username)
        last_login = user.last_login.replace(microsecond=0)
        secret_key = str(username).lower() + "/" + str(last_login)
        #secret_key_path = variant_json["secret_key_path"]
        # 客户端拿个秘钥
        try:
            #查看是否有私钥文件夹
            if not os.path.exists(settings.File_Root + "\\Draw_Process\\pems"):
                os.mkdir(settings.File_Root + "\\Draw_Process\\pems")
            #查看是否存在私钥文件
            choclead_secret_key = ""
            if not os.path.exists(settings.File_Root + "\\Draw_Process\\pems\\" + str(username).lower() + ".pem"):
                #生成对应账户私钥
                sha256 = hashlib.sha512()
                sha256.update(secret_key.encode('utf-8'))
                choclead_secret_key = sha256.hexdigest()
                with open(settings.File_Root + "\\Draw_Process\\pems\\" + str(username).lower() + ".pem", "w") as f:
                    f.write(choclead_secret_key)
            else:
                with open(settings.File_Root + "\\Draw_Process\\pems\\" + str(username).lower() + ".pem", "r") as f:
                    secret_key_data = f.readlines()
                    for content in secret_key_data:
                        choclead_secret_key+=content.replace("\n","")
            if choclead_secret_key == "":
                choclead_secret_key = secret_key
            if len(choclead_secret_key) > 32:
                choclead_secret_key = choclead_secret_key[0:32]
            # user_websocket = clients[str(username).lower()]
            # result = {}
            # result['username'] = username
            # result['action'] = "get_secret_key"
            # result['choclead_secret_key'] = choclead_secret_key
            # global password_secret_key
            # password_secret_key = None
            # user_websocket.send(json.dumps(result))
            # #传输密钥给机器人端
            # t_end = time.time() + 3
            # while time.time() < t_end:
            #     if password_secret_key is not None:
            #         break
            # print(password_secret_key)
            return saveVariantForSetPassword(request, choclead_secret_key)
            # if password_secret_key is None:
            #     result = {"action": "get_secret_key", "result": gettext("Please .")}
            #     return JsonResponse(result)
            # else:
            #     return saveVariantForSetPassword(request, password_secret_key)
        except Exception as e:
            result = {"action": "get_secret_key", "result": str(e)}
            return JsonResponse(result)
    else:
        return render(request, "login.html")
