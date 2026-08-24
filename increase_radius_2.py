import re

with open('assets/portrait_2.svg', 'r', encoding='utf-8') as f:
    text = f.read()

def replacer(match):
    r = float(match.group(1))
    new_r = min(5.0, r * 1.35)
    return f'r="{new_r:.2f}"'

new_text = re.sub(r'r="([0-9\.]+)"', replacer, text)

with open('assets/portrait_2.svg', 'w', encoding='utf-8') as f:
    f.write(new_text)
