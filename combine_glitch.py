import re

# Read both SVGs
with open('assets/portrait.svg', 'r', encoding='utf-8') as f:
    svg1 = f.read()

with open('assets/portrait_2.svg', 'r', encoding='utf-8') as f:
    svg2 = f.read()

# Extract inner content from svg2
s2_style_end = svg2.find('</style>') + 8
s2_svg_end = svg2.rfind('</svg>')
svg2_inner = svg2[s2_style_end:s2_svg_end]

# Extract header + style from svg1 (already has fade mask + opacity fix)
s1_style_end = svg1.find('</style>')

# Glitch animation - only opacity + transform (NO filter - GitHub blocks it)
glitch_styles = """
@keyframes img1Glitch {
    0%, 45%   { opacity: 1; transform: translate(0,0) skewX(0deg); }
    46%        { opacity: 0.6; transform: translate(-5px, 3px) skewX(12deg); }
    47%        { opacity: 0.3; transform: translate(5px,-3px) skewX(-12deg); }
    48%, 95%  { opacity: 0; }
    96%        { opacity: 0.3; transform: translate(4px,-2px) skewX(-8deg); }
    97%        { opacity: 0.6; transform: translate(-4px,2px) skewX(8deg); }
    98%, 100% { opacity: 1; transform: translate(0,0) skewX(0deg); }
}
@keyframes img2Glitch {
    0%, 45%   { opacity: 0; }
    46%        { opacity: 0.3; transform: translate(5px,-3px) skewX(-12deg); }
    47%        { opacity: 0.6; transform: translate(-5px,3px) skewX(12deg); }
    48%, 95%  { opacity: 1; transform: translate(0,0) skewX(0deg); }
    96%        { opacity: 0.6; transform: translate(-4px,2px) skewX(8deg); }
    97%        { opacity: 0.3; transform: translate(4px,-2px) skewX(-8deg); }
    98%, 100% { opacity: 0; }
}
.glitch1 { animation: img1Glitch 10s ease-in-out infinite; transform-origin: center; }
.glitch2 { animation: img2Glitch 10s ease-in-out infinite; transform-origin: center; }
"""

# Insert glitch styles before closing </style>
svg1 = svg1[:s1_style_end] + glitch_styles + svg1[s1_style_end:]

# Find the existing <g mask="..."> tag and add class="glitch1"
svg1 = svg1.replace('<g mask="url(#fadeMask)">', '<g mask="url(#fadeMask)" class="glitch1">', 1)

# Append PP2 as second layer before </svg>
img2_block = f'\n<g mask="url(#fadeMask)" class="glitch2">\n{svg2_inner}\n</g>\n'
svg1 = svg1.replace('</svg>', img2_block + '</svg>')

with open('assets/portrait.svg', 'w', encoding='utf-8') as f:
    f.write(svg1)

print('Size KB:', len(svg1)//1024)
print('Closes:', svg1.strip().endswith('</svg>'))
print('glitch1:', 'glitch1' in svg1)
print('glitch2:', 'glitch2' in svg1)
print('No filter:', 'filter:' not in svg1)
