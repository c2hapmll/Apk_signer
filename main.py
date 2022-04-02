#!/usr/bin/env python3
# coding:utf-8

import re
import os
import subprocess
import sys
import time
import shlex
import datetime
import threading
import logging

from PyQt5.QtWidgets import QApplication, QWidget, QDesktopWidget, QPushButton, QVBoxLayout, QTextEdit
from PyQt5.QtGui import QIcon

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_IF = 0


def execute_command(cmd_string, cwd=None, timeout=None, shell=True, return_value=False):
    """
         执行一个SHELL命令 封装了subprocess的Popen方法, 支持超时判断，支持读取stdout和stderr
        :parameter:
              cwd: 运行命令时更改路径，如果被设定，子进程会直接先更改当前路径到cwd
              timeout: 超时时间，秒，支持小数，精度0.1秒
              shell: 是否通过shell运行
        :return return_code
        :exception 执行超时
    """

    if shell:
        cmd_string_list = cmd_string
    else:
        cmd_string_list = shlex.split(cmd_string)
    if timeout:
        end_time = datetime.datetime.now() + datetime.timedelta(seconds=timeout)

    sub = subprocess.Popen(cmd_string_list,
                           cwd=cwd,
                           stdin=subprocess.PIPE,
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE,
                           shell=True, bufsize=4096)
    # todo
    (stdout, stderr) = sub.communicate()

    while sub.poll() is None:
        time.sleep(0.1)
        if timeout:
            if end_time <= datetime.datetime.now():
                raise Exception("Timeout：%s" % cmd_string)

    logging.debug(stdout)
    logging.debug(stderr)

    if return_value:
        return stdout
    else:
        result = str(sub.returncode)
        return result


def get_package_name(apk_path):
    p = subprocess.Popen("aapt dump badging %s" % apk_path, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE,
                         stdin=subprocess.PIPE, shell=True)
    (output, err) = p.communicate()
    match = re.compile("package: name='(\\S+)' versionCode='(\\d+)' versionName='(\\S+)'").match(output.decode())
    if not match:
        raise Exception("can't get package info")
    packagename = match.group(1)
    # versionCode = match.group(2)
    # versionName = match.group(3)

    print('packagename:' + packagename)
    return packagename


def install_apk(apk_path):
    adb_path = os.path.join("bin", "adb.exe")
    try:
        cmd = "%s install %s" % (adb_path, apk_path)
        res = os.popen(cmd).read()
        return res
    except RuntimeError:
        return -1


def uninstall_apk(packagename):
    adb_path = os.path.join("bin", "adb.exe")
    try:
        cmd = "%s uninstall %s" % (adb_path, packagename)
        res = os.popen(cmd).read()
        return res
    except RuntimeError:
        return -1


def v1_singer(apk_path):
    jre_path = os.path.join("bin", "java.exe")
    jarsinger_path = os.path.join("bin", "jarsigner.exe")
    test_keystore_path = os.path.join("Assets", "test.jks")
    out_apk = apk_path.replace(".apk", "_V1.apk").replace('\n', '').replace('\r', '')

    # cmd = "%s -jar %s -verbose -keystore %s -signedjar %s %s -storepass 123456 mykey" % (
    #     jre_path, jarsinger_path, test_keystore_path, out_apk, apk_path.replace('\n', '').replace('\r', ''))
    cmd = "jarsigner -verbose -keystore %s -signedjar %s %s -storepass 123456 mykey" % (
           test_keystore_path, out_apk, apk_path.replace('\n', '').replace('\r', ''))
    print(cmd)
    # jarsigner -verbose -keystore [jks路径] -signedjar [V1签名完后apk文件输出路径] [需要签名的apk路径] [签名文件别名]
    res = execute_command(cmd)
    return res


def v2_singer(apk_path):
    jre_path = os.path.join("bin", "jre1.8.0_321", "bin", "java.exe")
    apksigner_path = os.path.join("bin", "apksigner.jar")
    test_keystore_path = os.path.join("Assets", "test.jks")
    out_apk = apk_path.replace(".apk", "_V2.apk").replace('\n', '').replace('\r', '')

    cmd = "%s -jar %s sign -ks %s --ks-pass pass:123456 --out %s  %s" % (jre_path, apksigner_path, test_keystore_path, out_apk, apk_path.replace('\n', '').replace('\r', ''))
    res = execute_command(cmd)
    print(cmd)
    return res


def singer_check(apk_path):
    # apksigner verify -v [APK的路径]
    cmd = "apksigner verify -v %s" % apk_path
    result = execute_command(cmd, return_value=True)
    return result.decode()


def clear_apk_log():
    cmd = "adb logcat -c"
    os.popen(cmd).read()
    cmd = "adb logcat -G 10M"
    os.popen(cmd)
    return 0


def get_apk_log():
    desktop_path = get_desktop()
    log_path = os.path.join(desktop_path, "log_%s.h" % time.strftime('%H_%M_%S', time.localtime()))
    cmd = "adb logcat > %s" % log_path
    # cmd = "adb logcat"
    if LOG_IF == 1:
        p = subprocess.Popen(cmd,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,
                             stdin=subprocess.PIPE,
                             shell=True)


