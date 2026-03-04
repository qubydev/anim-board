import base64
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Generator
from PIL import Image
import io

# ── Global export settings ────────────────────────────────────────────────────
WIDTH         = 1920
HEIGHT        = 1080
FPS           = 25           # zoompan works best at 25fps
VIDEO_CODEC   = "libx264"
AUDIO_CODEC   = "aac"
AUDIO_BITRATE = "128k"
CRF           = 23
PRESET        = "ultrafast"
JPEG_QUALITY  = 95
ZOOM_PER_SEC  = 0.01         # zoom change per second — e.g. 0.04 = 4%/s
                              # set to 0.0 to disable Ken Burns effect
# ─────────────────────────────────────────────────────────────────────────────


def _parse_timestamp(ts: str) -> float:
    ts = ts.replace(',', '.')
    h, m, s = ts.split(':')
    return float(h) * 3600 + float(m) * 60 + float(s)


def _fit_image(pil_img: Image.Image) -> Image.Image:
    """Cover-fit: fill WIDTH×HEIGHT, crop overflow from centre."""
    img_w, img_h = pil_img.size
    scale = max(WIDTH / img_w, HEIGHT / img_h)
    new_w, new_h = int(img_w * scale), int(img_h * scale)
    resized = pil_img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - WIDTH)  // 2
    top  = (new_h - HEIGHT) // 2
    return resized.crop((left, top, left + WIDTH, top + HEIGHT))


def _compute_scene_durations(scenes: list) -> list:
    """Absolute (start, end) per scene, gaps split 50/50 between neighbours."""
    raw = []
    for scene in scenes:
        sentences = scene.get("sentences", [])
        if sentences:
            try:
                t0 = _parse_timestamp(sentences[0]["start"])
                t1 = _parse_timestamp(sentences[-1]["end"])
                raw.append((t0, max(t1, t0 + 0.5)))
                continue
            except Exception:
                pass
        raw.append(None)

    for i, t in enumerate(raw):
        if t is not None:
            continue
        prev_end = raw[i - 1][1] if i > 0 and raw[i - 1] is not None else 0.0
        next_start = next((raw[j][0] for j in range(i + 1, len(raw)) if raw[j] is not None), None)
        raw[i] = (prev_end, next_start if next_start is not None else prev_end + 3.0)

    adjusted = list(raw)
    for i in range(len(adjusted) - 1):
        curr_end, next_start = adjusted[i][1], adjusted[i + 1][0]
        if next_start > curr_end:
            mid = (curr_end + next_start) / 2.0
            adjusted[i]     = (adjusted[i][0], mid)
            adjusted[i + 1] = (mid, adjusted[i + 1][1])

    return adjusted


def _make_kenburns_filter(duration: float, zoom_in: bool) -> str:
    """
    Proven smooth Ken Burns via zoompan:
    - scale=8000:-1 first so zoompan has massive float-precision headroom
      (this is the key trick that eliminates shaking)
    - zoom+step per frame for zoom-in
    - if(lte(zoom,1.0), start_zoom, max(zoom-step, 1.0)) for zoom-out
    - centred x/y: iw/2-(iw/zoom/2), ih/2-(ih/zoom/2)
    """
    n_frames   = max(1, round(duration * FPS))
    total_zoom = ZOOM_PER_SEC * duration          # e.g. 0.04 * 5s = 0.20
    zoom_step  = total_zoom / n_frames            # per-frame increment
    start_zoom = 1.0 + total_zoom                 # zoom-out starts here

    if zoom_in:
        z_expr = f"zoom+{zoom_step:.6f}"
    else:
        # Start at start_zoom, decrease by step each frame, floor at 1.0
        z_expr = f"if(lte(zoom,1.0),{start_zoom:.6f},max(zoom-{zoom_step:.6f},1.0))"

    x_expr = "iw/2-(iw/zoom/2)"
    y_expr = "ih/2-(ih/zoom/2)"

    return (
        f"scale=8000:-1,"                 # oversample — eliminates shake
        f"zoompan="
        f"z='{z_expr}':"
        f"x='{x_expr}':"
        f"y='{y_expr}':"
        f"d={n_frames}:"
        f"s={WIDTH}x{HEIGHT}:"
        f"fps={FPS},"
        f"trim=duration={duration:.3f},"  # hard-cap duration
        f"format=yuv420p"
    )


