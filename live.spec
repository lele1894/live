# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from PyInstaller.utils.hooks import collect_all

block_cipher = None

# 收集所有需要的数据和二进制文件
qt_data, qt_binaries, qt_hiddenimports = collect_all('PyQt6')
sd_data, sd_binaries, sd_hiddenimports = collect_all('sounddevice')
sc_data, sc_binaries, sc_hiddenimports = collect_all('soundcard')
cv_data, cv_binaries, cv_hiddenimports = collect_all('cv2')

# 获取PyQt6安装路径
import PyQt6
pyqt_path = os.path.join(os.path.dirname(PyQt6.__file__), 'Qt6', 'bin')

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[*qt_binaries, *sd_binaries, *sc_binaries, *cv_binaries],
    datas=[*qt_data, *sd_data, *sc_data, *cv_data],
    hiddenimports=[
        *qt_hiddenimports,
        *sd_hiddenimports,
        *sc_hiddenimports,
        *cv_hiddenimports,
        'sounddevice',
        'soundcard',
        'mss',
        'pydub',
        'psutil',
        'numpy',
        'cv2',
        'ffmpeg',
        'PyQt6',
        'PyQt6.QtWidgets',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.sip',
        'PyQt6.QtNetwork',
        'win32gui',
        'win32con',
        'win32api',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# 确保包含所有需要的DLL
a.binaries += [
    ('Qt6Core.dll', os.path.join(pyqt_path, 'Qt6Core.dll'), 'BINARY'),
    ('Qt6Gui.dll', os.path.join(pyqt_path, 'Qt6Gui.dll'), 'BINARY'),
    ('Qt6Widgets.dll', os.path.join(pyqt_path, 'Qt6Widgets.dll'), 'BINARY')
]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='live',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='app.ico',
    version='file_version_info.txt',
) 