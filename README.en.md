<div align="center">

[简体中文](README.md) · **English**

# 词境 · Cíjìng

**A point-and-read game for learning the English words for everyday things**

One scene, one world. Tap an object → its name, pronunciation & meaning. Like a grown-up's touch-to-read pen.

*"The things around you that you can't name."*

<br>

<img src="docs/screenshots/map.jpg" width="720" alt="Cíjìng town map">

<sub>A whole little town · tap any building to jump into that scene</sub>

<br><br>

### ▶️ [**Play online — no download, just click**](https://mrsenter.github.io/cijing/)

<sub>Or [download the single file](https://github.com/MrSenter/cijing/releases/latest) to play offline (one html, images & audio baked in) · phone/tablet below</sub>

</div>

---

> **This repo, two ways to use it** 👇
> - 🎮 **Just play** → [**play online**](https://mrsenter.github.io/cijing/) (one click) or [download the single file](https://github.com/MrSenter/cijing/releases/latest) to play offline
> - 🛠️ **Reproduce / add a scene / switch language** → see the [**`factory/` directory**](factory/) — the **full production workflow** (character & scene libraries, image task-books, visual auditing, audio pipeline, poster pipeline + all the specs)

## What is this

Cíjìng is a **scene-based, point-and-read English learning game**. Each image is an everyday scene (a kitchen, a car, a supermarket, an airport…), and every object in it is tappable — tap it and up pops its English name, phonetic spelling, Chinese meaning, and an example sentence, read aloud to you.

- **27 scenes · ~800 words**: from home (bedroom / kitchen / bathroom) to out and about (supermarket / café / clinic / airport / hotel) — a complete little city
- **Four modes**: EN+中 / English only / Chinese only / all hidden (turns into a "find the word" quiz)
- **A whole-town map**: tap a building to jump straight into its scene
- **Runs fully local**: open and play — no internet, no uploads, no ads, no tracking

<p align="center">
  <img src="docs/screenshots/car-driver.jpg" width="49%" alt="Car — driver's view">
  <img src="docs/screenshots/supermarket.jpg" width="49%" alt="Supermarket">
  <img src="docs/screenshots/airport.jpg" width="49%" alt="Airport">
  <img src="docs/screenshots/park.jpg" width="49%" alt="Park">
</p>

<sub>Tap an object → English + phonetics + Chinese + example sentence + audio. Above is the "both languages" mode; you can switch to English-only, Chinese-only, or hide-all to quiz yourself.</sub>

## Who it's for

- **Anyone who wants the real, everyday vocabulary** (students abroad, new immigrants, overseas Chinese — or learners at home filling the "words the textbook never taught" gap). You can discuss *economy* and *politics*, yet not know your home's *downspout*, the bathroom *vanity*, or a car's *mud flap*. Cíjìng follows real daily-life routines, so what you learn is what you'll **actually need next time** — it even covers the "stuck at the worst moment" scenes: seeing a doctor, dealing with utilities/renting, car maintenance.
- **Kids' English & parent-child learning** — the storybook art + tap-to-hear makes it great for pointing at things and learning names together. The content skews toward **everyday life**; kids will find the kitchen, bedroom, park, and supermarket easiest (the more technical scenes like car repair and plumbing are better with a grown-up).

## How to play

**Computer (Mac / Windows)**: download and double-click the single-file version, or open `index.html`.

**iPad / iPhone** (two ways):

> ⚠️ iOS caveat: after you copy the html into the Files app, **tapping it only previews — it won't launch the game** (Safari/Chrome don't even appear in "Open with" — an iOS limitation). Use one of these:

- **Option A · install Edge**: copy the file to your device → share from the Files app → open with **Edge** (Edge registers as a local-html handler, so it launches properly).
- **Option B · local network (no file transfer)**: run a local server on your computer, connect your phone/tablet to the same Wi-Fi (or the computer's hotspot), and open the link in a browser:
  ```bash
  # on your computer, inside the cijing folder:
  python3 -m http.server 8000
  # then on your phone/tablet, open: http://<computer-LAN-IP>:8000
  ```

**Controls**:
- **Tap an object** → hear it, see the word card
- **↑ ↓** change scene　**← →** pan between views within a scene (e.g. the car's four views; the airport's check-in → security → gate → baggage claim)
- Top bar: switch **EN+中 / English only / Chinese only / hide all**; "hide all" starts a **find-the-word quiz**
- Left **📖 index** grouped by 🏠home / 🚗transit / 🛒out; right **🗺 map** jumps by building
- Word labels are **semi-transparent by default and pop to the front when tapped**, so crowded scenes stay tappable

## Pronunciation

- **English audio** is bundled (local, [Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M) neural voice, Apache-2.0)
- **Chinese audio** is not bundled (see license note); tapping a word in Chinese falls back to your browser's built-in voice. To generate offline Chinese audio, see the audio pipeline in [`factory/pipeline/发音管线`](factory/pipeline/发音管线).

> **The pronunciation is AI-generated.** It's accurate the vast majority of the time, but a few words may have synthesis glitches. Cíjìng has run a round of machine-ear QA (whisper cross-check), but trust your own ears. To re-check/re-fix the audio yourself, the factory repo has a full **QA mode** (`发音质检.py`) — it needs an open-source speech-recognition model ([whisper.cpp](https://github.com/ggerganov/whisper.cpp)) to "grade" the audio.

## License

Cíjìng licenses **code** and **assets** separately:

| Part | License | What you can do |
|------|---------|-----------------|
| Code (`index.html` & app logic) | **MIT** | Use, modify, sell freely — just keep the copyright notice |
| Assets (illustrations / audio / vocabulary) | **CC BY-NC 4.0** | Learn, share, remix freely — **must credit "词境 / Cíjìng", no commercial use** |

Full terms: [`LICENSE`](LICENSE) (code) and [`LICENSE-assets.md`](LICENSE-assets.md) (assets).

> The cartoon characters are residents of the town of Cíjìng. Assets are non-commercial — please don't use the characters or scenes for profit.

## Still growing · build a town of your own

Cíjìng's everyday scenes are **far from complete** — a post office breakdown, a school, a hospital ward, a wet market, a hardware store… there's plenty left to add. It's a city that keeps growing, and you're welcome to add to it.

The whole production pipeline lives in this repo's [`factory/`](factory/) directory — but it can do more than "add a scene":

> **You can swap the map for your own town, and cast yourself (and the people you care about) as the main characters** — a point-and-read city that's entirely yours.

That's exactly what Cíjìng's two "libraries" are for — the **character library** keeps a fixed cast looking like the same people across every scene (so the protagonist can be *you*), and the **scene library** grows a town with a coherent spatial flow (so it's *your city*, not a pile of loose pictures). Switch languages, add a scene, or build a whole new city — it all starts in `factory/`.

---

<div align="center">
Made with ❤️ for people who'd rather play than memorize word lists
</div>
