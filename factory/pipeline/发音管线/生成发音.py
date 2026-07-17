#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
词境 · 批量预生成英文单词发音

用法：
  <kokoro-venv>/bin/python 生成发音.py

做的事：
  1. 从同目录 词境.html 里正则提取所有 en:"..." 单词，去重
  2. 用 mlx-audio + Kokoro-82M 合成 wav（用你自己的 Kokoro/mlx-audio venv）
  3. afconvert 转成 m4a（aac 64kbps），删掉中间 wav
  4. 输出到 sounds/<slug>.m4a，slug 规则须与 词境.html 里的 JS 版 slug() 完全一致

已知坑：mlx-audio 0.4.4 的 Kokoro istftnet 解码器里 SineGen 有个确定性 bug——
sine_waves（上采样路径，特定帧数会多出采样）和 uv（直接从 f0 算）长度不一致，
触发 ValueError: [broadcast_shapes] Shapes (...) cannot be broadcast。是否触发
由 (文本, 声线, 语速) 三元组确定性决定——同参数重试没用，必须变参数或修底层。
应对两层：
  1. _patch_mlx_audio_sinegen()：monkey-patch SineGen.__call__，把 sine_waves
     和 uv 裁到同长再合成，从根上修掉这个 bug（（同一套 SineGen 补丁思路））。
  2. 补丁万一没生效（导入路径变了等），退一步用语速梯子重试
     [0.9, 0.936, 0.864, 0.972]——帧数一变就绕开残余崩溃，每档只试一次。
  四档全失败就记入失败清单，宁缺毋滥——不再回落 macOS say，避免把不同音色的
  音频混进产出目录（历史上这样污染过 146 个文件）。html 侧有 Web Speech API
  兜底朗读，缺几个 m4a 不致命。

可重跑：已存在且 >0 字节的 m4a 直接跳过，增量补词直接再跑一遍即可。

500 词左右全量跑大约 15-25 分钟，建议后台跑：
  cd 词境目录
  nohup <kokoro-venv>/bin/python 生成发音.py > /tmp/tts_log.txt 2>&1 &
  tail -f /tmp/tts_log.txt
