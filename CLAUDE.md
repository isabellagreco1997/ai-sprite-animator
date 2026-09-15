# Instructions for AI agents working in this repo

You are turning a short AI generated video of a pixel art character into a sprite sheet. Follow this order and do not skip the gate.

1. **Intake first, always.** Run `python3 scripts/intake.py <clip.mp4> work/<name>` and show the user the scorecard and the contact sheet before doing anything else. Explain every flag in one line: what it is, why it matters, what fixes it (a prompt change, a regeneration, or a pipeline option). Then ask: proceed as is, proceed with fixes, or regenerate with the corrected prompt from `docs/prompts.md`.
2. **Green screen is the expected input.** If the background is white or black, warn that character parts sharing that colour (eye whites, pupils, dark clothes, gaps between limbs) cannot be separated reliably, offer the green screen prompt, and only use `scripts/key_white.py` if the user insists.
3. **Run the pipeline.** `python3 scripts/pipeline_green.py work/<name> <name>`. It keys, finds the walk cycle, reconstructs every frame with pixel-art-fixer at one cell size, removes edge specks and packages frames, sheets, JSON and a loop GIF.
4. **Check on magenta before showing anything.** Open `out/all_frames_magenta.png`. Look for stray islands, missing parts (hands, eye whites, a dress), filled gaps, background coloured rims. Fix the key, never the sprite.
5. **Offer, do not assume.** These are options the user must ask for: the cell size comparison (`scripts/grid_compare.py`), the keep one drop two cut at 8 fps, palette reduction, and head or face stabilisation (`scripts/stabilize_head.py`). The faithful all frame build is the deliverable. Stabilisation pastes pixels between frames and can leave seams; say so when you offer it.
6. **Report honestly.** State what was verified (frame count, sprite size, cell, cycle range, islands, green cells left) and what was not (engine testing). If something in the source is wrong (shimmering hair from gradients, a 4 px bob that rounds to whole cells), say it is in the video and offer the prompt fix.

Never: fill holes blindly on a black background, reopen pockets without a colour gate, lock or vote colours across frames by default, judge output on a dark preview, or reuse keyed frames from an earlier run after the cycle range changes.

Requirements: `pip install -r requirements.txt` and `git clone https://github.com/Retro-Diffusion/pixel-art-fixer ~/Projects/pixel-art-fixer` (or set `PIXELFIXER` to its `python/` folder).
