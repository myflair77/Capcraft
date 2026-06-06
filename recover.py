import json

try:
    with open(r'C:\Users\user\.gemini\antigravity-ide\brain\9da88ae9-e54a-4978-94ec-c881ffabb291\.system_generated\logs\transcript.jsonl', 'r', encoding='utf-8') as f:
        for line in f:
            if '"step_index":76' in line:
                data = json.loads(line)
                content = data.get('content', '')
                with open('recovered.txt', 'w', encoding='utf-8') as out:
                    out.write(content)
                break
except Exception as e:
    print(e)
