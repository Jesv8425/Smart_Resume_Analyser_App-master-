import json
from huggingface_hub import InferenceClient

# MODEL_NAME = "microsoft/Phi-4-mini-instruct"
# Alternative models you could try:
MODEL_NAME="mistralai/Mixtral-8x7B-Instruct-v0.1" #10gb
#MODEL_NAME = "microsoft/Phi-3-mini-4k-instruct"
# MODEL_NAME = "meta-llama/Llama-2-7b-chat-hf"

client = InferenceClient(token="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", model=MODEL_NAME)

def llm_resume_analysis(resume_text: str):
    prompt = f"""
    Analyze the following resume text and provide a JSON response with the following:
    - name: Full name of the candidate.
    - email: Email address of the candidate.
    - predicted_field: Which job field this resume is most suitable for.
    - extracted_skills: Top 10 technical or soft skills identified.
    - recommended_skills: based on identified skills suggest top 5 skills that are missing but should be included.
    - experience_level: Entry, Mid, or Senior level based on the content.
    - resume_score: Resume score out of 100 based on completeness.
    - suggestions: List of improvements or additions recommended.
    - recommended_courses: List of courses that can help the candidate improve their skills.
    - user_level: Entry, Mid, or Senior level based on the content.

    Resume Text:
    {resume_text}
    """
    try:
        response = client.text_generation(prompt, max_new_tokens=512)
        print(response)
        json_start = response.find('{')
        json_end = response.rfind('}') + 1
        return response[json_start:json_end]
    except json.JSONDecodeError:
        return "Error: Unable to parse the response as JSON."

def pdf_to_str(pdf_path: str) -> str:
    try:
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text
    except Exception as e:
        return f"Error: {str(e)}"

# test_resume = "I am a software engineer skilled in Python, React, and Docker. I built several ML projects using scikit-learn."
# llm_json_response = llm_resume_analysis(test_resume)
# response = json.loads(llm_json_response)
# formatted_response = json.dumps(response, indent=4)
# print(formatted_response)
