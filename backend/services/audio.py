import base64

def encode_audio(data: bytes) -> str:
    """Encode raw bytes to base64 string."""
    return base64.b64encode(data).decode("utf-8")

def decode_audio(base64_str: str) -> bytes:
    """Decode base64 string to raw bytes."""
    return base64.b64decode(base64_str)
