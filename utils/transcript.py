import whisper
import torch
from nanoid import generate

MODELS_FOLDER = "../models"

def format_data(data):
    formatted_data = []

    for segment in data["segments"]:
        item = {
            "type": "segment",
            "id": segment.get("id", generate(size=10)),
            "start": segment["start"],
            "end": segment["end"],
            "text": segment["text"],
            "words": segment.get("words", [])
        }
        formatted_data.append(item)
    
    return formatted_data


def transcribe_audio(file_path: str):
    print("Loading Whisper model...")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")

    model = whisper.load_model(
        "turbo",
        device=device,
        download_root=MODELS_FOLDER
    )

    print("Transcribing audio...")
    result = model.transcribe(
        file_path,
        word_timestamps=True,
        verbose=False
    )

    del model
    if device == "cuda":
        torch.cuda.empty_cache()

    return format_data(result)
