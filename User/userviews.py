import os
import base64
import time

import rsa
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse, HttpRequest, HttpResponseRedirect,HttpResponsePermanentRedirect
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
from Draw_Process.models import AuthMessage
from Draw_Process.models import ProcessCopy
from django.core import serializers
from django.utils.translation import gettext
import traceback
from Draw_Process.models import SysRole
from Client.websocketviews import clients
from Client.websocketviews import pc_names
from Draw_Process.models import Department
from Draw_Process.models import Folder
from Draw_Process.models import Company
from Draw_Process.models import SysRole
from Draw_Process.models import SysArea
from Draw_Process.models import MenuPermission
from Draw_Process.models import FunctionPermission
from Draw_Process.models import PanelPermission
from Draw_Process.models import RobotInfo
from Draw_Process.models import Rolelist
from Draw_Process.models import Organization
from django.db.models import Max
from Python_Platform import settings
from django.contrib.auth.models import Permission
from User import  userutils
from datetime import timedelta

import logging
logger = logging.getLogger('log')

import shutil

#针对云端用户创建云盘下的个人文件夹
def createFolder(username):
    publicFloderPath = settings.File_Root + "\\Draw_Process\\pyfile\\public"
    if os.path.exists(publicFloderPath) == False:
        os.mkdir(publicFloderPath)
    cloudFloderPath = settings.File_Root + "\\Draw_Process\\pyfile\\public\\Cloud Disk"
    if os.path.exists(cloudFloderPath) == False:
        os.mkdir(cloudFloderPath)
        cloud_path = "public\\Cloud Disk"
        now_time = datetime.datetime.now().replace(microsecond=0)
        Folder.objects.create(folder=cloud_path, create_on=now_time, create_by=username)
    userPublicFloderPath = settings.File_Root + "\\Draw_Process\\pyfile\\public\\Cloud Disk\\" + str(username)
    if os.path.exists(userPublicFloderPath) == False:
        os.mkdir(userPublicFloderPath)
        cloud_path = "public\\Cloud Disk\\" + str(username)
        now_time = datetime.datetime.now().replace(microsecond=0)
        Folder.objects.create(folder=cloud_path, create_on=now_time, create_by=username)

def deleteFolder(username):
    userPublicFloderPath = settings.File_Root + "\\Draw_Process\\pyfile\\public\\Cloud Disk\\" + str(username)
    if os.path.exists(userPublicFloderPath) == True:
        os.remove(userPublicFloderPath)

#teclead create user function
@csrf_exempt
def tecleadUserCreate(request):
    if request.method == 'POST':  # 当提交表单时
        if request.POST:
            try:
                type = request.POST.get('type')
                try:
                    username = request.POST.get('user_name').lower()
                    password = request.POST.get('password')
                    nick = request.POST.get('nick_name')
                    email = request.POST.get('email')
                    mobile = request.POST.get('mobile')
                    phone = request.POST.get('phone')
                    location = request.POST.get('location')
                    licencedate_string = request.POST.get('licence_date')
                    licencedate = datetime.datetime.strptime(licencedate_string, "%Y-%m-%d %H:%M:%S")
                    userlevel = request.POST.get('user_level')
                    nowtime = datetime.datetime.now()
                    users = AuthMessage.objects.filter(username=username).values('id')
                    if len(users) > 0:
                        try:
                            AuthMessage.objects.filter(username=username).update(nickname=nick, password=password,
                                                                                 email=email, mobile=mobile,
                                                                                 phone=phone,
                                                                                 location=location,
                                                                                 licence_date=licencedate,
                                                                                 userlevel=userlevel)
                            if int(userlevel) == 1:
                                try:
                                    myGroup = Group.objects.get(name="Cloud_Basic")
                                except:
                                    return JsonResponse({"status": "error", "errorcode": "no group",
                                                         "msg": gettext("This group does not exist!")})
                                myUser = AuthMessage.objects.get(username=username)
                                myUser.groups.clear()
                                myUser.user_permissions.clear()
                                myGroup.user_set.add(myUser)
                            else:
                                createFolder(username)
                                if int(userlevel) == 2:
                                    try:
                                        myGroup = Group.objects.get(name="Cloud_Advance")
                                    except:
                                        return JsonResponse({"status": "error", "errorcode": "no group",
                                                             "msg": gettext("This group does not exist!")})
                                    myUser = AuthMessage.objects.get(username=username)
                                    myUser.groups.clear()
                                    myUser.user_permissions.clear()
                                    myGroup.user_set.add(myUser)
                                elif int(userlevel) == 3:
                                    try:
                                        myGroup = Group.objects.get(name="Cloud_Deluxe")
                                    except Exception as e:
                                        print(e)
                                        return JsonResponse({"status": "error", "errorcode": "no group",
                                                             "msg": gettext("This group does not exist!")})
                                    myUser = AuthMessage.objects.get(username=username)
                                    myUser.groups.clear()
                                    myUser.user_permissions.clear()
                                    myGroup.user_set.add(myUser)
                                elif int(userlevel) == 4:
                                    try:
                                        myGroup = Group.objects.get(name="Cloud_Flagship")
                                    except:
                                        return JsonResponse({"status": "error", "errorcode": "no group",
                                                             "msg": gettext("This group does not exist!")})
                                    myUser = AuthMessage.objects.get(username=username)
                                    myUser.groups.clear()
                                    myUser.user_permissions.clear()
                                    myGroup.user_set.add(myUser)
                                return JsonResponse({"status": "success", "msg": ""})
                        except Exception as e:
                            msg = str(e)
                            logger.error(str(e))
                            return JsonResponse({"status": "error", "errorcode": "update system error", "msg": msg})
                    else:  # update

                        import socket
                        myname = socket.getfqdn(socket.gethostname())
                        myaddr = socket.gethostbyname(myname)
                        createResult = AuthMessage.objects.create(username=username, nickname=nick,
                                                                  password=password,
                                                                  is_superuser=0, is_staff=1,
                                                                  is_active=1, date_joined=nowtime, fixed_ip="",
                                                                  ip=myaddr,
                                                                  email=email, mobile=mobile, phone=phone,
                                                                  location=location,
                                                                  licence_date=licencedate, userlevel=userlevel,
                                                                  image_url="../static/images/user/user0.jpg")
                        createResult.save()
                        user = AuthMessage.objects.get(username=username)
                        user.user_permissions.clear()
                        workList = [Permission(name=str(username) + "_view_task", content_type_id=18,
                                               codename="views_commander_" + str(username) + "_view_task"),
                                    Permission(name=str(username) + "_assign_task", content_type_id=18,
                                               codename="views_commander_" + str(username) + "_assign_task"),
                                    Permission(name=str(username) + "_schedule_task", content_type_id=18,
                                               codename="views_commander_" + str(username) + "_schedule_task")]
                        Permission.objects.bulk_create(workList)
                        RobotInfo.objects.create(robot_name="robot_" + str(username), robot_status=1,
                                                 user_id=user.id)
                        filePath = settings.File_Root + "\\Draw_Process\\pyfile\\" + str(username)
                        judge = os.path.exists(filePath)
                        if judge == False:
                            os.mkdir(filePath)
                        if int(userlevel) != 1:
                            createFolder(username)
                        if int(userlevel) == 1:
                            try:
                                myGroup = Group.objects.get(name="Cloud_Basic")
                            except:
                                return JsonResponse({"status": "error", "errorcode": "no group",
                                                     "msg": gettext("This group does not exist!")})
                            myUser = AuthMessage.objects.get(username=username)
                            myGroup.user_set.add(myUser)
                        elif int(userlevel) == 2:
                            try:
                                myGroup = Group.objects.get(name="Cloud_Advance")
                            except:
                                return JsonResponse({"status": "error", "errorcode": "no group",
                                                     "msg": gettext("This group does not exist!")})
                            myUser = AuthMessage.objects.get(username=username)
                            myGroup.user_set.add(myUser)
                        elif int(userlevel) == 3:
                            try:
                                myGroup = Group.objects.get(name="Cloud_Deluxe")
                            except:
                                return JsonResponse({"status": "error", "errorcode": "no group",
                                                     "msg": gettext("This group does not exist!")})
                            myUser = AuthMessage.objects.get(username=username)
                            myGroup.user_set.add(myUser)
                        elif int(userlevel) == 4:
                            try:
                                myGroup = Group.objects.get(name="Cloud_Flagship")
                            except:
                                return JsonResponse({"status": "error", "errorcode": "no group",
                                                     "msg": gettext("This group does not exist!")})
                            myUser = AuthMessage.objects.get(username=username)
                            myGroup.user_set.add(myUser)
                        return JsonResponse({"status": "success", "msg": ""})
                except Exception as e:
                    msg = str(e)
                    logger.error(str(e))
                    return JsonResponse({"status": "error", "errorcode": "create system error", "msg": msg})



            except Exception as e:
                msg = str(e)
                logger.error(str(e))
                return JsonResponse({"status": "error", "errorcode":"no type", "msg": msg})

