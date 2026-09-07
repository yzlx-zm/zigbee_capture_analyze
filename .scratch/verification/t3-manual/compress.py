# 选用图 → 压缩输出 t3-manual/final/*.jpg (宽 <=1240, q82)
from PIL import Image
import os

PICKS = [
    ('import_main', 'import_main.jpg'),
    ('import_keys', 'import_keys.jpg'),
    ('import_split_panel', 'import_split_panel.jpg'),
    ('diag_detect', 'diag_detect2.jpg'),
    ('diag_hitcard', 'diag_hitcard.jpg'),
    ('diag_learn', 'diag_learn2.jpg'),
    ('topo_main', 'topo_main.jpg'),
    ('topo_legend', 'topo_legend.jpg'),
    ('timeline_main', 'timeline_main.jpg'),
    ('timeline_detail', 'timeline_detail.jpg'),
    ('nodes_main', 'nodes_main.jpg'),
    ('nodes_expand', 'nodes_expand2.jpg'),
    ('nodes_clusters', 'nodes_clusters.jpg'),
    ('nodes_example', 'nodes_example2.jpg'),
    ('ai_panel', 'ai_panel.jpg'),
    ('ai_config', 'ai_config.jpg'),
    ('ai_kb', 'ai_kb_result2.jpg'),
]
SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)))
DST = os.path.join(SRC, 'final')
os.makedirs(DST, exist_ok=True)
total = 0
for name, f in PICKS:
    im = Image.open(os.path.join(SRC, f)).convert('RGB')
    if im.width > 1240:
        im = im.resize((1240, int(im.height * 1240 / im.width)), Image.LANCZOS)
    out = os.path.join(DST, name + '.jpg')
    im.save(out, quality=82, optimize=True)
    kb = os.path.getsize(out) // 1024
    total += kb
    print(f'{name}: {im.size} {kb}KB')
print(f'TOTAL: {total}KB')
