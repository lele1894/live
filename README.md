# 简易直播软件

一个简单的直播和录制软件，支持屏幕捕获、摄像头、系统声音和背景音乐。

## 功能特点

- 支持全屏、窗口和区域捕获
- 支持摄像头输入
- 支持系统声音捕获
- 支持背景音乐
- 支持录制和直播
- 支持B站直播推流
- 支持最小化到系统托盘

## 使用前准备

1. 下载并安装 [FFmpeg](https://ffmpeg.org/download.html)
2. 将 FFmpeg 添加到系统环境变量，或将以下文件放在程序同目录：
   - ffmpeg.exe
   - ffplay.exe
   - ffprobe.exe

## 使用说明

1. 视频输入
   - 全屏：捕获整个屏幕
   - 框选区域：手动选择捕获区域
   - 窗口：选择要捕获的窗口

2. 音频输入
   - 系统声音：捕获系统声音
   - 静音：不捕获系统声音
   - 背景音乐：可选择音乐文件作为背景音

3. 直播设置
   - 输入推流地址（支持 RTMP、UDP 等）
   - 点击"开始直播"按钮

4. 录制设置
   - 选择保存路径
   - 点击"开始录制"按钮

## 系统要求

- Windows 10 或更高版本
- FFmpeg
- 2GB 以上内存
- 支持 DirectX 的显卡

## 常见问题

1. 找不到 FFmpeg
   - 确保 FFmpeg 已正确安装
   - 检查环境变量设置
   - 或将 FFmpeg 文件放在程序同目录

2. 无法捕获系统声音
   - 启用立体声混音设备
   - Windows 设置 -> 声音 -> 声音控制面板 -> 录制 -> 显示禁用设备 -> 启用立体声混音

3. 直播卡顿
   - 降低分辨率
   - 检查网络连接
   - 关闭不必要的后台程序

## 开发环境

- Python 3.9
- PyQt6
- OpenCV
- FFmpeg

## 依赖安装

```bash
pip install -r requirements.txt
```

## 构建说明

```bash
# 安装 pyinstaller
pip install pyinstaller

# 打包程序
pyinstaller --clean live.spec
```

## 许可证

MIT License

## 更新日志

### v1.0.0
- 初始版本发布
- 基本功能实现

## 贡献指南

1. Fork 本仓库
2. 创建新分支
3. 提交更改
4. 发起 Pull Request

## 联系方式

- 提交 Issue
- 发起 Pull Request
