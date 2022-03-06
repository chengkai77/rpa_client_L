
from django.shortcuts import render
from django.http import JsonResponse

from django.contrib.auth.models import User
from django.contrib.auth.models import Group
from django.contrib.auth.models import Permission
from django.views.decorators.csrf import csrf_exempt
from Draw_Process.models import Department
from Draw_Process.models import Company
from Draw_Process.models import MenuPermission
from Draw_Process.models import FunctionPermission
from Draw_Process.models import PanelPermission
from Draw_Process.models import Organization
from Draw_Process.models import AuthMessage
from django.utils.translation import gettext



#???????
@csrf_exempt
def editUserFolderAuth(request):
    if 'username' in request.session and 'password' in request.session:
        if request.method == 'POST':
            username = request.session['username']
            per_json = {}
            organizations = Organization.objects.distinct().filter(status=1).values('organization')
            folder_list = []
            id = 1
            permissions = []
            for organization in organizations:
                organization_json = {}
                organization_name = organization['organization']
                organization_json['name'] = organization_name
                organization_json['pId'] = "0"
                organization_json['id'] = str(id)
                organization_id = str(id)
                id+=1
                organization_json['title'] = organization_name
                organization_perm = "Draw_Process.views_folder_" + organization_name.replace(" ","")
                organization_json['perm'] = organization_perm
                permissions.append(organization_perm)
                folder_list.append(organization_json)
                companies = Company.objects.distinct().filter(organization__organization=organization_name,status=1).values('company')
                for company in companies:
                    company_json = {}
                    company_name = company['company']
                    company_json['name'] = company_name
                    company_json['pId'] = organization_id
                    company_json['id'] = str(id)
                    company_id = str(id)
                    id+=1
                    company_json['title'] = company_name
                    company_perm = "Draw_Process.views_folder_" + organization_name.replace(" ","") + "\\" + company_name.replace(" ", "")
                    company_json['perm'] = company_perm
                    permissions.append(company_perm)
                    folder_list.append(company_json)
                    departments = Department.objects.distinct().filter(company__organization__organization=organization_name,company__company=company_name,status=1).values('department_code', 'parent_code', 'department_name')
                    for department in departments:
                        department_json = {}
                        department_name = department['department_name']
                        department_json['name'] = department_name
                        pId = department['parent_code']
                        if int(pId) == 0:
                            department_json['pId'] = company_id
                            department_perm = "Draw_Process.views_folder_" + organization_name.replace(" ","") + "\\" + company_name.replace(" ", "") + "\\" + department_name.replace(" ", "")
                            department_json['perm'] = department_perm
                            permissions.append(department_perm)
                        else:
                            department_json['pId'] = pId
                            folder = department_name.replace(" ", "")
                            while int(pId) != 0:
                                department_tuple = Department.objects.filter(department_code=pId).values('parent_code', 'department_name')
                                pId = department_tuple[0]['parent_code']
                                upper_department_name = department_tuple[0]['department_name']
                                folder = upper_department_name.replace(" ", "") + "\\" + folder
                            department_json['perm'] = "Draw_Process.views_folder_" + organization_name.replace(" ","") + "\\" + company_name.replace(" ", "") + "\\" + folder
                            permissions.append(department_json['perm'])
                        department_code = department['department_code']
                        department_json['id'] = department_code
                        department_json['title'] = department_name
                        folder_list.append(department_json)
            try:
                perms_list = []
                userid = request.GET['user']
                user = AuthMessage.objects.get(username=userid)
                perms = AuthMessage.get_all_permissions(user)
                for permission in permissions:
                    if permission in perms:
                        perms_list.append(permission)
            except Exception:
                perms_list = []
            return JsonResponse({"list": folder_list,"perms":perms_list})
    else:
        return render(request, "login.html")

