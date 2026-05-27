import os
import random
from PyQt5.QtCore import Qt, QTimer, QPoint, QSize, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt5.QtGui import QPixmap, QPainter, QCursor, QTransform, QFont, QFontMetrics, QMovie, QColor, QPainterPath, QPen
from PyQt5.QtWidgets import QWidget, QLabel, QApplication, QMenu, QAction

from config_manager import ConfigManager
from asset_manager import AssetManager
from monitor import Monitor
from floating_menu import FloatingMenu
import control_panel as cp_module



class BubbleLabel(QWidget):
    """气泡对话框，带三角指向、淡入淡出动画"""

    TAIL_H = 8
    PAD_X = 14
    PAD_Y = 8
    RADIUS = 12

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._text = ""
        self._opacity = 0.0
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.fade_out)

        self._fade_anim = QPropertyAnimation(self, b"opacity")
        self._fade_anim.setDuration(200)
        self._fade_anim.setEasingCurve(QEasingCurve.OutCubic)

    def get_opacity(self):
        return self._opacity

    def set_opacity(self, val):
        self._opacity = val
        self.update()

    opacity = pyqtProperty(float, fget=get_opacity, fset=set_opacity)

    def show_text(self, text, duration=3000):
        if not text:
            return
        self._text = text
        self._timer.stop()

        font = QFont("Microsoft YaHei", 11)
        fm = QFontMetrics(font)
        text_rect = fm.boundingRect(0, 0, 220, 100, Qt.TextWordWrap, text)
        w = text_rect.width() + self.PAD_X * 2
        h = text_rect.height() + self.PAD_Y * 2 + self.TAIL_H

        pw = self.parent().width() if self.parent() else 200
        x = (pw - w) // 2
        y = -h - 4

        self.setGeometry(int(x), int(y), int(w), int(h))
        self.show()
        self.raise_()

        self._fade_anim.stop()
        self._fade_anim.setStartValue(self._opacity)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.start()

        self._timer.start(duration)

    def fade_out(self):
        self._fade_anim.stop()
        self._fade_anim.setStartValue(self._opacity)
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.finished.connect(self._on_fade_out_done)
        self._fade_anim.start()

    def _on_fade_out_done(self):
        try:
            self._fade_anim.finished.disconnect(self._on_fade_out_done)
        except Exception:
            pass
        if self._opacity <= 0.01:
            self.hide()

    def paintEvent(self, event):
        if self._opacity < 0.01:
            return

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setOpacity(self._opacity)

        bubble_rect = self.rect().adjusted(0, 0, 0, -self.TAIL_H)

        shadow_path = QPainterPath()
        shadow_path.addRoundedRect(bubble_rect.adjusted(1, 1, 1, 1), self.RADIUS, self.RADIUS)
        p.fillPath(shadow_path, QColor(0, 0, 0, 25))

        bg_path = QPainterPath()
        bg_path.addRoundedRect(bubble_rect, self.RADIUS, self.RADIUS)

        cx = bubble_rect.center().x()
        tail_top = bubble_rect.bottom()
        tail_path = QPainterPath()
        tail_path.moveTo(cx - 7, tail_top - 1)
        tail_path.lineTo(cx, tail_top + self.TAIL_H)
        tail_path.lineTo(cx + 7, tail_top - 1)
        tail_path.closeSubpath()

        bg_path.addPath(tail_path)
        p.fillPath(bg_path, QColor(255, 255, 255, 240))

        pen = QPen(QColor(200, 200, 200, 120))
        pen.setWidthF(0.8)
        p.setPen(pen)
        p.drawPath(bg_path)

        p.setPen(QColor(51, 51, 51))
        font = QFont("Microsoft YaHei", 11)
        p.setFont(font)
        text_rect = bubble_rect.adjusted(self.PAD_X, self.PAD_Y, -self.PAD_X, -self.PAD_Y)
        p.drawText(text_rect, Qt.TextWordWrap | Qt.AlignCenter, self._text)

        p.end()