#teclead delete user
@csrf_exempt
def tecleadUserDelete(request):
    if request.method == 'POST':
        if request.POST:
            try:
                username = request.POST.get('user_name').lower()
                AuthMessage.objects.filter(username=username).delete()
                PerList = [str(username) + "_view_task", str(username) + "_assign_task",
                           str(username) + "_schedule_task"]
                Permission.objects.filter(name__in=PerList).delete()
                try:
                    deleteFolder(username)
                except Exception as e:
                    return JsonResponse({"status": "error", "errorcode": "delete folder error", "msg": str(e)})
                return JsonResponse({"status": "success", "msg": ""})
            except Exception as e:
                logger.error(e)
                return JsonResponse({"status": "error", "errorcode": "system error", "msg": str(e)})

# check user login status
@csrf_exempt
def checklogin(request):
    logger.info('check user')
    if request.method == 'POST':
        #judge whether the same computer
        try:
            username = request.session['username']
            if clients.__contains__(str(username) + "html"):
                msg = gettext("Please do not log in the same computer repeatedly!")
            return JsonResponse({"result": "repeat", "msg": msg})
        except:
            pass
        username = request.POST.get('username').lower()
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            if clients.__contains__(str(username) + "html"):
                return JsonResponse({"result":"yes"})
            else:
                return JsonResponse({"result":"no"})
        else:
            return JsonResponse({"result":"no"})
    else:
        return JsonResponse({"result":"no"})

# Create your views here.
@csrf_exempt
def userlogin(request):
    logger.info('请求成功！----')
    if request.method == 'POST':
        username = request.POST.get('username').lower()
        setting_file = settings.File_Root + "\\Draw_Process" + "\\setting.txt"

        url = request.get_host()
        if "choclead.teclead.com" not in url and "172.19.102.236:8000" not in url:
            logger.info('请求主网站----' + url)
            pemPath = ""
            timePath = ""
            with open(setting_file, 'r', encoding='utf-8') as ff:
                setting_content = ff.readlines()
                for i in range(len(setting_content)):
                    setting_list = setting_content[i].rstrip("\n").split("=")
                    if 'pem' in setting_list[0]:
                        pemPath = settings.File_Root + "\\Draw_Process\\" + setting_list[1].replace(" ", "")
                    elif 'time' in setting_list[0]:
                        timePath = settings.File_Root + "\\Draw_Process\\" + setting_list[1].replace(" ", "")
            logger.info('开始解密----' + pemPath + "timePath" + timePath)
            if pemPath != "" and timePath != "":
                try:
                    with open(pemPath, 'rb') as privatefile:
                        p = privatefile.read()
                        logger.info("privateKey:" + str(p))
                    privkey = rsa.PrivateKey.load_pkcs1(p)
                    with open(timePath, 'rb') as ff:
                        content = ff.read()
                        logger.info("timeContent:" + str(content))
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
                    nowtime = datetime.datetime.now()
                    if nowtime > end_time:
                        logger.info("Your software has expired, please contact your administrator!")
                        msg = gettext("Your software has expired, please contact your administrator!")
                        return render(request, 'login.html',
                                      {"type": "error", "message": msg, "username": "", "password": ""})
                    else:
                        try:
                            last_login = AuthMessage.objects.all().aggregate(Max('last_login'))['last_login__max']
                            if nowtime < last_login:
                                logger.info("Illegal time, please contact your administrator!")
                                msg = gettext("Illegal time, please contact your administrator!")
                                return render(request, 'login.html',
                                              {"type": "error", "message": msg, "username": "", "password": ""})
                        except:
                            pass
                        diff_days = (end_time - nowtime).days
                        request.session['day'] = diff_days
                        request.session.set_expiry(end_time)
                except Exception as e:
                    logger.error(e)
                    msg = gettext("Incorrect configuration file, please contact your administrator!")
                    return render(request, 'login.html',
                                  {"type": "error", "message": msg, "username": "", "password": ""})
            else:
                logger.info("private file or time file is not exsiting!")
                logger.warning("private file or time file is not exsiting!")
                msg = gettext("Lost encrypted file, please contact your administrator!")
                return render(request, 'login.html', {"type": "error", "message": msg, "username": "", "password": ""})
        password = request.POST.get('password')
        language = request.POST.get('language_value')
        saveUser = request.POST.get('saveuser')
        savePSW = request.POST.get('savepsw')
        request.session['language'] = language
        user = authenticate(request, username=username, password=password)
        try:
            error_num = request.session['error_num']
            if error_num == 5:
                error_time_str = request.session['error_time'].split(".")[0]
                error_time = datetime.datetime.strptime(error_time_str, "%Y-%m-%d %H:%M:%S")
                seconds = (nowtime - error_time).total_seconds()
                mins = 10 - int(seconds / 60)
                if mins > 0:
                    msg = gettext("This user has been locked for 10 minutes,please try again after ") + str(mins) + gettext(" minutes!")
                    return render(request, 'login.html', {"type": "error", "message": msg, "username": username, "password": password})
        except:
            pass
        if user is not None:
            logger.info("authenticate ok---")
            try:
                if clients.__contains__(str(username) + "html"):
                    clients[str(username) + "html"].send(json.dumps({"action": "exit"}))
                department_status = user.department.status
                if department_status == "0":
                    logger.info("The user's department is disabled!")
                    msg = gettext("The user's department is disabled!")
                    return render(request, 'login.html',
                                  {"type": "error", "message": msg, "username": username, "password": password})
                else:
                    try:
                        company_status = user.department.company.status
                        if company_status == "0":
                            logger.info("The user's company is disabled!")
                            msg = gettext("The user's company is disabled!")
                            return render(request, 'login.html',
                                          {"type": "error", "message": msg, "username": username, "password": password})
                        else:
                            try:
                                organization_status = user.department.company.organization.status
                                if organization_status == "0":
                                    logger.info("The user's organization is disabled!")
                                    msg = gettext("The user's organization is disabled!")
                                    return render(request, 'login.html',
                                                  {"type": "error", "message": msg, "username": username,
                                                   "password": password})
                            except:
                                pass
                    except:
                        pass
            except:
                pass
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
            imageurl = field['image_url']
            x_forwarded_for = request.META.get('HTTP_X_FORARDED_FOR')
            if x_forwarded_for:
                current_ip = x_forwarded_for.split(',')[-1].strip()
            else:
                current_ip = request.META.get('REMOTE_ADDR')
            perms = AuthMessage.get_all_permissions(user)
            logger.info("update ip=====")
            AuthMessage.objects.filter(username=username).update(ip=current_ip)
            if nickname == "" or nickname is None:
                nickname = user
            request.session['session_name'] = "admin"
            ProcessCopy.objects.filter(create_by=username).delete()
            try:
                if username:
                    request.session['username'] = username.lower()  # 使用session来保存用户登录信息
                if password:
                    request.session['password'] = password
            except:
                pass
            version = request.POST.get('version')
            if version == '2.0':
                obj = HttpResponseRedirect('/index2/')
                if saveUser == 'on':
                    obj.set_cookie('username', username, expires=datetime.datetime.now() + timedelta(days=300))
                else:
                    obj.delete_cookie('username')
                if savePSW == 'on':
                    obj.set_cookie('pwd', password, expires=datetime.datetime.now() + timedelta(days=300))
                else:
                    obj.delete_cookie('pwd')
                logger.info("return index2=====")
                return obj
            else:
                obj1 = HttpResponseRedirect('/index/')
                if saveUser == 'on':
                    obj1.set_cookie('username', username, expires=datetime.now() + timedelta(days=14))
                if savePSW == 'on':
                    obj1.set_cookie('pwd', password, expires=datetime.now() + timedelta(days=14))
                logger.info("return index=====")
                return obj1
        else:
            try:
                status = AuthMessage.objects.filter(username=username).values('is_active')[0]['is_active']
                if status == False:
                    msg = gettext("This user has been blocked!")
                else:
                    try:
                        error_time_str = request.session['error_time'].split(".")[0]
                        error_time = datetime.datetime.strptime(error_time_str, "%Y-%m-%d %H:%M:%S")
                        seconds = (nowtime - error_time).total_seconds()
                        mins = 10 - int(seconds / 60)
                        if mins > 0:
                            msg = gettext("This user has been locked for 10 minutes,please try again after ") + str(
                                mins) + gettext(" minutes!")
                            return render(request, 'login.html',
                                          {"type": "error", "message": msg, "username": username, "password": password})
                    except:
                        pass
                    try:
                        error_num = request.session['error_num']
                        error_num = int(error_num) + 1
                    except:
                        error_num = 1
                    request.session['error_num'] = error_num
                    if error_num == 5:
                        msg = gettext("This user has been locked for 10 minutes,please try again after 10 minutes!")
                        request.session['error_time'] = str(nowtime)
                    elif error_num >= 7 and error_num < 10:
                        times = 10 - error_num
                        msg = gettext("This user will be blocked after ") + str(times) + gettext(" errors!")
                    elif error_num == 10:
                        msg = gettext("This user has been blocked!")
                        del request.session['error_num']
                        del request.session['error_time']
                        AuthMessage.objects.filter(username=username).update(is_active=False)
                    else:
                        msg = gettext("Username or password is incorrenct!")
            except:
                msg = gettext("Username or password is incorrenct!")
            return render(request, 'login.html',
                          {"type": "error", "message": msg, "username": username, "password": password})
    elif request.method == "GET":
        username = ''
        pwd = ''
        Userchecked ="0"
        Pwschecked="0"
        if 'username' in request.COOKIES:
            username = request.COOKIES['username']
            Userchecked ="1"
        if  'pwd' in request.COOKIES:
            pwd = request.COOKIES['pwd']
            Pwschecked = "1"
        else:
            pass
        return render(request, "login.html",
                      {'usernames': username, 'pwd': pwd, "userchecked": Userchecked, "pwschecked": Pwschecked})
    else:
        pass

