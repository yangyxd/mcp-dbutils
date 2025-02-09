# MCP 数据库服务

## 项目简介
MCP数据库服务是一个统一的数据库访问服务，支持多种数据库类型（PostgreSQL和SQLite）。它通过抽象层设计，为MCP服务器提供了简单、统一的数据库操作接口。

## 功能特性
- 统一的数据库访问接口
- 支持多个数据库配置
- 安全的只读查询执行
- 表结构和模式信息查询
- 智能的连接管理和资源清理
- 支持调试模式

## 安装与配置

### 安装方式

#### 使用 uvx 安装（推荐）
不需要专门安装，直接使用 `uvx` 运行：
```bash
uvx mcp-dbutils --config /path/to/config.yaml
```

添加到 Claude 配置：
```json
"mcpServers": {
  "database": {
    "command": "uvx",
    "args": ["mcp-dbutils", "--config", "/path/to/config.yaml"]
  }
}
```

#### 使用 pip 安装
```bash
pip install mcp-dbutils
```

添加到 Claude 配置：
```json
"mcpServers": {
  "database": {
    "command": "python",
    "args": ["-m", "mcp_dbutils", "--config", "/path/to/config.yaml"]
  }
}
```

#### 使用 Docker 安装
```bash
docker run -i --rm \
  -v /path/to/config.yaml:/app/config.yaml \
  mcp/dbutils --config /app/config.yaml
```

添加到 Claude 配置：
```json
"mcpServers": {
  "database": {
    "command": "docker",
    "args": ["run", "-i", "--rm", "-v", "/path/to/config.yaml:/app/config.yaml", 
             "mcp/dbutils", "--config", "/app/config.yaml"]
  }
}
```

### 环境要求
- Python 3.10+
- PostgreSQL (可选)
- SQLite3 (可选)

### 配置文件
项目运行需要一个YAML格式的配置文件，通过 `--config` 参数指定路径。配置示例：

```yaml
databases:
  # PostgreSQL配置示例
  my_postgres:
    type: postgres
    dbname: test_db
    user: postgres
    password: secret
    host: localhost
    port: 5432

  # SQLite配置示例
  my_sqlite:
    type: sqlite
    path: /path/to/database.db
    password: optional_password  # 可选
```

### 调试模式
设置环境变量 `MCP_DEBUG=1` 启用调试模式，可以看到详细的日志输出。

## 架构设计

### 核心理念：抽象层设计
在MCP数据库服务中，抽象层设计是最核心的架构思想。它就像一个通用遥控器，不管是控制电视还是空调，用户只需要知道"按下按钮就能完成操作"。

#### 1. 简化用户交互
- 用户只需要知道数据库的配置名称（比如 "my_postgres"）
- 不需要关心具体的连接参数和实现细节
- MCP服务器自动处理正确的数据库连接和查询

#### 2. 统一接口设计
- DatabaseHandler抽象类定义了统一的操作接口
- 所有具体数据库实现（PostgreSQL/SQLite）都遵循相同的接口
- 用户使用相同的方式访问不同类型的数据库

#### 3. 配置与实现分离
- 复杂的数据库配置参数封装在配置文件中
- 运行时通过简单的数据库名称引用这些配置
- 便于管理和修改数据库配置而不影响业务代码

### 系统组件
1. DatabaseServer
   - 作为MCP服务器的核心组件
   - 处理资源和工具请求
   - 管理数据库连接生命周期

2. DatabaseHandler
   - 抽象基类，定义统一接口
   - 包含get_tables()、get_schema()、execute_query()等方法
   - PostgreSQL和SQLite分别实现这些接口

3. 配置系统
   - 基于YAML的配置文件
   - 支持多数据库配置
   - 类型安全的配置验证

4. 错误处理和日志
   - 统一的错误处理机制
   - 详细的日志输出
   - 敏感信息屏蔽

## 使用示例

### 基本查询
```python
# 通过数据库名称访问
async with server.get_handler("my_postgres") as handler:
    # 执行SQL查询
    result = await handler.execute_query("SELECT * FROM users")
```

### 查看表结构
```python
# 获取所有表
tables = await handler.get_tables()

# 获取特定表的结构
schema = await handler.get_schema("users")
```

### 错误处理
```python
try:
    async with server.get_handler("my_db") as handler:
        result = await handler.execute_query("SELECT * FROM users")
except ValueError as e:
    print(f"配置错误: {e}")
except Exception as e:
    print(f"查询错误: {e}")
```

## 安全说明
- 仅支持SELECT查询，保护数据库安全
- 自动屏蔽日志中的敏感信息（如密码）
- 使用只读事务执行查询

## API文档

### DatabaseServer
核心服务器类，提供:
- 资源列表获取
- 工具调用处理
- 数据库处理器管理

### DatabaseHandler
抽象基类，定义接口:
- get_tables(): 获取表资源列表
- get_schema(): 获取表结构
- execute_query(): 执行SQL查询
- cleanup(): 资源清理

### PostgreSQL实现
提供PostgreSQL特定功能:
- 支持远程连接
- 表描述信息
- 约束查询

### SQLite实现
提供SQLite特定功能:
- 文件路径处理
- URI模式支持
- 密码保护支持（可选）
