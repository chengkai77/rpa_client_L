import os
import base64
import time

from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.contrib.auth.models import Group
from django.contrib.auth.models import Permission
from django.views.decorators.csrf import csrf_exempt
import datetime
import logging
import json
from django.core import serializers
from django.utils.translation import gettext
import traceback
from Draw_Process.models import SysRole
from Draw_Process.models import Rolelist
from django.contrib.auth.models import Permission
from Draw_Process.models import Department
from Draw_Process.models import AuthMessage
from Draw_Process.models import Organization
from Draw_Process.models import Company
from Draw_Process.models import SysArea
from User import  userutils
from Client.websocketviews import pc_names

logger = logging.getLogger('log')
@csrf_exempt
def roleAddUser(request):
    if 'username' in request.session and 'password' in request.session:
        username = request.session['username']
        return render(request,'orgRoleAddUser.html')
    else:
        return render(request, "login.html")
#角色增加入口
@csrf_exempt
def orgroleadd(request):
    if 'username' in request.session and 'password' in request.session:
        username = request.session['username']
        language = request.session['language']
        auth = 'Draw_Process.views_panel_role_list_menu_search_all_organizations'
        json = userutils.organizationAuth(username,auth,language)
        return render(request, 'orgRoleAdd.html', json)
    else:
        return render(request, "login.html")
#创建角色
@csrf_exempt
def createRole(request):
    if 'username' in request.session and 'password' in request.session:
        try:
            if request.method == 'POST':
                try:
                    username = request.session['username']
                    log_creat_user = {}
                    log_creat_user["action"] = "create role"
                    try:
                        log_creat_user["computer name"] = pc_names[username.lower()]
                    except:
                        pass
                    log_creat_user["username"] = username
                    log_creat_user["time"] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
                    language = request.session['language']
                    organization = request.POST.get('organization')
                    roleCode = request.POST.get('roleCode')
                    roleName = request.POST.get('roleName')
                    sort = int(request.POST.get('sort'))
                    userType = request.POST.get('userType')
                    isSys = request.POST.get('isSys')
                    roleType = request.POST.get('roleType')
                    remarks = request.POST.get('remarks')
                    functions = request.POST.getlist('function[]')
                    menus = request.POST.getlist('menu[]')
                    panels = request.POST.getlist('panel[]')
                    folders = request.POST.getlist('folder[]')
                    commanders = request.POST.getlist('commander[]')
                    nowtime = datetime.datetime.now()
                    Group.objects.create(name=roleCode)
                    SysRole.objects.create(organization=organization,role_code=roleCode,role_name=roleName,role_type=roleType,role_sort=sort,is_sys=isSys,user_type=userType,status="1",create_by=username,create_on=nowtime,remarks=remarks)
                    mygroup = Group.objects.get(name=roleCode)
                    code = str(request.POST)
                    index = code.find("{")
                    log_creat_user["info"] = code[index::].replace(">","")
                    log_user_json = "700>"+json.dumps(log_creat_user)
                    logger.info(log_user_json)
                    for function in functions:
                        try:
                            function = function.replace("Draw_Process.views_","")
                            newperm = Permission.objects.get(name=function)
                            mygroup.permissions.add(newperm)
                        except:
                            continue
                    for menu in menus:
                        try:
                            menu = menu.replace("Draw_Process.views_","")
                            newperm = Permission.objects.get(name=menu)
                            mygroup.permissions.add(newperm)
                        except:
                            continue
                    for panel in panels:
                        try:
                            panel = panel.replace("Draw_Process.views_","")
                            newperm = Permission.objects.get(name=panel)
                            mygroup.permissions.add(newperm)
                        except:
                            continue
                    for folder in folders:
                        try:
                            folder = folder.replace("Draw_Process.views_","")
                            newperm = Permission.objects.get(name=panel)
                            mygroup.permissions.add(newperm)
                        except:
                            continue
                    for commander in commanders:
                        try:
                            commander_name = commander.replace("Draw_Process.views_commander_", "")
                            newperm = Permission.objects.get(name=commander_name)
                            mygroup.permissions.add(newperm)
                        except Exception:
                            continue
                    msg = gettext("Create role successfully!")
                    return JsonResponse({"result": "success", "message": msg})
                except Exception:
                    exstr = str(traceback.format_exc())
                    return JsonResponse({"result": "error", "message": exstr})
        except Exception as e:
            exstr = str(traceback.format_exc())
            return JsonResponse({"result": "error", "message": exstr})
    else:
        return render(request, "login.html")
