import logging
import os
import base64
import time

from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import datetime
import json
from Draw_Process.models import AuthMessage
from django.core import serializers
from django.utils.translation import gettext
from Draw_Process.models import Organization
from Python_Platform import settings
from django.contrib.auth.models import Permission
from Client.websocketviews import pc_names
from User import  userutils

logger = logging.getLogger('log')
#进入到组织界面,入口
@csrf_exempt
def orgOrganization(request):
    if 'username' in request.session and 'password' in request.session:
        username = request.session['username']
        user = AuthMessage.objects.get(username=username)
        perms = AuthMessage.get_all_permissions(user)
        return render(request,'orgOrganization.html',{"perms":perms})
    else:
        return render(request, "login.html")
@csrf_exempt
def orgOrganizationList(request):
    if 'username' in request.session and 'password' in request.session:
        username = request.session['username']
        if request.method == 'POST':
            page_No = request.POST.get("pageNo")
            page_Size = request.POST.get("pageSize")
            orderBy = request.POST.get("orderBy")
            # 筛选条件
            organization = userutils.xstr(request.POST.get("organization"))
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
                auth_tupe = Organization.objects.all().filter(organization__icontains=organization)
            else:
                auth_tupe = Organization.objects.all().filter(organization__icontains=organization).order_by(order_condition)
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
                auth_json["status"] = field['status']
                auth_json["remarks"] = field['remarks']
                auth_json["create_on"] = field['create_on'].replace("T"," ")
                auth_json["create_by"] = field['create_by']
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
@csrf_exempt
def changeOrganizationStatus(request):
    if 'username' in request.session and 'password' in request.session:
        username = request.session['username']
        log_creat_user = {}
        log_creat_user["action"] = "active/inactive organization"
        try:
            log_creat_user["computer name"] = pc_names[username.lower()]
        except:
            pass
        log_creat_user["username"] = username
        log_creat_user["time"] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
        language = request.session['language']
        organization = request.POST.get('organization')
        log_creat_user["organization"] = organization
        try:
            organization_tupe = Organization.objects.all().filter(organization=organization).values('status')
            status = int(organization_tupe[0]['status'])
            if status == 0:
                status = 1
                action = "active"
            else:
                status = 0
                action = "inactive"
            log_creat_user["status"] = action
            log_user_json = "802>" + json.dumps(log_creat_user)
            logger.info(log_user_json)
            Organization.objects.filter(organization=organization).update(status=status)
            result = {"result":"success"}
        except:
            msg = gettext("Change organization status failed!")
            result = {"result":msg}
        return JsonResponse(result)
    else:
        return render(request, "login.html")

@csrf_exempt
def organizationAdd(request):
    if 'username' in request.session and 'password' in request.session:
        username = request.session['username']
        return render(request, 'organizationAdd.html')
    else:
        return render(request, "login.html")

@csrf_exempt
def checkOrganization(request):
    if 'username' in request.session and 'password' in request.session:
        try:
            username = request.session['username']
            language = request.session['language']
            organization = request.POST.get("organization")
            organizations = Organization.objects.filter(organization=organization).values('organization')
            if len(organizations) > 0:
                msg = gettext("This organization already exists!")
                return JsonResponse({"result": "exist","msg": msg})
            else:
                return JsonResponse({"result": gettext("not exist")})
        except:
            return JsonResponse({"result": gettext("not exist")})
    else:
        return render(request, "login.html")


