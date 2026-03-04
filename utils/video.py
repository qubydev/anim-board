import json
import base64
import os
import tempfile
import asyncio
import re
import shutil
import logging
import subprocess
import io
from PIL import Image
from typing import AsyncGenerator

WIDTH = 1920
HEIGHT = 1080

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

async def export_video_generator(project_data: dict) -> AsyncGenerator[str, None]:
    temp_dir = tempfile.mkdtemp()
    project_id = id(project_data)
    
    logger.info(f"Starting video export for project [{project_id}] at {WIDTH}x{HEIGHT}")
    
    try:
        items = project_data.get("items", [])
        scenes = [item for item in items if item.get("type") == "scene"]
        
        if not scenes:
            logger.error("Export failed: No scenes found.")
            yield f"data: {json.dumps({'error': 'No scenes found in project file'})}\n\n"
            return

        concat_file_path = os.path.join(temp_dir, "concat.txt")
        total_duration = 0.0

        with open(concat_file_path, "w") as f:
            for idx, scene in enumerate(scenes):
                img_data = scene.get("image", "")
                if "base64," in img_data:
                    img_data = img_data.split("base64,")[1]
                
                img_bytes = base64.b64decode(img_data)
                img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
                
                img_w, img_h = img.size
                
                # Calculate scale to cover the 1920x1080 area completely
                scale_w = WIDTH / img_w
                scale_h = HEIGHT / img_h
                fill_scale = max(scale_w, scale_h)
                
                new_w = int(img_w * fill_scale)
                new_h = int(img_h * fill_scale)
                
                resized_img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                
                # Create the 1080p canvas
                canvas = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
                
                # Center the resized image on the canvas
                paste_x = (WIDTH - new_w) // 2
                paste_y = (HEIGHT - new_h) // 2
                canvas.paste(resized_img, (paste_x, paste_y))
                
                img_path = os.path.join(temp_dir, f"scene_{idx}.jpg")
                canvas.save(img_path, "JPEG", quality=95)

                sentences = scene.get("sentences", [])
                if not sentences:
                    duration = 3.0
                else:
                    duration = float(sentences[-1]["end"]) - float(sentences[0]["start"])
                
                duration = max(0.1, duration)
                total_duration += duration
                
                f.write(f"file '{img_path}'\n")
                f.write(f"duration {duration}\n")
            
            if scenes:
                f.write(f"file '{os.path.join(temp_dir, f'scene_{len(scenes)-1}.jpg')}'\n")

        output_filename = f"exported_{project_id}.mp4"
        output_path = os.path.join(tempfile.gettempdir(), output_filename)
        
        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_file_path, 
            "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", output_path
        ]

        logger.info(f"Running FFmpeg...")
        process = subprocess.Popen(
            cmd, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='ignore'
        )

        time_pattern = re.compile(r"time=(\d+):(\d+):(\d+\.\d+)")
        last_logged_progress = -1

        while True:
            line = await asyncio.to_thread(process.stderr.readline)
            if not line and process.poll() is not None:
                break
            
            match = time_pattern.search(line)
            if match:
                h, m, s = map(float, match.groups())
                elapsed = h * 3600 + m * 60 + s
                progress = min(99, int((elapsed / total_duration) * 100))
                
                if progress >= last_logged_progress + 5:
                    logger.info(f"Export Progress: {progress}%")
                    last_logged_progress = progress
                
                yield f"data: {json.dumps({'status': 'processing', 'progress': progress})}\n\n"

        if process.returncode != 0:
            yield f"data: {json.dumps({'error': 'FFmpeg failed'})}\n\n"
        else:
            logger.info(f"Export Complete: {output_filename}")
            yield f"data: {json.dumps({'status': 'done', 'url': f'/api/download-video/{output_filename}'})}\n\n"

    except Exception as e:
        logger.exception("Export crashed")
        yield f"data: {json.dumps({'error': str(e)})}\n\n"
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)