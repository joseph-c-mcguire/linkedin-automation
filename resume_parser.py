from docx import Document
import PyPDF2
import os
import logging


class ResumeParser:
    def __init__(self, resume_path):
        self.resume_path = resume_path
        self.logger = logging.getLogger("linkedin_bot")
        self.resume_text = self._parse_resume()

    def _parse_resume(self):
        """Parse resume content based on file type"""
        if self.resume_path.endswith(".pdf"):
            return self._parse_pdf()
        elif self.resume_path.endswith(".docx"):
            return self._parse_docx()
        elif self.resume_path.endswith(".txt"):
            return self._parse_txt()
        else:
            raise ValueError(
                "Unsupported resume format. Please use .pdf, .docx, or .txt"
            )

    def _parse_pdf(self):
        """Extract text from PDF file"""
        try:
            with open(self.resume_path, "rb") as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                self.logger.debug("Successfully parsed PDF resume")
                return text.strip()
        except Exception as e:
            self.logger.error(f"Error parsing PDF file: {str(e)}")
            raise ValueError(f"Error parsing PDF file: {str(e)}")

    def _parse_docx(self):
        """Extract text from DOCX file"""
        doc = Document(self.resume_path)
        return " ".join([paragraph.text for paragraph in doc.paragraphs])

    def _parse_txt(self):
        """Extract text from TXT file"""
        with open(self.resume_path, "r", encoding="utf-8") as file:
            return file.read()

    def get_resume_content(self):
        return self.resume_text
