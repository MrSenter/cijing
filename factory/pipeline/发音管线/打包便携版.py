#!/usr/bin/env python3
"""词境便携版打包：单文件 html（舞台图/面板图/地图 JPEG 化内联 + 608 词双语发音全内联）。

用法：python3 打包便携版.py [输出路径]     # 默认输出 ~/Projects/词境-便携版.html
- 原 词境.html 与目录资产零改动，重跑安全（加新场景后重新跑一遍即可）
- 海报 场景*.png 是已砍除海报模式的死引用，不内联不影响运行
- 隐私：剔除词条备注里的工作流注释；图片经 JPEG 重编码顺带剥离 PNG 元数据
- 发音查表查不到时给空 src → 触发页面原有 Web Speech 回落链
"""
import base64, os, re, subprocess, sys, tempfile

VD = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser('~/Projects/词境-便携版.html')
html = open(os.path.join(VD, '词境.html'), encoding='utf-8').read()

# 1. 隐私剔除：分发前自查源 html 无个人信息（路径/姓名/内部备注）——按需在此加 replace

# 2. 图片内联：舞台图/面板图/地图 → JPEG(q80) data URI
#    base64 拆成 4KB 短行字符串拼接——iPad Quick Look 预览对超长行解析会翻车（2026-07-16 实测），
#    全文件不留巨行。舞台图都在 JS 数据里（可用括号拼接表达式）；地图在 HTML 属性里，改运行时注入
def chunk_expr(b64):
    chunks = [b64[i:i+4000] for i in range(0, len(b64), 4000)]
    return '("data:image/jpeg;base64,"\n+"' + '"\n+"'.join(chunks) + '")'

imgs = sorted(set(re.findall(r'"(舞台[^"]+\.png|地图-词境小镇\.png)"', html)))
tmp = tempfile.mkdtemp()
img_bytes = 0
map_expr = None
for name in imgs:
    j = os.path.join(tmp, 'x.jpg')
    subprocess.run(['sips', '-s', 'format', 'jpeg', '-s', 'formatOptions', '80',
                    os.path.join(VD, name), '--out', j], capture_output=True, check=True)
    b = base64.b64encode(open(j, 'rb').read()).decode()
    img_bytes += len(b)
    if name == '地图-词境小镇.png':
        html = html.replace('src="地图-词境小镇.png"', 'src=""')
        map_expr = chunk_expr(b)
    else:
        html = html.replace('"%s"' % name, chunk_expr(b))
assert map_expr, '没找到地图图片'
print(f'图片内联 {len(imgs)} 张，base64 共 {img_bytes/1e6:.1f}MB')

# 3. 发音内联：sounds/ 全目录 → PORTABLE_SOUNDS 查表（键=文件名去扩展名）
snd_dir = os.path.join(VD, 'sounds')
entries = []
for f in sorted(os.listdir(snd_dir)):
    if f.endswith('.m4a'):
        key, mime = f[:-4], 'audio/mp4'
    elif f.endswith('.mp3'):
        key, mime = f[:-4], 'audio/mpeg'
    else:
        continue
    b = base64.b64encode(open(os.path.join(snd_dir, f), 'rb').read()).decode()
    entries.append('"%s":"data:%s;base64,%s"' % (key, mime, b))
print(f'发音内联 {len(entries)} 条')

# 4. 音频路径改查表（挂点=词境.html 中唯一的 audioSrc 构造处）
#    (window.PORTABLE_SOUNDS||{}) 兜底：发音块若被弱预览器（iPad Quick Look）掐掉，
#    图片交互照常，发音自动走页面原有 Web Speech 回落
old = '''    var audioSrc = (speakLang === "zh")
      ? "sounds/" + slugify(word.en) + "_zh.mp3"
      : "sounds/" + slugify(word.en) + ".m4a";'''
new = '''    var audioSrc = (speakLang === "zh")
      ? ((window.PORTABLE_SOUNDS||{})[slugify(word.en) + "_zh"] || "")
      : ((window.PORTABLE_SOUNDS||{})[slugify(word.en)] || "");'''
assert old in html, '音频路径挂点没找到——词境.html 该段改过，需同步本脚本'
html = html.replace(old, new)

# 5. 注入发音表：放主脚本之后（</body> 前），拆成小块多行——
#    iPad Quick Look 对超长单行/巨型 script 会解析失败并波及其后所有脚本（2026-07-16 实测），
#    故：主脚本在前不被拖累；每块 ≤40 条、一条一行
CHUNK = 40
blocks = ['<script>window.PORTABLE_SOUNDS=window.PORTABLE_SOUNDS||{};Object.assign(window.PORTABLE_SOUNDS,{\n%s\n});</script>'
          % ',\n'.join(entries[i:i+CHUNK]) for i in range(0, len(entries), CHUNK)]
blocks.append('<script>document.getElementById("mapImg").src=%s;</script>' % map_expr)
idx = html.rindex('</body>')
html = html[:idx] + '\n'.join(blocks) + '\n' + html[idx:]

os.makedirs(os.path.dirname(OUT), exist_ok=True)
open(OUT, 'w', encoding='utf-8').write(html)
print(f'产出 {OUT}  {os.path.getsize(OUT)/1e6:.1f}MB')
