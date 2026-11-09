#!/usr/bin/env python3
"""Builds the clickable concept site from canvas boards (.dc.html) in src/.

Each board becomes a standalone page that runs on assets/dc-runtime.js. Links between boards of one concept
(href="Main.dc.html") are rewritten to the generated pages. Run from the repository root:

    python3 tools/build.py
"""
import hashlib
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = json.loads((ROOT / 'tools' / 'concepts.json').read_text(encoding='utf-8'))
# Pages may serve a cached runtime for up to 10 minutes; a content hash in the URL makes every page load the runtime
# it was built with, so an old cached runtime never runs a new board.
RUNTIME_VERSION = hashlib.sha256((ROOT / 'assets' / 'dc-runtime.js').read_bytes()).hexdigest()[:10]
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
body.framed #board{display:flex;justify-content:center;padding:32px 16px 64px;overflow-x:auto}
body.framed #board > *{flex:none;box-shadow:0 1px 2px rgba(28,36,39,.12),0 8px 32px rgba(28,36,39,.10)}
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
    script = parts['script']
    for source_name, target in links.items():
        template = template.replace(f'href="{source_name}"', f'href="{target}"')
        # Links computed in the board's script (e.g. a tile's href from renderVals) point at boards too.
        script = script.replace(f"'{source_name}'", f"'{target}'")
    if '</script' in script.lower() or '</template' in template.lower():
        raise SystemExit(f"{board['source']}: zawiera </script> albo </template>, nie da się osadzić")
    # <sc-for>/<sc-if> inside a table would be moved out of it by the HTML parser (foster parenting), leaving rows
    # without their loop. A nested <template data-sc> stays where it is in any context; the runtime reads both forms.
    template = re.sub(r'<sc-(for|if)\b', r'<template data-sc="\1"', template)
    template = re.sub(r'</sc-(for|if)>', '</template>', template)
    defaults = {k: v['default'] for k, v in parts['props'].items()}
    controls = ''.join(
        f'<label>{html.escape(PROP_LABELS.get(k, k))}<select data-prop="{html.escape(k)}">'
        + ''.join(f'<option{" selected" if o == v["default"] else ""}>{html.escape(o)}</option>' for o in v['options'])
        + '</select></label>'
        for k, v in parts['props'].items() if k in board.get('controls', ['theme', 'rola']))
    current = ' aria-current="page"'
    tabs = '' if concept.get('nav') is False else ''.join(
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
<body{' class="framed"' if board.get('framed') else ''}>
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
<script src="../assets/dc-runtime.js?v={RUNTIME_VERSION}"></script>
<script>
{script}
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


def plural(n: int) -> str:
    if n == 1:
        return 'plansza'
    return 'plansze' if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14) else 'plansz'


def tile(c: dict) -> str:
    first = c['boards'][0]['page']
    href = f"{c['id']}/" if first == 'index.html' else f"{c['id']}/{first}"
    count = len(c['boards'])
    meta = f"{count} {plural(count)}" + (f" · {html.escape(c['updated'])}" if c.get('updated') else '')
    art = f'<img src="assets/tiles/{html.escape(c["art"])}" alt="" loading="lazy" decoding="async"><span class="veil" aria-hidden="true"></span>' if c.get('art') else ''
    new = '<span class="new">Nowe</span>' if c.get('new') else ''
    return (f'<li><a class="tile" href="{href}" title="{html.escape(c["description"])}">{art}'
            f'<span class="top"><span class="info">{new}<span class="meta">{meta}</span></span>'
            '<svg class="arrow" width="18" height="18" viewBox="0 0 18 18" aria-hidden="true"><path d="M1.5 16.5L16.5 1.5M5.5 1.5h11v11"/></svg></span>'
            f'<span class="ttl">{html.escape(c["title"])}</span></a></li>')


