import re

with open('assets/portrait.svg', 'r', encoding='utf-8') as f:
    text1 = f.read()
    
with open('assets/portrait_2.svg', 'r', encoding='utf-8') as f:
    text2 = f.read()

content2 = text2[text2.find('</style>')+8 : text2.rfind('</svg>')]

style_end1 = text1.find('</style>')

glitch_styles = """
@keyframes img1Anim {
    0%, 46% { opacity: 1; transform: translate(0, 0); filter: hue-rotate(0deg); }
    47% { opacity: 0.8; transform: translate(-8px, 6px) skewX(20deg); filter: hue-rotate(90deg); }
    48% { opacity: 0.5; transform: translate(8px, -6px) skewX(-20deg); filter: hue-rotate(180deg); }
    49% { opacity: 0; transform: translate(0, 0); }
    50%, 96% { opacity: 0; }
    97% { opacity: 0.8; transform: translate(6px, -8px) skewX(-20deg); filter: hue-rotate(90deg); }
    98% { opacity: 0.5; transform: translate(-6px, 8px) skewX(20deg); filter: hue-rotate(-90deg); }
    99%, 100% { opacity: 1; transform: translate(0, 0); }
}

@keyframes img2Anim {
    0%, 46% { opacity: 0; }
    47% { opacity: 0.5; transform: translate(8px, -6px) skewX(-20deg); filter: hue-rotate(180deg); }
    48% { opacity: 0.8; transform: translate(-8px, 6px) skewX(20deg); filter: hue-rotate(-90deg); }
    49%, 96% { opacity: 1; transform: translate(0, 0); filter: hue-rotate(0deg); }
    97% { opacity: 0.8; transform: translate(-8px, 6px) skewX(20deg); filter: hue-rotate(90deg); }
    98% { opacity: 0.5; transform: translate(6px, -8px) skewX(-20deg); filter: hue-rotate(180deg); }
    99%, 100% { opacity: 0; transform: translate(0, 0); }
}

.glitch-img1 { animation: img1Anim 10s infinite step-end; transform-origin: center; }
.glitch-img2 { animation: img2Anim 10s infinite step-end; transform-origin: center; }
"""

text1 = text1[:style_end1] + glitch_styles + text1[style_end1:]

text1 = text1.replace('<g mask="url(#fadeMask)">', '<g mask="url(#fadeMask)" class="glitch-img1">')

content2_wrapped = f'\n<g mask="url(#fadeMask)" class="glitch-img2">\n{content2}\n</g>\n'

text1 = text1.replace('</svg>', content2_wrapped + '</svg>')

with open('assets/portrait.svg', 'w', encoding='utf-8') as f:
    f.write(text1)
