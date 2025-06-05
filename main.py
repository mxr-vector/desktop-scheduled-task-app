import sys
import os
import json
import socket
from PyQt6.QtWidgets import (
    QApplication, QSystemTrayIcon, QMenu, QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QTimeEdit, QPushButton, QMessageBox, QCheckBox, QMainWindow,
    QWidget, QListWidget, QListWidgetItem, QTextEdit, QGroupBox, QComboBox
)
from PyQt6.QtCore import QTimer, QTime, QSettings, Qt, QSocketNotifier
from PyQt6.QtGui import QIcon, QAction, QFont, QPalette, QColor
import datetime
import winreg

# 定义一个特定的端口用于单实例检查
SINGLE_INSTANCE_PORT = 54321

def is_instance_running():
    try:
        # 尝试创建一个监听套接字
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('127.0.0.1', SINGLE_INSTANCE_PORT))
        sock.listen(1)
        return False, sock
    except OSError:
        return True, None

def activate_existing_instance():
    try:
        # 尝试连接到已运行的实例
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(('127.0.0.1', SINGLE_INSTANCE_PORT))
        sock.send(b'ACTIVATE')
        sock.close()
    except Exception:
        pass

# 检测Windows系统是否处于暗黑模式
def is_windows_dark_mode():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                           r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        winreg.CloseKey(key)
        return value == 0  # 0表示暗黑模式，1表示浅色模式
    except Exception:
        return False  # 如果无法检测，默认返回False

APP_DIR = ''

def resource_path(relative_path):
    """ 获取资源的绝对路径，优先查找exe同级目录下的文件 """
    # 获取可执行文件所在目录
    if getattr(sys, 'frozen', False):
        # PyInstaller打包后的路径
        exe_dir = os.path.dirname(sys.executable)
    else:
        # 普通运行时路径
        exe_dir = os.path.abspath(".")

    # 优先检查exe同级目录下是否存在该文件
    exe_file_path = os.path.join(exe_dir, relative_path)
    if os.path.exists(exe_file_path):
        return exe_file_path

    # 如果exe同级目录下不存在，则尝试从打包资源中获取
    try:
        # PyInstaller创建的临时文件夹路径
        base_path = sys._MEIPASS
    except Exception:
        # 如果不是打包环境，使用当前目录
        base_path = exe_dir

    # # 确保目录存在
    # dir_name = os.path.dirname(relative_path)
    # if dir_name:
    #     os.makedirs(os.path.join(exe_dir, dir_name), exist_ok=True)

    return os.path.join(base_path, relative_path)

# 示例：获取 icon.ico 和 tasks_data.json 的路径
# 示例：获取 icon.ico 和 tasks_data.json 的路径
ICON_PATH = resource_path("assets/icon.ico")
APP_NAME = "ScheduledTaskApp"
DATA_FILE = resource_path("data/tasks_data.json")

# 定义主题类型
THEME_SYSTEM = "system"
THEME_LIGHT = "light"
THEME_DARK = "dark"

