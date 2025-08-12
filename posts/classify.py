import os
import json
import google.generativeai as genai
import textwrap
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure Gemini AI
try:
    api_key = os.getenv('api_key')
    if not api_key:
        raise ValueError("API key not found in environment variables")
    genai.configure(api_key=api_key)
except Exception as e:
    raise RuntimeError(f"Failed to configure Gemini API: {str(e)}")

def extract_details_and_classify(comment):
    """
    Extract details and classify Facebook comments with structured output.
    Handles both English and Malayalam comments.
    """
    departments = [
        "sports", "LSGD", "SC/ST", "forest", "Drinking water supply",
        "Land issues", "Education", "Life mission", "Disaster",
        "Road work", "Health", "Waste management"
    ]

    prompt = textwrap.dedent(f"""
    Extract information from this comment and classify it. The comment may be in English or Malayalam.
    
    Departments: {', '.join(departments)}
    
    Extract these details:
    - subject: Brief summary of main issue (1 sentence)
    - description: Detailed problem description
    - applicant name: Person's name (if mentioned)
    - address: Full address (Panchayat/Ward/Village)
    - contact no: Phone number (if any)
    - mail id: Email (if any)
    - department: Most relevant department from the list
    
    Return JSON format EXACTLY like this:
    {{
        "subject": "summary here",
        "description": "detailed description here",
        "applicant name": "name or empty",
        "address": "address or empty",
        "contact no": "number or empty",
        "mail id": "email or empty",
        "department": "best matching department"
    }}

    Comment: "{comment}"
    """)

    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        
        json_str = response.text.strip()
        for prefix in ['```json', '```']:
            if json_str.startswith(prefix):
                json_str = json_str[len(prefix):]
            if json_str.endswith(prefix):
                json_str = json_str[:-len(prefix)]
        
        data = json.loads(json_str)
        
        if data['department'] not in departments:
            data['department'] = 'Other'
            
        return data
        
    except json.JSONDecodeError as e:
        return {
            "error": "JSON parsing failed",
            "details": str(e),
            "raw_response": response.text if 'response' in locals() else None
        }
    except Exception as e:
        return {
            "error": "Classification failed",
            "details": str(e)
        }