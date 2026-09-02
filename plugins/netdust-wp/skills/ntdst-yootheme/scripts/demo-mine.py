#!/usr/bin/env python3
"""
Mine an official YOOtheme demo package (or any YOOtheme WP database dump)
without installing it.

A demo package ships `wp-content/sample_yootheme.json` — the whole database as a
JSON array of SQL statements, with `@@TABLE_PREFIX@@` / `@@SITES_URL@@` /
`@@ADMIN_EMAIL@@` placeholders. This reads it directly.

    # pull the file out of the zip (fast — no full extraction)
    unzip -o -j <demo>_demo_package_wordpress.zip wp-content/sample_yootheme.json -d .

    python3 demo-mine.py sample_yootheme.json summary
    python3 demo-mine.py sample_yootheme.json config      > customizer.json
    python3 demo-mine.py sample_yootheme.json settings    # site/header/mobile/top/bottom/post/blog
    python3 demo-mine.py sample_yootheme.json templates
    python3 demo-mine.py sample_yootheme.json pages       # id, type, slug, builder|-
    python3 demo-mine.py sample_yootheme.json menus
    python3 demo-mine.py sample_yootheme.json layout home > home.json
    python3 demo-mine.py sample_yootheme.json footer      > footer.json
    python3 demo-mine.py sample_yootheme.json census

Needs `php` on PATH for `config`/`footer`/`menus` (theme_mods is PHP-serialized).
See references/yootheme-site-model.md for what the output means.
"""
import collections
import json
import re
import subprocess
import sys

# --- SQL dump parsing -------------------------------------------------------

UNESC = {'\\n': '\n', '\\r': '\r', '\\t': '\t', '\\0': '\0',
         '\\\\': '\\', "\\'": "'", '\\"': '"', '\\Z': '\x1a'}


def _unesc(v):
    v = v.strip()
    if v == 'NULL':
        return None
    if len(v) >= 2 and v[0] == v[-1] == "'":
        v = v[1:-1]
    return re.sub(r'\\(.)', lambda m: UNESC.get(m.group(0), m.group(1)), v)


def _split_values(s):
    """Split a mysqldump VALUES(...),(...) tail into row tuples, respecting
    quotes and backslash escapes."""
    rows, cur, field = [], [], []
    i, n, in_str, depth = 0, len(s), False, 0
    while i < n:
        ch = s[i]
        if in_str:
            if ch == '\\':
                field.append(s[i:i + 2]); i += 2; continue
            if ch == "'":
                in_str = False
            else:
                field.append(ch)
            i += 1; continue
        if ch == "'":
            in_str = True; i += 1; continue
        if ch == '(':
            depth += 1
            if depth == 1:
                cur, field = [], []
                i += 1; continue
        elif ch == ')':
            depth -= 1
            if depth == 0:
                cur.append(''.join(field)); rows.append(cur)
                cur, field = [], []
                i += 1; continue
        elif ch == ',' and depth == 1:
            cur.append(''.join(field)); field = []
            i += 1; continue
        if depth == 1:
            field.append(ch)
        i += 1
    return rows


def rows(stmts, table, default_cols=None):
    """Column-mapped rows for `insert into <table>`.

    NB: these dumps carry an EXPLICIT and REORDERED column list —
    postmeta is (meta_id, meta_key, meta_value, post_id). Always honour it.
    """
    pat = re.compile(r'^\s*insert into\s+`?@@TABLE_PREFIX@@' + table +
                     r'`?\s*(\([^)]*\))?\s*values\s*', re.I | re.S)
    out, cols = [], default_cols
    for s in stmts:
        m = pat.match(s)
        if not m:
            continue
        if m.group(1):
            cols = [c.strip(' `') for c in m.group(1).strip('()').split(',')]
        tail = s[m.end():]
        if not tail.startswith('('):
            tail = s[s.index('(', m.end() - 1):]
        for r in _split_values(tail):
            out.append(dict(zip(cols, [_unesc(v) for v in r])))
    return out


