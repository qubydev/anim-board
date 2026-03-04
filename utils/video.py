import json
import base64
import os
import asyncio
import re
import shutil
import logging
import io
import subprocess
from PIL import Image
from typing import AsyncGenerator

WIDTH = 1920
HEIGHT = 1080

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def parse_srt_timestamp(srt_string):
    if isinstance(srt_string, (int, float)):
        return float(srt_string)
    match = re.match(r"^(\d{2,}):(\d{2}):(\d{2})(?:,|.)(\d{3})$", str(srt_string).strip())
    if not match:
        try:
            return float(srt_string)
        except ValueError:
            return 0.0
    h, m, s, ms = match.groups()
    return (int(h) * 3600) + (int(m) * 60) + int(s) + (int(ms) / 1000.0)

async def export_video_generator(project_data: dict, audio_bytes: bytes = None, audio_filename: str = None) -> AsyncGenerator[str, None]:
    project_id = id(project_data)
    base_tmp_dir = "tmp"
    os.makedirs(base_tmp_dir, exist_ok=True)
    temp_dir = os.path.join(base_tmp_dir, f"export_{project_id}")
    os.makedirs(temp_dir, exist_ok=True)
    
    try:
        items = project_data.get("items", [])
        scenes = [item for item in items if item.get("type") == "scene"]
        
        if not scenes:
            yield f"data: {json.dumps({'error': 'No scenes found in project file'})}\n\n"
            return

        scene_times = []
        for scene in scenes:
            sentences = scene.get("sentences", [])
            if not sentences:
                scene_times.append({"start": 0.0, "end": 3.0, "empty": True})
            else:
                starts = [parse_srt_timestamp(s.get("start", 0)) for s in sentences]
                ends = [parse_srt_timestamp(s.get("end", 0)) for s in sentences]
                scene_times.append({
                    "start": min(starts) if starts else 0.0,
                    "end": max(ends) if ends else 3.0,
                    "empty": False
                })

        scene_durations = []
        for i in range(len(scene_times)):
            if scene_times[i]["empty"]:
                scene_durations.append(3.0)
                continue
                
            adj_start = scene_times[i]["start"]
            adj_end = scene_times[i]["end"]
            
            if i > 0 and not scene_times[i-1]["empty"]:
                adj_start = (scene_times[i-1]["end"] + scene_times[i]["start"]) / 2.0
                
            if i < len(scene_times) - 1 and not scene_times[i+1]["empty"]:
                adj_end = (scene_times[i]["end"] + scene_times[i+1]["start"]) / 2.0
                
            dur = max(0.1, adj_end - adj_start)
            scene_durations.append(dur)

        concat_file_path = os.path.join(temp_dir, "concat.txt")
        total_duration = 0.0

        with open(concat_file_path, "w") as f:
            for idx, scene in enumerate(scenes):
                img_data = scene.get("image", "")
                if "base64," in img_data:
                    img_data = img_data.split("base64,")[1]
                
                if not img_data:
                    canvas = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
                else:
                    img_bytes = base64.b64decode(img_data)
                    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
                    img_w, img_h = img.size
                    scale_w = WIDTH / img_w
                    scale_h = HEIGHT / img_h
                    fill_scale = max(scale_w, scale_h)
                    new_w = int(img_w * fill_scale)
                    new_h = int(img_h * fill_scale)
                    resized_img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                    canvas = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
                    paste_x = (WIDTH - new_w) // 2
                    paste_y = (HEIGHT - new_h) // 2
                    canvas.paste(resized_img, (paste_x, paste_y))
                
                img_path = os.path.join(temp_dir, f"scene_{idx}.jpg")
                canvas.save(img_path, "JPEG", quality=95)

                duration = scene_durations[idx]
                total_duration += duration
                
                posix_path = os.path.abspath(img_path).replace("\\", "/")
                f.write(f"file '{posix_path}'\n")
                f.write(f"duration {duration}\n")
            
            if scenes:
                last_img_path = os.path.join(temp_dir, f"scene_{len(scenes)-1}.jpg")
                posix_last = os.path.abspath(last_img_path).replace("\\", "/")
                f.write(f"file '{posix_last}'\n")

        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_file_path
        ]

        if audio_bytes and audio_filename:
            audio_path = os.path.join(temp_dir, audio_filename)
            with open(audio_path, "wb") as af:
                af.write(audio_bytes)
            posix_audio = os.path.abspath(audio_path).replace("\\", "/")
            cmd.extend(["-i", posix_audio])

        cmd.extend([
            "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p"
        ])

        if audio_bytes and audio_filename:
            cmd.extend(["-c:a", "aac", "-b:a", "192k"])

        output_path = os.path.join(temp_dir, "output.mp4")
        posix_output = os.path.abspath(output_path).replace("\\", "/")

        cmd.extend([
            "-t", str(total_duration),
            posix_output
        ])

        logger.info("Running FFmpeg locally to standard MP4...")
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        time_pattern = re.compile(r"time=(\d+):(\d+):(\d+\.\d+)")
        last_logged_progress = -1
        error_log = []

        while True:
            line_bytes = await asyncio.to_thread(process.stderr.readline)
            if not line_bytes and process.poll() is not None:
                break
            
            line_str = line_bytes.decode('utf-8', errors='ignore')
            
            if line_str.strip():
                error_log.append(line_str.strip())
                if len(error_log) > 10:
                    error_log.pop(0)

            match = time_pattern.search(line_str)
            if match:
                h, m, s = map(float, match.groups())
                elapsed = h * 3600 + m * 60 + s
                progress = min(99, int((elapsed / total_duration) * 100))
                
                if progress >= last_logged_progress + 5:
                    last_logged_progress = progress
                
                yield f"data: {json.dumps({'status': 'processing', 'progress': progress})}\n\n"

        await asyncio.to_thread(process.wait)

        if process.returncode != 0:
            err_msg = "FFmpeg Error: " + " | ".join(error_log[-3:])
            logger.error(err_msg)
            yield f"data: {json.dumps({'error': err_msg})}\n\n"
        else:
            # Read the standard MP4 into memory
            with open(output_path, "rb") as video_file:
                video_bytes = video_file.read()
            
            b64_video = base64.b64encode(video_bytes).decode('utf-8')
            yield f"data: {json.dumps({'status': 'done', 'video_data': b64_video})}\n\n"

    except Exception as e:
        logger.exception("Export crashed")
        yield f"data: {json.dumps({'error': str(e)})}\n\n"
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)