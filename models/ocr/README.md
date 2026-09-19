# Local OCR models

Models are installed explicitly by `python scripts/setup_ocr.py`. Runtime never downloads models.
The manifest pins RapidAI's v3.9.2 ONNX exports and their published SHA-256 checksums.

- PP-OCRv5 server detector: detects text regions, including Korean.
- Korean PP-OCRv5 mobile recognizer: Korean and English text.
- PP-OCRv4 orientation classifier: required by RapidOCR initialization; disabled in capture inference
  because it falsely rotated upright Korean text in validation.

Sources and licensing:
- https://github.com/RapidAI/RapidOCR (Apache-2.0)
- https://github.com/PaddlePaddle/PaddleOCR (Apache-2.0)
- https://github.com/RapidAI/RapidOCR/blob/v3.9.2/python/rapidocr/default_models.yaml

ONNX binaries are intentionally excluded from Git, but included in the packaging spec.
Do not build an OCR-enabled release without installing and validating all manifest models.
