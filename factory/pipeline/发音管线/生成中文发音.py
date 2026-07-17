#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
词境 · 批量预生成中文释义发音（zh 字段）

用法：
  python3 生成中文发音.py --dry-run          # 只提取+统计，不合成，验证数据健康度
  python3 生成中文发音.py --limit 3           # 只生成前 3 个缺失的，试听样本用
  python3 生成中文发音.py                     # 全量增量跑（已存在的自动跳过）
  python3 生成中文发音.py --edge-tts-bin 路径  # 显式指定 edge-tts 可执行文件

做的事：
  1. 从同目录 词境.html 里提取所有 (en, zh) 对——按 "{...}" 词条对象逐个切开再在
     对象内部找 en:"..." 和 zh:"..."，确保两者来自同一个词条，不会跨对象串词
     （词条对象内部不嵌套花括号，用 [^{}]* 隔离是安全的，见验证记录）
  2. 按 en 的 slug 去重（slug 规则须与 词境.html 里 JS 版 slugify() / 词境目录
     生成发音.py 里的 Python 版完全一致）；同一 slug 撞到不同 zh 文本时打警告，
     取首次出现的
  3. 调本地 edge-tts CLI（微软云端神经声线）合成 mp3，输出到
     sounds/<en-slug>_zh.mp3 —— 用 en 的 slug 因为中文没法直接 slug
  4. 已存在且 >0 字节的文件直接跳过，可重跑增量补词

声线：顶部常量 VOICE，试听后按需改这里。中文单词/短语本来就短，不传 --rate，
不减速（对比 生成发音.py 里的英文单词发音，同样不减速（同款做法）
里句子才减速）。

edge-tts 可执行文件按序解析：--edge-tts-bin 参数 → 环境变量 EDGE_TTS_BIN →
PATH（which edge-tts）→ 本机 fallback（改成你的 edge-tts 路径）。
显式指定（参数/环境变量）无效时直接报错退出，不静默降级到下一级——避免用错声线
库还不知道。

已知坑：
  - html 里词条对象都是单行 `{ en:"...", ipa:"...", zh:"...", note:"..." }`，
    en/zh 之间没有嵌套花括号，也没有转义引号——提取正则按此假设写，若未来数据
    格式变化（多行 / 嵌套 / 转义引号）需要重新审视 extract_pairs()
  - edge-tts 调的是微软云端 API，需要联网；单条 60s 超时，网络抖动会导致失败，
    重跑一次通常能补上（已存在跳过，不会重复计费/重复生成）

这个脚本只用标准库；edge-tts 是外部 CLI 子进程，不 import 任何 edge-tts 的
Python 包。
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------
# 顶部常量：声线，试听后按需改这里
# ---------------------------------------------------------------
VOICE = "zh-CN-XiaoxiaoNeural"

# 维护者本机 fallback：仅当 参数 / EDGE_TTS_BIN / PATH 三级都未命中时才使用。
FALLBACK_EDGE_TTS_BIN = Path("~/edge-tts/venv/bin/edge-tts").expanduser()
EDGE_TTS_TIMEOUT = 60  # 秒，单条合成的网络调用超时

HERE = Path(__file__).resolve().parent
HTML_PATH = HERE / "词境.html"
SOUNDS_DIR = HERE / "sounds"

# 词条对象内部的字段模式（不嵌套花括号，验证过：{ 与 } 计数在全文里配平）
ENTRY_RE = re.compile(r"\{[^{}]*\}")
EN_RE = re.compile(r'en:"((?:[^"\\]|\\.)*)"')
ZH_RE = re.compile(r'zh:"((?:[^"\\]|\\.)*)"')


def slugify(word):
    """与 词境.html 里 JS 版 slug() / 生成发音.py 里 Python 版规则必须完全一致：
    小写 -> 非 [a-z0-9] 全部替换为 _ -> 连续 _ 合并 -> 去首尾 _
    """
    s = word.lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s)
    s = s.strip("_")
    return s


def _unescape(s):
    return s.encode().decode("unicode_escape") if "\\" in s else s


