# 简易直播软件

一个基于 Python 的直播和录制软件，支持屏幕捕获、摄像头、系统声音和背景音乐。

## 功能特点

- 视频捕获
  - 全屏捕获
  - 框选区域捕获
  - 摄像头捕获
- 音频处理
  - 系统声音捕获
  - 背景音乐支持
  - 音频混音
- 直播功能
  - RTMP推流（支持B站等平台）
  - UDP推流
  - 自定义推流地址
- 录制功能
  - 视频录制
  - 音频录制
  - 自定义保存路径
- 其他功能
  - 系统托盘支持
  - 性能监控
  - 帧率控制

## 使用前准备

1. 下载最新版本的 [FFmpeg](https://ffmpeg.org/download.html)
2. 选择以下任一方式配置 FFmpeg：
   - 将 FFmpeg 添加到系统环境变量
   - 将 FFmpeg 文件放在程序同目录

## 快速开始

1. 下载最新版本的程序
2. 准备 FFmpeg（见上文）
3. 运行程序，选择捕获模式和音频设置
4. 开始直播或录制

## 使用说明

### 直播设置

1. 选择视频输入
   - 全屏：捕获整个屏幕
   - 框选区域：手动选择区域
   - 摄像头：使用摄像头输入

2. 配置音频
   - 选择音频输入设备
   - 可选：添加背景音乐
   - 调整音量混合比例

3. 设置推流
   - 输入推流地址（RTMP/UDP）
   - 点击"开始直播"

### 录制设置

1. 选择保存路径
2. 设置录制选项
3. 点击"开始录制"

## 系统要求

- Windows 7/8/10/11
- Python 3.7-3.9
- FFmpeg 4.x
- 2GB+ RAM
- DirectX 9 及以上显卡

## 开发指南

### 环境设置

```bash
# 安装 Python 3.7-3.9
# 推荐使用 Python 3.7.9: https://www.python.org/downloads/release/python-379/

# 克隆仓库
git clone https://github.com/your-username/live.git
cd live

# 安装依赖
python -m pip install --upgrade pip
pip install -r requirements.txt

# 运行程序
python main.py
```

### 兼容性说明

- Windows 7 用户请使用 Python 3.7.9
- 如遇到 DLL 缺失，请安装 Visual C++ Redistributable 2015-2019
- 部分功能在 Windows 7 上可能需要额外配置

## 常见问题

1. FFmpeg 相关
   - 确保 FFmpeg 正确安装
   - 检查版本兼容性
   - 验证文件完整性

2. 音频问题
   - 检查音频设备设置
   - 确认系统混音器开启
   - 验证音频权限

3. 性能问题
   - 降低捕获分辨率
   - 减小帧率
   - 关闭不必要的后台程序

## 更新日志

### v1.0.0
- 初始版本发布
- 基本功能实现
- 性能优化

## 贡献指南

1. Fork 本仓库
2. 创建功能分支
3. 提交更改
4. 发起 Pull Request

## 许可证

MIT License

## 联系方式

- 提交 Issue
- 发起 Pull Request
