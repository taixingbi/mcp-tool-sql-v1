

curl -N -sS "http://localhost:8000/mcp/" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "sql_agent",
      "arguments": {
        "args": {
          "question": "List 5 job titles in Ventura"
        }
      }
    }
  }'


  curl -N -sS "http://localhost:8000/mcp/" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "sql_agent",
      "arguments": {
        "args": {
            "question": "List 5 job titles in Ventura",
            "request_id": "12345678",
            "session_id": "123456"
        }
      }
    }
  }'




curl -N -sS "https://mcp-tool-sql-v1-dev.fly.dev/mcp/" \
-H "Content-Type: application/json" \
-H "Accept: application/json, text/event-stream" \
-d '{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "sql_agent",
    "arguments": {
      "args": {
          "question": "List 5 job titles in Ventura",
          "request_id": "12345678",
          "session_id": "123456"
      }
    }
  }
}'





{
  "metadata": {
    "everything else"
  },
  "error": null,
  "data": {
    "question": "...",
    "answer": "..."
  }
}
