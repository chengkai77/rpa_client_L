import logging
import os
import time

from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import datetime
from django.utils.translation import gettext
from Draw_Process.models import Department
from django.db.models import Max
from Python_Platform import settings
from django.contrib.auth.models import Permission
from User import  userutils
import json
from django.core import serializers
from Draw_Process.models import Organization
from Draw_Process.models import  Company
from Client.websocketviews import pc_names

logger = logging.getLogger('log')

@csrf_exempt
def updateDepartment(request):
    if 'username' in request.session and 'password' in request.session:
        username = request.session['username']
        log_creat_user = {}
        log_creat_user["action"] = "update department"
        try:
            log_creat_user["computer name"] = pc_names[username.lower()]
        except:
            pass
        log_creat_user["username"] = username
        log_creat_user["time"] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
        departmentCode = request.POST.get('departmentCode')
        remarks = request.POST.get('remarks')
        old_remarks = list(Department.objects.filter(department_code=departmentCode).values("remarks"))[0]["remarks"]
        log_creat_user["old_info"] = old_remarks
        log_creat_user["new_info"] = remarks
        try:
            Department.objects.filter(department_code=departmentCode).update(remarks=remarks)
            log_user_json = "1001>" + json.dumps(log_creat_user)
            logger.info(log_user_json)
            result = {"result":"success"}
        except:
            result = {"result":"Update remark failed!"}
        return JsonResponse(result)
    else:
        return render(request, "login.html")


@csrf_exempt
def changeDepartmentStatus(request):
    if 'username' in request.session and 'password' in request.session:
        username = request.session['username']
        log_creat_user = {}
        log_creat_user["action"] = "active/inactive department"
        try:
            log_creat_user["computer name"] = pc_names[username.lower()]
        except:
            pass
        log_creat_user["username"] = username
        log_creat_user["time"] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
        language = request.session['language']
        departmentCode = request.POST.get('departmentCode')
        department_name = list(Department.objects.all().filter(department_code=departmentCode).values("department_name"))[0]["department_name"]
        log_creat_user["department"] = department_name
        try:
            department_tupe = Department.objects.all().filter(department_code=departmentCode).values('parent_codes','tree_leaf','status')
            treeLeaf = int(department_tupe[0]['tree_leaf'])
            status = int(department_tupe[0]['status'])
            if status == 0:
                status = 1
                action = "active"
            else:
                status = 0
                action = "inactive"
            log_creat_user["status"] = action
            Department.objects.filter(department_code=departmentCode).update(status=status)
            if treeLeaf == 0:
                parentCodes = department_tupe[0]['parent_codes'] + departmentCode + ','
                Department.objects.filter(parent_codes__icontains=parentCodes).update(status=status)
            log_user_json = "1002>" + json.dumps(log_creat_user)
            logger.info(log_user_json)
            result = {"result":"success"}
        except:
            msg = gettext("Change department status failed!")
            result = {"result":msg}
        return JsonResponse(result)
    else:
        return render(request, "login.html")


