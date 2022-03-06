import os
import shutil
from Draw_Process.models import AuthMessage

def xstr(s):
    if s is None:
        return ''
    else:
        return s
def deletePath(path):
    try:
        os.remove(path)
    except:
        try:
            os.rmdir(path)
        except:
            shutil.rmtree(path)

from Draw_Process.models import Department
from Draw_Process.models import Company
from django.contrib.auth.models import Permission


#删除组织下面的所有公司权限表
def deleteOrganizationReleatedCompany(organization):
    companies = Company.objects.filter(organization=organization).values('company')
    for company_json in companies:
        company = company_json['company']
        try:
            organization = Company.objects.filter(company=company).values('organization')[0]['organization']
            folder = organization.replace(" ", "") + "\\" + company.replace(" ", "")
            Permission.objects.filter(name=folder).delete()
            deleteDepartment = deleteCompanyReleatedDepartment(company)
            if deleteDepartment == "success":
                return "success"
            else:
                return "failed"
        except Exception as e:
            ex = str(e)
            return "failed"


def deleteCompanyReleatedDepartment(company):
    departments = Department.objects.filter(company=company).values('department_code')
    for department in departments:
        departmentCode = department['department_code']
        try:
            department_tupe = Department.objects.all().filter(department_code=departmentCode).values('parent_code',
                                                                                                     'parent_codes',
                                                                                                     'tree_leaf',
                                                                                                     'organization',
                                                                                                     'company',
                                                                                                     'department_name')
            treeLeaf = int(department_tupe[0]['tree_leaf'])
            parentCode = department_tupe[0]['parent_code']
            departmentName = department_tupe[0]['department_name']
            organization = department_tupe[0]['organization']
            company = department_tupe[0]['company']
            topDepartmentCode = parentCode
            folder_path = departmentName.replace(" ", "")
            while topDepartmentCode != "0":
                department_tuple = Department.objects.filter(department_code=topDepartmentCode).values('parent_code',
                                                                                                       'department_name')
                topDepartmentCode = department_tuple[0]['parent_code']
                department_name = department_tuple[0]['department_name']
                folder_path = department_name.replace(" ", "") + "\\" + folder_path
            folder = organization.replace(" ", "") + "\\" + company.replace(" ", "") + "\\" + folder_path

            Permission.objects.filter(name=folder).delete()
            if treeLeaf == 0:
                parentCodes = parentCode + ',' + departmentCode + ','
                Department.objects.filter(parent_codes__icontains=parentCodes).delete()
            Department.objects.filter(department_code=departmentCode).delete()
            if len(Department.objects.all().filter(parent_code=parentCode).values('department_code')) == 0:
                Department.objects.all().filter(department_code=parentCode).update(tree_leaf=1)
            return "success"
        except Exception:
            return "failed"



def organizationAuth(username,auth,language):
    user = AuthMessage.objects.get(username=username)
    perms = AuthMessage.get_all_permissions(user)
    json = {}
    json['perms'] = perms
    json['language'] = language
    if auth in perms:
        json['organization'] = ''
        json['readonly'] = ''
    else:
        organization = user.department.company.organization.organization
        json['organization'] = organization
        json['readonly'] = 'readonly'
    return json

def companyAuth(username,auth1,auth2,language):
    user = AuthMessage.objects.get(username=username)
    perms = AuthMessage.get_all_permissions(user)
    json = {}
    json['perms'] = perms
    json['language'] = language
    if auth1 in perms:
        json['organization'] = ''
        json['organizationReadonly'] = ''
    else:
        organization = user.department.company.organization.organization
        json['organization'] = organization
        json['organizationReadonly'] = 'readonly'
    if auth2 in perms:
        json['company'] = ''
        json['companyReadonly'] = ''
    else:
        company = user.department.company.company
        json['company'] = company
        json['organizationReadonly'] = 'readonly'
        json['companyReadonly'] = 'readonly'
    return json

#获取用户所在的组织
def getOrganization(username,auth):
    user = AuthMessage.objects.get(username=username)
    perms = AuthMessage.get_all_permissions(user)
    if auth in perms:
        organization = ''
    else:
        try:
            organization = AuthMessage.objects.filter(username=username).values('organization')[0]['organization']
        except:
            organization = ''
    return organization