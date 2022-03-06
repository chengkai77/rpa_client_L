import base64
import rsa
from django.shortcuts import render
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse, HttpRequest, HttpResponseRedirect,HttpResponsePermanentRedirect, FileResponse
from django.contrib.auth import authenticate, login, logout, get_user
from django.contrib.auth.hashers import make_password, check_password
from django.contrib import admin,auth
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.models import Group
from django.contrib.auth.models import Permission
from django.views.decorators.csrf import csrf_exempt
import datetime
import json
from Draw_Process.models import AuthMessage, Store
from Draw_Process.models import ProcessCopy
from django.core import serializers
from Draw_Process.models import Actions
from Draw_Process.models import TaskInformation
from Draw_Process.models import TaskResult
from Python_Platform import settings
from django.utils.translation import gettext
from Client.websocketviews import port
import logging
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph
import re
# Create your views here.

@csrf_exempt
def checkLicence(request):
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
                    licence_date = AuthMessage.objects.filter(username=username).values("licence_date")[0]["licence_date"]
                    if licence_date:
                        licence_date_time = datetime.datetime.strptime(str(licence_date) + " 00:00:00", "%Y-%m-%d %H:%M:%S")
                        if licence_date_time < end_time:
                            end_time = licence_date_time
                except Exception:
                    pass
                diff_days = (end_time - nowtime).days
                return JsonResponse({"result": "success", "day":diff_days})
            else:
                logging.warning("private file or time file is not exsiting!")
                msg = gettext("Lost encrypted file, please contact your administrator!")
                return JsonResponse({"result": "error", "message": msg})
        except Exception as e:
            logging.error(str(e))
            return JsonResponse({"result": "error", "message": str(e)})
    else:
        return render(request, "login.html")

@csrf_exempt
def updateLicence(request):
    if 'username' in request.session and 'password' in request.session:
        try:
            username = request.session['username']
            key = request.POST.get('key')
            licence = request.POST.get('licence')
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
                with open(pemPath, 'w') as privatefile:
                    privatefile.write(key)
                with open(timePath, 'w') as licencefile:
                    licencefile.write(licence)
                return JsonResponse({"result": "success"})
            else:
                logging.warning("private file or time file is not exsiting!")
                msg = gettext("Lost encrypted file, please contact your administrator!")
                return JsonResponse({"result": "error", "message": msg})
        except Exception as e:
            logging.error(str(e))
            return JsonResponse({"result": "error", "message": str(e)})
    else:
        return render(request, "login.html")