@csrf_exempt
def editUserCommanderAuth(request):
    if 'username' in request.session and 'password' in request.session:
        if request.method == 'POST':
            username = request.session['username']
            per_json = {}
            organizations = Organization.objects.distinct().filter(status=1).values('organization')
            folder_list = []
            id = 1
            permissions = []
            for organization in organizations:
                organization_json = {}
                organization_name = organization['organization']
                organization_json['name'] = organization_name
                organization_json['pId'] = "0"
                organization_json['id'] = str(id)
                organization_id = str(id)
                id+=1
                organization_json['title'] = organization_name
                organization_perm = "Draw_Process.views_folder_" + organization_name.replace(" ","")
                organization_json['perm'] = organization_perm
                permissions.append(organization_perm)
                folder_list.append(organization_json)
                companies = Company.objects.distinct().filter(organization__organization=organization_name,status=1).values('company')
                for company in companies:
                    company_json = {}
                    company_name = company['company']
                    company_json['name'] = company_name
                    company_json['pId'] = organization_id
                    company_json['id'] = str(id)
                    company_id = str(id)
                    id+=1
                    company_json['title'] = company_name
                    company_perm = "Draw_Process.views_folder_" + organization_name.replace(" ","") + "\\" + company_name.replace(" ", "")
                    company_json['perm'] = company_perm
                    permissions.append(company_perm)
                    folder_list.append(company_json)
                    departments = Department.objects.distinct().filter(company__organization__organization=organization_name,company__company=company_name,status=1).values('department_code', 'parent_code', 'department_name', 'tree_leaf')
                    for department in departments:
                        department_json = {}
                        department_name = department['department_name']
                        department_json['name'] = department_name
                        pId = department['parent_code']
                        tree_leaf = int(department['tree_leaf'])
                        department_code = department['department_code']
                        usernames_list = AuthMessage.objects.filter(department_id=department_code).values('username')
                        for i in range(len(usernames_list)):
                            username_json = {}
                            username = str(usernames_list[i]['username'])
                            username_json['id'] = str(department_code) + "-" + str(i+1)
                            username_json['pId'] = department_code
                            username_json['title'] = username
                            username_json['name'] = username
                            user_perm = "Draw_Process.views_user_" + username
                            username_json['perm'] = user_perm
                            permissions.append(user_perm)
                            folder_list.append(username_json)
                            view_json = {}
                            view_json['id'] = str(department_code) + "-" + str(i + 1) + "-0"
                            view_json['pId'] = str(department_code) + "-" + str(i + 1)
                            view_json['title'] = gettext("View Task")
                            view_json['name'] = gettext("View Task")
                            view_perm = "Draw_Process.views_commander_" + username + "_view_task"
                            view_json['perm'] = view_perm
                            permissions.append(view_perm)
                            folder_list.append(view_json)
                            assign_json = {}
                            assign_json['id'] = str(department_code) + "-" + str(i + 1) + "-1"
                            assign_json['pId'] =  str(department_code) + "-" + str(i + 1)
                            assign_json['title'] = gettext("Assign Task")
                            assign_json['name'] = gettext("Assign Task")
                            assign_perm = "Draw_Process.views_commander_" + username + "_assign_task"
                            assign_json['perm'] = assign_perm
                            permissions.append(assign_perm)
                            folder_list.append(assign_json)
                            schedule_json = {}
                            schedule_json['id'] = str(department_code) + "-" + str(i + 1) + "-2"
                            schedule_json['pId'] = str(department_code) + "-" + str(i + 1)
                            schedule_json['title'] = gettext("Schedule Task")
                            schedule_json['name'] = gettext("Schedule Task")
                            schedule_perm = "Draw_Process.views_commander_" + username + "_schedule_task"
                            schedule_json['perm'] = schedule_perm
                            permissions.append(schedule_perm)
                            folder_list.append(schedule_json)
                        if int(pId) == 0:
                            department_json['pId'] = company_id
                            department_perm = "Draw_Process.views_folder_" + organization_name.replace(" ","") + "\\" + company_name.replace(" ", "") + "\\" + department_name.replace(" ", "")
                            department_json['perm'] = department_perm
                            permissions.append(department_perm)
                        else:
                            department_json['pId'] = pId
                            folder = department_name.replace(" ", "")
                            while int(pId) != 0:
                                department_tuple = Department.objects.filter(department_code=pId).values('parent_code', 'department_name','department_code')
                                pId = department_tuple[0]['parent_code']
                                upper_department_name = department_tuple[0]['department_name']
                                folder = upper_department_name.replace(" ", "") + "\\" + folder
                            department_json['perm'] = "Draw_Process.views_folder_" + organization_name.replace(" ","") + "\\" + company_name.replace(" ", "") + "\\" + folder
                        department_json['id'] = department_code
                        department_json['title'] = department_name
                        folder_list.append(department_json)
            try:
                perms_list = []
                userid = request.GET['user']
                user = AuthMessage.objects.get(username=userid)
                perms = AuthMessage.get_all_permissions(user)
                for permission in permissions:
                    if permission in perms:
                        perms_list.append(permission)
            except Exception:
                perms_list = []
            return JsonResponse({"list": folder_list,"perms":perms_list})
    else:
        return render(request, "login.html")

