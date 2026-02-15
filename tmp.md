

curl -N -sS "http://localhost:8000/mcp/" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "sql_query",
      "arguments": {
        "args": {
          "request": {
            "version": "v1",
            "dataset": "gov_jobs",
            "metrics": [{"name": "amount", "agg": "avg"}],
            "dimensions": ["jurisdiction", "title"],
            "filters": { "location": ["ventura"] },
            "limit": 10
          }
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
      "name": "sql_query",
      "arguments": {
        "args": {
            "request": {
              "version": "v1",
              "dataset": "gov_jobs",
              "metrics": [{"name": "amount", "agg": "avg"}],
              "dimensions": ["jurisdiction", "title"],
              "limit": 10
            },
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
    "name": "sql_query",
    "arguments": {
      "args": {
          "request": {
            "version": "v1",
            "dataset": "gov_jobs",
            "metrics": [{"name": "amount", "agg": "avg"}],
            "dimensions": ["jurisdiction", "title"],
            "limit": 10
          },
          "request_id": "12345678",
          "session_id": "123456"
      }
    }
  }
}'