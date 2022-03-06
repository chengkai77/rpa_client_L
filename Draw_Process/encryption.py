# import binascii
# # from pyDes import des, CBC, PAD_PKCS5
# #
# #
# # def get_secret_key(path):
# #     with open(path, 'r', encoding='utf-8') as ff:
# #         setting_content = ff.readlines()
# #         for i in range(len(setting_content)):
# #             setting_list = setting_content[i].rstrip("\n").split("=")
# #             if 'secret_key' in setting_list[0]:
# #                 secret_key = setting_list[1].replace(" ", "")
# #                 return secret_key
# #         return None
# #
# #
# # def des_encrypt(s, path):
# #     """
# #     DES 加密
# #     :param path:
# #     :param s: 原始字符串
# #     :return: 加密后字符串，16进制
# #     """
# #     secret_key = get_secret_key(path)
# #     iv = secret_key
# #     k = des(secret_key, CBC, iv, pad=None, padmode=PAD_PKCS5)
# #     en = k.encrypt(s, padmode=PAD_PKCS5)
# #     res_encrypt = binascii.b2a_hex(en)
# #     return "ChocLead_encrypt: " + str(res_encrypt, encoding="utf-8")
# #
# #
# # def des_encrypt_by_key(s, secret_key):
# #     """
# #     DES 加密
# #     :param path:
# #     :param s: 原始字符串
# #     :return: 加密后字符串，16进制
# #     """
# #     secret_key = secret_key
# #     iv = secret_key
# #     k = des(secret_key, CBC, iv, pad=None, padmode=PAD_PKCS5)
# #     en = k.encrypt(s, padmode=PAD_PKCS5)
# #     res_encrypt = binascii.b2a_hex(en)
# #     return "ChocLead_encrypt: " + str(res_encrypt, encoding="utf-8")
# #
# #
# # def des_descrypt(s, path):
# #     """
# #     DES 解密
# #     :param path:
# #     :param s: 加密后的字符串，16进制
# #     :return: 解密后的字符串
# #     """
# #     secret_key = get_secret_key(path)
# #     iv = secret_key
# #     if "ChocLead_encrypt: " in s:
# #         s = s.replace("ChocLead_encrypt: ", "")
# #     k = des(secret_key, CBC, iv, pad=None, padmode=PAD_PKCS5)
# #     de = k.decrypt(binascii.a2b_hex(s), padmode=PAD_PKCS5)
# #     return str(de, encoding="utf-8")
# #
# #
# # def is_encrypt(s):
# #     if "ChocLead_encrypt: " in s:
# #         return True
# #     else:
# #         return False
# #
# #
# # if __name__ == '__main__':
# #     path = 'D:\RPA Client\client 20210219\password_key.txt'
# #     str_en = des_encrypt('Sunnic1988!@S@', path)
# #     print(str_en)
# #     str_de = des_descrypt(str_en, path)
# #     print(str_de)


# 上部分是DES加密，被下部分AES取代
# coding:utf-8
import base64
from Crypto.Cipher import AES


# 判断是否加密过
def is_encrypt(s):
    if "ChocLead_encrypt: " in s:
        return True
    else:
        return False


# 获取秘钥文件中的key
def get_secret_key(path):
    with open(path, 'r', encoding='utf-8') as ff:
        setting_content = ff.readlines()
        for i in range(len(setting_content)):
            setting_list = setting_content[i].rstrip("\n").split("=")
            if 'secret_key' in setting_list[0]:
                secret_key = setting_list[1].replace(" ", "")
                return secret_key
        return None


# 解密
def aes_decode(data, path):
    if "ChocLead_encrypt: " in data:
        data = data.replace("ChocLead_encrypt: ", "")
    key = get_secret_key(path)
    print("key值：", key)
    try:
        while len(key) % 16 != 0:  # 补足key长度为16的倍数
            key += (16 - len(key) % 16) * chr(16 - len(key) % 16)
        aes = AES.new(str.encode(key), AES.MODE_ECB)  # 初始化加密器
        decrypted_text = aes.decrypt(base64.decodebytes(bytes(data, encoding='utf8'))).decode("utf8")  # 解密
        decrypted_text = decrypted_text[:-ord(decrypted_text[-1])]  # 去除多余补位
    except Exception as e:
        pass
    return decrypted_text


# 加密
def aes_encode(data, path):
    key = get_secret_key(path)
    print("key值：", key)
    while len(data) % 16 != 0:  # 补足字符串长度为16的倍数
        data += (16 - len(data) % 16) * chr(16 - len(data) % 16)
    while len(key) % 16 != 0:  # 补足key长度为16的倍数
        key += (16 - len(key) % 16) * chr(16 - len(key) % 16)
    data = str.encode(data)
    aes = AES.new(str.encode(key), AES.MODE_ECB)  # 初始化加密器
    aes_res = str(base64.encodebytes(aes.encrypt(data)), encoding='utf8').replace('\n', '')  # 加密
    return "ChocLead_encrypt: " + str(aes_res)


# 加密
def aes_encode_by_key(data, key):
    print("key值：", key)
    while len(data) % 64 != 0:  # 补足字符串长度为16的倍数
        data += (64 - len(data) % 64) * chr(64 - len(data) % 64)
    while len(key) % 32 != 0:  # 补足key长度为16的倍数
        key += (32 - len(key) % 32) * chr(32 - len(key) % 32)
    data = str.encode(data)
    aes = AES.new(str.encode(key), AES.MODE_ECB)  # 初始化加密器
    aes_res = str(base64.encodebytes(aes.encrypt(data)), encoding='utf8').replace('\n', '')  # 加密
    return "ChocLead_encrypt: " + str(aes_res)


if __name__ == '__main__':
    key = '12345678g01234ab'  # 密钥长度必须为16、24或32位，分别对应AES-128、AES-192和AES-256
    path = r'D:\RPA Client\client 20210219\password_key.txt'
    data = "198876"  # 待加密文本

    mi = aes_encode(data, path)
    print("加密值：", mi)
    print("解密值：", aes_decode(mi, path))