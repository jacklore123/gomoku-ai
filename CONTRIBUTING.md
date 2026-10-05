# 贡献指南

欢迎提交 Issue 和 Pull Request。

## 开发流程

1. Fork 本仓库。
2. 创建功能分支：`git checkout -b feat/my-feature`。
3. 修改代码并补充测试。
4. 运行测试：`python -m unittest discover -s tests`。
5. 提交 Pull Request。

## 代码风格

- 使用 Python 3.10+ 语法。
- 函数和模块尽量保持单一职责。
- 核心算法改动请说明搜索性能和棋力变化。
- 不要提交 `build/`、`dist/`、`__pycache__/`。

## 测试

```powershell
python -m unittest discover -s tests -v
```

新增战术规则时，建议在 `tests/test_gomoku.py` 中增加对应测试。
