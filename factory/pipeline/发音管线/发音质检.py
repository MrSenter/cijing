#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
词境 · 单词发音质检与修复（whisper 机器验耳，抓 TTS 翻车词如 tip→"see ya bye"）

用法：
  <kokoro-venv>/bin/python 发音质检.py audit        # 增量对账：只查台账里没有/文件变过的词（每波新词秒级）
  <kokoro-venv>/bin/python 发音质检.py audit --all  # 全量对账：608+ 词全扫（约 15 分钟，大修用）
  <kokoro-venv>/bin/python 发音质检.py repair       # 按报告修复：语速网格→拼写/音素变体→载体切割，验过才覆盖并记台账

台账：发音质检台账.json（slug → 文件 mtime/size），验过且指纹没变的词跳过

背景与打法（全库大修实测 608 词、真翻车 44、修复 44/44）：
  - Kokoro-82M 对部分超短词确定性坍缩（tip→"see ya bye"、pot→"part"、couch→"cow"），
    换语速/大小写/标点救不了的，用【载体短语】让它在句子语境里正常发音，再按能量最大
    间隙切出目标段（如 "tip? tip." 取后段、"listen! pot." 取后段）
  - 个别词是 G2P 错误（cumin→"coming"），用 misaki 音素覆盖语法 [word](/音标/) 直接指定
  - whisper 判卷有拼写偏好（brake 永远写成 break），ACCEPT 白名单收同音拼写
  - 判卷模型 ~/.cache/whisper-cpp/ggml-medium.bin；报告写 发音质检报告.json（本目录）