@csrf_exempt
def deleteDepartment(request):
    if 'username' in request.session and 'password' in request.session:
        username = request.session['username']
        log_creat_user = {}
        log_creat_user["action"] = "delete department"
        try:
            log_creat_user["computer name"] = pc_names[username.lower()]
        except:
            pass
        log_creat_user["username"] = username
        log_creat_user["time"] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
        language = request.session['language']
        departmentCode = request.POST.get('departmentCode')
        department_name = list(Department.objects.filter(department_code=departmentCode).values("department_name"))[0]["department_name"]
        department_list = [department_name]
        init_dep = department_name
        children_name_list = list(Department.objects.filter(parent_code__istartswith=departmentCode).values("department_name").order_by('department_code'))
        for children_name in children_name_list:
            init_dep = init_dep + "/" + children_name["department_name"]
            department_list.append(init_dep)
        log_creat_user["department"] = str(department_list)
        try:
            department_tupe = Department.objects.all().filter(department_code=departmentCode).values('parent_code','parent_codes','tree_leaf','company__organization','company','department_name')
            treeLeaf = int(department_tupe[0]['tree_leaf'])
            parentCode = department_tupe[0]['parent_code']
            departmentName = department_tupe[0]['department_name']
            organization = department_tupe[0]['company__organization']
            company = department_tupe[0]['company']
            organizationobj  = Organization.objects.get(pk=organization)
            Companyobj = Company.objects.get(pk=company)

            topDepartmentCode = parentCode
            folder_path = departmentName.replace(" ", "")
            while topDepartmentCode != "0":
                department_tuple = Department.objects.filter(department_code=topDepartmentCode).values('parent_code',
                                                                                                       'department_name')
                topDepartmentCode = department_tuple[0]['parent_code']
                department_name = department_tuple[0]['department_name']
                folder_path = department_name.replace(" ", "") + "\\" + folder_path
            folder = organizationobj.organization.replace(" ", "") + "\\" + Companyobj.company.replace(" ","") + "\\" + folder_path
            folder1 = settings.File_Root + "\\Draw_Process\\pyfile\\public\\" +  organizationobj.organization.replace(" ", "") + "\\" + Companyobj.company.replace(" ",
                                                                                                           "") + "\\" + folder_path
            folder2 = settings.File_Root  + "\\Draw_Process\\pyfile\\release\\" +  organizationobj.organization.replace(" ", "") + "\\" + Companyobj.company.replace(" ",
                                                                                                        "") + "\\" + folder_path

            if os.path.exists(folder1):
                userutils.deletePath(folder1)
            if os.path.exists(folder2):
                userutils.deletePath(folder2)

            Permission.objects.filter(name__icontains=folder).delete()
            if treeLeaf == 0:
                parentCodes = parentCode + ',' + departmentCode + ','
                Department.objects.filter(parent_codes__icontains=parentCodes).delete()
            Department.objects.filter(department_code=departmentCode).delete()
            if len(Department.objects.all().filter(parent_code=parentCode).values('department_code')) == 0:
                Department.objects.all().filter(department_code=parentCode).update(tree_leaf=1)
            log_user_json = "1003>" + json.dumps(log_creat_user)
            logger.info(log_user_json)
            result = {"result":"success"}
        except Exception as  e:
            print(str(e))
            msg = gettext("Delete department failed!")
            result = {"result":msg}
        return JsonResponse(result)
    else:
        return render(request, "login.html")



@csrf_exempt
def departmentAdd(request):
    if 'username' in request.session and 'password' in request.session:
        username = request.session['username']
        language = request.session['language']
        auth = 'Draw_Process.views_panel_company_list_menu_search_all_organizations'
        auth1 = "Draw_Process.views_panel_department_list_menu_search_all_organizations"
        auth2 = "Draw_Process.views_panel_department_list_menu_search_all_companies"
        department_json = userutils.companyAuth(username, auth1, auth2, language)
        try:
            upperDepartmentCode = request.GET['upperDepartmentCode']
            upperDepartment = request.GET['upperDepartment']
        except:
            upperDepartmentCode = "0"
            upperDepartment = ''
        if upperDepartmentCode == "0":
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
            department_tuple = Department.objects.filter(department_code=upperDepartmentCode).values( 'company__company','company__organization__organization')
            organization = department_tuple[0]['company__organization__organization']
            company = department_tuple[0]['company__company']
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
            department_json['organization'] = organization
            department_json['company'] =company
            department_json['upperDepartmentCode'] = upperDepartmentCode
            department_json['upperDepartment'] = upperDepartment
            department_json['departmentCode'] = departmentCode
            department_json['treeSort'] = treeSort
        return render(request, 'departmentAdd.html', department_json)
    else:
        return render(request, "login.html")