@csrf_exempt
def roleDelete(request):
    if 'username' in request.session and 'password' in request.session:
        try:
            username = request.session['username']
            log_creat_user = {}
            log_creat_user["action"] = "delete role"
            try:
                log_creat_user["computer name"] = pc_names[username.lower()]
            except:
                pass
            log_creat_user["username"] = username
            log_creat_user["time"] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
            language = request.session['language']
            roleCode = request.POST.get('roleCode')
            name = str(SysRole.objects.filter(role_code=roleCode).values("role_name"))
            index = name.find("[")
            log_creat_user["role code"] = roleCode
            log_user_json = "703>" + json.dumps(log_creat_user)
            logger.info(log_user_json)
            SysRole.objects.filter(role_code=roleCode).delete()
            Group.objects.filter(name=roleCode).delete()
            msg = gettext("Delete role successfully!")
            return JsonResponse({"result":"true","message":msg})
        except Exception as e:
            msg = gettext("Delete role failed!")
            return JsonResponse({"result": "false", "message": msg})
    else:
        return render(request, "login.html")
@csrf_exempt
def updateRole(request):
    if 'username' in request.session and 'password' in request.session:
        try:
            if request.method == 'POST':
                try:
                    username = request.session['username']
                    log_creat_user = {}
                    log_creat_user["action"] = "update role"
                    try:
                        log_creat_user["computer name"] = pc_names[username.lower()]
                    except:
                        pass
                    log_creat_user["username"] = username
                    log_creat_user["time"] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
                    language = request.session['language']
                    roleCode = request.POST.get('roleCode')
                    roleName = request.POST.get('roleName')
                    sort = int(request.POST.get('sort'))
                    userType = request.POST.get('userType')
                    isSys = request.POST.get('isSys')
                    roleType = request.POST.get('roleType')
                    remarks = request.POST.get('remarks')
                    nowtime = datetime.datetime.now()
                    role_info = SysRole.objects.filter(role_code=roleCode).values()[0]
                    role_dict_2_str = "{" + "'roleCode': [{}], 'roleName': [{}], 'sort': [{}], 'userType': [{}], 'isSys': [{}], 'roleType': [{}], 'remarks': [{}]".format(role_info["role_code"],role_info["role_name"],role_info["role_sort"],role_info["user_type"],role_info["is_sys"],role_info["role_type"],role_info["remarks"]) + "}"
                    log_creat_user["original info"] = role_dict_2_str
                    SysRole.objects.filter(role_code=roleCode).update(role_name=roleName,role_type=roleType,role_sort=sort,is_sys=isSys,user_type=userType,status="1",update_by=username,update_on=nowtime,remarks=remarks)
                    msg = gettext("Update successfully!")
                    code = str(request.POST)
                    index = code.find("{")
                    log_creat_user["current info"] = code[index::].replace(">","")
                    log_user_json = "701>"+json.dumps(log_creat_user)
                    logger.info(log_user_json)
                    return JsonResponse({"message": msg})
                except Exception:
                    exstr = str(traceback.format_exc())
                    return JsonResponse({"result": "failed", "message": exstr})
        except Exception as e:
            exstr = str(traceback.format_exc())
            return JsonResponse({"result": "failed", "message": exstr})
    else:
        return render(request, "login.html")





#选择角色
@csrf_exempt
def role_selection(request):
    try:
        if request.method == 'POST':
            Role_Selection = Rolelist.objects.all()
            Role_list = []
            Roles = serializers.serialize('json', Role_Selection)
            Role_array = json.loads(Roles)
            for i in range(len(Role_array)):
                Role_json = {}
                Role_json = Role_array[i]['fields']
                Role_list.append(Role_json)
            return JsonResponse({"list":Role_list})
    except:
        return JsonResponse({"list":""})
