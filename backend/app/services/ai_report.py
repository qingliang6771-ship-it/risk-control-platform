"""AI Report Service - combines ThinkingData queries with AI analysis."""
import json
import re
from openai import AsyncOpenAI
from ..config import settings
from .thinkingdata import ta_service
from .schema_knowledge import PROJECTS, USER_TABLE_SCHEMA, EVENT_TABLE_SCHEMA, RISK_QUERY_TEMPLATES


class AIReportService:
    """
    AI-powered data report service.
    Flow: User question -> AI generates SQL -> Query ThinkingData -> AI analyzes results
    """

    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.AI_API_KEY,
            base_url=settings.AI_BASE_URL,
        )
        self.model = settings.AI_MODEL

    def _extract_project_id(self, query: str) -> tuple[str, str]:
        """Extract project ID from query prefix like [项目105] or from natural language."""
        # Project keyword mapping
        project_keywords = {
            "102": ["黄老师"],
            "105": ["丁老师"],
            "116": ["魏老师"],
            "128": ["支付中心"],
        }
        
        # First strip the explicit prefix format [项目xxx]
        prefix_project = None
        clean_query = query
        match = re.match(r'\[项目(\d+)\]\s*(.+)', query, re.DOTALL)
        if match:
            prefix_project = match.group(1)
            clean_query = match.group(2)
        
        # Check if the actual question text contains project keywords (higher priority)
        for pid, keywords in project_keywords.items():
            for kw in keywords:
                if kw in clean_query:
                    # Found keyword in text - use this project, remove keyword
                    final_query = clean_query.replace(kw, "").strip()
                    # Clean up leftover punctuation
                    final_query = re.sub(r'^[的项目，,\s]+', '', final_query)
                    if not final_query:
                        final_query = clean_query
                    return pid, final_query
        
        # No keyword in text, use prefix project or default
        if prefix_project:
            return prefix_project, clean_query
        
        return "105", query  # default to 105

    async def generate_report(self, user_question: str) -> dict:
        """
        Main entry: user asks a question in natural language,
        AI generates SQL, queries ThinkingData, then AI summarizes the result.
        """
        project_id, clean_question = self._extract_project_id(user_question)

        # Step 1: AI generates SQL based on user question
        sql = await self._generate_sql(clean_question, project_id)

        # Step 2: Execute SQL on ThinkingData
        try:
            query_result = await ta_service.query_sql(sql, format="json", timeout_seconds=30)
        except Exception as e:
            return {
                "question": clean_question,
                "sql": sql,
                "data": None,
                "analysis": f"数据查询失败: {str(e)}",
                "error": str(e),
            }

        # Step 3: AI analyzes the query result
        analysis = await self._analyze_data(clean_question, sql, query_result, project_id)

        return {
            "question": clean_question,
            "sql": sql,
            "data": {
                "headers": query_result["headers"],
                "rows": query_result["rows"][:100],  # Limit to 100 rows for display
                "total_rows": query_result["row_count"],
            },
            "analysis": analysis,
            "error": None,
        }

    async def direct_sql_query(self, sql: str) -> dict:
        """Directly execute a SQL query without AI generation."""
        try:
            query_result = await ta_service.query_sql(sql, format="json", timeout_seconds=30)
            return {
                "sql": sql,
                "data": {
                    "headers": query_result["headers"],
                    "rows": query_result["rows"][:500],
                    "total_rows": query_result["row_count"],
                },
                "error": None,
            }
        except Exception as e:
            return {
                "sql": sql,
                "data": None,
                "error": str(e),
            }

    async def _generate_sql(self, user_question: str, project_id: str = "105") -> str:
        """Use AI to generate SQL from natural language question."""
        project_name = PROJECTS.get(project_id, "未知项目")

        system_prompt = f"""你是一个数据分析专家，负责将用户的自然语言问题转换为 ThinkingData SQL 查询语句。

当前查询项目: {project_id} ({project_name})
事件表: v_event_{project_id}
用户表: v_user_{project_id}

{USER_TABLE_SCHEMA}

{EVENT_TABLE_SCHEMA}

{RISK_QUERY_TEMPLATES}

重要SQL语法规则（必须严格遵守）：
1. 字段名需要用双引号包裹，例如 "#user_id", "$part_date", "#event_name", "#event_time"
2. 【最重要】查询事件表(v_event_xxx)时，WHERE条件中必须包含 "$part_date" 过滤！这是分区字段，不传会报错！
3. "$part_date" 是 varchar 类型，格式为 'YYYY-MM-DD'，用于时间范围过滤
4. "#event_name" 是事件名称字段，用于过滤事件类型
5. "#event_time" 是事件精确时间(timestamp)，用于排序或精确时间筛选
6. 获取今天日期必须用: cast(current_date as varchar)，绝对不要用 CURRENT_DATE() 函数
7. 日期比较示例: WHERE "$part_date" = cast(current_date as varchar)
8. 昨天: WHERE "$part_date" = cast(current_date - interval '1' day as varchar)
9. 最近7天: WHERE "$part_date" >= cast(current_date - interval '7' day as varchar)
10. 最近30天: WHERE "$part_date" >= cast(current_date - interval '30' day as varchar)
11. 如果用户没有指定时间范围，默认查询最近7天的数据
12. 只返回纯SQL语句，不要任何解释、不要markdown代码块
13. 默认限制返回 1000 行
14. 不支持 CURRENT_DATE()、NOW()、GETDATE() 等函数，只能用 current_date
15. 事件名过滤必须同时带分区: WHERE "#event_name" = 'order_pay' AND "$part_date" >= cast(current_date - interval '7' day as varchar)
16. 布尔字段比较用 true/false: WHERE "is_true" = true
17. 如果用户提到 account_id 或账号ID，用 "#account_id" 字段查询
18. 如果用户提到 user_id 或用户ID，用 "#user_id" 字段查询
19. 查询用户表(v_user_xxx)时不需要 "$part_date"，只有事件表需要
20. 按时间排序用: ORDER BY "#event_time" DESC

示例SQL（必须严格参考这些格式）：
- 查今天充值总额: SELECT SUM("pay_amount") AS total_pay, COUNT(*) AS pay_count FROM v_event_{project_id} WHERE "#event_name" = 'order_pay' AND "is_true" = true AND "$part_date" = cast(current_date as varchar)
- 查最近7天每天活跃用户: SELECT "$part_date", COUNT(DISTINCT "#account_id") AS dau FROM v_event_{project_id} WHERE "$part_date" >= cast(current_date - interval '7' day as varchar) GROUP BY "$part_date" ORDER BY "$part_date"
- 查某用户最近充值记录: SELECT "#event_time", "pay_amount", "payment_type", "pay_id" FROM v_event_{project_id} WHERE "#event_name" = 'order_pay' AND "#account_id" = '12345' AND "$part_date" >= cast(current_date - interval '30' day as varchar) ORDER BY "#event_time" DESC
- 查某用户信息: SELECT * FROM v_user_{project_id} WHERE "#account_id" = '12345'
- 查最近7天提现申请: SELECT "#account_id", "#event_time", "amount", "payment_method" FROM v_event_{project_id} WHERE "#event_name" = 'withdraw_apply' AND "$part_date" >= cast(current_date - interval '7' day as varchar) ORDER BY "#event_time" DESC LIMIT 100"""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_question},
            ],
            temperature=0.1,
        )

        sql = response.choices[0].message.content.strip()
        # Clean up: remove markdown code blocks if present
        if sql.startswith("```"):
            lines = sql.split("\n")
            sql = "\n".join(lines[1:])  # remove first line
        if sql.endswith("```"):
            sql = sql[:-3]
        if sql.startswith("sql"):
            sql = sql[3:]
        sql = sql.strip()
        
        # Safety check: ensure $part_date is present when querying event table
        sql = self._ensure_part_date(sql, project_id)
        return sql

    def _ensure_part_date(self, sql: str, project_id: str) -> str:
        """Ensure $part_date filter exists when querying event table."""
        event_table = f"v_event_{project_id}"
        # Only check if querying event table
        if event_table not in sql.lower() and f"v_event_{project_id}" not in sql:
            return sql
        # Check if $part_date is already in the SQL
        if "$part_date" in sql:
            return sql
        # Need to inject $part_date - add default last 7 days filter
        # Find WHERE clause and append, or add WHERE before GROUP/ORDER/LIMIT
        if " WHERE " in sql.upper():
            # Append to existing WHERE
            sql = re.sub(
                r'(WHERE\s+)',
                r'\1"$part_date" >= cast(current_date - interval \'7\' day as varchar) AND ',
                sql,
                count=1,
                flags=re.IGNORECASE,
            )
        elif " GROUP " in sql.upper():
            sql = re.sub(
                r'(\s+GROUP\s)',
                r' WHERE "$part_date" >= cast(current_date - interval \'7\' day as varchar)\1',
                sql,
                count=1,
                flags=re.IGNORECASE,
            )
        elif " ORDER " in sql.upper():
            sql = re.sub(
                r'(\s+ORDER\s)',
                r' WHERE "$part_date" >= cast(current_date - interval \'7\' day as varchar)\1',
                sql,
                count=1,
                flags=re.IGNORECASE,
            )
        elif " LIMIT " in sql.upper():
            sql = re.sub(
                r'(\s+LIMIT\s)',
                r' WHERE "$part_date" >= cast(current_date - interval \'7\' day as varchar)\1',
                sql,
                count=1,
                flags=re.IGNORECASE,
            )
        else:
            # No WHERE/GROUP/ORDER/LIMIT, append at end
            sql = sql.rstrip(';') + ' WHERE "$part_date" >= cast(current_date - interval \'7\' day as varchar)'
        return sql

    async def _analyze_data(self, question: str, sql: str, data: dict, project_id: str = "105") -> str:
        """Use AI to analyze query results and provide insights."""
        project_name = PROJECTS.get(project_id, "未知项目")

        # Prepare data summary for AI
        data_summary = {
            "headers": data["headers"],
            "row_count": data["row_count"],
            "sample_rows": data["rows"][:20],  # Send first 20 rows as sample
        }

        system_prompt = f"""你是一个风控数据分析专家，当前分析项目: {project_id} ({project_name})。
根据用户的问题、执行的SQL和查询结果，提供专业的数据分析报告。

要求：
1. 用中文回答
2. 总结关键发现
3. 如果发现异常数据，重点标注
4. 给出风控相关的建议
5. 使用 Markdown 格式，包含表格和列表
6. 简洁明了，重点突出"""

        user_content = f"""用户问题: {question}

执行的SQL: {sql}

查询结果摘要:
- 总行数: {data_summary['row_count']}
- 列名: {json.dumps(data_summary['headers'], ensure_ascii=False)}
- 数据样本 (前20行):
{json.dumps(data_summary['sample_rows'], ensure_ascii=False, indent=2)}"""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=0.3,
        )

        return response.choices[0].message.content


ai_report_service = AIReportService()
