<div align="center">

**English** · [简体中文](README.zh.md)

# 词境 Factory · Cíjìng Factory

**The production line behind 词境** — the full toolkit and specs for turning "an idea for a scene" into "a tappable, point-and-read image."

Want to add a scene, switch languages, or **swap the map for your own town and cast yourself as the protagonist** — building a point-and-read city that's entirely yours? Start here.

</div>

> The playable product (the "just play it" one) is in the [repo root](https://github.com/MrSenter/cijing). This `factory/` directory is **how it's made**.
>
> 词境's everyday scenes are far from complete — it's a city meant to keep growing. You don't have to wait for it to be finished; take this workflow and build your own.

---

## The core idea: art layer and interaction layer, fully separated

The secret to "point-and-read" is one rule:

> **The stage image only ever draws a clean, wordless scene. Words, pronunciation, and translation are all overlaid by the code layer at runtime.**

Never bake text into the pixels. Once you do, it degrades into a poster — un-tappable, un-hideable, un-quizzable, un-editable. With the separation:

- **One image, many languages** — the art is generated once; a new language only swaps the word layer.
- **No hand-labeling** — a vision model reads the image and emits percentage-coordinate hotspots.
- **One hotspot set, four modes** — show both / English only / Chinese only / hide-all (a find-the-word quiz).

## The two "libraries": characters & scenes

Two libraries hold a coherent town together:

**🎭 Character library** — why the people look like the same people across scenes.
A fixed cast (a couple, a family, a dog) each has: (1) a written **appearance anchor** (hair / clothes / accessories pinned down in text) and (2) a **reference sheet**. When generating a new scene, the sheet goes in as an `image_gen` reference and the anchor text is copied into the task-book — **a double lock keeping characters consistent scene to scene.** Without it, the same person becomes two different people in the supermarket vs. the gas station. If a character is itself a vocabulary word (barista / bellhop…), the person *is* the hotspot.

**🏙 Scene library** — how a city grows.
Each **scene = one slide** (word list + hotspots + stage image + optional panels), grouped into **sections** (🏠home / 🚗transit / 🛒out). The key: **the order of the slides encodes a spatial route** through town (wake up → go downstairs → head out → hit the road → arrive), so ↑↓ = walking around the city; multi-view scenes (car / airport) share a `sceneId`, and ←→ pans between views. Adding a scene = adding one item to this library (structure in [`docs/场景数据格式.md`](docs/场景数据格式.md)). Scenes can also hold **portals** (tap a door/car in one scene to jump to another).

> In short: **the character library keeps *people* consistent across scenes; the scene library keeps the *city* spatially coherent.** These are why 词境 reads like a city, not a pile of loose pictures.

## The pipeline

```
① Word list       decide the tappable objects in a scene (new words, no dupes)
     ↓
② Image task-book → wordless stage image        templates/生图任务书模板.md
     ↓              (unified art spec + "no text" rule + physical-plausibility rule + char/decor consistency lock)
③ Visual audit     verify each word present, zero text, plausible construction   pipeline/审计员岗位.md
     ↓              (missing object → local inpaint fix, not a full redraw)
④ Hotspots         read the image, box each word in % coords            docs/场景数据格式.md
     ↓
⑤ Assemble slide   word list + hotspots + image → one entry in the slides array
     ↓
⑥ Audio            English via Kokoro / Chinese via edge-tts      pipeline/发音管线/
     ↓              (+ whisper machine-ear QA)
⑦ Test & pack      browser smoke-test → single-file build         pipeline/发音管线/打包便携版.py
     ↓
(optional) Poster pipeline: stage image + word list → labeled printable poster   pipeline/海报管线/
```

## Try it in one command

The smallest runnable slice — one wordless image + a tiny word list → one playable HTML — is in [`quickstart/`](quickstart/):

```bash
cd quickstart
python3 build_scene.py example/words.json example/scene.jpg -o output.html
# open output.html and tap the objects
```

## The task-card layer: talk → card → assign → review

Beyond the pipeline, 词境 drives each scene with a **task card** (the author uses **Notion**; any task tool works — Trello / Linear / a Markdown checklist). Per scene: **talk** it through (which words, what event, how many views), open a **card** with clear acceptance criteria, **assign** the work (image-gen agent, audit role, hotspotting), then **review** against the card. The card owns *scope / acceptance / handoff*; execution details follow the work object.

## Contents

| Path | What it is |
|------|-----------|
| `templates/生图任务书模板.md` | The task-book template for the image-gen agent (art spec / no-text / plausibility / local-inpaint) |
| `pipeline/审计员岗位.md` | The visual-audit role definition — per-word verification, two-tier (fatal text vs. note-level icons) |
| `pipeline/发音管线/` | English (Kokoro) + Chinese (edge-tts) audio generation + whisper QA + single-file packaging |
| `pipeline/海报管线/` | Stage image + word list → DOM layout → Playwright screenshot poster (zero spelling errors, free re-render) |
| `docs/场景数据格式.md` | slide / hotspot / panel / portal data structures + the full add-a-scene steps |
| `docs/开源前清洁清单.md` | Pre-open-source checklist for stripping personal info |
| `quickstart/` | One-command minimal single-scene demo |

## Dependencies

- **Image generation** — any `image_gen` agent (the author uses Codex CLI). You supply the model.
- **English TTS** — [Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M) + [mlx-audio](https://github.com/Blaizzy/mlx-audio) (Apache-2.0, redistributable).
- **Chinese TTS** — [edge-tts](https://github.com/rany2/edge-tts) (free, no key) — ⚠️ see below.
- **QA** — [whisper.cpp](https://github.com/ggerganov/whisper.cpp) (machine-ear, catches TTS failures).
- **Posters** — Node + Playwright.

## ⚠️ Honest limitations

- **This is a human-in-the-loop, multi-step workflow, not a one-click generator.** You direct each stage; auditing and hotspotting still need a human.
- **Bring your own image model** — no weights are shipped.
- **Chinese audio & redistribution**: English (Kokoro, Apache-2.0) is freely redistributable. **edge-tts uses Microsoft's online voices — bundling the generated mp3s is a legal gray area**, so the official build ships no Chinese audio (it falls back to the browser's Web Speech). For clean offline Chinese, regenerate with Kokoro's Chinese voices (`zf_/zm_`, also Apache-2.0).

## License

Code / scripts / docs are **MIT**; generated assets (images / audio / vocabulary) are **CC BY-NC 4.0** — see [`LICENSE`](../LICENSE) and [`LICENSE-assets.md`](../LICENSE-assets.md) in the repo root.
