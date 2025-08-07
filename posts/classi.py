import os
import json
import random
from datetime import datetime, timedelta
import google.generativeai as genai
import pandas as pd
import textwrap
from posts.classify import extract_details_and_classify

# Configure Gemini AI
try:
    genai.configure(api_key='AIzaSyC86ncGOtqfoS9RJV-e_atb29VPpRYnUtE')
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    raise RuntimeError(f"Failed to initialize Gemini model: {str(e)}")

DEPARTMENTS = {
    "sports": "SPRT",
    "LSGD": "LSGD",
    "SC/ST": "SCST",
    "forest": "FRST",
    "Drinking water supply": "WATR",
    "Land issues": "LAND",
    "Education": "EDUC",
    "Life mission": "LIFE",
    "Disaster": "DSTR",
    "Road work": "ROAD",
    "Health": "HLTH",
    "Waste management": "WAST"
}

def generate_facebook_grievance_id():
    """Generate unique ID starting with GRIF"""
    today_str = datetime.now().strftime('%Y%m%d')
    random_number = random.randint(1000, 9999)
    return f"GRIF{today_str}{random_number}"

def extract_district_from_address(address):
    """Extract district code from address if mentioned"""
    district_mapping = {
        'തൃശൂർ': 'TSR',
        'തൃശ്ശൂർ': 'TSR',
        'എറണാകുളം': 'EKM',
        'കോഴിക്കോട്': 'KKD',
        # Add more district mappings as needed
    }
    for mal_district, code in district_mapping.items():
        if mal_district in address:
            return code
    return 'GEN'  # General if district not found

def classify_facebook_comment(comment):
    """Classify Facebook comment and prepare Excel data"""
    try:
        classification = extract_details_and_classify(comment)
        
        if 'error' in classification:
            return classification
        
        current_time = datetime.now()
        address = classification.get('address', '')
        
        return {
            'grievance_id': generate_facebook_grievance_id(),
            'date_filed': current_time.strftime('%Y-%m-%d %H:%M:%S'),
            'last_updated': current_time.strftime('%Y-%m-%d %H:%M:%S'),
            'subject': classification.get('subject', '')[:200],
            'description': classification.get('description', ''),
            'source': 'Facebook',
            'status': 'Pending',
            'priority': 'Medium',
            'due_date': (current_time + timedelta(days=30)).strftime('%Y-%m-%d'),
            'applicant_name': classification.get('applicant name', '')[:100],
            'applicant_address': address,
            'contact_number': classification.get('contact no', '')[:15],
            'email': classification.get('mail id', '')[:254],
            'department_id': DEPARTMENTS.get(classification.get('department', 'Other'), 'OTHR'),
            'district_id': extract_district_from_address(address)
        }
    except Exception as e:
        return {'error': str(e)}

def save_grievances_to_excel(grievance_data_list, output_file="facebook_grievances.xlsx"):
    """Save to Excel with only the specified fields"""
    if not grievance_data_list:
        return False
    
    try:
        # Filter out error entries
        valid_grievances = [g for g in grievance_data_list if 'error' not in g]
        if not valid_grievances:
            return False
            
        df = pd.DataFrame(valid_grievances)
        
        # Exact column order as specified
        columns = [
            'grievance_id',
            'date_filed',
            'last_updated',
            'subject',
            'description',
            'source',
            'status',
            'priority',
            'due_date',
            'applicant_name',
            'applicant_address',
            'contact_number',
            'email',
            'department_id',
            'district_id'
        ]
        
        # Ensure all columns exist (fill missing with empty strings)
        for col in columns:
            if col not in df.columns:
                df[col] = ''
        
        # Select and order columns exactly as specified
        df = df[columns]
        
        # Save to Excel
        df.to_excel(output_file, index=False, engine='openpyxl')
        return True
    except Exception as e:
        print(f"Error saving to Excel: {str(e)}")
        return False