POSTS_COLS = ['ID', 'post_author', 'post_date', 'post_date_gmt', 'post_content',
              'post_title', 'post_excerpt', 'post_status', 'comment_status',
              'ping_status', 'post_password', 'post_name', 'to_ping', 'pinged',
              'post_modified', 'post_modified_gmt', 'post_content_filtered',
              'post_parent', 'guid', 'menu_order', 'post_type', 'post_mime_type',
              'comment_count']


def options(st):
    return {r['option_name']: r['option_value']
            for r in rows(st, 'options', ['option_id', 'option_name', 'option_value', 'autoload'])}


def posts(st):
    return rows(st, 'posts', POSTS_COLS)


def php_unserialize(s):
    r = subprocess.run(
        ['php', '-r', '$d=unserialize(file_get_contents("php://stdin"));'
                      'echo json_encode($d, JSON_UNESCAPED_SLASHES|JSON_UNESCAPED_UNICODE);'],
        input=s, capture_output=True, text=True)
    if r.returncode != 0 or not r.stdout:
        sys.exit('php unserialize failed — is php on PATH?')
    return json.loads(r.stdout)


# --- YOOtheme structures ----------------------------------------------------

LAYOUT_RE = re.compile(r'<!--\s?(\{.*\})\s?-->', re.S)   # PostHelper::PATTERN


def layout_of(post_content):
    """The builder layout embedded in a post_content, or None."""
    if not post_content:
        return None
    m = LAYOUT_RE.search(post_content)
    try:
        return json.loads(m.group(1)) if m else None
    except json.JSONDecodeError:
        return None


def yoo_config(st):
    """theme_mods_yootheme -> config (already JSON-decoded)."""
    mods = php_unserialize(options(st)['theme_mods_yootheme'])
    cfg = mods.get('config')
    cfg = json.loads(cfg) if isinstance(cfg, str) else (cfg or {})
    cfg['_nav_menu_locations'] = mods.get('nav_menu_locations')
    return cfg


def yoo_templates(st):
    """The `yootheme` option -> {id: template}."""
    return (json.loads(options(st).get('yootheme') or '{}')).get('templates', {})


def walk(node):
    if isinstance(node, dict):
        yield node
        for ch in node.get('children') or []:
            yield from walk(ch)
    elif isinstance(node, list):
        for ch in node:
            yield from walk(ch)


def builder_widgets(st):
    """[(position, widget_id, title, layout)] — builder layouts placed in
    widget positions (navbar, header, dialog-mobile, bottom, builder-1…6, …)."""
    o = options(st)
    widgets = php_unserialize(o.get('widget_builderwidget') or 'a:0:{}') or {}
    sidebars = php_unserialize(o.get('sidebars_widgets') or 'a:0:{}') or {}
    where = {}
    for position, ids in (sidebars.items() if isinstance(sidebars, dict) else []):
        for wid in (ids or []):
            if isinstance(wid, str) and wid.startswith('builderwidget-'):
                where[wid.split('-', 1)[1]] = position
    out = []
    for k, v in (widgets.items() if isinstance(widgets, dict) else []):
        if isinstance(v, dict) and v.get('content'):
            out.append((where.get(str(k), 'unplaced'), k, v.get('title'), v['content']))
    return out


def all_trees(st):
    """Every builder tree in the site: pages, templates, footer, mega menus,
    and Builder widgets."""
    out = []
    for p in posts(st):
        lay = layout_of(p.get('post_content'))
        if lay:
            out.append((f"page:{p['post_name'] or p['ID']}", lay))
    for tid, t in yoo_templates(st).items():
        # a template's `layout` is ALREADY a {"type":"layout","children":[…]} object,
        # the same root shape as a page — do NOT wrap it again (Builder::load()
        # rejects anything that isn't an object, which is the giveaway).
        if t.get('layout'):
            out.append((f"template:{t.get('name')}", t['layout']))
    cfg = yoo_config(st)
    if (cfg.get('footer') or {}).get('content'):
        out.append(('footer', cfg['footer']['content']))
    for mid, v in ((cfg.get('menu') or {}).get('items') or {}).items():
        if isinstance(v.get('content'), dict):
            out.append((f'menu-item:{mid}', v['content']))
    for position, wid, title, layout in builder_widgets(st):
        out.append((f'widget:{position}:{title}', layout))
    return out


