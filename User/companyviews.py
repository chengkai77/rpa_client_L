import os
import base64
import time

from django.shortcuts import render
from django.http import JsonResponse

from django.views.decorators.csrf import csrf_exempt
import datetime
from django.utils.translation import gettext
from Draw_Process.models import Company
from Python_Platform import settings
from django.contrib.auth.models import Permission
from User import  userutils
import json
from django.core import serializers
from Draw_Process.models import Organization
import logging
from Client.websocketviews import pc_names

logger = logging.getLogger('log')


@csrf_exempt
def companyAdd(request):
    if 'username' in request.session and 'password' in request.session:
        username = request.session['username']
        language = request.session['language']
        auth = 'Draw_Process.views_panel_company_list_menu_search_all_organizations'
        json = userutils.organizationAuth(username, auth, language)
        return render(request, 'companyAdd.html', json)
    else:
        return render(request, "login.html")

@csrf_exempt
def updateCompany(request):
    if 'username' in request.session and 'password' in request.session:
        username = request.session['username']
        log_creat_user = {}
        log_creat_user["action"] = "update company"
        try:
            log_creat_user["computer name"] = pc_names[username.lower()]
        except:
            pass
        log_creat_user["username"] = username
        log_creat_user["time"] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
        company = request.POST.get('company')
        remarks = request.POST.get('remarks')
        old_info = list(Company.objects.filter(company=company).values("remarks"))[0]["remarks"]
        log_creat_user["original remarks"] = old_info
        log_creat_user["current remarks"] = remarks
        log_user_json = "901>" + json.dumps(log_creat_user)
        logger.info(log_user_json)
        try:
            Company.objects.filter(company=company).update(remarks=remarks)
            result = {"result":"success"}
        except:
            result = {"result":"Update remark failed!"}
        return JsonResponse(result)
    else:
        return render(request, "login.html")


@csrf_exempt
def changeCompanyStatus(request):
    if 'username' in request.session and 'password' in request.session:
        username = request.session['username']
        language = request.session['language']
        company = request.POST.get('company')
        log_creat_user = {}
        log_creat_user["action"] = "active/inactive company"
        try:
            log_creat_user["computer name"] = pc_names[username.lower()]
        except:
            pass
        log_creat_user["username"] = username
        log_creat_user["time"] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
        try:
            company_tupe = Company.objects.all().filter(company=company).values('status')
            status = int(company_tupe[0]['status'])
            if status == 0:
                status = 1
                action = "active"
            else:
                status = 0
                action = "inactive"
            log_creat_user["status"] = action
            Company.objects.filter(company=company).update(status=status)
            log_user_json = "902>" + json.dumps(log_creat_user)
            logger.info(log_user_json)
            result = {"result":"success"}
        except:
            msg = gettext("Change company status failed!")
            result = {"result":msg}
        return JsonResponse(result)
    else:
        return render(request, "login.html")


@csrf_exempt
def deleteCompany(request):
    if 'username' in request.session and 'password' in request.session:
        username = request.session['username']
        log_creat_user = {}
        log_creat_user["action"] = "delete company"
        try:
            log_creat_user["computer name"] = pc_names[username.lower()]
        except:
            pass
        log_creat_user["username"] = username
        log_creat_user["time"] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
        language = request.session['language']
        company = request.POST.get('company')
        log_creat_user["company"] = company
        try:
           # organization = Company.objects.filter(company=company).values('organization')[0]['organization']
            organization = Organization.objects.filter(company__company=company)[0]

            folder = organization.organization.replace(" ", "") + "\\" + company.replace(" ", "")
            foldersub = organization.organization.replace(" ", "") + "\\" + company.replace(" ", "")+"\\"
            folder1 = settings.File_Root + "\\Draw_Process\\pyfile\\public\\" + organization.organization.replace(" ", "") + "\\" + company.replace(" ","")
            folder2 = settings.File_Root + "\\Draw_Process\\pyfile\\release\\" + organization.organization.replace(" ", "") + "\\" + company.replace(" ","")
            if os.path.exists(folder1):
                userutils.deletePath(folder1)
            if os.path.exists(folder2):
                userutils.deletePath(folder2)

            Permission.objects.filter(name=folder).delete() #
            Permission.objects.filter(name__startswith=foldersub).delete()  # 删除公司下所有的权限
            Company.objects.filter(company=company).delete()
            log_user_json = "903>" + json.dumps(log_creat_user)
            logger.info(log_user_json)
            '''deleteDepartment = userutils.deleteCompanyReleatedDepartment(company)'''
            result = {"result": "success"}
            '''if deleteDepartment == "success" or deleteDepartment == None:
                result = {"result":"success"}
            else:
                msg = gettext("Delete related departments failed!")
                result = {"result": msg}'''
        except Exception:
            msg = gettext("Delete company failed!")
            result = {"result":msg}
        return JsonResponse(result)
    else:
        return render(request, "login.html")

