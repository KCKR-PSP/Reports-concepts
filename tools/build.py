#!/usr/bin/env python3
"""Builds the clickable concept site from canvas boards (.dc.html) in src/.

Each board becomes a standalone page that runs on assets/dc-runtime.js. Links between boards of one concept
(href="Main.dc.html") are rewritten to the generated pages. Run from the repository root:

    python3 tools/build.py
"""
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = json.loads((ROOT / 'tools' / 'concepts.json').read_text(encoding='utf-8'))
PROP_LABELS = {'theme': 'Motyw', 'rola': 'Widok', 'stan': 'Stan danych', 'zagrozenie': 'Zagrożenie gminy'}

SHELL_CSS = """
html,body{margin:0;background:#ebeef0}
body.dark{background:#121518}
.cbar{position:sticky;top:0;z-index:50;display:flex;flex-wrap:wrap;align-items:center;gap:8px 20px;padding:8px clamp(16px, 4vw, 40px);
  background:#1c2427;color:#ebeef0;font:500 13px/1.3 'Instrument Sans',ui-sans-serif,system-ui,sans-serif}
.cbar a{color:inherit;text-decoration:none;display:inline-flex;align-items:center;min-height:36px}
.cbar a:hover{text-decoration:underline}
.cbar .ttl{font-weight:700}
.cbar .tag{padding:3px 8px;border:1px solid #535f65;color:#a9b3b8;font-size:12px}
.cbar .sp{flex:1}
.cbar nav{display:flex;flex-wrap:wrap;gap:4px 16px}
.cbar nav a[aria-current="page"]{font-weight:700;text-decoration:underline}
.cbar label{display:inline-flex;align-items:center;gap:8px;color:#a9b3b8}
.cbar select{min-height:32px;padding:0 8px;border:1px solid #535f65;border-radius:0;background:#1c2427;color:#ebeef0;font:inherit}
.cbar a:focus-visible,.cbar select:focus-visible{outline:2px solid #ebeef0;outline-offset:2px}
@media (max-width: 760px){.cbar{position:static}}
"""


def board_parts(path: Path) -> dict:
    source = path.read_text(encoding='utf-8')
    helmet = re.search(r'<helmet>(.*?)</helmet>', source, re.S).group(1)
    template = re.search(r'</helmet>(.*?)</x-dc>', source, re.S).group(1)
    script = re.search(r'<script type="text/x-dc"[^>]*>(.*?)</script>', source, re.S).group(1)
    props_match = re.search(r"data-props='([^']*)'", source)
    props = json.loads(props_match.group(1)) if props_match else {}
    return {'helmet': helmet, 'template': template, 'script': script,
            'props': {k: v for k, v in props.items() if isinstance(v, dict) and v.get('editor') == 'enum'}}


def page(concept: dict, board: dict, parts: dict, links: dict) -> str:
    template = parts['template']
    for source_name, target in links.items():
        template = template.replace(f'href="{source_name}"', f'href="{target}"')
    if '</script' in parts['script'].lower() or '</template' in template.lower():
        raise SystemExit(f"{board['source']}: zawiera </script> albo </template>, nie da się osadzić")
    defaults = {k: v['default'] for k, v in parts['props'].items()}
    controls = ''.join(
        f'<label>{html.escape(PROP_LABELS.get(k, k))}<select data-prop="{html.escape(k)}">'
        + ''.join(f'<option{" selected" if o == v["default"] else ""}>{html.escape(o)}</option>' for o in v['options'])
        + '</select></label>'
        for k, v in parts['props'].items() if k in board.get('controls', ['theme', 'rola']))
    current = ' aria-current="page"'
    tabs = ''.join(
        f'<a href="{b["page"]}"{current if b is board else ""}>{html.escape(b["title"])}</a>' for b in concept['boards'] if b.get('nav', True) or b is board)
    return f"""<!doctype html>
<html lang="pl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>{html.escape(board['title'])} · Koncepcje Reports</title>
{parts['helmet']}
<style>{SHELL_CSS}</style>
</head>
<body>
<div class="cbar">
<a href="../index.html">← Koncepcje Reports</a>
<span class="ttl">{html.escape(concept['title'])}</span>
<span class="tag">Koncepcja · dane przykładowe</span>
<nav aria-label="Plansze">{tabs}</nav>
<span class="sp"></span>
{controls}
</div>
<div id="board"></div>
<template id="board-template">{template}</template>
<script src="../assets/dc-runtime.js"></script>
<script>
{parts['script']}
(function () {{
  const props = {json.dumps(defaults, ensure_ascii=False)};
  const applyTheme = () => document.body.classList.toggle('dark', props.theme === 'ciemny');
  const board = mountBoard(document.getElementById('board'), document.getElementById('board-template'), Component, props);
  applyTheme();
  document.querySelectorAll('.cbar select[data-prop]').forEach((select) => select.addEventListener('change', () => {{
    props[select.dataset.prop] = select.value;
    board.setProps({{ [select.dataset.prop]: select.value }});
    applyTheme();
  }}));
}})();
</script>
</body>
</html>
"""


