
# -*- coding: utf-8 -*-
# download后面改为后台线程运行

import sys
from myserial import Ui_MainWindow
from PyQt5 import QtWidgets
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtCore import QDir

from PyQt5 import QtCore
from PyQt5.QtCore import *

import serial
import serial.tools.list_ports
import binascii
import os
import time
import operator
import threading

counter = 0

send_num = 0

recv_data = ''
recv_num = 0

data_num_sended = 0

ser = serial.Serial()

filetype = ''

# 继承QThread
class Runthread(QtCore.QThread):
    # python3,pyqt5与之前的版本有些不一样
    #  通过类成员对象定义信号对
    sinOut = pyqtSignal(str, int, int)

    def __init__(self, parent=None):
        super(Runthread, self).__init__()

    def __del__(self):
        self.wait()

    def run(self):

        global filetype
        global recv_data
        # 串口操作命令
        self.serialoperation = 0

        self.progress = 0

        # 串口命令下标
      #  self.cmdindex = 0

        # 串口命令最大下标
       # self.cmdmaxindex = 3
        if ser.isOpen():
            self.checkoutbuf = ['7f00\r\n', '9f00\r\n', 'af00\r\n']
            self.checkout = []

            for i in range(len(self.checkoutbuf)):
                self.checkout.append(self.checkoutbuf[i].encode())  # 将字符串编码为bytes

            # 发送擦除命令 0x7f 0x0a
            # 等待接收到: 0x7f 0x00,非0x00则失败需要再次发送命令
            # 接收到命令成功后开始发送烧写数据max_size = 128B 0x9f 0X00
            # 等待接收命令: 0xAF 0x00, 非0x00则烧写失败，需要再次发送当前数据进行烧写，重发5次烧写失败则再次下发擦除命令
            # 发送完最后一帧数据后，下发0xaf 0x0A，退出烧写模式，若没接收到0x9f 0x00则需要再次重发

            self.eraseflash()
            self.programme()
            self.gotoapp()


    def eraseflash(self):
            # 下载长度累计
            self.counterlen = 0
            # 下载次数计算
            self.counterdownload = 0

            if ser.isOpen():

                self.flash_data = b'\x7f'  # 定义bytes : b'\x...'
                self.flash_data += b'\x55'
                self.flash_data += b'\xaa'
                self.write_len = ser.write(self.flash_data)
                ser.flush()
                time.sleep(0.8)

                try:
                    self.size = ser.inWaiting()
                except ValueError:
                    pass

                if self.size > 0:
                    recv_data = ''
                    recv_data = ser.read(self.size)

                    if recv_data != '':
                        self.size = len(recv_data)
                        # 清除接收缓存
                        ser.flushInput()
                        file_str = recv_data.decode('iso-8859-1')

                        if recv_data == self.checkout[0]:
                            file_str += "  Flash Erase Is Sucess!!!"
                        else:
                            file_str += "  Flash Erase Is Fail!!!" + str(recv_data)
                        self.sinOut.emit(file_str, 0, self.progress)

                        self.size = 0
                else:
                    file_str = "串口关闭"
            file_str = ""
            self.sinOut.emit(file_str, 0, self.progress)

    def programme(self):
            # 下载长度累计
            self.counterlen = 0
            # 下载次数计算
            self.counterdownload = 0

            # 进度条每次计数
            self.progressadd = 0

            f = open(filetype[0], 'rb')  # ''' rb : read bin file'''
            self.read_addr = 0
            # 获取下载文件大小
            self.length = os.path.getsize(filetype[0])

            self.counterdownload = self.length//128
            if self.length % 128 != 0:
                self.counterdownload += 1

            # 获取每次进度条加的数值
            self.progressadd = 100//self.counterdownload
            if 100 % self.counterdownload != 0:
                self.progressadd += 1

            while self.counterdownload > 0:
                if ser.isOpen():
                    self.read_addr = f.tell()  # 获取读开始地址

                    f.seek(self.read_addr, 0)  # 从起始位置即文件首行首字符开始移动 x 个字符

                    self.flash_data = b'\x9f'  # 定义bytes : b'\x...'

                    if self.length - self.counterlen >= 128:
                        self.flash_data += f.read(128)
                    else:
                        self.flash_data += f.read(self.length - self.counterlen)
                    self.flash_data += b'\x55'
                    self.flash_data += b'\xaa'

                    time.sleep(0.6)  # 400ms预留处理
                    self.write_len = ser.write(self.flash_data)
                    ser.flush()
                    time.sleep(0.6)

                    try:
                        self.size = ser.inWaiting()
                    except ValueError:
                        pass

                    if self.size > 0:
                        recv_data = ''
                        recv_data = ser.read(self.size)
                        #   self.recv_text.insertPlainText("size: " + str(self.size))
                        if recv_data != '':
                            self.size = len(recv_data)
                            # 清除接收缓存
                            ser.flushInput()
                            file_str = recv_data.decode('iso-8859-1')
                            file_str += "开始写地址： " + str(self.read_addr) + "下载倒计数: " + str(self.counterdownload)
                            if recv_data[-6:] == self.checkout[1]:
                                file_str += "  Flash Download Is Sucess!!!"
                                self.progress += self.progressadd
                            else:
                                file_str += "  Flash Download Is Fail!!!" + str(recv_data[-6:])
                            self.sinOut.emit(file_str, 0, self.progress)

                            self.size = 0
                    self.counterlen += 128
                    self.counterdownload -= 1

                else:
                    file_str = "串口关闭"
                    break
            f.close()
            file_str = ""
            self.sinOut.emit(file_str, 0, self.progress)

    def gotoapp(self):
            # 下载长度累计
            self.counterlen = 0
            # 下载次数计算
            self.counterdownload = 0

            if ser.isOpen():

                self.flash_data = b'\xaf'  # 定义bytes : b'\x...'
                self.flash_data += b'\x55'
                self.flash_data += b'\xaa'
                self.write_len = ser.write(self.flash_data)
                ser.flush()
                time.sleep(0.8)

                try:
                    self.size = ser.inWaiting()
                except ValueError:
                    pass

                if self.size > 0:
                    recv_data = ''
                    recv_data = ser.read(self.size)

                    if recv_data != '':
                        self.size = len(recv_data)
                        # 清除接收缓存
                        ser.flushInput()
                        file_str = recv_data.decode('iso-8859-1')

                        if recv_data == self.checkout[2]:
                            file_str += "  Go to Is Sucess!!!"
                        else:
                            file_str += "  Go to Is Fail!!!" + str(recv_data)
                        self.sinOut.emit(file_str, 0, self.progress)

                        self.size = 0
                else:
                    file_str = "串口关闭"
            file_str = ""
            self.sinOut.emit(file_str, 1, self.progress)



