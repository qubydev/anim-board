from dotenv import load_dotenv
load_dotenv()

from langchain_groq import ChatGroq
import os
from pydantic import BaseModel, Field

# Definations 
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

model = ChatGroq(
    api_key=GROQ_API_KEY,
    model="llama-3.3-70b-versatile"
)

# Models
class ScenesWithIndexGroups(BaseModel):
    scenes: list[list[int]] = Field(..., description="list of list of line indices, groupped into scenes.")

class SceneImagePrompt(BaseModel):
    prompt: str = Field(..., description="A descriptive prompt for generating an image based on the scene lines.")


# Prompts
GENERATE_SCENES_SYSTEM = """You are a visual planner for an AI video generation pipeline. Lines from a script with their indices are provided to you. Your task is to group these lines into short scenes.

CRITICAL CONSTRAINT: ONE SCENE = ONE IMAGE
- Every scene you create will be represented by ONE single image in the video.
- Therefore, you CANNOT group lines together which does not fit into a single scene image.
- Because of this, most scenes will probably contain 1 to 2 lines.

RULES:
- Return ONLY a valid JSON list of lists of line indices (e.g., [[0], [1, 2], [3], [4]]). No other text, formatting, or markdown blocks.
- Do not miss or repeat any index.

EXAMPLE OF EXPECTED PACING:
Text: 
0. The neon signs of Neo-Tokyo flicker in the heavy rain.
1. A cyber-thief drops silently from the glass rooftop.
2. She lands perfectly balanced on the rusted fire escape.
3. A security drone sweeps its red targeting laser across the dark alley.
4. She presses her back flat against the cold brick wall to hide.
5. The drone hovers for a second before flying away.

Correct Output for Example:
[[0], [1, 2], [3], [4], [5]]
"""

GENERATE_SCENES_USER = """Please generate scenes for the following script:

TITLE: {title}

LINES:
{formatted_lines}
"""

# 2D animation style focused
GENERATE_IMAGE_PROMPT_SYSTEM = """You are a creative AI image prompt engineer specializing in 2D animation style. Some lines from a animation script and some other optional details are provided to you, your task is to generate a descriptive image-generation prompt that represents the scene following the given details. This prompt will later be used to generate an image using a text-to-image AI model.

POSSIBLE INPUTS:
- **SCENE LINES** (REQUIRED): A few lines from the script that describe the scene.
- **CHARACTER DESCRIPTION** (OPTIONAL): A visual description of the main character(s) in the scene.
- **ANIMATION STYLE** (OPTIONAL): A specific 2D animation style to apply.

RULES:
- Be creative and descriptive in your prompt to ensure the generated image captures the essence of the scene.
- It is not mendatory to show the character in the scene, you may or may not contain the character based on the provided inputs.
- Do not add any instruction to add any type of caption text in the output image.
"""

def GENERATE_IMAGE_PROMPT_USER(
        scene_lines: str,
        character_description: str | None = None,
        animation_style: str | None = None,
    ) -> str:
    prompt = f"Generate an image prompt using the following inputs:\n\n**SCENE LINES:**\n{scene_lines}"
    if character_description:
        prompt += f"\n\n**CHARACTER DESCRIPTION:**\n{character_description}"
    if animation_style:
        prompt += f"\n\n**ANIMATION STYLE:**\n{animation_style}"
    
    return prompt


# Functions 
def generate_scenes(title: str, lines: list[dict]) -> list[list[int]]:
    structured_model = model.with_structured_output(ScenesWithIndexGroups)
    formatted_lines = "\n".join([f"{i}: \"{line['text']}\"" for i, line in enumerate(lines)])

    response = structured_model.invoke([
        {"role": "system", "content": GENERATE_SCENES_SYSTEM},
        {"role": "user", "content": GENERATE_SCENES_USER.format(title=title, formatted_lines=formatted_lines)}
    ])
    return response.scenes

def generate_image_prompt(
        scene_lines: str,
        character_description: str | None = None,
        animation_style: str | None = None
    ) -> str:
    structured_model = model.with_structured_output(SceneImagePrompt)
    response = structured_model.invoke([
        {"role": "system", "content": GENERATE_IMAGE_PROMPT_SYSTEM},
        {"role": "user", "content": GENERATE_IMAGE_PROMPT_USER(
            scene_lines=scene_lines,
            character_description=character_description,
            animation_style=animation_style
        )}
    ])
    return response.prompt
    