def index(concepts: list) -> str:
    items = ''.join(
        f'<li><h2>{html.escape(c["title"])}</h2><p>{html.escape(c["description"])}</p><p class="links">'
        + ''.join(f'<a href="{c["id"]}/{b["page"]}">{html.escape(b["title"])} →</a>' for b in c['boards'] if b.get('nav', True))
        + '</p></li>' for c in concepts)
    return f"""<!doctype html>
<html lang="pl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>Lista elementów do wprowadzenia · Reports</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Instrument+Sans:wght@400;500;600;700&amp;display=swap" rel="stylesheet">
<style>
:root{{--bg:#ebeef0;--fg:#1c2427;--mut:#535f65;--line:#d3dadd}}
@media (prefers-color-scheme: dark){{:root{{--bg:#121518;--fg:#e6ecee;--mut:#a9b3b8;--line:#363d43}}}}
body{{margin:0;background:var(--bg);color:var(--fg);font:400 16px/1.5 'Instrument Sans',ui-sans-serif,system-ui,sans-serif}}
main{{max-width:960px;margin:0 auto;padding:56px 16px 80px;display:flex;flex-direction:column;gap:32px}}
.eyebrow{{margin:0;font-size:12px;font-weight:600;letter-spacing:.14em;text-transform:uppercase;color:var(--mut)}}
h1{{margin:8px 0 0;font-size:36px;line-height:1.15;font-weight:600;letter-spacing:-.01em}}
ul{{list-style:none;margin:0;padding:0;border-top:1px solid var(--fg)}}
li{{padding:24px 0;border-bottom:1px solid var(--line)}}
h2{{margin:0;font-size:22px;font-weight:600}}
li p{{margin:8px 0 0;color:var(--mut);max-width:70ch}}
.links{{display:flex;flex-wrap:wrap;gap:8px 24px}}
a{{color:var(--fg);font-weight:600;text-underline-offset:3px}}
a:focus-visible{{outline:2px solid var(--fg);outline-offset:2px}}
</style>
</head>
<body>
<main>
<header><p class="eyebrow">Państwowa Straż Pożarna · Reports</p><h1>Lista elementów do wprowadzenia</h1></header>
<ul>{items}</ul>
<p class="eyebrow">Wszystkie dane na planszach są przykładowe.</p>
</main>
</body>
</html>
"""


def main() -> None:
    for concept in CONFIG['concepts']:
        out = ROOT / concept['id']
        out.mkdir(exist_ok=True)
        links = {b['source']: b['page'] for b in concept['boards']}
        for board in concept['boards']:
            parts = board_parts(ROOT / 'src' / concept['id'] / board['source'])
            (out / board['page']).write_text(page(concept, board, parts, links), encoding='utf-8')
            print(f"{concept['id']}/{board['page']}")
    (ROOT / 'index.html').write_text(index(CONFIG['concepts']), encoding='utf-8')
    print('index.html')


if __name__ == '__main__':
    main()
