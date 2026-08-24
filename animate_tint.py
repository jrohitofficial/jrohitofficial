import re

with open('assets/portrait.svg', 'r', encoding='utf-8') as f:
    text = f.read()

# Ensure we don't add it twice
if 'gold-tint' not in text:
    style_end = text.find('</style>')
    if style_end != -1:
        new_style = "@keyframes tintFade{0%{opacity:1}70%{opacity:1}100%{opacity:0}}.gold-tint{fill:#ff6600;mix-blend-mode:color;animation:tintFade 3.5s ease-out forwards;pointer-events:none;}"
        text = text[:style_end] + new_style + text[style_end:]

    # Add the rect before the closing g tag
    g_end = text.rfind('</g>\n</svg>')
    if g_end != -1:
        rect = '<rect class="gold-tint" x="0" y="0" width="1266" height="1266" />'
        text = text[:g_end] + rect + text[g_end:]

with open('assets/portrait.svg', 'w', encoding='utf-8') as f:
    f.write(text)
