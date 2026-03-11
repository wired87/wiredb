from pix2text import Pix2Text
from pathlib import Path

r"""r = process_pdf_bytes(
    pdf_bytes=open(str((Path(__file__).resolve().parents[4] / "test_paper.pdf")), "rb")
)
print("r", r)"""


if __name__ =="__main__":
    # Initialisierung (lädt Modelle für Layout, Text und Formeln)
    p2t = Pix2Text.from_config()

    # Ein ganzes PDF analysieren
    pdf_path = str((Path(__file__).resolve().parents[4] / "test_paper.pdf"))
    pages = p2t.recognize_pdf(pdf_path)

    for i, page in enumerate(pages):
        # Das Ergebnis ist ein strukturiertes Objekt (Markdown-ähnlich)
        print(f"--- Seite {i + 1} ---")
        print(page.to_markdown('output_dir'))

