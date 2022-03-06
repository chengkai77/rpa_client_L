# -*-coding:utf-8 -*-
import os
import time

from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime
import json
from Draw_Process.models import AuthMessage
from Draw_Process.models import TaskResult
from django.core import serializers
import traceback
from django.shortcuts import render, redirect
from Draw_Process.models import TaskInformation
# Create your views here.
#client redict here when it finished the booked task
from Email import send_mail
from django.utils.translation import gettext
import requests
from Draw_Process.models import SysRole
from Draw_Process.utils import get_tasklist
from Python_Platform import settings
import Client.websocketviews  #当前的机器人客户端
from Draw_Process.models import RobotInfo
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
import datetime
from pytz import utc
import logging
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR


book_time_json = {}
logger = logging.getLogger('log')
def my_job(id='my_job'): print(id, '-->', datetime.datetime.now())
def my_listener(event):
    if event.exception:
        print ('任务出错了！！！！！！')
    else:
        print ('任务照常运行...')

def aps_testadd(x,y):
    print (datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), x)
    return  x+y


from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore


def aps_test(x):
    print (datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), x)

def get_week_day(date):
    week_day_dict = {
        0 : 'monday',
        1 : 'tuesday',
        2 : 'wednesday',
        3 : 'thursday',
        4 : 'friday',
        5 : 'saturday',
        6 : 'sunday',
    }
    day = date.weekday()
    return week_day_dict[day]

#服务器重启了，一些未来的任务需要重新加入队列里面
def ResumAllTask():
    jobs=scheduler.get_jobs()
    schedules = []
    if len(jobs)==0:
        now_time = datetime.datetime.now()
        mappings = TaskInformation.objects.distinct().filter( booked_time__gte=now_time).order_by( 'booked_time', 'sequence')
        mappings_list = serializers.serialize('json', mappings)
        mappings_array = json.loads(mappings_list)
        if len(mappings_array)>0:
            for i in range(len(mappings_array)):
                filePath = settings.File_Root + "\\Draw_Process\\pyfile\\" + mappings_array[i]['fields']['file_path']
                code = ""
                with open(filePath, 'r', encoding='utf-8') as f:  # 读文件代码
                    code_list = f.readlines()
                for code_item in code_list:
                    code = code + code_item
                taskname = mappings_array[i]['fields']['task_name']
                robotname = mappings_array[i]['fields']['pc_name']
                booked_time = mappings_array[i]['fields']['booked_time']
                try:
                    booked_time2 = datetime.datetime.strptime(booked_time, '%Y-%m-%dT%H:%M:%S')  # str->datetime，预定的时间
                    now_time = datetime.datetime.now()  # 当前时间
                    time_diff = (booked_time2 - now_time).total_seconds()
                except Exception as  e:
                    error = str(e)
                    time_diff = 30
                scheduler.add_job(func=taskDoing, args=(taskname, robotname, code,),
                                  next_run_time=datetime.datetime.now() + datetime.timedelta(seconds=time_diff))
                logger.info('服务器重启了，定时任务未来任务重新加入任务队列')

#启动服务器更新所有的机器人的状态为离线
def  initRobotStatus():
    RobotInfo.objects.all().update(robot_status=1)





def my_job(id='my_job'):
    print(id, '-->', datetime.datetime.now())
jobstores = {
'default': SQLAlchemyJobStore(url='sqlite:///Schudejob.sqlite')
}

executors = {

'default': ThreadPoolExecutor(20),
'processpool': ProcessPoolExecutor(10)
}

job_defaults = {

'coalesce': False,
'max_instances': 3,
'misfire_grace_time': 864000   #10 day
}

scheduler = BackgroundScheduler(jobstores=jobstores, executors=executors, job_defaults=job_defaults)
#scheduler.add_job(my_job, args=['job_interval12121', ], id='job_interval', trigger='interval', seconds=5,replace_existing=True)
#scheduler.add_job(my_job, args=['job_date_once', ], id='job_date_once8', trigger='date', run_date='2020-11-19 13:37:05')
scheduler.add_job(func=ResumAllTask, next_run_time=datetime.datetime.now() + datetime.timedelta(seconds=2)) #开服务器后检查任务表中是否有未来任务
scheduler.add_job(func=initRobotStatus, next_run_time=datetime.datetime.now() + datetime.timedelta(seconds=1)) #开服务器后检查机器人状态，全部设置为1

#scheduler.add_job(func=aps_testadd,args=( 5,6,),trigger='cron',second='12/5') #从12s 开始
#scheduler.add_listener(my_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
#scheduler.add_job(my_job, args=['job_interval12121', ], id='job_interval', trigger='interval', seconds=5,replace_existing=True)

scheduler.start()







#获取某个机器人的过期最严重的任务
def getexpiredesttask(robotname):
    logger.info('（0）-------过期的任务-----' + '' + robotname )
    now_time = datetime.datetime.now()
    robot_tupe = RobotInfo.objects.filter(robot_name=robotname)
    robot_list = serializers.serialize('json', robot_tupe)
    robot_array = json.loads(robot_list)
    field = robot_array[0]['fields']
    robotstatus = field['robot_status']  # 机器人状态
    if (robotstatus == 2):  # 分配的机器人在线空闲，可以执行
        RobotInfo.objects.filter(robot_name=robotname).update(robot_status=3)
        logger.info('（1）-------过期的任务-----'  + '' + robotname + "设置机器人忙碌---")

        mappings = TaskInformation.objects.distinct().filter(pc_name=robotname, booked_time__lte=now_time).order_by(
            'booked_time', 'sequence')
        mappings_list = serializers.serialize('json', mappings)
        mappings_array = json.loads(mappings_list)
        if len(mappings_array) > 0:
            filePath = settings.File_Root + "\\Draw_Process\\pyfile\\" + mappings_array[0]['fields']['file_path']
            code = ""
            with open(filePath, 'r', encoding='utf-8') as f:  # 读文件代码
                code_list = f.readlines()
            for code_item in code_list:
                code = code + code_item
            taskname = mappings_array[0]['fields']['task_name']
            logger.info('（2）-------过期的任务' + taskname + '服务器代码组织完成----：' + robotname)
            taskDoing(taskname, robotname, code)
        else:
            RobotInfo.objects.filter(robot_name=robotname).update(robot_status=2)
            logger.info('（2）-------没有过期的任务-----' + '' + robotname + "设置机器人空闲---")
    elif (robotstatus == 1):
        logger.info('（1-1）------过期的任务-----'  + "------机器人不在线：" + robotname)
    else:
        logger.info('（1-2）------过期的任务-----' + "------机器人忙碌：" + robotname)




#任务指派给某个用户的机器人
def taskassigntoRoboot(taskname,rootname,book_time):
    logger.info('（0）------触发任务-----'+taskname + "------机器人名字：" + rootname)

    robot_tupe = RobotInfo.objects.filter(robot_name=rootname)
    robot_list = serializers.serialize('json', robot_tupe)
    robot_array = json.loads(robot_list)
    field = robot_array[0]['fields']
    robotstatus = field['robot_status']  # 机器人状态
    if (robotstatus == 2):  # 分配的机器人在线空闲，可以执行
        RobotInfo.objects.filter(robot_name=rootname).update(robot_status=3)
        logger.info('（1）-------执行任务中-----' + taskname + '定时任务执行中----：' + rootname + "设置机器人忙碌---")

        now_time = datetime.datetime.now()  # 现在的时间
        mappings = TaskInformation.objects.distinct().filter(booked_time=book_time).order_by('sequence')
        mappings_list = serializers.serialize('json', mappings)
        mappings_array = json.loads(mappings_list)
        if len(mappings_array) > 0:

            filePath = settings.File_Root + "\\Draw_Process\\pyfile\\" + mappings_array[0]['fields']['file_path']
            code = ""
            with open(filePath, 'r', encoding='utf-8') as f:  # 读文件代码
                code_list = f.readlines()
                for code_item in code_list:
                    code = code + code_item

            Runtaskname = mappings_array[0]['fields']['task_name']
            logger.info('（2）-------执行任务中-----' + Runtaskname + '服务器代码组织完成----：' + rootname )
            taskDoing(Runtaskname, rootname, code)

        else:
            clientname = rootname.split('_')[1];
            userid = AuthMessage.objects.filter(username=clientname).values('id')[0]['id']
            RobotInfo.objects.filter(user_id=userid).update(robot_status=2)
            logger.info('数据库中没有任务------')
    elif(robotstatus == 1):
        logger.info('（0-1）------触发任务-----' + taskname + "------机器人不在线：" + rootname)
    else:
        logger.info('（0-2）------触发任务-----' + taskname + "------机器人忙碌：" + rootname)




# (1, '离线'),
# (2, '在线空闲'),
# (3, '在线忙碌'),
#任务时间到了，开始执行任务
def taskDoing(taskname,rootname,code):
    clientname = rootname.split('_')[1];
    if Client.websocketviews.clients.__contains__(clientname):
        logger.info('（3）------后台与机器人是连接是OK的-----' + clientname + '---')
        if Client.websocketviews.clients[clientname] is not None:
            websocket = Client.websocketviews.clients[clientname]
            result = {}
            result['code'] = code
            if "General_Module.SetPassword" in code and os.path.exists(settings.File_Root + "\\Draw_Process\\pems\\" + str(clientname).lower() + ".pem"):
                choclead_secret_key = ""
                with open(settings.File_Root + "\\Draw_Process\\pems\\" + str(clientname).lower() + ".pem", "r") as f:
                    secret_key_data = f.readlines()
                    for content in secret_key_data:
                        choclead_secret_key += content.replace("\n", "")
                    result['choclead_secret_key'] = choclead_secret_key
            result['username'] = clientname
            result['action'] = 'runtask'
            result['taskname'] = taskname

            try:

                TaskInformation.objects.distinct().filter(task_name=taskname).update(status="running")
                logger.info('（4）------执行任务中-----' + taskname + '开始发送代码到机器人---')
                websocket.send(json.dumps(result))
                logger.info('（5）------执行任务中-----' + taskname + '发送代码到机器人完毕---')
            except Exception as e:
                clientname = rootname.split('_')[1];
                userid = AuthMessage.objects.filter(username=clientname).values('id')[0]['id']
                RobotInfo.objects.filter(user_id=userid).update(robot_status=2)
                TaskInformation.objects.distinct().filter(task_name=taskname).update(status="waiting")
                logger.info('（4-1）------执行任务中-----' + taskname + '发送代码到机器人发送异常---')
                logger.error(str(e))


    else:
        logger.info('------后台与机器人是没有连接的-----' + clientname + '---')





