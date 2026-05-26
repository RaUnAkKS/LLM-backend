import PyPDF2
import docx


def extract_text_from_file(file):
    name = file.name.lower()

    if name.endswith(".pdf"):
        reader = PyPDF2.PdfReader(file) #read the pdf file
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text

    elif name.endswith(".docx"):
        doc = docx.Document(file) #read the docx file
        text = ""
        for para in doc.paragraphs:
            text += para.text + "\n"
        return text

    elif name.endswith(".txt"):
        return file.read().decode("utf-8") #decode the file to utf-8, because it is in bytes, and we need to return string

    else:
        raise ValueError("Unsupported file type")