class PetWidget(QWidget):
    def __init__(self):
        super().__init__()

        self.config_mgr = ConfigManager()
        self.asset_mgr = AssetManager()

        self.state = "IDLE"
        self.direction = random.choice([1, -1])
        self.frame_index = 0
        self.is_paused = False
        self.is_dragging = False
        self.pending_click = False
        self.drag_offset = QPoint()
        self.drag_threshold = 5
        self.drag_moved = False

        self.scale_factor = self.config_mgr.get("scaleFactor", 4)
        self.fps = self.config_mgr.get("fps", 15)
        self.speed = self.config_mgr.get("speed", 4)
        self.default_frames = {}
        self.current_frames = []
        self.current_pixmap = None
        self.current_movie = None

        self.monitor_win = None
        self.floating_menu = None
        self.control_panel = None

        self._gif_natural = QSize(400, 710)  # 默认值，会被实际 GIF 覆盖
        self._load_default_frames()
        self._init_window()
        self._init_timers()
        self._init_bubble()
        self._load_initial_asset()

    # ─── Window Setup ───

    def _init_window(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self.setCursor(Qt.OpenHandCursor)
        self._update_size()

        pos = self.config_mgr.get("petPosition", {"x": 100, "y": 100})
        screen = QApplication.primaryScreen().availableGeometry()
        x = max(0, min(pos["x"], screen.width() - self.width()))
        y = max(0, min(pos["y"], screen.height() - self.height()))
        self.move(x, y)

    def _apply_size(self):
        """根据 GIF 原始尺寸和 scale_factor 计算窗口大小"""
        target_h = max(50, int(70 * self.scale_factor))
        ratio = target_h / max(1, self._gif_natural.height())
        w = int(self._gif_natural.width() * ratio)
        self.setFixedSize(w, target_h)

    def _update_size(self):
        self._apply_size()

    # ─── Timers ───

    def _init_timers(self):
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._tick_animation)

        self.state_timer = QTimer(self)
        self.state_timer.timeout.connect(self._random_state_change)

        self.hover_timer = QTimer(self)
        self.hover_timer.setSingleShot(True)
        self.hover_timer.timeout.connect(self._show_monitor)

        self._start_anim_timer()
        self._schedule_state_change()

    def _start_anim_timer(self):
        self.anim_timer.start(max(33, 1000 // max(1, self.fps)))

    def _schedule_state_change(self):
        jitter = random.randint(0, 10000)
        self.state_timer.start(60000 + jitter)

    # ─── Bubble ───

    def _init_bubble(self):
        self.bubble = BubbleLabel(self)
        self.bubble.hide()

    def _show_bubble(self, text):
        if not text:
            return
        duration = self.config_mgr.get("bubbleDuration", 3) * 1000
        self.bubble.show_text(text, duration)

    # ─── Asset Loading ───

    def _load_default_frames(self):
        self.default_frames = {}

    def _load_initial_asset(self):
        binding = self.config_mgr.get_bindings().get("idle", "")
        if binding and self.asset_mgr.exists(binding):
            path = self.asset_mgr.get_path(binding)
            ext = os.path.splitext(binding)[1].lower()
            if ext == ".gif":
                movie = QMovie(path)
                if movie.isValid():
                    movie.jumpToFrame(0)
                    natural = movie.currentPixmap().size()
                    movie.deleteLater()
                    if natural.width() > 0 and natural.height() > 0:
                        self._gif_natural = natural
            self._apply_size()
            self._load_state_asset(binding)
        else:
            self.current_frames = []
            self.current_pixmap = None

    def _load_state_asset(self, filename):
        self._stop_media()
        self.current_frames = []
        self.current_pixmap = None

        if not filename:
            return

        ext = os.path.splitext(filename)[1].lower()
        path = self.asset_mgr.get_path(filename)

        if ext == ".gif":
            self._load_gif(path)
        else:
            pm = QPixmap(path)
            if not pm.isNull():
                self.current_pixmap = pm
            else:
                self.current_pixmap = None
        self.update()

    def _load_gif(self, path):
        self.current_movie = QMovie(path)
        if self.current_movie.isValid():
            self.current_movie.jumpToFrame(0)
            natural = self.current_movie.currentPixmap().size()
            if natural.width() > 0 and natural.height() > 0:
                target_h = max(50, int(70 * self.scale_factor))
                ratio = target_h / natural.height()
                self.setFixedSize(int(natural.width() * ratio), target_h)
            self.current_movie.frameChanged.connect(lambda: self.update())
            self.current_movie.start()
        else:
            self.current_movie = None

    def _stop_media(self):
        if self.current_movie:
            self.current_movie.stop()
            self.current_movie.deleteLater()
            self.current_movie = None

    # ─── State / Interaction ───

    def _do_interaction(self, action):
        if action == "walk":
            if self.state == "IDLE":
                self._enter_walk()
            return
        self.state = action.upper() if action.upper() in ("PET", "FEED", "PLAY", "DRAG") else action
        self.frame_index = 0
        self._stop_media()
        self.current_frames = []
        self.current_pixmap = None

        binding = self.config_mgr.get_bindings().get(action, "")
        if binding and self.asset_mgr.exists(binding):
            self._load_state_asset(binding)
        else:
            idle_binding = self.config_mgr.get_bindings().get("idle", "")
            if idle_binding and self.asset_mgr.exists(idle_binding):
                self._load_state_asset(idle_binding)
            else:
                self.current_pixmap = None

        responses = self.config_mgr.get_responses(action)
        if responses:
            self._show_bubble(random.choice(responses))

        # 等 GIF 播完一整遍再切回待机
        if self.current_movie and self.current_movie.isValid():
            self._interaction_frame_count = 0
            self._interaction_total_frames = max(1, self.current_movie.frameCount())
            self.current_movie.frameChanged.connect(self._on_interaction_frame)
        else:
            QTimer.singleShot(3000, self._return_to_idle)

    def _on_interaction_frame(self):
        self._interaction_frame_count += 1
        if self._interaction_frame_count >= self._interaction_total_frames:
            try:
                self.current_movie.frameChanged.disconnect(self._on_interaction_frame)
            except Exception:
                pass
            self._return_to_idle()

    def _return_to_idle(self):
        self.state = "IDLE"
        self.frame_index = 0
        self._stop_media()
        self.current_frames = []
        self.current_pixmap = None

        binding = self.config_mgr.get_bindings().get("idle", "")
        if binding and self.asset_mgr.exists(binding):
            self._load_state_asset(binding)
        self.update()

    def _random_state_change(self):
        if self.is_paused or self.is_dragging or self.state not in ("IDLE",):
            self._schedule_state_change()
            return
        self._enter_walk()

    def _enter_walk(self):
        """走路：先向左走8秒，再向右走8秒回到原位"""
        self.state = "WALK"
        self.frame_index = 0
        self._walk_start_x = self.x()
        self._walk_phase = "left"

        self._stop_media()
        self.current_frames = []
        self.current_pixmap = None

        bindings = self.config_mgr.get_bindings()
        left_gif = bindings.get("walk_left", "")
        if left_gif and self.asset_mgr.exists(left_gif):
            self._load_state_asset(left_gif)

        # 安全检查：如果 GIF 没加载成功，直接回待机
        if not self.current_movie or not self.current_movie.isValid():
            self._return_to_idle()
            return

        QTimer.singleShot(8000, self._walk_turn_right)

    def _walk_turn_right(self):
        """切换到向右走"""
        if self.state != "WALK" or self.is_dragging:
            return
        self._walk_phase = "right"

        self._stop_media()
        self.current_frames = []
        self.current_pixmap = None

        bindings = self.config_mgr.get_bindings()
        right_gif = bindings.get("walk_right", "")
        if right_gif and self.asset_mgr.exists(right_gif):
            self._load_state_asset(right_gif)

        if not self.current_movie or not self.current_movie.isValid():
            self._walk_return()
            return

        QTimer.singleShot(8000, self._walk_return)

    def _walk_return(self):
        """回到原位，结束走路"""
        if self.state != "WALK":
            return
        screen = QApplication.primaryScreen().availableGeometry()
        target_x = max(0, min(self._walk_start_x, screen.width() - self.width()))
        self.move(target_x, self.y())
        self._return_to_idle()

    # ─── Movement ───

    def _move_pet(self):
        if self.state != "WALK":
            return
        speed = max(1, self.width() // 60)
        if self._walk_phase == "left":
            new_x = self.x() - speed
            screen = QApplication.primaryScreen().availableGeometry()
            self.move(max(0, new_x), self.y())
        else:
            target = self._walk_start_x
            cur = self.x()
            if cur < target:
                self.move(min(target, cur + speed), self.y())

    # ─── Animation Tick ───

    def _tick_animation(self):
        if self.is_paused:
            return
        if self.current_frames:
            self.frame_index = (self.frame_index + 1) % len(self.current_frames)
        if self.state == "WALK":
            self._move_pet()
        self.update()

    # ─── Paint ───

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, False)

        if self.current_movie and self.current_movie.isValid():
            frame = self.current_movie.currentPixmap()
            if not frame.isNull():
                scaled = frame.scaled(self.size(), Qt.KeepAspectRatio, Qt.FastTransformation)
                x = (self.width() - scaled.width()) // 2
                y = (self.height() - scaled.height()) // 2
                painter.drawPixmap(x, y, scaled)
            return

        if self.current_frames:
            if self.frame_index >= len(self.current_frames):
                self.frame_index = 0
            pm = self.current_frames[self.frame_index]
            if self.direction == -1:
                pm = pm.transformed(QTransform().scale(-1, 1), Qt.FastTransformation)
            painter.drawPixmap(0, 0, pm.scaled(self.size(), Qt.KeepAspectRatio, Qt.FastTransformation))
            return

        if self.current_pixmap and not self.current_pixmap.isNull():
            scaled = self.current_pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.FastTransformation)
            if self.direction == -1:
                scaled = scaled.transformed(QTransform().scale(-1, 1), Qt.FastTransformation)
            painter.drawPixmap(0, 0, scaled)
            return

        painter.setFont(QFont("Segoe UI Emoji", max(12, min(self.width(), self.height()) * 6 // 10)))
        painter.drawText(self.rect(), Qt.AlignCenter, "🐱")

    # ─── Mouse Events ───

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.pending_click = True
            self.is_dragging = False
            self.drag_moved = False
            self.drag_offset = event.pos()
            self.setCursor(Qt.ClosedHandCursor)

        if event.button() == Qt.LeftButton and self.floating_menu:
            self.floating_menu.close()
            self.floating_menu = None

        self.hover_timer.stop()
        if self.monitor_win:
            self.monitor_win.close()
            self.monitor_win = None

        if self.state == "DRAG":
            self._return_to_idle()

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        self.setCursor(Qt.OpenHandCursor)
        if self.is_dragging:
            self.is_dragging = False
            self.config_mgr.set("petPosition", {"x": self.x(), "y": self.y()})
            self.config_mgr.save()
            self._return_to_idle()
        elif self.pending_click and not self.drag_moved:
            self._open_floating_menu(event.globalPos())
        self.pending_click = False
        self.is_dragging = False

    def mouseMoveEvent(self, event):
        if self.is_dragging or (event.buttons() & Qt.LeftButton and self.pending_click):
            delta = event.pos() - self.drag_offset
            if not self.is_dragging and (abs(delta.x()) > self.drag_threshold or abs(delta.y()) > self.drag_threshold):
                self.is_dragging = True
                self.drag_moved = True
                if self.state != "DRAG":
                    self.state = "DRAG"
                    self._stop_media()
                    self.current_frames = []
                    self.current_pixmap = None
                    drag_binding = self.config_mgr.get_bindings().get("drag", "")
                    if drag_binding and self.asset_mgr.exists(drag_binding):
                        self._load_state_asset(drag_binding)
            if self.is_dragging:
                new_pos = event.globalPos() - self.drag_offset
                self.move(new_pos)
                self.config_mgr.set("petPosition", {"x": new_pos.x(), "y": new_pos.y()})
        else:
            self.hover_timer.start(2000)

    def leaveEvent(self, event):
        self.hover_timer.stop()
        if self.monitor_win:
            self.monitor_win.close()
            self.monitor_win = None

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background: #fff; border: 1px solid #ddd; border-radius: 8px; padding: 5px; font-size: 12px; }
            QMenu::item { padding: 6px 24px; border-radius: 4px; }
            QMenu::item:selected { background: #e8f0fe; }
        """)

        panel_act = QAction("设置", self)
        panel_act.triggered.connect(self._open_control_panel)
        menu.addAction(panel_act)

        exit_act = QAction("退出", self)
        exit_act.triggered.connect(QApplication.instance().quit)
        menu.addAction(exit_act)

        menu.exec_(event.globalPos())

    # ─── Actions ───

    def _toggle_pause(self):
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.anim_timer.stop()
            self.state_timer.stop()
            self.frame_index = 0
        else:
            self._start_anim_timer()
            self._schedule_state_change()
            if self.state == "IDLE":
                binding = self.config_mgr.get_bindings().get("idle", "")
                if binding and self.asset_mgr.exists(binding):
                    self._load_state_asset(binding)
        self.update()

    def _set_state(self, new_state):
        if new_state == "IDLE":
            self.state = "IDLE"
            self._stop_media()
            self.current_frames = []
            self.current_pixmap = None
            binding = self.config_mgr.get_bindings().get("idle", "")
            if binding and self.asset_mgr.exists(binding):
                self._load_state_asset(binding)
        else:
            self.state = "WALK"
            self._stop_media()
            self.current_frames = []
            self.current_pixmap = None
            binding = self.config_mgr.get_bindings().get("walk", "")
            if binding and self.asset_mgr.exists(binding):
                self._load_state_asset(binding)
                self._update_size()
        self.frame_index = 0
        self.update()

    def _adjust_size(self, delta):
        self.scale_factor = max(1, min(8, self.scale_factor + delta))
        self._update_size()
        self.config_mgr.set("scaleFactor", self.scale_factor)
        self.config_mgr.save()
        if self.current_movie:
            self.current_movie.setScaledSize(QSize(self.width(), self.height()))
        self.update()

    def _adjust_speed(self, delta):
        self.fps = max(6, min(30, self.fps + delta))
        self._start_anim_timer()
        self.config_mgr.set("fps", self.fps)
        self.config_mgr.save()

    def _open_floating_menu(self, pos):
        if self.floating_menu:
            self.floating_menu.close()
            self.floating_menu = None

        states = self.config_mgr.get_interaction_states()
        menu_states = [s for s in states if s["key"] == "pet"]
        menu_states.append({"key": "walk", "label": "走一走", "emoji": "🚶"})
        if not menu_states:
            menu_states = [
                {"key": "pet", "label": "摸摸", "emoji": "🤚"},
                {"key": "feed", "label": "喂食", "emoji": "🍖"},
                {"key": "play", "label": "玩耍", "emoji": "⚽"},
            ]

        menu_pos = QPoint(pos.x() + self.width() - 100, pos.y())
        self.floating_menu = FloatingMenu(menu_pos, menu_states)
        self.floating_menu.action_triggered.connect(self._do_interaction)
        self.floating_menu.destroyed.connect(lambda: setattr(self, "floating_menu", None))

    def _show_monitor(self):
        if not self.rect().contains(self.mapFromGlobal(QCursor.pos())):
            return
        if not self.monitor_win:
            self.monitor_win = Monitor()
        mx = self.x() + self.width() + 8
        my = self.y()
        screen = QApplication.primaryScreen().availableGeometry()
        if mx + self.monitor_win.width() > screen.width():
            mx = self.x() - self.monitor_win.width() - 8
        if my + self.monitor_win.height() > screen.height():
            my = screen.height() - self.monitor_win.height()
        self.monitor_win.move(mx, max(0, my))
        self.monitor_win.show()

    def _open_control_panel(self):
        if not self.control_panel:
            self.control_panel = cp_module.ControlPanel(self.config_mgr)
            self.control_panel.config_changed.connect(self._on_config_changed)
            self.control_panel.closed.connect(self._on_panel_closed)
        self.control_panel.show()
        self.control_panel.raise_()
        self.control_panel.activateWindow()

    def _on_config_changed(self, new_config):
        self.scale_factor = new_config.get("scaleFactor", self.scale_factor)
        self._apply_size()

    def _on_panel_closed(self):
        self.control_panel = None

    def _idle_tick(self):
        if self.is_paused or self.state != "IDLE":
            return
        msgs = self.config_mgr.get_idle_messages()
        if msgs:
            self._show_bubble(random.choice(msgs))

    def showEvent(self, event):
        super().showEvent(event)
        self._idle_msg_timer = QTimer(self)
        self._idle_msg_timer.timeout.connect(self._idle_tick)
        self._idle_msg_timer.start(self.config_mgr.get("idleInterval", 45) * 1000)

    def closeEvent(self, event):
        self.anim_timer.stop()
        self.state_timer.stop()
        self.hover_timer.stop()
        self._stop_media()
        if self.monitor_win:
            self.monitor_win.close()
        if self.floating_menu:
            self.floating_menu.close()
        if self.control_panel:
            self.control_panel.close()
        event.accept()
