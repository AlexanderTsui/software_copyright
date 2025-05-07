import serial
import struct
import time

# 串口配置，根据设备的串口号和波特率调整
SERIAL_PORT = 'COM4'      # Windows 示例, macOS/Linux 可能是 '/dev/ttyUSB0'
BAUD_RATE = 115200
FRAME_LEN = 8            # 1 字节包头 + 7 字节数据

def parse_frame(frame: bytes):
    """
    frame: b'\xAA\x98\x14\x24\x01\xA1\x01\x0E'
    按顺序解析：电池电压、温度、湿度、深度H、深度L、航向H、航向L
    """
    # 跳过第一个字节（包头），其后 7 字节
    b_vol, temp, hum, d_h, d_l, hdg_h, hdg_l = struct.unpack('7B', frame[1:])
    
    # 电池电压： (高4bit*16 + 低4bit) + 100  再除 10
    # 但直接用 b_vol 即十六进制转十进制：举例 0x98 = 152 -> (152 + 100)/10
    battery = (b_vol + 100) / 10.0  # 单位 V
    
    # 温度：直接十六进制转十进制，单位 ℃
    temperature = temp
    
    # 湿度：直接十六进制转十进制，单位 %
    humidity = hum
    
    # 深度：高位在前，低位在后，单位 cm
    depth = d_h * 256 + d_l
    
    # 航向：高位在前，低位在后，得到 0~360，再减 360（若 >180），单位 °
    raw_hdg = hdg_h * 256 + hdg_l
    heading = raw_hdg
    if heading > 180:
        heading -= 360
    
    return {
        'battery_V': battery,
        'temperature_C': temperature,
        'humidity_pct': humidity,
        'depth_cm': depth,
        'heading_deg': heading
    }

def main():
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)
    buf = bytearray()
    print(f"Opened {SERIAL_PORT} @ {BAUD_RATE}bps")
    
    try:
        while True:
            # 读入串口所有可用字节
            data = ser.read( ser.in_waiting or 1 )
            if data:
                buf.extend(data)
            
            # 在缓冲区里找包头
            while True:
                idx = buf.find(b'\xAA')
                if idx < 0 or len(buf) - idx < FRAME_LEN:
                    # 没找到完整帧就跳出
                    break
                
                # 截取一帧
                frame = buf[idx: idx + FRAME_LEN]
                # 移除已处理部分
                del buf[: idx + FRAME_LEN]
                
                # 解析并打印
                info = parse_frame(frame)
                print(f"{time.strftime('%H:%M:%S')} | "
                      f"Volt: {info['battery_V']:.1f} V, "
                      f"Temp: {info['temperature_C']} °C, "
                      f"Hum: {info['humidity_pct']} %, "
                      f"Depth: {info['depth_cm']} cm, "
                      f"Hdg: {info['heading_deg']}°")
            
            # 为了不跑满 CPU
            time.sleep(0.01)
    except KeyboardInterrupt:
        print("Interrupted by user")
    finally:
        ser.close()

if __name__ == '__main__':
    main()
