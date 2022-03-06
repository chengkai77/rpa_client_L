# -*- coding: utf-8 -*-
from django.db import models


# Create your models here.
class Actions(models.Model):
    div_id = models.CharField(max_length=255, blank=True, null=True)
    node_no = models.IntegerField(blank=True, null=True)
    function = models.CharField(max_length=255)
    name = models.CharField(max_length=255, blank=True, null=True)
    last_node = models.CharField(max_length=255, blank=True, null=True)
    next_node = models.CharField(max_length=255, blank=True, null=True)
    input = models.CharField(max_length=255, blank=True, null=True)
    output = models.CharField(max_length=255, blank=True, null=True)
    variant = models.CharField(max_length=1000, blank=True, null=True)
    public_variant = models.CharField(max_length=1000, blank=True, null=True)
    create_on = models.DateTimeField()
    create_by = models.CharField(max_length=255)
    group = models.CharField(max_length=255, blank=True, null=True)
    group_id = models.CharField(max_length=255, blank=True, null=True)
    group_node_no = models.IntegerField(blank=True, null=True)
    group_source_type = models.CharField(max_length=255, blank=True, null=True)
    group_target_type = models.CharField(max_length=255, blank=True, null=True)
    group_left = models.CharField(max_length=255, blank=True, null=True)
    group_top = models.CharField(max_length=255, blank=True, null=True)
    version = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=255, blank=True, null=True)
    tab = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'actions'


from django.contrib.auth.models import AbstractUser


