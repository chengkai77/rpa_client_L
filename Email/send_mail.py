#coding:utf-8
from smtplib import SMTP
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email import encoders
from email.header import Header
import traceback
import os
from  Timetasks import  timetasksviews
import logging
logger = logging.getLogger('log')
from Python_Platform import settings

def run(receiver,name,start,end,duration,result,step,message):
    try:
        setting_file=settings.File_Root + "\\Draw_Process" + "\\setting.txt"
        with open(setting_file, 'r',encoding='utf-8') as ff:
            setting_content = ff.readlines()
            for i in range(len(setting_content)):
                setting_list = setting_content[i].rstrip("\n").split("=")
                if 'smtpserver' in setting_list[0]:
                    smtpserver = setting_list[1].replace(" ", "")
                elif 'sender' in setting_list[0]:
                    sender = setting_list[1].replace(" ", "")
                elif 'smtpport' in setting_list[0]:
                    port = setting_list[1].replace(" ", "")

        receivers = []
        receivers.append(receiver)
        subject = str(name)
        msg = MIMEMultipart("related")
        msg["Subject"] = Header(subject, "utf-8")
        msg['From'] = 'RPA'
        msg['to'] = Header(",".join(receivers))
        SendHtml = '<font face="arial">Name: '+'</font><font color="blue">'+str(name)+'</font><br><br>'
        SendHtml = SendHtml + '<font face="arial">Start: </font><font color="blue">'+str(start)+'</font><br><br>'
        SendHtml = SendHtml + '<font face="arial">End: </font><font color="blue">' + str(end) + '</font><br><br>'
        SendHtml = SendHtml + '<font face="arial">Duration: </font><font color="blue">' + str(duration) + '</font><br><br>'
        SendHtml = SendHtml + '<font face="arial">Status: </font><font color="blue">' + str(result) + '</font><br><br>'
        if result != "success":
            SendHtml = SendHtml + '<font face="arial">Err Step: </font><font color="red">' + str(step) + '</font><br><br>'
            SendHtml = SendHtml + '<font face="arial">Err Message: </font><font color="red">' + str(message) + '</font><br><br>'
        msgText = MIMEText(SendHtml, "html", "utf-8")
        msg.attach(msgText)
        smtp = SMTP()
        smtp.connect(smtpserver,port)
        smtp.sendmail(from_addr=sender, to_addrs=receiver, msg=msg.as_string())
        smtp.quit()
    except Exception:
        exstr = str(traceback.format_exc())
        logger.error(''+ exstr)
        return {"result": "error", "step": "6b6704e0-2e01-11ea-b2f0-ed10b4b553c8", "msg": "Send_Mail Failed!", "conso":exstr}
    return {"result": "success"}

import datetime
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
def my_listener(event):
    if event.exception:
        print ('')
    else:
        print ('')
#
def SendEmailTask(receiver,name,start,end,duration,result,step,message):
    timetasksviews.scheduler.add_job(func=run, args=(receiver,name,start,end,duration,result,step,message,), next_run_time=datetime.datetime.now() + datetime.timedelta(seconds=2))
    #timetasksviews.scheduler.add_listener(my_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)