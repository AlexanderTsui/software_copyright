import pygame
from PyQt5.QtCore import QThread, pyqtSignal
from typing import Dict, Optional
import time

class GamepadModule(QThread):
    data_updated = pyqtSignal(dict)  # 发送手柄数据
    error_occurred = pyqtSignal(str)  # 发送错误信息
    connection_status = pyqtSignal(bool)  # 发送连接状态
    
    def __init__(self):
        super().__init__()
        self.running = False
        self.simulation_mode = True
        self.joystick: Optional[pygame.joystick.Joystick] = None
        
        # 初始化pygame
        try:
            pygame.init()
            pygame.joystick.init()
        except Exception as e:
            self.error_occurred.emit(f"游戏手柄初始化失败: {str(e)}")
    
    def connect(self) -> bool:
        """连接到游戏手柄"""
        try:
            if pygame.joystick.get_count() > 0:
                self.joystick = pygame.joystick.Joystick(0)
                self.joystick.init()
                self.simulation_mode = False
                self.connection_status.emit(True)
                print("手柄连接成功")
                return True
        except Exception as e:
            self.error_occurred.emit(f"游戏手柄连接失败: {str(e)}")
            self.simulation_mode = True
        return False
    
    def disconnect(self):
        """断开游戏手柄连接"""
        if self.joystick:
            self.joystick.quit()
            self.joystick = None
        self.simulation_mode = True
        self.connection_status.emit(False)
    
    def generate_simulation_data(self) -> Dict:
        """生成模拟的手柄数据"""
        return {
            'left_stick_x': 0.0,
            'left_stick_y': 0.0,
            'right_stick_x': 0.0,
            'right_stick_y': 0.0,
            'buttons': [False] * 8
        }
    
    def get_gamepad_data(self) -> Dict:
        """获取实际的手柄数据"""
        if not self.joystick:
            return self.generate_simulation_data()
        
        try:
            pygame.event.pump()
            
            return {
                'left_stick_x': self.joystick.get_axis(0),
                'left_stick_y': self.joystick.get_axis(1),
                'right_stick_x': self.joystick.get_axis(2),
                'right_stick_y': self.joystick.get_axis(3),
                'buttons': [self.joystick.get_button(i) for i in range(8)]
            }
        except Exception as e:
            self.error_occurred.emit(f"读取手柄数据失败: {str(e)}")
            return self.generate_simulation_data()
    
    def run(self):
        """线程运行函数"""
        self.running = True
        
        while self.running:
            try:
                if self.simulation_mode:
                    data = self.generate_simulation_data()
                else:
                    data = self.get_gamepad_data()
                
                self.data_updated.emit(data)
                time.sleep(0.02)  # 50Hz更新频率
                
            except Exception as e:
                self.error_occurred.emit(f"手柄数据更新错误: {str(e)}")
                if not self.simulation_mode:
                    self.simulation_mode = True
    
    def wait(self, timeout=None):
        """等待线程结束，支持超时"""
        if timeout is not None:
            return super().wait(timeout)
        return super().wait()

    def stop(self):
        """停止手柄数据读取"""
        self.running = False
        self.disconnect()
        try:
            pygame.quit()
        except:
            pass 