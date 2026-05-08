import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

pattern = r'key="([^"]+)",\s*("[^"]+")'
replacement = r'\2, key="\1"'
content = re.sub(pattern, replacement, content)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Fixed app.py")