def menus(st):
    terms = {t['term_id']: t for t in rows(st, 'terms', ['term_id', 'name', 'slug', 'term_group'])}
    tt = {t['term_taxonomy_id']: t for t in
          rows(st, 'term_taxonomy', ['term_taxonomy_id', 'term_id', 'taxonomy',
                                     'description', 'parent', 'count'])
          if t['taxonomy'] == 'nav_menu'}
    ps = {p['ID']: p for p in posts(st)}
    meta = collections.defaultdict(dict)
    for m in rows(st, 'postmeta', ['meta_id', 'post_id', 'meta_key', 'meta_value']):
        meta[m['post_id']][m['meta_key']] = m['meta_value']
    out = collections.defaultdict(list)
    for r in rows(st, 'term_relationships', ['object_id', 'term_taxonomy_id', 'term_order']):
        t = tt.get(r['term_taxonomy_id'])
        p = ps.get(r['object_id'])
        if not t or not p or p['post_type'] != 'nav_menu_item':
            continue
        out[terms[t['term_id']]['name']].append({
            'id': p['ID'], 'order': int(p['menu_order'] or 0),
            'title': p['post_title'],
            **{k.replace('_menu_item_', ''): v for k, v in meta[p['ID']].items()
               if k.startswith('_menu_item_')}})
    return {k: sorted(v, key=lambda x: x['order']) for k, v in out.items()}


# --- commands ---------------------------------------------------------------

def cmd_summary(st):
    ps = posts(st)
    c = collections.Counter(p['post_type'] for p in ps)
    cfg, tpls = yoo_config(st), yoo_templates(st)
    print(f"style          : {cfg.get('style')}   (theme {cfg.get('version')})")
    print(f"pages / posts  : {c['page']} / {c['post']}")
    print(f"templates      : {len(tpls)}")
    print(f"menus          : {len(menus(st))}")
    print(f"footer layout  : {'yes' if (cfg.get('footer') or {}).get('content') else 'no'}")
    cpts = sorted(k for k in c if k not in
                  ('attachment', 'post', 'page', 'nav_menu_item', 'revision')
                  and not k.startswith('acf-'))
    print(f"CPTs           : {', '.join(cpts) or '-'}")
    print(f"ACF objects    : {c['acf-post-type']} post types, {c['acf-taxonomy']} taxonomies, "
          f"{c['acf-field-group']} groups, {c['acf-field']} fields")
    print(f"customizer LESS: less={cfg.get('less')} custom_less={len(cfg.get('custom_less') or '')} chars")


def cmd_templates(st):
    for tid, t in yoo_templates(st).items():
        print(f"[{tid}] {t.get('type',''):<24} status={t.get('status','') or '-':<9} "
              f"{str(t.get('name'))[:36]:<38} query={json.dumps(t.get('query'))}"
              + (f"  params={json.dumps(t['params'])}" if t.get('params') else ''))
    print('\n# match() takes the FIRST hit in this order; a template with an empty '
          'query is the catch-all and must come last.')


def cmd_menus(st):
    cfg = yoo_config(st)
    for name, items in menus(st).items():
        print(f'MENU "{name}" ({len(items)} items)')
        for it in items:
            print(f"   {it['order']:>3}. {it.get('title') or '(post title)':<28} "
                  f"type={it.get('type')} object={it.get('object')} parent={it.get('menu_item_parent')}")
    print('\nnav_menu_locations:', json.dumps(cfg.get('_nav_menu_locations')))
    print('menu.positions   :', json.dumps({k: v for k, v in (cfg.get('menu') or {}).get('positions', {}).items()
                                            if v.get('menu') not in ('', None)}))
    mega = [m for m, v in ((cfg.get('menu') or {}).get('items') or {}).items()
            if isinstance(v.get('content'), dict)]
    print('mega-menu items  :', mega or 'none')
    print('\nBuilder widgets (arbitrary layouts placed in positions):')
    for position, wid, title, _ in builder_widgets(st):
        print(f'   {position:<16} builderwidget-{wid}  {title!r}')
    print('\nheader           :', json.dumps({k: v for k, v in (cfg.get('header') or {}).items()
                                              if k in ('layout', 'width', 'transparent', 'search', 'social')}))
    print('dialog           :', json.dumps({k: v for k, v in (cfg.get('dialog') or {}).items()
                                            if k in ('layout', 'toggle')}))
    mh = (cfg.get('mobile') or {})
    print('mobile.breakpoint:', mh.get('breakpoint'))
    print('mobile.header    :', json.dumps({k: v for k, v in (mh.get('header') or {}).items()
                                            if k in ('layout', 'search', 'social', 'transparent')}))
    print('mobile.dialog    :', json.dumps({k: v for k, v in (mh.get('dialog') or {}).items()
                                            if k in ('layout', 'toggle')}))


