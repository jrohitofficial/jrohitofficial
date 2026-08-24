import re

with open('assets/portrait.svg', 'r', encoding='utf-8') as f:
    text = f.read(5000)

radii = re.findall(r'r="([0-9\.]+)"', text)
print(radii[:20])