@csrf_exempt
def editUserMenuAuth(request):
    if 'username' in request.session and 'password' in request.session:
        if request.method == 'POST':
            username = request.session['username']
            per_json = {}
            pers = MenuPermission.objects.values('name','child_name1','child_name2','child_name3','child_name4','perm')
            for per in pers:
                name = per['name']
                child_name1 = per['child_name1']
                if not child_name1 is None and child_name1 != 'null':
                    child_name1 = "-" + str(child_name1) + "-"
                else:
                    child_name1 = ""
                child_name2 = per['child_name2']
                if not child_name2 is None and child_name2 != 'null':
                    child_name2 = "-" + str(child_name2) + "-"
                else:
                    child_name2 = ""
                child_name3 = per['child_name3']
                if not child_name3 is None and child_name3 != 'null':
                    child_name3 = "-" + str(child_name3) + "-"
                else:
                    child_name3 = ""
                child_name4 = per['child_name4']
                if not child_name4 is None and child_name4 != 'null':
                    child_name4 = "-" + str(child_name4) + "-"
                else:
                    child_name4 = ""
                per_json[str(name) + child_name1 + child_name2 + child_name3 + child_name4] = per['perm']
            menus = MenuPermission.objects.values('name')
            menus_list_new = []
            menus_name_list = []
            for i in menus:
                if i['name'] not in menus_name_list:
                    menus_name_list.append(i['name'])
                    menus_list_new.append(i)
            menus = menus_list_new
            menus_list = []
            for menu in menus:
                menu_json = {}
                menus_childs = []
                name = menu['name']
                menu_json['name'] = gettext(name)
                menu_json['pId'] = "0"
                menu_json['title'] = gettext(name)
                menu_json['perm'] = "Draw_Process.views_menu_" + name.lower().replace(" ","_")
                child1_menus = MenuPermission.objects.distinct().filter(name=name).values('child_name1')
                child1_list = []
                if len(child1_menus) > 1:
                    for child1 in child1_menus:
                        child1_json = {}
                        child_name1 = child1['child_name1']
                        child1_json['name'] = gettext(child_name1)
                        child1_json['pId'] = "1"
                        child1_json['title'] = gettext(child_name1)
                        child1_json['perm'] = "Draw_Process.views_menu_" + name.lower().replace(" ","_") + "_" + child_name1.lower().replace(" ","_")
                        child2_menus = MenuPermission.objects.distinct().filter(name=name,child_name1=child_name1).values('child_name2')
                        child2_list = []
                        if len(child2_menus) > 1:
                            for child2 in child2_menus:
                                child2_json = {}
                                child_name2 = child2['child_name2']
                                child2_json['name'] = gettext(child_name2)
                                child2_json['pId'] = "2"
                                child2_json['title'] = gettext(child_name2)
                                child2_json['perm'] = "Draw_Process.views_menu_" + name.lower().replace(" ","_") + "_" + child_name1.lower().replace(" ","_") + "_" + child_name2.lower().replace(" ","_")
                                child3_menus = MenuPermission.objects.distinct().filter(name=name,child_name1=child_name1,child_name2=child_name2).values('child_name3')
                                child3_list = []
                                if len(child3_menus) > 1:
                                    for child3 in child3_menus:
                                        child3_json = {}
                                        child_name3 = child3['child_name3']
                                        child3_json['name'] = gettext(child_name3)
                                        child3_json['pId'] = "3"
                                        child3_json['title'] = gettext(child_name3)
                                        child3_json['perm'] = "Draw_Process.views_menu_" + name.lower().replace(" ","_") + "_" + child_name1.lower().replace(" ","_") + "_" + child_name2.lower().replace(" ","_") + "_" + child_name3.lower().replace(" ","_")
                                        child4_menus = MenuPermission.objects.distinct().filter(name=name,child_name1=child_name1,child_name2=child_name2,child_name3=child_name3).values('child_name4')
                                        child4_list = []
                                        if len(child4_menus) > 1:
                                            for child4 in child4_menus:
                                                child4_json = {}
                                                child_name4 = child4['child_name4']
                                                child4_json['name'] = gettext(child_name4)
                                                child4_json['pId'] = "4"
                                                child4_json['title'] = gettext(child_name4)
                                                child4_json['perm'] = per_json[name + "-" + child_name1 + "-" + child_name2 + "-" + child_name3 + "-" + child_name4]
                                                child4_list.append(child4_json)
                                        child3_json['children'] = child4_list
                                        child3_list.append(child3_json)
                                child2_json['children'] = child3_list
                                child2_list.append(child2_json)
                        child1_json['children'] = child2_list
                        child1_list.append(child1_json)
                menu_json['children'] = child1_list
                menus_list.append(menu_json)
            ctrlName_en = request.POST.get('ctrlName_en')
            try:
                perms_list = []
                userid = request.GET['user']
                user = AuthMessage.objects.get(username=userid)
                perms = AuthMessage.get_all_permissions(user)
                permissions = MenuPermission.objects.values('perm')
                for permission in permissions:
                    perm = permission['perm']
                    if perm in perms:
                        perms_list.append(perm)
            except:
                perms_list = []
            return JsonResponse({"list": menus_list,"perms":perms_list})
    else:
        return render(request, "login.html")

@csrf_exempt
def editUserFunctionAuth(request):
    if 'username' in request.session and 'password' in request.session:
        if request.method == 'POST':
            username = request.session['username']
            functions = FunctionPermission.objects.values('module')
            functions_list_new = []
            functions_name_list = []
            for i in functions:
                if i['module'] not in functions_name_list:
                    functions_name_list.append(i['module'])
                    functions_list_new.append(i)
            functions = functions_list_new
            functions_list = []
            for function in functions:
                function_json = {}
                functions_childs = []
                module = function['module']
                function_json['name'] = gettext(module)
                function_json['pId'] = "0"
                function_json['title'] = gettext(module)
                if module == "Main Function":
                    perm = "main_function"
                elif module == "General Module":
                    perm = "general_module"
                elif module == "Mouse&Keyboard":
                    perm = "mouse&keyboard"
                elif module == "SAP":
                    perm = "sap"
                elif module == "Excel Module":
                    perm = "excel_module"
                elif module == "File Module":
                    perm = "file_module"
                elif module == "Access Module":
                    perm = "access_module"
                elif module == "Web Module":
                    perm = "web_module"
                elif module == "Mail":
                    perm = "mail"
                elif module == "HCI Module":
                    perm = "hci_module"
                elif module == "AI Module":
                    perm = "ai_module"
                elif module == "Self Development":
                    perm = "self_development"
                function_json['perm'] = perm
                childrens = FunctionPermission.objects.distinct().filter(module=module).values('function','perm')
                childrens_list = []
                for children in childrens:
                    children_json = {}
                    function = children['function']
                    children_json['name'] = gettext(function)
                    children_json['pId'] = "1"
                    children_json['title'] = gettext(function)
                    children_json['perm'] = children['perm']
                    childrens_list.append(children_json)
                function_json['children'] = childrens_list
                functions_list.append(function_json)
            ctrlName_en = request.POST.get('ctrlName_en')
            try:
                perms_list = []
                userid = request.GET['user']
                user = AuthMessage.objects.get(username=userid)
                perms = AuthMessage.get_all_permissions(user)
                permissions_list = []
                permissions = FunctionPermission.objects.values('perm')
                for permission in permissions:
                    perm = permission['perm']
                    if perm in perms:
                        perms_list.append(perm)
            except:
                perms_list = []
            return JsonResponse({"list": functions_list,"perms":perms_list})
    else:
        return render(request, "login.html")


