



#process of left function menu when open the homepage
import os
from Draw_Process.models import AuthMessage
from Draw_Process.models import Folder


def get_tasklist(username, dir, json):
    if os.path.isfile(dir):
        fileName = dir.split("\\")[len(dir.split("\\")) - 1]
        fileName = os.path.splitext(fileName)[0]
        folder = os.path.dirname(os.path.realpath(__file__)) + "\\pyfile\\"
        json['id'] = dir.replace(folder,"")
        json['title'] = fileName
        json['path'] = dir.replace(folder,"")
        return json
    elif os.path.isdir(dir):
        list = []
        folder = os.path.dirname(os.path.realpath(__file__)) + "\\pyfile\\"
        folder1 = os.path.dirname(os.path.realpath(__file__)) + "\\pyfile\\public"
        folder2 = os.path.dirname(os.path.realpath(__file__)) + "\\pyfile\\public\\"
        folder3 = os.path.dirname(os.path.realpath(__file__)) + "\\pyfile\\release"
        folder4 = os.path.dirname(os.path.realpath(__file__)) + "\\pyfile\\release\\"
        replace_dir = dir.replace(folder2, "").replace(folder1, "")
        replace_dir = replace_dir.replace(folder4, "").replace(folder3, "")
        type = dir.replace(folder, "").split("\\")[0]
        if type != 'release' and type != 'public':
            type = 'private'
        folder_path = dir.replace(folder, "")
        perm = "Draw_Process.views_folder_" + replace_dir
        user = AuthMessage.objects.get(username=username)
        folder_path_length = len(Folder.objects.filter(folder=folder_path).values('folder'))
        if user.has_perm(perm) or replace_dir == "" or folder_path_length == 1 or type == 'private':
            for s in os.listdir(dir):
                newDir = os.path.join(dir, s)
                append_result = get_tasklist(username, newDir, {})
                if len(append_result) > 0:
                    list.append(append_result)
            fileName = dir.split("\\")[len(dir.split("\\")) - 1]
            fileName = os.path.splitext(fileName)[0]
        if len(list) > 0:
            json['title'] = fileName
            json['id'] = dir.replace(folder,"")
            json['path'] = dir.replace(folder,"")
            json['children'] = list
            json['state'] = "closed"
            return json
        else:
            return json