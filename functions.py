from PyPDF2 import PdfFileMerger
from pathlib import Path
import shutil


def merge_pdf(dirpath, filename):
    merged = PdfFileMerger()
    path = Path(dirpath)
    for WindowsPath in path.iterdir():
        file = str(WindowsPath)
        merged.append(file)
    merged.write(f'{path.parent}/{filename}')
    merged.close()
    shutil.rmtree(str(path.absolute()))


def merge_txt(dirpath, filename):
    path = Path(dirpath)
    with open(f'{path.parent}/{filename}', 'w') as out:
        for WindowsPath in path.iterdir():
            with open(str(WindowsPath), 'r') as read:
                out.write(read.read())
            out.write("\n")
    shutil.rmtree(str(path.absolute()))
