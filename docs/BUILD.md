# 构建与打包

## 环境要求

- Windows 10/11
- Python 3.10 或更高版本
- 已安装 PyInstaller

安装构建依赖：

```powershell
pip install -r requirements-build.txt
```

## 一键构建

使用 Python 脚本：

```powershell
python scripts/build_exe.py
```

或者使用 PowerShell 脚本：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build_exe.ps1
```

构建完成后：

- `dist/GomokuAI_CLI.exe`：命令行版，带控制台窗口，可以打印 AI 运算过程。
- `dist/GomokuAI_GUI.exe`：图形界面版，无额外控制台窗口。

## 手动构建

命令行版：

```powershell
pyinstaller --onefile --console --name GomokuAI_CLI gomoku_cli.py
```

图形界面版：

```powershell
pyinstaller --onefile --noconsole --name GomokuAI_GUI gomoku_gui.py
```

## 常见问题

### 杀毒软件误报

PyInstaller 单文件 EXE 有时会被杀毒软件误报。可以将 `build` 和 `dist` 加入信任区，或使用 `--onedir` 模式。

### 中文显示乱码

CLI 已经强制使用 UTF-8 输出。若旧版控制台仍显示乱码，可在启动前执行：

```powershell
chcp 65001
```

### 想生成 32 位 EXE

需要在 32 位 Python 环境中重新运行构建脚本。
