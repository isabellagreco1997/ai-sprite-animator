# Prompts that worked (Grok, September 2026)

The three lines that matter for the pipeline are the flat green, "no green on the character", and "no shadow, no ground line". Keep them in every prompt.

## Character still

```
Pixel art sprite of a cute girl, retro 16-bit SNES style, side view facing right, full body, standing in a simple idle pose with feet flat on the ground. Short bob haircut, big expressive eyes, oversized hoodie and shorts, chunky sneakers. Clean readable silhouette, limited palette of about 16 colours, crisp dark outline around the whole character, flat colours, no anti-aliasing, no gradients, no glow. Generous empty margin around her. Solid flat pure green background #00FF00 filling the entire frame, absolutely no green on the character, no ground line, no shadow, no scenery, no text.
```

## Walk cycle

```
Animate this exact character walking in place, facing right, a full repeating walk cycle with both alternating steps, subtle body bob, hair swaying slightly. Keep her design, colours and pixel style identical. Fixed camera, fixed scale, full body always visible. Solid flat pure green background #00FF00 the whole time, nothing green on her, no ground line, no shadow, no scenery, no text. The last frame matches the first so it loops.
```

## Notes

- Ask for "chunky pixels, no gradients" if the intake reports a soft grid. Hair drawn with gradients shimmers after reconstruction.
- Ask for the same framing every time ("head to feet fills 60% of the frame height") if you want several characters at the same size. Same cell size does not mean same character size.
- If the character must have green on it (eyes, clothes), it is kept as long as it is enclosed and a different shade from the screen. Magenta `#FF00FF` works as a screen colour for green characters.