#????????
@csrf_exempt
def editUserPanelAuth(request):
    if 'username' in request.session and 'password' in request.session:
        if request.method == 'POST':
            username = request.session['username']
            per_json = {}
            panels_list = []
            pers = PanelPermission.objects.values('name', 'child_name1', 'child_name2', 'child_name3', 'child_name4','perm')
            for per in pers:
                name = per['name'].lower().replace(" ","_")
                child_name1 = per['child_name1']
                if not child_name1 is None and child_name1 != 'null' and child_name1 != '':
                    child_name1 = "-" + str(child_name1).lower().replace(" ","_")
                else:
                    child_name1 = ""
                child_name2 = per['child_name2']
                if not child_name2 is None and child_name2 != 'null' and child_name2 != '':
                    child_name2 = "-" + str(child_name2).lower().replace(" ","_")
                else:
                    child_name2 = ""
                child_name3 = per['child_name3']
                if not child_name3 is None and child_name3 != 'null' and child_name3 != '':
                    child_name3 = "-" + str(child_name3).lower().replace(" ","_")
                else:
                    child_name3 = ""
                child_name4 = per['child_name4']
                if not child_name4 is None and child_name4 != 'null' and child_name4 != '':
                    child_name4 = "-" + str(child_name4).lower().replace(" ","_")
                else:
                    child_name4 = ""
                per_json[str(name) + child_name1 + child_name2 + child_name3 + child_name4] = per['perm']
            panels = PanelPermission.objects.values('name')
            panels_list_new = []
            panels_name_list = []
            for i in panels:
                if i['name'] not in panels_name_list:
                    panels_name_list.append(i['name'])
                    panels_list_new.append(i)
            panels = panels_list_new
            for panel in panels:
                panel_json = {}
                name = panel['name']
                panel_json['name'] = gettext(name)
                panel_json['pId'] = "0"
                panel_json['title'] = gettext(name)
                panel_json['perm'] = "Draw_Process.views_panel_" + name.lower().replace(" ", "_")
                child1_menus = PanelPermission.objects.distinct().filter(name=name).values('child_name1')
                child1_list = []
                if len(child1_menus) >= 1:
                    for child1 in child1_menus:
                        child1_json = {}
                        child_name1 = child1['child_name1']
                        if child_name1 != '' and child_name1 != None:
                            child1_json['name'] = gettext(child_name1)
                            child1_json['pId'] = "1"
                            child1_json['title'] = gettext(child_name1)
                            child1_json['perm'] = "Draw_Process.views_panel_" + name.lower().replace(" ","_") + "_" + child_name1.lower().replace(" ", "_")
                            child2_menus = PanelPermission.objects.distinct().filter(name=name, child_name1=child_name1).values('child_name2')
                            child2_list = []
                            if len(child2_menus) > 1:
                                for child2 in child2_menus:
                                    child2_json = {}
                                    child_name2 = child2['child_name2']
                                    if child_name2 != '' and child_name2 != None:
                                        child2_json['name'] = gettext(child_name2)
                                        child2_json['pId'] = "2"
                                        child2_json['title'] = gettext(child_name2)
                                        child2_json['perm'] = "Draw_Process.views_panel_" + name.lower().replace(" ","_") + "_" + child_name1.lower().replace(" ", "_") + "_" + child_name2.lower().replace(" ", "_")
                                        child3_menus = PanelPermission.objects.distinct().filter(name=name, child_name1=child_name1, child_name2=child_name2).values('child_name3')
                                        child3_list = []
                                        if len(child3_menus) > 1:
                                            for child3 in child3_menus:
                                                child3_json = {}
                                                child_name3 = child3['child_name3']
                                                if child_name3 != '' and child_name3 != None:
                                                    child3_json['name'] = gettext(child_name3)
                                                    child3_json['pId'] = "3"
                                                    child3_json['title'] = gettext(child_name3)
                                                    child3_json['perm'] = "Draw_Process.views_panel_" + name.lower().replace(" ",
                                                                                                                            "_") + "_" + child_name1.lower().replace(
                                                        " ", "_") + "_" + child_name2.lower().replace(" ",
                                                                                                      "_") + "_" + child_name3.lower().replace(
                                                        " ", "_")
                                                    child4_menus = PanelPermission.objects.distinct().filter(name=name,
                                                                                                            child_name1=child_name1,
                                                                                                            child_name2=child_name2,
                                                                                                            child_name3=child_name3).values(
                                                        'child_name4')
                                                    child4_list = []
                                                    if len(child4_menus) > 1:
                                                        for child4 in child4_menus:
                                                            child4_json = {}
                                                            child_name4 = child4['child_name4']
                                                            if child_name4 != '' and child_name4 != None:
                                                                child4_json['name'] = gettext(child_name4)
                                                                child4_json['pId'] = "4"
                                                                child4_json['title'] = gettext(child_name4)
                                                                child4_json['perm'] = per_json[
                                                                    name.lower().replace(" ", "_") + "-" + child_name1.lower().replace(" ", "_") + "-" + child_name2.lower().replace(" ", "_") + "-" + child_name3.lower().replace(" ", "_") + "-" + child_name4.lower().replace(" ", "_")]
                                                                child4_list.append(child4_json)
                                                    child3_json['children'] = child4_list
                                                    child3_list.append(child3_json)
                                        child2_json['children'] = child3_list
                                        child2_list.append(child2_json)
                            child1_json['children'] = child2_list
                            child1_list.append(child1_json)
                panel_json['children'] = child1_list
                panels_list.append(panel_json)
            try:
                perms_list = []
                userid = request.GET['user']
                user = AuthMessage.objects.get(username=userid)
                perms = AuthMessage.get_all_permissions(user)
                permissions_list = []
                permissions = PanelPermission.objects.values('perm')
                for permission in permissions:
                    perm = permission['perm']
                    if perm in perms:
                        perms_list.append(perm)
            except Exception:
                perms_list = []
            return JsonResponse({"list": panels_list,"perms":perms_list})
    else:
        return render(request, "login.html")