#收到定时任务的结果,删除定时任务表，创建已完成定时任务表记录
def timetaskResult(username,pc_name,taskname,result,start_time,end_time,msg,clientip,step):
    task_informations = TaskInformation.objects.distinct().filter(task_name=taskname)
    logger.info(taskname+'--定时任务执行完成----：'  )
    mappings_list = serializers.serialize('json', task_informations)
    mappings_array = json.loads(mappings_list)
    if len(mappings_array) > 0:
        mapping = mappings_array[0]
        id = mapping['pk']
        file_path = mapping['fields']['file_path']
        file_name = mapping['fields']['file_name']
        logger.info(taskname + '删除定时任务----：')
        createbyCommander =mapping['fields']['create_by']
        TaskInformation.objects.distinct().filter(task_name=taskname).delete()
        current_time = datetime.datetime.now()
        TaskResult.objects.create(pc_name=pc_name, task_name=taskname, file_path=file_path, file_name=file_name,
                                  status='unread', result=result, start_time=start_time, end_time=end_time,
                                  step=step, message=msg,
                                  create_on=current_time, create_by=createbyCommander, ip_address=clientip)
        notification= mapping['fields']['notification']
        if notification == "yes":
            duration_time = mapping['fields']['duration']
            ip= mapping['fields']['ip_address']
            receivearray= AuthMessage.objects.filter(username=username).values("email")
            if(len(receivearray)>0):
                receiver = AuthMessage.objects.filter(username=username).values("email")[0]['email']
                if receiver != "" and receiver != None:
                    if result == "success":
                        send_mail.SendEmailTask(receiver, taskname, start_time,
                                                    end_time, duration_time, 'success',
                                                    '',
                                                    '')

                    else:
                        send_mail.SendEmailTask(receiver, taskname, start_time,
                                                    end_time, duration_time, 'error',
                                                    step,
                                                    msg)
            else:
                logger.info(taskname + '用户没有邮箱----：')
        else:
            logger.info(taskname + '邮箱通知为No----：')



#收到循环任务的结果，创建已完成定时任务表记录，策略的删除任务信息表
def CycleTaskResult(username,pc_name,taskname,result,start_time,end_time,msg,clientip,step):
    task_informations = TaskInformation.objects.distinct().filter(task_name=taskname)
    logger.info(taskname+'--循环任务执行完成----：'  )
    mappings_list = serializers.serialize('json', task_informations)
    mappings_array = json.loads(mappings_list)
    if len(mappings_array) > 0:
        mapping = mappings_array[0]
        id = mapping['pk']
        file_path = mapping['fields']['file_path']
        file_name = mapping['fields']['file_name']

        createbyCommander =mapping['fields']['create_by']
        job = scheduler.get_job(job_id=taskname,)
        if job is None:
            logger.info(taskname + '删除定时任务----：')
            TaskInformation.objects.distinct().filter(task_name=taskname).delete()
        else:
            TaskInformation.objects.distinct().filter(task_name=taskname).update(status="waiting")
        #TaskInformation.objects.distinct().filter(task_name=taskname).delete()
        current_time = datetime.datetime.now()
        TaskResult.objects.create(pc_name=pc_name, task_name=taskname, file_path=file_path, file_name=file_name,
                                  status='unread', result=result, start_time=start_time, end_time=end_time,
                                  step=step, message=msg,
                                  create_on=current_time, create_by=createbyCommander, ip_address=clientip)
        notification= mapping['fields']['notification']
        if notification == "yes":
            duration_time = mapping['fields']['duration']
            ip= mapping['fields']['ip_address']
            receivearray= AuthMessage.objects.filter(username=username).values("email")
            if(len(receivearray)>0):
                receiver = AuthMessage.objects.filter(username=username).values("email")[0]['email']
                if receiver != "" and receiver != None:
                    if result == "success":
                        send_mail.SendEmailTask(receiver, taskname, start_time,
                                                    end_time, duration_time, 'success',
                                                    '',
                                                    '')

                    else:
                        send_mail.SendEmailTask(receiver, taskname, start_time,
                                                    end_time, duration_time, 'error',
                                                    step,
                                                    msg)
            else:
                logger.info(taskname + '用户没有邮箱----：')
        else:
            logger.info(taskname + '邮箱通知为No----：')

#select unused hours according to the scheduled date
@csrf_exempt
def houroption(request):
    if 'username' in request.session and 'password' in request.session:
        hour_list = []
        try:
            username = request.session['username']
            robotname = request.POST.get("robotname")
            if robotname == None:
                robotname = "robot_"+username

            ip_address = request.session['ip']
            day = request.POST.get("day")
            for h in range(24):
                if h < 10:
                    hour = str(0) + str(1)
                else:
                    hour = str(h)
                hour1 = hour + ":00:00"
                hour2 = hour + ":59:00"
                ip = request.POST.get("ip")
                st1 = str(day) + " " + str(hour1)
                st2 = str(day) + " " + str(hour2)
                min_list = []
                try:
                    book_time1 = datetime.datetime.strptime(st1, "%Y-%m-%d %H:%M:%S")
                    book_time2 = datetime.datetime.strptime(st2, "%Y-%m-%d %H:%M:%S")
                except:
                    hour_list.append(h)
                    continue
                times = TaskInformation.objects.distinct().filter(pc_name=robotname , booked_time__lte=book_time2,).values(
                    'booked_time', 'duration').order_by('booked_time', 'sequence')
                start_time = 0
                begin_time = 0
                for i in range(60):
                    min_list.append(i)
                current_time = datetime.datetime.now()
                current_hour = current_time.hour
                book_hour = book_time1.hour
                if book_hour == current_hour:
                    current_minute = current_time.minute
                    for i in range(current_minute + 1):
                        min_list.remove(i)
                last_end_time = 0
                for i in range(len(times)):
                    each_time = times[i]['booked_time']
                    each_duration = times[i]['duration']
                    duration_h = int(each_duration.split(":")[0])
                    duration_m = int(each_duration.split(":")[1])
                    duration_s = int(each_duration.split(":")[2])
                    duration_time = datetime.timedelta(hours=duration_h, minutes=duration_m, seconds=duration_s)
                    if begin_time == 0:
                        begin_time = each_time
                        end_time = each_time + duration_time
                        start_time = each_time
                        last_end_time = end_time
                    else:
                        if begin_time == each_time:
                            end_time = last_end_time + duration_time
                            start_time = last_end_time
                            last_end_time = end_time
                        else:
                            start_time = each_time
                            if last_end_time <= each_time:
                                end_time = each_time + duration_time
                            else:
                                end_time = last_end_time + duration_time
                            begin_time = each_time
                            last_end_time = end_time
                    if end_time < book_time1:
                        continue
                    else:
                        if start_time <= book_time1 and end_time >= book_time2:
                            min_list = []
                            break
                        elif start_time <= book_time1:
                            time_min = end_time.minute
                            for j in range(time_min + 1):
                                try:
                                    min_list.remove(j)
                                except:
                                    continue
                        else:
                            if start_time < book_time2:
                                time_min1 = start_time.minute
                                if end_time < book_time2:
                                    time_min2 = end_time.minute
                                else:
                                    time_min2 = 59
                                for j in range(time_min1, time_min2 + 1, 1):
                                    try:
                                        min_list.remove(j)
                                    except:
                                        continue
                if len(min_list) == 0:
                    hour_list.append(h)
            return JsonResponse({"hour_list": hour_list})
        except Exception:
            return JsonResponse({"hour_list": hour_list})
    else:
        return render(request, "login.html")

