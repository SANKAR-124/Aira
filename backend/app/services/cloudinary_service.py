import io
import os
from typing import Union

import cv2
import numpy as np
import cloudinary
import cloudinary.uploader

from app.core.config import settings

# Initialize the Cloudinary client once at module load using settings from .env
cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
    secure=True,
)


def upload_image(image_array_or_path: Union[np.ndarray, str], timeout: int = 60) -> str:
    """
    Upload an image to Cloudinary and return the secure URL.

    Args:
        image_array_or_path: Either an OpenCV NumPy BGR image array
                             or an absolute file path string to an image.
        timeout:             Request timeout in seconds (default 60).
                             Passed directly to the Cloudinary SDK so uploads
                             don't hang indefinitely on network failures.

    Returns:
        The secure Cloudinary URL (str) of the uploaded image.

    Raises:
        RuntimeError: If the upload fails or Cloudinary returns no URL.
    """
    if isinstance(image_array_or_path, np.ndarray):
        # Encode the NumPy array to a JPEG in-memory buffer and upload directly.
        success, buffer = cv2.imencode(".jpg", image_array_or_path)
        if not success:
            raise RuntimeError("cv2.imencode failed -- could not encode frame to JPEG.")

        byte_stream = io.BytesIO(buffer.tobytes())
        response = cloudinary.uploader.upload(
            byte_stream,
            folder="rcmp/alerts",
            resource_type="image",
            timeout=timeout,
        )
    elif isinstance(image_array_or_path, str):
        if not os.path.isfile(image_array_or_path):
            raise FileNotFoundError(f"Image file not found: {image_array_or_path}")

        response = cloudinary.uploader.upload(
            image_array_or_path,
            folder="rcmp/alerts",
            resource_type="image",
            timeout=timeout,
        )
    else:
        raise TypeError(
            f"upload_image expects a NumPy array or a file path string, "
            f"got {type(image_array_or_path).__name__}"
        )

    secure_url: str = response.get("secure_url", "")
    if not secure_url:
        raise RuntimeError(
            f"Cloudinary upload succeeded but returned no URL. Response: {response}"
        )

    return secure_url

def delete_image(secure_url: str) -> None:
    """Extract public_id from Cloudinary URL and delete it from Cloudinary."""
    if not secure_url or "cloudinary.com" not in secure_url:
        return
    
    try:
        parts = secure_url.split("/upload/")
        if len(parts) > 1:
            path_part = parts[1]
            if path_part.startswith("v"):
                path_part = path_part.split("/", 1)[-1]
            public_id = path_part.rsplit(".", 1)[0]
            cloudinary.uploader.destroy(public_id)
    except Exception as e:
        print(f"Failed to delete Cloudinary image: {e}")
