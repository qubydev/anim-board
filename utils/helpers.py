from fastapi.responses import JSONResponse

# -----------------------------
# Unified Error Response Helper
# -----------------------------
def error_response(status_code: int, message: str, errors=None, refresh=False):
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "message": message,
            "errors": errors,
            "refresh": refresh
        },
    )

def number_to_position(n):
    if n < 1 or n > 10:
        raise ValueError("Input must be an integer between 1 and 10")

    positions = {
        1: "First",
        2: "Second",
        3: "Third",
        4: "Fourth",
        5: "Fifth",
        6: "Sixth",
        7: "Seventh",
        8: "Eighth",
        9: "Ninth",
        10: "Tenth"
    }
    return positions.get(n, "Number out of range")