#select unused minutes according to the scheduled date and scheduled hour
@csrf_exempt
def minuteoption(request):
    if 'username' in request.session and 'password' in request.session:
        try:
            username = request.session['username']
            robotname = request.POST.get("robotname")
            if robotname == None:
                robotname = "robot_" + username
            ip_address = request.session['ip']
            day = request.POST.get("day")
            hour1 = request.POST.get("hour1")
            hour2 = request.POST.get("hour2")
            ip = request.POST.get("ip")
            st1 = str(day) + " " + str(hour1)
            st2 = str(day) + " " + str(hour2)
            min_list = []
            try:
                book_time1 = datetime.datetime.strptime(st1, "%Y-%m-%d %H:%M:%S")
                book_time2 = datetime.datetime.strptime(st2, "%Y-%m-%d %H:%M:%S")
            except:
                return JsonResponse({"min_list": min_list})
            times = TaskInformation.objects.distinct().filter(pc_name=robotname , booked_time__lte=book_time2,).values('booked_time','duration').order_by(
                'booked_time', 'sequence')
            start_time = 0
            begin_time = 0
            for i in range(60):
                min_list.append(i)
            current_time = datetime.datetime.now()
            current_hour = current_time.hour
            book_hour = book_time1.hour
            if book_hour == current_hour:
                current_minute = current_time.minute
                for i in range(current_minute + 1):
                    min_list.remove(i)
            last_end_time = 0
            for i in range(len(times)):
                each_time = times[i]['booked_time']
                each_duration = times[i]['duration']
                duration_h = int(each_duration.split(":")[0])
                duration_m = int(each_duration.split(":")[1])
                duration_s = int(each_duration.split(":")[2])
                duration_time = datetime.timedelta(hours=duration_h, minutes=duration_m, seconds=duration_s)
                if begin_time == 0:
                    begin_time = each_time
                    end_time = each_time + duration_time
                    start_time = each_time
                    last_end_time = end_time
                else:
                    if begin_time == each_time:
                        end_time = last_end_time + duration_time
                        start_time = last_end_time
                        last_end_time = end_time
                    else:
                        start_time = each_time
                        begin_time = each_time
                        if last_end_time <= each_time:
                            end_time = each_time + duration_time
                        else:
                            end_time = last_end_time + duration_time
                        last_end_time = end_time
                if end_time < book_time1:
                    continue
                else:
                    if start_time <= book_time1 and end_time >= book_time2:
                        min_list = []
                        break
                    elif start_time <= book_time1:
                        time_min = end_time.minute
                        for j in range(time_min + 1):
                            try:
                                min_list.remove(j)
                            except:
                                continue
                    else:
                        if start_time < book_time2:
                            time_min1 = start_time.minute
                            if end_time < book_time2:
                                time_min2 = end_time.minute
                            else:
                                time_min2 = 59
                            for j in range(time_min1,time_min2 + 1,1):
                                try:
                                    min_list.remove(j)
                                except:
                                    continue
            return JsonResponse({"min_list": min_list})
        except Exception:
            return JsonResponse({"result":"failed"})
    else:
        return render(request, "login.html")



#process of left function menu when open the homepage
@csrf_exempt
def datalist2(request):
    if 'username' in request.session and 'password' in request.session:
        data = []
        try:
            username = request.session['username']
            language = request.session['language']
            folder = settings.File_Root + "\\Draw_Process\\pyfile\\"
            filepath1 = folder + str(username)
            filepath2 = folder + "public"
            filepath3 = folder + "release"
            file_json1 = get_tasklist(username, filepath1, {})
            file_json2 = get_tasklist(username, filepath2, {})
            file_json3 = get_tasklist(username, filepath3, {})
            if file_json1 is not None and str(file_json1) != '{}':
                children1 = file_json1['children']
                title1 = gettext("Private")
                json1 = {}
                json1['title'] = title1
                json1['children'] = children1
                json1['path'] = str(username)
                data.append(json1)
            if file_json2 is not None and str(file_json2) != '{}':
                children2 = file_json2['children']
                title2 = gettext("Public")
                json2 = {}
                json2['title'] = title2
                json2['children'] = children2
                json2['path'] = "public"
                data.append(json2)
            if file_json3 is not None and str(file_json3) != '{}':
                children3 = file_json3['children']
                title3 = gettext("Release")
                json3 = {}
                json3['title'] = title3
                json3['children'] = children3
                json3['path'] = "release"
                data.append(json3)
        except Exception:
            print(Exception)
        return JsonResponse({"rows":data})
    else:
        return render(request, "login.html")


#检测任务名是否重复
@csrf_exempt
def checktitle(request):
    if 'username' in request.session and 'password' in request.session:
        try:
            username = request.session['username']
            language = request.session['language']
            title = request.POST.get("title")
            titles = TaskInformation.objects.filter(task_name=title).values('create_by')
            if len(titles) > 0:
                createor = titles[0]['create_by']
                if language == "en":
                    msg = "Same task has been created by " + str(createor)
                else:
                    msg = gettext("Same task has been created by") + str(createor) + gettext("created")
                return JsonResponse({"result": "exist","msg": msg})
            else:
                return JsonResponse({"result": gettext("not exist")})
        except:
            return JsonResponse({"result": gettext("not exist")})
    else:
        return render(request, "login.html")

def addTaskInformation(pc_name, sequence, create_by,task_name, file_path, file_name, duration, method ,booked_time, create_on,ip_address, status, notification):
    task = TaskInformation.objects.create(pc_name=pc_name, sequence=sequence, create_by=create_by,
                                      task_name=task_name, file_path=file_path, file_name=file_name,
                                      duration=duration, method=method,
                                      booked_time=booked_time, create_on=create_on,
                                      ip_address=ip_address, status=status,
                                      notification=notification)
    return task_name