def extract_pairs(html_text):
    """提取全部 (en, zh) 对：先按 {...} 切出每个词条对象（对象内不嵌套花括号，
    这样切不会跨词条串词），再在对象内部分别找 en:"..." 和 zh:"..."。
    只有对象内同时有 en 和 zh 才收录。返回 list[(en, zh)]，保留原始出现顺序。
    """
    pairs = []
    skipped_no_zh = 0
    for m in ENTRY_RE.finditer(html_text):
        block = m.group(0)
        en_m = EN_RE.search(block)
        if not en_m:
            continue
        zh_m = ZH_RE.search(block)
        if not zh_m:
            skipped_no_zh += 1
            continue
        en = _unescape(en_m.group(1))
        zh = _unescape(zh_m.group(1))
        pairs.append((en, zh))
    if skipped_no_zh:
        print(f"[提示] {skipped_no_zh} 个含 en 的对象没找到 zh 字段，已跳过")
    return pairs


def dedup_by_slug(pairs):
    """按 en 的 slug 去重，同一 slug 撞到不同 zh 文本时打警告、取首次出现的。
    返回 list[(en, zh, slug)]。
    """
    result = []
    slug_seen = {}  # slug -> (en, zh)  首次出现的
    collisions = []
    for en, zh in pairs:
        s = slugify(en)
        if s in slug_seen:
            prev_en, prev_zh = slug_seen[s]
            if prev_zh != zh:
                collisions.append((s, prev_en, prev_zh, en, zh))
            continue
        slug_seen[s] = (en, zh)
        result.append((en, zh, s))
    if collisions:
        print(f"警告：{len(collisions)} 处 slug 碰撞且 zh 文本不同（取首次出现的）：")
        for s, e1, z1, e2, z2 in collisions:
            print(f"  slug={s!r}：{e1!r}->{z1!r}（保留） vs {e2!r}->{z2!r}（丢弃）")
    return result


def _die_edge_tts_missing(detail):
    print(f"[错误] {detail}", file=sys.stderr)
    print(
        "安装：pip install edge-tts（任意 Python 环境均可）。\n"
        "已装在非 PATH 位置时，用环境变量 EDGE_TTS_BIN 或参数 --edge-tts-bin 指定可执行文件。",
        file=sys.stderr,
    )
    sys.exit(1)


def find_edge_tts_bin(arg_bin):
    """按序解析 edge-tts 可执行文件：--edge-tts-bin 参数 → 环境变量 EDGE_TTS_BIN →
    PATH（shutil.which）→ 维护者本机 fallback。显式指定（参数/环境变量）无效时
    直接报错，不静默降级到下一级。"""
    def usable(p):
        return p.exists() and os.access(str(p), os.X_OK)

    if arg_bin:
        candidate = arg_bin.expanduser().resolve()
        if usable(candidate):
            return candidate
        _die_edge_tts_missing(f"--edge-tts-bin 指定的 edge-tts 不可用：{candidate}")

    env_bin = os.environ.get("EDGE_TTS_BIN")
    if env_bin:
        candidate = Path(env_bin).expanduser().resolve()
        if usable(candidate):
            return candidate
        _die_edge_tts_missing(f"环境变量 EDGE_TTS_BIN 指定的 edge-tts 不可用：{candidate}")

    which_bin = shutil.which("edge-tts")
    if which_bin:
        return Path(which_bin)

    if usable(FALLBACK_EDGE_TTS_BIN):
        return FALLBACK_EDGE_TTS_BIN

    _die_edge_tts_missing("找不到 edge-tts 可执行文件（参数 / EDGE_TTS_BIN / PATH 均未命中）")


def _unlink_partial(target_path):
    """失败路径统一清掉可能写了一半的文件——半截 mp3 若 >0 字节会被下次增量跑
    误当成品跳过，必须删干净才能兑现"重跑补上"的承诺。"""
    try:
        target_path.unlink(missing_ok=True)
    except OSError:
        pass


def run_edge_tts(edge_tts_bin, text, voice, target_path):
    """调 edge-tts 生成音频到 target_path。成功返回 (True, None)；失败返回 (False, 错误信息)。"""
    cmd = [str(edge_tts_bin), "-t", text, "-v", voice, "--write-media", str(target_path)]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=EDGE_TTS_TIMEOUT
        )
    except subprocess.TimeoutExpired:
        _unlink_partial(target_path)
        return False, f"edge-tts 超时（>{EDGE_TTS_TIMEOUT}s）"
    except OSError as e:
        _unlink_partial(target_path)
        return False, f"无法执行 edge-tts：{e}"

    if result.returncode != 0:
        _unlink_partial(target_path)
        err = (result.stderr or result.stdout or f"退出码 {result.returncode}").strip()
        return False, err

    if not target_path.exists() or target_path.stat().st_size == 0:
        if target_path.exists():
            try:
                target_path.unlink()
            except OSError:
                pass
        return False, "生成后文件缺失或为空"

    return True, None


