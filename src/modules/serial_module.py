import serial
import serial.tools.list_ports
from PyQt5.QtCore import QThread, pyqtSignal, QTimer
from typing import Optional, List, Dict
import time
import random
from .CommunicationProtocol import parse_frame

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
        self.last_data_time = 0  # 记录最后一次收到数据的时间
        self.check_timer = QTimer()  # 用于定期检查串口状态
        self.check_timer.timeout.connect(self.check_connection)
        self.check_timer.start(1000)  # 每秒检查一次
        
    @staticmethod
    def list_ports() -> List[str]:
        """列出所有可用的串口"""
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports]
    
    def connect(self, port: str) -> bool:
        """连接到指定串口"""
        try:
            self.serial = serial.Serial(port, self.baud_rate, timeout=0.1)
            if self.serial.is_open:
                # 清空串口缓冲区
                self.serial.reset_input_buffer()
                self.serial.reset_output_buffer()
                
                # 等待并检查是否有数据传入
                start_time = time.time()
                while time.time() - start_time < 5:  # 最多等待5秒
                    if self.serial.in_waiting:
                        # 尝试读取数据
                        data = self.serial.read(self.serial.in_waiting)
                        if data:
                            # 找到有效数据，切换到正常模式
                            self.simulation_mode = False
                            self.last_data_time = time.time()
                            self.connection_status.emit(True, port)
                            print(f"串口 {port} 连接成功，检测到数据")
                            return True
                    time.sleep(0.1)  # 短暂等待，避免CPU占用过高
                
                # 5秒内没有收到数据，切换到模拟模式
                self.simulation_mode = True
                self.connection_status.emit(False, "")
                self.error_occurred.emit(f"串口 {port} 连接成功但未检测到数据，切换到模拟模式")
                return False
                
        except Exception as e:
            self.error_occurred.emit(f"串口连接失败: {str(e)}")
            self.simulation_mode = True
        return False
    
    def check_connection(self):
        """检查串口连接状态"""
        if not self.simulation_mode and self.serial and self.serial.is_open:
            current_time = time.time()
            if current_time - self.last_data_time > 5:  # 5秒没有数据
                self.simulation_mode = True
                self.connection_status.emit(False, "")
                self.error_occurred.emit("串口连接超时，切换到模拟模式")
    
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
        buf = bytearray()
        
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
                        # 读入串口所有可用字节
                        data = self.serial.read(self.serial.in_waiting or 1)
                        if data:
                            buf.extend(data)
                            self.last_data_time = time.time()  # 更新最后接收时间
                        
                        # 在缓冲区里找包头
                        while True:
                            idx = buf.find(b'\xAA')
                            if idx < 0 or len(buf) - idx < 8:  # 8字节一帧
                                break
                            
                            # 截取一帧
                            frame = buf[idx: idx + 8]
                            # 移除已处理部分
                            del buf[: idx + 8]
                            
                            # 解析数据
                            try:
                                info = parse_frame(frame)
                                # 转换数据格式以匹配UI显示
                                data = {
                                    'temperature': info['temperature_C'],
                                    'humidity': info['humidity_pct'],
                                    'depth': info['depth_cm'] / 100.0,  # 转换为米
                                    'heading': info['heading_deg'],
                                    'voltage': info['battery_V']
                                }
                                self.data_received.emit(data)
                            except Exception as e:
                                self.error_occurred.emit(f"数据解析错误: {str(e)}")
                    
            except Exception as e:
                self.error_occurred.emit(f"数据接收错误: {str(e)}")
                if not self.simulation_mode:
                    self.simulation_mode = True
                    self.connection_status.emit(False, "")
    
    def wait(self, timeout=None):
        """等待线程结束，支持超时"""
        if timeout is not None:
            return super().wait(timeout)
        return super().wait()

    def stop(self):
        """停止串口通信"""
        self.running = False
        self.check_timer.stop()
        self.disconnect() 