#发布定时任务
@csrf_exempt
def getBookedTask(request):
    #scheduler.add_job(func=aps_test, args=('定时任务',), trigger='cron', second='*/5')
    if 'username' in request.session and 'password' in request.session:
        try:
            username = request.session['username']
            language = request.session['language']
            path = request.POST.get("path")
            robotname = request.POST.get("robotname")
            log_timetask_robotname = robotname
            robot_status = ""
            if robotname == "":
                robotname = "robot_" + username
            try:
                robot_status = RobotInfo.objects.filter(robot_name=robotname).values('robot_status')[0]['robot_status']
            except Exception as e:
                logger.error(str(e))
            filePath = ""
            fileNames = path.split("\\")
            for i in range(len(fileNames)):
                if i == 0:
                    filePath =settings.File_Root+ "\\Draw_Process\\pyfile\\" + fileNames[i]
                else:
                    filePath = filePath + "\\" + fileNames[i]
            fileName = ""
            for i in range(len(fileNames)):  #获取文件名
                if ".py" in fileNames[i]:
                    fileName = fileNames[i]
            day = request.POST.get("day")
            hour = request.POST.get("hour")
            method = request.POST.get("method")
            notification = request.POST.get("notification")
            title = request.POST.get("title")
            titles = TaskInformation.objects.filter(task_name=title).values('create_by')
            if len(titles) > 0:
                createor = titles[0]['create_by']
                if language == "en":
                    msg = "Same task has been created by " + str(createor)
                else:
                    msg = gettext("Same task has been created by") + str(createor) + gettext("created")
                return JsonResponse({"result": "exist","msg": msg})
            task = request.POST.get("task")
            sequence = request.POST.get("sequence")
            duration = request.POST.get("duration")
            ip = request.POST.get("ip")
            fixed_ip = request.POST.get("fixed_ip")
            st = str(day) + " " + str(hour)
            try:
                book_time = datetime.datetime.strptime(st, "%Y-%m-%d %H:%M:%S")
            except:
                book_time = ""
            current_time = datetime.datetime.now()
            try:
                timer_start_time = (book_time - current_time).total_seconds()
                time_diff = int(timer_start_time)
            except:
                time_diff = 0
            log_timetask_nowtime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
            log_timetask = {}
            log_timetask["action"] = "booking process"
            try:
                log_timetask["computer name"] = Client.websocketviews.pc_names[username.lower()]
            except:
                pass
            log_timetask_username = username
            # log_timetask_nowtime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
            log_timetask_timing = book_time
            log_timetask["username"] = log_timetask_username
            log_timetask["time"] = log_timetask_nowtime
            log_timetask["booking time"] = str(log_timetask_timing)
            task_id = ""
            if method == "time":
                log_timetask["method"] = "time"
                if time_diff > 0:
                    times = TaskInformation.objects.distinct().filter(pc_name=ip, create_by=username, ip_address=fixed_ip, booked_time__lte=book_time).values('booked_time','duration').order_by('booked_time', 'sequence')
                    start_time = 0
                    begin_time = 0
                    last_end_time = 0
                    for i in range(len(times)):
                        each_time = times[i]['booked_time']
                        each_duration = times[i]['duration']
                        duration_h = int(each_duration.split(":")[0])
                        duration_m = int(each_duration.split(":")[1])
                        duration_s = int(each_duration.split(":")[2])
                        duration_time = datetime.timedelta(hours=duration_h,minutes=duration_m,seconds=duration_s)
                        if begin_time == 0:
                            begin_time = each_time
                            end_time = each_time + duration_time
                            start_time = each_time
                            last_end_time = end_time
                            if book_time >= start_time and book_time <= end_time:
                                msg = gettext("This time has been booked!")
                                return JsonResponse({"result": "failed", "msg": msg})
                        else:
                            if begin_time == each_time:
                                end_time = last_end_time + duration_time
                                start_time = last_end_time
                                last_end_time = end_time
                                if book_time >= start_time and book_time <= end_time:
                                    msg = gettext("This time has been booked!")
                                    return JsonResponse({"result": "failed", "msg": msg})
                            else:
                                start_time = each_time
                                end_time = each_time + duration_time
                                begin_time = each_time
                                last_end_time = end_time
                                if book_time >= start_time and book_time <= end_time:
                                    msg = gettext("This time has been booked!")
                                    return JsonResponse({"result": "failed", "msg": msg})
                    task=TaskInformation.objects.create(pc_name=robotname,sequence=1.0,create_by=username,task_name=title,file_path=path,file_name=fileName,duration=duration,method=method,booked_time=book_time,create_on=current_time,ip_address=fixed_ip,status='waiting',notification=notification)

                    task_id = task.id
                    scheduler.add_job(func=taskassigntoRoboot, args=(title, robotname,book_time),
                                      next_run_time=book_time)
                    logger.info('（第0步）-------发布任务任务名：' + title +"--------将运行在机器人：" +  robotname )
                else:
                    return JsonResponse({"result": "failed","msg": "Timeout!"})
            elif method == "sequence":  #序列任务
                log_timetask["method"] = "sequence"
                refers = TaskInformation.objects.distinct().filter(create_by=username,task_name=task).values('sequence','booked_time','duration','method')
                try:
                    seq = refers[0]['sequence']
                    book_time = refers[0]['booked_time']
                    refersduration= refers[0]['duration']
                    refersmethod = refers[0]['method']
                    intseq = int(seq)


                    timer_start_time = (book_time - current_time).total_seconds()
                    time_diff = int(timer_start_time)
                    if time_diff > 0:
                        duration_h = int(duration.split(":")[0])
                        duration_m = int(duration.split(":")[1])
                        duration_s = int(duration.split(":")[2])

                        refersduration_h = int(refersduration.split(":")[0])
                        refersduration_m = int(refersduration.split(":")[1])
                        refersduration_s = int(refersduration.split(":")[2])
                        if sequence == "before":
                            task = TaskInformation.objects.create(pc_name=robotname, sequence=seq-0.5,create_by=username, task_name=title, file_path=path,
                                                           file_name=fileName, duration=duration, method=method, notification=notification,
                                                           booked_time=book_time, create_on=current_time, ip_address=fixed_ip, status='waiting')

                            scheduler.add_job(func=taskassigntoRoboot, args=(title, robotname,book_time),
                                              next_run_time=book_time)


                            logger.info('（第0步）--------发布任务任务名:' + title + "----------将运行在机器人：" + robotname)

                        else:

                            duration_h = int(refersduration.split(":")[0])
                            duration_m = int(refersduration.split(":")[1])
                            duration_s = int(refersduration.split(":")[2])

                            task = TaskInformation.objects.create(pc_name=robotname, sequence=seq+0.5, create_by=username, task_name=title,
                                                            file_path=path,file_name=fileName, duration=duration, method=method, notification=notification,
                                                            booked_time=book_time, create_on=current_time, ip_address=fixed_ip, status='waiting')
                            scheduler.add_job(func=taskassigntoRoboot, args=(title, robotname,book_time),
                                              next_run_time=book_time)
                            logger.info('（第0步）--------发布任务任务名:' + title + "----------将运行在机器人：" + robotname)
                        task_id = task.id
                    else:
                        return JsonResponse({"result": "failed"})
                except Exception as e:
                    s = str(e)
                    return JsonResponse({"result": "failed"})
            elif method == "cycle":  #start_date end_date
                log_timetask["method"] = "cycle"
                mode = request.POST.get("cycle_mode")
                endtimemode = request.POST.get("cycle_range_mode") #接收模式为次数或者为结束时间
                starttime = book_time   #任务开始时间

                start_date = request.POST.get("start_date") #周期开始时间
                end_date= request.POST.get("end_date") #周期开始时间

                starttimestring = book_time.strftime("%Y-%m-%d  %H:%M:%S")

                hourminuteseconds=  hour.split(':')
                hourstring = hourminuteseconds[0]
                minutestring = hourminuteseconds[1]
                secondstring = hourminuteseconds[2]

                if mode== 'day':
                    daymode = request.POST.get("day_mode")
                    if endtimemode == "time":  # 按次数
                        times = request.POST.get("times")  #循环次数
                        if daymode == "every_day":  # 每多少天模式
                            dayinterval = request.POST.get("day_mode_interval")  # 间隔多少天
                            daynum =int(dayinterval)
                            delday = int(times)*daynum
                            endttimedate=book_time+datetime.timedelta(days=delday)
                            enddata_time=endttimedate.strftime("%Y-%m-%d  %H:%M:%S")
                              #从startday 开始，每隔daynum  循环执行
                            dayintervalstring  = "*/" + dayinterval
                            taskid= addTaskInformation(robotname, 1.0, username,title, path, fileName,duration, method,book_time, current_time,fixed_ip, 'waiting',notification)
                            scheduler.add_job(func=CicletaskassigntoRoboots, args=(title, path,robotname,enddata_time),id = taskid,
                                              trigger='cron',year = '*',month= '*',day=dayintervalstring,hour =int(hourstring), minute=int(minutestring),second = int(secondstring),
                                              start_date=start_date, end_date=endttimedate, )
                            logger.info('--------发布定期循环任务任务名:' + title + "----------将运行在机器人：" + robotname  )



                        else:  # 每个工作日
                            endttimedate = book_time + datetime.timedelta(days=int(times))
                            enddata_time = endttimedate.strftime("%Y-%m-%d  %H:%M:%S")
                            taskid = addTaskInformation(robotname, 1.0, username, title, path, fileName, duration,
                                                        method, book_time, current_time, fixed_ip, 'waiting',
                                                        notification)
                            scheduler.add_job(func=CicletaskassigntoRoboots, args=(title, path, robotname,enddata_time),id = taskid, trigger='cron',
                                              day_of_week="mon-fri",hour =int(hourstring), minute=int(minutestring),second = int(secondstring),
                                              start_date=book_time, end_date=endttimedate, )


                    else: #按结束时间
                        enddate = request.POST.get("end_date")
                        if daymode == "every_day":  # 每多少天模式
                            dayinterval = request.POST.get("day_mode_interval")  # 间隔多少天
                            daynum = int(dayinterval)
                            # 从startday 开始，每隔daynum  循环执行
                            dayintervalstring = "*/" + dayinterval
                            taskid = addTaskInformation(robotname, 1.0, username, title, path, fileName, duration,
                                                        method, book_time, current_time, fixed_ip, 'waiting',
                                                        notification)
                            scheduler.add_job(func=CicletaskassigntoRoboots, args=(title, path, robotname,enddate),id = taskid, trigger='cron',
                                              day=dayintervalstring,hour =int(hourstring), minute=int(minutestring),second = int(secondstring),
                                              start_date=starttime, end_date=enddate, )


                        else:  # 每个工作日
                            taskid = addTaskInformation(robotname, 1.0, username, title, path, fileName, duration,
                                                        method, book_time, current_time, fixed_ip, 'waiting',
                                                        notification)
                            scheduler.add_job(func=CicletaskassigntoRoboots, args=(title, path, robotname,),id = taskid, trigger='cron',
                                              day_of_week="mon-fri",hour =int(hourstring), minute=int(minutestring),second = int(secondstring),
                                              start_date=starttime, end_date=enddate, )


                elif mode == "week":

                    weekinterval = request.POST.get("week_mode_interval")
                    weeknum=int(weekinterval)  #间隔周数
                    weekindex = book_time.isocalendar()[1]  # 获取当前开始时间属于多少周
                    dayofweek=request.POST.getlist("week_mode_selection[]")  #j需要转换
                    weekstring=""
                    for each in dayofweek:
                        day = each[0:3]
                        if len(weekstring)==0:
                            weekstring = day
                        else:
                            weekstring= weekstring+","+day

                    times = request.POST.get("times")  # 循环次数
                    logger.info('------按星期cycle'+ "间隔周期：" +weekinterval + "星期：" + weekstring )
                    if endtimemode == "time":  # 按次数
                        inttimes = int(times)
                        inttimes = inttimes+1
                        enddata_time  =book_time  + datetime.timedelta(days= inttimes* weeknum*7)  #间隔周*循环次数*7天
                        enddate= enddata_time.strftime("%Y-%m-%d")
                    else:
                        enddate = request.POST.get("end_date")

                    weekinter = str(weekindex) + "/" + weekinterval  # 从weekindex 周开始，间隔weeknum周循环
                    taskid = addTaskInformation(robotname, 1.0, username, title, path, fileName, duration, method,
                                                book_time, current_time, fixed_ip, 'waiting', notification)
                    scheduler.add_job(func=CicletaskassigntoRoboots, args=(title, path, robotname,enddate), id = taskid,trigger='cron', week=weekinter,
                                      day_of_week=weekstring,hour =int(hourstring), minute=int(minutestring),second = int(secondstring),
                                     start_date=starttime, end_date=enddate)





                elif mode == "month":
                    monthmode = request.POST.get("month_mode")
                    if monthmode == "every_day": # 每个月的第几天的模式
                        monthnum = 1
                        daytime = request.POST.get("cycle_day") #第多少天
                        daynum= int(daytime) #第多少天
                        times = request.POST.get("times")  # 循环次数
                        timestring  = int(times)
                        if endtimemode == "time":  # 按次数
                            total =book_time.month+timestring
                            if total >12:
                                newyear = int(total/12)
                                newmonth = total%12
                                enddates = datetime.datetime(book_time.year+newyear, newmonth, book_time.day, book_time.hour,
                                                            book_time.minute, book_time.second)
                                enddate = enddates.strftime("%Y-%m-%d")
                            else:
                                enddates = datetime.datetime(book_time.year,total , book_time.day, book_time.hour,
                                                            book_time.minute, book_time.second)
                                enddate = enddates.strftime("%Y-%m-%d")


                            i = 0
                        else:
                            enddate = request.POST.get("end_date")
                        taskid = addTaskInformation(robotname, 1.0, username, title, path, fileName, duration, method,
                                                    book_time, current_time, fixed_ip, 'waiting', notification)
                        scheduler.add_job(func=CicletaskassigntoRoboots, args=(title,  path,robotname,enddate),id = taskid, trigger='cron',   #每个月的第多少天
                                              month="*", day=daynum ,
                                              hour=int(hourstring), minute=int(minutestring), second=int(secondstring),
                                              start_date=book_time, end_date=enddate, )
                    else: #每多少个月的第几个星期几模式

                        weektime=request.POST.get("weekday")#星期几,天，
                        index=request.POST.get("cycle_sequence")  #1,2,3,4，last
                        #monthtimenum= int(monthtime)

                        if endtimemode == "time":  # 按次数
                            times = request.POST.get("times")  # 循环次数
                            timestring = int(times)
                            total = book_time.month + timestring
                            if total > 12:
                                newyear = int(total / 12)
                                newmonth = total % 12
                                enddates = datetime.datetime(book_time.year +newyear, newmonth, book_time.day, book_time.hour,
                                                            book_time.minute, book_time.second)
                                enddate = enddates.strftime("%Y-%m-%d")
                            else:
                                enddates = datetime.datetime(book_time.year, total, book_time.day, book_time.hour,
                                                            book_time.minute, book_time.second)
                                enddate = enddates.strftime("%Y-%m-%d")

                            i = 0
                        else:
                            enddate = request.POST.get("end_date")

                        if weektime == "day":
                            if index=="last":
                                daystring = "last"  #最后一天
                            else:
                                daystring =int(index)  #第几天模式

                            taskid = addTaskInformation(robotname, 1.0, username, title, path, fileName, duration,
                                                        method,
                                                        book_time, current_time, fixed_ip, 'waiting', notification)
                            scheduler.add_job(func=CicletaskassigntoRoboots, args=(title, path, robotname, enddate),
                                              id=taskid,
                                              trigger='cron',
                                              month="*", day=daystring,
                                              hour=int(hourstring), minute=int(minutestring),
                                              second=int(secondstring),
                                              start_date=book_time, end_date=enddate, )

                        elif weektime == "weekend":  # 周末模式
                            if index=="last":
                                daystring =  "last sat,last sun"  #最后一个周末
                            else:
                                daystring = index+"th sat" + ","+ index+"th sun" # 第几个周末

                            taskid = addTaskInformation(robotname, 1.0, username, title, path, fileName, duration,
                                                        method,
                                                        book_time, current_time, fixed_ip, 'waiting', notification)
                            scheduler.add_job(func=CicletaskassigntoRoboots, args=(title, path, robotname, enddate),
                                              id=taskid,
                                              trigger='cron',
                                              month="*", day=daystring,
                                              hour=int(hourstring), minute=int(minutestring),
                                              second=int(secondstring),
                                              start_date=book_time, end_date=enddate, )

                        elif weektime == "workingday":#工作日模式
                            if index == "last":  # 最后一个工作日，最后一个星期五
                                dayindex = GetLastworkday(book_time.year, book_time.month)
                            elif index == "1":
                                dayindex = GetFirtworkday(book_time.year, book_time.month)
                            elif index == "2":
                                dayindex = GetSecondworkday(book_time.year, book_time.month)
                            elif index == "3":
                                dayindex = GetThirdworkday(book_time.year, book_time.month)
                            elif index == "4":
                                dayindex = GetFourthworkday(book_time.year, book_time.month)

                            taskid = addTaskInformation(robotname, 1.0, username, title, path, fileName, duration,
                                                        method,
                                                        book_time, current_time, fixed_ip, 'waiting', notification)

                            current_time = datetime.datetime.now()  # 当前时间

                            nexttimes = datetime.datetime(book_time.year, book_time.month,
                                                          dayindex, book_time.hour,
                                                          book_time.minute, book_time.second)

                            taskid = addTaskInformation(robotname, 1.0, username, title, path, fileName, duration,
                                                        method,
                                                        book_time, current_time, fixed_ip, 'waiting', notification)
                            if nexttimes < current_time :

                                total = book_time.month + 1
                                if total > 12:
                                    newyear = int(total / 12)
                                    newmonth = total % 12
                                    nexttimes = datetime.datetime(current_time.year + newyear, newmonth,
                                                                  dayindex, book_time.hour,
                                                                  book_time.minute, book_time.second)
                                else:
                                    nexttimes = datetime.datetime(current_time.year, total,
                                                                  dayindex, book_time.hour,
                                                                  book_time.minute, book_time.second)
                                scheduler.add_job(func=CicleworkdaytaskassigntoRoboots,
                                                  args=(title, path, robotname, enddates),
                                                  id=taskid,
                                                  trigger='date',
                                                  next_run_time=nexttimes)

                            else:
                                scheduler.add_job(func=CicleworkdaytaskassigntoRoboots,
                                                      args=(title, path, robotname, enddates),
                                                      id=taskid,
                                                      trigger='date',
                                                      next_run_time=nexttimes)

                        else:  #第几个星期几模式
                            if index == "last":  # 最后一个星期几触发
                                daystring = "last "+ weektime[0:3]
                            else:
                                daystring = index+"th " +  weektime[0:3]

                            taskid = addTaskInformation(robotname, 1.0, username, title, path, fileName, duration,
                                                        method,
                                                        book_time, current_time, fixed_ip, 'waiting', notification)
                            scheduler.add_job(func=CicletaskassigntoRoboots, args=(title, path, robotname, enddate),
                                              id=taskid,
                                              trigger='cron',
                                              month="*", day=daystring,
                                              hour=int(hourstring), minute=int(minutestring),
                                              second=int(secondstring),
                                              start_date=book_time, end_date=enddate, )




                elif mode == "year": #年模式

                    if endtimemode == "time":  # 按次数
                        times = request.POST.get("times")  # 循环次数
                        total = book_time.month + int(times)
                        if total > 12:
                            newyear = int(total / 12)
                            newmonth = total % 12
                            enddates = datetime.datetime(book_time.year + newyear, newmonth, book_time.day,
                                                        book_time.hour,
                                                        book_time.minute, book_time.second)
                            enddate = enddates.strftime("%Y-%m-%d")
                        else:
                            enddates = datetime.datetime(book_time.year, total, book_time.day, book_time.hour,
                                                        book_time.minute, book_time.second)
                            enddate = enddates.strftime("%Y-%m-%d")

                    yearmode = request.POST.get("year_mode")
                    if yearmode=="year_day":   #第几个月的第几天的模式
                        monthtime = request.POST.get("month")  # 第几个月
                        monthtimenum = int(monthtime)
                        daytime = request.POST.get("cycle_day") #哪一天
                        daynum = int(daytime)  # 第多少天
                        taskid = addTaskInformation(robotname, 1.0, username, title, path, fileName, duration, method,
                                                    book_time, current_time, fixed_ip, 'waiting', notification)
                        scheduler.add_job(func=CicletaskassigntoRoboots, args=(title, path, robotname,enddates),id = taskid,
                                          trigger='cron',
                                          month=monthtimenum, day=daynum,
                                          hour=int(hourstring), minute=int(minutestring),
                                          second=int(secondstring),
                                          start_date=book_time, end_date=enddate, )


                    else:  #每个月的第几个周几模式
                        monthtime = request.POST.get("month")  # 第多少月
                        weektime = request.POST.get("weekday")  # 星期几
                        index = request.POST.get("sequence")  # 第几个星期
                        monthtimenum = int(monthtime)


                        if weektime == "day":
                            if index=="last":
                                daystring = "last"  #最后一天
                            else:
                                daystring =int(index)  #第几天模式
                            taskid = addTaskInformation(robotname, 1.0, username, title, path, fileName, duration,
                                                        method,
                                                        book_time, current_time, fixed_ip, 'waiting', notification)
                            scheduler.add_job(func=CicletaskassigntoRoboots, args=(title, path, robotname, enddates),
                                              id=taskid,
                                              trigger='cron',
                                              month=monthtimenum, day=daystring,
                                              hour=int(hourstring), minute=int(minutestring),
                                              second=int(secondstring),
                                              start_date=book_time, end_date=enddate, )


                        elif weektime == "weekend":  # 周末模式
                            if index == "last":
                                daystring = "last sat,last sun"  # 最后一个周末
                            else:
                                daystring = index+"th sat" + ","+ index+"th sun" # 第几个周末
                            taskid = addTaskInformation(robotname, 1.0, username, title, path, fileName, duration,
                                                        method,
                                                        book_time, current_time, fixed_ip, 'waiting', notification)
                            scheduler.add_job(func=CicletaskassigntoRoboots, args=(title, path, robotname, enddates),
                                              id=taskid,
                                              trigger='cron',
                                              month=monthtimenum, day=daystring,
                                              hour=int(hourstring), minute=int(minutestring),
                                              second=int(secondstring),
                                              start_date=book_time, end_date=enddate, )
                        elif weektime == "workingday":#工作日模式
                            if index=="last": #最后一个工作日，最后一个星期五
                                dayindex = GetLastworkday(book_time.year,monthtimenum)
                            elif  index == "1":
                                dayindex = GetFirtworkday(book_time.year, monthtimenum)
                            elif index == "2":
                                dayindex = GetSecondworkday(book_time.year, monthtimenum)
                            elif index == "3":
                                dayindex = GetThirdworkday(book_time.year, monthtimenum)
                            elif index == "4":
                                dayindex = GetFourthworkday(book_time.year, monthtimenum)


                            current_time = datetime.datetime.now() #当前时间

                            nexttimes = datetime.datetime(book_time.year , monthtimenum,
                                                         dayindex, book_time.hour,
                                                         book_time.minute, book_time.second)
                            taskid = addTaskInformation(robotname, 1.0, username, title, path, fileName, duration,
                                                        method,
                                                        book_time, current_time, fixed_ip, 'waiting', notification)
                            if nexttimes<current_time:

                                total = monthtimenum + 1
                                if total > 12:
                                    newyear = int(total / 12)
                                    newmonth = total % 12
                                    nexttimes = datetime.datetime(current_time.year + newyear, newmonth,
                                                                 dayindex, book_time.hour,
                                                                 book_time.minute, book_time.second)
                                    scheduler.add_job(func=CicleworkdaytaskassigntoRoboots,
                                                      args=(title, path, robotname, enddates),
                                                      id=taskid,
                                                      trigger='date',
                                                      next_run_time=nexttimes)
                                else:
                                    nexttimes = datetime.datetime(current_time.year, total,
                                                                  dayindex, book_time.hour,
                                                                  book_time.minute, book_time.second)
                                    scheduler.add_job(func=CicleworkdaytaskassigntoRoboots,
                                                      args=(title, path, robotname, enddates),
                                                      id=taskid,
                                                      trigger='date',
                                                      next_run_time=nexttimes)

                            else:
                                scheduler.add_job(func=CicleworkdaytaskassigntoRoboots,
                                                      args=(title, path, robotname, enddates),
                                                      id=taskid,
                                                      trigger='date',
                                                      next_run_time=nexttimes)



                        else:  #第几个星期几模式
                            if index == "last":  # 最后一个星期几触发
                                daystring = "last "+ weektime[0:3]
                            else:
                                daystring = index + "th " + weektime[0:3]
                            taskid = addTaskInformation(robotname, 1.0, username, title, path, fileName, duration,
                                                        method,
                                                        book_time, current_time, fixed_ip, 'waiting', notification)
                            scheduler.add_job(func=CicletaskassigntoRoboots, args=(title, path, robotname, enddates),
                                              id=taskid,
                                              trigger='cron',
                                              month=monthtimenum, day=daystring,
                                              hour=int(hourstring), minute=int(minutestring),
                                              second=int(secondstring),
                                              start_date=book_time, end_date=enddate, )
                try:
                    task_id = TaskInformation.objects.distinct().filter(task_name=title).values('id')[0]['id']
                except:
                    task_id = ""
            # log_timetask = {}
            # log_timetask["action"] = "booking process"
            # try:
            #     log_timetask["computer name"] = Client.websocketviews.pc_names[username.lower()]
            # except:
            #     pass
            # log_timetask_username = username
            # # log_timetask_nowtime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
            # log_timetask_timing = book_time
            log_timetask_path = path
            log_timetask_code = ""
            with open(filePath, 'r', encoding='utf-8') as f:  # 读文件代码
                try:
                    code_list = f.readlines()
                except:
                    code_list = []
            for code_item in code_list:
                if "coding:utf-8" not in code_item and code_item[0:6] != "import":
                    log_timetask_code = log_timetask_code + code_item
            # log_timetask["username"] = log_timetask_username
            # log_timetask["time"] = log_timetask_nowtime
            # log_timetask["booking time"] = str(log_timetask_timing)
            log_timetask["path"] = log_timetask_path
            log_timetask["process nodes"] = log_timetask_code[0:len(log_timetask_code)-1]
            if robotname:
                log_timetask_json = "400>" + json.dumps(log_timetask)
            else:
                log_timetask["robot pc"] = str(robotname).lower()
                log_timetask_json = "500>" + json.dumps(log_timetask)
            logger.info(log_timetask_json)
            file_length = ""
            log_file_path = settings.File_Root + "\\logs\\info-" + str(log_timetask_nowtime)[0:10] + ".log"
            if os.path.exists(log_file_path) and task_id:
                with open(log_file_path, encoding='utf-8') as f:
                    data = f.readlines()
                    if len(data) > 0:
                        file_length = len(data) - 1
                book_time_json[str(task_id)] = file_length
            # log_timetask["robot"] = log_timetask_robotname
            # log_timetask_json_command = "777>" + json.dumps(log_timetask)
            # logger.info(log_timetask_json_command)

            mappings = TaskInformation.objects.distinct().filter(ip_address=fixed_ip).order_by('booked_time',
                                                                                               'sequence')
            mappings_list = serializers.serialize('json', mappings)
            mappings_array = json.loads(mappings_list)
            task_id = ""
            for i in range(len(mappings_array)):
                mapping = mappings_array[i]
                id = mapping['pk']
                task_name = mapping['fields']['task_name']
                if task_name == title:
                    task_id = id
                TaskInformation.objects.distinct().filter(id=id).update(sequence=i + 1)
            timer_start_time = (book_time - current_time).total_seconds()
            time_diff = int(timer_start_time)
            if task is not None:
                return JsonResponse({"result": "success","robot_status":robot_status})
            else:
                return JsonResponse({"result": "timeout"})
        except Exception as e:
            logger.error('发生异常了' + str(e))
            return JsonResponse({"result":"failed"})
    else:
        return render(request, "login.html")


