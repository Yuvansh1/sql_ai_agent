# SQL AI Agent

A natural language to SQL agent powered by Ollama — runs 100% locally, no API key, no cost.

## Features

- Converts plain English questions to SQL using a local LLM (Ollama)
- Executes queries against a local SQLite database (zero setup)
- Explains results in plain English
- Conversation memory for follow-up questions
- SQL safety guardrails (read-only, blocks write operations)
- Clean Streamlit UI with query history and CSV export

## Stack

| Layer | Tech |
|---|---|
| LLM | Ollama (llama3.2, local) |
| Database | SQLite (built-in, no server needed) |
| UI | Streamlit |
| Language | Python 3.9+ |

**Only 3 dependencies:** `streamlit`, `pandas`, `requests`

## Quick Start

### 1. Install Ollama

Download from https://ollama.com/download and install it.

Then pull a model:
```bash
ollama pull llama3.2
```

### 2. Clone and install

```bash
git clone https://github.com/Yuvansh1/sql-ai-agent
cd sql-ai-agent
pip install -r requirements.txt
```

### 3. Seed the database

```bash
python db/seed.py
```

This creates `db/store.db` with a sample e-commerce dataset:
- 20 customers across 6 countries
- 10 products across 4 categories
- ~70 orders with order items (2024 data)

### 4. Start Ollama

```bash
ollama serve
```

### 5. Run the app

```bash
streamlit run app/main.py --server.port 8502
```

Open `http://localhost:8502`, select your model in the sidebar, click **Connect**, and start asking questions.

## Example Questions

- *"Who are the top 5 customers by total revenue?"*
- *"What are monthly sales for 2024?"*
- *"Which product categories generate the most revenue?"*
- *"Show me all pending orders"*
- *"What is the average order value by country?"*

## Project Structure

```
sql-ai-agent/
├── agent/
│   └── sql_agent.py      # Core agent: NL -> SQL -> results -> explanation
├── app/
│   └── main.py           # Streamlit UI
├── db/
│   └── seed.py           # Creates and seeds store.db
├── requirements.txt
└── README.md
```

## How It Works

1. User types a question in the UI
2. `SQLAgent` sends the question + schema to Ollama with a strict system prompt
3. Ollama returns a SQL query (plain text, no markdown)
4. The agent validates the query (blocks any write operations)
5. The query runs against `store.db` via Python's built-in `sqlite3`
6. Ollama generates a plain English explanation of the results
7. Results, SQL, and explanation are displayed in the UI

## License

MIT
```