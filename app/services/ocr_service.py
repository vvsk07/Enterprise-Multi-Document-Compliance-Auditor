"""
OCR Service Abstraction using subprocess Tesseract CLI and PIL.
Eliminates third-party package DLL locks on Windows.
"""

import os
import io
import shutil
import tempfile
import subprocess
from typing import Tuple
from PIL import Image
from app.config import settings
from app.core.logging import logger

class OCRService:
    def __init__(self):
        self.tesseract_cmd = settings.TESSERACT_CMD or "tesseract"

    def is_ocr_available(self) -> bool:
        """
        Detects if Tesseract CLI executable is installed and available.
        """
        # Check explicit path first
        if os.path.exists(self.tesseract_cmd):
            return True
        # Check system PATH
        return shutil.which("tesseract") is not None

    def _get_executable(self) -> str:
        if os.path.exists(self.tesseract_cmd):
            return self.tesseract_cmd
        which_path = shutil.which("tesseract")
        if which_path:
            return which_path
        return self.tesseract_cmd

    def perform_ocr_on_image_bytes(self, image_bytes: bytes) -> Tuple[str, bool, str]:
        """
        Performs OCR on image raw bytes using Tesseract CLI.
        Returns: (extracted_text, success, status_message)
        """
        if not self.is_ocr_available():
            logger.warning("OCR requested but Tesseract binary is not installed or available.")
            return "", False, "OCR_UNAVAILABLE: Tesseract executable not found on server."

        try:
            cmd = self._get_executable()
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_img:
                tmp_img.write(image_bytes)
                tmp_img_path = tmp_img.name

            try:
                result = subprocess.run(
                    [cmd, tmp_img_path, "stdout", "-l", "eng"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    check=True
                )
                extracted_text = result.stdout.strip()
                return extracted_text, True, "OCR_SUCCESS"
            finally:
                if os.path.exists(tmp_img_path):
                    os.remove(tmp_img_path)

        except subprocess.TimeoutExpired:
            logger.error("OCR execution timed out after 30 seconds.")
            return "", False, "OCR_FAILED: Execution timed out."
        except Exception as e:
            logger.error(f"OCR execution failed: {e}")
            return "", False, f"OCR_FAILED: {str(e)}"

ocr_service = OCRService()
