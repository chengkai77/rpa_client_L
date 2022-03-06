"""Python_Platform URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views   import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf.urls import url
from django.contrib import admin
from django.urls import path, re_path

from Draw_Process import views
# from Testapp import  testappviews

from index import  indexviews
from Timetasks import  timetasksviews
from User import  companyviews
from User import  userviews
from User import  organizationviews
from User import  departmentview
from User import  rolesviews
from User import  Permissionvviews

from django.views.i18n import JavaScriptCatalog
from django.conf.urls.i18n import i18n_patterns
from django.urls import include, translate_url
from Client import websocketviews

urlpatterns = [
    url('i18n/',include('django.conf.urls.i18n')),
    path('jsi18n/', JavaScriptCatalog.as_view(), name='javascript-catalog'),
    path('admin/', admin.site.urls),


    #websocket app
    url(r'^websocketlink/$', websocketviews.websocketLink, name='websocketlink'),
    url(r'^commanderpage/$', websocketviews.commanderPage, name='commanderpage'),
    url(r'^commanderlist/$', websocketviews.commanderList, name='commanderlist'),
    url(r'^rpadesignstudio/$', websocketviews.rpadesignstudio, name='rpadesignstudio'),
    url(r'^saverecordvariant/$', websocketviews.saveRecordVariant, name='saverecordvariant'),
    url(r'^savepasswordvariant/$', websocketviews.savePasswordVariant, name='savepasswordvariant'),

    #create teclead user
    path('createtecleduser/', userviews.tecleadUserCreate),
    path('deletetecleduser/', userviews.tecleadUserDelete),

    #index app
    url(r'^index/$', indexviews.index, name='index'),#主页
    url(r'^index2/$', indexviews.index2, name='index2'),  # 主页
    path('welcome/', indexviews.welcome),
    path('welcome2/', indexviews.welcome2),
    path('updatelicence/', indexviews.updateLicence),
    path('checklicence/', indexviews.checkLicence),
    path('downloadprocess/', indexviews.downloadProcess),  # 下载流程
    path('getdownloadcodes/', indexviews.getDownloadCodes),  # 获取代码视图
    path('startdownloadcodes/', indexviews.startDownloadCodes),  # 下载代码视图
    path('uploadprocess/', indexviews.uploadProcess),  # 上传流程
    path('transfertoaction/', indexviews.transferToAction),  # 将上传的流程变量传输至action表


    #user app
    path('', userviews.userlogin),
    path('checklogin/', userviews.checklogin),
    url(r'^login/$', userviews.userlogin, name='login'),#登录界面
    url(r'^logout/$', userviews.logout, name='logout'),#登录界面
    url(r'getuser/$', userviews.getUser, name='getuser'), #获取用户名
    path('changepassword/', userviews.changepassword), #修改密码
    url(r'resetpassword/$', userviews.ResetPassword, name='resetpassword'), #密码重置
    path('areaselect/', userviews.areaSelect),
    path('orgaccountlist/', userviews.orgaccountList),
    path('roleaddaccountlist/', userviews.roleAddAccountList),
    path('userrolelist/', userviews.userRoleList),
    path('updateuserassign/', userviews.updateUserAssign),
    path('treeselect/', userviews.treeselect),
    path('usereditpermission/', userviews.userEditPermission),
    path('userfolderpermission/', userviews.userFolderPermission),
    path('usercommanderpermission/', userviews.userCommanderPermission),
    path('usereditassign/', userviews.userEditAssign),
    path('changetreesort/', userviews.changeTreeSort),
    path('updateinformation/', userviews.updateinformation),
    path('updateuser/', userviews.updateuser),
    path('uploaduser/', userviews.upload_user),
    url(r'orgedit/$', userviews.orgEdit, name='orgEdit'),
    url(r'canceluserauthorization/$', userviews.cancelUserAuthorization, name='canceluserauthorization'),
    url(r'cancelusersauthorization/$',userviews.cancelUsersAuthorization, name='cancelusersauthorization'),
    url(r'userdelete/$', userviews.userDelete, name='userdelete'),
    url(r'orguser/$', userviews.orgUser, name='orguser'),
    url(r'changeuserstatus/$', userviews.changeUserStatus, name='changeuserstatus'),
    path('checkuserid/', userviews.check_userId),
    path('createuserid/', userviews.createUserID),
    path('updateuserpermission/', userviews.updateUserPermission),
    path('updateusersomepermission/', userviews.updateUserSomePermission),
    path('updateuserinformation/', userviews.updateUserInformation),
    path('orguseradd/', userviews.orguseradd), #增加用户
    url(r'getfilepath/$', views.getfilepath, name='getfilepath'),
    url(r'edituserlicense/$', userviews.editUserLicense, name='edituserlicense'),  # 更改用户有效期
    url(r'editrolelicense/$', userviews.editRoleLicense, name='editrolelicense'),  # 更改角色有效期

    #user app role
    path('createrole/', rolesviews.createRole),  #创建角色
    path('updaterole/', rolesviews.updateRole),  #更新角色
    url(r'orgroleedit/$', rolesviews.orgRoleEdit, name='orgroleedit'),#编辑角色
    url(r'roledelete/$', rolesviews.roleDelete, name='roledelete'), #删除角色
    path('roleaccountlist/', rolesviews.roleAccountList),
    path('rolelist/', rolesviews.roleList),
    path('rolelist/', rolesviews.role_selection),
    path('roleeditpermission/', rolesviews.roleEditPermission),
    path('rolefolderpermission/', rolesviews.roleFolderPermission),
    path('rolecommanderpermission/', rolesviews.roleCommanderPermission),
    path('orgroleadd/', rolesviews.orgroleadd),
    path('roleadduser/', rolesviews.roleAddUser),
    url(r'orgrole/$', rolesviews.orgRole, name='orgrole'),
    url(r'roleassign/$', rolesviews.roleAssign, name='roleassign'),
    url(r'changerolestatus/$', rolesviews.changeRoleStatus, name='changerolestatus'),
    url(r'rolesaveuseradd/$', rolesviews.roleSaveUserAdd, name='rolesaveuseradd'),
    path('updaterolepermission/', rolesviews.updateRolePermission),
    path('updaterolesomepermission/', rolesviews.updateRoleSomePermission),

    #user app organization
    path('organizationselect/', organizationviews.organizationSelect),
    url(r'updateorganization/$', organizationviews.updateOrganization, name='updateorganization'),
    url(r'orgorganization/$', organizationviews.orgOrganization, name='orgorganization'),
    path('orgorglist/', organizationviews.orgOrganizationList),
    url(r'changeorganizationstatus/$', organizationviews.changeOrganizationStatus, name='changeorganizationstatus'),
    path('organizationadd/', organizationviews.organizationAdd),
    path('checkorganization/', organizationviews.checkOrganization),
    path('createorganization/', organizationviews.createOrganization),
    url(r'deleteorganization/$', organizationviews.deleteOrganization, name='deleteorganization'),

    #user app company
    path('checkcompany/', companyviews.checkCompany),
    path('createcompany/', companyviews.createCompany),
    path('companyadd/', companyviews.companyAdd),
    path('orgcomlist/', companyviews.orgCompanyList),
    url(r'deletecompany/$', companyviews.deleteCompany, name='deletecompany'),
    path('companyselect/', companyviews.companySelect),
    url(r'orgcompany/$', companyviews.orgCompany, name='orgcompany'),
    url(r'changecompanystatus/$', companyviews.changeCompanyStatus, name='changecompanystatus'),
    url(r'updatecompany/$', companyviews.updateCompany, name='updatecompany'),

    # user app department
    path('createdepartment/', departmentview.createDepartment),
    url(r'deletedepartment/$', departmentview.deleteDepartment, name='deletedepartment'),
    path('deplist/', departmentview.departmentList),
    path('departmentadd/', departmentview.departmentAdd),
    path('departmentselect/', departmentview.departmentSelect),
    url(r'orgdepartment/$', departmentview.orgDepartment, name='orgdepartment'),
    url(r'updatedepartment/$', departmentview.updateDepartment, name='updatedepartment'),
    url(r'changedepartmentstatus/$', departmentview.changeDepartmentStatus, name='changedepartmentstatus'),

    #usr app permission
    url(r'editusermenuauth/$', Permissionvviews.editUserMenuAuth, name='editusermenuauth'),
    url(r'edituserpanelauth/$', Permissionvviews.editUserPanelAuth, name='edituserpanelauth'),
    url(r'edituserfolderauth/$', Permissionvviews.editUserFolderAuth, name='edituserfolderauth'),
    url(r'edituserfunctionauth/$', Permissionvviews.editUserFunctionAuth, name='edituserfunctionauth'),
    url(r'editusercommanderauth/$', Permissionvviews.editUserCommanderAuth, name='editusercommanderauth'),
    url(r'editrolemenuauth/$', Permissionvviews.editRoleMenuAuth, name='editrolemenuauth'),
    url(r'editrolefunctionauth/$', Permissionvviews.editRoleFunctionAuth, name='editrolefunctionauth'),
    url(r'editrolepanelauth/$', Permissionvviews.editRolePanelAuth, name='editrolepanelauth'),
    url(r'editrolefolderauth/$', Permissionvviews.editRoleFolderAuth, name='editrolefolderauth'),
    url(r'editrolecommanderauth/$', Permissionvviews.editRoleCommanderAuth, name='editrolecommanderauth'),

    #draw process app
    url(r'getrobotcode/$', views.getRobotCode, name='getrobotcode'),
    url(r'before/$',views.before, name='before'),
    url(r'getcodes/$', views.getCodes, name='getcodes'),
    url(r'changevariant/$',views.changevariant, name='changevariant'),
    url(r'filejudge/$',views.fileJudge, name='filejudge'),
    url(r'createfolder/$', views.createFolder, name='createfolder'),
    url(r'releasejudge/$', views.releaseJudge, name='releasejudge'),
    url(r'deleteprocess/$',views.deleteProcess, name='deleteprocess'),
    url(r'drawprocess/$',views.drawProcess, name='drawprocess'),
    url(r'showprocess/$', views.showProcess, name='showprocess'),
    url(r'saveprocess/$',views.saveProcess, name='saveprocess'),
    url(r'savevariant/$',views.saveVariant, name='savevariant'),
    url(r'getname/$',views.getName, name='getname'),
    url(r'processnames/$',views.processNames, name='processnames'),
    url(r'sortvariant/$',views.sortVariant, name='sortvariant'),
    # url(r'showinfo/$', views.showVariantInfo, name='showinfo'),
    #url(r'showvariant/$', views.showVariant, name='showvariant'),
    url(r'deletevariant/$',views.deleteVariant, name='deletevariant'),
    url(r'batchdelete/$', views.batchDelete, name='batchdelete'),
    url(r'deleteaction/$',views.deleteAction, name='deleteaction'),
    url(r'publicvariant/$',views.publicvariant, name='publicvariant'),
    url(r'processvariant/$',views.processvariant, name='processvariant'),
    url(r'publictransfer/$',views.publictransfer, name='publictransfer'),
    url(r'transfervariant/$',views.transfervariant, name='transfervariant'),
    path('getalerts/', views.getalerts),
    url(r'saveinsertvariant/$', views.saveProcessVariant, name='saveinsertvariant'),
    url(r'updateinsertvariant/$', views.updateProcessVariant, name='updateinsertvariant'),
    url(r'creatediv/$', views.createDiv, name='creatediv'),
    url(r'savediv/$', views.saveDiv, name='savediv'),
    #url(r'searchdiv/$', views.searchDiv, name='searchdiv'),
    url(r'saveconnection/$', views.saveConnection, name='saveconnection'),
    path('pyfile/', views.export),
    path('datalist/', views.datalist),
    path('datalist3/', views.datalist3),
    path('taskdelete/', views.taskdelete),
    path('movefile/', views.movefile),
    path('openfile/', views.openfile),
    path('releasefile/', views.releasefile),
    path('releasecopy/', views.releaseCopy),
    path('browseradd/', views.browseradd),
    path('getvars/', views.getvars),
    path('imageclip/', views.imageclip),
    path('timesleep/', views.time_sleep),
    path('groupsteps/', views.groupSteps),
    path('breakupsteps/', views.breakUpSteps),
    path('judgesubprocess/', views.judgeSubProcess),

    #定时任务
    path('tasklist/', timetasksviews.tasklist),
    path('getrobotlist/', timetasksviews.getrobotlist),
    path('bookedlist/', timetasksviews.bookedList),
    path('bookedschedule/', timetasksviews.bookedschedule),
    path('finishedschedule/', timetasksviews.finishedschedule),
    path('finishedlist/', timetasksviews.finishedList),
    path('taskcreateor/', timetasksviews.taskcreateor),
    path('booktask/', timetasksviews.booktask),
    url(r'minuteoption/$', timetasksviews.minuteoption, name='minuteoption'),
    url(r'houroption/$', timetasksviews.houroption, name='houroption'),
    url(r'^startfuturetask/$', timetasksviews.startFutureTask, name='startfuturetask'),
    path('receivebookedtask/', timetasksviews.receiveBookedTask),
    path('datalist2/', timetasksviews.datalist2),
    path('checktitle/', timetasksviews.checktitle),
    path('getbookedtask/', timetasksviews.getBookedTask),
    url(r'updatefinishedtask/$', timetasksviews.updateFinishedTask, name='updatefinishedtask'),
    url(r'deletefinishedtask/$', timetasksviews.deleteFinishedTask, name='deletefinishedtask'),
    url(r'deletebookedtask/$', timetasksviews.deleteBookedTask, name='deletebookedtask'),
    url(r'schedulecyclehtml/$', timetasksviews.scheduleCycleHtml, name='schedulecyclehtml'),


   # #test app
   #  url(r'target/$', testappviews.target, name='target'),
   #  url(r'webtar/$', testappviews.webTarget, name='webtar'),
   #  path('starttask/', testappviews.starttask),
   #  path('runtask/', testappviews.runtask),
   #  url(r'run/$', testappviews.run, name='run'),
]
from django.conf.urls import static
from Python_Platform import settings
urlpatterns += static.static(settings.STATIC_URL,document_root=settings.STATIC_ROOT)