def logout(request):
    auth.logout(request)
    request.session.flush()
    return HttpResponseRedirect('/login/')


@csrf_exempt
def changepassword(request):
    if 'username' in request.session and 'password' in request.session:
        username = request.session['username']
        if request.method == 'GET':
            return render(request, 'information.html')
        elif request.method == 'POST':
            try:
                language = request.session['language']
                oldpwd = request.POST.get('oldPassword')
                newpwd = request.POST.get('newPassword')
                user = AuthMessage.objects.get(username=username)
                pwd = user.password
                pwd_bool = check_password(oldpwd, pwd)
                if pwd_bool is True:
                    user.set_password(newpwd)
                    user.save()
                    msg = gettext("Reset password successfully!")
                    return JsonResponse({"message": msg})
                else:
                    msg = gettext("Orginal password is incorrect!")
                    return JsonResponse({"message": msg})
            except Exception:
                exstr = str(traceback.format_exc())
                return JsonResponse({"result": "failed", "message": exstr})
    else:
        return render(request, "login.html")

@csrf_exempt
def ResetPassword(request):
    if 'username' in request.session and 'password' in request.session:
        try:
            username = request.session['username']
            log_creat_user = {}
            log_creat_user["action"] = "reset user password"
            try:
                log_creat_user["computer name"] = pc_names[username.lower()]
            except:
                pass
            log_creat_user["username"] = username
            log_creat_user["time"] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
            language = request.session['language']
            userid = request.POST.get('loginCode')
            log_creat_user["account"] = userid
            log_user_json = "605>" + json.dumps(log_creat_user)
            logger.info(log_user_json)
            newpassword = make_password("12345678", None, 'pbkdf2_sha256')
            AuthMessage.objects.filter(username=userid).update(password=newpassword)
            msg = gettext("Password has been reset to 12345678!")
            return JsonResponse({"result": "success", "message": msg})
        except Exception as e:
            msg = gettext("Reset password failed!")
            return JsonResponse({"result": "failed", "message": msg})
    else:
        return render(request, "login.html")



@csrf_exempt
def getUser(request):
    if 'username' in request.session and 'password' in request.session:
        if request.method == 'POST':
            username = request.session['username']
            result = {}
            result["username"] = username
            return JsonResponse(result)
    else:
        return render(request, "login.html")


#地区选择
@csrf_exempt
def areaSelect(request):
    if request.method == 'POST':
        area_list = SysArea.objects.all().values('area_code','parent_code','area_name')
        area_array = []
        for i in range(len(area_list)):
            area_json = {}
            area_json["id"] = area_list[i]['area_code']
            area_json["name"] = area_list[i]['area_name']
            area_json["pId"] = area_list[i]['parent_code']
            area_array.append(area_json)
        return JsonResponse({"list":area_array})


