import cv2
import numpy as np


def calculate_optical_flow(prev_frame: np.ndarray, curr_frame: np.ndarray) -> float:
    """
    Compute the Farneback dense optical flow between two consecutive video frames
    and return the average motion magnitude as a proxy for crowd motion speed.

    Args:
        prev_frame: Previous OpenCV BGR frame (HxWx3 NumPy uint8 array).
        curr_frame: Current  OpenCV BGR frame (HxWx3 NumPy uint8 array).

    Returns:
        avg_magnitude (float): Mean pixel-level optical-flow magnitude across the
                               entire frame.  A higher value indicates faster or
                               more turbulent crowd movement.
    """
    # --- 1. Convert both frames to grayscale --------------------------------
    prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
    curr_gray = cv2.cvtColor(curr_frame, cv2.COLOR_BGR2GRAY)

    # --- 2. Compute dense optical flow (Farneback) --------------------------
    # Returns a 2-channel float32 array of shape (H, W, 2):
    #   flow[..., 0] = horizontal (x) displacement in pixels
    #   flow[..., 1] = vertical   (y) displacement in pixels
    #
    # Parameters (as specified in the build doc):
    #   pyr_scale  = 0.5  → each pyramid level shrinks by half
    #   levels     = 3    → number of pyramid levels
    #   winsize    = 15   → averaging window size
    #   iterations = 3    → iterations per pyramid level
    #   poly_n     = 5    → pixel neighbourhood for poly expansion
    #   poly_sigma = 1.2  → Gaussian std for poly expansion
    #   flags      = 0    → default
    flow: np.ndarray = cv2.calcOpticalFlowFarneback(
        prev_gray, curr_gray,
        None,   # flow output (None → allocate new array)
        0.5,    # pyr_scale
        3,      # levels
        15,     # winsize
        3,      # iterations
        5,      # poly_n
        1.2,    # poly_sigma
        0,      # flags
    )

    # --- 3. Compute per-pixel magnitude from the (x, y) flow vectors --------
    # cv2.cartToPolar expects separate x and y arrays and returns
    # (magnitude, angle_in_radians_or_degrees).
    magnitude, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])

    # --- 4. Return the mean magnitude as the crowd "motion speed" -----------
    avg_magnitude: float = float(np.mean(magnitude))
    return avg_magnitude
