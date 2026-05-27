import time
import psutil
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPainter, QColor, QFont, QPen
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel


class ProgressBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.value = 0
        self.setFixedHeight(20)
        self.setMinimumWidth(200)

    def set_value(self, v):
        self.value = max(0, min(100, v))
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(34, 34, 34))
        pen = QPen(QColor(102, 102, 102))
        pen.setWidth(2)
        p.setPen(pen)
        p.drawRect(0, 0, self.width() - 1, self.height() - 1)
        if self.value > 0:
            w = int((self.width() - 4) * self.value / 100)
            c = QColor(50, 205, 50) if self.value < 60 else QColor(255, 165, 0) if self.value < 80 else QColor(220, 20, 60)
            p.fillRect(2, 2, w, self.height() - 4, c)
            ps = 4
            for x in range(2, 2 + w, ps):
                for y in range(2, self.height() - 4, ps):
                    p.fillRect(x, y, ps - 1, ps - 1, QColor(c.red() + 20, c.green() + 20, c.blue() + 20))


class Monitor(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("系统监控")
        self.setFixedSize(250, 180)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.last_net_io = psutil.net_io_counters()
        self.last_net_time = time.time()

        self._init_ui()

        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_stats)
        self.update_timer.start(1000)
        self.update_stats()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        title = QLabel("系统监控", self)
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Courier New", 14, QFont.Bold))
        title.setStyleSheet("color: white;")
        layout.addWidget(title)

        cpu_row = QHBoxLayout()
        cpu_lbl = QLabel("CPU:", self)
        cpu_lbl.setFont(QFont("Courier New", 10))
        cpu_lbl.setStyleSheet("color: white;")
        cpu_row.addWidget(cpu_lbl)
        self.cpu_val = QLabel("0%", self)
        self.cpu_val.setFont(QFont("Courier New", 10))
        self.cpu_val.setStyleSheet("color: white;")
        self.cpu_val.setFixedWidth(50)
        self.cpu_val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        cpu_row.addWidget(self.cpu_val)
        layout.addLayout(cpu_row)

        self.cpu_bar = ProgressBar(self)
        layout.addWidget(self.cpu_bar)

        mem_row = QHBoxLayout()
        mem_lbl = QLabel("内存:", self)
        mem_lbl.setFont(QFont("Courier New", 10))
        mem_lbl.setStyleSheet("color: white;")
        mem_row.addWidget(mem_lbl)
        self.mem_val = QLabel("0%", self)
        self.mem_val.setFont(QFont("Courier New", 10))
        self.mem_val.setStyleSheet("color: white;")
        self.mem_val.setFixedWidth(50)
        self.mem_val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        mem_row.addWidget(self.mem_val)
        layout.addLayout(mem_row)

        self.mem_bar = ProgressBar(self)
        layout.addWidget(self.mem_bar)

        net_row = QHBoxLayout()
        net_lbl = QLabel("网络:", self)
        net_lbl.setFont(QFont("Courier New", 10))
        net_lbl.setStyleSheet("color: white;")
        net_row.addWidget(net_lbl)
        net_row.addStretch()
        self.down_lbl = QLabel("↓ 0 KB/s", self)
        self.down_lbl.setFont(QFont("Courier New", 10))
        self.down_lbl.setStyleSheet("color: #3CB371;")
        net_row.addWidget(self.down_lbl)
        self.up_lbl = QLabel("↑ 0 KB/s", self)
        self.up_lbl.setFont(QFont("Courier New", 10))
        self.up_lbl.setStyleSheet("color: #FF6347;")
        net_row.addWidget(self.up_lbl)
        layout.addLayout(net_row)

        self.setStyleSheet("QWidget { background-color: #222222; color: white; border: 2px solid #666666; }")

    def update_stats(self):
        self.cpu_val.setText(f"{psutil.cpu_percent():.1f}%")
        self.cpu_bar.set_value(psutil.cpu_percent())
        mem = psutil.virtual_memory()
        self.mem_val.setText(f"{mem.percent:.1f}%")
        self.mem_bar.set_value(mem.percent)

        cur = psutil.net_io_counters()
        now = time.time()
        dt = now - self.last_net_time
        if dt > 0:
            self.down_lbl.setText(f"↓ {self._fmt((cur.bytes_recv - self.last_net_io.bytes_recv) / dt)}")
            self.up_lbl.setText(f"↑ {self._fmt((cur.bytes_sent - self.last_net_io.bytes_sent) / dt)}")
            self.last_net_io = cur
            self.last_net_time = now

    def _fmt(self, bps):
        if bps < 1024:
            return f"{bps:.0f} B/s"
        elif bps < 1048576:
            return f"{bps / 1024:.1f} KB/s"
        else:
            return f"{bps / 1048576:.1f} MB/s"
