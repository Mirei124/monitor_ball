import asyncio
import math
import os
import sys

import psutil
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QRect
from PyQt5.QtGui import QPixmap, QPainter, QCursor, QFont, QColor, QPainterPath, QBrush
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QMenu, QAction

base_path = getattr(sys, '_MEIPASS', '.') + '/'


# def w_log(msg):
#     print(time.strftime('%H:%M:%S ') + str(msg))


class UI(QWidget):
    def __init__(self):
        super().__init__()
        # Qt.WindowStaysOnTopHint |
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # 设置大小 200px 124px
        self.resize(200, 124)

        # 设置位置
        try:
            with open(os.getenv('APPDATA') + '\\' + 'monitor.txt', 'r') as fp:
                pos_x = int(fp.readline())
                pos_y = int(fp.readline())
                self.move(pos_x, pos_y)
        except FileNotFoundError:
            pass
        except ValueError:
            fp.close()

        # 背景
        self.bg = QPixmap(base_path + 'bg.png')

        # 窗口置顶状态
        self.is_top = False
        # 标记拖动状态
        self.m_drag = False
        # 鼠标相对窗口位置
        self.m_drag_position = None
        # 内存使用率
        self.ram_percent = 80

        # 内存占用圆圈
        self.pix = QPixmap(90, 90)
        self.pix.fill(Qt.transparent)

        # 内存占用
        self.ram_label = QLabel(self)
        self.ram_label.setText('00<font size="1">%</font>')
        self.ram_font = QFont("KaiTi", 22, QFont.Bold)
        self.ram_label.setFont(self.ram_font)
        self.ram_label.setStyleSheet('color: #3c4c68;')
        self.ram_label.move(25, 35)

        # CPU温度
        self.cpu_tem_label = QLabel(self)
        self.cpu_tem_label.setText('00<font size="1">℃</font>')
        self.tem_font = QFont("KaiTi", 10)
        self.cpu_tem_label.setFont(self.tem_font)
        self.cpu_tem_label.setStyleSheet('color: #3c4c68;')
        self.cpu_tem_label.move(38, 75)

        self.net_font = QFont("KaiTi", 10)
        # 上传速度
        self.net_up_label = QLabel(self)
        self.net_up_label.setText('000 K/s')
        self.net_up_label.setFont(self.net_font)
        self.net_up_label.setStyleSheet('color: #3c4c68;')
        self.net_up_label.move(110, 40)
        # 下载速度
        self.net_down_label = QLabel(self)
        self.net_down_label.setText('000 K/s')
        self.net_down_label.setFont(self.net_font)
        self.net_down_label.setStyleSheet('color: #3c4c68;')
        self.net_down_label.move(110, 70)

        # 右键菜单
        self.main_menu = QMenu()

        self.top_act = QAction('置顶', self)
        self.exit_act = QAction('退出', self)

        self.main_menu.addAction(self.top_act)
        self.main_menu.addAction(self.exit_act)

        self.top_act.triggered.connect(self.set_top)
        self.exit_act.triggered.connect(self.app_quit)

        # 加载qss
        with open(base_path + 'style.qss', 'r') as fp:
            self.main_menu.setStyleSheet(fp.read())

        # 数据更新线程
        self.update_thread = Data()
        self.update_thread.ram_signal.connect(self.set_ram)
        self.update_thread.net_up_signal.connect(self.set_net_up)
        self.update_thread.net_down_signal.connect(self.set_net_down)
        self.update_thread.cpu_tem_signal.connect(self.set_cpu_tem)
        # 启动线程
        self.update_thread.start()

    # 绘制背景
    def paintEvent(self, event):
        painter = QPainter(self)
        # 绘制背景
        # painter.drawPixmap(0, 0, self.bg.scaled(self.bg.width(), self.bg.height(), Qt.IgnoreAspectRatio,
        #                                         Qt.SmoothTransformation))
        painter.drawPixmap(0, 0, self.bg)

        # 绘制圆圈
        painter.drawPixmap(5, 17, self.pix)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.m_drag = True
            self.m_drag_position = event.globalPos() - self.pos()
            event.accept()
            self.setCursor(QCursor(Qt.OpenHandCursor))

    def mouseMoveEvent(self, q_mouse_event):
        if Qt.LeftButton and self.m_drag:
            self.move(q_mouse_event.globalPos() - self.m_drag_position)
            q_mouse_event.accept()

    def mouseReleaseEvent(self, q_mouse_event):
        self.m_drag = False
        self.setCursor(QCursor(Qt.ArrowCursor))

    def contextMenuEvent(self, event):
        self.main_menu.exec_(QCursor.pos())

    def set_top(self):
        if self.is_top:
            self.top_act.setText('置顶')
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
            self.is_top = False
            self.show()
        else:
            self.top_act.setText('取消置顶')
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
            self.is_top = True
            self.show()

    def app_quit(self):
        with open(os.getenv('APPDATA') + '\\' + 'monitor.txt', 'w') as fp:
            pos = str(self.x()) + '\n' + str(self.y())
            fp.write(pos)
        self.destroy()

    def set_ram(self, ram_percent):
        self.ram_label.setText(f'{ram_percent}<font size="1">%</font>')
        self.ram_percent = ram_percent

        # global flag
        # if flag == 0:
        #     a = 100
        # else:
        #     a = 50
        # w_log('-' * 10)
        # w_log('debug1')
        painter = QPainter(self.pix)
        self.paint_ram_circle(painter)
        self.update()
        # flag = 1
        # w_log('-' * 10)

    def set_net_up(self, net_up_speed):
        self.net_up_label.setText(net_up_speed)

    def set_net_down(self, net_down_speed):
        self.net_down_label.setText(net_down_speed)

    def set_cpu_tem(self, cpu_tem):
        # 设置温度标签颜色
        if cpu_tem < 45:
            self.cpu_tem_label.setStyleSheet('color: #3c4c68;')
        elif cpu_tem < 65:
            self.cpu_tem_label.setStyleSheet('color: #ec8f6a;')
        else:
            self.cpu_tem_label.setStyleSheet('color: #ef4b4b;')

        self.cpu_tem_label.setText(f'{cpu_tem}<font size="1">℃</font>')

    def paint_ram_circle(self, painter):
        ram_percent = self.ram_percent

        # 重置画布
        cir = QRect(0, 0, 90, 90)
        painter.setPen(Qt.NoPen)
        brush = QBrush(QColor(233, 237, 240, 255))
        painter.setBrush(brush)
        painter.drawPie(cir, 0, 16 * 360)

        # 绘制圆圈
        draw_circle = QPainterPath()
        x, y = 0, 0

        # 圆 (x-40)^2 + (y-40)^2 =1600
        # 起点
        y0 = (1 - ram_percent * 0.01) * 80
        # y0 = int((1 - 50 * 0.01) * 80)
        x0 = int((-1) * (1600 - (y0 - 40) ** 2) ** 0.5 + 40)
        draw_circle.moveTo(x0, y0)

        # 正弦 y = 5sin(0.08x)+y0
        for x in range(x0, 81 - x0):
            y = 5 * math.sin(0.08 * x) + y0
            draw_circle.lineTo(x, y)
        x1, y1 = x, y

        # 下半圆
        if y1 < 40:
            for x in range(x1, 81):
                y = (-1) * (1600 - (x - 40) ** 2) ** 0.5 + 40
                draw_circle.lineTo(x, y)
            arc_op_x = 80
        else:
            arc_op_x = x1
        if y0 < 40:
            for x in range(arc_op_x, -1, -1):
                y = (1600 - (x - 40) ** 2) ** 0.5 + 40
                draw_circle.lineTo(x, y)
            for x in range(0, x0 + 1):
                y = (-1) * (1600 - (x - 40) ** 2) ** 0.5 + 40
                draw_circle.lineTo(x, y)
        else:
            for x in range(arc_op_x, x0 - 1, -1):
                y = (1600 - (x - 40) ** 2) ** 0.5 + 40
                draw_circle.lineTo(x, y)

        painter.translate(5, 5)
        painter.setPen(Qt.NoPen)
        brush = QBrush(QColor(194, 211, 246, 255))
        painter.setBrush(brush)

        painter.drawPath(draw_circle)