class mywindow(QtWidgets.QWidget, Ui_MainWindow):

    def __init__(self):
        super(mywindow, self).__init__()
        self.setupUi(self)
        self.init()
        self.setserial()

        # 定义全局串口
        global ser

        """设置按钮颜色"""
        self.pushButton_open.setStyleSheet("background-color:white")

    def init(self):
        global send_num
        global data_num_sended
        data_num_sended = 0
        num = 0
        """按钮与鼠标点击事件相关联"""
        self.pushButton_open.clicked.connect(self.openserial_click)
        self.pushButton_send.clicked.connect(self.data_send)
        self.pushButton_clearsend.clicked.connect(self.clear_send)
        self.pushButton_clear.clicked.connect(self.clear_recv)
        '''定时器接收数据'''
        self.timer = QTimer()
        self.timer.timeout.connect(self.receive_data)

        '''下载文件功能'''
        self.openfile.clicked.connect(self.getpath)
        self.pushButton_download.clicked.connect(self.download)

        # 创建线程
        self.thread = Runthread()
        # 连接信号
        self.thread.sinOut.connect(self.callbacklog)

        '''数据保存功能 --- 1.23'''

        '''显示时间功能 --- 1.23'''

        '''烧写协议 --- 1.23'''

    def setserial(self):

        # 串口波特率
        brate = ['460800', '256000', '230400', '128000', '115200', '76800', '9600', '4800']
        for index in range(len(brate)):
            self.comboBox_brate.addItem(brate[index])
        self.comboBox_brate.setCurrentIndex(6)  # 设置默认显示数值
        # 停止位
        stop = ['1', '1.5', '2']
        for index in range(len(stop)):
            self.comboBox_stop.addItem(stop[index])

        # 数据位
        data = ['7', '8', '9']
        for index in range(len(data)):
            self.comboBox_byte.addItem(data[index])
        self.comboBox_byte.setCurrentIndex(1)  # 设置默认显示数值

        # 奇偶校验位
        crc = ['无', '奇校验', "偶校验"]
        for index in range(len(crc)):
            self.comboBox_parity.addItem(crc[index])

        port_list = list(serial.tools.list_ports.comports())

        if len(port_list) <= 0:
            self.recv_text.append("The Serial port can't find!")
            self.pushButton_open.setText("打开")
        else:
            for id in range(len(port_list)):
                port_list_0 = list(port_list[id])
                port_serial = port_list_0[0]
                self.comboBox_serialid.addItem(port_serial)

    def openserial_click(self):
        """定义全局变量"""
        global counter

        counter += 1

        if counter % 2 == 0:
            self.pushButton_open.setText("打开")
            self.pushButton_open.setStyleSheet("background-color:white")

            try:
                ser.port = self.comboBox_serialid.currentText()
                ser.close()
                self.timer.stop()
            except ValueError:
                pass
            self.pushButton_open.setText("打开")
        else:
            """串口操作"""
            ser.port = self.comboBox_serialid.currentText()
            ser.baudrate = int(self.comboBox_brate.currentText())
            ser.bytesize = int(self.comboBox_byte.currentText())
            ser.stopbits = int(self.comboBox_stop.currentText())
            ser.TImeout = 2

            if "无" == self.comboBox_parity.currentText():
                ser.parity = 'N'
            elif "奇校验" == self.comboBox_parity.currentText():
                ser.parity = 'O'
            else:
                ser.parity = 'E'
            self.pushButton_open.setText("关闭")
            self.pushButton_open.setStyleSheet("background-color:red")
            try:
                ser.port = self.comboBox_serialid.currentText()

                ''''注意serial必须设置DTR RTS为拉低状态，否则可能会造成硬件设备进入Bootloader '''
                # 进boot DTR = 0 RTS = 1
                ser.setDTR(0)
                ser.setRTS(0)
                ser.open()
            except ValueError:
                QMessageBox.information(self, "Port Error", "此串口不能被打开！")
                # self.recv_text.append("The Serial port is open fail")
                return None
        if ser.is_open:
            # 打开串口接收定时器，周期为2ms
            self.timer.start(2)
          #  self.recv_text.append("is_open:")

    def data_send(self):
        global send_num
        global data_num_sended
        if ser.is_open:
            get_data = self.textEdit.toPlainText()
            if self.checkBox_newline.isChecked():
                get_data += "\r\n"
            if get_data != "":
                if self.checkBox_sendhex.isChecked():
                    # hex发送
                    get_data = get_data.strip()
                    #self.recv_text.append("hex:" + get_data)
                    send_list = []

                    while get_data != '':
                        if (len(get_data[0:2]) % 2) == 0:
                            try:
                                send_num = 0
                                send_num = int(get_data[0:2], 16)  # 16进制转10进制

                            except ValueError:
                                self.recv_text.append('wrong data 请输入十六进制数据!')
                                QMessageBox.information(self, 'wrong data', '请输入十六进制数据!')
                                return None
                        else:
                            self.recv_text.append("16进制数据非偶数错误")
                            return None

                        get_data = get_data[2:].strip()  # 过滤掉前面已转换数据，同时过滤掉空格
                        # self.recv_text.append("get_data:" + get_data)
                        send_list.append(send_num)
                        # self.recv_text.append("num: " + str(send_num))
                    get_data = bytes(send_list)
                else:
                    # ascii发送
                    get_data = get_data.encode('utf-8')

                send_num = ser.write(get_data)
                data_num_sended += send_num
               # self.recv_text.append("RecvLen: " + str(send_num))
               # self.recv_text.append("get data: " + str(get_data))
            else:
                pass
        else:
            pass

    def clear_send(self):
        self.textEdit.setText("")

    def clear_recv(self):
        self.recv_text.setText("")

    def receive_data(self):
        global recv_data
        global recv_num

        if ser.is_open:
            try:
                self.size = ser.inWaiting()
            except ValueError:
                pass

            if self.size > 0:
                recv_data = ''
                recv_data = ser.read(self.size)
             #   self.recv_text.insertPlainText("size: " + str(self.size))
                if recv_data != '':
                    self.size = len(recv_data)
                    # 清除接收缓存
                    ser.flushInput()

                    if self.checkBox_hex.isChecked():
                        self.recv_text.insertPlainText(binascii.b2a_hex(recv_data).decode())
                    else:
                        self.recv_text.insertPlainText(recv_data.decode('iso-8859-1'))

                    recv_num += self.size
                    self.size = 0

                    # 获取到text光标
                    textCursor = self.recv_text.textCursor()
                    # 滚动到底部
                    textCursor.movePosition(textCursor.End)
                    # 设置光标到text中去
                    self.recv_text.setTextCursor(textCursor)
                else:
                    pass
            else:
                pass

    def getpath(self):
        global filetype
        filetype = QFileDialog.getOpenFileName(self,"QFileDialog.getOpenFileName()", "./", "Bin Files (*.bin);;Txt Files (*.txt);;Hex Files (*.hex)")  # 设置文件扩展名过滤,注意用双分号间隔

        if filetype[0]:
           self.recv_text.append(filetype[0])
           self.comboBox_path.addItem(filetype[0])

           ''' 相对路径 '''
         #  cur_path = QDir('.')
         #  relative_path = cur_path.relativeFilePath(filetype[0])
         #  self.recv_text.append(relative_path)
        else:
            pass

    def download(self):
        if self.checkBox_file.isChecked():
            if filetype[0]:
                # 开始线程
                self.timer.stop()
                self.progressBar.setValue(0)
                self.thread.start()
        else:
            pass

    def callbacklog(self, file_inf, timerrest, progress):
        self.recv_text.append(file_inf)

        self.progressBar.setValue(progress)

        if timerrest == 1:
            self.timer.start(2)

        # 获取到text光标
        textCursor = self.recv_text.textCursor()
        # 滚动到底部
        textCursor.movePosition(textCursor.End)
        # 设置光标到text中去
        self.recv_text.setTextCursor(textCursor)


if __name__=="__main__":

    app=QtWidgets.QApplication(sys.argv)
    myshow=mywindow()
    myshow.show()

    sys.exit(app.exec_())