#更新已经完成任务
@csrf_exempt
def updateFinishedTask(request):
    if 'username' in request.session and 'password' in request.session:
        if request.method == 'POST':
            username = request.session['username']
            row = request.POST.get('row')
            if row != None:
                rows = []
                rows.append(row)
            else:
                rows = request.POST.getlist('rows[]')
            result = {}
            try:
                TaskResult.objects.filter(create_by=username,id__in=rows).update(status='read')
                result['result'] = 'success'
            except:
                result['result'] = 'failed'
            return JsonResponse(result)
    else:
        return render(request, "login.html")
#删除完成任务
@csrf_exempt
def deleteFinishedTask(request):
    if 'username' in request.session and 'password' in request.session:
        if request.method == 'POST':
            username = request.session['username']
            row = request.POST.get('row')
            if row != None:
                rows = []
                rows.append(row)
            else:
                rows = request.POST.getlist('rows[]')
            result = {}
            try:
                TaskResult.objects.filter(create_by=username,id__in=rows).delete()
                result['result'] = 'success'
            except:
                result['result'] = 'failed'
            return JsonResponse(result)
    else:
        return render(request, "login.html")

#删除定时任务
@csrf_exempt
def deleteBookedTask(request):
    if 'username' in request.session and 'password' in request.session:
        if request.method == 'POST':
            username = request.session['username']
            row = request.POST.get('row')
            if row != None:
                rows = []
                rows.append(row)
            else:
                rows = request.POST.getlist('rows[]')
            result = {}
            try:
                mappings=TaskInformation.objects.filter(id__in=rows).values("task_name")
                for mapping in mappings:
                    task_id = mapping['task_name']
                    deletetask = scheduler.get_job(job_id= task_id)
                    if deletetask != None:
                        logger.info('获取的定期任务是' + deletetask.id + "任务名：" + deletetask.args[0])
                        scheduler.remove_job(str(deletetask.id))

                TaskInformation.objects.filter(create_by=username, id__in=rows).delete()
                result['result'] = 'success'
            except:
                result['result'] = 'failed'
            return JsonResponse(result)
    else:
        return render(request, "login.html")

