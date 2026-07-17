#!/usr/bin/env python3
"""词境 quickstart — 一张无字场景图 + 一份词表 → 一个自包含、可点读的单场景 HTML。

用法：
    python3 build_scene.py example/words.json example/scene.jpg -o output.html
    # 然后浏览器打开 output.html，点画面里的物体听发音、看释义

这是词境交互引擎的最小可跑版：图片内联，热区叠加，点击出词卡 + Web Speech 朗读，
标签可显隐。生产版（27 场景、本地神经发音、多视角、面板、找词测验）见仓库根目录。

Build a self-contained, tap-to-read single scene from one wordless image + a word list.
No dependencies beyond Python 3's standard library.
"""
import argparse, base64, json, sys
from pathlib import Path

TEMPLATE = r"""<!doctype html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>__TITLE__ · 词境 quickstart</title>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{background:#e9e3d5;font-family:-apple-system,"PingFang SC",Georgia,serif;display:flex;flex-direction:column;align-items:center;padding:16px;gap:12px}
  h1{font-size:1rem;color:#7a4a2b;letter-spacing:.05em}
  .modes{display:flex;gap:2px;background:#f4efe4;border-radius:8px;padding:3px}
  .modes button{border:0;background:transparent;padding:6px 12px;border-radius:6px;font:inherit;font-size:.82rem;color:#8a7a60;cursor:pointer}
  .modes button.on{background:#e6d9bf;color:#5a3d22;font-weight:700}
  .stage{position:relative;max-width:100%;line-height:0;box-shadow:0 4px 18px rgba(0,0,0,.15);border-radius:6px;overflow:hidden}
  .stage img{max-width:100%;height:auto;display:block}
  .hs{position:absolute;border:2px solid transparent;border-radius:5px;cursor:pointer;transition:background .12s,border-color .12s}
  .hs:hover,.hs:focus{border-color:#e0a94f;background:rgba(224,169,79,.16);outline:0}
  .lbl{position:absolute;bottom:100%;left:50%;transform:translateX(-50%);margin-bottom:3px;
       background:#faf5e8;border:1px solid #d8c39a;border-radius:4px;padding:2px 6px;white-space:nowrap;
       text-align:center;line-height:1.25;box-shadow:0 2px 5px rgba(0,0,0,.12);opacity:.82;pointer-events:none}
  .hs:hover .lbl,.hs:focus .lbl{opacity:1;z-index:9}
  .lbl .en{display:block;font-weight:700;font-size:.66rem;color:#2b2b2b}
  .lbl .zh{display:block;font-size:.62rem;color:#8a4a2b}
  .card{width:min(560px,92vw);background:#faf5e8;border:1px solid #d8c39a;border-radius:10px;padding:12px 16px;min-height:56px;display:flex;align-items:baseline;gap:12px;flex-wrap:wrap}
  .card .en{font-size:1.25rem;font-weight:700;color:#2b2b2b}
  .card .ipa{color:#8a7a60}
  .card .zh{font-size:1.05rem;color:#7a4a2b}
  .card .hint{color:#a99;font-style:italic}
  .foot{font-size:.72rem;color:#a99}.foot a{color:#7a4a2b}
</style></head><body>
<h1>__TITLE__</h1>
<div class="modes" id="modes">
  <button data-m="both" class="on">中英</button><button data-m="en">EN</button>
  <button data-m="zh">中</button><button data-m="none">隐藏</button>
</div>
<div class="stage"><img id="img" src="__IMG__" alt="__TITLE__"><div id="layer"></div></div>
<div class="card" id="card"><span class="hint">点画面里的物体 · tap an object</span></div>
<div class="foot">用 <a href="https://github.com/MrSenter/cijing">词境 quickstart</a> 生成 · Web Speech 发音</div>
<script>
var WORDS=__WORDS__, mode="both", layer=document.getElementById("layer"), card=document.getElementById("card");
function speak(t,lang){try{speechSynthesis.cancel();var u=new SpeechSynthesisUtterance(t);u.lang=lang;u.rate=.9;speechSynthesis.speak(u);}catch(e){}}
function showCard(w){card.innerHTML='<span class="en">'+w.en+'</span>'+(w.ipa?'<span class="ipa">'+w.ipa+'</span>':'')+'<span class="zh">'+w.zh+'</span>';speak(w.en,"en-US");}
WORDS.forEach(function(w){
  var h=document.createElement("div");h.className="hs";h.tabIndex=0;
  h.style.left=w.x+"%";h.style.top=w.y+"%";h.style.width=w.wd+"%";h.style.height=w.ht+"%";
  var l=document.createElement("div");l.className="lbl";
  l.innerHTML='<span class="en">'+w.en+'</span><span class="zh">'+w.zh+'</span>';
  h.appendChild(l);
  h.addEventListener("click",function(){showCard(w);});
  h.addEventListener("keydown",function(e){if(e.key==="Enter"||e.key===" "){e.preventDefault();showCard(w);}});
  layer.appendChild(h);
});
function applyMode(){document.querySelectorAll(".lbl").forEach(function(l){
  var en=l.querySelector(".en"),zh=l.querySelector(".zh");
  l.style.display=mode==="none"?"none":"";
  en.style.display=(mode==="both"||mode==="en")?"":"none";
  zh.style.display=(mode==="both"||mode==="zh")?"":"none";});}
document.getElementById("modes").addEventListener("click",function(e){
  var b=e.target.closest("button");if(!b)return;
  mode=b.dataset.m;document.querySelectorAll("#modes button").forEach(function(x){x.classList.toggle("on",x===b);});applyMode();});
applyMode();
</script></body></html>"""

def main():
    ap = argparse.ArgumentParser(description="Build a tap-to-read single scene from an image + word list.")
    ap.add_argument("words", help="words.json (see example/words.json)")
    ap.add_argument("image", help="wordless scene image (jpg/png)")
    ap.add_argument("-o", "--out", default="output.html", help="output html (default: output.html)")
    a = ap.parse_args()

    data = json.loads(Path(a.words).read_text(encoding="utf-8"))
    words = data.get("words", data if isinstance(data, list) else [])
    for i, w in enumerate(words):
        for k in ("en", "zh", "x", "y", "wd", "ht"):
            if k not in w:
                sys.exit(f"word #{i} ({w.get('en','?')}) missing '{k}'. Each word needs en/zh/x/y/wd/ht (x,y,wd,ht in %).")
        w.setdefault("ipa", "")

    img_bytes = Path(a.image).read_bytes()
    mime = "image/png" if a.image.lower().endswith(".png") else "image/jpeg"
    img_uri = f"data:{mime};base64," + base64.b64encode(img_bytes).decode()
    title = data.get("sceneName", "Scene") if isinstance(data, dict) else "Scene"

    html = (TEMPLATE
            .replace("__TITLE__", title)
            .replace("__IMG__", img_uri)
            .replace("__WORDS__", json.dumps(words, ensure_ascii=False)))
    Path(a.out).write_text(html, encoding="utf-8")
    print(f"✅ {a.out}  ({len(words)} words, {len(html)//1024} KB) — open it in a browser and tap the objects.")

if __name__ == "__main__":
    main()
