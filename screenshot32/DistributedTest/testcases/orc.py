import pytesseract
from PIL import Image


def Orc(path):
    pytesseract.pytesseract.tesseract_cmd = 'C:\\Program Files (x86)\\Tesseract-OCR\\tesseract.exe'
    tessdata_dir_config = '--tessdata-dir "C:\\Program Files (x86)\\Tesseract-OCR\\tessdata"'
    image = Image.open(path)
    code = pytesseract.image_to_string(image, config=tessdata_dir_config)
    return code