@csrf_exempt
def checkCompany(request):
    if 'username' in request.session and 'password' in request.session:
        try:
            username = request.session['username']
            language = request.session['language']
            company = request.POST.get("company")
            companies = Company.objects.filter(company=company).values('company')
            if len(companies) > 0:
                msg = gettext("This company already exists!")
                return JsonResponse({"result": "exist","msg": msg})
            else:
                return JsonResponse({"result": gettext("not exist")})
        except:
            return JsonResponse({"result": gettext("not exist")})
    else:
        return render(request, "login.html")


@csrf_exempt
def createCompany(request):
    if 'username' in request.session and 'password' in request.session:
        try:
            username = request.session['username']
            log_creat_user = {}
            log_creat_user["action"] = "create company"
            try:
                log_creat_user["computer name"] = pc_names[username.lower()]
            except:
                pass
            log_creat_user["username"] = username
            log_creat_user["time"] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
            language = request.session['language']
            organization = request.POST.get("organization")
            Organizationobj= Organization.objects.filter(organization=organization)[0]

            company = request.POST.get("company")
            remarks = request.POST.get("remarks")
            now_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            companies = Company.objects.filter(company=company).values('company')
            info = str(request.POST)
            index = info.find("{")
            log_creat_user["info"]= info[index::].replace(">","")
            if len(companies) > 0:
                msg = gettext("This company already exists!")
                return JsonResponse({"result": "failed", "msg": msg})
            else:
                folder1 = settings.File_Root + "\\Draw_Process\\pyfile\\public\\" + organization.replace(" ","") + "\\" + company.replace(" ","")
                folder2 =settings.File_Root + "\\Draw_Process\\pyfile\\release\\" + organization.replace(" ","") + "\\" + company.replace(" ", "")
                if os.path.exists(folder1):
                    pass
                else:
                    os.mkdir(folder1)
                if os.path.exists(folder2):
                    pass
                else:
                    os.mkdir(folder2)
                name = organization.replace(" ","") + "\\" + company.replace(" ","")
                codeName = "views_folder_" + organization.replace(" ","") + "\\" + company.replace(" ","")

                Company.objects.create(company=company,status=1,remarks=remarks,create_on=now_time,create_by=username,organization=Organizationobj)
                Permission.objects.create(name=name, content_type_id=18, codename=codeName)
                log_user_json = "900>" + json.dumps(log_creat_user)
                logger.info(log_user_json)
                return JsonResponse({"result": "success"})
        except Exception as e:
            logger.error('创建公司异常！----'+ str(e))
            msg = gettext("Create company failed!")
            return JsonResponse({"result": "failed","msg":str(e)})
    else:
        return render(request, "login.html")

@csrf_exempt
def orgCompany(request):
    if 'username' in request.session and 'password' in request.session:
        username = request.session['username']
        language = request.session['language']
        auth = "Draw_Process.views_panel_company_list_menu_search_all_organizations"
        json = userutils.organizationAuth(username, auth, language)
        return render(request,'orgCompany.html',json)
    else:
        return render(request, "login.html")


@csrf_exempt
def orgCompanyList(request):
    if 'username' in request.session and 'password' in request.session:
        username = request.session['username']
        if request.method == 'POST':
            page_No = request.POST.get("pageNo")
            page_Size = request.POST.get("pageSize")
            orderBy = request.POST.get("orderBy")
            # 筛选条件
            organization = request.POST.get("organization")
            company = request.POST.get("company")
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
            auth = "Draw_Process.views_panel_company_list_menu_search_all_organizations"
            user_organization = userutils.getOrganization(username, auth)
            if orderBy == "":
                if user_organization == "":
                    #正向查询组织
                    auth_tupe = Company.objects.all().filter(organization__organization__icontains=organization,company__icontains=company)
                else:
                    # 正向查询组织
                    auth_tupe = Company.objects.all().filter(organization__organization=user_organization, company__icontains=company)
            else:
                if user_organization == "": #正向查询组织
                    auth_tupe = Company.objects.all().filter(organization__organization__icontains=organization, company__icontains=company).order_by(order_condition)
                else: #正向查询组织
                    auth_tupe = Company.objects.all().filter(organization__organization=user_organization, company__icontains=company).order_by(order_condition)
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
                auth_json["organization"] = Organization.objects.get(pk= field['organization']).organization
                auth_json["company"] = field['company']
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
def companySelect(request):
    if request.method == 'POST':
        organization = request.POST.get("organization")
        if organization == "" or organization == None:
            company_list = Company.objects.distinct().filter(status="1").values('company')
        else:
            company_list = Company.objects.distinct().filter(organization__organization=organization,status="1").values('company')
        company_array = []
        for i in range(len(company_list)):
            company_json = {}
            company_json["name"] = company_list[i]['company']
            company_array.append(company_json)
        return JsonResponse({"list":company_array})