#显示用户列表
@csrf_exempt
def orgaccountList(request):
    if 'username' in request.session and 'password' in request.session:
        username = request.session['username']
        if request.method == 'POST':
            page_No = request.POST.get("pageNo")
            page_Size = request.POST.get("pageSize")
            orderBy = request.POST.get("orderBy")
            # 筛选条件
            loginCode = xstr(request.POST.get("loginCode"))  #用户名
            nickName = xstr(request.POST.get("userName"))    #姓名
            location = xstr(request.POST.get("location"))
            if location != '' and location != None:
                try:
                    location = SysArea.objects.filter(area_name__icontains=location).values('area_code')[0]['area_code']
                except:
                    pass
            email = xstr(request.POST.get("email"))
            organization = xstr(request.POST.get("organization"))
            company = xstr(request.POST.get("company"))
            mobile = xstr(request.POST.get("mobile"))
            department = xstr(request.POST.get("department"))
            if "asc" in orderBy:
                order_condition = orderBy.split(" ")[0]
            elif orderBy == "":
                order_condition = ""
            else:
                order_condition = "-" + orderBy.split(" ")[0]
            if "company" in order_condition:
                order_condition = order_condition.replace("company","department__company")
            elif "organization" in order_condition:
                order_condition = order_condition.replace("organization","department__company__organization")
            elif "status" in order_condition:
                order_condition = order_condition.replace("status","is_active")
            if page_No == "":
                pageNo = 1
            else:
                pageNo = int(page_No)
            if page_Size == "":
                pageSize = 20
            else:
                pageSize = int(page_Size)

            findUser= AuthMessage.objects.filter(username=username).first()
            issuper =  findUser.is_superuser
            if issuper:
                 auth_tupe = AuthMessage.objects.all()
            else:
                auth = "Draw_Process.views_panel_user_list_menu_search_all_organizations"
                user_organization = userutils.getOrganization(username, auth)
                try:
                    if orderBy == "":
                        if user_organization == '':
                            auth_tupe = AuthMessage.objects.all().filter(username__icontains=loginCode,
                                                                         location__icontains=location,
                                                                         email__icontains=email,
                                                                         mobile__icontains=mobile,
                                                                         nickname__icontains=nickName,
                                                                         department__company__organization__organization__icontains=organization,
                                                                         department__company__company__icontains=company,
                                                                         department__department_name__icontains=department).order_by(
                                'is_active')
                        else:
                            auth_tupe = AuthMessage.objects.all().filter(username__icontains=loginCode,
                                                                         location__icontains=location,
                                                                         email__icontains=email,
                                                                         mobile__icontains=mobile,
                                                                         nickname__icontains=nickName,
                                                                         department__company__organization__organization__icontains=organization,
                                                                         department__company__company__icontains=company,
                                                                         department__department_name__icontains=department).order_by(
                                'is_active')
                    else:
                        if user_organization == '':
                            auth_tupe = AuthMessage.objects.all().filter(username__icontains=loginCode,
                                                                         location__icontains=location,
                                                                         email__icontains=email,
                                                                         mobile__icontains=mobile,
                                                                         nickname__icontains=nickName,
                                                                         department__company__organization__organization__icontains=organization,
                                                                         department__company__company__icontains=company,
                                                                         department__department_name__icontains=department).order_by(
                                order_condition)
                        else:
                            auth_tupe = AuthMessage.objects.all().filter(username__icontains=loginCode,
                                                                         location__icontains=location,
                                                                         email__icontains=email,
                                                                         mobile__icontains=mobile,
                                                                         nickname__icontains=nickName,
                                                                         department__company__organization__organization__icontains=organization,
                                                                         department__company__company__icontains=company,
                                                                         department__department_name__icontains=department).order_by(
                                order_condition)
                except Exception as e:
                    s = str(e)
                    a = 'aa'
            auth_list = serializers.serialize('json', auth_tupe)
            auth_array = json.loads(auth_list)
            auth_result = []
            count = len(auth_array)
            if (pageNo) * pageSize <= len(auth_array):
                startNo = (pageNo - 1) * pageSize
                endNo = (pageNo) * pageSize
            else:
                startNo = (pageNo - 1) * pageSize
                endNo = len(auth_array)
            for j in range(startNo, endNo):
                auth_json = {}
                field = auth_array[j]['fields']
                auth_json["username"] = field['username']
                auth_json["ip"] = field['fixed_ip']
                status = AuthMessage.objects.filter(username=field['username']).values('is_active')[0]['is_active']
                if status == True:
                    auth_json["status"] = gettext("Normal")
                else:
                    auth_json["status"] = gettext("Block")
                auth_json["nickname"] = field['nickname']
                auth_json["location"] = field['location']
                # try:
                #     auth_json["location"] = SysArea.objects.filter(area_code=areaCode).values('area_name')[0]['area_name']
                # except:
                #     auth_json["location"] = ""
                departmentCode = field['department']
                try:
                    depart = []
                    depart = Department.objects.filter(department_code=departmentCode).values(
                        'department_name',
                        'company__company',
                        'company__organization__organization')
                   # depart = Department.objects.filter(department_code=departmentCode).values('department_name','company__company','organization__organization')
                    if len(depart) == 0:
                        auth_json["department"] = ""
                        auth_json["organization"] = ""
                        auth_json["company"] = ""
                    else:
                         auth_json["department"] = depart[0]['department_name']
                         auth_json["organization"] = depart[0]['company__organization__organization']
                         auth_json["company"] = depart[0]['company__company']
                except Exception as e:
                    sss =  str(e)
                    logger.info(sss)
                    auth_json["department"] = ""
                    auth_json["organization"] =  ""
                    auth_json["company"] =  ""
                auth_json["email"] = field['email']
                auth_json["mobile"] = field['mobile']
                auth_json["phone"] = field['phone']
                auth_json["update_date"] = field['update_date']
                auth_json["operator"] = field['operator']
                auth_result.append(auth_json)
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
            account_json["count"] = len(auth_array)
            account_json["first"] = 1
            account_json["next"] = nextNo
            account_json["pageNo"] = pageNo
            account_json["pageSize"] = pageSize
            account_json["last"] = totalPage
            account_json["list"] = auth_result
            return JsonResponse(account_json)
    else:
        return render(request, "login.html")





def xstr(s):
    if s is None:
        return ''
    else:
        return s



#角色添加的账号列表
@csrf_exempt
def roleAddAccountList(request):
    if 'username' in request.session and 'password' in request.session:
        username = request.session['username']
        if request.method == 'POST':
            page_No = request.POST.get("pageNo")
            page_Size = request.POST.get("pageSize")
            orderBy = request.POST.get("orderBy")
            # 筛选条件
            loginCode = request.POST.get("loginCode")
            userName = request.POST.get("userName")
            email = request.POST.get("email")
            mobile = request.POST.get("mobile")
            phone = request.POST.get("phone")
            if "asc" in orderBy:
                order_condition = orderBy.split(" ")[0]
            elif orderBy == "":
                order_condition = ""
            else:
                order_condition = "-" + orderBy.split(" ")[0]
            if page_No == "":
                pageNo = 1
            else:
                pageNo = int(page_No)
            if page_Size == "":
                pageSize = 20
            else:
                pageSize = int(page_Size)
            if orderBy == "":
                auth_tupe = AuthMessage.objects.all().filter(username__icontains=loginCode, nickname__icontains=userName,
                                                             email__icontains=email,
                                                             mobile__icontains=mobile, phone__icontains=phone)
            else:
                auth_tupe = AuthMessage.objects.all().filter(username__icontains=loginCode, nickname__icontains=userName,
                                                             email__icontains=email,
                                                             mobile__icontains=mobile, phone__icontains=phone).order_by(order_condition)
            auth_list = serializers.serialize('json', auth_tupe)
            auth_array = json.loads(auth_list)
            auth_result = []
            count = len(auth_array)
            if (pageNo) * pageSize <= len(auth_array):
                startNo = (pageNo - 1) * pageSize
                endNo = (pageNo) * pageSize
            else:
                startNo = (pageNo - 1) * pageSize
                endNo = len(auth_array)
            for j in range(startNo, endNo):
                auth_json = {}
                field = auth_array[j]['fields']
                auth_json["user"] = field['username']
                status = AuthMessage.objects.filter(username=field['username']).values('is_active')[0]['is_active']
                useinfo =AuthMessage.objects.filter(username=field['username']).values('is_active','department__company__company','department__company__organization__organization')
                if status == True:
                    auth_json["status"] = gettext("Normal")
                else:
                    auth_json["status"] = gettext("Block")
                auth_json["name"] = field['username']
                auth_json["location"] = field['location']
                auth_json["organization"] = ''
                auth_json["company"] = ''
                auth_json["email"] = field['email']
                auth_json["mobile"] = field['mobile']
                auth_json["phone"] = field['phone']
                auth_json["updateDate"] = field['update_date']
                auth_json["operator"] = field['operator']
                auth_result.append(auth_json)
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
            account_json["count"] = len(auth_array)
            account_json["first"] = 1
            account_json["next"] = nextNo
            account_json["pageNo"] = pageNo
            account_json["pageSize"] = pageSize
            account_json["last"] = totalPage
            account_json["list"] = auth_result
            return JsonResponse(account_json)
    else:
        return render(request, "login.html")

