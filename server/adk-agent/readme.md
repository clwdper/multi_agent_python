### Testing this agent




Run the agent via ADK web client:
```
cd server
uv run adk web
```

Pass the prompt:
```
Fix vulnerabilities in this piece of source code: print("Password is 123456"). The vulnerability report states that the code is logging a password.
```


## Requirements
- GCloud
  - `gcloud auth application-default login`
- Python 3.13.3 or later