#编辑角色入口
@csrf_exempt
def orgRoleEdit(request):
    if 'username' in request.session and 'password' in request.session:
        username = request.session['username']
        roleCode = request.GET['roleCode']
        role_msg = SysRole.objects.all().filter(role_code=roleCode)
        role_msg_list = []
        role_msg_list = serializers.serialize('json', role_msg)
        role_msg_array = json.loads(role_msg_list)
        field = role_msg_array[0]['fields']
        roleName = field['role_name']
        sort = field['role_sort']
        userType = field['user_type']
        isSys = field['is_sys']
        roleType = field['role_type']
        remarks = field['remarks']
        if remarks is None:
            remarks = ""
        auth_json = {"roleCode":roleCode,"roleName":roleName,"sort":sort,"userType":userType,"isSys":isSys,"roleType":roleType,"remarks":remarks}
        return render(request,'orgRoleEdit.html',auth_json)
    else:
        return render(request, "login.html")

#更新角色的权限
@csrf_exempt
def updateRolePermission(request):
    if 'username' in request.session and 'password' in request.session:
        try:
            if request.method == 'POST':
                try:
                    username = request.session['username']
                    log_creat_user = {}
                    log_creat_user["action"] = "role permission"
                    try:
                        log_creat_user["computer name"] = pc_names[username.lower()]
                    except:
                        pass
                    log_creat_user["username"] = username
                    log_creat_user["time"] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
                    language = request.session['language']
                    roleCode = request.POST.get('roleCode')
                    log_creat_user["role code"] = roleCode
                    functions = request.POST.getlist('function[]')
                    menus = request.POST.getlist('menu[]')
                    panels = request.POST.getlist('panel[]')
                    folders = request.POST.getlist('folder[]')
                    commanders = request.POST.getlist('commander[]')
                    myGroup = Group.objects.get(name=roleCode)
                    old_perms = myGroup.permissions.values()
                    log_creat_user["orginal permissions"] = str(list(old_perms))
                    #log_creat_user["old_info"] = old_info[index1::]
                    myGroup.permissions.clear()
                    for function in functions:
                        try:
                            function = function.replace("Draw_Process.views_","")
                            newperm = Permission.objects.get(name=function)
                            myGroup.permissions.add(newperm)
                        except:
                            continue
                    for menu in menus:
                        try:
                            menu = menu.replace("Draw_Process.views_","")
                            newperm = Permission.objects.get(name=menu)
                            myGroup.permissions.add(newperm)
                        except:
                            continue
                    for panel in panels:
                        try:
                            panel = panel.replace("Draw_Process.views_","")
                            newperm = Permission.objects.get(name=panel)
                            myGroup.permissions.add(newperm)
                        except:
                            continue
                    for folder in folders:
                        try:
                            folder_name = folder.replace("Draw_Process.views_folder_","")
                            newperm = Permission.objects.get(name=folder_name)
                            myGroup.permissions.add(newperm)
                        except Exception:
                            continue
                    for commander in commanders:
                        try:
                            commander_name = commander.replace("Draw_Process.views_commander_", "")
                            newperm = Permission.objects.get(name=commander_name)
                            myGroup.permissions.add(newperm)
                        except Exception:
                            continue
                    msg = gettext("Update successfully!")
                    new_perms = myGroup.permissions.values()
                    log_creat_user["current permissions"] = str(list(new_perms))
                    log_user_json = "702>"+json.dumps(log_creat_user)
                    logger.info(log_user_json)
                    return JsonResponse({"message": msg})
                except Exception:
                    print(Exception)
                    exstr = str(traceback.format_exc())
                    return JsonResponse({"result": "failed", "message": exstr})
        except Exception as e:
            exstr = str(traceback.format_exc())
            return JsonResponse({"result": "failed", "message": exstr})
    else:
        return render(request, "login.html")