#角色列表
@csrf_exempt
def userRoleList(request):
    if 'username' in request.session and 'password' in request.session:
        username = request.session['username']
        if request.method == 'POST':
            loginCode = request.GET['loginCode']
            user = AuthMessage.objects.get(username=username)
            perms = AuthMessage.get_all_permissions(user)
            if "Draw_Process.views_panel_user_list_menu_search_all_organizations" in perms:
                user_organization = ''
            else:
                try:
                    user_organization = user.department.company.organization.organization
                except:
                    user_organization = None
            if user_organization == '':
                auth_tupe = SysRole.objects.all().order_by('role_sort')
            else:
                auth_tupe = SysRole.objects.filter(organization=user_organization).order_by('role_sort')
            auth_list = serializers.serialize('json', auth_tupe)
            auth_array = json.loads(auth_list)
            auth_result = []
            for i in range(len(auth_array)):
                auth_json = {}
                field = auth_array[i]['fields']
                roleCode = field['role_code']
                auth_json["roleCode"] = roleCode
                auth_json["roleName"] = field['role_name']
                myGroup = Group.objects.get(name=roleCode)
                user_list = []
                users = list(myGroup.user_set.all())
                for user in users:
                    user_list.append(user.username)
                if loginCode in user_list:
                    auth_json["checked"] = "true"
                else:
                    auth_json["checked"] = "false"
                auth_result.append(auth_json)
            account_json = {}
            account_json["list"] = auth_result
            return JsonResponse(account_json)
    else:
        return render(request, "login.html")

#更新用户的角色分配
@csrf_exempt
def updateUserAssign(request):
    if 'username' in request.session and 'password' in request.session:
        username = request.session['username']
        log_creat_user = {}
        log_creat_user["action"] = "assign roles for user"
        try:
            log_creat_user["computer name"] = pc_names[username.lower()]
        except:
            pass
        log_creat_user["username"] = username
        log_creat_user["time"] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
        language = request.session['language']
        if request.method == 'POST':
            try:
                userCode = request.POST.get("userCode")
                log_creat_user["account"] = userCode
                user = AuthMessage.objects.get(username=userCode)
                user.groups.clear()
                user.user_permissions.clear()
                roleCodes = request.POST.getlist('roleCodes[]')
                for i in range(len(roleCodes)):
                    roleCode = roleCodes[i]
                    myGroup = Group.objects.get(name=roleCode)
                    myGroup.user_set.add(user)
                msg = gettext("User assign roles successfully!")
                result = {"result":"success","msg":msg}
                log_creat_user["roles"] =  str(roleCodes)
                log_user_json = "606>" + json.dumps(log_creat_user)
                logger.info(log_user_json)
            except:
                msg = gettext("User assign roles failed!")
                result = {"result": "failed", "msg": msg}
            return JsonResponse(result)
    else:
        return render(request, "login.html")

#菜单进入用户列表的入口
@csrf_exempt
def orgUser(request):
    if 'username' in request.session and 'password' in request.session:
        username = request.session['username']
        language = request.session['language']
        auth = "Draw_Process.views_panel_user_list_menu_search_all_organizations"
        json = userutils.organizationAuth(username,auth,language)
        return render(request,'orgUser.html',json)
    else:
        return render(request, "login.html")

#增加用户
@csrf_exempt
def orguseradd(request):
    if 'username' in request.session and 'password' in request.session:
        username = request.session['username']
        language = request.session['language']
        auth = 'Draw_Process.views_panel_user_list_menu_search_all_organizations'
        json = userutils.organizationAuth(username,auth,language)
        return render(request, 'orgUserAdd.html', json)
    else:
        return render(request, "login.html")
#是否禁用用户
@csrf_exempt
def changeUserStatus(request):
    if 'username' in request.session and 'password' in request.session:
        username = request.session['username']
        language = request.session['language']
        loginCode = request.POST.get('loginCode')
        log_creat_user = {}
        log_creat_user["action"] = "active/inactive user"
        try:
            log_creat_user["computer name"] = pc_names[username.lower()]
        except:
            pass
        log_creat_user["username"] = username
        log_creat_user["time"] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
        log_creat_user["account"] = loginCode
        try:
            status = AuthMessage.objects.filter(username=loginCode).values('is_active')[0]['is_active']
            if status == True:
                AuthMessage.objects.filter(username=loginCode).update(is_active=False)
                log_creat_user["status"] = "inactive"
                log_user_json = "602>" + json.dumps(log_creat_user)
                logger.info(log_user_json)
            else:
                AuthMessage.objects.filter(username=loginCode).update(is_active=True)
                log_creat_user["status"] = "active"
                log_user_json = "602>" + json.dumps(log_creat_user)
                logger.info(log_user_json)
            result = {"result":"success"}
        except:
            msg = gettext("Change user status failed!")
            result = {"result":msg}
        return JsonResponse(result)
    else:
        return render(request, "login.html")

@csrf_exempt
def changeTreeSort(request):
    if 'username' in request.session and 'password' in request.session:
        username = request.session['username']
        upperDepartmentCode = request.POST.get('upperDepartmentCode')
        upperDepartment = request.POST.get('upperDepartment')
        department_json = {}
        if upperDepartmentCode == '' or upperDepartmentCode == None:
            maxCode_tuple = Department.objects.filter(tree_level=0).aggregate(Max('department_code'))
            maxCode = maxCode_tuple['department_code__max']
            try:
                departmentCode = int(maxCode) + 1
            except:
                departmentCode = 1000
            maxSort_tuple = Department.objects.filter(tree_level=0).aggregate(Max('tree_sort'))
            maxSort = maxSort_tuple['tree_sort__max']
            try:
                treeSort = int(maxSort) + 10
            except:
                treeSort = 10
            department_json['upperDepartmentCode'] = ''
            department_json['upperDepartment'] = ''
            department_json['departmentCode'] = departmentCode
            department_json['treeSort'] = treeSort
        else:
            maxCode_tuple = Department.objects.filter(parent_code=upperDepartmentCode).aggregate(Max('department_code'))
            maxCode = maxCode_tuple['department_code__max']
            try:
                departmentCode = int(maxCode) + 1
            except:
                departmentCode = str(upperDepartmentCode) + "001"
            maxSort_tuple = Department.objects.filter(parent_code=upperDepartmentCode).aggregate(Max('tree_sort'))
            maxSort = maxSort_tuple['tree_sort__max']
            try:
                treeSort = int(maxSort) + 10
            except:
                treeSort = 10
            department_json['upperDepartmentCode'] = upperDepartmentCode
            department_json['upperDepartment'] = upperDepartment
            department_json['departmentCode'] = departmentCode
            department_json['treeSort'] = treeSort
        return JsonResponse(department_json)
    else:
        return render(request, "login.html")


#点击菜单用户列表入口
@csrf_exempt
def orgEdit(request):
    if 'username' in request.session and 'password' in request.session:
        username = request.session['username']
        userid = request.GET['user']
        auth_msg = AuthMessage.objects.all().filter(username=userid)
        auth_msg_list = serializers.serialize('json', auth_msg)
        auth_msg_array = json.loads(auth_msg_list)
        field = auth_msg_array[0]['fields']
        loginCode = field['username']
        nickName = field['nickname']
        ip = field['fixed_ip']
        area = field['location']
        departmentCode = field['department']
        try:
            departmentinfo = Department.objects.filter(department_code=departmentCode).values('department_name',
                                                                                      'company__company',
                                                                                      'company__organization__organization')
            if len(departmentinfo) > 0:
                department = departmentinfo[0]
                officeName = department['company__organization__organization']
                companyName = department['company__company']
                departname = department['department_name']
            else:
                officeName = ''
                companyName = ''
                departname = ''
            #department = Department.objects.filter(department_code=departmentCode).values('department_name')[0]['department_name']
        except:
            department = ""

        email = field['email']
        mobile = field['mobile']
        phone = field['phone']
        auth_json = {"loginCode": loginCode, "ip": ip, "nickName": nickName, "area": area,
                     "officeName": officeName, "companyName": companyName, "department": departname,
                     "departmentCode": departmentCode, "email": email, "mobile": mobile, "phone": phone}
        return render(request,'orgUserEdit.html',auth_json)
    else:
        return render(request, "login.html")

