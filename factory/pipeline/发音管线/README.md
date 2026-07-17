# 发音管线

词境的单词发音生成 + 机器验耳质检 + 便携版打包。发音文件名 slug 规则须与成品 `index.html` 的 JS `slug()` 一致。

## 脚本

| 脚本 | 干什么 |
|------|--------|
| `生成发音.py` | 英文发音：mlx-audio + Kokoro-82M（声线 af_heart）→ `sounds/<slug>.m4a`。可增量（已存在跳过）。含 SineGen 补丁 + 语速梯子（缺一个会批量合成失败，别删） |
| `生成中文发音.py` | 中文发音：edge-tts（微软云端晓晓声线）→ `sounds/<slug>_zh.mp3`。⚠️ 见下 |
| `发音质检.py` | whisper 对账机器验耳：`audit`（增量）/ `audit --all` / `repair`（三板斧修翻车词：语速网格 / 音素覆盖 / 载体短语切割） |
| `打包便携版.py` | 把 html + 图（JPEG 内联）+ 音频（base64 内联）打包成单文件 html，双击即用 |

## 用法

```bash
# 英文（需 Kokoro/mlx-audio venv）
<kokoro-venv>/bin/python 生成发音.py

# 中文（需 edge-tts，改脚本里的路径）
python3 生成中文发音.py

# 机器验耳（需 whisper.cpp）
<kokoro-venv>/bin/python 发音质检.py audit     # 抓可疑
<kokoro-venv>/bin/python 发音质检.py repair    # 修翻车

# 打包单文件便携版
python3 打包便携版.py 输出.html
```

## ⚠️ 中文发音与再分发

edge-tts 用微软 Edge 在线语音，**生成的 mp3 再分发有法律灰色**。官方成品仓不内置中文音频（走浏览器 Web Speech 兜底）。

想要"离线中文发音又干净"：把中文也用 Kokoro 中文声线（`zf_/zm_`，lang_code=z，Apache-2.0）生成——照 `生成发音.py` 改 `VOICE` 和 `LANG_CODE` 即可，产出改存 `_zh` 后缀。

## 已知坑

- Kokoro 的 mlx-audio 对**超短词**偶发确定性坍缩（tip→"see ya bye" 之流，实测翻车率 ~7%）——所以单词级 TTS **必须机器验耳后再用**，`发音质检.py repair` 那套三板斧就是修这个的
- whisper 判卷有同音/拼写偏好（brake↔break、seesaw↔"as he saw"），会误报——人耳抽测通道要保留