@csrf_exempt
def createOrganization(request):
    if 'username' in request.session and 'password' in request.session:
        try:
            username = request.session['username']
            log_creat_user = {}
            log_creat_user["action"] = "create organization"
            try:
                log_creat_user["computer name"] = pc_names[username.lower()]
            except:
                pass
            log_creat_user["username"] = username
            log_creat_user["time"] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
            language = request.session['language']
            organization = request.POST.get("organization")
            remarks = request.POST.get("remarks")
            now_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            info = str(request.POST)
            index = info.find("{")
            log_creat_user["info"] = info[index::].replace(">","")
            log_user_json = "800>" + json.dumps(log_creat_user)
            logger.info(log_user_json)
            organizations = Organization.objects.filter(organization=organization).values('organization')
            if len(organizations) > 0:
                msg = gettext("This organization already exists!")
                return JsonResponse({"result": "failed", "msg": msg})
            else:
                folder1 = settings.File_Root + "\\Draw_Process\\pyfile\\public\\" + organization.replace(" ","")
                folder2 =settings.File_Root + "\\Draw_Process\\pyfile\\release\\" + organization.replace(" ", "")
                if os.path.exists(folder1):
                    pass
                else:
                    os.mkdir(folder1)
                if os.path.exists(folder2):
                    pass
                else:
                    os.mkdir(folder2)
                codeName = "views_folder_" + organization.replace(" ","")
                Permission.objects.create(name=organization.replace(" ",""),content_type_id=18,codename=codeName)
                Organization.objects.create(organization=organization,status=1,remarks=remarks,create_on=now_time,create_by=username)
                return JsonResponse({"result": "success"})
        except Exception as e:
            logger.error('创建组织失败'+ str(e))
            msg = gettext("Create Organization failed!")
            return JsonResponse({"result":"failed","msg":msg})
    else:
        return render(request, "login.html")


@csrf_exempt
def deleteOrganization(request):
    if 'username' in request.session and 'password' in request.session:
        username = request.session['username']
        log_creat_user = {}
        log_creat_user["action"] = "delete organization"
        try:
            log_creat_user["computer name"] = pc_names[username.lower()]
        except:
            pass
        log_creat_user["username"] = username
        log_creat_user["time"] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
        language = request.session['language']
        organization = request.POST.get('organization')
        log_creat_user["organization"] = organization
        try:
            folder = organization.replace(" ", "")
            foldersub = organization.replace(" ", "")+"\\"
            folder1 = settings.File_Root + "\\Draw_Process\\pyfile\\public\\" + organization.replace(" ", "")
            folder2 = settings.File_Root + "\\Draw_Process\\pyfile\\release\\" + organization.replace(" ", "")

            if os.path.exists(folder1):
                userutils.deletePath(folder1)
            if os.path.exists(folder2):
                userutils.deletePath(folder2)

            Permission.objects.filter(name=folder).delete()
            #aa = Permission.objects.filter(name__startswith=foldersub)
            Permission.objects.filter(name__startswith=foldersub).delete() #删除组织下所有的权限
            #Organizationobi = Organization.objects.filter(organization=organization)[0]
            #com = Organizationobi.company_set.all()

            Organization.objects.filter(organization=organization).delete()
            log_user_json = "803>" + json.dumps(log_creat_user)
            logger.info(log_user_json)
            result = {"result": "success"}
            '''elete_company = deleteOrganizationReleatedCompany(organization)
            if delete_company == "success" or delete_company == None:
                result = {"result": "success"}
            else:
                msg = gettext("Delete related companies of related departments failed!")
                result = {"result": msg}'''

        except Exception as  e:
            print('str(e):\t\t', str(e))
            msg = gettext("Delete organization failed!" + e + str(e))
            result = {"result":msg}
        return JsonResponse(result)
    else:
        return render(request, "login.html")


#更新组织描述
@csrf_exempt
def updateOrganization(request):
    if 'username' in request.session and 'password' in request.session:
        username = request.session['username']
        log_creat_user = {}
        log_creat_user["action"] = "update organization"
        try:
            log_creat_user["computer name"] = pc_names[username.lower()]
        except:
            pass
        log_creat_user["username"] = username
        log_creat_user["time"] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
        organization = request.POST.get('organization')
        remarks = request.POST.get('remarks')
        old_info = list(Organization.objects.filter(organization=organization).values("remarks"))[0]["remarks"]
        log_creat_user["original remarks"] = old_info
        log_creat_user["current remarks"] = remarks
        log_user_json = "801>" + json.dumps(log_creat_user)
        logger.info(log_user_json)
        try:
            Organization.objects.filter(organization=organization).update(remarks=remarks)
            result = {"result":"success"}
        except:
            result = {"result":"Update remark failed!"}
        return JsonResponse(result)
    else:
        return render(request, "login.html")

#选择公司
@csrf_exempt
def organizationSelect(request):
    if request.method == 'POST':
        organization_list = Organization.objects.distinct().filter(status="1").values('organization')
        organization_array = []
        for i in range(len(organization_list)):
            organization_json = {}
            organization_json["name"] = organization_list[i]['organization']
            organization_array.append(organization_json)
        return JsonResponse({"list":organization_array})