def _render_scene_clip(img_path: str, duration: float, zoom_in: bool, output_path: str):
    """Render one scene image to an MP4 clip with Ken Burns. Returns stderr or None."""
    vf  = _make_kenburns_filter(duration, zoom_in)
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-framerate", str(FPS), "-i", img_path,
        "-vf", vf,
        "-t", f"{duration:.3f}",
        "-c:v", VIDEO_CODEC, "-preset", PRESET, "-crf", str(CRF),
        "-an", output_path,
    ]
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return None if r.returncode == 0 else r.stderr.decode("utf-8", errors="replace")


def export_video_generator(
    project_json: dict,
    audio_bytes: Optional[bytes] = None,
    audio_filename: Optional[str] = None,
) -> Generator[dict, None, None]:
    try:
        scenes = [s for s in project_json.get("items", []) if s.get("type") == "scene"]
        if not scenes:
            yield {"status": "error", "error": "No scenes found in project file."}
            return

        total       = len(scenes)
        scene_times = _compute_scene_durations(scenes)

        with tempfile.TemporaryDirectory() as tmpdir:

            # ── 1. Render each scene clip ─────────────────────────────────
            clip_paths = []
            for idx, scene in enumerate(scenes):
                yield {"status": "processing", "progress": int((idx / total) * 75)}

                t0, t1   = scene_times[idx]
                duration = max(t1 - t0, 0.5)
                zoom_in  = (idx % 2 == 0)

                img_data = scene.get("image", "")
                img_path = os.path.join(tmpdir, f"scene_{idx:04d}.jpg")

                if not img_data:
                    Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0)).save(img_path, "JPEG")
                else:
                    if ',' in img_data:
                        img_data = img_data.split(',', 1)[1]
                    pil = Image.open(io.BytesIO(base64.b64decode(img_data))).convert("RGB")
                    pil = _fit_image(pil)
                    pil.save(img_path, "JPEG", quality=JPEG_QUALITY)

                clip_path = os.path.join(tmpdir, f"clip_{idx:04d}.mp4")

                if ZOOM_PER_SEC > 0:
                    err = _render_scene_clip(img_path, duration, zoom_in, clip_path)
                    if err:
                        yield {"status": "error", "error": f"ffmpeg scene {idx} failed:\n{err}"}
                        return
                else:
                    cmd = [
                        "ffmpeg", "-y",
                        "-loop", "1", "-framerate", str(FPS), "-i", img_path,
                        "-vf", f"scale={WIDTH}:{HEIGHT}:flags=lanczos,format=yuv420p",
                        "-t", f"{duration:.3f}",
                        "-c:v", VIDEO_CODEC, "-preset", PRESET, "-crf", str(CRF),
                        "-an", clip_path,
                    ]
                    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    if r.returncode != 0:
                        yield {"status": "error", "error": r.stderr.decode("utf-8", errors="replace")}
                        return

                clip_paths.append(clip_path)

            yield {"status": "processing", "progress": 80}

            # ── 2. Concat list ────────────────────────────────────────────
            concat_path = os.path.join(tmpdir, "concat.txt")
            with open(concat_path, "w") as f:
                for cp in clip_paths:
                    f.write(f"file '{cp}'\n")

            yield {"status": "processing", "progress": 83}

            # ── 3. Save audio ─────────────────────────────────────────────
            audio_path = None
            if audio_bytes:
                ext = Path(audio_filename).suffix if audio_filename else ".mp3"
                audio_path = os.path.join(tmpdir, f"audio{ext}")
                with open(audio_path, "wb") as f:
                    f.write(audio_bytes)

            yield {"status": "processing", "progress": 86}

            # ── 4. Final concat + mux ─────────────────────────────────────
            output_path = os.path.join(tmpdir, "output.mp4")
            cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_path]
            if audio_path:
                cmd += ["-i", audio_path, "-shortest"]
            cmd += ["-c:v", "copy"]
            if audio_path:
                cmd += ["-c:a", AUDIO_CODEC, "-b:a", AUDIO_BITRATE]
            cmd.append(output_path)

            r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if r.returncode != 0:
                yield {"status": "error", "error": f"ffmpeg concat failed:\n{r.stderr.decode('utf-8', errors='replace')}"}
                return

            yield {"status": "processing", "progress": 97}

            # ── 5. Return base64 video ────────────────────────────────────
            with open(output_path, "rb") as f:
                video_b64 = base64.b64encode(f.read()).decode("utf-8")

        yield {"status": "done", "video_data": video_b64}

    except Exception as e:
        import traceback
        yield {"status": "error", "error": f"{type(e).__name__}: {e}\n{traceback.format_exc()}"}