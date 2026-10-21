import sqlite3
import pandas as pd
from langchain_core.tools import tool

# Point to the database we created in Phase 1
DB_PATH = 'ecommerce.db'

@tool
def list_tables() -> str:
    """Fetches all available table names in the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # SQLite-specific query to get all table names
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    conn.close()
    
    return ", ".join([t[0] for t in tables])

@tool
def get_schema(table_names: str) -> str:
    """Gets the schema (columns, types) and a sample row for the specified comma-separated table names."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    schema_info = ""
    
    for table in table_names.split(","):
        table = table.strip()
        
        # PRAGMA is SQLite's way to get column metadata
        cursor.execute(f"PRAGMA table_info({table});")
        columns = cursor.fetchall()
        
        if not columns:
            schema_info += f"Table '{table}' not found.\n"
            continue
            
        col_details = ", ".join([f"{col[1]} ({col[2]})" for col in columns])
        schema_info += f"Table: {table}\nColumns: {col_details}\n"
        
        # Fetch one sample row to help the LLM understand the data formatting
        cursor.execute(f"SELECT * FROM {table} LIMIT 1;")
        sample = cursor.fetchone()
        schema_info += f"Sample Row: {sample}\n\n"
        
    conn.close()
    return schema_info.strip()

@tool
def execute_query(query: str) -> str:
    """Executes a SQL SELECT statement and returns the results or an error message."""
    if not query.strip().upper().startswith("SELECT"):
        return "Error: For database safety, only SELECT queries are allowed."
    
    try:
        conn = sqlite3.connect(DB_PATH)
        # Use Pandas to execute the query and fetch data with column headers
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        # Save the raw data to a temporary CSV file for the Streamlit frontend
        df.to_csv("results.csv", index=False)
        
        # Return a string representation so the LLM can read the data and synthesize an answer
        return df.to_string(index=False)
        
    except Exception as e:
        return f"SQL Execution Error: {e}"

# --- Test block ---
# If you run this file directly, it will test the tools without the LLM.
if __name__ == "__main__":
    print("Available Tables:", list_tables.invoke(""))
    print("\nSchema for 'users' and 'orders':\n", get_schema.invoke("customers, orders"))
    print("Test Query Result:", execute_query.invoke("SELECT count(*) FROM products;"))

@tool
def generate_chart(code: str) -> str:
    """Executes Python code to create a chart. 
    Rules:
    1. Use matplotlib.pyplot as plt.
    2. The dataset must be hardcoded within the code based on your SQL results.
    3. You MUST save the plot using plt.savefig('output_chart.png').
    4. NEVER use plt.show().
    """
    try:
        # Execute the code in an isolated dictionary namespace
        namespace = {}
        exec(code, namespace)
        return "Chart generated successfully and saved to output_chart.png."
    except Exception as e:
        return f"Python execution error: {e}"