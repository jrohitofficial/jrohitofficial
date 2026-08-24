import re

# Read both SVGs (portrait_temp = PP1, portrait_2 = PP2, both same canvas)
with open('assets/portrait_temp.svg', 'r', encoding='utf-8') as f:
    svg1 = f.read()

with open('assets/portrait_2.svg', 'r', encoding='utf-8') as f:
    svg2 = f.read()

# Extract inner content from svg2 (everything between </style> and </svg>)
s2_style_end = svg2.find('</style>') + 8
s2_svg_end = svg2.rfind('</svg>')
svg2_inner = svg2[s2_style_end:s2_svg_end]

# Fix svg1 opacity animation: end at 1.0 not 0.45
svg1 = svg1.replace(
    '@keyframes dp{0%,100%{opacity:.45}50%{opacity:1}}',
    '@keyframes dp{0%{opacity:.2}40%{opacity:.6}100%{opacity:1}}'
)
svg1 = svg1.replace(
    '.d{animation:dp 4.0s ease-in-out infinite}',
    '.d{animation:dp 4.0s ease-in-out 1 forwards}'
)

# Inject glitch styles before </style>
glitch_styles = """
@keyframes img1Glitch {
    0%, 45%   { opacity: 1; transform: translate(0,0) skewX(0deg); }
    46%        { opacity: 0.6; transform: translate(-5px,3px) skewX(12deg); }
    47%        { opacity: 0.2; transform: translate(5px,-3px) skewX(-12deg); }
    48%, 95%  { opacity: 0; }
    96%        { opacity: 0.2; transform: translate(4px,-2px) skewX(-8deg); }
    97%        { opacity: 0.6; transform: translate(-4px,2px) skewX(8deg); }
    98%, 100% { opacity: 1; transform: translate(0,0) skewX(0deg); }
}
@keyframes img2Glitch {
    0%, 45%   { opacity: 0; }
    46%        { opacity: 0.2; transform: translate(5px,-3px) skewX(-12deg); }
    47%        { opacity: 0.6; transform: translate(-5px,3px) skewX(12deg); }
    48%, 95%  { opacity: 1; transform: translate(0,0) skewX(0deg); }
    96%        { opacity: 0.6; transform: translate(-4px,2px) skewX(8deg); }
    97%        { opacity: 0.2; transform: translate(4px,-2px) skewX(-8deg); }
    98%, 100% { opacity: 0; }
}
.glitch1 { animation: img1Glitch 10s ease-in-out infinite; transform-origin: center; }
.glitch2 { animation: img2Glitch 10s ease-in-out infinite; transform-origin: center; }
"""

svg1 = svg1.replace('</style>', glitch_styles + '</style>')

# Add fade mask defs
style_end = svg1.find('</style>') + 8
defs = """<defs>
  <linearGradient id="fadeGradient" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="white" stop-opacity="1" />
    <stop offset="68%" stop-color="white" stop-opacity="1" />
    <stop offset="100%" stop-color="white" stop-opacity="0" />
  </linearGradient>
  <mask id="fadeMask">
    <rect x="0" y="0" width="100%" height="100%" fill="url(#fadeGradient)" />
  </mask>
</defs>"""

# Get svg1 inner content (after </style>)
svg1_inner = svg1[style_end:svg1.rfind('</svg>')]

# Build final SVG
final = (
    svg1[:style_end] +
    defs +
    '\n<g mask="url(#fadeMask)" class="glitch1">\n' +
    svg1_inner +
    '\n</g>\n' +
    '<g mask="url(#fadeMask)" class="glitch2">\n' +
    svg2_inner +
    '\n</g>\n' +
    '</svg>'
)

with open('assets/portrait.svg', 'w', encoding='utf-8') as f:
    f.write(final)

print('Size KB:', len(final)//1024)
print('Closes:', final.strip().endswith('</svg>'))
print('glitch1:', 'glitch1' in final)
print('glitch2:', 'glitch2' in final)
print('filter CSS:', 'filter:' in final)
