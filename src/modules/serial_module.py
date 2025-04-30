import serial
import serial.tools.list_ports
from PyQt5.QtCore import QThread, pyqtSignal
from typing import Optional, List, Dict
import time
import random

class SerialModule(QThread):
    data_received = pyqtSignal(dict)  # 发送接收到的数据
    error_occurred = pyqtSignal(str)  # 发送错误信息
    connection_status = pyqtSignal(bool, str)  # 发送连接状态和串口号
    
    def __init__(self, baud_rate: int = 115200):
        super().__init__()
        self.serial: Optional[serial.Serial] = None
        self.baud_rate = baud_rate
        self.running = False
        self.simulation_mode = True
        
    @staticmethod
    def list_ports() -> List[str]:
        """列出所有可用的串口"""
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports]
    
    def connect(self, port: str) -> bool:
        """连接到指定串口"""
        try:
            self.serial = serial.Serial(port, self.baud_rate, timeout=1)
            if self.serial.is_open:
                self.simulation_mode = False
                self.connection_status.emit(True, port)
                return True
        except Exception as e:
            self.error_occurred.emit(f"串口连接失败: {str(e)}")
            self.simulation_mode = True
        return False
    
    def disconnect(self):
        """断开串口连接"""
        if self.serial and self.serial.is_open:
            self.serial.close()
        self.simulation_mode = True
        self.connection_status.emit(False, "")
    
    def send_data(self, data: bytes):
        """发送数据到串口"""
        if self.serial and self.serial.is_open:
            try:
                self.serial.write(data)
            except Exception as e:
                self.error_occurred.emit(f"数据发送失败: {str(e)}")
    
    def generate_simulation_data(self) -> Dict:
        """生成模拟数据"""
        return {
            'temperature': 25 + random.uniform(-2, 2),
            'humidity': 60 + random.uniform(-5, 5),
            'depth': 10 + random.uniform(-1, 1),
            'heading': random.uniform(0, 360),
            'voltage': 12 + random.uniform(-0.5, 0.5)
        }
    
    def run(self):
        """线程运行函数"""
        self.running = True
        
        while self.running:
            try:
                if self.simulation_mode:
                    # 生成模拟数据
                    data = self.generate_simulation_data()
                    self.data_received.emit(data)
                    time.sleep(0.1)  # 模拟数据更新频率
                else:
                    # 从串口读取数据
                    if self.serial and self.serial.is_open:
                        if self.serial.in_waiting:
                            # 这里需要根据实际的通信协议解析数据
                            raw_data = self.serial.readline()
                            # TODO: 解析数据包
                            # data = self.parse_data(raw_data)
                            # self.data_received.emit(data)
                    
            except Exception as e:
                self.error_occurred.emit(f"数据接收错误: {str(e)}")
                if not self.simulation_mode:
                    self.simulation_mode = True
    
    def wait(self, timeout=None):
        """等待线程结束，支持超时"""
        if timeout is not None:
            return super().wait(timeout)
        return super().wait()

    def stop(self):
        """停止串口通信"""
        self.running = False
        self.disconnect() 