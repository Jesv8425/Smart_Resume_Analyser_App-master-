import spacy
import pdfplumber
import pandas as pd
from spacy.matcher import PhraseMatcher

# Load spaCy model
nlp = spacy.load("en_core_web_sm")

# Load predefined skills from CSV
skills_df = pd.read_csv("skills_1.csv")  # Ensure the CSV has a column named 'skills'
skill_phrases = [skill.lower() for skill in skills_df["skills"].dropna().tolist()]  # Remove NaN values

# Create a spaCy PhraseMatcher
matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
patterns = [nlp(skill) for skill in skill_phrases]
matcher.add("SKILL_MATCH", patterns)

# Function to extract text from PDF
def extract_text_from_pdf(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        text = "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])
    return text

# Function to extract skills using spaCy PhraseMatcher
def extract_skills(text):
    doc = nlp(text)
    matches = matcher(doc)
    extracted_skills = set([doc[start:end].text for match_id, start, end in matches])
    return list(extracted_skills)


if __name__ == '__main__':
    # Example Usage
    pdf_path = "/Users/jesvanth/Desktop/Smart_Resume_Analyser_App-master /Uploaded_Resumes/resume (1).pdf"  # Change to your file path
    text = extract_text_from_pdf(pdf_path)
    extracted_skills = extract_skills(text)
    print("Extracted Skills:", extracted_skills)