@csrf_exempt
def createDepartment(request):
    if 'username' in request.session and 'password' in request.session:
        try:
            username = request.session['username']
            log_creat_user = {}
            log_creat_user["action"] = "create department"
            try:
                log_creat_user["computer name"] = pc_names[username.lower()]
            except:
                pass
            log_creat_user["username"] = username
            log_creat_user["time"] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
            info = str(request.POST)
            index = info.find("{")
            log_creat_user["info"] = info[index::].replace(">","")
            language = request.session['language']
            organization = request.POST.get("organization")
            remarks = request.POST.get("remarks")
            company = request.POST.get("company")

            companyobj = Company.objects.filter(company=company)[0]

            upperDepartmentCode = request.POST.get("upperDepartmentCode")
            departmentName = request.POST.get("departmentName")
            departmentCode = request.POST.get("departmentCode")
            fullName = request.POST.get("fullName")
            treeSort = request.POST.get("treeSort")
            now_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            if upperDepartmentCode == '' or upperDepartmentCode == None:
                upperDepartmentCode = "0"
            if len(Department.objects.filter(company__organization__organization=organization,company__company=company,department_code=departmentCode).values('department_code')) > 0:
                msg = gettext("This department code already exists!")
                return JsonResponse({"result": "failed", "msg": msg})
            elif len(Department.objects.filter(company__organization__organization=organization,company__company=company,department_name=departmentName,parent_code=upperDepartmentCode).values('department_code')) > 0:
                msg = gettext("This department name already exists!")
                return JsonResponse({"result": "failed", "msg": msg})
            else:
                if upperDepartmentCode != "0":
                    topDepartmentCode = upperDepartmentCode
                    folder_path = departmentName.replace(" ","")
                    while topDepartmentCode != "0":
                        department_tuple = Department.objects.filter(department_code=topDepartmentCode).values('parent_code', 'department_name')
                        topDepartmentCode = department_tuple[0]['parent_code']
                        department_name = department_tuple[0]['department_name']
                        folder_path = department_name.replace(" ","") + "\\" + folder_path
                    folder1 = settings.File_Root + "\\Draw_Process\\pyfile\\public\\" + organization.replace(" ","") + "\\" + company.replace(" ","") + "\\" + folder_path
                    folder2 = settings.File_Root + "\\Draw_Process\\pyfile\\release\\" + organization.replace(" ", "") + "\\" + company.replace(" ",
                                                                                                           "") + "\\" + folder_path
                    if os.path.exists(folder1):
                        pass
                    else:
                        os.mkdir(folder1)
                    if os.path.exists(folder2):
                        pass
                    else:
                        os.mkdir(folder2)
                    Department.objects.distinct().filter(department_code=upperDepartmentCode).update(tree_leaf=0)
                    upperDepartment_tuple = Department.objects.distinct().filter(department_code=upperDepartmentCode).values('parent_codes','tree_sorts','tree_level')
                    parent_codes = upperDepartment_tuple[0]['parent_codes'] + upperDepartmentCode + ','
                    sort_length = len(str(treeSort))
                    tree_sorts = upperDepartment_tuple[0]['parent_codes'] + treeSort.zfill(10-sort_length) + ','
                    tree_level = int(upperDepartment_tuple[0]['tree_level']) + 1
                    per_name = organization.replace(" ", "") + "\\" + company.replace(" ","") + "\\" + folder_path
                    codeName = "views_folder_" + organization.replace(" ", "") + "\\" + company.replace(" ", "") + "\\" + folder_path
                    per = Permission.objects.filter(name=per_name, content_type_id=18, codename=codeName)
                    if per == None or per.count() == 0:
                        Permission.objects.create(name=per_name, content_type_id=18, codename=codeName)
                    Department.objects.create( company=companyobj,
                                              department_code=departmentCode,parent_code=upperDepartmentCode,
                                              parent_codes=parent_codes,tree_sort=treeSort,tree_sorts=tree_sorts,
                                              tree_leaf=1,tree_level=tree_level,department_name=departmentName,
                                              full_name=fullName,status=1,remarks=remarks,create_on=now_time,create_by=username)


                else:
                    folder1 = settings.File_Root + "\\Draw_Process\\pyfile\\public\\" + organization.replace(" ","") + "\\" + company.replace(" ","") + "\\" + departmentName.replace(" ","")
                    folder2 = settings.File_Root + "\\Draw_Process\\pyfile\\release\\" + organization.replace(" ","") + "\\" + company.replace(" ","") + "\\" + departmentName.replace(" ","")
                    if os.path.exists(folder1):
                        pass
                    else:
                        os.mkdir(folder1)
                    if os.path.exists(folder2):
                        pass
                    else:
                        os.mkdir(folder2)
                    tree_sorts = str(treeSort) + ","
                    per_name = organization.replace(" ","") + "\\" + company.replace(" ","") + "\\" + departmentName.replace(" ","")
                    codeName = "views_folder_" + organization.replace(" ","") + "\\" + company.replace(" ","") + "\\" + departmentName.replace(" ","")


                    Department.objects.create(company=companyobj,
                                              department_code=departmentCode, parent_code="0",
                                              parent_codes="0,", tree_sort=treeSort, tree_sorts=tree_sorts,
                                              tree_leaf=1, tree_level=0, department_name=departmentName,
                                              full_name=fullName, status=1, remarks=remarks, create_on=now_time,
                                              create_by=username)
                    per =  Permission.objects.filter(name=per_name, content_type_id=18, codename=codeName)
                    if per != None or per.count() == 0:
                        Permission.objects.create(name=per_name, content_type_id=18, codename=codeName)
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
                log_user_json = "1000>" + json.dumps(log_creat_user)
                logger.info(log_user_json)
                return JsonResponse({"result": "success", "maxSort": maxSort, "treeSort": treeSort})
        except Exception as e:
            s = str(e)
            msg = gettext("Create Department failed!")
            return JsonResponse({"result": "failed","msg":msg})
    else:
        return render(request, "login.html")


