# The Hibah Files: Case File 01 – Scene 2 multi-cam edit

`output/HibahFiles_CF01_Scene2_multicam.mp4`: 1920x1080, 30 fps, H.264 + AAC 320k, same length as the source.

Rebuild:

```
python3 tools/build.py SOURCE.mp4 OUT.mp4 FONT_DIR WORK_DIR
```

FONT_DIR must contain `Anton-Regular.ttf`, `Montserrat-Bold.ttf` and `Montserrat-SemiBold.ttf`.
Requires ffmpeg, numpy and Pillow.

- `tools/angles.py`: the simulated camera angles. Each one is a single projective warp (125% punch-in, ±3.5° tilt, 2% keystone), and the reframing is pushed as far as possible without exposing frame edges.
- `tools/build.py`: the edit decision list, the graphics (Pillow, piped as RGBA), the synthesized SFX and ambience bed, and the final render.
