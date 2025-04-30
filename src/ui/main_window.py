from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QFrame)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QImage, QPixmap
import cv2
import numpy as np
import threading

from ..modules.video_module import VideoReceiver, VideoOverlay
from ..modules.serial_module import SerialModule
from ..modules.gamepad_module import GamepadModule

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ROV控制系统")
        self.resize(1200, 800)
        
        # 初始化模块
        self.video_receiver = VideoReceiver()
        self.serial_module = SerialModule()
        self.gamepad_module = GamepadModule()
        
        # 创建UI
        self.setup_ui()
        
        # 连接信号
        self.connect_signals()
        
        # 启动所有模块
        self.start_modules()
        
        # 用于优雅关闭的标志
        self.is_closing = False
    
    def setup_ui(self):
        """设置UI布局"""
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QHBoxLayout(central_widget)
        
        # 左侧布局（视频显示）
        left_layout = QVBoxLayout()
        self.video_frame = QLabel()
        self.video_frame.setMinimumSize(800, 600)
        self.video_frame.setFrameStyle(QFrame.Box | QFrame.Sunken)
        self.video_frame.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(self.video_frame)
        
        # 右侧布局
        right_layout = QVBoxLayout()
        
        # 串口控制
        self.port_button = QPushButton("选择串口号")
        self.port_button.clicked.connect(self.on_port_button_clicked)
        right_layout.addWidget(self.port_button)
        
        # 温湿度显示
        temp_humid_frame = QFrame()
        temp_humid_frame.setFrameStyle(QFrame.Box | QFrame.Sunken)
        temp_humid_layout = QVBoxLayout(temp_humid_frame)
        self.temp_label = QLabel("舱内温度: --°C")
        self.humid_label = QLabel("舱内湿度: --%")
        temp_humid_layout.addWidget(self.temp_label)
        temp_humid_layout.addWidget(self.humid_label)
        right_layout.addWidget(temp_humid_frame)
        
        # 手柄数据显示
        gamepad_frame = QFrame()
        gamepad_frame.setFrameStyle(QFrame.Box | QFrame.Sunken)
        gamepad_layout = QVBoxLayout(gamepad_frame)
        self.gamepad_labels = {
            'left_stick': QLabel("左摇杆: (0.00, 0.00)"),
            'right_stick': QLabel("右摇杆: (0.00, 0.00)"),
            'buttons': QLabel("按钮状态: []")
        }
        for label in self.gamepad_labels.values():
            gamepad_layout.addWidget(label)
        right_layout.addWidget(gamepad_frame)
        
        # 添加到主布局
        main_layout.addLayout(left_layout, stretch=7)
        main_layout.addLayout(right_layout, stretch=3)
    
    def connect_signals(self):
        """连接信号和槽"""
        # 视频模块信号
        self.video_receiver.frame_received.connect(self.update_video_frame)
        self.video_receiver.error_occurred.connect(self.handle_error)
        
        # 串口模块信号
        self.serial_module.data_received.connect(self.update_sensor_data)
        self.serial_module.error_occurred.connect(self.handle_error)
        self.serial_module.connection_status.connect(self.update_port_button)
        
        # 手柄模块信号
        self.gamepad_module.data_updated.connect(self.update_gamepad_data)
        self.gamepad_module.error_occurred.connect(self.handle_error)
    
    def start_modules(self):
        """启动所有模块"""
        self.video_receiver.start()
        self.serial_module.start()
        self.gamepad_module.start()
    
    def update_video_frame(self, frame: np.ndarray):
        """更新视频显示"""
        # BGR转RGB
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # 添加数据叠加层
        frame = VideoOverlay.add_overlay(
            frame,
            self.serial_module.generate_simulation_data()['depth'],
            self.serial_module.generate_simulation_data()['heading'],
            self.serial_module.generate_simulation_data()['voltage']
        )
        
        # 转换为QImage
        height, width, channel = frame.shape
        bytes_per_line = 3 * width
        q_image = QImage(frame.data, width, height, bytes_per_line, QImage.Format_RGB888)
        
        # 显示图像
        pixmap = QPixmap.fromImage(q_image)
        scaled_pixmap = pixmap.scaled(self.video_frame.size(), Qt.KeepAspectRatio)
        self.video_frame.setPixmap(scaled_pixmap)
    
    def update_sensor_data(self, data: dict):
        """更新传感器数据显示"""
        self.temp_label.setText(f"舱内温度: {data['temperature']:.1f}°C")
        self.humid_label.setText(f"舱内湿度: {data['humidity']:.1f}%")
    
    def update_gamepad_data(self, data: dict):
        """更新手柄数据显示"""
        self.gamepad_labels['left_stick'].setText(
            f"左摇杆: ({data['left_stick_x']:.2f}, {data['left_stick_y']:.2f})"
        )
        self.gamepad_labels['right_stick'].setText(
            f"右摇杆: ({data['right_stick_x']:.2f}, {data['right_stick_y']:.2f})"
        )
        self.gamepad_labels['buttons'].setText(
            f"按钮状态: {data['buttons']}"
        )
    
    def update_port_button(self, connected: bool, port: str):
        """更新串口按钮显示"""
        if connected:
            self.port_button.setText(f"串口号：{port}")
        else:
            self.port_button.setText("选择串口号")
    
    def on_port_button_clicked(self):
        """处理串口按钮点击事件"""
        # TODO: 显示串口选择对话框
        available_ports = self.serial_module.list_ports()
        if available_ports:
            # 这里简化处理，直接连接第一个可用串口
            self.serial_module.connect(available_ports[0])
    
    def handle_error(self, error_msg: str):
        """处理错误信息"""
        print(f"错误: {error_msg}")  # 这里可以改为显示错误对话框
    
    def closeEvent(self, event):
        """窗口关闭事件处理"""
        if self.is_closing:
            event.accept()
            return
            
        self.is_closing = True
        
        # 创建一个定时器在超时后强制关闭
        force_close_timer = QTimer(self)
        force_close_timer.setSingleShot(True)
        force_close_timer.timeout.connect(self.force_close)
        force_close_timer.start(1000)  # 1秒后强制关闭
        
        # 在单独的线程中关闭模块
        threading.Thread(target=self.cleanup_modules, daemon=True).start()
        
        # 先不接受关闭事件
        event.ignore()
    
    def cleanup_modules(self):
        """清理所有模块"""
        # 停止所有模块
        self.video_receiver.stop()
        self.serial_module.stop()
        self.gamepad_module.stop()
        
        # 确保所有模块都已停止
        modules = [self.video_receiver, self.serial_module, self.gamepad_module]
        for module in modules:
            module.wait(100)  # 等待最多100ms
            
        # 在主线程中关闭窗口
        self.close()
    
    def force_close(self):
        """强制关闭窗口"""
        # 确保所有模块停止运行
        self.video_receiver.running = False
        self.serial_module.running = False
        self.gamepad_module.running = False
        
        # 强制退出
        self.close() 