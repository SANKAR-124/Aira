import torch
import torch.nn.functional as F
import torchvision.transforms as transforms
import numpy as np
import cv2

from app.core.config import settings
from app.ai.csrnet_model import CSRNet

# --- ImageNet normalisation (same stats used during CSRNet training) ---
_TRANSFORM = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225],
    ),
])

# Load model once at module import so every call shares the same instance.
_device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


def _load_model() -> CSRNet:
    model = CSRNet(load_weights=True)
    checkpoint = torch.load(settings.CSRNET_WEIGHTS_PATH, map_location=_device)
    state_dict = checkpoint["state_dict"] if isinstance(checkpoint, dict) and "state_dict" in checkpoint else checkpoint
    model.load_state_dict(state_dict, strict=True)
    model.to(_device)
    model.eval()
    return model


_model: CSRNet = _load_model()


def process_frame(frame: np.ndarray) -> tuple[int, np.ndarray]:
    """
    Run CSRNet density estimation on a single OpenCV BGR frame.

    Args:
        frame: HxWx3 NumPy array in BGR format (as returned by cv2.VideoCapture).

    Returns:
        headcount (int): Estimated number of people in the frame.
        density_map (np.ndarray): The raw density map as a 2-D float32 array,
                                   suitable for heatmap overlay via cv2.applyColorMap().
    """
    # OpenCV is BGR; convert to RGB for torchvision transforms.
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Normalise and add batch dimension: (1, 3, H, W)
    tensor = _TRANSFORM(rgb).unsqueeze(0).to(_device)

    with torch.no_grad():
        output = _model(tensor)           # shape: (1, 1, H/8, W/8)

    # Sum the density map to get the estimated headcount.
    headcount = int(output.sum().item())

    # Convert density map to a 2-D NumPy float32 array for visualisation.
    density_map: np.ndarray = output.squeeze().cpu().numpy().astype(np.float32)

    return headcount, density_map
