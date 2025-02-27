# 动态 SQL 生成器

基于 Flask 的 Web 服务，可根据预定义模板和用户提供的参数动态生成并执行 SQL 查询。

## 概述

本项目提供 HTTP API，接收 JSON 格式的参数，根据提供的业务类型(`biz_type`)选择适当的 SQL 模板，使用参数填充模板，对 MySQL 数据库执行查询，并返回结果。

## 主要功能

- 提供 REST API 接收查询参数
- 基于模板动态生成 SQL 语句
- 支持不同业务类型的 SQL 模板
- 安全参数处理，防止 SQL 注入
- 可配置的数据库连接
- 完善的错误处理和参数验证
- 全面的日志记录和监控
- 缓存机制提高性能
- 支持外部 SQL 模板加载

## 项目结构

```
dynamic-SQL-generate/
├── app/
│   ├── __init__.py           # Flask应用初始化
│   ├── api/                  # API端点
│   │   ├── __init__.py
│   │   └── routes.py         # API路由定义
│   ├── config/               # 配置文件
│   │   ├── __init__.py
│   │   └── config.py         # 不同环境的配置设置
│   ├── database/             # 数据库连接和操作
│   │   ├── __init__.py
│   │   └── db.py             # 数据库连接模块
│   ├── services/             # 业务逻辑
│   │   ├── __init__.py
│   │   └── sql_service.py    # SQL模板处理服务
│   └── templates/            # SQL模板
│       ├── __init__.py
│       └── sql_templates.py  # SQL模板定义
├── tests/                    # 单元测试
│   └── __init__.py
├── .env.example              # 环境变量示例文件
├── .gitignore                # Git忽略文件
├── config.py                 # 配置加载器
├── requirements.txt          # 项目依赖
└── run.py                    # 应用入口点
```

## 安装和部署

### 前提条件

- Python 3.8+
- MySQL 数据库

### 安装步骤

1. 克隆代码库:

   ```
   git clone <仓库URL>
   cd dynamic-SQL-generate
   ```

