import cv2
import numpy as np
import socket
import threading
from PyQt5.QtCore import QThread, pyqtSignal
from typing import Optional, Tuple

class VideoReceiver(QThread):
    frame_received = pyqtSignal(np.ndarray)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, host: str = 'localhost', port: int = 8000):
        super().__init__()
        self.host = host
        self.port = port
        self.running = False
        self.socket: Optional[socket.socket] = None
        self.connected = False
        
        # 用于模拟视频的属性
        self.simulation_mode = True
        self.cap: Optional[cv2.VideoCapture] = None
    
    def connect_to_rov(self) -> bool:
        """尝试连接到ROV"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.connected = True
            self.simulation_mode = False
            return True
        except Exception as e:
            self.error_occurred.emit(f"连接失败: {str(e)}")
            self.simulation_mode = True
            return False
    
    def start_simulation(self):
        """启动模拟模式，使用本地摄像头或测试视频"""
        try:
            self.cap = cv2.VideoCapture(0)  # 尝试打开本地摄像头
            if not self.cap.isOpened():
                # 如果没有摄像头，创建一个模拟画面
                self.cap = None
                self.simulation_mode = True
            else:
                self.simulation_mode = True
        except Exception as e:
            self.error_occurred.emit(f"模拟模式启动失败: {str(e)}")
    
    def create_simulation_frame(self) -> np.ndarray:
        """创建模拟视频帧"""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        # 添加一些测试图形 (使用BGR颜色格式)
        cv2.putText(frame, "Simulation Mode", (50, 50),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)  # BGR格式的绿色
        cv2.rectangle(frame, (100, 100), (540, 380), (0, 255, 0), 2)  # BGR格式的绿色
        return frame
    
    def run(self):
        """线程运行函数"""
        self.running = True
        
        if not self.connected:
            self.start_simulation()
        
        while self.running:
            try:
                if self.simulation_mode:
                    if self.cap is not None:
                        ret, frame = self.cap.read()
                        if not ret:
                            frame = self.create_simulation_frame()
                    else:
                        frame = self.create_simulation_frame()
                else:
                    # 从TCP接收视频数据
                    # 这里需要根据实际的视频传输协议进行实现
                    pass
                
                self.frame_received.emit(frame)
                
            except Exception as e:
                self.error_occurred.emit(f"视频接收错误: {str(e)}")
                if not self.simulation_mode:
                    self.simulation_mode = True
                    self.start_simulation()
    
    def wait(self, timeout=None):
        """等待线程结束，支持超时"""
        if timeout is not None:
            return super().wait(timeout)
        return super().wait()

    def stop(self):
        """停止视频接收"""
        self.running = False
        if self.socket:
            try:
                self.socket.shutdown(socket.SHUT_RDWR)
                self.socket.close()
            except:
                pass
        if self.cap:
            self.cap.release()

class VideoOverlay:
    """视频叠加层，用于在视频上显示数据"""
    
    @staticmethod
    def add_overlay(frame: np.ndarray, depth: float, heading: float, voltage: float) -> np.ndarray:
        """在视频帧上添加数据叠加层"""
        # 创建叠加层
        overlay = frame.copy()
        
        # 文本颜色 (BGR格式的白色)
        text_color = (255, 255, 255)
        
        # 添加文本信息
        cv2.putText(overlay, f"深度: {depth:.1f}m", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, text_color, 2)
        cv2.putText(overlay, f"航向: {heading:.1f}°", (10, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, text_color, 2)
        cv2.putText(overlay, f"电压: {voltage:.1f}V", (10, 90),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, text_color, 2)
        
        # 合并原始帧和叠加层
        alpha = 0.7
        return cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0) 