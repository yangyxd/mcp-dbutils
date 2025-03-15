#!/bin/bash

# 修复导入排序问题 (I001)
echo "修复导入排序问题 (I001)..."
ruff check --select I --fix src/ tests/

# 修复未使用的导入 (F401)
echo "修复未使用的导入 (F401)..."
ruff check --select F401 --fix src/ tests/

# 修复过时的typing导入 (UP035)
echo "修复过时的typing导入 (UP035)..."
ruff check --select UP035 --fix src/ tests/

echo "导入问题修复完成！"