class TaskData:
    def __init__(self):
        self.tasks = []
        self.load_data()

    def load_data(self):
        try:
            if os.path.exists(DATA_FILE):
                with open(DATA_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.tasks = data.get('tasks', [])
        except Exception as e:
            print(f"加载数据失败: {e}")
            self.tasks = []

    def save_data(self):
        try:
            data = {'tasks': self.tasks}
            with open(DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存数据失败: {e}")

    def add_task(self, content, weekdays, time_str):
        task = {
            'id': len(self.tasks) + 1,
            'content': content,
            'weekdays': weekdays,
            'time': time_str,
            'enabled': True,
            'last_triggered': None
        }
        self.tasks.append(task)
        self.save_data()
        return task

    def remove_task(self, task_id):
        self.tasks = [t for t in self.tasks if t['id'] != task_id]
        self.save_data()

    def get_active_tasks(self):
        return [t for t in self.tasks if t['enabled']]

class CustomNotification(QDialog):
    def __init__(self, task, parent=None, is_dark_mode=False):
        super().__init__(parent)
        self.task = task
        self.is_dark_mode = is_dark_mode
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("📅 定期提醒")
        self.setFixedSize(400, 200)
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Dialog)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # 时间标签
        time_label = QLabel(f"⏰ {self.task['time']}")
        time_label.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {'#ecf0f1' if self.is_dark_mode else '#2c3e50'};")
        layout.addWidget(time_label)

        # 内容
        content_label = QLabel(self.task['content'])
        content_label.setWordWrap(True)
        content_label.setStyleSheet(f"font-size: 14px; color: {'#ecf0f1' if self.is_dark_mode else '#34495e'}; padding: 10px; background-color: {'#2c3e50' if self.is_dark_mode else '#f8f9fa'}; border-radius: 5px;")
        layout.addWidget(content_label)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        ok_btn = QPushButton("知道了")
        ok_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {'#3498db' if not self.is_dark_mode else '#2980b9'};
                color: {'#ecf0f1' if self.is_dark_mode else 'white'};
                border: none;
                border-radius: 5px;
                padding: 8px 20px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {'#2980b9' if not self.is_dark_mode else '#3498db'};
            }}
        """)
        ok_btn.clicked.connect(self.accept)
        btn_layout.addWidget(ok_btn)

        layout.addLayout(btn_layout)

        # 设置对话框背景色
        if self.is_dark_mode:
            self.setStyleSheet("background-color: #1e272e;")

class ModernMainWindow(QMainWindow):
    def __init__(self, tray_app):
        super().__init__()
        self.tray_app = tray_app
        self.task_data = tray_app.task_data
        self.setup_ui()
        self.apply_theme()
        self.load_tasks()

    def setup_ui(self):
        self.setWindowTitle("定期提醒工具")
        self.setGeometry(500, 200, 700, 600)
        self.setMinimumSize(600, 500)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(30, 30, 30, 30)

        # 标题
        title_label = QLabel("📅 定期提醒任务管理")
        title_label.setObjectName("titleLabel")
        main_layout.addWidget(title_label)

        # 任务添加区域
        add_group = QGroupBox("添加新任务")
        add_group.setObjectName("addGroup")
        add_layout = QVBoxLayout(add_group)

        # 任务内容输入
        content_layout = QHBoxLayout()
        content_layout.addWidget(QLabel("提醒内容:"))
        self.content_input = QTextEdit()
        self.content_input.setMaximumHeight(80)
        self.content_input.setPlaceholderText("请输入提醒内容...")
        content_layout.addWidget(self.content_input)
        add_layout.addLayout(content_layout)

        # 星期选择
        week_layout = QHBoxLayout()
        week_layout.addWidget(QLabel("提醒星期:"))
        self.weekday_checkboxes = []
        weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        for i, day in enumerate(weekdays):
            checkbox = QCheckBox(day)
            checkbox.setObjectName(f"weekday_{i}")
            self.weekday_checkboxes.append(checkbox)
            week_layout.addWidget(checkbox)
        add_layout.addLayout(week_layout)

        # 时间设置
        time_layout = QHBoxLayout()
        time_layout.addWidget(QLabel("提醒时间:"))
        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm")
        self.time_edit.setTime(QTime(9, 0))
        time_layout.addWidget(self.time_edit)
        time_layout.addStretch()

        self.add_btn = QPushButton("➕ 添加任务")
        self.add_btn.setObjectName("addButton")
        self.add_btn.clicked.connect(self.add_task)
        time_layout.addWidget(self.add_btn)
        add_layout.addLayout(time_layout)

        main_layout.addWidget(add_group)

        # 任务列表区域
        list_group = QGroupBox("当前任务列表")
        list_group.setObjectName("listGroup")
        list_layout = QVBoxLayout(list_group)

        self.task_list = QListWidget()
        self.task_list.setObjectName("taskList")
        self.task_list.itemDoubleClicked.connect(self.remove_task)
        list_layout.addWidget(self.task_list)

        main_layout.addWidget(list_group)

        # 底部按钮区域
        btn_layout = QHBoxLayout()

        # 开机自启动复选框
        self.startup_checkbox = QCheckBox("⚙️ 开机自启动")
        self.startup_checkbox.setObjectName("startupCheckbox")
        self.startup_checkbox.setChecked(self.is_startup_enabled())
        self.startup_checkbox.stateChanged.connect(self.toggle_startup)
        btn_layout.addWidget(self.startup_checkbox)

        btn_layout.addStretch()

        self.minimize_btn = QPushButton("🔽 最小化到托盘")
        self.minimize_btn.setObjectName("minimizeButton")
        self.minimize_btn.clicked.connect(self.hide)
        btn_layout.addWidget(self.minimize_btn)

        self.close_btn = QPushButton("❌ 关闭程序")
        self.close_btn.setObjectName("closeButton")
        self.close_btn.clicked.connect(self.close_app)
        btn_layout.addWidget(self.close_btn)

        main_layout.addLayout(btn_layout)

    def apply_theme(self):
        theme = self.tray_app.settings.value("theme", THEME_SYSTEM, type=str)
        is_dark = False
        
        if theme == THEME_SYSTEM:
            is_dark = is_windows_dark_mode()
        elif theme == THEME_DARK:
            is_dark = True
            
        if is_dark:
            self.apply_dark_style()
        else:
            self.apply_light_style()

    def apply_light_style(self):
        style = """
        QMainWindow {
            background-color: #f8f9fa;
        }

        #titleLabel {
            font-size: 24px;
            font-weight: bold;
            color: #2c3e50;
            padding: 10px;
            background-color: #ecf0f1;
            border-radius: 8px;
            margin-bottom: 10px;
        }

        QGroupBox {
            font-size: 14px;
            font-weight: bold;
            color: #34495e;
            border: 2px solid #bdc3c7;
            border-radius: 10px;
            margin-top: 10px;
            padding-top: 10px;
        }

        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 8px 0 8px;
            background-color: #f8f9fa;
        }

        QTextEdit, QLineEdit {
            border: 2px solid #e0e0e0;
            border-radius: 6px;
            padding: 8px;
            font-size: 12px;
            background-color: white;
        }

        QTextEdit:focus, QLineEdit:focus {
            border-color: #3498db;
        }

        QTimeEdit {
            border: 2px solid #e0e0e0;
            border-radius: 6px;
            padding: 8px;
            font-size: 12px;
            background-color: white;
            min-width: 80px;
        }

        QCheckBox {
            font-size: 12px;
            spacing: 5px;
        }

        QCheckBox::indicator {
            width: 18px;
            height: 18px;
            border-radius: 3px;
            border: 2px solid #bdc3c7;
        }

        QCheckBox::indicator:checked {
            background-color: #3498db;
            border-color: #3498db;
        }

        #startupCheckbox {
            font-size: 14px;
            font-weight: bold;
            color: #8e44ad;
            spacing: 8px;
        }

        #startupCheckbox::indicator {
            width: 20px;
            height: 20px;
            border-radius: 4px;
            border: 2px solid #8e44ad;
        }

        #startupCheckbox::indicator:checked {
            background-color: #8e44ad;
            border-color: #8e44ad;
        }

        #addButton {
            background-color: #27ae60;
            color: white;
            border: none;
            border-radius: 6px;
            padding: 10px 20px;
            font-size: 12px;
            font-weight: bold;
        }

        #addButton:hover {
            background-color: #229954;
        }

        #minimizeButton {
            background-color: #f39c12;
            color: white;
            border: none;
            border-radius: 6px;
            padding: 10px 20px;
            font-size: 12px;
            font-weight: bold;
        }

        #minimizeButton:hover {
            background-color: #e67e22;
        }

        #closeButton {
            background-color: #e74c3c;
            color: white;
            border: none;
            border-radius: 6px;
            padding: 10px 20px;
            font-size: 12px;
            font-weight: bold;
        }

        #closeButton:hover {
            background-color: #c0392b;
        }

        #taskList {
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            background-color: white;
            alternate-background-color: #f8f9fa;
            selection-background-color: #3498db;
            font-size: 12px;
        }

        QListWidget::item {
            padding: 10px;
            border-bottom: 1px solid #ecf0f1;
        }

        QListWidget::item:hover {
            background-color: #e8f4fd;
        }

        QListWidget::item:selected {
            background-color: #3498db;
            color: white;
        }

        QComboBox {
            border: 2px solid #e0e0e0;
            border-radius: 6px;
            padding: 8px;
            font-size: 12px;
            background-color: white;
            min-width: 120px;
        }

        QComboBox::drop-down {
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 20px;
            border-left-width: 1px;
            border-left-color: #e0e0e0;
            border-left-style: solid;
        }
        """
        self.setStyleSheet(style)

    def apply_dark_style(self):
        style = """
        QMainWindow {
            background-color: #1e272e;
            color: #ecf0f1;
        }

        QLabel {
            color: #ecf0f1;
        }

        #titleLabel {
            font-size: 24px;
            font-weight: bold;
            color: #ecf0f1;
            padding: 10px;
            background-color: #2c3e50;
            border-radius: 8px;
            margin-bottom: 10px;
        }

        QGroupBox {
            font-size: 14px;
            font-weight: bold;
            color: #ecf0f1;
            border: 2px solid #34495e;
            border-radius: 10px;
            margin-top: 10px;
            padding-top: 10px;
        }

        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 8px 0 8px;
            background-color: #1e272e;
        }

        QTextEdit, QLineEdit {
            border: 2px solid #34495e;
            border-radius: 6px;
            padding: 8px;
            font-size: 12px;
            background-color: #2c3e50;
            color: #ecf0f1;
        }

        QTextEdit:focus, QLineEdit:focus {
            border-color: #3498db;
        }

        QTimeEdit {
            border: 2px solid #34495e;
            border-radius: 6px;
            padding: 8px;
            font-size: 12px;
            background-color: #2c3e50;
            color: #ecf0f1;
            min-width: 80px;
        }

        QCheckBox {
            font-size: 12px;
            spacing: 5px;
            color: #ecf0f1;
        }

        QCheckBox::indicator {
            width: 18px;
            height: 18px;
            border-radius: 3px;
            border: 2px solid #7f8c8d;
        }

        QCheckBox::indicator:checked {
            background-color: #3498db;
            border-color: #3498db;
        }

        #startupCheckbox {
            font-size: 14px;
            font-weight: bold;
            color: #9b59b6;
            spacing: 8px;
        }

        #startupCheckbox::indicator {
            width: 20px;
            height: 20px;
            border-radius: 4px;
            border: 2px solid #9b59b6;
        }

        #startupCheckbox::indicator:checked {
            background-color: #9b59b6;
            border-color: #9b59b6;
        }

        #addButton {
            background-color: #27ae60;
            color: #ecf0f1;
            border: none;
            border-radius: 6px;
            padding: 10px 20px;
            font-size: 12px;
            font-weight: bold;
        }

        #addButton:hover {
            background-color: #2ecc71;
        }

        #minimizeButton {
            background-color: #d35400;
            color: #ecf0f1;
            border: none;
            border-radius: 6px;
            padding: 10px 20px;
            font-size: 12px;
            font-weight: bold;
        }

        #minimizeButton:hover {
            background-color: #e67e22;
        }

        #closeButton {
            background-color: #c0392b;
            color: #ecf0f1;
            border: none;
            border-radius: 6px;
            padding: 10px 20px;
            font-size: 12px;
            font-weight: bold;
        }

        #closeButton:hover {
            background-color: #e74c3c;
        }

        #taskList {
            border: 2px solid #34495e;
            border-radius: 8px;
            background-color: #2c3e50;
            alternate-background-color: #34495e;
            selection-background-color: #3498db;
            color: #ecf0f1;
            font-size: 12px;
        }

        QListWidget::item {
            padding: 10px;
            border-bottom: 1px solid #34495e;
            color: #ecf0f1;
        }

        QListWidget::item:hover {
            background-color: #34495e;
        }

        QListWidget::item:selected {
            background-color: #3498db;
            color: #ecf0f1;
        }

        QComboBox {
            border: 2px solid #34495e;
            border-radius: 6px;
            padding: 8px;
            font-size: 12px;
            background-color: #2c3e50;
            color: #ecf0f1;
            min-width: 120px;
        }

        QComboBox::drop-down {
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 20px;
            border-left-width: 1px;
            border-left-color: #34495e;
            border-left-style: solid;
        }

        QMenu {
            background-color: #2c3e50;
            color: #ecf0f1;
            border: 1px solid #34495e;
        }

        QMenu::item {
            padding: 5px 20px 5px 20px;
        }

        QMenu::item:selected {
            background-color: #3498db;
        }

        QMessageBox {
            background-color: #1e272e;
            color: #ecf0f1;
        }
        """
        self.setStyleSheet(style)

    def add_task(self):
        content = self.content_input.toPlainText().strip()
        if not content:
            QMessageBox.warning(self, "警告", "请输入提醒内容！")
            return

        selected_weekdays = []
        for i, checkbox in enumerate(self.weekday_checkboxes):
            if checkbox.isChecked():
                selected_weekdays.append(i)

        if not selected_weekdays:
            QMessageBox.warning(self, "警告", "请至少选择一个星期！")
            return

        time_str = self.time_edit.time().toString("HH:mm")

        self.task_data.add_task(content, selected_weekdays, time_str)
        self.load_tasks()
        self.clear_inputs()

        QMessageBox.information(self, "成功", "任务添加成功！")

    def clear_inputs(self):
        self.content_input.clear()
        for checkbox in self.weekday_checkboxes:
            checkbox.setChecked(False)
        self.time_edit.setTime(QTime(9, 0))

    def load_tasks(self):
        self.task_list.clear()
        weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

        for task in self.task_data.tasks:
            weekdays_str = ", ".join([weekday_names[w] for w in task['weekdays']])
            status = "✅" if task['enabled'] else "❌"
            item_text = f"{status} {task['content'][:30]}{'...' if len(task['content']) > 30 else ''} | {weekdays_str} | {task['time']}"

            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, task['id'])
            self.task_list.addItem(item)

    def remove_task(self, item):
        task_id = item.data(Qt.ItemDataRole.UserRole)
        reply = QMessageBox.question(self, "确认删除", "确定要删除这个任务吗？",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.task_data.remove_task(task_id)
            self.load_tasks()

    def is_startup_enabled(self):
        """检查是否已设置开机自启动"""
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                 r"Software\Microsoft\Windows\CurrentVersion\Run",
                                 0, winreg.KEY_READ)
            winreg.QueryValueEx(key, APP_NAME)
            winreg.CloseKey(key)
            return True
        except FileNotFoundError:
            return False
        except Exception:
            return False

    def toggle_startup(self):
        """切换开机自启动状态"""
        if self.startup_checkbox.isChecked():
            self.enable_startup()
        else:
            self.disable_startup()

    def enable_startup(self):
        """启用开机自启动"""
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                 r"Software\Microsoft\Windows\CurrentVersion\Run",
                                 0, winreg.KEY_SET_VALUE)
            if getattr(sys, 'frozen', False):
                app_path = sys.executable
            else:
                app_path = os.path.abspath(__file__)

            if not getattr(sys, 'frozen', False):
                bat_path = os.path.join(APP_DIR, f"{APP_NAME}.bat")
                with open(bat_path, "w") as bat_file:
                    bat_file.write(f'@echo off\n"{sys.executable}" "{app_path}"')
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, f'"{bat_path}"')
            else:
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, f'"{app_path}"')
            winreg.CloseKey(key)
            QMessageBox.information(self, "设置成功", "开机自启动已启用！")
        except Exception as e:
            QMessageBox.warning(self, "设置失败", f"无法设置开机自启动: {e}")
            self.startup_checkbox.setChecked(False)

    def disable_startup(self):
        """禁用开机自启动"""
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                 r"Software\Microsoft\Windows\CurrentVersion\Run",
                                 0, winreg.KEY_SET_VALUE)
            winreg.DeleteValue(key, APP_NAME)
            winreg.CloseKey(key)
            bat_path = os.path.join(APP_DIR, f"{APP_NAME}.bat")
            if os.path.exists(bat_path):
                os.remove(bat_path)
            QMessageBox.information(self, "设置成功", "开机自启动已禁用！")
        except FileNotFoundError:
            pass
        except Exception as e:
            QMessageBox.warning(self, "设置失败", f"无法取消开机自启动: {e}")
            self.startup_checkbox.setChecked(True)

    def closeEvent(self, event):
        self.hide()
        event.ignore()
    
    def close_app(self):
        self.tray_app.quit_application()

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.settings = QSettings("MyCompany", APP_NAME)
        self.setup_ui()
        self.apply_theme()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # 每日弹窗提醒
        self.daily_popup_checkbox = QCheckBox("启用每日弹窗提醒")
        self.daily_popup_checkbox.setChecked(self.settings.value("daily_popup", True, type=bool))
        layout.addWidget(self.daily_popup_checkbox)

        # 主题设置
        theme_layout = QHBoxLayout()
        theme_layout.addWidget(QLabel("应用主题:"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItem("跟随系统", THEME_SYSTEM)
        self.theme_combo.addItem("浅色模式", THEME_LIGHT)
        self.theme_combo.addItem("深色模式", THEME_DARK)
        
        current_theme = self.settings.value("theme", THEME_SYSTEM, type=str)
        index = self.theme_combo.findData(current_theme)
        if index >= 0:
            self.theme_combo.setCurrentIndex(index)
            
        theme_layout.addWidget(self.theme_combo)
        layout.addLayout(theme_layout)

        # 保存按钮
        self.save_button = QPushButton("保存设置")
        self.save_button.clicked.connect(self.save_settings)
        layout.addWidget(self.save_button)

    def save_settings(self):
        self.settings.setValue("daily_popup", self.daily_popup_checkbox.isChecked())
        self.settings.setValue("theme", self.theme_combo.currentData())
        QMessageBox.information(self, "设置已保存", "设置已成功保存！需要重启应用以应用主题更改。")
        self.accept()

    def apply_theme(self):
        theme = self.settings.value("theme", THEME_SYSTEM, type=str)
        is_dark = False
        
        if theme == THEME_SYSTEM:
            is_dark = is_windows_dark_mode()
        elif theme == THEME_DARK:
            is_dark = True
            
        if is_dark:
            self.setStyleSheet("""
                QDialog {
                    background-color: #1e272e;
                    color: #ecf0f1;
                }
                QLabel {
                    color: #ecf0f1;
                }
                QCheckBox {
                    color: #ecf0f1;
                }
                QPushButton {
                    background-color: #3498db;
                    color: #ecf0f1;
                    border: none;
                    border-radius: 5px;
                    padding: 8px 20px;
                }
                QPushButton:hover {
                    background-color: #2980b9;
                }
                QComboBox {
                    border: 2px solid #34495e;
                    border-radius: 6px;
                    padding: 8px;
                    background-color: #2c3e50;
                    color: #ecf0f1;
                }
            """)

class TrayApplication(QApplication):
    def __init__(self, *args, socket=None, **kwargs):  # 添加 socket 关键字参数
        super().__init__(*args, **kwargs)
        self.setQuitOnLastWindowClosed(False)
        
        self.settings = QSettings("MyCompany", APP_NAME)
        self.task_data = TaskData()
        self.main_window = ModernMainWindow(self)
        self.settings_dialog = SettingsDialog()
        self.last_check_time = datetime.datetime.now().replace(second=0, microsecond=0)

        # 单实例套接字服务器
        self.server_socket = socket  # 使用传入的 socket 参数
        if self.server_socket:
            self.socket_notifier = QSocketNotifier(self.server_socket.fileno(), QSocketNotifier.Type.Read, self)
            self.socket_notifier.activated.connect(self.handle_socket_connection)

        # 创建托盘图标
        self.tray_icon = QSystemTrayIcon(self)
        self.create_icon()
        if not self.tray_icon.icon().isNull():
            self.tray_icon.show()
        else:
            from PyQt6.QtWidgets import QStyle
            fallback_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxInformation)
            self.tray_icon.setIcon(fallback_icon)
            self.tray_icon.show()

        # 创建托盘菜单
        self.tray_menu = QMenu()
        
        show_action = QAction("显示主窗口", self)
        show_action.triggered.connect(self.show_main_window)
        self.tray_menu.addAction(show_action)
        
        settings_action = QAction("设置", self)
        settings_action.triggered.connect(self.show_settings_dialog)
        self.tray_menu.addAction(settings_action)
        
        self.tray_menu.addSeparator()
        
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.quit_application)
        self.tray_menu.addAction(exit_action)

        # 应用主题到托盘菜单
        theme = self.settings.value("theme", THEME_SYSTEM, type=str)
        is_dark = False
        if theme == THEME_SYSTEM:
            is_dark = is_windows_dark_mode()
        elif theme == THEME_DARK:
            is_dark = True
            
        if is_dark:
            self.tray_menu.setStyleSheet("""
                QMenu {
                    background-color: #2c3e50;
                    color: #ecf0f1;
                    border: 1px solid #34495e;
                }
                QMenu::item {
                    padding: 5px 20px 5px 20px;
                }
                QMenu::item:selected {
                    background-color: #3498db;
                }
            """)

        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.activated.connect(self.on_tray_icon_activated)

        # 定时器检查时间
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_time_and_notify)
        self.timer.start(10000)
        
        print(f"应用程序启动。加载了 {len(self.task_data.tasks)} 个任务。")
        self.check_time_and_notify()

    def create_icon(self):
        if os.path.exists(ICON_PATH):
            icon = QIcon(ICON_PATH)
            if not icon.isNull():
                self.tray_icon.setIcon(icon)
            else:
                self.set_default_icon()
        else:
            self.set_default_icon()

    def set_default_icon(self):
        try:
            from PyQt6.QtWidgets import QStyle
            fallback_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxInformation)
            self.tray_icon.setIcon(fallback_icon)
        except Exception as e:
            print(f"设置图标错误: {e}")

    def show_main_window(self):
        self.main_window.show()
        self.main_window.raise_()
        self.main_window.activateWindow()

    def show_settings_dialog(self):
        self.settings_dialog.exec()

    def check_time_and_notify(self):
        current_datetime = datetime.datetime.now().replace(second=0, microsecond=0)
        current_weekday = current_datetime.weekday()
        current_time_str = current_datetime.strftime("%H:%M")
        
        if current_datetime <= self.last_check_time:
            return
        
        self.last_check_time = current_datetime
        
        for task in self.task_data.get_active_tasks():
            if (current_weekday in task['weekdays'] and 
                task['time'] == current_time_str):
                
                last_triggered = task.get('last_triggered')
                today_str = current_datetime.date().isoformat()
                
                if last_triggered != today_str:
                    self.show_custom_notification(task)
                    task['last_triggered'] = today_str
                    self.task_data.save_data()

    def show_custom_notification(self, task):
        # 托盘通知
        title = "📅 定期提醒"
        message = f"⏰ {task['time']}\n\n{task['content']}"
        self.tray_icon.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 8000)
        
        # 弹窗通知（如果启用）
        if self.settings.value("daily_popup", True, type=bool):
            # 检查是否为暗黑模式
            theme = self.settings.value("theme", THEME_SYSTEM, type=str)
            is_dark = False
            if theme == THEME_SYSTEM:
                is_dark = is_windows_dark_mode()
            elif theme == THEME_DARK:
                is_dark = True
                
            notification = CustomNotification(task, is_dark_mode=is_dark)
            notification.exec()

    def on_tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.show_main_window()

    def handle_socket_connection(self):
        # 接受连接并显示主窗口
        try:
            client_socket, _ = self.server_socket.accept()
            client_socket.recv(1024)  # 接收数据（不需要处理）
            client_socket.close()
            self.show_main_window()
        except Exception as e:
            print(f"处理套接字连接错误: {e}")

    def quit_application(self):
        print("退出应用程序...")
        self.timer.stop()
        self.tray_icon.hide()
        if hasattr(self, 'socket_notifier'):
            self.socket_notifier.setEnabled(False)
        if hasattr(self, 'server_socket'):
            self.server_socket.close()
        self.quit()

if __name__ == "__main__":
    is_running, sock = is_instance_running()
    if is_running:
        activate_existing_instance()
        sys.exit(0)
    app = TrayApplication(sys.argv, socket=sock)
    app.main_window.show()
    exit_code = app.exec()
    sys.exit(exit_code)