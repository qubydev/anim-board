from utils.redis_client import client as r_client
import requests


WHISK_SESSION_TOKEN_KEY = "whisk:session_token"
SESSION_URL = "https://labs.google/fx/api/auth/session"
IMAGE_GENERATION_URL = "https://aisandbox-pa.googleapis.com/v1/whisk:generateImage"


def fetch_access_token(session_token):
    resp = requests.get(
        SESSION_URL,
        headers={"Cookie": f"__Secure-next-auth.session-token={session_token}"}
    )
    if not resp.ok:
        raise RuntimeError(
            f"Failed to fetch access token: {resp.status_code} {resp.text}"
        )

    data = resp.json()
    access_token = data.get("access_token")

    if not access_token:
        raise RuntimeError("Access token not found in response")

    return access_token


def generate_image(
        prompt,
        aspect_ratio="IMAGE_ASPECT_RATIO_LANDSCAPE",
        model="IMAGEN_3_5",
        session_token=None
):
    if not session_token:
        raise RuntimeError("Session token is required to generate image")

    if not prompt:
        raise RuntimeError("Prompt is required to generate image")
    
    access_token = r_client.get(WHISK_SESSION_TOKEN_KEY)

    if access_token and isinstance(access_token, bytes):
        access_token = access_token.decode("utf-8")

    if not access_token:
        access_token = fetch_access_token(session_token)

        r_client.set(WHISK_SESSION_TOKEN_KEY, access_token)

        # Retrieve again and decode
        access_token = r_client.get(WHISK_SESSION_TOKEN_KEY)
        if access_token and isinstance(access_token, bytes):
            access_token = access_token.decode("utf-8")

    if not access_token:
        raise RuntimeError("Failed to update access token")
    
    payload = {
        "imageModelSettings": {
            "imageModel": model,
            "aspectRatio": aspect_ratio
        },
        "prompt": prompt
    }

    response = requests.post(
        IMAGE_GENERATION_URL,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        },
        json=payload
    )

    if not response.ok:
        raise RuntimeError(
            f"Failed to generate image: {response.status_code} {response.text}"
        )

    return response.json()