@csrf_exempt
def editRolePanelAuth(request):
    if 'username' in request.session and 'password' in request.session:
        if request.method == 'POST':
            username = request.session['username']
            panels_list = []
            per_json = {}
            pers = PanelPermission.objects.values('name', 'child_name1', 'child_name2', 'child_name3', 'child_name4', 'perm')
            for per in pers:
                name = per['name'].lower().replace(" ", "_")
                child_name1 = per['child_name1']
                if not child_name1 is None and child_name1 != 'null' and child_name1 != '':
                    child_name1 = "-" + str(child_name1).lower().replace(" ", "_")
                else:
                    child_name1 = ""
                child_name2 = per['child_name2']
                if not child_name2 is None and child_name2 != 'null' and child_name2 != '':
                    child_name2 = "-" + str(child_name2).lower().replace(" ", "_")
                else:
                    child_name2 = ""
                child_name3 = per['child_name3']
                if not child_name3 is None and child_name3 != 'null' and child_name3 != '':
                    child_name3 = "-" + str(child_name3).lower().replace(" ", "_")
                else:
                    child_name3 = ""
                child_name4 = per['child_name4']
                if not child_name4 is None and child_name4 != 'null' and child_name4 != '':
                    child_name4 = "-" + str(child_name4).lower().replace(" ", "_")
                else:
                    child_name4 = ""
                per_json[str(name) + child_name1 + child_name2 + child_name3 + child_name4] = per['perm']
            panels = PanelPermission.objects.values('name')
            panels_list_new = []
            panels_name_list = []
            for i in panels:
                if i['name'] not in panels_name_list:
                    panels_name_list.append(i['name'])
                    panels_list_new.append(i)
            panels = panels_list_new
            for panel in panels:
                panel_json = {}
                name = panel['name']
                panel_json['name'] = gettext(name)
                panel_json['pId'] = "0"
                panel_json['title'] = gettext(name)
                panel_json['perm'] = "Draw_Process.views_panel_" + name.lower().replace(" ", "_")
                child1_menus = PanelPermission.objects.distinct().filter(name=name).values('child_name1')
                child1_list = []
                if len(child1_menus) >= 1:
                    for child1 in child1_menus:
                        child1_json = {}
                        child_name1 = child1['child_name1']
                        if child_name1 != '' and child_name1 != None:
                            child1_json['name'] = gettext(child_name1)
                            child1_json['pId'] = "1"
                            child1_json['title'] = gettext(child_name1)
                            child1_json['perm'] = "Draw_Process.views_panel_" + name.lower().replace(" ",
                                                                                                     "_") + "_" + child_name1.lower().replace(
                                " ", "_")
                            child2_menus = PanelPermission.objects.distinct().filter(name=name,
                                                                                     child_name1=child_name1).values(
                                'child_name2')
                            child2_list = []
                            if len(child2_menus) > 1:
                                for child2 in child2_menus:
                                    child2_json = {}
                                    child_name2 = child2['child_name2']
                                    if child_name2 != '' and child_name2 != None:
                                        child2_json['name'] = gettext(child_name2)
                                        child2_json['pId'] = "2"
                                        child2_json['title'] = gettext(child_name2)
                                        child2_json['perm'] = "Draw_Process.views_panel_" + name.lower().replace(" ",
                                                                                                                 "_") + "_" + child_name1.lower().replace(
                                            " ", "_") + "_" + child_name2.lower().replace(" ", "_")
                                        child3_menus = PanelPermission.objects.distinct().filter(name=name,
                                                                                                 child_name1=child_name1,
                                                                                                 child_name2=child_name2).values(
                                            'child_name3')
                                        child3_list = []
                                        if len(child3_menus) > 1:
                                            for child3 in child3_menus:
                                                child3_json = {}
                                                child_name3 = child3['child_name3']
                                                if child_name3 != '' and child_name3 != None:
                                                    child3_json['name'] = gettext(child_name3)
                                                    child3_json['pId'] = "3"
                                                    child3_json['title'] = gettext(child_name3)
                                                    child3_json[
                                                        'perm'] = "Draw_Process.views_panel_" + name.lower().replace(
                                                        " ",
                                                        "_") + "_" + child_name1.lower().replace(
                                                        " ", "_") + "_" + child_name2.lower().replace(" ",
                                                                                                      "_") + "_" + child_name3.lower().replace(
                                                        " ", "_")
                                                    child4_menus = PanelPermission.objects.distinct().filter(name=name,
                                                                                                             child_name1=child_name1,
                                                                                                             child_name2=child_name2,
                                                                                                             child_name3=child_name3).values(
                                                        'child_name4')
                                                    child4_list = []
                                                    if len(child4_menus) > 1:
                                                        for child4 in child4_menus:
                                                            child4_json = {}
                                                            child_name4 = child4['child_name4']
                                                            if child_name4 != '' and child_name4 != None:
                                                                child4_json['name'] = gettext(child_name4)
                                                                child4_json['pId'] = "4"
                                                                child4_json['title'] = gettext(child_name4)
                                                                child4_json['perm'] = per_json[
                                                                    name.lower().replace(" ",
                                                                                         "_") + "-" + child_name1.lower().replace(
                                                                        " ", "_") + "-" + child_name2.lower().replace(
                                                                        " ", "_") + "-" + child_name3.lower().replace(
                                                                        " ", "_") + "-" + child_name4.lower().replace(
                                                                        " ", "_")]
                                                                child4_list.append(child4_json)
                                                    child3_json['children'] = child4_list
                                                    child3_list.append(child3_json)
                                        child2_json['children'] = child3_list
                                        child2_list.append(child2_json)
                            child1_json['children'] = child2_list
                            child1_list.append(child1_json)
                panel_json['children'] = child1_list
                panels_list.append(panel_json)
            try:
                perms_list = []
                roleCode = request.GET['roleCode']
                myGroup = Group.objects.get(name=roleCode)
                groupPerms = myGroup.permissions.all()
                perms = []
                for groupPerm in groupPerms:
                    perms.append("Draw_Process." + str(groupPerm.codename))
                permissions = PanelPermission.objects.values('perm')
                for permission in permissions:
                    perm = permission['perm']
                    if perm in perms:
                        perms_list.append(perm)
            except:
                perms_list = []
            return JsonResponse({"list": panels_list,"perms":perms_list})
    else:
        return render(request, "login.html")