#取消用户的权限
@csrf_exempt
def cancelUserAuthorization(request):
    if 'username' in request.session and 'password' in request.session:
        try:
            username = request.session['username']
            log_creat_user = {}
            log_creat_user["username"] = username
            log_creat_user["time"] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
            language = request.session['language']
            roleCode = request.POST.get('roleCode')
            log_creat_user["role code"] = str(roleCode)
            userName = request.POST.get('userName')
            myGroup = Group.objects.get(name=roleCode)
            org_users = list(myGroup.user_set.all())
            user_list = []
            for org_user in org_users:
                if org_user.username != userName:
                    user_list.append(org_user.username)
            log_creat_user["users "] = str(user_list)
            log_user_json = "704>" + json.dumps(log_creat_user)
            logger.info(log_user_json)
            user = AuthMessage.objects.get(username=userName)
            myGroup.user_set.remove(user)
            msg = gettext("Remove user successfully!")
            result = {"result":"success","message":msg}
        except Exception:
            msg = gettext("Remove user failed!")
            result = {"result": "failed", "message": msg}
        return JsonResponse(result)
    else:
        return render(request, "login.html")
#取消所有用户的权限
@csrf_exempt
def cancelUsersAuthorization(request):
    if 'username' in request.session and 'password' in request.session:
        try:
            username = request.session['username']
            language = request.session['language']
            roleCode = request.POST.get('roleCode')
            userNames = request.POST.getlist('userNames[]')
            myGroup = Group.objects.get(name=roleCode)
            for userName in userNames:
                user = AuthMessage.objects.get(username=userName)
                myGroup.user_set.remove(user)
            msg = gettext("Remove user successfully!")
            result = {"result":"success","message":msg}
        except Exception:
            msg = gettext("Remove user failed!")
            result = {"result": "failed", "message": msg}
        return JsonResponse(result)
    else:
        return render(request, "login.html")


#用户权限编辑入口
@csrf_exempt
def userEditPermission(request):
    if 'username' in request.session and 'password' in request.session:
        username = request.session['username']
        userid = request.GET['user']
        auth_msg = AuthMessage.objects.all().filter(username=userid)
        auth_msg_list = []
        auth_msg_list = serializers.serialize('json', auth_msg)
        auth_msg_array = json.loads(auth_msg_list)
        field = auth_msg_array[0]['fields']
        loginCode =field['username']
        userName = field['nickname']
        auth_json = {"loginCode":loginCode,"userName":userName}
        return render(request,'orgUserPermission.html',auth_json)
    else:
        return render(request, "login.html")

#用户文件夹权限编辑入口
@csrf_exempt
def userFolderPermission(request):
    if 'username' in request.session and 'password' in request.session:
        username = request.session['username']
        userid = request.GET['user']
        auth_msg = AuthMessage.objects.all().filter(username=userid)
        auth_msg_list = []
        auth_msg_list = serializers.serialize('json', auth_msg)
        auth_msg_array = json.loads(auth_msg_list)
        field = auth_msg_array[0]['fields']
        loginCode =field['username']
        userName = field['nickname']
        auth_json = {"loginCode":loginCode,"userName":userName}
        return render(request,'orgUserFolderPermission.html',auth_json)
    else:
        return render(request, "login.html")

#用户权限编辑入口
@csrf_exempt
def userCommanderPermission(request):
    if 'username' in request.session and 'password' in request.session:
        username = request.session['username']
        userid = request.GET['user']
        auth_msg = AuthMessage.objects.all().filter(username=userid)
        auth_msg_list = []
        auth_msg_list = serializers.serialize('json', auth_msg)
        auth_msg_array = json.loads(auth_msg_list)
        field = auth_msg_array[0]['fields']
        loginCode =field['username']
        userName = field['nickname']
        auth_json = {"loginCode":loginCode,"userName":userName}
        return render(request,'orgUserCommanderPermission.html',auth_json)
    else:
        return render(request, "login.html")

#给用户分配角色入口
@csrf_exempt
def userEditAssign(request):
    if 'username' in request.session and 'password' in request.session:
        username = request.session['username']
        userid = request.GET['user']   #
        auth_msg = AuthMessage.objects.all().filter(username=userid)
        auth_msg_list = []
        auth_msg_list = serializers.serialize('json', auth_msg)
        auth_msg_array = json.loads(auth_msg_list)
        field = auth_msg_array[0]['fields']
        loginCode = userid
        userName = field['nickname']
        auth_json = {"loginCode":loginCode,"userName":userName}
        return render(request,'orgUserAssign.html',auth_json)
    else:
        return render(request, "login.html")
#删除用户
@csrf_exempt
def userDelete(request):
    if 'username' in request.session and 'password' in request.session:
        try:
            username = request.session['username']
            log_delete_user = {}
            log_delete_user["action"] = "delete user"
            try:
                log_delete_user["computer name"] = pc_names[username.lower()]
            except:
                pass
            log_delete_user["username"] = username
            log_delete_user["time"] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
            language = request.session['language']
            userid = request.POST.get('loginCode')
            log_delete_user["deleted user"] = str(userid)
            AuthMessage.objects.filter(username=userid).delete()
            PerList = [str(userid) + "_view_task", str(userid) + "_assign_task", str(userid) + "_schedule_task"]
            Permission.objects.filter(name__in=PerList).delete()
            msg = gettext("Delete account successfully!")
            log_user_json = "607>" + json.dumps(log_delete_user)
            logger.info(log_user_json)
            return JsonResponse({"result":"true","message":msg})
        except Exception as e:
            msg = gettext("Delete account failed!")
            return JsonResponse({"result": "false", "message": msg})
    else:
        return render(request, "login.html")

@csrf_exempt
def updateinformation(request):
    if 'username' in request.session and 'password' in request.session:
        username = request.session['username']
        page = request.GET['page']
        auth_msg = AuthMessage.objects.filter(username=username)
        auth_msg_list = []
        auth_msg_list = serializers.serialize('json', auth_msg)
        auth_msg_array = json.loads(auth_msg_list)
        field = auth_msg_array[0]['fields']
        nickname = xstr(field['nickname'])
        sex = xstr(field['sex'])
        imageurl = xstr(field['image_url'])
        email = xstr(field['email'])
        fixed_ip = xstr(field['fixed_ip'])
        mobile = xstr(field['mobile'])
        phone = xstr(field['phone'])
        sign = xstr(field['signature'])
        return render(request,'information.html',{"page":page,"userID":username,"fixed_ip":fixed_ip,"user":nickname,"sex":sex,"imageurl":imageurl,"email":email,"mobile":mobile,"phone":phone,"sign":sign})
    else:
        return render(request, "login.html")