class AuthMessage(AbstractUser):
    fixed_ip = models.CharField(max_length=255, blank=True, null=True)
    ip = models.CharField(max_length=255, blank=True, null=True)
    sex = models.CharField(max_length=1, blank=True, null=True)
    mobile = models.CharField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=255, blank=True, null=True)
    signature = models.CharField(max_length=255, blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    image_url = models.CharField(max_length=255, blank=True, null=True)
    update_date = models.DateField(blank=True, null=True)
    operator = models.CharField(max_length=255, blank=True, null=True)
    nickname = models.CharField(max_length=255, blank=True, null=True)  # �ǳ�
    department = models.ForeignKey('Department', on_delete=models.SET_NULL, blank=True, null=True)
    licence_date = models.DateField(blank=True, null=True)  #用户期限
    user_type_level = (
        (1, '免费用户'),
        (2, '付费用户类型1'),
        (3, '付费用户类型2'),
        (4, '付费用户类型3'),
        (5, '企业用户'),
    )
    userlevel = models.IntegerField(choices=user_type_level, default=1)



    class Meta:
        managed = True
        db_table = 'Users'


class Company(models.Model):
    organization = models.ForeignKey('Organization', on_delete=models.CASCADE)
    company = models.CharField(max_length=255)
    status = models.CharField(max_length=1)
    remarks = models.CharField(max_length=500, blank=True, null=True)
    create_on = models.DateTimeField()
    create_by = models.CharField(max_length=64)

    class Meta:
        managed = True
        db_table = 'company'


class Department(models.Model):
    department_code = models.CharField(primary_key=True, max_length=64)
    company = models.ForeignKey('Company', models.CASCADE)
    parent_code = models.CharField(max_length=64)
    parent_codes = models.CharField(max_length=1000)
    tree_sort = models.DecimalField(max_digits=10, decimal_places=0)
    tree_sorts = models.CharField(max_length=1000)
    tree_leaf = models.CharField(max_length=1)
    tree_level = models.DecimalField(max_digits=4, decimal_places=0)
    tree_names = models.CharField(max_length=1000)
    department_name = models.CharField(max_length=100)
    full_name = models.CharField(max_length=200)
    status = models.CharField(max_length=1)
    remarks = models.CharField(max_length=500, blank=True, null=True)
    create_on = models.DateTimeField()
    create_by = models.CharField(max_length=64)

    class Meta:
        managed = True
        db_table = 'department'


class Folder(models.Model):
    folder = models.CharField(max_length=1000)
    create_on = models.DateTimeField()
    create_by = models.CharField(max_length=64)

    class Meta:
        managed = True
        db_table = 'folder'


class FunctionPermission(models.Model):
    id = models.IntegerField(primary_key=True)
    module = models.CharField(max_length=255)
    function = models.CharField(max_length=255, blank=True, null=True)
    permission = models.CharField(max_length=255, blank=True, null=True)
    perm = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'function_permission'
        unique_together = (('id', 'module'),)


class MenuPermission(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=255)
    child_name1 = models.CharField(max_length=255, blank=True, null=True)
    child_name2 = models.CharField(max_length=255, blank=True, null=True)
    child_name3 = models.CharField(max_length=255, blank=True, null=True)
    child_name4 = models.CharField(max_length=255, blank=True, null=True)
    permission = models.CharField(max_length=255, blank=True, null=True)
    perm = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'menu_permission'
        unique_together = (('id', 'name'),)


class Organization(models.Model):
    organization = models.CharField(max_length=255)
    status = models.CharField(max_length=1)
    remarks = models.CharField(max_length=500, blank=True, null=True)
    create_on = models.DateTimeField()
    create_by = models.CharField(max_length=64)

    class Meta:
        managed = True
        db_table = 'organization'


class Packages(models.Model):
    function = models.CharField(max_length=255)
    package = models.CharField(max_length=255)
    codes = models.CharField(max_length=1000, blank=True, null=True)
    codes_1 = models.CharField(max_length=1000, blank=True, null=True)
    codes_2 = models.CharField(max_length=1000, blank=True, null=True)
    codes_3 = models.CharField(max_length=1000, blank=True, null=True)
    codes_4 = models.CharField(max_length=1000, blank=True, null=True)
    codes_5 = models.CharField(max_length=1000, blank=True, null=True)
    codes_6 = models.CharField(max_length=1000, blank=True, null=True)
    module = models.CharField(max_length=255)


    class Meta:
        managed = True
        db_table = 'packages'


class PanelPermission(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    child_name1 = models.CharField(max_length=255, blank=True, null=True)
    child_name2 = models.CharField(max_length=255, blank=True, null=True)
    child_name3 = models.CharField(max_length=255, blank=True, null=True)
    child_name4 = models.CharField(max_length=255, blank=True, null=True)
    permission = models.CharField(max_length=255, blank=True, null=True)
    perm = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'panel_permission'


class ProcessCopy(models.Model):
    div_id = models.CharField(max_length=255, blank=True, null=True)
    function = models.CharField(max_length=255)
    input = models.CharField(max_length=255, blank=True, null=True)
    output = models.CharField(max_length=255, blank=True, null=True)
    variant = models.CharField(max_length=1000, blank=True, null=True)
    public_variant = models.CharField(max_length=1000, blank=True, null=True)
    create_on = models.DateTimeField()
    create_by = models.CharField(max_length=255)

    class Meta:
        managed = True
        db_table = 'process_copy'


class Rolelist(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=255)
    description = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'rolelist'
        unique_together = (('id', 'name'),)


class SelectInformation(models.Model):
    function = models.CharField(max_length=255)
    variant = models.CharField(max_length=255)
    value = models.CharField(max_length=255)
    text = models.CharField(max_length=255)
    choose = models.CharField(max_length=1)

    class Meta:
        managed = True
        db_table = 'select_information'


class Store(models.Model):
    type = models.CharField(max_length=255)
    file_name = models.CharField(max_length=1000)
    node_no = models.IntegerField(blank=True, null=True)
    source_id = models.CharField(max_length=255, blank=True, null=True)
    target_id = models.CharField(max_length=255, blank=True, null=True)
    source_type = models.CharField(max_length=255, blank=True, null=True)
    target_type = models.CharField(max_length=255, blank=True, null=True)
    jnode_class = models.CharField(max_length=1000, blank=True, null=True)
    jnode = models.CharField(max_length=1000, blank=True, null=True)
    jnode_html = models.CharField(max_length=1000, blank=True, null=True)
    left = models.CharField(max_length=255, blank=True, null=True)
    top = models.CharField(max_length=255, blank=True, null=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    input = models.CharField(max_length=255, blank=True, null=True)
    output = models.CharField(max_length=255, blank=True, null=True)
    variant = models.CharField(max_length=1000, blank=True, null=True)
    public_variant = models.CharField(max_length=1000, blank=True, null=True)
    create_on = models.DateTimeField()
    create_by = models.CharField(max_length=255)
    group = models.CharField(max_length=255, blank=True, null=True)
    group_id = models.CharField(max_length=255, blank=True, null=True)
    group_node_no = models.IntegerField(blank=True, null=True)
    group_node_name = models.CharField(max_length=255, blank=True, null=True)
    group_source_type = models.CharField(max_length=255, blank=True, null=True)
    group_target_type = models.CharField(max_length=255, blank=True, null=True)
    group_left = models.CharField(max_length=255, blank=True, null=True)
    group_top = models.CharField(max_length=255, blank=True, null=True)
    version = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'store'


class SysArea(models.Model):
    area_code = models.TextField(blank=True, null=True)
    parent_code = models.CharField(max_length=192, blank=True, null=True)
    parent_codes = models.TextField(blank=True, null=True)
    tree_sort = models.BigIntegerField(blank=True, null=True)
    tree_sorts = models.TextField(blank=True, null=True)
    tree_leaf = models.CharField(max_length=3, blank=True, null=True)
    tree_level = models.BigIntegerField(blank=True, null=True)
    tree_names = models.TextField(blank=True, null=True)
    area_name = models.TextField(blank=True, null=True)
    area_type = models.CharField(max_length=3, blank=True, null=True)
    status = models.CharField(max_length=3, blank=True, null=True)
    create_by = models.CharField(max_length=192, blank=True, null=True)
    create_date = models.DateField(blank=True, null=True)
    update_by = models.CharField(max_length=192, blank=True, null=True)
    update_date = models.DateField(blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'sys_area'


class SysRole(models.Model):
    role_code = models.CharField(max_length=192, blank=True, null=True)
    role_name = models.TextField(blank=True, null=True)
    role_type = models.TextField(blank=True, null=True)
    role_sort = models.BigIntegerField(blank=True, null=True)
    is_sys = models.CharField(max_length=3, blank=True, null=True)
    user_type = models.CharField(max_length=48, blank=True, null=True)
    status = models.CharField(max_length=3, blank=True, null=True)
    create_by = models.CharField(max_length=192, blank=True, null=True)
    create_on = models.DateTimeField(blank=True, null=True)
    update_by = models.CharField(max_length=192, blank=True, null=True)
    update_on = models.DateTimeField(blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)
    organization = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'sys_role'


class TaskInformation(models.Model):
    pc_name = models.CharField(max_length=255, blank=True, null=True)
    sequence = models.FloatField(blank=True, null=True)
    task_name = models.CharField(max_length=255, blank=True, null=True)
    file_path = models.CharField(max_length=255, blank=True, null=True)
    file_name = models.CharField(max_length=255, blank=True, null=True)
    duration = models.CharField(max_length=255, blank=True, null=True)
    method = models.CharField(max_length=255, blank=True, null=True)
    notification = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=255, blank=True, null=True)
    booked_time = models.DateTimeField(blank=True, null=True)
    start_time = models.DateTimeField(blank=True, null=True)
    end_time = models.DateTimeField(blank=True, null=True)
    create_on = models.DateTimeField()
    create_by = models.CharField(max_length=255)
    ip_address = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'task_information'


class TaskResult(models.Model):
    pc_name = models.CharField(max_length=255, blank=True, null=True)
    task_name = models.CharField(max_length=255, blank=True, null=True)
    file_path = models.CharField(max_length=255)
    file_name = models.CharField(max_length=255, blank=True, null=True)
    result = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=255, blank=True, null=True)
    step = models.CharField(max_length=255, blank=True, null=True)
    message = models.TextField(blank=True, null=True)
    start_time = models.DateTimeField(blank=True, null=True)
    end_time = models.DateTimeField(blank=True, null=True)
    create_on = models.DateTimeField()
    create_by = models.CharField(max_length=255)
    ip_address = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'task_result'


class Function(models.Model):
    id = models.IntegerField(primary_key=True)
    functionname = models.CharField(max_length=255)
    estimate_time = models.IntegerField(blank=True,null=True )

    class Meta:
        managed = True
        db_table = 'function'

class RobotInfo(models.Model):
    user = models.OneToOneField(AuthMessage, on_delete=models.CASCADE)
    robot_name = models.CharField(max_length=255,blank=True, null=True)
    robot_status_type_choices = (
        (1, '离线'),
        (2, '在线空闲'),
        (3, '在线忙碌'),
    )
    robot_status = models.IntegerField(choices=robot_status_type_choices, default=1)
    schedule = models.FloatField(blank=True, null=True)
    mac = models.CharField(max_length=255,blank=True, null=True)
    file_path = models.CharField(max_length=255, blank=True, null=True)
    reverse1 = models.CharField(max_length=255,blank=True, null=True)
    reverse2 = models.CharField(max_length=255, blank=True, null=True)
    reverse3  = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'robot_info'