def environmental_inspection():
    environmental_list = []
    cmd = "adb --version"
    result = execute_command(cmd)
    if result == 0:
        environmental_list.append("False")
    else:
        environmental_list.append("True")

    cmd = "java -version"
    result = execute_command(cmd)
    if result == 0:
        environmental_list.append("False")
    else:
        environmental_list.append("True")

    cmd = "apksigner --version"
    result = execute_command(cmd)
    if result == 0:
        environmental_list.append("False")
    else:
        environmental_list.append("True")

    cmd = "aapt v"
    result = execute_command(cmd)
    if result == 0:
        environmental_list.append("False")
    else:
        environmental_list.append("True")

    cmd = "jarsigner"
    result = execute_command(cmd)
    if result == 0:
        environmental_list.append("False")
    else:
        environmental_list.append("True")

    return environmental_list


# 定位桌面
def get_desktop():
    return os.path.join(os.path.expanduser("~"), 'Desktop')


class Example(QWidget):
    def __init__(self):
        super().__init__()

        self.paths = ""
        self.packagename = ""
        self.layout = None
        self.label1 = None
        self.label2 = None
        self.label3 = None
        self.label4 = None
        self.label5 = None
        self.label6 = None
        self.label7 = None
        self.textEdit = None
        self.init_ui()  # 界面绘制交给InitUi方法
        self.setAcceptDrops(True)  # 允许控件接受文件

    def init_ui(self):
        self.layout = QVBoxLayout()

        self.label1 = QPushButton("安装")
        self.label1.clicked.connect(self.on_label1_func)

        self.label2 = QPushButton("卸载")
        self.label2.clicked.connect(self.on_label2_func)

        self.label3 = QPushButton("V1签名")
        self.label3.clicked.connect(self.on_label3_func)

        self.label4 = QPushButton("V2签名")
        self.label4.clicked.connect(self.on_label4_func)

        self.label5 = QPushButton("签名检查")
        self.label5.clicked.connect(self.on_label5_func)

        self.label6 = QPushButton("日志抓取")
        self.label6.clicked.connect(self.on_label6_func)

        self.label7 = QPushButton("环境检查")
        self.label7.clicked.connect(self.on_label7_func)

        self.textEdit = QTextEdit()
        self.textEdit.append("请拖动APK到此窗口")
        self.textEdit.setReadOnly(True)

        self.layout.addWidget(self.label1)
        self.layout.addWidget(self.label2)
        self.layout.addWidget(self.label3)
        self.layout.addWidget(self.label4)
        self.layout.addWidget(self.label5)
        self.layout.addWidget(self.label6)
        self.layout.addWidget(self.label7)
        self.layout.addWidget(self.textEdit)

        # 设置垂直盒布局的控件间距大小
        # self.layout.setSpacing(50)
        self.setLayout(self.layout)

        # 设置窗口的位置和大小
        self.resize(250, 600)
        self.center()
        # 设置窗口的标题
        self.setWindowTitle('Apk tools')
        # 设置窗口的图标，引用当前目录下的web.png图片
        self.setWindowIcon(QIcon('Assets/tools.png'))

        # 显示窗口
        self.show()

    # 安装按钮
    def on_label1_func(self):
        if self.paths == "":
            self.textEdit.append('未选择APK文件!\n')
            return -1
        else:
            uninstall_apk(self.packagename)
            self.textEdit.append('正在安装,请稍后...!\n')
            sing_thread = threading.Thread(target=install_apk, args=(self.paths,))
            sing_thread.start()
            return 0

    def on_label2_func(self):
        uninstall_apk(self.packagename)
        return 0

    def on_label3_func(self):
        self.textEdit.append("\n正在进行V1签名，请稍后...")
        time.sleep(1)
        sing_thread = threading.Thread(target=v1_singer, args=(self.paths, ))
        sing_thread.start()

    def on_label4_func(self):
        # v2_singer(self.paths)
        sing_thread = threading.Thread(target=v2_singer, args=(self.paths,))
        sing_thread.start()
        return 0

    def on_label5_func(self):
        # v2_singer(self.paths)
        res = singer_check(self.paths)
        self.textEdit.append("\n" + res)
        return 0

    def on_label7_func(self):
        en_list = environmental_inspection()
        cn_list = ["ADB:", "JAVA:", "apksigner:", "aapt:", "jarsigner:"]
        count = 0
        for i in en_list:
            self.textEdit.append(cn_list[count] + i)
            count += 1
        return 0

    # 控制窗口显示在屏幕中心的方法
    def center(self):
        # 获得窗口
        qr = self.frameGeometry()
        # 获得屏幕中心点
        cp = QDesktopWidget().availableGeometry().center()
        # 显示到屏幕中心
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    # 拖放文件重写
    def dragEnterEvent(self, event):
        file = event.mimeData().urls()[0].toLocalFile()
        if file not in self.paths:  # ==> 去重显示
            self.paths = ""
            self.paths += file + "\n"
            print("拖拽的文件 ==> {}".format(file))
            self.packagename = get_package_name(self.paths)
            self.textEdit.append("\n应用路径为：%s" % self.paths)
            self.textEdit.append("应用包名为：%s" % self.packagename)

    def dragLeaveEvent(self, event):
        self.setWindowTitle('鼠标放开了')

    def on_label6_func(self):
        global LOG_IF
        if 1 == LOG_IF:
            LOG_IF = 0
            self.label6.setText("抓取日志")
        else:
            LOG_IF = 1
            self.label6.setText("停止抓取")
        time.sleep(1)
        print(LOG_IF)
        clear_apk_log()
        sing_thread = threading.Thread(target=get_apk_log())
        sing_thread.start()
        # get_apk_log()
        return 0


if __name__ == '__main__':
    # 创建应用程序和对象
    app = QApplication(sys.argv)
    ex = Example()
    sys.exit(app.exec_())
