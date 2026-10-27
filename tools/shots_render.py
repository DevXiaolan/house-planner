#!/usr/bin/env python3
"""批量渲染镜头：python3 -I tools/shots_render.py <project.json> <shots.json> <outdir>
把工程和镜头清单注入设计器页面的一个临时副本，用无头 Chrome 驱动 houseShot.renderAll()，
把每个镜头的结构图写到 <outdir>/<序号-id>/structure.png。首次运行需要联网（加载 three.js）。"""
import sys, os, json, re, html, base64, subprocess, tempfile

CHROME = os.environ.get('CHROME', '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
APP = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'house-planner_2.html')

def main(project_path, shots_path, outdir):
    project = json.load(open(project_path, encoding='utf8'))
    shots = json.load(open(shots_path, encoding='utf8'))
    shots = shots['shots'] if isinstance(shots, dict) else shots
    src = open(APP, encoding='utf8').read()
    inject = '<script>window.__HOUSE_PROJECT__=%s;window.__SHOTS__=%s;</script>\n' % (json.dumps(project), json.dumps(shots))
    driver = '''<script>
window.addEventListener('load', async ()=>{
  const out = document.createElement('pre'); out.id = 'shots-out'; document.body.appendChild(out);
  try{ out.textContent = JSON.stringify(await window.houseShot.renderAll(window.__SHOTS__)); }
  catch(e){ out.textContent = 'ERR ' + (e && e.message || e); }
});
</script></body>'''
    page = src.replace('<script type="importmap">', inject + '<script type="importmap">', 1).replace('</body>', driver, 1)
    with tempfile.TemporaryDirectory() as td:
        f = os.path.join(td, 'run.html'); open(f, 'w', encoding='utf8').write(page)
        r = subprocess.run([CHROME, '--headless=new', '--use-angle=swiftshader', '--enable-unsafe-swiftshader',
                            '--window-size=1600,1000', '--virtual-time-budget=%d' % (60000 + 30000 * len(shots)),
                            '--dump-dom', 'file://' + f], capture_output=True, text=True, timeout=300 + 120 * len(shots))
    m = re.search(r'<pre id="shots-out"[^>]*>(.*?)</pre>', r.stdout, re.S)
    if not m: sys.exit('没有拿到渲染结果（Chrome 没跑完？）\n' + r.stderr[-800:])
    body = html.unescape(m.group(1))
    if body.startswith('ERR'): sys.exit(body)
    os.makedirs(outdir, exist_ok=True)
    for i, item in enumerate(json.loads(body), 1):
        d = os.path.join(outdir, '%02d-%s' % (i, item['id'])); os.makedirs(d, exist_ok=True)
        open(os.path.join(d, 'structure.png'), 'wb').write(base64.b64decode(item['png'].split(',', 1)[1]))
        print('✓', d)

if __name__ == '__main__':
    if len(sys.argv) != 4: sys.exit(__doc__)
    main(*sys.argv[1:])
