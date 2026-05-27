from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton


class FloatingMenu(QWidget):
    action_triggered = pyqtSignal(str)

    def __init__(self, pos, states, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_DeleteOnClose)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        for s in states:
            btn = QPushButton(f"{s['emoji']} {s['label']}", self)
            btn.setFont(QFont("Microsoft YaHei", 11))
            btn.setFixedHeight(34)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background: rgba(255,255,255,0.95);
                    border: none;
                    border-radius: 17px;
                    padding: 6px 16px;
                    text-align: left;
                }
                QPushButton:hover { background: #fff; }
            """)
            btn.clicked.connect(lambda checked, k=s["key"]: self._on_click(k))
            layout.addWidget(btn)

        self.adjustSize()
        self.move(pos)
        self.show()

    def _on_click(self, key):
        self.action_triggered.emit(key)
        self.close()
