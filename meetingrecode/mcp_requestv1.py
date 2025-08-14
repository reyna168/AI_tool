import requests

def call_nl_sql_api(query_text: str):
    """
    Calls the /nl_sql API endpoint with a natural language query.
    """
    url = "http://localhost:8000/nl_sql"
    headers = {"Content-Type": "application/json"}
    data = {"query": query_text}
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()  # Raise an exception for bad status codes
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error calling API: {e}")
        return None

# Example query
query_string = "請列出 2025-08-05 當天的會議標題與時間與描述，最多 10 筆"
result = call_nl_sql_api(query_string)
print(result)
if result:
    print("Generated SQL:")
    print(result.get("sql"))
    print("\nQuery Results:")
    print(result.get("rows"))
    print("\nSummary Answer:")
    print(result.get("answer"))
