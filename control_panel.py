from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider


class ControlPanel(QWidget):
    config_changed = pyqtSignal(dict)
    closed = pyqtSignal()

    def __init__(self, config_mgr, parent=None):
        super().__init__(parent)
        self.config_mgr = config_mgr
        self.setWindowTitle("桌宠设置")
        self.setFixedSize(300, 120)
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)

        title = QLabel("桌宠大小")
        title.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        layout.addWidget(title)

        row = QHBoxLayout()
        self.size_slider = QSlider(Qt.Horizontal)
        self.size_slider.setRange(1, 8)
        self.size_slider.setValue(self.config_mgr.get("scaleFactor", 4))
        self.size_slider.setStyleSheet(
            "QSlider::groove:horizontal { height: 6px; background: #ddd; border-radius: 3px; } "
            "QSlider::handle:horizontal { background: #4a90d9; width: 18px; height: 18px; margin: -6px 0; border-radius: 9px; }"
        )
        self.size_label = QLabel(f"{self.size_slider.value()}x")
        self.size_label.setFixedWidth(30)
        self.size_label.setAlignment(Qt.AlignRight)

        self.size_slider.valueChanged.connect(lambda v: self.size_label.setText(f"{v}x"))
        self.size_slider.sliderReleased.connect(self._on_release)
        row.addWidget(self.size_slider)
        row.addWidget(self.size_label)
        layout.addLayout(row)

        tip = QLabel("拖动滑块调整大小，松手后生效")
        tip.setStyleSheet("color: #999; font-size: 11px;")
        layout.addWidget(tip)

        self.setStyleSheet("QWidget { font-family: 'Microsoft YaHei', sans-serif; } QLabel { background: transparent; }")

    def _on_release(self):
        val = self.size_slider.value()
        self.config_mgr.set("scaleFactor", val)
        self.config_mgr.save()
        self.config_changed.emit(self.config_mgr.config)

    def closeEvent(self, event):
        self.closed.emit()
        event.accept()
