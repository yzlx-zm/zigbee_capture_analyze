// 选用图 → 压缩输出 t3-manual/final/*.jpg (宽 ≤1240, q82)
import { mkdirSync } from 'fs';
const picks = [
  ['import_main', 'import_main.jpg'],
  ['import_keys', 'import_keys.jpg'],
  ['import_split_panel', 'import_split_panel.jpg'],
  ['diag_detect', 'diag_detect2.jpg'],
  ['diag_hitcard', 'diag_hitcard.jpg'],
  ['diag_learn', 'diag_learn2.jpg'],
  ['topo_main', 'topo_main.jpg'],
  ['topo_legend', 'topo_legend.jpg'],
  ['timeline_main', 'timeline_main.jpg'],
  ['timeline_detail', 'timeline_detail.jpg'],
  ['nodes_main', 'nodes_main.jpg'],
  ['nodes_expand', 'nodes_expand2.jpg'],
  ['nodes_clusters', 'nodes_clusters.jpg'],
  ['nodes_example', 'nodes_example2.jpg'],
  ['ai_panel', 'ai_panel.jpg'],
  ['ai_config', 'ai_config.jpg'],
  ['ai_kb', 'ai_kb_result2.jpg'],
];
mkdirSync('.scratch/verification/t3-manual/final', { recursive: true });
const { execSync } = await import('child_process');
const list = picks.map(([n, f]) => `${n} ${f}`).join('\n');
const py = `
from PIL import Image
import os
pairs = """${list}""".strip().split('\n')
src = '.scratch/verification/t3-manual/'
dst = src + 'final/'
for line in pairs:
    name, f = line.split()
    im = Image.open(src + f).convert('RGB')
    if im.width > 1240:
        im = im.resize((1240, int(im.height * 1240 / im.width)), Image.LANCZOS)
    im.save(dst + name + '.jpg', quality=82, optimize=True)
    print(name, im.size, os.path.getsize(dst + name + '.jpg') // 1024, 'KB')
`;
execSync('python -c "' + py.replace(/"/g, '\\"').replace(/\n/g, ' ') + '"', { stdio: 'inherit' });