@csrf_exempt
def orgDepartment(request):
    if 'username' in request.session and 'password' in request.session:
        username = request.session['username']
        language = request.session['language']
        auth1 = "Draw_Process.views_panel_department_list_menu_search_all_organizations"
        auth2 = "Draw_Process.views_panel_department_list_menu_search_all_companies"
        json = userutils.companyAuth(username, auth1, auth2, language)
        return render(request,'department.html',json)
    else:
        return render(request, "login.html")

@csrf_exempt
def departmentList(request):
    if 'username' in request.session and 'password' in request.session:
        username = request.session['username']
        language = request.session['language']
        if request.method == 'POST':
            # 筛选条件
            organization = userutils.xstr(request.POST.get("organization"))
            company =  userutils.xstr(request.POST.get("company"))
            departmentName =  userutils.xstr(request.POST.get("departmentName"))
            nodeId =  userutils.xstr(request.POST.get('nodeid'))
            auth1 = "Draw_Process.views_panel_department_list_menu_search_all_organizations"
            auth2 = "Draw_Process.views_panel_department_list_menu_search_all_companies"
            company_json =  userutils.companyAuth(username, auth1, auth2, language)
            dep_json = {}
            if nodeId != None and nodeId != "":
                department_tupe = Department.objects.all().filter(department_code=nodeId).values('parent_codes','tree_leaf')
                treeLeaf = int(department_tupe[0]['tree_leaf'])
                if treeLeaf == 0:
                    parentCodes = department_tupe[0]['parent_codes'] + nodeId + ','
                    department_tupe = Department.objects.all().filter(parent_codes__icontains=parentCodes)
                    department_list = serializers.serialize('json', department_tupe)
                    department_array = json.loads(department_list)
                    department_result = []
                    for j in range(len(department_array)):
                        department_json = {}
                        field = department_array[j]['fields']
                        department_json["id"] = department_array[j]['pk']
                        department_json["departmentCode"] = department_array[j]['pk']
                        department_json["organization"] = field['organization']
                        department_json["company"] = field['company']
                        department_json["remarks"] = field['remarks']
                        department_json["createOn"] = field['create_on'].replace("T", " ")
                        department_json["createBy"] = field['create_by']
                        department_json["treeSorts"] = field['tree_sorts']
                        department_json["treeLevel"] = int(field['tree_level'])
                        department_json["treeSort"] = int(field['tree_sort'])
                        department_json["parentCodes"] = field['parent_codes']
                        department_json["parentCode"] = field['parent_code']
                        department_json["status"] = field['status']
                        treeLeaf = int(field['tree_leaf'])
                        if treeLeaf == 0:
                            department_json["isTreeLeaf"] = False
                        else:
                            department_json["isTreeLeaf"] = True
                        department_json["treeLeaf"] = field['tree_leaf']
                        department_json["departmentName"] = field['department_name']
                        department_json["fullName"] = field['full_name']
                        department_result.append(department_json)
                    dep_json["list"] = department_result
                return JsonResponse(dep_json)
            else:
                if company_json['organization'] == "" and company_json['company'] == "":
                    department_tupe = Department.objects.all().filter(company__organization__organization__icontains=organization, company__company__icontains=company, department_name__icontains=departmentName)
                elif company_json['organization'] != "" and company_json['company'] == "":
                    department_tupe = Department.objects.all().filter(company__organization__organization=company_json['organization'], company__company__icontains=company, department_name__icontains=departmentName)
                else:
                    department_tupe = Department.objects.all().filter(company__organization__organization=company_json['organization'], company__company=company_json['company'], department_name__icontains=departmentName)
                department_list = serializers.serialize('json', department_tupe)
                department_array = json.loads(department_list)
                department_result = []
                for j in range(len(department_array)):
                    department_json = {}
                    field = department_array[j]['fields']
                    department_json["id"] = department_array[j]['pk']
                    department_json["departmentCode"] = department_array[j]['pk']
                    Departmentarrayinfo = Department.objects.filter(department_code=department_array[j]['pk']).values(
                                                                                            'company__company',
                                                                                            'company__organization__organization')
                    if len(Departmentarrayinfo)>0 :
                        Departmentinfo = Departmentarrayinfo[0]
                        department_json["organization"] = Departmentinfo['company__organization__organization']
                        department_json["company"] = Departmentinfo['company__company']
                    else:
                        department_json["organization"] = ''
                        department_json["company"] = ''

                    department_json["remarks"] = field['remarks']
                    department_json["createOn"] = field['create_on'].replace("T"," ")
                    department_json["createBy"] = field['create_by']
                    department_json["treeSorts"] = field['tree_sorts']
                    department_json["treeLevel"] = int(field['tree_level'])
                    department_json["treeSort"] = int(field['tree_sort'])
                    department_json["parentCodes"] = field['parent_codes']
                    department_json["parentCode"] = field['parent_code']
                    department_json["status"] = field['status']
                    treeLeaf = int(field['tree_leaf'])
                    if treeLeaf == 0:
                        department_json["isTreeLeaf"] = False
                    else:
                        department_json["isTreeLeaf"] = True
                    department_json["treeLeaf"] = field['tree_leaf']
                    department_json["departmentName"] = field['department_name']
                    department_json["fullName"] = field['full_name']
                    department_result.append(department_json)
                dep_json["list"] = department_result
                return JsonResponse(dep_json)
    else:
        return render(request, "login.html")


@csrf_exempt
def departmentSelect(request):
    if request.method == 'POST':
        organization = request.POST.get("organization")
        company = request.POST.get("company")
        department_list = Department.objects.distinct().filter(company__organization__organization=organization,company__company=company,status="1").values('department_code','department_name','parent_code','full_name')
        department_array = []
        for i in range(len(department_list)):
            department_json = {}
            department_json["id"] = department_list[i]['department_code']
            department_json["name"] = department_list[i]['department_name']
            department_json["pId"] = department_list[i]['parent_code']
            department_json["title"] = department_list[i]['full_name']
            department_array.append(department_json)
        return JsonResponse({"list":department_array})