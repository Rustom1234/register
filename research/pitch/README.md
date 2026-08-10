# Wayside — KXIC pitch deck

Pitch deck for the Kevin Xu Innovation Challenge, built from the Equitech
template sections. Renamed from the project's original working name
("Pukaar") to **Wayside** — the product itself has not been renamed yet;
see the root project's open thread on that.

| File | What it is |
|---|---|
| the demo film | **1:45, the whole loop on the real map.** Shot live by `pukaar/scripts/record_pitch_video.py`. It now lives at `pukaar/pukaar/static/wayside-demo.mp4` — not here — because that is what the Docker image copies, so the app can serve it at **`/film`**. Anywhere else and the link 404s in production |
| [wayside-kxic-pitch.pptx](./wayside-kxic-pitch.pptx) | The deck — 13 slides, dark throughout, expanded to match the long-form pitch |
| [wayside-kxic-pitch.md](./wayside-kxic-pitch.md) | The same pitch as plain text, in slide order — read this if you can't open the pptx |
| [build_deck.js](./build_deck.js) | Generates the pptx via [pptxgenjs](https://gitbrent.github.io/PptxGenJS/) |
| [assets/](./assets) | The six demo screenshots the deck embeds (header chrome cropped out) |

A longer, illustrated version of the same pitch — full prose instead of slide
fragments, six screenshots instead of two — exists as a self-contained web
page; ask in-session for a copy if you don't have the link.

To regenerate the deck:

```sh
npm install
node build_deck.js
```