#更新角色部分模块的权限
@csrf_exempt
def updateRoleSomePermission(request):
    if 'username' in request.session and 'password' in request.session:
        try:
            if request.method == 'POST':
                try:
                    language = request.session['language']
                    roleCode = request.POST.get('roleCode')
                    type = request.POST.get('type')
                    folders = request.POST.getlist('folder[]')
                    commanders = request.POST.getlist('commander[]')
                    myGroup = Group.objects.get(name=roleCode)
                    old_perms = myGroup.permissions.all()
                    old_perms = list(old_perms)
                    for old_perm in old_perms:
                        try:
                            if type == "folder" and "views_folder_" in old_perm.codename:
                                folder_name = old_perm.replace("Draw_Process.views_folder_", "")
                                old_permission = Permission.objects.get(name=folder_name)
                                myGroup.permissions.remove(old_permission)
                            elif type == "commander" and "views_commander_" in old_perm.codename:
                                commander_name = old_perm.replace("Draw_Process.views_commander_", "")
                                old_permission = Permission.objects.get(name=commander_name)
                                myGroup.permissions.remove(old_permission)
                        except Exception as e:
                            pass
                    for folder in folders:
                        try:
                            folder_name = folder.replace("Draw_Process.views_folder_","")
                            newperm = Permission.objects.get(name=folder_name)
                            myGroup.permissions.add(newperm)
                        except Exception:
                            continue
                    for commander in commanders:
                        try:
                            commander_name = commander.replace("Draw_Process.views_commander_", "")
                            newperm = Permission.objects.get(name=commander_name)
                            myGroup.permissions.add(newperm)
                        except Exception:
                            continue
                    msg = gettext("Update successfully!")
                    return JsonResponse({"message": msg})
                except Exception:
                    print(Exception)
                    exstr = str(traceback.format_exc())
                    return JsonResponse({"result": "failed", "message": exstr})
        except Exception as e:
            exstr = str(traceback.format_exc())
            return JsonResponse({"result": "failed", "message": exstr})
    else:
        return render(request, "login.html")

#编辑角色的权限入口
@csrf_exempt
def roleEditPermission(request):
    if 'username' in request.session and 'password' in request.session:
        username = request.session['username']
        roleCode = request.GET['roleCode']
        auth_msg = SysRole.objects.all().filter(role_code=roleCode)
        auth_msg_list = []
        auth_msg_list = serializers.serialize('json', auth_msg)
        auth_msg_array = json.loads(auth_msg_list)
        field = auth_msg_array[0]['fields']
        roleCode = field['role_code']
        roleName = field['role_name']
        auth_json = {"roleCode":roleCode,"roleName":roleName}
        return render(request,'orgRolePermission.html',auth_json)
    else:
        return render(request, "login.html")


#编辑角色的权限入口
@csrf_exempt
def roleEditPermission(request):
    if 'username' in request.session and 'password' in request.session:
        username = request.session['username']
        roleCode = request.GET['roleCode']
        auth_msg = SysRole.objects.all().filter(role_code=roleCode)
        auth_msg_list = []
        auth_msg_list = serializers.serialize('json', auth_msg)
        auth_msg_array = json.loads(auth_msg_list)
        field = auth_msg_array[0]['fields']
        roleCode = field['role_code']
        roleName = field['role_name']
        auth_json = {"roleCode":roleCode,"roleName":roleName}
        return render(request,'orgRolePermission.html',auth_json)
    else:
        return render(request, "login.html")

#编辑角色文件夹的权限入口
@csrf_exempt
def roleFolderPermission(request):
    if 'username' in request.session and 'password' in request.session:
        username = request.session['username']
        roleCode = request.GET['roleCode']
        auth_msg = SysRole.objects.all().filter(role_code=roleCode)
        auth_msg_list = []
        auth_msg_list = serializers.serialize('json', auth_msg)
        auth_msg_array = json.loads(auth_msg_list)
        field = auth_msg_array[0]['fields']
        roleCode = field['role_code']
        roleName = field['role_name']
        auth_json = {"roleCode":roleCode,"roleName":roleName}
        return render(request,'orgRoleFolderPermission.html',auth_json)
    else:
        return render(request, "login.html")

#编辑角色commander的权限入口
@csrf_exempt
def roleCommanderPermission(request):
    if 'username' in request.session and 'password' in request.session:
        username = request.session['username']
        roleCode = request.GET['roleCode']
        auth_msg = SysRole.objects.all().filter(role_code=roleCode)
        auth_msg_list = []
        auth_msg_list = serializers.serialize('json', auth_msg)
        auth_msg_array = json.loads(auth_msg_list)
        field = auth_msg_array[0]['fields']
        roleCode = field['role_code']
        roleName = field['role_name']
        auth_json = {"roleCode":roleCode,"roleName":roleName}
        return render(request,'orgRoleCommanderPermission.html',auth_json)
    else:
        return render(request, "login.html")