新场景加词后的标准动作：跑 生成发音.py → 跑本脚本 audit → 有翻车就 repair → 仍失败的人工裁决。
"""
import sys, subprocess, tempfile, os, wave, struct, json, re, shutil
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import importlib
mod = importlib.import_module('生成发音')

MODEL_W = os.path.expanduser('~/.cache/whisper-cpp/ggml-medium.bin')
REPORT = HERE / '发音质检报告.json'
LEDGER = HERE / '发音质检台账.json'

def load_ledger():
    return json.loads(LEDGER.read_text(encoding='utf-8')) if LEDGER.exists() else {}

def ledger_key(m4a):
    st = m4a.stat()
    return {'mtime': int(st.st_mtime), 'size': st.st_size}

def mark_verified(slug, m4a, ledger=None):
    led = ledger if ledger is not None else load_ledger()
    led[slug] = ledger_key(m4a)
    LEDGER.write_text(json.dumps(led, ensure_ascii=False, indent=0), encoding='utf-8')
    return led

# 已知同音/近音可接受拼写（whisper 偏好），可随修复经验追加
ACCEPT_EXTRA = {
 "brake": ["break"], "cane": ["kane","cain","caine"], "can opener": ["ken opener","kan opener"],
 "cumin": ["kumin","cuman"], "hook": ["hooke"], "lawn": ["lon"], "lawn mower": ["lawnmower"],
 "peephole": ["peep hole","pee hole"], "pot": ["pott","paht"], "flour": ["flower"],
 "grater": ["greater"], "faucet": ["fawcett"], "shutters": ["shudders"], "wok": ["walk"],
 "tow hitch": ["toe hitch"], "tumbler": ["tumblr"], "siding": ["sighting"], "hoodie": ["hootie"],
 "utility pole": ["utility poll"], "utility sink": ["utility sync"],
 "window screen": ["windows screen"], "window switch": ["windows switch"],
 "clothesline": ["closeline"], "clothespin": ["clospin"], "duct tape": ["duxtape"],
 "crisper drawer": ["crispr drawer"], "eye chart": ["ichart"], "high chair": ["hi chair"],
 "key fob": ["keefob"], "a/c": ["ac"], "stirrer": ["sterrer"], "mayo": ["mayer"],
}
# 已知 G2P 需音素覆盖 / 拼写变体的词（修复时优先用）
TEXT_VARIANTS = {
 "cumin": ["[cumin](/kjˈumɪn/)"], "peephole": ["peep-hole"],
}
CARRIERS = ["{w}? {w}.", "okay. {w}.", "one, {w}.", "listen! {w}.", "number one. {w}."]
SPEEDS = [0.936, 0.9, 0.972, 0.864, 1.0, 0.85]

def norm(s):
    s = s.lower().strip(); s = re.sub(r"[^a-z0-9' -]", '', s)
    return re.sub(r'\s+', ' ', s).strip()

def hear(p):
    tmpw = tempfile.mktemp(suffix='.wav')
    subprocess.run(['afconvert','-f','WAVE','-d','LEI16@16000','-c','1',str(p),tmpw],check=True,capture_output=True)
    r = subprocess.run(['whisper-cli','-m',MODEL_W,'-l','en','-np','-nt',tmpw],capture_output=True,text=True)
    os.unlink(tmpw); return norm(r.stdout)

def acceptable(heard, word):
    a = heard.replace(' ','').replace('-','')
    cands = [norm(word)] + [norm(x) for x in ACCEPT_EXTRA.get(norm(word), [])]
    for c in cands:
        b = c.replace(' ','').replace('-','')
        if a == b or (b in a and len(a) <= len(b)+4):
            return True
    return False

def all_words():
    # 只取词条（en 后必跟 ipa 字段）；例句是 en/zh 无 ipa，排除
    html = (HERE / '词境.html').read_text(encoding='utf-8')
    return sorted(set(re.findall(r'en:"([^"]+)",\s*ipa:', html)))

def audit(full=False):
    words = all_words(); bad = []; ledger = load_ledger(); checked = 0
    for i, w in enumerate(words):
        slug = mod.slugify(w)
        m4a = HERE / 'sounds' / f'{slug}.m4a'
        if not m4a.exists():
            bad.append({'word': w, 'heard': '(缺文件)'}); continue
        if not full and ledger.get(slug) == ledger_key(m4a):
            continue  # 验过且指纹没变，跳过
        checked += 1
        h = hear(m4a)
        if acceptable(h, w):
            ledger = mark_verified(slug, m4a, ledger)
        else:
            bad.append({'word': w, 'heard': h})
        if checked % 50 == 0: print(f'已查 {checked}，可疑 {len(bad)}', flush=True)
    REPORT.write_text(json.dumps(bad, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'对账完成：库 {len(words)} 词，实查 {checked}，可疑 {len(bad)} → {REPORT}')

def cut_last(cm, tmp):
    full = str(tmp/'f.wav')
    subprocess.run(['afconvert','-f','WAVE','-d','LEI16@24000','-c','1',str(cm),full],check=True,capture_output=True)
    w = wave.open(full,'rb'); fr=w.getframerate(); n=w.getnframes()
    data = struct.unpack(f'<{n}h', w.readframes(n)); w.close()
    win = int(fr*0.02)
    rms = [sum(abs(x) for x in data[i:i+win])/win for i in range(0,n-win,win)]
    voiced = [i for i,v in enumerate(rms) if v>max(rms)*0.10]
    if not voiced: return None
    gaps = [(voiced[k+1]-voiced[k],k) for k in range(len(voiced)-1) if voiced[k+1]-voiced[k]>4]
    if not gaps: return None
    gaps.sort(reverse=True)
    cutpos = voiced[gaps[0][1]+1]
    t0 = max(0, cutpos*win-int(0.05*fr)); t1 = min(n,(voiced[-1]+1)*win+int(0.10*fr))
    cutw = str(tmp/'cut.wav')
    wo = wave.open(cutw,'wb'); wo.setnchannels(1); wo.setsampwidth(2); wo.setframerate(fr)
    wo.writeframes(struct.pack(f'<{t1-t0}h', *data[t0:t1])); wo.close()
    cand = tmp/'cand.m4a'; mod.wav_to_m4a(Path(cutw), cand); return cand

def repair():
    mod._patch_mlx_audio_sinegen()
    from mlx_audio.tts.utils import load_model
    from mlx_audio.tts.generate import generate_audio
    model = load_model('prince-canuma/Kokoro-82M')
    bad = json.loads(REPORT.read_text(encoding='utf-8'))
    results = []
    for item in bad:
        word = item['word']
        out = HERE / 'sounds' / f'{mod.slugify(word)}.m4a'
        fixed = None
        texts = [word] + TEXT_VARIANTS.get(norm(word), [])
        for text in texts:
            for speed in SPEEDS:
                tmp = Path(tempfile.mkdtemp()); cand = tmp/'c.m4a'
                try: mod.synth_kokoro(model, generate_audio, text, speed, cand, tmp)
                except Exception: continue
                if acceptable(hear(cand), word):
                    shutil.copy(cand, out); fixed = f'direct<{text}>@{speed}'; break
            if fixed: break
        if not fixed:
            for c in CARRIERS:
                tmp = Path(tempfile.mkdtemp()); cm = tmp/'c.m4a'
                try: mod.synth_kokoro(model, generate_audio, c.format(w=word), 0.9, cm, tmp)
                except Exception: continue
                cand = cut_last(cm, tmp)
                if cand and acceptable(hear(cand), word):
                    shutil.copy(cand, out); fixed = f'carrier<{c}>'; break
        if fixed:
            mark_verified(mod.slugify(word), out)
        results.append({'word': word, 'result': fixed or 'FAIL'})
        print(f"{word}: {fixed or 'FAIL(保留原文件，人工裁决)'}", flush=True)
    ok = sum(1 for r in results if r['result'] != 'FAIL')
    print(f'修复完成：{ok}/{len(results)}')

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'repair':
        repair()
    else:
        audit(full='--all' in sys.argv)
