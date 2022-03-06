escape_dict = {'\a': r'\a',
               '\b': r'\b',
               '\c': r'\c',
               '\f': r'\f',
               '\n': r'\n',
               '\r': r'\r',
               '\t': r'\t',
               '\v': r'\v',
               '\'': r'\'',
               '\"': r'\"',
               '\0': r'\0',
               '\1': r'\1',
               '\2': r'\2',
               '\3': r'\3',
               '\4': r'\4',
               '\5': r'\5',
               '\6': r'\6',
               '\7': r'\7',
               '\8': r'\8',
               '\9': r'\9'}


def raw_string(str):
    str1 = str
    rstring = ""
    for char in str:  # 防止图片地址发生转义
        try:
            if char in escape_dict:
                rstring += escape_dict[char]
            else:
                rstring += char
        except Exception as e:
            KeyError: print("字符串变量转义发生错误")
    return rstring


def trans_slash(value, type):
    # 替换反斜杠 1、先替换\"为特别奇怪的字符，然后把\替换\\，再把奇怪字符替换回来\"
    # 1、"D:\RPA流程\"+str(costcenterNr)+".xlsx"
    # 2、"=IF(J2-K2=W2,\"数量一致\",\"数量不一致\")"
    # 先解决 \"+ 或者 \" +
    # 再解决 \"
    # 再解决 \
    special_str_include_plus = "forward_slash_include_plus_need_to_be_replaced_for_choclead"
    special_str = "forward_slash_need_to_be_replaced_for_choclead"
    if "\\\"+" in value:
        value = value.replace("\\\"+", special_str_include_plus)
    if "\\\" +" in value:
        value = value.replace("\\\" +", special_str_include_plus)
    if "\\\"" in value:
        value = value.replace("\\\"", special_str)

    if type == "yes":
        if "\\" in value:
            value = value.replace("\\", "\\\\")

    # 再转化回来
    if special_str in value:
        value = value.replace(special_str, "\\\"")
    # 再转化回来
    if special_str_include_plus in value:
        value = value.replace(special_str_include_plus, "\\\\\" +")
    if value[len(value) - 2:] == "\\\"":
        # 增加逻辑，替换最后一个"\\\""
        value = value[0:len(value) - 2] + "\\\\\""
        # value = value.replace("\\\"", "\\\\\"")
    # print(value)
    return value
