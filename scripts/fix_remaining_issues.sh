#!/bin/bash

# 修复导入排序问题 (I001)
echo "修复导入排序问题 (I001)..."
ruff check --select I --fix src/ tests/

# 修复print语句 (T201)
echo "修复print语句 (T201)..."
ruff check --select T201 --fix src/ tests/

echo "剩余问题修复完成！"
