#!/usr/bin/env python3
"""Inline web/ (three.js + model + app) into one self-contained HTML file.

  python3 tools/bundle.py [out.html]      (default: dist/airlie30-3d.html)
"""
import os, re, sys
root = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
web = os.path.join(root, 'web')
out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(root, 'dist', 'airlie30-3d.html')
html = open(os.path.join(web, 'index.html'), encoding='utf-8').read()

def inline(m):
    src = m.group(1)
    code = open(os.path.join(web, src), encoding='utf-8').read().replace('</script', '<\\/script')
    return '<script>/* %s */\n%s\n</script>' % (src, code)

html = re.sub(r'<script src="([^"]+)"></script>', inline, html)
os.makedirs(os.path.dirname(out), exist_ok=True)
open(out, 'w', encoding='utf-8').write(html)
print(out, os.path.getsize(out) // 1024, 'KB')
