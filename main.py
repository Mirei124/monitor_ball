import asyncio
import sys

import psutil
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap, QPainter, QBitmap, QCursor, QFont
from PyQt5.QtWidgets import QApplication, QWidget, QLabel


class UI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowStaysOnTopHint|Qt.Tool)
        # 设置遮罩 200px 124px
        self.pix = QBitmap('mask.png')
        self.resize(self.pix.size())
        self.setMask(self.pix)

        # 标记拖动状态
        self.m_drag = False
        # 鼠标相对窗口位置
        self.m_drag_position = None

        # 内存占用
        self.ram_label = QLabel(self)
        self.ram_label.setText('00<font size="1">%</font>')
        self.ram_font = QFont("楷体", 23, QFont.Bold)
        self.ram_label.setFont(self.ram_font)
        self.ram_label.move(15, 30)

        # CPU温度
        self.cpu_tem_label = QLabel(self)
        self.cpu_tem_label.setText('00<font size="1">℃</font>')
        self.tem_font = QFont("楷体", 14)
        self.cpu_tem_label.setFont(self.tem_font)
        self.cpu_tem_label.move(32, 75)

        self.net_font = QFont("楷体", 10)
        # 上传速度
        self.net_up_label = QLabel(self)
        self.net_up_label.setText('000 K/s')
        self.net_up_label.setFont(self.net_font)
        self.net_up_label.move(110, 35)
        # 下载速度
        self.net_down_label = QLabel(self)
        self.net_down_label.setText('000 K/s')
        self.net_down_label.setFont(self.net_font)
        self.net_down_label.move(110, 65)

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
        painter.drawPixmap(0, 0, self.pix.width(), self.pix.height(), QPixmap('background.png'))

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

    def set_ram(self, ram_percent):
        self.ram_label.setText(f'{ram_percent}<font size="1">%</font>')

    def set_net_up(self, net_up_speed):
        self.net_up_label.setText(net_up_speed)

    def set_net_down(self, net_down_speed):
        self.net_down_label.setText(net_down_speed)

    def set_cpu_tem(self, cpu_tem):
        self.cpu_tem_label.setText(f'{cpu_tem}<font size="1">℃</font>')


class Data(QThread):
    ram_signal = pyqtSignal(str)
    net_up_signal = pyqtSignal(str)
    net_down_signal = pyqtSignal(str)
    cpu_tem_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.ram_percent = None
        self.net_up_speed = None
        self.net_down_speed = None
        self.cpu_tem = None

    async def update_ram(self):
        while True:
            self.ram_percent = round(psutil.virtual_memory().percent)
            self.ram_signal.emit(str(self.ram_percent))
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
            self.cpu_tem_signal.emit(str(round(self.cpu_tem)))
            await asyncio.sleep(5)

    # 进程信息
    # for p in psutil.process_iter(['memory_percent', 'name']):
    #     print(p.info)

    async def update_net(self):
        counter1 = psutil.net_io_counters()
        while True:
            await asyncio.sleep(1)
            counter2 = psutil.net_io_counters()
            self.net_up_speed = self.format_net_speed(counter2.bytes_sent - counter1.bytes_sent)
            self.net_down_speed = self.format_net_speed(counter2.bytes_recv - counter1.bytes_recv)
            self.net_up_signal.emit(self.net_up_speed)
            self.net_down_signal.emit(self.net_down_speed)
            counter1 = counter2

    # 格式化网速
    def format_net_speed(self, num):
        if type(num) == int:
            if num < 1024:
                return str(num) + ' B/s'
            elif num < 1048576:
                return str(round(num / 1024)) + ' K/s'
            elif num < 1073741824:
                return str(round(num / 1048576)) + ' M/s'
            else:
                return str(round(num / 1073741824)) + ' G/s'
        else:
            return 'xx'

    async def gather_tasks(self):
        await asyncio.gather(self.update_ram(), self.update_net(), self.update_tem())

    def run(self):
        asyncio.run(self.gather_tasks())


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ui = UI()
    ui.show()
    sys.exit(app.exec_())