"""

import re
import subprocess
import sys
import tempfile
from pathlib import Path

# ---------------------------------------------------------------
# 顶部常量：声线 / 语速，试听后按需改这里
# ---------------------------------------------------------------
VOICE = "af_heart"
LANG_CODE = "a"
SPEED = 0.9
SPEED_LADDER = [SPEED, SPEED * 1.04, SPEED * 0.96, SPEED * 1.08]  # 每档试一次
MODEL_NAME = "mlx-community/Kokoro-82M-bf16"

HERE = Path(__file__).resolve().parent
HTML_PATH = HERE / "词境.html"
SOUNDS_DIR = HERE / "sounds"


def _patch_mlx_audio_sinegen():
    """修 mlx-audio 0.4.4 的底层 bug：SineGen 里 sine_waves（上采样路径，特定帧数会
    多出采样）和 uv（直接从 f0 算）长度不一致 → broadcast_shapes 崩溃。
    补丁：两者裁到同长再合成。幂等，失败不阻断（语速梯子仍兜底）。
    抄自 <你的 Kokoro TTS 脚本> 的 _patch_mlx_audio_sinegen()。"""
    try:
        import mlx.core as mx
        from mlx_audio.tts.models.kokoro import istftnet

        if getattr(istftnet.SineGen, "_ai_radio_patched", False):
            return

        def patched_call(self, f0):
            fn = f0 * mx.arange(1, self.harmonic_num + 2)[None, None, :]
            sine_waves = self._f02sine(fn) * self.sine_amp
            uv = self._f02uv(f0)
            n = min(sine_waves.shape[1], uv.shape[1])  # ← 对齐长度，原版没有这步
            sine_waves = sine_waves[:, :n, :]
            uv = uv[:, :n, :]
            noise_amp = uv * self.noise_std + (1 - uv) * self.sine_amp / 3
            noise = noise_amp * mx.random.normal(sine_waves.shape)
            sine_waves = sine_waves * uv + noise
            return sine_waves, uv, noise

        istftnet.SineGen.__call__ = patched_call
        istftnet.SineGen._ai_radio_patched = True
        print("SineGen 补丁已生效")
    except Exception as e:
        print(f"[提示] SineGen 补丁未生效（{e}），继续用语速梯子兜底")


def slugify(word):
    """与 词境.html 里 JS 版 slug() 规则必须完全一致：
    小写 -> 非 [a-z0-9] 全部替换为 _ -> 连续 _ 合并 -> 去首尾 _
    """
    s = word.lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s)
    s = s.strip("_")
    return s


def extract_words(html_text):
    """提取词条 en:"..."（后必跟 ipa: 字段——例句也是 en/zh 结构但无 ipa，特意不做读音，勿抓）"""
    raw = re.findall(r'en:"((?:[^"\\]|\\.)*)",\s*ipa:', html_text)
    # 处理 JS 转义（目前数据里没有用到，但做个兜底）
    unescaped = [w.encode().decode("unicode_escape") if "\\" in w else w for w in raw]
    seen_lower = set()
    words = []
    for w in unescaped:
        key = w.lower()
        if key in seen_lower:
            continue
        seen_lower.add(key)
        words.append(w)
    return words


def wav_to_m4a(wav_path, out_path):
    result = subprocess.run(
        ["afconvert", "-f", "m4af", "-d", "aac", "-b", "64000", str(wav_path), str(out_path)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"afconvert 失败: {result.stderr.strip()}")
    if not out_path.exists() or out_path.stat().st_size == 0:
        raise RuntimeError("m4a 未生成或为空")


def synth_kokoro(model, generate_audio, word, speed, out_path, tmp_dir):
    """用 Kokoro 以指定语速合成单词发音到 out_path（m4a）。失败抛异常。"""
    prefix = str(Path(tmp_dir) / "tts_tmp")
    generate_audio(
        text=word,
        model=model,
        voice=VOICE,
        lang_code=LANG_CODE,
        speed=speed,
        file_prefix=prefix,
        audio_format="wav",
        verbose=False,
    )
    wav_path = Path(prefix + "_000.wav")
    if not wav_path.exists():
        raise RuntimeError(f"未生成 wav：{wav_path}")
    try:
        wav_to_m4a(wav_path, out_path)
    finally:
        wav_path.unlink(missing_ok=True)


def synth_one(model, generate_audio, word, out_path, tmp_dir):
    """合成单词发音到 out_path（m4a）。按语速梯子逐档尝试（每档一次），
    全部失败直接抛异常——不回落任何其他引擎，宁缺毋滥。"""
    last_err = None
    for speed in SPEED_LADDER:
        try:
            synth_kokoro(model, generate_audio, word, speed, out_path, tmp_dir)
            return
        except Exception as e:
            last_err = e
    raise RuntimeError(f"语速梯子 {SPEED_LADDER} 全部失败，最后一次错误：{last_err}")


def main():
    if not HTML_PATH.exists():
        print(f"找不到 {HTML_PATH}")
        sys.exit(1)

    html_text = HTML_PATH.read_text(encoding="utf-8")
    words = extract_words(html_text)
    print(f"提取到 {len(words)} 个去重单词（sanity check：应在 400-600 之间）")
    if not (400 <= len(words) <= 600):
        print("警告：数量不在预期区间，请检查提取正则是否匹配到全部 en: 字段")

    SOUNDS_DIR.mkdir(exist_ok=True)

    # 计算 slug，检查是否有 slug 碰撞（不同词撞到同一个 slug）
    slug_map = {}
    collisions = []
    for w in words:
        s = slugify(w)
        if s in slug_map and slug_map[s] != w:
            collisions.append((w, slug_map[s], s))
        else:
            slug_map[s] = w
    if collisions:
        print("警告：以下单词 slug 冲突（请人工检查数据）：")
        for w1, w2, s in collisions:
            print(f"  {w1!r} vs {w2!r} -> {s}")

    todo = []
    skipped = 0
    for w in words:
        s = slugify(w)
        out_path = SOUNDS_DIR / f"{s}.m4a"
        if out_path.exists() and out_path.stat().st_size > 0:
            skipped += 1
            continue
        todo.append((w, s, out_path))

    print(f"待生成 {len(todo)} 个，已存在跳过 {skipped} 个")

    if not todo:
        print("没有需要生成的词，结束。")
        return

    print("加载模型 ...")
    from mlx_audio.tts.utils import load_model
    from mlx_audio.tts.generate import generate_audio

    _patch_mlx_audio_sinegen()
    model = load_model(MODEL_NAME)
    print("模型加载完成，开始合成")

    ok_list = []
    fail_list = []

    with tempfile.TemporaryDirectory() as tmp_dir:
        for i, (word, s, out_path) in enumerate(todo, 1):
            try:
                synth_one(model, generate_audio, word, out_path, tmp_dir)
                ok_list.append(word)
            except Exception as e:
                fail_list.append((word, str(e)))
                print(f"  [失败] {word!r}: {e}")

            if i % 20 == 0 or i == len(todo):
                print(f"进度 {i}/{len(todo)}")

    print("\n===== 完成 =====")
    print(f"成功 {len(ok_list)} 个，失败 {len(fail_list)} 个，跳过（已存在）{skipped} 个")
    if fail_list:
        print("\n" + "=" * 60)
        print(f"!!! 以下 {len(fail_list)} 个词语速梯子全部失败，未生成音频 !!!")
        print("=" * 60)
        for w, err in fail_list:
            print(f"  - {w}: {err}")


if __name__ == "__main__":
    main()