@csrf_exempt
def editRoleFolderAuth(request):
    if 'username' in request.session and 'password' in request.session:
        if request.method == 'POST':
            username = request.session['username']
            per_json = {}
            organizations = Organization.objects.distinct().filter(status=1).values('organization')
            folder_list = []
            id = 1
            permissions = []
            for organization in organizations:
                organization_json = {}
                organization_name = organization['organization']
                organization_json['name'] = organization_name
                organization_json['pId'] = "0"
                organization_json['id'] = str(id)
                organization_id = str(id)
                id+=1
                organization_json['title'] = organization_name
                organization_perm = "Draw_Process.views_folder_" + organization_name.replace(" ","")
                organization_json['perm'] = organization_perm
                permissions.append(organization_perm)
                folder_list.append(organization_json)
                companies = Company.objects.distinct().filter(organization__organization=organization_name,status=1).values('company')
                for company in companies:
                    company_json = {}
                    company_name = company['company']
                    company_json['name'] = company_name
                    company_json['pId'] = organization_id
                    company_json['id'] = str(id)
                    company_id = str(id)
                    id+=1
                    company_json['title'] = company_name
                    company_perm = "Draw_Process.views_folder_" + organization_name.replace(" ","") + "\\" + company_name.replace(" ", "")
                    company_json['perm'] = company_perm
                    permissions.append(company_perm)
                    folder_list.append(company_json)
                    departments = Department.objects.distinct().filter(company__organization__organization=organization_name,company__company=company_name,status=1).values('department_code', 'parent_code', 'department_name')
                    for department in departments:
                        department_json = {}
                        department_name = department['department_name']
                        department_json['name'] = department_name
                        pId = department['parent_code']
                        if int(pId) == 0:
                            department_json['pId'] = company_id
                            department_perm = "Draw_Process.views_folder_" + organization_name.replace(" ","") + "\\" + company_name.replace(" ", "") + "\\" + department_name.replace(" ", "")
                            department_json['perm'] = department_perm
                            permissions.append(department_perm)
                        else:
                            department_json['pId'] = pId
                            folder = department_name.replace(" ", "")
                            while int(pId) != 0:
                                department_tuple = Department.objects.filter(department_code=pId).values('parent_code', 'department_name')
                                pId = department_tuple[0]['parent_code']
                                upper_department_name = department_tuple[0]['department_name']
                                folder = upper_department_name.replace(" ", "") + "\\" + folder
                            department_json['perm'] = "Draw_Process.views_folder_" + organization_name.replace(" ","") + "\\" + company_name.replace(" ", "") + "\\" + folder
                            permissions.append(department_json['perm'])
                        department_code = department['department_code']
                        department_json['id'] = department_code
                        department_json['title'] = department_name
                        folder_list.append(department_json)
            try:
                perms_list = []
                roleCode = request.GET['roleCode']
                myGroup = Group.objects.get(name=roleCode)
                groupPerms = myGroup.permissions.all()
                perms = []
                for groupPerm in groupPerms:
                    perms.append("Draw_Process." + str(groupPerm.codename))
                for permission in permissions:
                    if permission in perms:
                        perms_list.append(permission)
            except Exception:
                perms_list = []
            return JsonResponse({"list": folder_list,"perms":perms_list})
    else:
        return render(request, "login.html")


