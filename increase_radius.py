import re

with open('assets/portrait.svg', 'r', encoding='utf-8') as f:
    text = f.read()

def replacer(match):
    r = float(match.group(1))
    # increase radius by 1.35x to make the dots larger and the image clearer, without changing the colors
    new_r = min(5.0, r * 1.35)
    return f'r="{new_r:.2f}"'

new_text = re.sub(r'r="([0-9\.]+)"', replacer, text)

with open('assets/portrait.svg', 'w', encoding='utf-8') as f:
    f.write(new_text)