#获取定时任务已选择的信息
@csrf_exempt
def taskcreateor(request):
    if 'username' in request.session and 'password' in request.session:
        username = request.session['username']
        task = request.POST.get("task")
        mappings = TaskInformation.objects.distinct().filter(create_by=username, task_name=task).values('id','create_by','booked_time')
        createor = ""
        booked_day = ""
        booked_hour = ""
        for mapping in mappings:
            task_id = mapping['id']
            createor = mapping['create_by']
            booked_time = mapping['booked_time']
            booked_day = booked_time.strftime('%Y-%m-%d')
            booked_hour = booked_time.strftime('%H:%M:%S')
        return JsonResponse({"task_id":task_id,"createor":createor,"booked_day":booked_day,"booked_hour":booked_hour})
    else:
        return render(request, "login.html")

#获取定时任务的信息
@csrf_exempt
def tasklist(request):
    if 'username' in request.session and 'password' in request.session:
        username = request.session['username']
        ip = request.POST.get("ip")
        mappings = TaskInformation.objects.distinct().filter(create_by=username).values('task_name').order_by('sequence')
        task_list = []
        for mapping in mappings:
            task = mapping['task_name']
            task_list.append(task)
        return JsonResponse({"task":task_list})
    else:
        return render(request, "login.html")

#获取机器人的信息
@csrf_exempt
def getrobotlist(request):
    if 'username' in request.session and 'password' in request.session:
        username = request.session['username']
        ip = request.POST.get("ip")
        user = AuthMessage.objects.get(username=username)
        perms = AuthMessage.get_all_permissions(user)
        robot_list = []
        for perm in perms:
            if "Draw_Process.views_commander_" in perm and "_schedule_task" in perm:
                robot_code = "robot_" + str(
                    perm.replace("Draw_Process.views_commander_", "").replace("_schedule_task", ""))
                if robot_code not in robot_list:
                    robot_list.append(robot_code)
        mappings = RobotInfo.objects.filter(robot_name__in=robot_list)
        #mappings = TaskInformation.objects.distinct().filter(create_by=username, pc_name=ip).values('task_name').order_by('sequence')
        mappings_list = serializers.serialize('json', mappings)
        mappings_array = json.loads(mappings_list)
        Robot_list = []
        for mapping in mappings_array:
            robot = mapping['fields']['robot_name']
            Robot_list.append(robot)
        return JsonResponse({"robotlist":Robot_list})
    else:
        return render(request, "login.html")


#book task web page
@csrf_exempt
def booktask(request):
    if 'username' in request.session and 'password' in request.session:
        username = request.session['username']
        language = request.session['language']
        try:
            ip = request.GET['ip']
        except:
            ip = request.GET['robot']
        fixed_ip = request.session['ip']
        try:
            show = request.GET['show']
        except:
            show = "no"
        return render(request,'booktask.html',{"ip":ip,"fixed_ip":fixed_ip,"username":username,"language":language,"show":show})
    else:
        return render(request, "login.html")