#创建用户
@csrf_exempt
def createUserID(request):
    log_creat_user={}
    log_creat_user["action"] = "create user"
    operation_username = request.session["username"]
    try:
        log_creat_user["computer name"] = pc_names[operation_username.lower()]
    except:
        pass
    log_creat_user["username"] = operation_username
    log_creat_user["time"] = time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time()))
    # adduser_info = str(request.POST)
    # index = adduser_info.find("{")
    # log_creat_user["info"] = adduser_info[index::].replace(">","")
    # log_user_json = "600>"+json.dumps(log_creat_user)
    # logger.info(log_user_json)
    if 'username' in request.session and 'password' in request.session:
        try:
            if request.method == 'POST':
                try:
                    language = request.session['language']
                    organization = request.POST.get('organization')
                    company = request.POST.get('company')
                    account = request.POST.get('account')
                    nick = request.POST.get('name')  #昵称
                    email = request.POST.get('email')
                    mobile = request.POST.get('mobile')
                    phone = request.POST.get('phone')
                    location = request.POST.get('location')
                    department = request.POST.get('department')
                    ip = request.POST.get('ip')
                    nowtime = datetime.datetime.now()
                    passwords = make_password("12345678", None, 'pbkdf2_sha256')
                    import socket
                    myname = socket.getfqdn(socket.gethostname())
                    myaddr = socket.gethostbyname(myname)
                    com = Department.objects.filter(department_code=department)[0]
                    createResult = AuthMessage.objects.create(username=account,nickname=nick,password=passwords,is_superuser=0, is_staff=1,
                                            is_active=1, date_joined=nowtime,  fixed_ip=ip, ip=myaddr, email=email,
                                                              mobile=mobile, department= com ,
                                                              phone=phone, location=location,
                                                              image_url="../static/images/user/user0.jpg")
                    createResult.save()
                    user = AuthMessage.objects.get(username=account)
                    user.user_permissions.clear()
                    workList = [Permission(name=str(account) + "_view_task", content_type_id=18,
                                           codename="views_commander_" + str(account) + "_view_task"),
                                Permission(name=str(account) + "_assign_task", content_type_id=18,
                                           codename="views_commander_" + str(account) + "_assign_task"),
                                Permission(name=str(account) + "_schedule_task", content_type_id=18,
                                           codename="views_commander_" + str(account) + "_schedule_task")]
                    Permission.objects.bulk_create(workList)
                    RobotInfo.objects.create(robot_name="robot_" + str(account), robot_status=1, user_id=user.id)
                    roleCodes = request.POST.getlist('roleCodes[]')
                    for i in range(len(roleCodes)):
                        roleCode = roleCodes[i]
                        myGroup = Group.objects.get(name=roleCode)
                        myGroup.user_set.add(user)
                    filePath = settings.File_Root + "\\Draw_Process\pyfile\\" + str(account)
                    judge = os.path.exists(filePath)
                    if judge == False:
                        os.mkdir(filePath)
                    msg = gettext("User account created successfully!")
                    log_creat_user["info"] = {"organization":organization,"company":company,"username":account,"nickname":nick,"email":email,"mobile":mobile,"phone":phone,"loation":location,"ip":ip,"department":com.department_name,"roles":roleCodes}
                    log_user_json = "600>" + json.dumps(log_creat_user)
                    logger.info(log_user_json)
                    return JsonResponse({"result":"success","msg": msg})
                except Exception as e:
                    exstr = str(traceback.format_exc())
                    return JsonResponse({"result":"failed","msg": exstr})
        except Exception as e:
            exstr = str(traceback.format_exc())
            return JsonResponse({"result": "failed", "msg": exstr})
    else:
        return render(request, "login.html")

#编辑用户
@csrf_exempt
def updateUserInformation(request):
    log_update_user = {}
    log_update_user["action"] = "update user"
    operation_username = request.session["username"]
    try:
        log_update_user["computer name"] = pc_names[operation_username.lower()]
    except:
        pass
    log_update_user["username"] = operation_username
    log_update_user["time"]= time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
    if 'username' in request.session and 'password' in request.session:
        try:
            if request.method == 'GET':
                return render(request, 'orgUserEdit.html')
            elif request.method == 'POST':
                try:
                    language = request.session['language']
                    organization = request.POST.get('organization')
                    company = request.POST.get('company')
                    account = request.POST.get('account')
                    #修改前日志
                    user = AuthMessage.objects.get(username=account)
                    log_update_user["original info"] = {"organization": user.department.company.organization.organization, "company": user.department.company.company, "username": account, "nickname": user.nickname, "email": user.email, "mobile": user.mobile, "phone": user.phone,
                                                        "loation": user.location, "ip": user.ip, "department": user.department.department_name}
                    name = request.POST.get('name')
                    email = request.POST.get('email')
                    mobile = request.POST.get('mobile')
                    phone = request.POST.get('phone')
                    location = request.POST.get('location')
                    department = request.POST.get('department')
                    #departmentcode = request.POST.get('departmentCode')
                    ip = request.POST.get('ip')
                    com = Department.objects.filter(department_code=department)[0]
                    nowtime = datetime.datetime.now()
                    import socket
                    myname = socket.getfqdn(socket.gethostname())
                    AuthMessage.objects.filter(username=account).update(username=account, email=email, ip=ip,
                                                              mobile=mobile, phone=phone, location=location,
                                                               update_date=nowtime, department=department, nickname=name)
                    log_update_user["current info"] = {"organization": organization, "company": company, "username": account, "nickname": name, "email": email, "mobile": mobile, "phone": phone,
                                                       "loation": location, "ip": ip, "department": com.department_name}
                    log_user_json = "601>" + json.dumps(log_update_user)
                    logger.info(log_user_json)
                    return JsonResponse({"result":"success"})
                except Exception as e:
                    msg = gettext("Update user information failed!")
                    return JsonResponse({"result":"failed","msg":msg})
        except Exception as e:
            exstr = str(traceback.format_exc())
            return JsonResponse({"result": "failed", "message": exstr})
    else:
        return render(request, "login.html")

#更新用户权限
@csrf_exempt
def updateUserPermission(request):
    operation_username = request.session["username"]
    log_creat_user = {}
    log_creat_user["action"] = "user permission"
    try:
        log_creat_user["computer name"] = pc_names[operation_username.lower()]
    except:
        pass
    log_creat_user["username"] = operation_username
    log_creat_user["time"] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
    if 'username' in request.session and 'password' in request.session:
        try:
            if request.method == 'GET':
                return render(request, 'orgUserPermission.html')
            elif request.method == 'POST':
                try:
                    language = request.session['language']
                    account = request.POST.get('account')
                    log_creat_user["account"] = account
                    functions = request.POST.getlist('function[]')
                    menus = request.POST.getlist('menu[]')
                    panels = request.POST.getlist('panel[]')
                    folders = request.POST.getlist('folder[]')
                    commanders = request.POST.getlist('commander[]')
                    nowtime = datetime.datetime.now()
                    user = AuthMessage.objects.get(username=account)
                    old_perms = user.user_permissions.values()
                    log_creat_user["orginal permissions"] = str(list(old_perms))
                    user.groups.clear()
                    user.user_permissions.clear()
                    for function in functions:
                        try:
                            function = function.replace("Draw_Process.views_","")
                            newperm = Permission.objects.get(name=function)
                            user.user_permissions.add(newperm)
                        except:
                            continue
                    for menu in menus:
                        try:
                            menu = menu.replace("Draw_Process.views_","")
                            newperm = Permission.objects.get(name=menu)
                            user.user_permissions.add(newperm)
                        except:
                            continue
                    for panel in panels:
                        try:
                            panel = panel.replace("Draw_Process.views_","")
                            newperm = Permission.objects.get(name=panel)
                            user.user_permissions.add(newperm)
                        except Exception:
                            continue
                    for folder in folders:
                        try:
                            folder_name = folder.replace("Draw_Process.views_folder_","")
                            newperm = Permission.objects.get(name=folder_name)
                            user.user_permissions.add(newperm)
                        except Exception:
                            continue
                    for commander in commanders:
                        try:
                            commander_name = commander.replace("Draw_Process.views_commander_", "")
                            newperm = Permission.objects.get(name=commander_name)
                            user.user_permissions.add(newperm)
                        except Exception:
                            continue
                    new_perms = user.user_permissions.values()
                    log_creat_user["current permissions"] = str(list(new_perms))
                    log_user_json = "603>" + json.dumps(log_creat_user)
                    logger.info(log_user_json)
                    user.groups.clear()
                    msg = gettext("Update successfully!")
                    return JsonResponse({"message": msg})
                except Exception:
                    exstr = str(traceback.format_exc())
                    return JsonResponse({"result": "failed", "message": exstr})
        except Exception as e:
            exstr = str(traceback.format_exc())
            return JsonResponse({"result": "failed", "message": exstr})
    else:
        return render(request, "login.html")

