from __future__ import annotations

import cv2
import numpy as np
from sanic.log import logger

from .categories import IMAGE_ADJUSTMENT
from .node_base import NodeBase
from .node_factory import NodeFactory
from .properties.inputs import *
from .properties.outputs import *
from .utils.image_utils import normalize
from .utils.pil_utils import *


@NodeFactory.register("chainner:image:hue_and_saturation")
class HueAndSaturationNode(NodeBase):
    """OpenCV Hue and Saturation Node"""

    def __init__(self):
        """Constructor"""
        super().__init__()
        self.description = "Adjust the hue and saturation of an image."
        self.inputs = [
            ImageInput(),
            SliderInput("Hue", -180, 180, 0),
            SliderInput("Saturation", -255, 255, 0),
        ]
        self.outputs = [ImageOutput()]
        self.category = IMAGE_ADJUSTMENT
        self.name = "Hue & Saturation"
        self.icon = "MdOutlineColorLens"
        self.sub = "Adjustments"

    def add_and_wrap_hue(self, img: np.ndarray, add_val: float) -> np.ndarray:
        """Adds hue change value to image and wraps on range overflow"""

        img += add_val
        img[img >= 360] -= 360  # Wrap positive overflow
        img[img < 0] += 360  # Wrap negative overflow
        return img

    def run(self, img: np.ndarray, hue: int, saturation: int) -> np.ndarray:
        """Adjust the hue and saturation of an image"""

        # Pass through grayscale and unadjusted images
        hue = int(hue)
        saturation = int(saturation)
        if (
            img.ndim < 3
            or img.shape[2] == 1
            or (int(hue) == 0 and int(saturation) == 0)
        ):
            return img

        img = normalize(img)

        # Preserve alpha channel if it exists
        c = img.shape[2]
        alpha = None
        if c > 3:
            alpha = img[:, :, 3]

        hls = cv2.cvtColor(img, cv2.COLOR_BGR2HLS)
        h, l, s = cv2.split(hls)

        # Adjust hue and saturation
        hnew = self.add_and_wrap_hue(h, hue)
        smod = 1 + (saturation / 255)
        snew = np.clip((s * smod), 0, 1)

        hlsnew = cv2.merge([hnew, l, snew])
        img = cv2.cvtColor(hlsnew, cv2.COLOR_HLS2BGR)
        if alpha is not None:  # Re-add alpha, if it exists
            img = np.dstack((img, alpha))

        return img


@NodeFactory.register("chainner:image:brightness_and_contrast")
class BrightnessAndContrastNode(NodeBase):
    """OpenCV Brightness and Contrast Node"""

    def __init__(self):
        """Constructor"""
        super().__init__()
        self.description = "Adjust the brightness and contrast of an image."
        self.inputs = [
            ImageInput(),
            SliderInput("Brightness", -255, 255, 0),
            SliderInput("Contrast", -255, 255, 0),
        ]
        self.outputs = [ImageOutput()]
        self.category = IMAGE_ADJUSTMENT
        self.name = "Brightness & Contrast"
        self.icon = "ImBrightnessContrast"
        self.sub = "Adjustments"

    def run(self, img: np.ndarray, b_amount: int, c_amount: int) -> np.ndarray:
        """Adjusts the brightness and contrast of an image"""

        b_amount = int(b_amount) / 255
        c_amount = int(c_amount) / 255

        # Pass through unadjusted image
        if b_amount == 0 and c_amount == 0:
            return img

        img = normalize(img)

        # Calculate brightness adjustment
        if b_amount > 0:
            shadow = b_amount
            highlight = 1
        else:
            shadow = 0
            highlight = 1 + b_amount
        alpha_b = highlight - shadow
        if img.ndim == 2:
            img = cv2.addWeighted(img, alpha_b, img, 0, shadow)
        else:
            img[:, :, :3] = cv2.addWeighted(
                img[:, :, :3], alpha_b, img[:, :, :3], 0, shadow
            )

        # Calculate contrast adjustment
        alpha_c = ((259 / 255) * (c_amount + 1)) / (
            (259 / 255) - c_amount
        )  # Contrast correction factor
        gamma_c = 0.5 * (1 - alpha_c)
        if img.ndim == 2:
            img = cv2.addWeighted(img, alpha_c, img, 0, gamma_c)
        else:
            img[:, :, :3] = cv2.addWeighted(
                img[:, :, :3], alpha_c, img[:, :, :3], 0, gamma_c
            )
        img = np.clip(img, 0, 1).astype("float32")

        return img


@NodeFactory.register("chainner:image:threshold")
class ThresholdNode(NodeBase):
    """OpenCV Threshold node"""

    def __init__(self):
        """Constructor"""
        super().__init__()
        self.description = "Perform a threshold on an image."
        self.inputs = [
            ImageInput(),
            SliderInput("Threshold", 0, 100, 50),
            SliderInput("Maximum Value", 0, 100, 100),
            ThresholdInput(),
        ]
        self.outputs = [ImageOutput()]
        self.category = IMAGE_ADJUSTMENT
        self.name = "Threshold"
        self.icon = "MdShowChart"
        self.sub = "Adjustments"

    def run(
        self, img: np.ndarray, thresh: int, maxval: int, thresh_type: int
    ) -> np.ndarray:
        """Takes an image and applies a threshold to it"""

        img = normalize(img)

        logger.info(f"thresh {thresh}, maxval {maxval}, type {thresh_type}")

        real_thresh = int(thresh) / 100
        real_maxval = int(maxval) / 100

        logger.info(f"real_thresh {real_thresh}, real_maxval {real_maxval}")

        _, result = cv2.threshold(img, real_thresh, real_maxval, int(thresh_type))

        return result


@NodeFactory.register("chainner:image:threshold_adaptive")
class AdaptiveThresholdNode(NodeBase):
    """OpenCV Adaptive Threshold node"""

    def __init__(self):
        """Constructor"""
        super().__init__()
        self.description = "Perform an adaptive threshold on an image."
        self.inputs = [
            ImageInput(),
            SliderInput("Maximum Value", 0, 100, 100),
            AdaptiveMethodInput(),
            AdaptiveThresholdInput(),
            OddIntegerInput("Block Size", default=3, minimum=3),
            IntegerInput("Mean Subtraction"),
        ]
        self.outputs = [ImageOutput()]
        self.category = IMAGE_ADJUSTMENT
        self.name = "Threshold (Adaptive)"
        self.icon = "MdAutoGraph"
        self.sub = "Adjustments"

    def run(
        self,
        img: np.ndarray,
        maxval: int,
        adaptive_method: int,
        thresh_type: int,
        block_size: int,
        c: int,
    ) -> np.ndarray:
        """Takes an image and applies an adaptive threshold to it"""

        assert (
            img.ndim == 2
        ), "Image must be grayscale (single channel) to apply an adaptive threshold"

        # Adaptive threshold requires uint8 input
        img = (normalize(img) * 255).astype("uint8")

        real_maxval = int(maxval) / 100 * 255

        result = cv2.adaptiveThreshold(
            img,
            real_maxval,
            int(adaptive_method),
            int(thresh_type),
            int(block_size),
            int(c),
        )

        return result.astype("float32") / 255