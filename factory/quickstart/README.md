# Quickstart — build one playable scene in one command

The smallest possible taste of the 词境 pipeline: take **one wordless image + a small word list**, and produce **one self-contained, tap-to-read HTML** — no dependencies beyond Python 3.

```bash
python3 build_scene.py example/words.json example/scene.jpg -o output.html
# then open output.html in a browser and tap the objects
```

That's it. The included example is a post-office scene with 17 words. Open the result and:
- **tap any object** → its English name, phonetics, Chinese, and a spoken pronunciation (via the browser's Web Speech)
- toggle labels: **中英 / EN / 中 / hide**

## Make your own scene

1. Get a **wordless** image of a scene (draw it, photograph it, or generate one — see [`../templates/生图任务书模板.md`](../templates/生图任务书模板.md) for the "no text" image spec).
2. Write a `words.json` — each word is a label **plus a hotspot box** in percentage coordinates:

```json
{
  "sceneName": "The Post Office",
  "words": [
    { "en": "parcel",  "ipa": "/ˈpɑːrsl/", "zh": "包裹", "x": 42, "y": 30, "wd": 30, "ht": 17 },
    { "en": "stamp",   "ipa": "/stæmp/",   "zh": "邮票", "x": 80, "y": 32, "wd": 10, "ht": 12 }
  ]
}
```

`x, y` = top-left of the box, `wd, ht` = width/height — all as **percentages of the image** (0–100). `ipa` is optional.

3. Run the command. Done.

## What this is (and isn't)

This is a **minimal, honest slice** of the real engine — enough to see the core idea work: *the image stays wordless; the code overlays everything*.

The production version (in the repo root) adds: 27 scenes stitched into a town with a map, local neural pronunciation (not just Web Speech), multi-view scenes, drill-down panels, a find-the-word quiz, and a single-file packager. The full pipeline that generates all of that — image task-books, visual auditing, hotspot annotation, audio + poster pipelines — is the rest of [`../`](../).

> Note: hotspots here are hand-written. In the full pipeline they come from a vision model reading the image; either way they're just percentage boxes.
