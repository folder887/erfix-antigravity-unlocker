import os
import sys
from PyQt6.QtCore import Qt, QPoint, QUrl, QThread, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QDesktopServices, QCursor
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QSystemTrayIcon, QMenu
)
import core

def get_asset_path(filename):
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, filename)

class WorkerThread(QThread):
    finished_signal = pyqtSignal(bool, str, str)

    def __init__(self, action="enable"):
        super().__init__()
        self.action = action

    def run(self):
        if self.action == "enable":
            try:
                # 1. Find best proxy
                proxy_str, latency, name = core.find_best_proxy()
                
                # 2. Apply settings
                core.apply_settings(proxy_str, enable=True)
                
                # 3. Ensure background service is running
                core.ensure_service_running()
                
                # 4. Restart or launch Antigravity
                success, msg = core.launch_antigravity()
                
                info = f"{name} ({latency} ms)"
                self.finished_signal.emit(True, info, msg)
            except Exception as e:
                self.finished_signal.emit(False, "", str(e))
        else:
            try:
                # Disable proxy
                proxy_str, _, _ = core.find_best_proxy()
                core.apply_settings(proxy_str, enable=False)
                self.finished_signal.emit(False, "Отключено", "Обход отключен")
            except Exception as e:
                self.finished_signal.emit(False, "", str(e))

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.is_enabled = False
        self.is_working = False
        self.drag_position = QPoint()

        self.init_ui()
        self.init_tray()

    def init_ui(self):
        self.setFixedSize(783, 494)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)

        icon_path = get_asset_path("app_icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # Titlebar Background (41px)
        self.titlebar_bg = QLabel(self)
        self.titlebar_bg.setGeometry(0, 0, 783, 41)
        self.titlebar_bg.setStyleSheet("background-color: #262626;")

        # Title text logo (x=16, y=10)
        self.title_label = QLabel(self)
        self.title_label.setGeometry(16, 10, 108, 20)
        title_pix = QPixmap(get_asset_path("erfix v1.0.png"))
        if not title_pix.isNull():
            self.title_label.setPixmap(title_pix)
        else:
            self.title_label.setText("erfix v1.0")
            self.title_label.setStyleSheet("color: white; font-weight: bold; font-size: 14px;")

        # Titlebar Buttons
        # Minimize Button (x=704, y=11, 30x20)
        self.btn_min = QPushButton(self)
        self.btn_min.setGeometry(700, 5, 36, 30)
        self.btn_min.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_min.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: #383838;
            }
        """)
        min_pix = QPixmap(get_asset_path("Vector 87.png"))
        if not min_pix.isNull():
            self.btn_min.setIcon(QIcon(min_pix))
            self.btn_min.setIconSize(min_pix.size())
        self.btn_min.clicked.connect(self.showMinimized)

        # Close Button (x=746, y=5, 36x30)
        self.btn_close = QPushButton(self)
        self.btn_close.setGeometry(744, 5, 36, 30)
        self.btn_close.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_close.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: #C42B1C;
            }
        """)
        close_pix = QPixmap(get_asset_path("btn_close.png"))
        if close_pix.isNull():
            close_pix = QPixmap(get_asset_path("Vector 88.png"))
        if not close_pix.isNull():
            self.btn_close.setIcon(QIcon(close_pix))
            self.btn_close.setIconSize(close_pix.size())
        self.btn_close.clicked.connect(self.close)

        # Central Toggle Button (x=244, y=148, 296x124)
        self.btn_toggle = QPushButton(self)
        self.btn_toggle.setGeometry(244, 148, 296, 124)
        self.btn_toggle.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_toggle.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
            }
            QPushButton:hover {
                opacity: 0.95;
            }
        """)
        
        self.pix_toggle_off = QPixmap(get_asset_path("Group 62.png"))
        self.pix_toggle_on = QPixmap(get_asset_path("Group 62-1.png"))
        self.update_toggle_icon()
        self.btn_toggle.clicked.connect(self.handle_toggle_click)

        # Status Label: "ВЫКЛЮЧЕНО" / "ВКЛЮЧЕНО" (y=297)
        self.status_label = QLabel(self)
        self.pix_status_off = QPixmap(get_asset_path("ВЫКЛЮЧЕНО.png"))
        self.pix_status_on = QPixmap(get_asset_path("ВКЛЮЧЕНО.png"))
        self.update_status_display()

        # Telegram Link: t.me/@folder887 (x=295, y=354, 196x24)
        self.btn_link = QPushButton(self)
        self.btn_link.setGeometry(295, 354, 196, 24)
        self.btn_link.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_link.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
            }
            QPushButton:hover {
                filter: brightness(1.2);
            }
        """)
        link_pix = QPixmap(get_asset_path("@folder887.png"))
        if not link_pix.isNull():
            self.btn_link.setIcon(QIcon(link_pix))
            self.btn_link.setIconSize(link_pix.size())
        self.btn_link.clicked.connect(self.open_telegram)

        # Subtle info label at bottom
        self.sub_info = QLabel(self)
        self.sub_info.setGeometry(100, 420, 583, 30)
        self.sub_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sub_info.setStyleSheet("color: #707070; font-size: 13px; font-family: Segoe UI, sans-serif;")
        self.sub_info.setText("")

    def init_tray(self):
        icon_path = get_asset_path("app_icon.ico")
        if os.path.exists(icon_path):
            self.tray_icon = QSystemTrayIcon(self)
            self.tray_icon.setIcon(QIcon(icon_path))
            self.tray_icon.setToolTip("erfix v1.0 - Antigravity Unlocker")
            
            tray_menu = QMenu()
            show_action = tray_menu.addAction("Открыть erfix")
            show_action.triggered.connect(self.show_normal_and_raise)
            tray_menu.addSeparator()
            exit_action = tray_menu.addAction("Выход")
            exit_action.triggered.connect(QApplication.instance().quit)
            
            self.tray_icon.setContextMenu(tray_menu)
            self.tray_icon.activated.connect(self.on_tray_activated)
            self.tray_icon.show()

    def show_normal_and_raise(self):
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.isVisible():
                self.hide()
            else:
                self.show_normal_and_raise()

    def paintEvent(self, event):
        painter = QPainter(self)
        # Background color #2F2F2F (matches Frame 33 & Frame 34)
        painter.fillRect(self.rect(), QColor("#2F2F2F"))
        # Top titlebar #262626
        painter.fillRect(0, 0, 783, 41, QColor("#262626"))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and event.pos().y() <= 41:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and not self.drag_position.isNull():
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.drag_position = QPoint()

    def update_toggle_icon(self):
        pix = self.pix_toggle_on if self.is_enabled else self.pix_toggle_off
        if not pix.isNull():
            self.btn_toggle.setIcon(QIcon(pix))
            self.btn_toggle.setIconSize(pix.size())

    def update_status_display(self):
        if self.is_enabled:
            # ВКЛЮЧЕНО (w=282, h=38), center x = (783 - 282) / 2 = 250
            self.status_label.setGeometry(250, 297, 282, 38)
            if not self.pix_status_on.isNull():
                self.status_label.setPixmap(self.pix_status_on)
        else:
            # ВЫКЛЮЧЕНО (w=324, h=38), center x = (783 - 324) / 2 = 229
            self.status_label.setGeometry(229, 297, 324, 38)
            if not self.pix_status_off.isNull():
                self.status_label.setPixmap(self.pix_status_off)

    def handle_toggle_click(self):
        if self.is_working:
            return

        self.is_working = True
        if not self.is_enabled:
            # Start Enabling Happy Path
            self.sub_info.setText("Подбор лучшего сервера и запуск Antigravity...")
            self.sub_info.setStyleSheet("color: #00C8B3; font-size: 13px; font-family: Segoe UI, sans-serif;")
            self.worker = WorkerThread(action="enable")
            self.worker.finished_signal.connect(self.on_enable_finished)
            self.worker.start()
        else:
            # Start Disabling
            self.sub_info.setText("Отключение обхода...")
            self.sub_info.setStyleSheet("color: #707070; font-size: 13px; font-family: Segoe UI, sans-serif;")
            self.worker = WorkerThread(action="disable")
            self.worker.finished_signal.connect(self.on_disable_finished)
            self.worker.start()

    def on_enable_finished(self, success, info, message):
        self.is_working = False
        if success:
            self.is_enabled = True
            self.update_toggle_icon()
            self.update_status_display()
            self.sub_info.setText(f"Подключено: {info} • Antigravity готов")
            self.sub_info.setStyleSheet("color: #00C8B3; font-size: 13px; font-family: Segoe UI, sans-serif;")
        else:
            self.sub_info.setText(f"Ошибка: {message}")
            self.sub_info.setStyleSheet("color: #FF5555; font-size: 13px; font-family: Segoe UI, sans-serif;")

    def on_disable_finished(self, is_enabled, info, message):
        self.is_working = False
        self.is_enabled = False
        self.update_toggle_icon()
        self.update_status_display()
        self.sub_info.setText("")

    def open_telegram(self):
        QDesktopServices.openUrl(QUrl("https://t.me/folder887"))

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
