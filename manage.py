# -*-coding:utf-8 -*-
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    if hasattr(sys, 'frozen'):  # 打包版本读取运行时候路径，否则转换为了绝对路径
        pyfile_directory = os.path.dirname(sys.executable) + "\\Draw_Process\\pyfile"
        pyfile_public_directory = os.path.dirname(sys.executable) + "\\Draw_Process\\pyfile\\public"
        pyfile_release_directory = os.path.dirname(os.path.realpath(__file__)) + "\\Draw_Process\\pyfile\\release"
        download_directory = os.path.dirname(os.path.realpath(__file__)) + "\\Draw_Process\\Download"
        temporary_directory = os.path.dirname(os.path.realpath(__file__)) + "\\Draw_Process\\temporary"
    else:
        pyfile_directory = os.path.dirname(os.path.realpath(__file__)) + "\\Draw_Process\\pyfile"
        pyfile_public_directory = os.path.dirname(os.path.realpath(__file__)) + "\\Draw_Process\\pyfile\\public"
        pyfile_release_directory = os.path.dirname(os.path.realpath(__file__)) + "\\Draw_Process\\pyfile\\release"
        download_directory = os.path.dirname(os.path.realpath(__file__)) + "\\Draw_Process\\Download"
        temporary_directory = os.path.dirname(os.path.realpath(__file__)) + "\\Draw_Process\\temporary"
    if not os.path.exists(pyfile_directory):
        print("pyfile_directory not exist and init create")
        os.mkdir(pyfile_directory)
    # else:
    #     print("pyfile_directory exist")
    if not os.path.exists(pyfile_public_directory):
        print("pyfile_public_directory not exist and init create")
        os.mkdir(pyfile_public_directory)
    # else:
    #     print("pyfile_public_directory exist")
    if not os.path.exists(pyfile_release_directory):
        print("pyfile_release_directory not exist and init create")
        os.mkdir(pyfile_release_directory)
    # else:
    #     print("pyfile_release_directory exist")
    if not os.path.exists(download_directory):
        print("download_directory not exist and init create")
        os.mkdir(download_directory)
    # else:
    #     print("download_directory exist")
    if not os.path.exists(temporary_directory):
        print("temporary_directory not exist and init create")
        os.mkdir(temporary_directory)
    # else:
    #     print("temporary_directory exist")

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Python_Platform.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)