#显示所有本账户下的未完成的任务
@csrf_exempt
def bookedList(request):
    if 'username' in request.session and 'password' in request.session:
        username = request.session['username']
        page_No = request.POST.get("pageNo")
        page_Size = request.POST.get("pageSize")
        orderBy = request.POST.get("orderBy")
        # 筛选条件
        loginCode = request.POST.get("loginCode")
        pcName = request.POST.get("pcName")
        status = request.POST.get("status")
        start = request.POST.get("start")
        try:
            start_time = datetime.datetime.strptime(start + ' 00:00:00','%Y-%m-%d %H:%M:%S')
        except:
            start_time = datetime.datetime.strptime('1900-01-01 00:00:00','%Y-%m-%d %H:%M:%S')
        end = request.POST.get("end")
        try:
            end_time = datetime.datetime.strptime(end + ' 23:59:59','%Y-%m-%d %H:%M:%S')
        except:
            end_time = datetime.datetime.strptime('2100-01-01 23:59:59','%Y-%m-%d %H:%M:%S')
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
            if status == '':
                auth_tupe = TaskInformation.objects.all().filter(create_by__icontains=loginCode, pc_name__icontains=pcName,
                                                            booked_time__gte=start_time, booked_time__lte=end_time)
            else:
                auth_tupe = TaskInformation.objects.all().filter(create_by__icontains=loginCode, pc_name__icontains=pcName,
                                                            status=status, booked_time__gte=start_time,
                                                            booked_time__lte=end_time)

        else:
            if status == '':
                auth_tupe = TaskInformation.objects.all().filter(create_by__icontains=loginCode, pc_name__icontains=pcName,
                                                            booked_time__gte=start_time, booked_time__lte=end_time).order_by(order_condition)
            else:
                auth_tupe = TaskInformation.objects.all().filter(create_by__icontains=loginCode, pc_name__icontains=pcName,
                                                            status=status, booked_time__gte=start_time,
                                                            booked_time__lte=end_time).order_by(order_condition)
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
            auth_json["id"] = auth_array[j]['pk']
            auth_json["sequence"] = field['sequence']
            auth_json["create_by"] = field['create_by']
            auth_json["pc_name"] = field['pc_name']
            auth_json["ip_address"] = field['ip_address']
            booked_time = field['booked_time']
            try:
                start_time = datetime.datetime.strptime(booked_time[:26], "%Y-%m-%dT%H:%M:%S.%f")
            except:
                start_time = datetime.datetime.strptime(booked_time[:26], "%Y-%m-%dT%H:%M:%S")
            duration = field['duration']
            duration_h = int(duration.split(":")[0])
            duration_m = int(duration.split(":")[1])
            duration_s = int(duration.split(":")[2])
            if duration_h != 0:
                if duration_m == 0:
                    duration_time = str(duration_h) + "h"
                else:
                    duration_time = str(duration_h + round(int(duration_m) / 60, 2)) + "h"
            elif duration_m != 0:
                if duration_s == 0:
                    duration_time = str(duration_m) + "min"
                else:
                    duration_time = str(duration_m + round(int(duration_s) / 60, 2)) + "min"
            else:
                duration_time = str(duration_s) + "s"
            start_time = start_time.strftime('%Y-%m-%d %H:%M:%S')
            auth_json["booked_time"] = str(start_time)
            auth_json["duration"] = duration_time
            auth_json["method"] = field['method']
            auth_json["task_name"] = field['task_name']
            auth_json["file_name"] = field['file_name']
            filePath = field['file_path']
            fileFolders = filePath.split("\\")
            file_folder = ''
            for i in range(len(fileFolders)):
                fileFolder = fileFolders[i]
                if i == 0:
                    if fileFolder == 'public':
                        file_folder = gettext('Public')
                    elif fileFolder == 'release':
                        file_folder = gettext('Release')
                    else:
                        file_folder = gettext('Private')
                else:
                    file_folder = file_folder + '\\' + fileFolder
            auth_json["filePath"] = field['file_path']
            auth_json["processPath"] = file_folder
            auth_json["method"] = gettext(field['method'])
            auth_json["status"] = gettext(field['status'])
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



#unfinished tasks web page
@csrf_exempt
def bookedschedule(request):
    if 'username' in request.session and 'password' in request.session:
        username = request.session['username']
        language = request.session['language']
        return render(request,'bookedSchedule.html',{'username':username,'language':language})
    else:
        return render(request, "login.html")

#get finished tasks list
@csrf_exempt
def finishedList(request):
    if 'username' in request.session and 'password' in request.session:
        username = request.session['username']
        page_No = request.POST.get("pageNo")
        page_Size = request.POST.get("pageSize")
        orderBy = request.POST.get("orderBy")
        # 筛选条件
        loginCode = request.POST.get("loginCode")
        pcName = request.POST.get("pcName")
        status = request.POST.get("status")
        start = request.POST.get("start")
        try:
            start_time = datetime.datetime.strptime(start + ' 00:00:00','%Y-%m-%d %H:%M:%S')
        except:
            start_time = datetime.datetime.strptime('1900-01-01 00:00:00','%Y-%m-%d %H:%M:%S')
        end = request.POST.get("end")
        try:
            end_time = datetime.datetime.strptime(end + ' 23:59:59','%Y-%m-%d %H:%M:%S')
        except:
            end_time = datetime.datetime.strptime('2100-01-01 23:59:59','%Y-%m-%d %H:%M:%S')
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
            if status == '':
                auth_tupe = TaskResult.objects.all().filter(create_by__icontains=loginCode, pc_name__icontains=pcName,
                                                            start_time__gte=start_time, end_time__lte=end_time).order_by('-start_time')
            else:
                auth_tupe = TaskResult.objects.all().filter(create_by__icontains=loginCode, pc_name__icontains=pcName,
                                                            status=status, start_time__gte=start_time,
                                                            end_time__lte=end_time).order_by('-start_time')

        else:
            if status == '':
                auth_tupe = TaskResult.objects.all().filter(create_by__icontains=loginCode, pc_name__icontains=pcName,
                                                            start_time__gte=start_time, end_time__lte=end_time).order_by(order_condition)
            else:
                auth_tupe = TaskResult.objects.all().filter(create_by__icontains=loginCode, pc_name__icontains=pcName,
                                                            status=status, start_time__gte=start_time,
                                                            end_time__lte=end_time).order_by(order_condition)
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
            auth_json["id"] = auth_array[j]['pk']
            auth_json["create_by"] = field['create_by']
            auth_json["pc_name"] = field['pc_name']
            auth_json["ip_address"] = field['ip_address']
            start = field['start_time']
            end = field['end_time']
            try:
                start_time = datetime.datetime.strptime(start[:26], "%Y-%m-%dT%H:%M:%S.%f")
            except:
                start_time = datetime.datetime.strptime(start, "%Y-%m-%dT%H:%M:%S")
            try:
                end_time = datetime.datetime.strptime(end[:26], "%Y-%m-%dT%H:%M:%S.%f")
            except:
                end_time = datetime.datetime.strptime(end, "%Y-%m-%dT%H:%M:%S")
            duration = (end_time - start_time).seconds
            if int(duration) > 3600:
                duration_time = str(round(int(duration) / 3600, 2)) + "h"
            elif int(duration) > 60:
                duration_time = str(round(int(duration) / 60, 2)) + "min"
            else:
                duration_time = str(duration) + "s"
            start_time = start_time.strftime('%Y-%m-%d %H:%M:%S')
            auth_json["start_time"] = str(start_time)
            auth_json["duration"] = duration_time
            auth_json["task_name"] = field['task_name']
            auth_json["file_name"] = field['file_name']
            filePath = field['file_path']
            fileFolders = filePath.split("\\")
            file_folder = ''
            for i in range(len(fileFolders)):
                fileFolder = fileFolders[i]
                if i == 0:
                    if fileFolder == 'public':
                        file_folder = gettext('Public')
                    elif fileFolder == 'release':
                        file_folder = gettext('Release')
                    else:
                        file_folder = gettext('Private')
                else:
                    file_folder = file_folder + '\\' + fileFolder
            auth_json["filePath"] = field['file_path']
            auth_json["processPath"] = file_folder
            auth_json["status"] = gettext(field['status'])
            auth_json["result"] = gettext(field['result'])
            auth_json["step"] = field['step']
            auth_json["message"] = field['message']
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

#finished tasks web page
@csrf_exempt
def finishedschedule(request):
    if 'username' in request.session and 'password' in request.session:
        username = request.session['username']
        language = request.session['language']
        return render(request,'finishedSchedule.html',{'username':username,'language':language})
    else:
        return render(request, "login.html")



#client get the expired tasks or the future tasks
@csrf_exempt
def startFutureTask(request):

    username = request.session['bookeduser']
    ip = request.session['bookedip']
    now_time = datetime.datetime.now()
    mappings = TaskInformation.objects.distinct().filter(create_by=username, ip_address=ip, booked_time__lte=now_time).order_by('booked_time', 'sequence')
    mappings_list = serializers.serialize('json', mappings)
    mappings_array = json.loads(mappings_list)
    headers = {
        'Connection': 'Keep-Alive',
        'User-Agent': 'Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 5.1; Trident/4.0)',
    }
    if len(mappings_array) > 0:
        filePath =  settings.File_Root  + "\\Draw_Process\\pyfile\\" + mappings_array[0]['fields']['file_path']
        task_id = mappings_array[0]['pk']
        notification = mappings_array[0]['fields']['notification']
        code = ""
        with open(filePath, 'r') as f:
            code_list = f.readlines()
            for code_item in code_list:
                code = code + code_item
        server_address = ""
        setting_file = settings.File_Root + "\\Draw_Process\\setting.txt"
        with open(setting_file, 'r',encoding="utf-8") as ff:
            setting_content = ff.readlines()
            for i in range(len(setting_content)):
                setting_list = setting_content[i].rstrip("\n").split("=")
                if 'server_address' in setting_list[0]:
                    server_address = setting_list[1].replace(" ", "")
                    break
        params = {'code': code, 'username': username, 'sequence': 1, 'timer_start_time': 1,
                  'task_id': task_id, 'ip': ip, 'notification': notification, 'server_address':server_address}
        r = requests.post('http://' + ip + ':8080/book', data=params, headers=headers)
        return HttpResponse('1')
    else:
        mappings = TaskInformation.objects.distinct().filter(create_by=username, ip_address=ip).order_by('booked_time', 'sequence').values('id','booked_time','notification','file_path')
        if len(mappings) > 0:
            task_id = mappings[0]['id']
            booked_time = mappings[0]['booked_time']
            notification = mappings[0]['notification']
            try:
                booked_time2 = datetime.datetime.strptime(booked_time, "%Y-%m-%d %H:%M:%S")
            except:
                booked_time2 = booked_time
            now_time = datetime.datetime.now()
            time_diff = (booked_time2 - now_time).seconds
            filePath =  settings.File_Root + + "\\Draw_Process\\pyfile\\" + mappings[0]['file_path']
            code = ""
            with open(filePath, 'r') as f:
                code_list = f.readlines()
                for code_item in code_list:
                    code = code + code_item
            params = {'code': code, 'username': username, 'sequence': 1, 'timer_start_time': time_diff,
                      'task_id': task_id, 'ip': ip, 'notification': notification}
            # r = requests.post('http://' + ip + ':8080/book', data=params, headers=headers)
        return HttpResponse('2')



