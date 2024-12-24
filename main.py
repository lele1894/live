from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QLabel, QComboBox, QGroupBox, QHBoxLayout, QFileDialog, QLineEdit, QMessageBox, QSystemTrayIcon, QMenu, QDialog
from PyQt6.QtCore import Qt, QTimer, QRect, QPoint, QEvent
from PyQt6.QtGui import QImage, QPixmap, QPainter, QPen, QColor
import cv2
import sys
import sounddevice as sd
import numpy as np
from mss import mss
import queue
import threading
import os
from datetime import datetime
import wave
import time
import ffmpeg
import subprocess
import soundcard as sc
from pydub import AudioSegment
import io
import psutil

class SelectAreaDialog(QDialog):
    """框选区域对话框"""
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowState(Qt.WindowState.WindowFullScreen)
        
        # 捕获整个屏幕
        screen = QApplication.primaryScreen()
        self.screenshot = screen.grabWindow(0)
        
        # 设置半透明背景
        self.setStyleSheet("background-color: rgba(0, 0, 0, 50);")
        
        self.begin = QPoint()
        self.end = QPoint()
        self.is_drawing = False
        self.selected_rect = None
    
    def paintEvent(self, event):
        painter = QPainter(self)
        
        # 绘制屏幕截图
        painter.drawPixmap(0, 0, self.screenshot)
        
        # 添加半透明遮罩
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))
        
        if self.is_drawing or self.selected_rect:
            # 设置选择框的样式
            painter.setPen(QPen(QColor(255, 0, 0), 2))
            
            if self.is_drawing:
                rect = QRect(self.begin, self.end)
            else:
                rect = self.selected_rect
            
            # 清除选择区域的遮罩
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            painter.fillRect(rect, Qt.GlobalColor.transparent)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            
            # 绘制选择框
            painter.drawRect(rect)
            
            # 显示尺寸信息
            size_text = f"{rect.width()} x {rect.height()}"
            painter.setPen(QPen(QColor(255, 255, 255)))
            painter.drawText(rect.center(), size_text)
    
    def mousePressEvent(self, event):
        self.begin = event.pos()
        self.end = self.begin
        self.is_drawing = True
        self.selected_rect = None
        self.update()
    
    def mouseMoveEvent(self, event):
        if self.is_drawing:
            self.end = event.pos()
            self.update()
    
    def mouseReleaseEvent(self, event):
        self.is_drawing = False
        self.selected_rect = QRect(self.begin, self.end).normalized()
        self.update()
        # 延迟关闭，让用户看到最终的选择区域
        QTimer.singleShot(500, self.accept)

class StreamingApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("简易直播软件")
        self.setGeometry(100, 100, 1280, 720)  # 增大窗口尺寸
        
        # 建主窗口部件
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # 使用水平布局分割左右两部分
        main_layout = QHBoxLayout()
        
        # 左侧预览区域
        preview_layout = QVBoxLayout()
        
        # 预览窗口
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumSize(800, 450)  # 16:9 比例
        self.preview_label.setStyleSheet("QLabel { background-color: black; }")
        preview_layout.addWidget(self.preview_label, stretch=1)  # stretch=1 使其占据所有可用空间
        
        # 直播控制按钮
        stream_control_layout = QHBoxLayout()
        self.start_button = QPushButton("开始直播")
        self.start_button.setMinimumHeight(40)
        self.start_button.clicked.connect(self.toggle_streaming)
        stream_control_layout.addWidget(self.start_button)
        preview_layout.addLayout(stream_control_layout)
        
        # 将左侧布局添加到主布局
        main_layout.addLayout(preview_layout, stretch=2)  # 左侧占据2/3空间
        
        # 右侧控制面板
        control_panel = QWidget()
        control_layout = QVBoxLayout()
        control_panel.setMaximumWidth(400)  # 限制右侧控制面板宽度
        
        # 设备选择区域
        devices_group = QGroupBox("设备选择")
        devices_layout = QVBoxLayout()
        
        # 摄像头选择区域
        camera_layout = QHBoxLayout()
        camera_label = QLabel("视频设备:")
        self.camera_combo = QComboBox()
        # 获取可用的摄像头列表
        self.update_camera_list()
        camera_layout.addWidget(camera_label)
        camera_layout.addWidget(self.camera_combo)
        devices_layout.addLayout(camera_layout)
        
        # 音频输入设��选择
        audio_in_layout = QHBoxLayout()
        audio_in_label = QLabel("音频输入:")
        self.audio_in_combo = QComboBox()
        self.audio_in_combo.addItems(self.get_audio_devices())
        audio_in_layout.addWidget(audio_in_label)
        audio_in_layout.addWidget(self.audio_in_combo)
        devices_layout.addLayout(audio_in_layout)
        
        # 在设备选择区域添加背景音选择
        bgm_layout = QHBoxLayout()
        bgm_label = QLabel("背景音乐:")
        self.bgm_path = None
        self.bgm_label = QLabel("未选择")
        select_bgm_button = QPushButton("选择音乐")
        select_bgm_button.clicked.connect(self.select_bgm)
        bgm_layout.addWidget(bgm_label)
        bgm_layout.addWidget(self.bgm_label)
        bgm_layout.addWidget(select_bgm_button)
        devices_layout.addLayout(bgm_layout)
        
        # 修改窗口捕获选择
        window_layout = QHBoxLayout()
        window_label = QLabel("捕获选择:")
        self.window_combo = QComboBox()
        self.window_combo.addItems(["全屏", "框选区域"])  # 添加框选区域选项
        self.update_window_list()
        window_layout.addWidget(window_label)
        window_layout.addWidget(self.window_combo)
        devices_layout.addLayout(window_layout)
        
        # 刷新按���
        refresh_button = QPushButton("刷新设备列表")
        refresh_button.clicked.connect(self.refresh_devices)
        devices_layout.addWidget(refresh_button)
        
        devices_group.setLayout(devices_layout)
        control_layout.addWidget(devices_group)
        
        # 推流设置区域
        stream_group = QGroupBox("推流设置")
        stream_layout = QVBoxLayout()
        
        # 推流地址输入
        stream_url_layout = QHBoxLayout()
        stream_url_label = QLabel("推流地址:")
        self.stream_url_input = QLineEdit()
        self.stream_url_input.setPlaceholderText("rtmp://your-streaming-server/live/stream-key")
        stream_url_layout.addWidget(stream_url_label)
        stream_url_layout.addWidget(self.stream_url_input)
        stream_layout.addLayout(stream_url_layout)
        
        stream_group.setLayout(stream_layout)
        control_layout.addWidget(stream_group)
        
        # 录制控制区域
        recording_group = QGroupBox("录制控制")
        recording_layout = QVBoxLayout()
        
        # 保存路径选择
        save_path_layout = QHBoxLayout()
        self.save_path_label = QLabel("保存路径: 未选择")
        self.save_path = "D:/"  # 修改默认保存路径
        # 确保目录存在
        if not os.path.exists(self.save_path):
            os.makedirs(self.save_path)
        self.save_path_label.setText(f"保存路径: {self.save_path}")
        
        select_path_button = QPushButton("选择保存路径")
        select_path_button.clicked.connect(self.select_save_path)
        save_path_layout.addWidget(self.save_path_label)
        save_path_layout.addWidget(select_path_button)
        recording_layout.addLayout(save_path_layout)
        
        # 录制控制按钮
        record_control_layout = QHBoxLayout()
        self.record_button = QPushButton("开始录制")
        self.record_button.clicked.connect(self.toggle_recording)
        record_control_layout.addWidget(self.record_button)
        recording_layout.addLayout(record_control_layout)
        
        # 在录制控制区域添加录制时长显示
        self.recording_time_label = QLabel("录制时长: 00:00:00")
        recording_layout.addWidget(self.recording_time_label)
        
        # 添加录制状态指示
        status_layout = QHBoxLayout()
        self.recording_status_label = QLabel("未录制")
        status_layout.addWidget(self.recording_status_label)
        recording_layout.addLayout(status_layout)
        
        recording_group.setLayout(recording_layout)
        control_layout.addWidget(recording_group)
        
        # ��加所有组到右侧控制面板
        control_layout.addStretch()  # 添加弹性空间
        
        control_panel.setLayout(control_layout)
        main_layout.addWidget(control_panel)  # 右侧占据1/3空间
        
        main_widget.setLayout(main_layout)
        
        # 视频捕获
        self.capture = None
        self.streaming = False
        
        # 时器用于更新预览
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_preview)
        
        # 在类初始化中添加新的成员变量
        self.screen_capture = mss()
        self.audio_queue = queue.Queue()
        self.audio_thread = None
        self.recording_audio = False
        
        # 添加录制相关的成员变量
        self.recording = False
        self.video_writer = None
        self.recording_start_time = None
        
        # 添加录制时长更新定时器
        self.recording_timer = QTimer()
        self.recording_timer.timeout.connect(self.update_recording_time)
        
        # 添加音频录制相关变量
        self.audio_file = None
        self.audio_writer = None
        self.is_recording_audio = False
        
        # 添加推流相关变量
        self.ffmpeg_process = None
        self.stream_pipe = None
        
        # 添加系统托盘图标支���
        self.tray_icon = None
        
        # 添加性能监控
        self.performance_timer = QTimer()
        self.performance_timer.timeout.connect(self.monitor_performance)
        self.performance_timer.start(5000)  # 每5秒监控一次
        self.frame_count = 0
        self.last_frame_time = time.time()
        
    def toggle_streaming(self):
        if not self.streaming:
            self.start_streaming()
        else:
            self.stop_streaming()
    
    def start_streaming(self):
        """开始直播"""
        try:
            # 使用默认地址，不再检查是否为空
            stream_url = self.stream_url_input.text().strip() or "udp://127.0.0.1:1234"
            self.stream_url_input.setText(stream_url)  # 显示使用的地址
            
            selected_mode = self.window_combo.currentText()
            
            # 全屏模式
            if selected_mode == "全屏":
                screen = QApplication.primaryScreen()
                size = screen.size()
                self.capture_region = {
                    'left': 0,
                    'top': 0,
                    'width': size.width(),
                    'height': size.height()
                }
                self.streaming = True
                self.start_button.setText("停止直播")
                self.timer.start(16)  # 约60fps的更新频率，让系统自己调节到30fps
                self.start_ffmpeg_stream()
                return
            
            # 框选区域模式
            elif selected_mode == "框选区域":
                if self.select_area():
                    self.streaming = True
                    self.start_button.setText("停止直播")
                    self.timer.start(16)  # 约60fps的更新频率，让系统自己调节到30fps
                    self.start_ffmpeg_stream()
                return
            
            # 窗口捕获模式
            elif selected_mode not in ["无可用摄像头", "需要安装pywin32库"]:
                try:
                    import win32gui
                    hwnd = win32gui.FindWindow(None, selected_mode)
                    if hwnd:
                        rect = win32gui.GetWindowRect(hwnd)
                        self.capture_region = {
                            'left': rect[0],
                            'top': rect[1],
                            'width': rect[2] - rect[0],
                            'height': rect[3] - rect[1]
                        }
                        self.target_window = hwnd
                        self.streaming = True
                        self.start_button.setText("停止直播")
                        self.timer.start(16)  # 约60fps的更新频率，让系统自己调节到30fps
                        self.start_ffmpeg_stream()
                        return
                except ImportError:
                    print("未安装pywin32库，无法捕获窗口")
                except Exception as e:
                    print(f"窗口捕获出错: {str(e)}")
            
            # 摄像头模式
            camera_text = self.camera_combo.currentText()
            if camera_text != "无可用摄像头":
                try:
                    camera_index = int(camera_text.split(" ")[1])
                    self.capture = cv2.VideoCapture(camera_index)
                    if self.capture.isOpened():
                        self.streaming = True
                        self.start_button.setText("停止直播")
                        self.timer.start(16)  # 约60fps的更新频率，让系统自己调节到30fps
                        self.start_ffmpeg_stream()
                    else:
                        print("无法打开摄像头")
                        self.capture = None
                except Exception as e:
                    print(f"打开摄像头出错: {str(e)}")
                    if self.capture:
                        self.capture.release()
                        self.capture = None
            else:
                print("没有可用的摄像头，请选择其他捕获模式")
            
        except Exception as e:
            print(f"开始直播时出错: {str(e)}")
            self.stop_streaming()
    
    def start_ffmpeg_stream(self):
        """启动FFmpeg推流进程"""
        try:
            if hasattr(self, 'ffmpeg_process') and self.ffmpeg_process:
                self.ffmpeg_process.terminate()
                self.ffmpeg_process.wait()
                self.ffmpeg_process = None

            # 获取推流地址
            stream_url = self.stream_url_input.text().strip()
            if not stream_url:
                print("请输入完整的推流地址，包括推流密钥")
                return
            
            # 获取视频尺寸并调整为2的倍数
            if hasattr(self, 'capture_region'):
                width = self.capture_region['width']
                height = self.capture_region['height']
            elif self.capture and self.capture.isOpened():
                width = int(self.capture.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
            else:
                raise Exception("无法获取视频尺寸")
            
            # 确保宽高都是2的倍数
            width = width - (width % 2)
            height = height - (height % 2)
            
            command = [
                'ffmpeg',
                '-y',  # 覆盖输出文件
                '-f', 'rawvideo',
                '-vcodec', 'rawvideo',
                '-pix_fmt', 'bgr24',
                '-s', f'{width}x{height}',
                '-r', '30',
                '-i', '-',  # 从管道读取视频
            ]
            
            # 如果有背景音乐，添加背景音输入
            if self.bgm_path:
                command.extend([
                    '-stream_loop', '-1',  # 循环播放背景音
                    '-i', self.bgm_path,
                    '-af', 'aresample=async=1000',  # 加音频采样
                    '-c:a', 'aac',
                    '-ar', '44100',
                    '-b:a', '192k',
                    '-map', '0:v',  # 映射视频流
                    '-map', '1:a',  # 映射背景音乐
                ])
            
            # 添加B站直播特定的编码参数
            command.extend([
                '-c:v', 'libx264',
                '-preset', 'superfast',
                '-tune', 'zerolatency',
                '-profile:v', 'baseline',
                '-pix_fmt', 'yuv420p',
                '-b:v', '2000k',
                '-maxrate', '2500k',
                '-bufsize', '2500k',
                '-r', '30',  # 固定输出帧率
                '-g', '30',  # 关键帧间隔与帧率相同
                '-keyint_min', '30',  # 最小关键帧间隔也设为帧率
                '-sc_threshold', '0',
                '-thread_queue_size', '4096',
                '-max_muxing_queue_size', '2048',
                '-vsync', 'cfr',  # 使用固定帧率模式
                '-fps_mode', 'cfr',  # 强制固定帧率
                '-x264opts', 'no-scenecut:keyint=30:min-keyint=30',  # 确保固定GOP大小
                '-probesize', '32',
                '-analyzeduration', '0',
            ])
            
            # 添加出格式和地址
            command.extend([
                '-f', 'flv',  # B站使用FLV格式
                stream_url
            ])
            
            print("执行FFmpeg命令:", ' '.join(command))
            
            # 修改进程创建
            self.ffmpeg_process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=10**8,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            # 建错误输出监控线程
            def monitor_ffmpeg():
                while self.ffmpeg_process and self.ffmpeg_process.poll() is None:
                    error_line = self.ffmpeg_process.stderr.readline()
                    if error_line:
                        error_text = error_line.decode().strip()
                        if "Error" in error_text or "error" in error_text:
                            print("FFmpeg错误:", error_text)
                        elif "Warning" in error_text or "warning" in error_text:
                            print("FFmpeg警告:", error_text)
                        else:
                            print("FFmpeg:", error_text)  # 打印所有输出以便调试
                    time.sleep(0.1)

            self.ffmpeg_monitor = threading.Thread(target=monitor_ffmpeg)
            self.ffmpeg_monitor.daemon = True
            self.ffmpeg_monitor.start()

            print(f"推流已启动到: {stream_url}")
            print(f"推流分辨率: {width}x{height}")
            
        except Exception as e:
            print(f"启动推流时出错: {str(e)}")
            if hasattr(self, 'ffmpeg_process') and self.ffmpeg_process:
                self.ffmpeg_process.terminate()
                self.ffmpeg_process = None
    
    def stop_streaming(self):
        """停止直播但不影响录制"""
        # 停止推流
        if self.ffmpeg_process:
            self.ffmpeg_process.stdin.close()
            self.ffmpeg_process.terminate()
            self.ffmpeg_process.wait()
            self.ffmpeg_process = None
        
        self.streaming = False
        self.start_button.setText("开始直播")
        
        # 如果没有在录制则停止预览和释放资源
        if not self.recording:
            self.timer.stop()
            if hasattr(self, 'capture_region'):
                delattr(self, 'capture_region')
            if self.capture:
                self.capture.release()
            self.preview_label.clear()
            if not self.recording:
                self.stop_audio()
    
    def update_preview(self):
        """更新预览、推流和录制"""
        try:
            # 精确的帧率控制
            current_time = time.time()
            if hasattr(self, '_last_update'):
                target_interval = 1.0 / 30  # 目标帧间隔（30fps）
                elapsed = current_time - self._last_update
                if elapsed < target_interval:
                    return  # 直接返回，不使用sleep
            self._last_update = current_time

            frame_obtained = False
            try:
                if hasattr(self, 'capture_region'):
                    # 使用numpy优化图像处理
                    with mss() as sct:
                        # 直接获取BGR格式的图像
                        screenshot = np.array(sct.grab(self.capture_region))
                        
                        # 如果分辨率太大，先缩放再处理
                        if screenshot.shape[0] > 1080 or screenshot.shape[1] > 1920:
                            scale = min(1920/screenshot.shape[1], 1080/screenshot.shape[0])
                            new_size = (int(screenshot.shape[1] * scale), int(screenshot.shape[0] * scale))
                            screenshot = cv2.resize(screenshot, new_size, interpolation=cv2.INTER_AREA)
                        
                        # 确保尺寸是2的倍数
                        h, w = screenshot.shape[:2]
                        w = w - (w % 2)
                        h = h - (h % 2)
                        if w != screenshot.shape[1] or h != screenshot.shape[0]:
                            screenshot = screenshot[:h, :w]
                        
                        # BGR转换
                        frame = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2BGR)
                        record_frame = frame.copy()  # 推流用的��
                        preview_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  # 预览用的帧
                        frame_obtained = True
                        self.frame_count += 1

                    # 推流时使用较小的缓冲区
                    if self.streaming and self.ffmpeg_process:
                        if self.ffmpeg_process.poll() is not None:
                            print("FFmpeg进程已退出")
                            error_output = self.ffmpeg_process.stderr.read().decode()
                            print("FFmpeg错误输出:", error_output)
                            self.stop_streaming()
                            return
                        try:
                            # 直接写入整个帧数据
                            self.ffmpeg_process.stdin.write(record_frame.tobytes())
                            self.ffmpeg_process.stdin.flush()
                        except Exception as e:
                            print(f"推流时出错: {str(e)}")
                            self.stop_streaming()
                            return

                    # 更新预览（使用QImage的快速路径）
                    if frame_obtained:
                        h, w = preview_frame.shape[:2]
                        bytes_per_line = 3 * w
                        image = QImage(preview_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
                        scaled_pixmap = QPixmap.fromImage(image).scaled(
                            self.preview_label.size(), 
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.FastTransformation  # 使用快速转换
                        )
                        self.preview_label.setPixmap(scaled_pixmap)

            except Exception as e:
                print(f"更新预览时出错: {str(e)}")
                import traceback
                traceback.print_exc()

        except Exception as e:
            print(f"预览更新主循环出错: {str(e)}")
    
    def get_audio_devices(self):
        """获取系统音频设备列表"""
        try:
            devices = sd.query_devices()
            input_devices = ["静音"]  # 添加静音选项
            for i, device in enumerate(devices):
                if device['max_input_channels'] > 0:
                    input_devices.append(f"{i}: {device['name']}")
                    print(f"找到音频设备: {i}: {device['name']} (输入通道: {device['max_input_channels']})")
            return input_devices
        except Exception as e:
            print(f"获取音频设备列表出错: {str(e)}")
            return ["静音"]
    
    def update_window_list(self):
        """更新可捕获窗口列表"""
        try:
            import win32gui
            def callback(hwnd, windows):
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    if title:
                        windows.append(title)
            windows = ["全屏", "框选区域"]  # 确保这两个选项始终存在
            win32gui.EnumWindows(callback, windows)
            self.window_combo.clear()
            self.window_combo.addItems(windows)
        except ImportError:
            self.window_combo.addItems(["全屏", "框选区域", "需要安装pywin32库"])
    
    def refresh_devices(self):
        """刷新所有设备列表"""
        # 更新摄像头列表
        current_camera = self.camera_combo.currentText()
        self.update_camera_list()
        if current_camera in [self.camera_combo.itemText(i) for i in range(self.camera_combo.count())]:
            self.camera_combo.setCurrentText(current_camera)
            
        # 更新音频设备列表
        current_audio = self.audio_in_combo.currentText()
        self.audio_in_combo.clear()
        self.audio_in_combo.addItems(self.get_audio_devices())
        if current_audio in [self.audio_in_combo.itemText(i) for i in range(self.audio_in_combo.count())]:
            self.audio_in_combo.setCurrentText(current_audio)
            
        # 更新窗口列表
        self.update_window_list()
    
    def audio_callback(self, indata, frames, time, status):
        """音频回调函数"""
        if status:
            print(f"音频回调状态: {status}")
        if self.recording and self.is_recording_audio:
            try:
                # 将数据转换为16位整数并调整音量
                audio_data = (indata * 32767 * 1.5).clip(-32768, 32767).astype(np.int16)
                self.audio_queue.put(audio_data)
            except Exception as e:
                print(f"音频回调处理出错: {str(e)}")
    
    def start_audio(self):
        """开始录制系统声音"""
        try:
            if self.audio_in_combo.currentText() == "静音":
                print("已选择静音模式")
                # 设置默认的音频参数
                self.audio_samplerate = 44100
                self.audio_channels = 2
                self.recording_audio = True
                self.is_recording_audio = True
                return
            
            # 尝试查找立体声混音设备
            devices = sd.query_devices()
            selected_device = None
            
            # 从当前选择的设备文本中获取设备ID
            device_text = self.audio_in_combo.currentText()
            if ':' in device_text:
                selected_device = int(device_text.split(':')[0])
            else:
                # 查找立体声混音设备
                for i, device in enumerate(devices):
                    device_name = device['name'].lower()
                    if ('mix' in device_name or 
                        'stereo' in device_name or 
                        '立体声混音' in device_name or 
                        'what u hear' in device_name or
                        'loopback' in device_name):
                        selected_device = i
                        break
            
            if selected_device is None:
                print("未找到立体声混音设备，请在系统声音设置中启用它")
                print("Windows系统启用方法：")
                print("1. 右键点击系统托盘音图标")
                print('2. 选择"声音设置"')
                print('3. 点击"声音控制面板"')
                print('4. 在"录制"标签页')
                print('5. 右键空白处，选择"显示禁用的设备"')
                print('6. 找到"立体声混音"，右键启用它')
                return
            
            # 获取设备信息
            device_info = devices[selected_device]
            print(f"使用音频设备: {device_info['name']}")
            
            # 配置音频参数
            self.audio_samplerate = int(device_info['default_samplerate'])
            self.audio_channels = min(2, device_info['max_input_channels'])
            
            # 开录制
            self.recording_audio = True
            self.is_recording_audio = True
            
            # 启动录音流
            self.audio_stream = sd.InputStream(
                device=selected_device,
                channels=self.audio_channels,
                samplerate=self.audio_samplerate,
                callback=self.audio_callback,
                blocksize=1024,
                dtype=np.float32
            )
            self.audio_stream.start()
            
            print(f"系统声音录制已启动: {self.audio_channels}通道, {self.audio_samplerate}Hz")
            
        except Exception as e:
            print(f"音频录制出错: {str(e)}")
            self.recording_audio = False
    
    def stop_audio(self):
        """停止录制音频"""
        self.recording_audio = False
        self.is_recording_audio = False
        if hasattr(self, 'audio_stream'):
            self.audio_stream.stop()
            self.audio_stream.close()
    
    def select_save_path(self):
        """选择录制文件保存路径"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "选择保存路径",
            self.save_path,
            QFileDialog.Option.ShowDirsOnly
        )
        if folder:
            self.save_path = folder
            self.save_path_label.setText(f"保存路径: {self.save_path}")
    
    def toggle_recording(self):
        """切换��制状态"""
        if not self.recording:
            self.start_recording()
        else:
            self.stop_recording()
    
    def start_recording(self):
        """开始录制"""
        try:
            if not self.streaming and not self.capture and not hasattr(self, 'capture_region'):
                selected_mode = self.window_combo.currentText()
                
                if selected_mode == "全屏":
                    # 获取主屏幕分辨率
                    screen = QApplication.primaryScreen()
                    size = screen.size()
                    self.capture_region = {
                        'left': 0,
                        'top': 0,
                        'width': size.width(),
                        'height': size.height()
                    }
                    self.timer.start(int(1000/30))  # 精确的30fps定时器间隔
                
                elif selected_mode == "框选区域":
                    if not self.select_area():
                        return
                    self.timer.start(int(1000/30))  # 精确的30fps定时器间隔
                
                elif selected_mode != "需要安装pywin32库":
                    try:
                        import win32gui
                        window_title = selected_mode
                        hwnd = win32gui.FindWindow(None, window_title)
                        if hwnd:
                            # 获取窗口位置，包括最小化的窗口
                            if win32gui.IsIconic(hwnd):  # 如果窗口是最小化的
                                win32gui.ShowWindow(hwnd, 9)  # SW_RESTORE = 9
                            rect = win32gui.GetWindowRect(hwnd)
                            self.capture_region = {
                                'left': rect[0],
                                'top': rect[1],
                                'width': rect[2] - rect[0],
                                'height': rect[3] - rect[1]
                            }
                            self.target_window = hwnd  # 保存目标窗口句柄
                            self.timer.start(int(1000/30))  # 精确的30fps定时器间隔
                    except ImportError:
                        pass
                else:
                    self.capture = cv2.VideoCapture(self.camera_combo.currentIndex())
                    if not self.capture.isOpened():
                        raise Exception("无法打开摄像头")
                    self.timer.start(int(1000/30))  # 精确的30fps定时器间隔
            
            # 确保音频设备已经启动
            if not self.recording_audio:
                self.start_audio()
            
            # 确保音频参数已设置
            if not hasattr(self, 'audio_channels'):
                self.audio_channels = 2
            if not hasattr(self, 'audio_samplerate'):
                self.audio_samplerate = 44100
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # 保存文件路径作为成员变量
            self.video_filename = os.path.join(self.save_path, f"recording_{timestamp}.mp4")
            self.audio_filename = os.path.join(self.save_path, f"recording_{timestamp}.wav")
            
            # 获取视频尺寸
            if hasattr(self, 'capture_region'):
                width = self.capture_region['width']
                height = self.capture_region['height']
            else:
                width = int(self.capture.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            # 创建视频写入器
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            self.video_writer = cv2.VideoWriter(
                self.video_filename,
                fourcc,
                30.0,
                (width, height)
            )
            
            if not self.video_writer.isOpened():
                raise Exception("无法创建视频文件")
            
            # 创建音频写入器
            self.audio_file = wave.open(self.audio_filename, 'wb')
            self.audio_file.setnchannels(self.audio_channels)  # 使用设备实际通道数
            self.audio_file.setsampwidth(2)  # 16位采样
            self.audio_file.setframerate(self.audio_samplerate)  # 使用设备的实际采样率
            
            # 开始录制
            self.recording = True
            self.is_recording_audio = True
            self.recording_start_time = datetime.now()
            self.recording_timer.start(1000)  # 每秒更新一次时间显示
            
            # 更新UI
            self.record_button.setText("停止录制")
            self.recording_status_label.setText("🔴 正在录制")
            
            # 启动音频录制线程
            self.audio_thread = threading.Thread(target=self.record_audio)
            self.audio_thread.start()
            
            print(f"开始录制到: {self.video_filename}")
            
            # 如果有背景音乐，创建混音器
            if self.bgm_path:
                self.setup_audio_mixing()
            
        except Exception as e:
            print(f"开始录制时出错: {str(e)}")
            self.stop_recording()
    
    def record_audio(self):
        """音频录制线程"""
        while self.is_recording_audio and self.audio_file:
            try:
                if not self.audio_queue.empty():
                    audio_data = self.audio_queue.get()
                    if audio_data is not None and len(audio_data) > 0:
                        self.audio_file.writeframes(audio_data.tobytes())
            except Exception as e:
                print(f"音频录制出错: {str(e)}")
                break
            time.sleep(0.001)
    
    def stop_recording(self):
        """停止录制但不影响直播"""
        try:
            # 停止视频录制
            if self.video_writer:
                self.video_writer.release()
                self.video_writer = None
            
            # 停止音频录制
            self.is_recording_audio = False
            if self.audio_thread:
                self.audio_thread.join()
            if self.audio_file:
                self.audio_file.close()
                self.audio_file = None
            
            # 合并音视频
            if hasattr(self, 'video_filename') and hasattr(self, 'audio_filename'):
                try:
                    output_path = os.path.splitext(self.video_filename)[0] + '_merged.mp4'
                    
                    # 使用ffmpeg合并音视频
                    stream = ffmpeg.input(self.video_filename)
                    audio = ffmpeg.input(self.audio_filename)
                    stream = ffmpeg.output(stream, audio, output_path, vcodec='copy', acodec='aac')
                    ffmpeg.run(stream, overwrite_output=True)
                    
                    # 删除原始文件
                    os.remove(self.video_filename)
                    os.remove(self.audio_filename)
                    
                    # 清理文件路径
                    delattr(self, 'video_filename')
                    delattr(self, 'audio_filename')
                    
                    print(f"音视频合并完成: {output_path}")
                    
                except Exception as e:
                    print(f"合并音视频时出错: {str(e)}")
            
            # 停止定时器
            self.recording_timer.stop()
            
            # 重置状态
            self.recording = False
            self.recording_start_time = None
            
            # 更新UI
            self.record_button.setText("开始录制")
            self.recording_status_label.setText("⚪ 未录制")
            self.recording_time_label.setText("录制时长: 00:00:00")
            
            # 果没有在直播，则停止预览和释放资源
            if not self.streaming:
                self.timer.stop()
                if hasattr(self, 'capture_region'):
                    delattr(self, 'capture_region')
                if self.capture:
                    self.capture.release()
                self.preview_label.clear()
                self.stop_audio()
                
        except Exception as e:
            print(f"停止录制时出错: {str(e)}")
        finally:
            # 重置状态
            self.recording = False
            self.recording_start_time = None
            self.recording_timer.stop()
            
            # 更新UI
            self.record_button.setText("开始录制")
            self.recording_status_label.setText("⚪ 未录制")
            self.recording_time_label.setText("录制时长: 00:00:00")
    
    def update_recording_time(self):
        """更新录制时长显示"""
        if self.recording and self.recording_start_time:
            elapsed = datetime.now() - self.recording_start_time
            hours = elapsed.seconds // 3600
            minutes = (elapsed.seconds % 3600) // 60
            seconds = elapsed.seconds % 60
            self.recording_time_label.setText(
                f"录制时长: {hours:02d}:{minutes:02d}:{seconds:02d}"
            )
    
    def closeEvent(self, event):
        """窗口关闭事件处理"""
        if self.recording or self.streaming:
            reply = QMessageBox.question(
                self, 
                '确认退出', 
                "录制或直播正在进行中，是否最小化到系统托盘继续运行？",
                QMessageBox.StandardButton.Yes | 
                QMessageBox.StandardButton.No | 
                QMessageBox.StandardButton.Cancel
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                event.ignore()
                self.hide()
                self.create_tray_icon()
            elif reply == QMessageBox.StandardButton.No:
                self.cleanup_resources()
                event.accept()
            else:
                event.ignore()
        else:
            self.cleanup_resources()
            event.accept()
    
    def changeEvent(self, event):
        """窗口状态改变事件处理"""
        if event.type() == QEvent.Type.WindowStateChange:
            if self.windowState() & Qt.WindowState.WindowMinimized:
                if self.recording or self.streaming:
                    # 最小化时自动隐藏到系统托盘
                    self.hide()
                    if not self.tray_icon:
                        self.create_tray_icon()
                    if self.tray_icon and not hasattr(self, 'minimize_notice_shown'):
                        self.tray_icon.showMessage(
                            "程序已最小化",
                            "程序将在后台继续运行，双击托盘图标可以恢复窗口",
                            QSystemTrayIcon.MessageIcon.Information,
                            2000
                        )
                        self.minimize_notice_shown = True
    
    def create_tray_icon(self):
        """创建系统托盘图标"""
        if not self.tray_icon:
            from PyQt6.QtWidgets import QStyle
            self.tray_icon = QSystemTrayIcon(self)
            self.tray_icon.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))
            
            # 创建托盘菜单
            tray_menu = QMenu()
            
            # 显示主窗口动作
            show_action = tray_menu.addAction("显示主窗口")
            show_action.triggered.connect(self.show)
            
            # 停止录制动作
            stop_record_action = tray_menu.addAction("停止录制")
            stop_record_action.triggered.connect(self.stop_recording)
            
            # 退出动作
            quit_action = tray_menu.addAction("退出")
            quit_action.triggered.connect(self.force_quit)
            
            self.tray_icon.setContextMenu(tray_menu)
            self.tray_icon.show()
            
            # 添加托盘图标双击事件
            self.tray_icon.activated.connect(self.tray_icon_activated)
    
    def tray_icon_activated(self, reason):
        """托盘图标激活事件处理"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show()
    
    def force_quit(self):
        """强制退出程序"""
        if self.recording:
            self.stop_recording()
        QApplication.quit()
    
    def select_bgm(self):
        """选择背景音乐"""
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "选择背景音乐",
            "",
            "音频文件 (*.mp3 *.wav *.m4a)"
        )
        if file_name:
            self.bgm_path = file_name
            self.bgm_label.setText(os.path.basename(file_name))
    
    def select_area(self):
        """选择制区域"""
        dialog = SelectAreaDialog()
        if dialog.exec() == QDialog.DialogCode.Accepted:
            rect = dialog.selected_rect
            if rect:
                self.capture_region = {
                    'left': rect.x(),
                    'top': rect.y(),
                    'width': rect.width(),
                    'height': rect.height()
                }
                return True
        return False
    
    def setup_audio_mixing(self):
        """设置音频混音"""
        try:
            # 读取音频文件（支持MP3和WAV）
            audio = AudioSegment.from_file(self.bgm_path)
            
            # 调整音量（可以根据需要调整）
            audio = audio + 10  # 增加10dB
            
            # 转换为WAV格式
            wav_data = io.BytesIO()
            audio.export(wav_data, format='wav')
            wav_data.seek(0)
            
            # 打开音频文件
            self.bgm_data = wave.open(wav_data, 'rb')
            self.bgm_position = 0
            
            # 调整样率和通道数以匹配录制设置
            if hasattr(self, 'audio_samplerate'):
                target_samplerate = self.audio_samplerate
            else:
                target_samplerate = 44100
            
            if self.bgm_data.getframerate() != target_samplerate:
                print(f"警告：背景音乐采样率({self.bgm_data.getframerate()})与录制采样率({target_samplerate})不匹配")
            
            print("背景音乐已加载")
            
            # 启动背景音乐处理线程
            self.bgm_thread = threading.Thread(target=self.process_bgm)
            self.bgm_thread.daemon = True
            self.bgm_thread.start()
            
        except Exception as e:
            print(f"设置背景音乐出错: {str(e)}")
            self.bgm_path = None
            self.bgm_label.setText("加载失败")
    
    def process_bgm(self):
        """处理背景音乐"""
        try:
            while self.recording and hasattr(self, 'bgm_data'):
                # 读取背景音乐数据
                frames = 1024  # 调整缓冲区大小
                bgm_frames = self.bgm_data.readframes(frames)
                
                if not bgm_frames:
                    # 循环播放
                    self.bgm_data.rewind()
                    bgm_frames = self.bgm_data.readframes(frames)
                
                # 将字节数据转换为numpy组
                bgm_data = np.frombuffer(bgm_frames, dtype=np.int16)
                
                # 确保音频通道数匹配
                if bgm_data.size > 0:  # 确保有数据
                    if self.bgm_data.getnchannels() == 1:  # 单声道转立体声
                        bgm_data = np.repeat(bgm_data, 2)
                    bgm_data = bgm_data.reshape(-1, 2)  # 制使用2通道
                
                # 如果是静音模式，直接使用背景音乐
                if self.audio_in_combo.currentText() == "静音":
                    self.audio_queue.put(bgm_data)
                else:
                    # 等待系统音频数
                    if not self.audio_queue.empty():
                        system_audio = self.audio_queue.get()
                        # 确保两个音频的形状匹配
                        if system_audio.shape[0] != bgm_data.shape[0]:
                            # 调整背景音乐长度以匹配系统音频
                            if system_audio.shape[0] > bgm_data.shape[0]:
                                bgm_data = np.pad(bgm_data, ((0, system_audio.shape[0] - bgm_data.shape[0]), (0, 0)))
                            else:
                                bgm_data = bgm_data[:system_audio.shape[0]]
                        # 合音频（调整混合比例）
                        mixed_data = (system_audio * 0.7 + bgm_data * 0.3).clip(-32768, 32767).astype(np.int16)
                        self.audio_queue.put(mixed_data)
                
                time.sleep(0.001)
                
        except Exception as e:
            print(f"背景音乐处理出错: {str(e)}")
            print(f"错误详情: {str(e.__traceback__)}")
    
    def update_camera_list(self):
        """更新摄像头列表"""
        available_cameras = []
        # 检查可用的摄像头
        for i in range(10):  # 检查前10个索引
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                # 读取一帧测试是否可用
                ret, _ = cap.read()
                if ret:
                    available_cameras.append(f"摄像头 {i}")
                cap.release()
        
        if not available_cameras:
            available_cameras = ["无可用摄像头"]
        
        self.camera_combo.clear()
        self.camera_combo.addItems(available_cameras)

    def cleanup_resources(self):
        """清理所有资源"""
        try:
            # 停止定时器
            self.timer.stop()
            
            # 停止推流
            if hasattr(self, 'ffmpeg_process') and self.ffmpeg_process:
                self.ffmpeg_process.terminate()
                self.ffmpeg_process.wait()
                self.ffmpeg_process = None
            
            # 停止录制
            if self.recording:
                self.stop_recording()
            
            # 释放摄像头
            if self.capture:
                self.capture.release()
            
            # 停止音频
            self.stop_audio()
            
        except Exception as e:
            print(f"清理资源时出错: {str(e)}")

    def monitor_performance(self):
        """监控推流性能"""
        try:
            current_time = time.time()
            elapsed = current_time - self.last_frame_time
            fps = self.frame_count / elapsed if elapsed > 0 else 0
            
            if self.streaming:
                print(f"当前帧率: {fps:.1f} FPS")
                if abs(fps - 30) > 2:  # 如果帧率偏离30fps超过2帧
                    print(f"警告: 帧率不稳定 ({fps:.1f} FPS)")
                    # 提供优化建议
                    if fps < 25:
                        print("性能优化建议:")
                        print("1. 降低捕获区域分辨率")
                        print("2. 关闭不必要的后台程序")
                        print("3. 检查CPU使用率和温度")
                
                # 检查系统资源
                if hasattr(self, 'ffmpeg_process'):
                    process = psutil.Process(self.ffmpeg_process.pid)
                    cpu_percent = process.cpu_percent()
                    memory_percent = process.memory_percent()
                    
                    # 获取系统总体CPU使用率
                    system_cpu = psutil.cpu_percent()
                    print(f"系统CPU使用率: {system_cpu:.1f}%")
                    print(f"FFmpeg CPU使用率: {cpu_percent:.1f}%, 内存使用率: {memory_percent:.1f}%")
                    
                    # 检查CPU是否过载
                    if system_cpu > 80:
                        print("警告: 系统CPU使用率过高")
                    
                    # 检查帧率稳定性
                    if hasattr(self, '_frame_times'):
                        frame_times = getattr(self, '_frame_times')
                        if len(frame_times) > 30:
                            frame_times.pop(0)
                        frame_times.append(current_time)
                        
                        if len(frame_times) > 1:
                            intervals = np.diff(frame_times)
                            jitter = np.std(intervals) * 1000
                            print(f"帧间隔抖动: {jitter:.2f}ms")
                            
                            if jitter > 20:
                                print("警告: 帧率不稳定，建议检查系统性能")
                    else:
                        self._frame_times = []
            
            self.frame_count = 0
            self.last_frame_time = current_time
            
        except Exception as e:
            print(f"性能监控出错: {str(e)}")

    def merge_audio_video(self, video_file, audio_file, output_file):
        """合并音频和视频文件"""
        try:
            # 使用正确的流映射
            command = [
                'ffmpeg',
                '-i', video_file,  # 视频输入
                '-i', audio_file,  # 音频输入
                '-c:v', 'copy',    # 复制视频流
                '-c:a', 'aac',     # 将音频转换为 AAC 格式
                '-map', '0:v:0',   # 从第一个输入取视频流
                '-map', '1:a:0',   # 从第二个输入取音频流
                '-shortest',       # 使用最短的流长度
                output_file
            ]
            
            # 执行命令
            result = subprocess.run(
                command,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                print("FFmpeg错误输出:", result.stderr)
                raise Exception("FFmpeg命令执行失败")
            
            print("音视频合并完成")
            
        except Exception as e:
            print(f"合并音视频时出错: {str(e)}")
            if os.path.exists(output_file):
                try:
                    os.remove(output_file)
                except:
                    pass
            raise

# 在程序开始时添加资源路径检查
def check_ffmpeg():
    """检查FFmpeg是否可用"""
    try:
        ffmpeg_path = os.path.join(os.path.dirname(sys.executable), 'ffmpeg.exe')
        if not os.path.exists(ffmpeg_path):
            ffmpeg_path = 'ffmpeg'  # 尝试使用系统PATH中的ffmpeg
        
        result = subprocess.run([ffmpeg_path, '-version'], 
                              capture_output=True, 
                              text=True)
        if result.returncode == 0:
            return True
        return False
    except Exception:
        return False

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # 检查FFmpeg
    if not check_ffmpeg():
        QMessageBox.critical(None, 
                           "错误", 
                           "未找到FFmpeg，请确保ffmpeg.exe在程序目录下或已添加到系统PATH中")
        sys.exit(1)
    
    window = StreamingApp()
    window.show()
    sys.exit(app.exec()) 