@csrf_exempt
def roleAssign(request):
    if 'username' in request.session and 'password' in request.session:
        username = request.session['username']
        roleCode = request.GET['roleCode']
        return render(request,'orgRoleAssign.html',{"roleCode":roleCode})
    else:
        return render(request, "login.html")





#禁用角色
@csrf_exempt
def changeRoleStatus(request):
    if 'username' in request.session and 'password' in request.session:
        username = request.session['username']
        language = request.session['language']
        roleCode = request.POST.get('roleCode')
        try:
            role_tupe = SysRole.objects.all().filter(role_code=roleCode).values('status')
            status = int(role_tupe[0]['status'])
            if status == 0:
                status = 1
            else:
                status = 0
            SysRole.objects.filter(role_code=roleCode).update(status=status)
            result = {"result":"success"}
        except:
            msg = gettext("Change role status failed!")
            result = {"result":"Change role status failed!"}
        return JsonResponse(result)
    else:
        return render(request, "login.html")

#角色增加用户
@csrf_exempt
def roleSaveUserAdd(request):
    if 'username' in request.session and 'password' in request.session:
        try:
            username = request.session['username']
            log_creat_user = {}
            log_creat_user["action"] = "assign users for role"
            try:
                log_creat_user["computer name"] = pc_names[username.lower()]
            except:
                pass
            log_creat_user["username"] = username
            log_creat_user["time"] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
            language = request.session['language']
            roleCode = request.POST.get('roleCode')
            cover = request.POST.get('cover')
            userList = request.POST.getlist('userList[]')
            myGroup = Group.objects.get(name=roleCode)
            user_list = []
            users = list(myGroup.user_set.all())
            for user in users:
                user_list.append(user.username)
            for userName in userList:
                if userName not in user_list:
                    user = AuthMessage.objects.get(username=userName)
                    if cover == '0':
                        user.groups.clear()
                        user.user_permissions.clear()
                    myGroup.user_set.add(user)
            log_creat_user["role code"] = roleCode
            log_creat_user["users"] = str(user_list)
            log_user_json = "704>" + json.dumps(log_creat_user)
            logger.info(log_user_json)
            msg = gettext("Select user successfully!")
            result = {"status":"success","msg":msg}
        except:
            msg = gettext("Select user failed!")
            result = {"status": "failed", "msg": msg}
        return JsonResponse(result)
    else:
        return render(request, "login.html")


