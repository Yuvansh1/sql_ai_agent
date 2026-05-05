"""
Core SQL Agent — converts natural language to SQL using Ollama (local, free),
executes against SQLite, and returns results with explanation.
"""

import sqlite3
import re
import requests
from pathlib import Path
from dataclasses import dataclass

OLLAMA_URL = "http://localhost:11434"

DB_PATH = Path(__file__).parent.parent / "db" / "store.db"

SCHEMA = """
Tables in the database:

customers(id, name, email, country, joined_at DATE)
products(id, name, category, price REAL, stock INTEGER)
orders(id, customer_id, status TEXT, created_at DATE)
  -- status values: 'completed', 'shipped', 'pending', 'cancelled'
order_items(id, order_id, product_id, quantity INTEGER, unit_price REAL)

Relationships:
  orders.customer_id -> customers.id
  order_items.order_id -> orders.id
  order_items.product_id -> products.id

Revenue = order_items.quantity * order_items.unit_price
Only count revenue from orders with status = 'completed' or 'shipped'.
"""

SYSTEM_PROMPT = f"""You are a SQL expert. Your only job is to output a single valid SQLite SELECT query.

{SCHEMA}

STRICT RULES — follow every one:
- Output ONLY the raw SQL query. No words before it, no words after it.
- No markdown, no backticks, no explanation, no comments.
- First word of your response must be SELECT.
- You MUST include LIMIT. If user says "top N", use LIMIT N. Default LIMIT 50.
- Use only SQLite syntax. No date_trunc — use strftime('%Y-%m', date_column) instead.
- If the user mentions a specific year (e.g. "2024"), you MUST filter using: WHERE strftime('%Y', o.created_at) = '2024'
- Never return data from a different year than what the user asked for.
- Never use DROP, DELETE, UPDATE, INSERT, ALTER, CREATE, TRUNCATE.

IMPORTANT — there is NO total_revenue, total, amount, or order_value column anywhere.
To calculate revenue or order value you MUST always compute it like this:
  SUM(oi.quantity * oi.unit_price)
To get average order value per order:
  SUM(oi.quantity * oi.unit_price) / COUNT(DISTINCT o.id)
To get average order value by country:
  SELECT c.country, SUM(oi.quantity * oi.unit_price) / COUNT(DISTINCT o.id) AS avg_order_value
  FROM customers c
  JOIN orders o ON c.id = o.customer_id
  JOIN order_items oi ON o.id = oi.order_id
  WHERE o.status IN ('completed', 'shipped')
  GROUP BY c.country
  ORDER BY avg_order_value DESC
  LIMIT 50
Never reference a column that is not listed in the schema above.
"""


@dataclass
class AgentResult:
    question: str
    sql: str
    success: bool
    data: list
    columns: list
    explanation: str
    error: str = ""
    row_count: int = 0


class SQLAgent:
    def __init__(self, model: str = "llama3.2"):
        self.model = model
        self.history = []  # conversation memory

    def _chat(self, messages: list, max_tokens: int = 1024) -> str:
        """Send a chat request to Ollama and return the response text."""
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"num_predict": max_tokens, "temperature": 0},
        }
        resp = requests.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=60)
        resp.raise_for_status()
        return resp.json()["message"]["content"].strip()

    def _generate_sql(self, question: str) -> str:
        """Ask Ollama to generate SQL for the question."""
        messages = (
            [{"role": "system", "content": SYSTEM_PROMPT}]
            + self.history
            + [{"role": "user", "content": question}]
        )
        raw = self._chat(messages)

        # Strip markdown fences
        raw = re.sub(r"```sql", "", raw, flags=re.IGNORECASE)
        raw = re.sub(r"```", "", raw)

        # Extract just the SELECT statement — ignore any explanation text
        match = re.search(r"(SELECT\s.+)", raw, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()

        return raw.strip()

    def _explain(self, question: str, sql: str, columns: list, rows: list) -> str:
        """Ask Ollama to explain the results in plain English."""
        preview = str(rows[:5]) if rows else "No results"
        prompt = (
            f"The user asked: {question}\n"
            f"SQL used: {sql}\n"
            f"Columns: {columns}\n"
            f"First few rows: {preview}\n"
            f"Total rows returned: {len(rows)}\n\n"
            "Write a concise 1-2 sentence plain English summary of the results."
        )
        return self._chat([{"role": "user", "content": prompt}], max_tokens=256)

    def _execute(self, sql: str):
        """Execute SQL against SQLite, returns (columns, rows)."""
        import re
        # Extract LIMIT from the query if user specified one
        limit_match = re.search(r'\bLIMIT\s+(\d+)', sql, re.IGNORECASE)
        user_limit = int(limit_match.group(1)) if limit_match else None

        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        try:
            cur = conn.execute(sql)
            rows = cur.fetchall()
            columns = [d[0] for d in cur.description] if cur.description else []
            data = [list(r) for r in rows]

            # Honor the user's requested limit strictly
            if user_limit:
                data = data[:user_limit]
            else:
                data = data[:50]  # default cap

            return columns, data
        finally:
            conn.close()

    def _is_safe(self, sql: str) -> bool:
        """Block any write operations."""
        forbidden = re.compile(
            r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|REPLACE)\b",
            re.IGNORECASE
        )
        return not forbidden.search(sql)

    def ask(self, question: str) -> AgentResult:
        """Main entry point: question -> AgentResult."""
        try:
            sql = self._generate_sql(question)

            if not self._is_safe(sql):
                return AgentResult(
                    question=question, sql=sql, success=False,
                    data=[], columns=[], explanation="",
                    error="Blocked: query contains write operations."
                )

            columns, rows = self._execute(sql)
            explanation = self._explain(question, sql, columns, rows)

            # Update conversation memory (last 6 turns)
            self.history.append({"role": "user", "content": question})
            self.history.append({"role": "assistant", "content": sql})
            self.history = self.history[-12:]

            return AgentResult(
                question=question, sql=sql, success=True,
                data=rows, columns=columns,
                explanation=explanation, row_count=len(rows)
            )

        except requests.exceptions.ConnectionError:
            return AgentResult(
                question=question, sql="", success=False,
                data=[], columns=[], explanation="",
                error="Cannot connect to Ollama. Make sure it is running: ollama serve"
            )
        except Exception as e:
            return AgentResult(
                question=question, sql="", success=False,
                data=[], columns=[], explanation="",
                error=str(e)
            )

    def reset(self):
        """Clear conversation memory."""
        self.history = []

    @staticmethod
    def list_models() -> list:
        """Return locally available Ollama models."""
        try:
            resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
            resp.raise_for_status()
            return [m["name"] for m in resp.json().get("models", [])]
        except Exception:
            return []

    @staticmethod
    def is_running() -> bool:
        """Check if Ollama is running."""
        try:
            requests.get(f"{OLLAMA_URL}/api/tags", timeout=3)
            return True
        except Exception:
            return False