2. 创建并激活虚拟环境:

   ```
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

3. 安装依赖:

   ```
   pip install -r requirements.txt
   ```

   > **注意**: 本项目使用纯 Python 实现的 PyMySQL 作为 MySQL 驱动，而不是需要编译的 mysqlclient。如果你希望使用 mysqlclient 以获得更好的性能，请先安装 MySQL 开发库:
   >
   > - 在 Debian/Ubuntu 上: `sudo apt-get install python3-dev default-libmysqlclient-dev build-essential`
   > - 在 RedHat/CentOS 上: `sudo yum install python3-devel mysql-devel`
   > - 在 macOS 上 (使用 Homebrew): `brew install mysql-client`
   >
   > 然后在 requirements.txt 中取消 mysqlclient 的注释并重新安装依赖。

4. 基于.env.example 创建.env 文件，设置数据库配置。

5. 运行应用:
   ```
   python run.py
   ```

## API 使用说明

### 查询接口

**接口:** `POST /api/query`

**请求体 (JSON):**

```json
{
  "biz_type": "customer_analysis",
  "parameters": {
    "customer_id": 12345,
    "start_date": "2023-01-01",
    "end_date": "2023-12-31"
  },
  "group_parameters": "customer_id,product_category",
  "sort_parameters": [
    {
      "sort_param": "purchase_date",
      "sort_type": "desc"
    },
    {
      "sort_param": "amount",
      "sort_type": "desc"
    }
  ]
}
```

**字段说明:**

- `biz_type`: (必填) 业务类型，用于确定使用哪个 SQL 模板
- `parameters`: (必填) 参数对象，用于填充 SQL 模板中的占位符
- `group_parameters`: (可选) 逗号分隔的字段名列表，用于动态指定 GROUP BY 子句
- `sort_parameters`: (可选) 排序参数列表，每个排序参数包含以下字段:
  - `sort_param`: 排序字段名
  - `sort_type`: 排序方式，值为 "asc" (升序)或 "desc" (降序)

如果提供了`group_parameters`，它将覆盖模板中的任何 GROUP BY 子句。
如果提供了`sort_parameters`，它将覆盖模板中的任何 ORDER BY 子句。

**成功响应 (JSON):**

```json
{
  "status": "success",
  "data": [
    {
      "column1": "value1",
      "column2": "value2",
      ...
    },
    ...
  ],
  "row_count": 10,
  "db_execution_time_ms": 25,
  "template_time_ms": 2,
  "total_time_ms": 30,
  "cache_hit": false
}
```

**错误响应:**

```json
{
  "status": "error",
  "error": "参数无效: customer_id必须是整数",
  "code": "INVALID_PARAMETER"
}
```

### 模板列表接口

**接口:** `GET /api/templates`

**响应 (JSON):**

```json
{
  "status": "success",
  "templates": {
    "customer_analysis": "分析客户订单历史",
    "product_performance": "分析产品销售表现"
  },
  "count": 2
}
```

### 样例请求接口

**接口:** `GET /api/sample/<biz_type>`

**响应 (JSON):**

```json
{
  "status": "success",
  "sample_request": {
    "biz_type": "customer_analysis",
    "parameters": {
      "customer_id": 1,
      "start_date": "2023-01-01",
      "end_date": "2023-01-01",
      "product_category": "sample_value"
    }
  },
  "description": "分析客户订单历史",
  "required_params": ["customer_id", "start_date", "end_date"],
  "optional_params": ["product_category"]
}
```

### 缓存统计接口

**接口:** `GET /api/cache/stats`

**响应 (JSON):**

```json
{
  "status": "success",
  "cache_stats": {
    "size": 10,
    "hits": 120,
    "misses": 30,
    "hit_ratio": 0.8
  }
}
```

### 清除缓存接口

**接口:** `POST /api/cache/clear`

**响应 (JSON):**

```json
{
  "status": "success",
  "message": "缓存已成功清除"
}
```

### 健康检查接口

**接口:** `GET /health`

**响应 (JSON):**

```json
{
  "status": "healthy",
  "service": "dynamic-sql-generator",
  "database": "healthy",
  "environment": "development"
}
```

## SQL 模板

SQL 模板定义在`app/templates/sql_templates.py`中，按业务类型组织。每个模板是一个带有参数占位符的字符串。

模板示例:

```python
SQL_TEMPLATES = {
    "customer_analysis": """
        SELECT
            o.order_id,
            p.product_name,
            o.amount,
            o.purchase_date
        FROM
            orders o
        JOIN
            products p ON o.product_id = p.product_id
        WHERE
            o.customer_id = :customer_id
            AND o.purchase_date BETWEEN :start_date AND :end_date
        {% if product_category %}
            AND p.category = :product_category
        {% endif %}
        ORDER BY
            o.purchase_date DESC
    """
}
```

## 添加新的 SQL 模板

通过两种方式添加新模板:

### 1. 在代码中直接添加

在`app/templates/sql_templates.py`的`SQL_TEMPLATES`字典中添加新模板:

```python
SQL_TEMPLATES["new_template"] = """
    SELECT * FROM table WHERE field = :param
"""

