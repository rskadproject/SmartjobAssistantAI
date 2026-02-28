import spacy
import re
from collections import Counter

# Load spaCy NLP model
try:
    nlp = spacy.load("en_core_web_sm")
except:
    print("Warning: spaCy model en_core_web_sm not found. Falling back to basic regex extraction.")
    nlp = None

BASIC_STOP_WORDS = {"a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but", "by", "can't", "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down", "during", "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't", "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here", "here's", "hers", "herself", "him", "himself", "his", "how", "how's", "i", "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it", "it's", "its", "itself", "let's", "me", "more", "most", "mustn't", "my", "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other", "ought", "our", "ours", "ourselves", "out", "over", "own", "same", "shan't", "she", "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such", "than", "that", "that's", "the", "their", "theirs", "them", "themselves", "then", "there", "there's", "these", "they", "they'd", "they'll", "they're", "they've", "this", "those", "through", "to", "too", "under", "until", "up", "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were", "weren't", "what", "what's", "when", "when's", "where", "where's", "which", "while", "who", "who's", "whom", "why", "why's", "with", "won't", "would", "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours", "yourself", "yourselves", "experience", "education", "skills", "projects", "work", "year", "years", "month", "months"}

class ATSScanner:
    def __init__(self):
        self.sections_keywords = {
            "Contact info": ["email", "phone", "linkedin", "github", "address", "mobile", "contact"],
            "Skills": ["skills", "core competencies", "technical skills", "expertise"],
            "Experience": ["experience", "employment", "work history", "professional background"],
            "Education": ["education", "academic", "degree", "university", "college"],
            "Projects": ["projects", "personal projects", "academic projects", "portfolio"],
            "Certifications": ["certifications", "certificates", "licenses", "courses"]
        }

    def parse_resume_info(self, text):
        """Extract Basic Info like Email and Phone using regex, and Name using spaCy NER."""
        # Regex for Email
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
        email = email_match.group(0) if email_match else None
        
        # Regex for Phone
        phone_match = re.search(r'(\+?\d{1,3}[\s-]?)?\(?\d{3}\)?[\s-]?\d{3}[\s-]?\d{4}', text)
        phone = phone_match.group(0) if phone_match else None
        
        # Extract Name using spaCy Entities (PERSON) if available
        name = None
        if nlp:
            doc = nlp(text)
            for ent in doc.ents:
                if ent.label_ == "PERSON":
                    name = ent.text
                    break
        else:
            # Very basic fallback: just grab the first line of the resume
            lines = [l.strip() for l in text.split('\n') if l.strip()]
            if lines: name = lines[0]
                
        return {
            "name": name,
            "email": email,
            "phone": phone
        }

    def extract_keywords(self, text):
        """Extract nouns, proper nouns, and specific keywords to match against the JD."""
        if not text:
            return []
            
        keywords = []
        if nlp:
            doc = nlp(text.lower())
            for token in doc:
                if not token.is_stop and not token.is_punct and not token.is_space:
                    if token.pos_ in ['NOUN', 'PROPN', 'ADJ']:
                        keywords.append(token.lemma_)
        else:
            # Fallback regex extraction
            words = re.findall(r'\b[a-z]{3,}\b', text.lower())
            keywords = [w for w in words if w not in BASIC_STOP_WORDS]
                    
        # Remove duplicates while preserving order
        return list(dict.fromkeys(keywords))

    def detect_sections(self, text):
        """Determine which standard resume sections are present based on headers."""
        text_lower = text.lower()
        found_sections = {}
        
        for section, keywords in self.sections_keywords.items():
            found = False
            for kw in keywords:
                # Look for the section title (might be preceded/followed by newlines or formatting)
                if re.search(r'(?m)^[\s#\*\-]*' + re.escape(kw) + r'[\s:]*$', text_lower) or \
                   f"\n{kw}\n" in f"\n{text_lower}\n":
                    found = True
                    break
            found_sections[section] = "Found" if found else "Missing"
            
        return found_sections

    def compare_keywords(self, resume_kws, jd_kws):
        """Compare resume keywords with JD keywords to find matches, missing, and extra."""
        res_set = set(resume_kws)
        jd_set = set(jd_kws)
        
        matched = list(res_set.intersection(jd_set))
        missing = list(jd_set - res_set)
        extra = list(res_set - jd_set)
        
        jd_provided = len(jd_set) > 0
        
        return {
            "matched": matched,
            "missing": missing,
            "extra": extra,
            "jd_provided": jd_provided,
            "match_rate": (len(matched) / len(jd_set)) if jd_provided else 1.0
        }

    def calculate_score(self, keyword_data, sections_dict, info_dict):
        """Calculate score out of 100 based on weights."""
        score = 0
        
        # 1. Keyword Match (40% Weight)
        match_rate = keyword_data['match_rate']
        
        # If no JD was provided, assume keywords are perfectly fine so they aren't penalized
        if not keyword_data.get('jd_provided', True):
            keyword_score = 40
        else:
            keyword_score = min(40, round(match_rate * 40))
            
        score += keyword_score
        
        # 2. Section Completeness (30% Weight)
        # Check standard sections
        expected_sections = ["Experience", "Education", "Skills", "Projects"]
        found_count = sum(1 for sec in expected_sections if sections_dict.get(sec) == "Found")
        section_score = round((found_count / len(expected_sections)) * 30)
        score += section_score
        
        # 3. Contact Info Presence (15% Weight)
        contact_score = 0
        if info_dict.get('email'): contact_score += 7.5
        if info_dict.get('phone'): contact_score += 7.5
        score += contact_score
        
        # 4. Formatting Quality Proxy (15% Weight)
        # We proxy formatting quality by checking text length and extraction success
        format_score = 15
        if not info_dict.get('email') and not info_dict.get('name'):
            format_score -= 10 # Likely poor formatting if it can't find basic info
        score += format_score
        
        return {
            "total_score": int(score),
            "breakdown": {
                "keyword_score": int(keyword_score), # out of 40
                "section_score": int(section_score), # out of 30
                "contact_score": int(contact_score), # out of 15
                "format_score": int(format_score)    # out of 15
            }
        }