@csrf_exempt
def editRoleMenuAuth(request):
    if 'username' in request.session and 'password' in request.session:
        if request.method == 'POST':
            username = request.session['username']
            per_json = {}
            pers = MenuPermission.objects.values('name', 'child_name1', 'child_name2', 'child_name3', 'child_name4',
                                                 'perm')
            for per in pers:
                name = per['name']
                child_name1 = per['child_name1']
                if not child_name1 is None and child_name1 != 'null':
                    child_name1 = "-" + str(child_name1) + "-"
                else:
                    child_name1 = ""
                child_name2 = per['child_name2']
                if not child_name2 is None and child_name2 != 'null':
                    child_name2 = "-" + str(child_name2) + "-"
                else:
                    child_name2 = ""
                child_name3 = per['child_name3']
                if not child_name3 is None and child_name3 != 'null':
                    child_name3 = "-" + str(child_name3) + "-"
                else:
                    child_name3 = ""
                child_name4 = per['child_name4']
                if not child_name4 is None and child_name4 != 'null':
                    child_name4 = "-" + str(child_name4) + "-"
                else:
                    child_name4 = ""
                per_json[str(name) + child_name1 + child_name2 + child_name3 + child_name4] = per['perm']
            menus = MenuPermission.objects.values('name')
            menus_list_new = []
            menus_name_list = []
            for i in menus:
                if i['name'] not in menus_name_list:
                    menus_name_list.append(i['name'])
                    menus_list_new.append(i)
            menus = menus_list_new
            menus_list = []
            for menu in menus:
                menu_json = {}
                menus_childs = []
                name = menu['name']
                menu_json['name'] = gettext(name)
                menu_json['pId'] = "0"
                menu_json['title'] = gettext(name)
                menu_json['perm'] = "Draw_Process.views_menu_" + name.lower().replace(" ", "_")
                child1_menus = MenuPermission.objects.distinct().filter(name=name).values('child_name1')
                child1_list = []
                if len(child1_menus) > 1:
                    for child1 in child1_menus:
                        child1_json = {}
                        child_name1 = child1['child_name1']
                        child1_json['name'] = gettext(child_name1)
                        child1_json['pId'] = "1"
                        child1_json['title'] = gettext(child_name1)
                        child1_json['perm'] = "Draw_Process.views_menu_" + name.lower().replace(" ",
                                                                                                "_") + "_" + child_name1.lower().replace(
                            " ", "_")
                        child2_menus = MenuPermission.objects.distinct().filter(name=name,
                                                                                child_name1=child_name1).values(
                            'child_name2')
                        child2_list = []
                        if len(child2_menus) > 1:
                            for child2 in child2_menus:
                                child2_json = {}
                                child_name2 = child2['child_name2']
                                child2_json['name'] = gettext(child_name2)
                                child2_json['pId'] = "2"
                                child2_json['title'] = gettext(child_name2)
                                child2_json['perm'] = "Draw_Process.views_menu_" + name.lower().replace(" ","_") + "_" + child_name1.lower().replace(" ", "_") + "_" + child_name2.lower().replace(" ", "_")
                                child3_menus = MenuPermission.objects.distinct().filter(name=name,child_name1=child_name1,child_name2=child_name2).values('child_name3')
                                child3_list = []
                                if len(child3_menus) > 1:
                                    for child3 in child3_menus:
                                        child3_json = {}
                                        child_name3 = child3['child_name3']
                                        child3_json['name'] = gettext(child_name3)
                                        child3_json['pId'] = "3"
                                        child3_json['title'] = gettext(child_name3)
                                        child3_json['perm'] = "Draw_Process.views_menu_" + name.lower().replace(" ","_") + "_" + child_name1.lower().replace(" ", "_") + "_" + child_name2.lower().replace(" ","_") + "_" + child_name3.lower().replace(" ", "_")
                                        child4_menus = MenuPermission.objects.distinct().filter(name=name,child_name1=child_name1,child_name2=child_name2,child_name3=child_name3).values('child_name4')
                                        child4_list = []
                                        if len(child4_menus) > 1:
                                            for child4 in child4_menus:
                                                child4_json = {}
                                                child_name4 = child4['child_name4']
                                                child4_json['name'] = gettext(child_name4)
                                                child4_json['pId'] = "4"
                                                child4_json['title'] = gettext(child_name4)
                                                child4_json['perm'] = per_json[name + "-" + child_name1 + "-" + child_name2 + "-" + child_name3 + "-" + child_name4]
                                                child4_list.append(child4_json)
                                        child3_json['children'] = child4_list
                                        child3_list.append(child3_json)
                                child2_json['children'] = child3_list
                                child2_list.append(child2_json)
                        child1_json['children'] = child2_list
                        child1_list.append(child1_json)
                menu_json['children'] = child1_list
                menus_list.append(menu_json)
            ctrlName_en = request.POST.get('ctrlName_en')
            try:
                perms_list = []
                roleCode = request.GET['roleCode']
                myGroup = Group.objects.get(name=roleCode)
                groupPerms = myGroup.permissions.all()
                perms = []
                for groupPerm in groupPerms:
                    perms.append("Draw_Process." + str(groupPerm.codename))
                permissions = MenuPermission.objects.values('perm')
                for permission in permissions:
                    perm = permission['perm']
                    if perm in perms:
                        perms_list.append(perm)
            except Exception:
                perms_list = []
            return JsonResponse({"list": menus_list,"perms":perms_list})
    else:
        return render(request, "login.html")

