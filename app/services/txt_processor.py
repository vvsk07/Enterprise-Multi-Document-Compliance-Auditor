"""
TXT Processing Service with Multi-Encoding Fallback Support.
"""

from app.core.logging import logger

class TXTProcessor:
    SUPPORTED_ENCODINGS = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]

    def process_txt(self, file_path: str) -> str:
        """
        Reads a text file using multiple encoding fallbacks.
        Returns extracted text string.
        """
        for encoding in self.SUPPORTED_ENCODINGS:
            try:
                with open(file_path, "r", encoding=encoding) as f:
                    text = f.read()
                logger.info(f"Successfully read TXT file using encoding '{encoding}'.")
                return text
            except UnicodeDecodeError:
                continue
            except Exception as e:
                logger.error(f"Error reading TXT file {file_path} with encoding {encoding}: {e}")
                raise RuntimeError(f"TXT file read error: {str(e)}")
                
        # Last resort fallback with replacement
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
        except Exception as e:
            raise RuntimeError(f"Failed to read TXT file {file_path}: {str(e)}")

txt_processor = TXTProcessor()