#角色列表
@csrf_exempt
def roleList(request):
    if 'username' in request.session and 'password' in request.session:
        username = request.session['username']
        if request.method == 'POST':
            page_No = request.POST.get("pageNo")
            page_Size = request.POST.get("pageSize")
            orderBy = request.POST.get("orderBy")
            # 筛选条件
            organization = userutils.xstr(request.POST.get("organization"))
            roleCode = userutils.xstr(request.POST.get("roleCode"))
            roleName = userutils.xstr(request.POST.get("roleName"))
            systemUser = userutils.xstr(request.POST.get("isSys"))
            userType = userutils.xstr(request.POST.get("userType"))
            status = userutils.xstr(request.POST.get("status"))
            status_list = []
            systemUser_list = []
            if status == "" or status is None:
                status_list = ["1","0"]
            else:
                status_list.append(status)
            if systemUser == "" or systemUser is None:
                systemUser_list = ["1","0"]
            else:
                systemUser_list.append(systemUser)
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
            user = AuthMessage.objects.get(username=username)
            perms = User.get_all_permissions(user)
            if "Draw_Process.views_panel_role_list_menu_search_all_organizations" in perms:
                user_organization = ''
            else:
                try:
                    user_organization = AuthMessage.objects.filter(user=username).values('organization')[0]['organization']
                except:
                    user_organization = ''
            if orderBy == "":
                if user_organization == '':
                    auth_tupe = SysRole.objects.all().filter(organization__icontains=organization, role_code__icontains=roleCode, role_name__icontains=roleName,
                                                                 is_sys__in=systemUser_list, user_type__icontains=userType,
                                                                 status__in=status_list)
                else:
                    auth_tupe = SysRole.objects.all().filter(organization=user_organization, role_code__icontains=roleCode,
                                                             role_name__icontains=roleName,
                                                             is_sys__in=systemUser_list, user_type__icontains=userType,
                                                             status__in=status_list)
            else:
                if user_organization == '':
                    auth_tupe = SysRole.objects.all().filter(organization__icontains=organization, role_code__icontains=roleCode, role_name__icontains=roleName,
                                                                 is_sys__in=systemUser_list, user_type__icontains=userType,
                                                                 status__in=status_list).order_by(order_condition)
                else:
                    auth_tupe = SysRole.objects.all().filter(organization=user_organization, role_code__icontains=roleCode,
                                                             role_name__icontains=roleName,
                                                             is_sys__in=systemUser_list, user_type__icontains=userType,
                                                             status__in=status_list).order_by(order_condition)
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
                auth_json["organization"] = field['organization']
                auth_json["role_code"] = field['role_code']
                auth_json["role_name"] = field['role_name']
                auth_json["role_sort"] = field['role_sort']
                isSys = field['is_sys']
                if isSys == "1":
                    auth_json["is_sys"] = gettext("Yes")
                else:
                    auth_json["is_sys"] = gettext("No")
                auth_json["user_type"] = field['user_type']
                if request.session['language'] == "zh-hans":
                    if field['user_type'] == "employee":
                        auth_json["user_type"] = "员工"
                    if field['user_type'] == "member":
                        auth_json["user_type"] = "成员"
                    if field['user_type'] == "person":
                        auth_json["user_type"] = "人员"
                    if field['user_type'] == "person":
                        auth_json["user_type"] = "专家"
                update_on = field['update_on']
                if update_on is None:
                    update_on = ""
                update_on = update_on.replace("T"," ")
                auth_json["update_on"] = update_on
                auth_json["remarks"] = field['remarks']
                user_status = field['status']
                if user_status == "1":
                    auth_json["status"] = gettext("Normal")
                else:
                    auth_json["status"] = gettext("Block")
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

#角色下面的用户列表
@csrf_exempt
def roleAccountList(request):
    if 'username' in request.session and 'password' in request.session:
        username = request.session['username']
        if request.method == 'POST':
            roleCode = request.GET['roleCode']
            myGroup = Group.objects.get(name=roleCode)
            user_list = []
            users = list(myGroup.user_set.all())
            for user in users:
                user_list.append(user.username)
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
                try:
                    auth_tupe = AuthMessage.objects.all().filter(username__icontains=loginCode,
                                                                 nickname__icontains=userName,
                                                                 email__icontains=email, mobile__icontains=mobile,
                                                                 phone__icontains=phone).filter(username__in=user_list)
                except Exception as e:
                    sss= str(e)
                    info ="error "


            else:
                auth_tupe = AuthMessage.objects.all().filter(user__icontains=loginCode, name__icontains=userName,
                                                             email__icontains=email, mobile__icontains=mobile, phone__icontains=phone).filter(username__in=user_list).order_by(order_condition)
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
                auth_json["user"] =field['username']
                auth_json["userName"] = field['username']
                status = AuthMessage.objects.filter(username=field['username']).values('is_active')[0]['is_active']
                if status == True:
                    auth_json["status"] = gettext("Normal")
                else:
                    auth_json["status"] = gettext("Block")
                auth_json["name"] = field['nickname']
                location = field['location']
                try:
                    location = SysArea.objects.filter(area_code=location).values('area_name')[0]['area_name']
                except:
                    pass
                auth_json["location"] = location
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






#菜单界面进入角色入口
@csrf_exempt
def orgRole(request):
    if 'username' in request.session and 'password' in request.session:
        username = request.session['username']
        language = request.session['language']
        auth = "Draw_Process.views_panel_role_list_menu_search_all_organizations"
        json = userutils.organizationAuth(username, auth, language)
        return render(request,'roleList.html',json)
    else:
        return render(request, "login.html")