@csrf_exempt
def receiveBookedTask(request):
    try:
        notification = request.POST.get("notification")
        ip = request.POST.get("ip")
        task_id = request.POST.get("task_id")
        username = request.POST.get("username")
        task_informations = TaskInformation.objects.distinct().filter(id=task_id).values('pc_name','task_name','file_path','file_name')
        if len(task_informations) > 0:
            task_information = task_informations[0]
            pc_name = task_information['pc_name']
            task_name = task_information['task_name']
            file_path = task_information['file_path']
            file_name = task_information['file_name']
            step = request.POST.get("step")
            msg = request.POST.get("conso")
            start_time = datetime.datetime.strptime(request.POST.get("start_time"), "%Y-%m-%d %H:%M:%S")
            end_time = datetime.datetime.strptime(request.POST.get("end_time"), "%Y-%m-%d %H:%M:%S")
            try:
                duration = (end_time - start_time).seconds
                if int(duration) > 3600:
                    duration_time = str(round(int(duration) / 3600, 2)) + "h"
                elif int(duration) > 60:
                    duration_time = str(round(int(duration) / 60, 2)) + "min"
                else:
                    duration_time = str(duration) + "s"
            except:
                duration_time = ''
            result = request.POST.get("result")
            current_time = datetime.datetime.now()
            TaskInformation.objects.distinct().filter(id=task_id).delete()
            TaskResult.objects.create(pc_name=pc_name, task_name=task_name, file_path=file_path, file_name=file_name,
                                      status='unread', result=result, start_time=start_time, end_time=end_time,
                                      step = step, message=msg,
                                      create_on=current_time, create_by=username)
            if notification == "yes":
                receiver = AuthMessage.objects.filter(user=username).values("email")[0]['email']
                if receiver != "" and receiver != None:
                    if result == "success":
                        mail_result = send_mail.run(receiver, task_name, start_time.strftime('%Y-%m-%d %H:%M:%S'),
                                      end_time.strftime('%Y-%m-%d %H:%M:%S'), duration_time, 'success', '', '')
                    else:
                        mail_result = send_mail.run(receiver, task_name, start_time.strftime('%Y-%m-%d %H:%M:%S'),
                                      end_time.strftime('%Y-%m-%d %H:%M:%S'), duration_time, 'error', step, msg)
                    send_result = mail_result['result']
                    if send_result != 'success':
                        conso = mail_result['conso']
                        logger.error(username + " " + ip + " " + task_name + " send mail failed!")
                        logger.error("Error message: " + conso)
            request.session['bookeduser'] = username
            request.session['bookedip'] = ip
            return redirect('/startfuturetask/')
        else:
            request.session['bookeduser'] = username
            request.session['bookedip'] = ip
            return redirect('/startfuturetask/')
    except Exception:
        exstr = str(traceback.format_exc())
        logger.error("Receive booked task error message: " + exstr)
        return JsonResponse({"msg": "Receive booked task error Message: " + exstr})

@csrf_exempt
def scheduleCycleHtml(request):
    if 'username' in request.session and 'password' in request.session:
        username = request.session['username']
        language = request.session['language']
        today = datetime.date.today()
        week_day = get_week_day(today)
        week_day_val = today.weekday()
        day = today.day
        month = today.month
        sequence = day // 7
        date2 = today + datetime.timedelta(days = 63)
        formatted_today = today.strftime('%Y-%m-%d')
        formatted_date2 = date2.strftime('%Y-%m-%d')
        return render(request,'scheduleCycle.html',{"date1":formatted_today,"date2":formatted_date2,"week_day":week_day,"week_day_val":week_day_val,"day":day,"month":month,"sequence":sequence,"language":language})
    else:
        return render(request, "login.html")


# (1, '离线'),
# (2, '在线空闲'),
# (3, '在线忙碌'),
#任务时间到了，开始执行任务
def CicletaskDoing(taskname,rootname,code,timestring):
    robot_tupe=RobotInfo.objects.filter(robot_name=rootname)
    robot_list = serializers.serialize('json', robot_tupe)
    robot_array = json.loads(robot_list)
    field = robot_array[0]['fields']
    logger.info(taskname+'定期任务执行---')
    robotstatus = field['robot_status'] #机器人状态
    if(robotstatus ==2): #分配的机器人在线空闲，可以执行
        print('机器人在线空闲')
        clientname = rootname.split('_')[1];
        if Client.websocketviews.clients.__contains__(clientname):
            if Client.websocketviews.clients[clientname] is not None:
                websocket = Client.websocketviews.clients[clientname]
                result={}
                result['code'] = code
                if "General_Module.SetPassword" in code and os.path.exists(settings.File_Root + "\\Draw_Process\\pems\\" + str(clientname).lower() + ".pem"):
                    choclead_secret_key = ""
                    with open(settings.File_Root + "\\Draw_Process\\pems\\" + str(clientname).lower() + ".pem", "r") as f:
                        secret_key_data = f.readlines()
                        for content in secret_key_data:
                            choclead_secret_key += content.replace("\n", "")
                        result['choclead_secret_key'] = choclead_secret_key
                result['username']=clientname
                result['action'] = 'runCycletask' #循环任务
                result['taskname'] = taskname
                websocket.send(json.dumps(result))
                userid = AuthMessage.objects.filter(username=clientname).values('id')[0]['id']
                RobotInfo.objects.filter(user_id=userid).update(robot_status=3)
                logger.info(taskname+'定期任务执行中----：'+ rootname+ "机器人忙碌---")
                TaskInformation.objects.distinct().filter(task_name=taskname).update(status="running")
        else:
            logger.info('定期任务执行中  websocket 没有连接------')
            if scheduler.get_job(rootname, jobstores) == None:
                scheduler.add_job(func=CicletaskDoing, args=(taskname, rootname, code,), id=taskname,
                                  next_run_time=datetime.datetime.now() + datetime.timedelta(seconds=300))  # 5分钟
            else:

                scheduler.reschedule_job(job_id=taskname,
                                         next_run_time=datetime.datetime.now() + datetime.timedelta(seconds=300))# 5分钟

    else:#机器人不在线或者忙碌，延迟执行
        if scheduler.get_job(rootname,jobstores) == None:
            scheduler.add_job(func=CicletaskDoing, args=(taskname, rootname, code,), id=taskname,
                              next_run_time=datetime.datetime.now() + datetime.timedelta(seconds=300)) # 5分钟
        else:

            scheduler.reschedule_job(job_id=taskname,next_run_time=datetime.datetime.now() + datetime.timedelta(seconds=300) )

        logger.info('不在线或者忙碌')




#一个循环任务发个多个机器人
def CicletaskassigntoRoboots(taskname,path,rootbot,timestring):

    filePath = settings.File_Root + "\\Draw_Process\\pyfile\\" + path
    code = ""
    with open(filePath, 'r', encoding='utf-8') as f:  # 读文件代码
        try:
            code_list = f.readlines()
        except Exception as e:
            pass
    for code_item in code_list:
        code = code + code_item
    CicletaskDoing(taskname,rootbot,code,timestring)


#框架没有工作日的循环模式，所以增加工作日的按月循环模式，上一个结束后，加入下一个时间
def CicleworkdaytaskassigntoRoboots(taskname,path,rootbot,timestring):
    timedate = datetime.datetime.strptime(timestring, '%Y-%m-%dT%H:%M:%S')
    current_time = datetime.datetime.now()
    if timedate > current_time:

        total = current_time.month + 1
        if total > 12:
            newyear = int(total / 12)
            newmonth = total % 12
            enddates = datetime.datetime(current_time.year + newyear, newmonth, current_time.day, current_time.hour,
                                         current_time.minute, current_time.second)

        else:
            enddates = datetime.datetime(current_time.year, total, current_time.day, current_time.hour,
                                         current_time.minute, current_time.second)

        scheduler.reschedule_job(job_id=taskname, next_run_time=enddates)


    filePath = settings.File_Root + "\\Draw_Process\\pyfile\\" + path
    code = ""
    with open(filePath, 'r') as f:  # 读文件代码
        code_list = f.readlines()
    for code_item in code_list:
        code = code + code_item
    CicletaskDoing(taskname,rootbot,code,timestring)




import datetime
import calendar


# 判断某一天是否是周末
def isworingday(year, month, day):
    currentday = calendar.weekday(year, month, day)
    if currentday >= 5:  # 5-》星期六，6-》星期天
        return True
        print("当天为周末")
    else:
        print("当天为工作日")
        return False


# 获取某月第一个工作日
def GetFirtworkday(year,month):
    dayindex =1
    while isworingday(year,month,dayindex):
        dayindex+=1
    return  dayindex

# 获取第2个工作日
def GetSecondworkday(year,month):
    dayindex =GetFirtworkday(year,month)
    dayindex= dayindex+1
    while isworingday(year,month,dayindex):
        dayindex+=1
    return  dayindex


# 获取第3个工作日
def GetThirdworkday(year,month):
    dayindex = GetSecondworkday(year, month)
    dayindex = dayindex + 1
    while isworingday(year, month, dayindex):
        dayindex += 1
    return dayindex


# 获取第4个工作日
def GetFourthworkday(year,month):
    dayindex = GetThirdworkday(year, month)
    dayindex = dayindex + 1
    while isworingday(year, month, dayindex):
        dayindex += 1
    return dayindex


# 获取第4个工作日
def GetLastworkday(year,month):
    monthRange = calendar.monthrange(year,month)
    dayindex =monthRange[1] #最后一天
    while isworingday(year,month,dayindex):
        dayindex-=1
    return  dayindex


