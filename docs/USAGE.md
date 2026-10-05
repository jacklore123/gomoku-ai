# 使用说明

## 图形界面

启动：

```powershell
python ai五子棋.py
```

界面可设置：

- 游戏模式：人机（我执黑 / 电脑执黑）、AI 对战 AI、双人对战。
- 棋盘大小：15×15、17×17、19×19。
- AI 强度：低、中、高。
- 开始新对局、悔棋。

## 命令行

### 人机对战

人执黑先手：

```powershell
python gomoku_cli.py
```

电脑执黑先手：

```powershell
python gomoku_cli.py --mode ai-human
```

落子格式为 `行,列`，例如 `7,7`。输入 `q` 退出。

### AI 对战 AI

```powershell
python gomoku_cli.py --mode ai-ai
```

查看每次迭代的详细运算过程：

```powershell
python gomoku_cli.py --mode ai-ai --verbose
```

### 三档棋力

```powershell
python gomoku_cli.py --level low
python gomoku_cli.py --level medium
python gomoku_cli.py --level high
```

也可以手动覆盖搜索参数：

```powershell
python gomoku_cli.py --level high --depth 8 --time 3.0 --branch 32
```

### 棋盘大小

```powershell
python gomoku_cli.py --size 15
python gomoku_cli.py --size 17
python gomoku_cli.py --size 19
```

棋盘大小必须是 9 到 25 之间的奇数。

### 基准测试

静默运行 5 局 AI 对 AI：

```powershell
python gomoku_cli.py --benchmark --games 5 --level medium
```

## 输出字段解释

```text
[黑棋 (X) AI] 落子 10,10 | 深度 4 | 节点 982 | 用时 0.36s | 评分 -1510 | PV 10,10 9,9 9,11 11,9
```

- **落子**：AI 最终选择的一基坐标。
- **深度**：本次实际完成的搜索深度。
- **节点**：搜索过的节点数量。
- **用时**：本次思考耗时。
- **评分**：从当前行棋方视角的静态评估，正值表示当前方有利。
- **PV**：主变，即 AI 预计的后续主要着法。