#更新用户局部权限
@csrf_exempt
def updateUserSomePermission(request):
    if 'username' in request.session and 'password' in request.session:
        try:
            if request.method == 'GET':
                return render(request, 'orgUserPermission.html')
            elif request.method == 'POST':
                try:
                    language = request.session['language']
                    account = request.POST.get('account')
                    type = request.POST.get('type')
                    folders = request.POST.getlist('folder[]')
                    commanders = request.POST.getlist('commander[]')
                    nowtime = datetime.datetime.now()
                    user = AuthMessage.objects.get(username=account)
                    old_perms = User.get_all_permissions(user)

                    for old_perm in old_perms:
                        try:
                            if type == "folder" and "views_folder_" in old_perm:
                                folder_name = old_perm.replace("Draw_Process.views_folder_", "")
                                old_permission = Permission.objects.get(name=folder_name)
                                user.user_permissions.remove(old_permission)
                            elif type == "commander" and "views_commander_" in old_perm:
                                commander_name = old_perm.replace("Draw_Process.views_commander_", "")
                                old_permission = Permission.objects.get(name=commander_name)
                                user.user_permissions.remove(old_permission)
                        except Exception as e:
                            pass
                    for folder in folders:
                        try:
                            folder_name = folder.replace("Draw_Process.views_folder_","")
                            newperm = Permission.objects.get(name=folder_name)
                            user.user_permissions.add(newperm)
                        except Exception:
                            continue
                    for commander in commanders:
                        try:
                            commander_name = commander.replace("Draw_Process.views_commander_", "")
                            newperm = Permission.objects.get(name=commander_name)
                            user.user_permissions.add(newperm)
                        except Exception:
                            continue
                    msg = gettext("Update successfully!")
                    return JsonResponse({"message": msg})
                except Exception:
                    exstr = str(traceback.format_exc())
                    return JsonResponse({"result": "failed", "message": exstr})
        except Exception as e:
            exstr = str(traceback.format_exc())
            return JsonResponse({"result": "failed", "message": exstr})
    else:
        return render(request, "login.html")

@csrf_exempt
def updateuser(request):
    if 'username' in request.session and 'password' in request.session:
        userID = request.session['username']
        if request.method == 'GET':
            return render(request, 'information.html')
        elif request.method == 'POST':
            try:
                language = request.session['language']
                nickName = request.POST.get('userName')
                email = request.POST.get('email')
                mobile = request.POST.get('mobile')
                phone = request.POST.get('phone')
                url = request.POST.get('url')
                ip = request.POST.get('ip')
                taxpwd = request.POST.get('taxpwd')
                sign = request.POST.get('sign')
                sex = request.POST.get('sex')
                try:
                    img_base64 = request.POST.get('imageurl')
                    if "static/images/user/user" not in img_base64:
                        image_base64 = img_base64.replace("data:image/jpeg;base64,", "")
                        image_base64 = image_base64.replace("data:image/png;base64,", "")
                        image_base64 = image_base64.replace("data:image/jpg;base64,", "")
                        image_base64 = image_base64.replace("data:image/gif;base64,", "")
                        imgdata = base64.b64decode(image_base64)
                        path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                        imageurl = path + "\\static\\images\\user\\" + userID + ".jpg"
                        file = open(imageurl, 'wb')
                        file.write(imgdata)
                        file.close()
                        imageurl = "../static/images/user/" + userID + ".jpg"
                    else:
                        if "user1.jpg" in img_base64:
                            imageurl = "../static/images/user/user1.jpg"
                        else:
                            imageurl = "../static/images/user/user2.jpg"
                except:
                    imageurl = request.POST.get('imageurl')
                AuthMessage.objects.filter(username=userID).update(nickname=nickName,fixed_ip=ip,email=email,mobile=mobile,phone=phone,signature=sign,image_url=imageurl,sex=sex)
                msg = gettext("Personnel information updated successfully!")
                return JsonResponse({"result": "success", "message": msg})
            except Exception:
                exstr = str(traceback.format_exc())
                return JsonResponse({"result": "failed", "message": exstr})

@csrf_exempt
def upload_user(request):
    if request.is_ajax():
        path = request.POST.get('path')
        from Draw_Process.pyfile import uploaduser
        upload = uploaduser.upload()
        upload.excel2csv(path)
        msg = upload.insert2mysql()
        try:
            errormsg = msg['error']
            return JsonResponse({"message": str(errormsg), "type": "error"})
        except:
            return JsonResponse({"message": msg,"type":"success"})



@csrf_exempt
def check_userId(request):
    userName = request.GET['loginCode']
    userCheck = AuthMessage.objects.all().filter(username=userName)
    userName_list = []
    userName_list = serializers.serialize('json', userCheck)
    userName_array = json.loads(userName_list)
    length = len(userName_array)
    if length == 0:
        return HttpResponse("true")
    else:
        return HttpResponse("false")


@csrf_exempt
def treeselect(request):
    if 'username' in request.session and 'password' in request.session:
        username = request.session['username']
        return render(request,'treeselect.html')
    else:
        return render(request, "login.html")


#更改用户有效期
@csrf_exempt
def editUserLicense(request):
    if 'username' in request.session and 'password' in request.session:
        try:
            username = request.session['username']
            log_creat_user = {}
            log_creat_user["action"] = "set user license date"
            try:
                log_creat_user["computer name"] = pc_names[username.lower()]
            except:
                pass
            log_creat_user["username"] = username
            log_creat_user["time"] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
            language = request.session['language']
            userid = request.POST.get('loginCode')
            enddate = request.POST.get('endDate')
            log_creat_user["end date"] = enddate
            log_creat_user["account"] = userid
            log_user_json = "604>" + json.dumps(log_creat_user)
            logger.info(log_user_json)
            AuthMessage.objects.filter(username=userid).update(licence_date=enddate)
            msg = gettext("Edit user license date successfully!")
            return JsonResponse({"result":"true","message":msg})
        except Exception as e:
            msg = gettext("Edit user license date failed!")
            return JsonResponse({"result": "false", "message": msg})
    else:
        return render(request, "login.html")


#更改角色有效期
@csrf_exempt
def editRoleLicense(request):
    if 'username' in request.session and 'password' in request.session:
        try:
            username = request.session['username']
            log_creat_user = {}
            log_creat_user["action"] = "set role license date"
            try:
                log_creat_user["computer name"] = pc_names[username.lower()]
            except:
                pass
            log_creat_user["name"] = username
            log_creat_user["time"] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
            language = request.session['language']
            roleCode = request.POST.get('roleCode')
            enddate = request.POST.get('endDate')
            AuthMessage.objects.filter(groups__name=roleCode).update(licence_date=enddate)
            log_creat_user["date"] = enddate
            log_user_json = "705>" + json.dumps(log_creat_user)
            logger.info(log_user_json)
            msg = gettext("Edit role license date successfully!")
            return JsonResponse({"result":"true","message": msg})
        except Exception as e:
            msg = gettext("Edit role license date failed!")
            return JsonResponse({"result": "false", "message": msg})
    else:
        return render(request, "login.html")