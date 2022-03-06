# coding=utf-8
import xlrd
import json
import os


def createActionsJson():
    # 打开文件
    data = xlrd.open_workbook('Actions Parameters.xlsx')

    # 通过文件名获得工作表,获取工作表1
    sheet = data.sheet_by_name('Sheet1')

    # 获取行数和列数
    print("总行数：" + str(sheet.nrows))

    # 获取整行的值 和整列的值，返回的结果为数组
    # 整行值：sheet.row_values(start,end)
    colValues = sheet.col_values(0, 3)
    actionList = list(set(colValues))
    # 读取所有动作
    print("actionList：" + str(actionList))

    # 读取动作对应参数
    startRow = 2
    parameters = []
    for i in range(startRow + 1, sheet.nrows):
        titleRows = sheet.row_values(startRow)
        rows = sheet.row_values(i)
        rowDict = {}
        for col in range(0, len(titleRows)):
            # 替换换行符为空，整理成基本格式
            text = str(rows[col]).replace("\n","")
            rowDict[titleRows[col]] = text
        parameters.append(rowDict)
    # print("parameters：" + str(parameters))

    # 转成这样的格式
    # actions = {
    #     "Excel_OpenWorkbook": {
    #         "Node No": {
    #             "title": {"class": "","style": "","text": "+gettext('Node No')+","name": ""},
    #             "input": {"class": "property-input","style":"","id":"nodeNo","name":"property","autocomplete":"","disabled":"","placeholder":"","oninput":""}
    #         }
    #     }
    # }

    actions = {}
    for i in range(0, len(actionList)):
        actions[actionList[i]] = {}
    for i in range(0, len(parameters)):
        """
        顺序是会有影响的
        """
        actions[parameters[i]["Action"]][parameters[i]["Parameters"]] = {}
        try:
            if parameters[i]["structure"] != "":
                actions[parameters[i]["Action"]][parameters[i]["Parameters"]]["structure"] = json.loads(parameters[i]["structure"])
        except Exception as e:
            print("structure 格式有问题: " + str(parameters[i]))
        try:
            if parameters[i]["required-icon"] != "":
                actions[parameters[i]["Action"]][parameters[i]["Parameters"]]["required-icon"] = json.loads(parameters[i]["required-icon"])
        except Exception as e:
            print("required-icon 格式有问题: " + str(parameters[i]))
        try:
            if parameters[i]["checkbox"] != "":
                actions[parameters[i]["Action"]][parameters[i]["Parameters"]]["checkbox"] = json.loads(parameters[i]["checkbox"])
        except Exception as e:
            print("checkbox 格式有问题: " + str(parameters[i]))
        try:
            actions[parameters[i]["Action"]][parameters[i]["Parameters"]]["title"] = json.loads(parameters[i]["title"])
        except Exception as e:
            print("title 格式有问题: " + str(parameters[i]))
        try:
            if parameters[i]["colorpicker"] != "":
                actions[parameters[i]["Action"]][parameters[i]["Parameters"]]["colorpicker"] = json.loads(parameters[i]["colorpicker"])
        except Exception as e:
            print("colorpicker 格式有问题: " + str(parameters[i]))
        try:
            if parameters[i]["pencil"] != "":
                actions[parameters[i]["Action"]][parameters[i]["Parameters"]]["pencil"] = json.loads(
                    parameters[i]["pencil"])
        except Exception as e:
            print("pencil 格式有问题: " + str(parameters[i]))
        try:
            if parameters[i]["custom_button"] != "":
                actions[parameters[i]["Action"]][parameters[i]["Parameters"]]["custom_button"] = json.loads(
                    parameters[i]["custom_button"])
        except Exception as e:
            print("custom_button 格式有问题: " + str(parameters[i]))
        try:
            if parameters[i]["add"] != "":
                actions[parameters[i]["Action"]][parameters[i]["Parameters"]]["add"] = json.loads(parameters[i]["add"])
        except Exception as e:
            print("add 格式有问题: " + str(parameters[i]))
        try:
            if parameters[i]["cancel"] != "":
                actions[parameters[i]["Action"]][parameters[i]["Parameters"]]["cancel"] = json.loads(
                    parameters[i]["cancel"])
        except Exception as e:
            print("cancel 格式有问题: " + str(parameters[i]))
        try:
            if parameters[i]["img"] != "":
                actions[parameters[i]["Action"]][parameters[i]["Parameters"]]["img"] = json.loads(parameters[i]["img"])
        except Exception as e:
            print("img 格式有问题: " + str(parameters[i]))
        try:
            if parameters[i]["infoButton"] != "":
                actions[parameters[i]["Action"]][parameters[i]["Parameters"]]["infoButton"] = json.loads(parameters[i]["infoButton"])
        except Exception as e:
            print("infoButton 格式有问题: " + str(parameters[i]))
        try:
            if parameters[i]["input"] != "":
                actions[parameters[i]["Action"]][parameters[i]["Parameters"]]["input"] = json.loads(parameters[i]["input"])
        except Exception as e:
            print("input 格式有问题: " + str(parameters[i]))
        try:
            if parameters[i]["textarea"] != "":
                actions[parameters[i]["Action"]][parameters[i]["Parameters"]]["textarea"] = json.loads(parameters[i]["textarea"])
        except Exception as e:
            print("textarea 格式有问题: " + str(parameters[i]))
        try:
            if parameters[i]["select"] != "":
                actions[parameters[i]["Action"]][parameters[i]["Parameters"]]["select"] = json.loads(parameters[i]["select"])
        except Exception as e:
            print("select 格式有问题: " + str(parameters[i]))

    # print("actions：" + str(actions))

    file_path = os.getcwd().replace("Draw_Process\Generate Parameters", "") + "static\\javascript\\actions.json"
    print(file_path)
    json_str = json.dumps(actions, indent=4)
    with open(file_path, "w") as f:
        f.write(json_str)
        print("加载入文件完成...")


def createModuleJson():
    # 打开文件
    data = xlrd.open_workbook('Actions Parameters.xlsx')
    # 通过文件名获得工作表,获取工作表1
    sheet = data.sheet_by_name('Sheet2')
    print("总行数：" + str(sheet.nrows))

    functions = {}
    # 获取整行的值 和整列的值，返回的结果为数组
    # 整行值：sheet.row_values(start,end)
    for i in range(0, sheet.nrows):
        colValues = sheet.row_values(i)
        functions[colValues[0]] = colValues[1]

    file_path = os.getcwd().replace("Generate Parameters", "") + "functions.json"
    print(file_path)
    json_str = json.dumps(functions, indent=4)
    with open(file_path, "w") as f:
        f.write(json_str)
        print("加载入文件完成...")


if __name__ == '__main__':
    createActionsJson()
    createModuleJson()