@csrf_exempt
def editRoleCommanderAuth(request):
    if 'username' in request.session and 'password' in request.session:
        if request.method == 'POST':
            username = request.session['username']
            per_json = {}
            organizations = Organization.objects.distinct().filter(status=1).values('organization')
            folder_list = []
            id = 1
            permissions = []
            for organization in organizations:
                organization_json = {}
                organization_name = organization['organization']
                organization_json['name'] = organization_name
                organization_json['pId'] = "0"
                organization_json['id'] = str(id)
                organization_id = str(id)
                id+=1
                organization_json['title'] = organization_name
                organization_perm = "Draw_Process.views_folder_" + organization_name.replace(" ","")
                organization_json['perm'] = organization_perm
                permissions.append(organization_perm)
                folder_list.append(organization_json)
                companies = Company.objects.distinct().filter(organization__organization=organization_name,status=1).values('company')
                for company in companies:
                    company_json = {}
                    company_name = company['company']
                    company_json['name'] = company_name
                    company_json['pId'] = organization_id
                    company_json['id'] = str(id)
                    company_id = str(id)
                    id+=1
                    company_json['title'] = company_name
                    company_perm = "Draw_Process.views_folder_" + organization_name.replace(" ","") + "\\" + company_name.replace(" ", "")
                    company_json['perm'] = company_perm
                    permissions.append(company_perm)
                    folder_list.append(company_json)
                    departments = Department.objects.distinct().filter(company__organization__organization=organization_name,company__company=company_name,status=1).values('department_code', 'parent_code', 'department_name')
                    for department in departments:
                        department_json = {}
                        department_name = department['department_name']
                        department_json['name'] = department_name
                        pId = department['parent_code']
                        department_code = department['department_code']
                        usernames_list = AuthMessage.objects.filter(department_id=department_code).values('username')
                        for i in range(len(usernames_list)):
                            username_json = {}
                            username = str(usernames_list[i]['username'])
                            username_json['id'] = str(department_code) + "-" + str(i + 1)
                            username_json['pId'] = department_code
                            username_json['title'] = username
                            username_json['name'] = username
                            user_perm = "Draw_Process.views_user_" + username
                            username_json['perm'] = user_perm
                            permissions.append(user_perm)
                            folder_list.append(username_json)
                            view_json = {}
                            view_json['id'] = str(department_code) + "-" + str(i + 1) + "-0"
                            view_json['pId'] = str(department_code) + "-" + str(i + 1)
                            view_json['title'] = "View Task"
                            view_json['name'] = "View Task"
                            view_perm = "Draw_Process.views_commander_" + username + "_view_task"
                            view_json['perm'] = view_perm
                            permissions.append(view_perm)
                            folder_list.append(view_json)
                            assign_json = {}
                            assign_json['id'] = str(department_code) + "-" + str(i + 1) + "-1"
                            assign_json['pId'] = str(department_code) + "-" + str(i + 1)
                            assign_json['title'] = "Assign Task"
                            assign_json['name'] = "Assign Task"
                            assign_perm = "Draw_Process.views_commander_" + username + "_assign_task"
                            assign_json['perm'] = assign_perm
                            permissions.append(assign_perm)
                            folder_list.append(assign_json)
                            schedule_json = {}
                            schedule_json['id'] = str(department_code) + "-" + str(i + 1) + "-2"
                            schedule_json['pId'] = str(department_code) + "-" + str(i + 1)
                            schedule_json['title'] = "Schedule Task"
                            schedule_json['name'] = "Schedule Task"
                            schedule_perm = "Draw_Process.views_commander_" + username + "_schedule_task"
                            schedule_json['perm'] = schedule_perm
                            permissions.append(schedule_perm)
                            folder_list.append(schedule_json)
                        if int(pId) == 0:
                            department_json['pId'] = company_id
                            department_perm = "Draw_Process.views_folder_" + organization_name.replace(" ","") + "\\" + company_name.replace(" ", "") + "\\" + department_name.replace(" ", "")
                            department_json['perm'] = department_perm
                            permissions.append(department_perm)
                        else:
                            department_json['pId'] = pId
                            folder = department_name.replace(" ", "")
                            while int(pId) != 0:
                                department_tuple = Department.objects.filter(department_code=pId).values('parent_code', 'department_name')
                                pId = department_tuple[0]['parent_code']
                                upper_department_name = department_tuple[0]['department_name']
                                folder = upper_department_name.replace(" ", "") + "\\" + folder
                            department_json['perm'] = "Draw_Process.views_folder_" + organization_name.replace(" ","") + "\\" + company_name.replace(" ", "") + "\\" + folder
                        department_json['id'] = department_code
                        department_json['title'] = department_name
                        folder_list.append(department_json)
            try:
                perms_list = []
                roleCode = request.GET['roleCode']
                myGroup = Group.objects.get(name=roleCode)
                groupPerms = myGroup.permissions.all()
                perms = []
                for groupPerm in groupPerms:
                    perms.append("Draw_Process." + str(groupPerm.codename))
                for permission in permissions:
                    if permission in perms:
                        perms_list.append(permission)
            except Exception:
                perms_list = []
            return JsonResponse({"list": folder_list,"perms":perms_list})
    else:
        return render(request, "login.html")

@csrf_exempt
def editRoleFunctionAuth(request):
    if 'username' in request.session and 'password' in request.session:
        if request.method == 'POST':
            username = request.session['username']
            functions = FunctionPermission.objects.values('module')
            functions_list_new = []
            functions_name_list = []
            for i in functions:
                if i['module'] not in functions_name_list:
                    functions_name_list.append(i['module'])
                    functions_list_new.append(i)
            functions = functions_list_new
            functions_list = []
            for function in functions:
                function_json = {}
                functions_childs = []
                module = function['module']
                function_json['name'] = gettext(module)
                function_json['pId'] = "0"
                function_json['title'] = gettext(module)
                if module == "Main Function":
                    perm = "main_function"
                elif module == "General Module":
                    perm = "general_module"
                elif module == "Mouse&Keyboard":
                    perm = "mouse&keyboard"
                elif module == "SAP":
                    perm = "sap"
                elif module == "Excel Module":
                    perm = "excel_module"
                elif module == "File Module":
                    perm = "file_module"
                elif module == "Access Module":
                    perm = "access_module"
                elif module == "Web Module":
                    perm = "web_module"
                elif module == "Mail":
                    perm = "mail"
                elif module == "HCI Module":
                    perm = "hci_module"
                elif module == "AI Module":
                    perm = "ai_module"
                elif module == "Self Development":
                    perm = "self_development"
                function_json['perm'] = perm
                childrens = FunctionPermission.objects.distinct().filter(module=module).values('function','perm')
                childrens_list = []
                for children in childrens:
                    children_json = {}
                    function = children['function']
                    children_json['name'] = gettext(function)
                    children_json['pId'] = "1"
                    children_json['title'] = gettext(function)
                    children_json['perm'] = children['perm']
                    childrens_list.append(children_json)
                function_json['children'] = childrens_list
                functions_list.append(function_json)
            ctrlName_en = request.POST.get('ctrlName_en')
            try:
                perms_list = []
                roleCode = request.GET['roleCode']
                myGroup = Group.objects.get(name=roleCode)
                groupPerms = myGroup.permissions.all()
                perms = []
                for groupPerm in groupPerms:
                    perms.append("Draw_Process." + str(groupPerm.codename))
                permissions = FunctionPermission.objects.values('perm')
                for permission in permissions:
                    perm = permission['perm']
                    if perm in perms:
                        perms_list.append(perm)
            except:
                perms_list = []
            return JsonResponse({"list": functions_list,"perms":perms_list})
    else:
        return render(request, "login.html")