def index(concepts: list) -> str:
    sections: dict = {}
    for c in concepts:
        sections.setdefault(c.get('section', 'Inne'), []).append(c)
    body = ''.join(
        f'<section aria-label="{html.escape(name)}"><h2>{html.escape(name)}</h2><ul class="grid">{"".join(tile(c) for c in items)}</ul></section>'
        for name, items in sections.items())
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
:root{{--bg:#ebeef0;--fg:#1c2427;--mut:#535f65;--card:#ffffff;--card-0:rgba(255,255,255,0);--card-70:rgba(255,255,255,.7);--art:.35}}
@media (prefers-color-scheme: dark){{:root{{--bg:#121518;--fg:#e6ecee;--mut:#a9b3b8;--card:#1d2327;--card-0:rgba(29,35,39,0);--card-70:rgba(29,35,39,.7);--art:.14}}}}
body{{margin:0;background:var(--bg);color:var(--fg);font:400 16px/1.5 'Instrument Sans',ui-sans-serif,system-ui,sans-serif}}
main{{max-width:1280px;margin:0 auto;padding:56px clamp(16px,4vw,40px) 80px;box-sizing:border-box;display:flex;flex-direction:column;gap:clamp(48px,5.6vw,72px)}}
.eyebrow{{margin:0;font-size:12px;font-weight:600;letter-spacing:.14em;text-transform:uppercase;color:var(--mut)}}
h1{{margin:8px 0 0;font-size:clamp(28px,3vw,40px);line-height:1.1;font-weight:600;letter-spacing:-.015em}}
section{{display:flex;flex-direction:column;gap:16px}}
h2{{margin:0;padding-bottom:12px;border-bottom:1px solid var(--fg);font-size:12px;font-weight:600;letter-spacing:.16em;text-transform:uppercase}}
.grid{{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}}
@media (min-width:640px){{.grid{{grid-template-columns:repeat(auto-fill,minmax(max(220px,calc((100% - 37px)/4)),1fr));gap:12px}}}}
.grid li{{display:flex;min-width:0}}
.tile{{position:relative;isolation:isolate;flex:1;display:flex;flex-direction:column;justify-content:space-between;gap:16px;aspect-ratio:1/1;box-sizing:border-box;padding:16px;background:var(--card);color:var(--fg);text-decoration:none;overflow:hidden;transition:background-color .2s,color .2s}}
@media (min-width:640px){{.tile{{aspect-ratio:5/4;gap:20px;padding:clamp(18px,1.7vw,24px)}}}}
.tile img{{position:absolute;inset:0;z-index:-2;width:100%;height:100%;object-fit:cover;object-position:78% center;opacity:var(--art);transition:opacity .2s}}
.tile .veil{{position:absolute;inset:0;z-index:-1;background:linear-gradient(to top,var(--card) 12%,var(--card-70) 38%,var(--card-0) 70%);transition:opacity .2s}}
.tile:hover,.tile:focus-visible{{background:var(--fg);color:var(--card);outline:none}}
.tile:focus-visible{{box-shadow:0 0 0 3px var(--bg),0 0 0 5px var(--fg)}}
.tile:hover img,.tile:focus-visible img{{opacity:.1}}
.tile:hover .veil,.tile:focus-visible .veil{{opacity:0}}
.top{{display:flex;align-items:flex-start;justify-content:space-between;gap:12px}}
.info{{display:flex;flex-direction:column;align-items:flex-start;gap:8px}}
.meta{{font-size:12px;font-variant-numeric:tabular-nums;opacity:.75}}
.new{{font-size:11px;font-weight:600;letter-spacing:.12em;text-transform:uppercase;padding:3px 7px;background:var(--fg);color:var(--card)}}
.tile:hover .new,.tile:focus-visible .new{{background:var(--card);color:var(--fg)}}
.arrow{{flex:none;fill:none;stroke:currentColor;stroke-width:1.25px;transition:transform .2s}}
.tile:hover .arrow{{transform:translate(5px,-5px)}}
.ttl{{font-size:clamp(17px,calc(1.4vw + 6px),26px);line-height:1.15;letter-spacing:-.015em;font-weight:500;text-wrap:balance;overflow-wrap:anywhere}}
@media (prefers-reduced-motion:reduce){{.tile,.tile img,.tile .veil,.arrow{{transition:none}}}}
</style>
</head>
<body>
<main>
<header><p class="eyebrow">Państwowa Straż Pożarna · Reports</p><h1>Lista elementów do wprowadzenia</h1></header>
{body}
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