class Data(QThread):
    ram_signal = pyqtSignal(int)
    net_up_signal = pyqtSignal(str)
    net_down_signal = pyqtSignal(str)
    cpu_tem_signal = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.ram_percent = None
        self.net_up_speed = None
        self.net_down_speed = None
        self.cpu_tem = None

    async def update_ram(self):
        while True:
            self.ram_percent = round(psutil.virtual_memory().percent)
            self.ram_signal.emit(self.ram_percent)
            await asyncio.sleep(5)

    async def update_tem(self):
        import clr  # the pythonnet module.

        clr.AddReference('OpenHardwareMonitorLib')
        from OpenHardwareMonitor.Hardware import Computer

        c = Computer()
        c.CPUEnabled = True  # get the Info about CPU
        c.Open()

        while True:
            # 获取温度
            c.Hardware[0].Update()
            for i in range(0, len(c.Hardware[0].Sensors)):
                # print(c.Hardware[0].Sensors[i].Identifier, c.Hardware[0].Sensors[i].Value)
                if 'temperature' in str(c.Hardware[0].Sensors[i].Identifier):
                    self.cpu_tem = c.Hardware[0].Sensors[i].Value
                    break
            else:
                self.cpu_tem = 0
            self.cpu_tem_signal.emit(round(self.cpu_tem))
            await asyncio.sleep(30)

    # 进程信息
    # for p in psutil.process_iter(['memory_percent', 'name']):
    #     print(p.info)

    async def update_net(self):
        counter1 = psutil.net_io_counters()
        interval = 2
        while True:
            await asyncio.sleep(interval)
            counter2 = psutil.net_io_counters()
            self.net_up_speed = Data.format_net_speed((counter2.bytes_sent - counter1.bytes_sent) / interval)
            self.net_down_speed = Data.format_net_speed((counter2.bytes_recv - counter1.bytes_recv) / interval)
            self.net_up_signal.emit(self.net_up_speed)
            self.net_down_signal.emit(self.net_down_speed)
            counter1 = counter2

    # 格式化网速
    @classmethod
    def format_net_speed(cls, num):
        if num < 1024:
            return str(round(num)) + ' B/s'
        elif num < 1048576:
            return str(round(num / 1024)) + ' K/s'
        elif num < 1073741824:
            return str(round(num / 1048576)) + ' M/s'
        else:
            return str(round(num / 1073741824)) + ' G/s'

    async def gather_tasks(self):
        await asyncio.gather(self.update_ram(), self.update_net(), self.update_tem())

    def run(self):
        asyncio.run(self.gather_tasks())


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ui = UI()
    ui.show()
    sys.exit(app.exec_())
