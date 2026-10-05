# 五子棋 AI（Gomoku AI）

一个面向 Windows 的 19×19（可切换 15/17/19）五子棋程序，包含：

- 图形界面（Tkinter）
- 命令行界面，可打印每一步 AI 的运算过程
- 低 / 中 / 高 三档棋力
- 可打包为独立的 `.exe` 文件
- 可直接上传 GitHub 的文档与工程文件

## 主要特性

- **棋盘更大**：默认 19×19，GUI 和 CLI 均可切换 15×15、17×17、19×19。
- **更强的搜索**：迭代加深 + Alpha-Beta 剪枝 + Zobrist 置换表 + 候选点剪枝。
- **更快的响应**：中档默认每步约 0.8 秒；低档更快，适合快速对局；高档约 2 秒，棋力更强。
- **清楚的运算过程**：CLI 会打印深度、节点数、耗时、评分和主变（PV）。
- **三档棋力**：低、中、高三档，GUI 可直接选择，CLI 使用 `--level` 选择。
- **完整的 GitHub 文档**：README、算法说明、构建说明、贡献指南、安全策略等。

## 快速开始

### 运行图形界面

```powershell
cd 项目目录
python ai五子棋.py
```

也可以用 ASCII 入口：

```powershell
python gomoku_gui.py
```

### 运行命令行版本

人执黑先手，电脑执白：

```powershell
python gomoku_cli.py
```

电脑执黑先手：

```powershell
python gomoku_cli.py --mode ai-human
```

AI 对战 AI，并打印运算过程：

```powershell
python gomoku_cli.py --mode ai-ai --verbose
```

选择三档棋力：

```powershell
python gomoku_cli.py --level low
python gomoku_cli.py --level medium
python gomoku_cli.py --level high
```

切换棋盘大小：

```powershell
python gomoku_cli.py --size 15
python gomoku_cli.py --size 17
python gomoku_cli.py --size 19
```

查看全部参数：

```powershell
python gomoku_cli.py --help
```

## 生成 EXE

需要先安装打包工具：

```powershell
pip install -r requirements-build.txt
```

然后运行：

```powershell
python scripts/build_exe.py
```

或者使用 PowerShell 脚本：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build_exe.ps1
```

生成结果：

- `dist/GomokuAI_CLI.exe`：命令行版，保留控制台，可打印运算过程。
- `dist/GomokuAI_GUI.exe`：图形界面版。

更详细的构建说明见 [docs/BUILD.md](docs/BUILD.md)。

## 文档目录

- [算法说明](docs/ALGORITHM.md)
- [使用说明](docs/USAGE.md)
- [构建与打包](docs/BUILD.md)
- [更新日志](CHANGELOG.md)
- [贡献指南](CONTRIBUTING.md)
- [行为准则](CODE_OF_CONDUCT.md)
- [安全策略](SECURITY.md)

## 项目结构

```text
.
├── ai五子棋.py          # 中文 GUI 入口
├── gomoku_gui.py        # ASCII GUI 入口（方便 PyInstaller）
├── gomoku_cli.py        # 命令行入口
├── gomoku.py            # 兼容旧版 API 的门面模块
├── gomoku_engine/
│   ├── ai.py            # Alpha-Beta 搜索与评估
│   ├── board.py         # 棋盘规则与基础工具
│   ├── cli.py           # 命令行实现
│   └── gui.py           # Tkinter 界面实现
├── scripts/
│   ├── build_exe.py
│   └── build_exe.ps1
├── tests/
│   └── test_gomoku.py
└── docs/
```

## 兼容说明

`gomoku.py` 仍提供原来的常用名字（如 `BLACK`、`WHITE`、`check_win`、`ai_move`），方便旧脚本继续使用。引擎内部使用整数 `0/1/2` 表示空、黑、白，坐标全部为从 0 开始的行列值；CLI 和 GUI 负责转换为一维/一基坐标。

## License

[MIT](LICENSE)