@csrf_exempt
def index(request):
    if 'username' in request.session and 'password' in request.session:
        username = request.session['username']
        Actions.objects.filter(create_by=username).delete()
        password = request.session['password']
        user = authenticate(request, username=username, password=password)
        last_logtime = user.last_login
        if last_logtime == "" or last_logtime is None:
            last_logtime_adj = ""
        else:
            last_logtime_adj = str(last_logtime.strftime('%Y-%m-%d %H:%M'))
        nowtime = datetime.datetime.now()
        User.objects.filter(username=username).update(last_login=nowtime)
        auth_msg = AuthMessage.objects.filter(user=user)
        auth_msg_list = []
        auth_msg_list = serializers.serialize('json', auth_msg)
        auth_msg_array = json.loads(auth_msg_list)
        users = User.objects.all().filter(username=username)
        users_list = []
        users_list = serializers.serialize('json', users)
        users_array = json.loads(users_list)
        user_id = users_array[0]['pk']
        field = auth_msg_array[0]['fields']
        nickname = field['name']
        lastIP = field['ip']
        x_forwarded_for = request.META.get('HTTP_X_FORARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[-1].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        if ip is None or ip == "" or "127.0" in ip:
            ip = field['fixed_ip']
        request.session['ip'] = ip
        imageurl = field['image_url']
        import socket
        myname = socket.getfqdn(socket.gethostname())
        try:
            myaddr = socket.gethostbyname(myname)
        except Exception:
            myaddr = ip
        perms = User.get_all_permissions(user)
        AuthMessage.objects.filter(username=username).update(ip=myaddr)
        if nickname == "" or nickname is None:
            nickname = user
        request.session['session_name'] = "admin"
        try:
            if username:
                request.session['username'] = username  # 使用session来保存用户登录信息
            if password:
                request.session['password'] = password
        except:
            pass
        booked_tasks = TaskInformation.objects.all().filter(create_by=username).values('pc_name', 'task_name','duration','booked_time').order_by('booked_time')
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
        finished_tasks = TaskResult.objects.all().filter(create_by=username, status='unread').values('task_name','result','end_time').order_by('end_time')
        finished_tasks_list = []
        for j in range(len(finished_tasks)):
            finished_json = {}
            finished_json['task_name'] = finished_tasks[j]['task_name']
            finished_json['result'] = finished_tasks[j]['result']
            finished_json['end_time1'] = finished_tasks[j]['end_time'].strftime("%H:%M")
            finished_json['end_time2'] = finished_tasks[j]['end_time'].strftime("%Y-%m-%d %H:%M")
            finished_tasks_list.append(finished_json)
        return render(request, 'index.html',
                      {"user": nickname, "userID": username, "ip": ip, "lastIP": lastIP, "lastLogin": last_logtime_adj,
                       "imageurl": imageurl, "perms": perms, "booked_tasks": json.dumps(booked_tasks_list),
                       "finished_tasks": json.dumps(finished_tasks_list)})
    else:
        return render(request, "login.html")

@csrf_exempt
def index2(request):
    if 'username' in request.session and 'password' in request.session:
        username = request.session['username']
        url = request.get_host()
        Actions.objects.filter(create_by=username).delete()
        password = request.session['password']
        user = authenticate(request, username=username, password=password)
        last_logtime = user.last_login
        if last_logtime == "" or last_logtime is None:
            last_logtime_adj = ""
        else:
            last_logtime_adj = str(last_logtime.strftime('%Y-%m-%d %H:%M'))
        nowtime = datetime.datetime.now()
        AuthMessage.objects.filter(username=username).update(last_login=nowtime)
        auth_msg = AuthMessage.objects.filter(username=username)
        auth_msg_list = []
        auth_msg_list = serializers.serialize('json', auth_msg)
        auth_msg_array = json.loads(auth_msg_list)
        users = AuthMessage.objects.all().filter(username=username)
        users_list = []
        users_list = serializers.serialize('json', users)
        users_array = json.loads(users_list)
        user_id = users_array[0]['pk']
        field = auth_msg_array[0]['fields']
        nickname = field['username']
        lastIP = field['ip']
        x_forwarded_for = request.META.get('HTTP_X_FORARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[-1].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        if ip is None or ip == "":
            ip = field['fixed_ip']
        request.session['ip'] = ip
        if "choclead.teclead.com" in url or "139.196.188.42" in url:
            request.session['version'] = "cloud"
        else:
            request.session['version'] = "local"
        imageurl = field['image_url']
        import socket
        myname = socket.getfqdn(socket.gethostname())
        try:
            myaddr = socket.gethostbyname(myname)
        except Exception:
            myaddr = ip
        perms = AuthMessage.get_all_permissions(user)
        AuthMessage.objects.filter(username=username).update(ip=myaddr)
        if nickname == "" or nickname is None:
            nickname = user
        request.session['session_name'] = "admin"
        try:
            if username:
                request.session['username'] = username  # 使用session来保存用户登录信息
            if password:
                request.session['password'] = password
        except:
            pass
        booked_tasks = TaskInformation.objects.all().filter(create_by=username).values('pc_name', 'task_name','duration','booked_time').order_by('booked_time')
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
            booked_json['booked_time'] = booked_tasks[i]['booked_time'].strftime("%m-%d %H:%M:%S")
            booked_json['booked_time2'] = booked_tasks[i]['booked_time'].strftime("%Y-%m-%d %H:%M:%S")
            booked_tasks_list.append(booked_json)
        finished_tasks = TaskResult.objects.all().filter(create_by=username, status='unread').values('id','task_name','result','end_time').order_by('end_time')
        finished_tasks_list = []
        for j in range(len(finished_tasks)):
            finished_json = {}
            finished_json['id'] = finished_tasks[j]['id']
            finished_json['task_name'] = finished_tasks[j]['task_name']
            finished_json['result'] = finished_tasks[j]['result']
            finished_json['end_time1'] = finished_tasks[j]['end_time'].strftime("%H:%M")
            finished_json['end_time2'] = finished_tasks[j]['end_time'].strftime("%Y-%m-%d %H:%M")
            finished_tasks_list.append(finished_json)
        version = request.session['version']
        return render(request, 'index2.html',
                      {"user": nickname, "userID": username, "ip": ip, "lastIP": lastIP, "lastLogin": last_logtime_adj,
                       "imageurl": imageurl, "perms": perms, "booked_tasks": json.dumps(booked_tasks_list), "version": version,
                       "finished_tasks": json.dumps(finished_tasks_list)})
    else:
        return render(request, "login.html")


def welcome(request):
    if 'username' in request.session and 'password' in request.session:
        username = request.session['username']
        ip = request.session['ip']
        json = {}
        json["ip"] = ip
        json["id"] = "{{id}}"
        json["top"] = "{{top}}"
        json["left"] = "{{left}}"
        json["jnodeClass"] = "{{jnodeClass}}"
        json["jnodeHtml"] = "{{{jnodeHtml}}}"
        user = AuthMessage.objects.get(username=username)
        perms = AuthMessage.get_all_permissions(user)
        json['perms'] = perms
        return render(request,'welcome.html',json)
    else:
        return render(request, "login.html")

def welcome2(request):
    if 'username' in request.session and 'password' in request.session:
        username = request.session['username']
        ip = request.session['ip']
        try:
            day = request.session['day']
        except:
            day = 0
        version = request.session['version']
        json = {}
        json["ip"] = ip
        json["id"] = "{{id}}"
        json["top"] = "{{top}}"
        json["left"] = "{{left}}"
        json["jnodeClass"] = "{{jnodeClass}}"
        json["jnodeHtml"] = "{{{jnodeHtml}}}"
        user = AuthMessage.objects.get(username=username)
        perms = AuthMessage.get_all_permissions(user)
        json['perms'] = perms
        try:
            cliet_port = port[username]
        except:
            cliet_port = "1234"
        json['port'] = cliet_port
        setting_file = settings.File_Root + "\\Draw_Process\\setting.txt"
        with open(setting_file, 'r', encoding='utf-8') as ff:
            setting_content = ff.readlines()
            for i in range(len(setting_content)):
                setting_list = setting_content[i].rstrip("\n").split("=")
                if 'server_address' in setting_list[0]:
                    server_address = setting_list[1].replace(" ", "")
        json['server_address'] = server_address
        json['day'] = day
        # try:
        #     if versions[username + "server"] == versions[username + "client"]:
        #         json['rpa_version'] = "different"
        #     else:
        #         json['rpa_version'] = "same"
        # except Exception as e:
        #     json['rpa_version'] = 'same'
        return render(request,'welcome2.html',json)
    else:
        return render(request, "login.html")


#download stored process and database to xml file
@csrf_exempt
def downloadProcess(request):
    if 'username' in request.session and 'password' in request.session:
        username = request.session['username']
        filePath = request.GET['filePath']
        file_paths = filePath.split("\\")
        relative_path = ""
        download_path = settings.File_Root + "\\Draw_Process\\Download\\"
        for i in range(len(file_paths)):
            if i == 0:
                if file_paths[0] == "Private":
                    file_path = username.lower()
                else:
                    file_path = file_paths[0].lower()
            else:
                file_path = file_paths[i]
            if i != len(file_paths) - 1:
                relative_path = relative_path + file_path + "\\"
            else:
                relative_path = relative_path + file_path + ".py"
                download_path = download_path + file_path + ".lbt"
                fileName = file_path + ".lbt"
        data = ""
        groups = Store.objects.distinct().filter(file_name=relative_path,group_node_name="Start").exclude(group=None).values('group')
        if len(groups) > 0:
            jnode_class_json = {}
            for group in groups:
                group_path = group['group']
                groups_mappings = Store.objects.distinct().filter(file_name=group_path).values('source_id','jnode_class','source_type','target_type','status')
                for group_mapping in groups_mappings:
                    jnode_class_json[group_mapping['source_id']] = group_mapping['jnode_class']
                    jnode_class_json[group_mapping['source_id'] + "-source_type"] = group_mapping['source_type']
                    jnode_class_json[group_mapping['source_id'] + "-target_type"] = group_mapping['target_type']
                    jnode_class_json[group_mapping['source_id'] + "-status"] = group_mapping['status']
        mappings = Store.objects.filter(file_name=relative_path).exclude(group_node_name="Start").exclude(
                    group_node_name="End").order_by('node_no','group_node_no')
        mappings_list = []
        mappings_list = serializers.serialize('json', mappings)
        mappings_array = json.loads(mappings_list)
        id = 1
        for mapping in mappings_array:
            step_json = mapping["fields"]
            if id < len(mappings_array):
                next_step_json = mappings_array[id]["fields"]
                next_group = next_step_json['group']
                if next_group:
                    step_json['target_id'] = next_step_json['group_id']
            step_json['node_no'] = id
            id += 1
            group = step_json['group']
            if group:
                step_json['jnode_html'] = '<span id="' + step_json['group_node_name'] + '" class ="flow-span" title="' + step_json['group_node_name'] + '">' + step_json['group_node_name'] + '</span>'
                step_json['source_id'] = step_json['group_id']
                step_json['left'] = step_json['group_left']
                step_json['top'] = step_json['group_top']
                # 合并流程在store表中无数据
                try:
                    step_json['jnode_class'] = jnode_class_json[step_json['source_id']]
                except:
                    # 处理特殊的节点
                    if step_json['group_node_name'] == "Wait":
                        step_json['jnode_class'] = "jnode-radius bdc-wait"
                        step_json['jnode'] = "end"
                    elif step_json['group_node_name'] in ["If", "Else", "Else_If", "End_If", "For", "Break", "Exit_For", "While", "Exit_W"]:
                        step_json['jnode_class'] = "jnode-diamond jnode-judge bdc-warning"
                        step_json['jnode'] = "judge"
                    else:
                        step_json['jnode_class'] = "jnode-task bdc-primary"
                        step_json['jnode'] = "task"
                try:  # 嵌入流程
                    step_json['source_type'] = jnode_class_json[step_json['source_id'] + "-source_type"]
                    step_json['target_type'] = jnode_class_json[step_json['source_id'] + "-target_type"]
                    step_json['status'] = jnode_class_json[step_json['source_id'] + "-status"]
                except:  # 合并流程
                    step_json['source_type'] = step_json['group_source_type']
                    step_json['target_type'] = step_json['group_target_type']
                    step_json['status'] = step_json["status"]
                step_json['group'] = ""
                step_json['group_id'] = ""
                step_json['group_node_no'] = ""
                step_json['group_node_name'] = ""
                step_json['group_source_type'] = ""
                step_json['group_target_type'] = ""
                step_json['group_left'] = ""
                step_json['group_top'] = ""
            content = json.dumps(step_json)
            data = data + content + "\n"
        if os.path.exists(download_path):
            os.remove(download_path)
        with open(download_path, 'w', encoding='utf-8') as f:
            f.write(data)
        file = open(download_path,'rb')
        response = FileResponse(file)
        response['Content-Type'] = 'application/octet-stream'
        fileName = fileName.encode('utf-8')
        response['Content-Disposition'] = 'attachment;filename="' + fileName.decode('unicode_escape')
        return response
    else:
        return render(request, "login.html")

#get codes
@csrf_exempt
def getDownloadCodes(request):
    if 'username' in request.session and 'password' in request.session:
        try:
            username = request.session['username']
            type = request.POST.get('type')
            fileName = request.POST.get('fileName')
            if type == "codesTxt":
                postfix = ".txt"
            else:
                postfix = ".pdf"
            if not fileName:
                import time
                fileName = str(int(time.time())) + postfix
            else:
                fileName = fileName + postfix
            codeList = request.POST.getlist('codeList[]')
            data = ""
            data_list = []
            for i in range(len(codeList)):
                content = codeList[i]
                if type == "codesTxt":
                    while "<" in content:
                        replace_content = re.findall("<(.*?)>", content)[0]
                        content = content.replace("<" + replace_content + ">", "")
                if type == "codesPdf":
                    data = data + content + "<br />"
                    #data_list.append(content)
                else:
                    data = data + content + "\n"
            direction = os.path.dirname(os.path.realpath(__file__))
            path = direction + "\\" + fileName
            if type == "codesPdf":
                #data = "<!DOCTYPE html><html><body><img src='../../static/images/icon/teclead.png'><br><br>" + data + "</body></html>"
                request.session[username+"-"+"code"] = data
            else:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(data)
            return JsonResponse({"result":"success","path":path})
        except Exception as e:
            return JsonResponse({"result": "error","msg":str(e)})
    else:
        return render(request, "login.html")

#download codes
@csrf_exempt
def startDownloadCodes(request):
    if 'username' in request.session and 'password' in request.session:
        try:
            pdfmetrics.registerFont(TTFont('Song', 'SimSun.ttf'))  # 注册字体
            username = request.session['username']
            path = request.GET['path']
            file_paths = path.split("\\")
            fileName = file_paths[len(file_paths) - 1]
            fileName = fileName.encode('utf-8')
            if ".txt" in path:
                file = open(path, 'rb')
                response = FileResponse(file)
                response['Content-Type'] = 'application/octet-stream'
                response['Content-Disposition'] = 'attachment;filename="' + fileName.decode('unicode_escape')
            else:
                response = HttpResponse(content_type='application/pdf')
                response['Content-Disposition'] = 'attachment; filename=' + fileName.decode('unicode_escape')
                p = canvas.Canvas(response, pagesize=A4)
                data = request.session[username+"-"+"code"].replace("style='color:","color='")
                width, height = A4
                image_path = os.getcwd() + "\\static\\images\\icon\\teclead.png"
                p.drawImage(image_path, 5, height - 30, mask='auto')
                p.setFont('Song', 12)
                style_sheet = getSampleStyleSheet()
                style = style_sheet['BodyText']
                style.fontName = 'Song'
                style.wordWrap = 'CJK'
                # 字体大小
                style.fontSize = 12
                # 设置行距
                style.leading = 20
                # 设置边距
                style.leftIndent = 20
                style.rightIndent = 5
                Pa = Paragraph(data, style)
                used_width, used_height = Pa.wrap(width-10, height-40)
                Pa.wrapOn(p, width - 10, height - 40)
                Pa.drawOn(p, 0, height - 40 - used_height)
                p.showPage()
                #check weather above 40 lines
                new_data = ""
                lines = Pa.blPara.lines
                if len(lines) > 40:
                    x = 0
                    y = 40
                    z = len(lines) % y
                    if z > 0:
                        num = len(lines) // y
                    else:
                        num = len(lines) // y - 1
                    for n in range(num):
                        x = (n + 1) * 40
                        y = min(len(lines), (n + 2) * 40)
                        for i in range(x, y):
                            line = lines[i]
                            words = line.words
                            for word in words:
                                text = word.text
                                color = word.textColor
                                if "#" not in text:
                                    new_data = new_data + "<span color=" + str(color) + ">" + text + "</span>"
                                else:
                                    new_data = new_data + "<br /><span color=" + str(color) + ">" + text + "</span><br />"
                        if new_data[0:6] == "<br />":
                            new_data = new_data.replace("<br />", "", 1)
                        p.drawImage(image_path, 5, height - 30, mask='auto')
                        Pa = Paragraph(new_data, style)
                        new_data = ""
                        used_width, used_height = Pa.wrap(width - 10, height - 40)
                        Pa.wrapOn(p, width - 10, height - 40)
                        Pa.drawOn(p, 0, height - 40 - used_height)
                        p.showPage()
                request.session[username+"-"+"code"] = ""
                p.save()
            return response
        except Exception as e:
            return JsonResponse({"result": "error","msg":str(e)})
    else:
        return render(request, "login.html")

#upload xml file to specific path and upload data to store table
@csrf_exempt
def uploadProcess(request):
    if 'username' in request.session and 'password' in request.session:
        result = {}
        try:
            username = request.session['username']
            file = request.FILES.get('file_obj',None)
            contents = ""
            for chunk in file.chunks():
                contents = contents + str(chunk, encoding="utf-8")
            content_list = contents.split("\n")
            process_list = []
            for content in content_list:
                if content:
                    process_list.append(json.loads(content))
            result["status"] = "success"
            result["list"] = process_list
            result["title"] = file.name.replace(".lbt","")
        except Exception as e:
            result["status"] = "error"
            result["conso"] = str(e)
            result["msg"] = gettext("Import Failed!")
        return JsonResponse(result)
    else:
        return render(request, "login.html")

#transfer import data to action table
@csrf_exempt
def transferToAction(request):
    if 'username' in request.session and 'password' in request.session:
        result = {}
        try:
            username = request.session['username']
            process_list = request.POST.getlist('list[]')
            tab = int(request.POST.get('tab'))
            workList = []
            now_time = datetime.datetime.now().replace(microsecond=0)
            for i in range(len(process_list)):
                process_json = json.loads(process_list[i])
                jnode_html = process_json['jnode_html']
                jnode_html_adj = jnode_html.split('id="')[1]
                function = jnode_html_adj.split('" ')[0]
                if function != "Start" and function != "End":
                    workList.append(
                        Actions(div_id=process_json['source_id'], function=function, input=process_json['input'],
                                output=process_json['output'],
                                variant=process_json['variant'], node_no=process_json['node_no'],
                                name=process_json['name'],
                                status=process_json['status'],
                                public_variant=process_json['public_variant'], create_on=now_time, create_by=username,
                                tab=tab))
            Actions.objects.bulk_create(workList)
            result["status"] = "success"
            result["list"] = process_list
        except Exception as e:
            result["status"] = "error"
            result["conso"] = str(e)
            result["msg"] = gettext("Import Failed!")
        return JsonResponse(result)
    else:
        return render(request, "login.html")