def main():
    parser = argparse.ArgumentParser(
        description="词境 · 从 词境.html 提取 zh 字段，批量生成中文发音（调 edge-tts）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="只提取+统计（对数/去重后数/slug 碰撞警告），不调用 edge-tts 合成",
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="只处理前 N 个待生成（跳过已存在的不计入 N），试听样本用",
    )
    parser.add_argument(
        "--edge-tts-bin", type=Path, default=None,
        help="edge-tts 可执行文件路径。缺省按序解析：环境变量 EDGE_TTS_BIN → PATH → 本机 fallback",
    )
    parser.add_argument(
        "--voice", default=VOICE,
        help=f"声线，默认 {VOICE}",
    )
    args = parser.parse_args()

    if not HTML_PATH.exists():
        print(f"[错误] 找不到 {HTML_PATH}", file=sys.stderr)
        sys.exit(1)

    html_text = HTML_PATH.read_text(encoding="utf-8")
    pairs = extract_pairs(html_text)
    zh_literal_count = len(re.findall(r'zh:"', html_text))

    print(f"提取到 (en, zh) 对：{len(pairs)}")
    print(f"html 中 zh:\" 出现次数：{zh_literal_count}")
    if abs(len(pairs) - zh_literal_count) > 5:
        print(
            f"警告：提取对数（{len(pairs)}）与 zh:\" 出现次数（{zh_literal_count}）"
            f"差距较大，请检查 extract_pairs() 是否漏配"
        )

    deduped = dedup_by_slug(pairs)
    print(f"按 en-slug 去重后：{len(deduped)} 条")

    if args.dry_run:
        print("\n[--dry-run] 仅提取统计，不合成。样例（前 5 条）：")
        for en, zh, s in deduped[:5]:
            print(f"  {en!r} -> {zh!r} -> sounds/{s}_zh.mp3")
        return

    edge_tts_bin = find_edge_tts_bin(args.edge_tts_bin)
    SOUNDS_DIR.mkdir(exist_ok=True)

    print(f"edge-tts：{edge_tts_bin}")
    print(f"声线：{args.voice}")
    print("-" * 60)

    stats = {"success": 0, "skip": 0, "fail": 0}
    fail_list = []
    processed_new = 0  # 本次实际尝试生成（未跳过）的计数，用于 --limit

    for en, zh, s in deduped:
        target_path = SOUNDS_DIR / f"{s}_zh.mp3"
        label = f"[{en!r} -> {zh!r}]"

        if target_path.exists() and target_path.stat().st_size > 0:
            stats["skip"] += 1
            continue

        if args.limit is not None and processed_new >= args.limit:
            break

        ok, err = run_edge_tts(edge_tts_bin, zh, args.voice, target_path)
        processed_new += 1
        if ok:
            stats["success"] += 1
            print(f"{label} -> sounds/{target_path.name} ... 生成成功")
        else:
            stats["fail"] += 1
            fail_list.append((en, zh, err))
            print(f"{label} -> sounds/{target_path.name} ... 失败：{err}", file=sys.stderr)

        total_done = stats["success"] + stats["fail"]
        if total_done % 20 == 0:
            print(f"进度（本次新处理）{total_done}")

    total = stats["success"] + stats["skip"] + stats["fail"]
    print("-" * 60)
    print(
        f"汇总：成功 {stats['success']} / 跳过 {stats['skip']} / 失败 {stats['fail']}"
        f"（共 {total} 条，全量 {len(deduped)} 条）"
    )
    if fail_list:
        print(f"\n{'=' * 60}")
        print(f"!!! 以下 {len(fail_list)} 条生成失败 !!!")
        print("=" * 60)
        for en, zh, err in fail_list:
            print(f"  - {en!r} ({zh!r}): {err}")
        sys.exit(1)


if __name__ == "__main__":
    main()