def cmd_settings(st):
    """The Layout + Settings panels, flattened. See references/yootheme-customizer.md."""
    cfg = yoo_config(st)

    def flat(d, prefix=''):
        for k, v in (d or {}).items():
            key = f'{prefix}{k}'
            if isinstance(v, dict) and k not in ('content',):
                yield from flat(v, key + '.')
            elif not isinstance(v, (list, dict)) or not v:
                yield key, v

    groups = [('site', ['logo', 'site']),
              ('header', ['header', 'navbar', 'dialog']),
              ('mobile', ['mobile']),
              ('top / bottom', ['top', 'bottom']),
              ('sidebar', ['main_sidebar', 'sidebar']),
              ('post / blog', ['post', 'blog']),
              ('settings', ['webp', 'avif', 'bootstrap', 'fontawesome', 'highlight',
                            'media_folder', 'disable_wpautop', 'consent', 'scripts',
                            'style', 'less', 'custom_less', 'custom', 'version',
                            'yootheme_apikey'])]
    for title, keys in groups:
        print(f'\n##### {title}')
        for k in keys:
            if k not in cfg:
                continue
            v = cfg[k]
            if isinstance(v, dict):
                for kk, vv in flat(v, f'{k}.'):
                    print(f'  {kk:<46} {json.dumps(vv)}')
            else:
                print(f'  {k:<46} {json.dumps(v)[:80]}')


def cmd_census(st):
    types = collections.Counter()
    props = collections.defaultdict(collections.Counter)
    bound = 0
    for _, tree in all_trees(st):
        for n in walk(tree):
            t = n.get('type')
            if not t:
                continue
            types[t] += 1
            if 'source' in n:
                bound += 1
            for k, v in (n.get('props') or {}).items():
                if isinstance(v, (str, bool, int, float)):
                    props[t][f'{k} = {v}'] += 1
    print(f'# {sum(types.values())} nodes, {bound} with a dynamic-content binding\n')
    for t, n in types.most_common():
        print(f'{n:>5}  {t}')


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    st = json.load(open(sys.argv[1]))
    cmd, arg = sys.argv[2], (sys.argv[3] if len(sys.argv) > 3 else None)
    if cmd == 'summary':
        cmd_summary(st)
    elif cmd == 'config':
        print(json.dumps(yoo_config(st), indent=2, ensure_ascii=False))
    elif cmd == 'templates':
        cmd_templates(st)
    elif cmd == 'menus':
        cmd_menus(st)
    elif cmd == 'settings':
        cmd_settings(st)
    elif cmd == 'census':
        cmd_census(st)
    elif cmd == 'footer':
        print(json.dumps((yoo_config(st).get('footer') or {}).get('content'), indent=2, ensure_ascii=False))
    elif cmd == 'layout':
        for p in posts(st):
            if p['post_name'] == arg or p['ID'] == arg:
                print(json.dumps(layout_of(p['post_content']), indent=2, ensure_ascii=False))
                return
        sys.exit(f'no post named {arg!r}')
    elif cmd == 'pages':
        for p in posts(st):
            if p['post_type'] in ('page', 'post'):
                print(f"{p['ID']:>6}  {p['post_type']:<5} {p['post_name'][:44]:<46} "
                      f"{'builder' if layout_of(p['post_content']) else '-'}")
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    # `… | head` / `| jq` should exit quietly, not raise BrokenPipeError
    try:
        import signal
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    except (ImportError, AttributeError, ValueError):
        pass
    main()
