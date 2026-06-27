import asyncio
import os
import sys

# Add src to path
sys.path.append(os.path.abspath('src'))

from app import analyze_text

def test_grammar_cases():
    cases = {
        "1. النعت والمنعوت (تذكير/تأنيث)": "رأيت سيارة جميل",
        "2. العدد والمعدود (من 3-10)": "اشتريت ثلاثة سيارات",
        "3. حروف الجر (مجرور)": "ذهبت إلى المهندسون",
        "4. الأسماء الخمسة (مفعول به منصوب)": "رأيت أبوك",
        "5. المضاف والمضاف إليه (جر)": "جاء مدير الشركةَ",
        "6. التاء المربوطة والهاء": "هذة مدرسة كبيرة"
    }

    print("=== Testing Grammar Rules ===")
    for desc, text in cases.items():
        print(f"\n[{desc}]")
        print(f"Input : {text}")
        
        # We need to run analyze_text which is async? No, it's a normal function if we look at the code, wait, let's check.
        # Actually app.analyze_text might not be async, let's call it.
        try:
            result, _ = analyze_text(text)
            
            # The result is a list of suggestions.
            # Let's apply them to get the final text.
            corrected = text
            # Sort suggestions by start index descending to not mess up offsets
            for sugg in sorted(result, key=lambda x: x['start'], reverse=True):
                corrected = corrected[:sugg['start']] + sugg['correction'] + corrected[sugg['end']:]
                
            print(f"Output: {corrected}")
            print(f"Diffs : {result}")
        except Exception as e:
            print(f"Error : {e}")

if __name__ == '__main__':
    test_grammar_cases()
