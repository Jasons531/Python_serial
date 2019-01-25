

# -*- coding: utf-8 -*-
import sys

from PyQt5 import QtWidgets
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtCore import QDir

from PyQt5 import QtCore
from PyQt5.QtCore import QCoreApplication

import serial
import serial.tools.list_ports
import binascii
import os
import time
import operator
import myserialmain

#继承 QThread 类
class BigWorkThread(QtCore.QThread):
    """docstring for BigWorkThread"""
    def __init__(self, parent=None):
        super(BigWorkThread, self).__init__(parent)

    #重写 run() 函数，在里面干大事。
    def run(self):
        #大事
        self.downloading.recv_text.append("测试烧写")
        time.sleep(1)