# 添加模板元数据用于参数验证
TEMPLATE_METADATA["new_template"] = {
    "description": "新模板描述",
    "required_params": ["param"],
    "optional_params": [],
    "param_types": {
        "param": "string"
    }
}
```

### 2. 通过外部文件添加

在应用实例目录(instance)的 templates 子目录中创建`sql_templates.json`文件:

```json
{
  "new_template": "SELECT * FROM table WHERE field = :param"
}
```

系统会在启动时自动加载这些模板。

## 安全考虑

- 所有参数都经过正确转义，防止 SQL 注入
- 敏感连接信息存储在环境变量中
- 对所有请求进行输入验证
- 数据库用户仅具有所需的最低权限
- 使用参数化查询防止 SQL 注入攻击

## 缓存机制

系统实现了 SQL 模板渲染结果的缓存:

- 使用参数和业务类型的哈希作为缓存键
- 缓存统计提供命中率信息
- 可通过 API 清除缓存

## 故障排除

常见问题及解决方案:

1. **数据库连接失败**

   - 检查.env 文件中的数据库配置
   - 确保 MySQL 服务正在运行

2. **未知的业务类型错误**

   - 检查请求中的`biz_type`是否正确
   - 使用`/api/templates`接口查看可用模板

3. **参数验证错误**

   - 使用`/api/sample/<biz_type>`获取正确的参数格式
   - 确保所有必需参数都已提供并且格式正确

4. **MySQL 驱动问题**
   - 默认使用 PyMySQL 作为纯 Python MySQL 驱动
   - 如需使用 mysqlclient 获取更好性能，请参考安装注意事项

## 贡献指南

1. 复刻(Fork)代码库
2. 创建特性分支: `git checkout -b feature/功能名称`
3. 提交更改: `git commit -m '添加某功能'`
4. 推送到分支: `git push origin feature/功能名称`
5. 提交拉取请求(Pull Request)

## 许可证

本项目采用 MIT 许可证 - 详情请参阅 LICENSE 文件

## 高级查询功能

### 动态分组

通过`group_parameters`参数，您可以动态指定 SQL 查询的 GROUP BY 子句，无需修改 SQL 模板。这对于灵活的数据分析和聚合非常有用。

**示例：**

```json
{
  "biz_type": "event_flow",
  "parameters": {
    "start_date": "2023-01-01",
    "end_date": "2023-12-31"
  },
  "group_parameters": "tenant_id,status"
}
```

这将生成一个按`tenant_id`和`status`分组的查询，并覆盖模板中原有的 GROUP BY 子句。

### 动态排序

通过`sort_parameters`参数，您可以动态指定 SQL 查询的 ORDER BY 子句，支持多字段排序和不同的排序方向。

**示例：**

```json
{
  "biz_type": "event_flow",
  "parameters": {
    "start_date": "2023-01-01",
    "end_date": "2023-12-31"
  },
  "sort_parameters": [
    {
      "sort_param": "create_time",
      "sort_type": "desc"
    },
    {
      "sort_param": "id",
      "sort_type": "asc"
    }
  ]
}
```

这将生成一个按`create_time`降序和`id`升序排序的查询，并覆盖模板中原有的 ORDER BY 子句。

### 组合使用

您可以同时使用动态分组和动态排序功能：

```json
{
  "biz_type": "event_flow",
  "parameters": {
    "start_date": "2023-01-01",
    "end_date": "2023-12-31",
    "tenant_id": 100
  },
  "group_parameters": "department_id,status",
  "sort_parameters": [
    {
      "sort_param": "status",
      "sort_type": "asc"
    },
    {
      "sort_param": "count(*)",
      "sort_type": "desc"
    }
  ]
}
```

### 实际场景示例：基层治理事件信息流转

对于基层治理事件信息流转表的多表关联查询，可以使用以下请求：

```json
{
  "biz_type": "event_flow",
  "parameters": {
    "start_date": "2023-01-01",
    "end_date": "2023-12-31",
    "tenant_id": 12345,
    "status": "处理中"
  },
  "group_parameters": "tenant_id,status",
  "sort_parameters": [
    {
      "sort_param": "create_time",
      "sort_type": "desc"
    },
    {
      "sort_param": "id",
      "sort_type": "asc"
    }
  ]
}
```

此查询将：

1. 使用`event_flow`模板基础查询
2. 按`tenant_id`和`status`进行分组
3. 按`create_time`降序和`id`升序排序
4. 过滤日期范围、租户 ID 和状态
