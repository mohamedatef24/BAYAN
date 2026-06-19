import os
import re

files = [
    r'd:\BAYAN\src\nlp\spelling\araspell_service.py',
    r'd:\BAYAN\src\nlp\grammar\grammar_service.py',
    r'd:\BAYAN\src\nlp\punctuation\punctuation_service.py',
    r'd:\BAYAN\src\nlp\autocomplete\autocomplete_service.py'
]

for file in files:
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if 'grammar_service' in file:
        content = content.replace('    global _grammar_checker, _load_error\n\n    if _grammar_checker is not None:\n        return _grammar_checker\n\n    try:', '    global _grammar_checker, _load_error, _load_lock\n\n    if _grammar_checker is not None:\n        return _grammar_checker\n\n    with _load_lock:\n        if _grammar_checker is not None:\n            return _grammar_checker\n\n        try:')
        content = re.sub(r'(?<=        try:\n)(.*?)(?=\n    except|\n\n)', lambda m: m.group(1).replace('\n    ', '\n        '), content, flags=re.DOTALL)
        content = content.replace('    except Exception as e:\n        _load_error = str(e)\n        logger.error(f"Grammar model failed to load: {e}")\n        raise RuntimeError(f"Grammar model failed to load: {e}")\n\n    return _grammar_checker', '        except Exception as e:\n            _load_error = str(e)\n            logger.error(f"Grammar model failed to load: {e}")\n            raise RuntimeError(f"Grammar model failed to load: {e}")\n\n        return _grammar_checker')
    elif 'araspell_service' in file:
        content = content.replace('        if _load_error is not None:\n            raise RuntimeError(f"Spelling model previously failed to load: {_load_error}")\n\n    try:\n        t0 = time.time()', '        if _load_error is not None:\n            raise RuntimeError(f"Spelling model previously failed to load: {_load_error}")\n\n        try:\n            t0 = time.time()')
        content = content.replace('\n    try:', '\n        try:')
        content = content.replace('\n    except', '\n        except')
        content = content.replace('\n    return _spell_checker', '\n        return _spell_checker')
        lines = content.split('\n')
        in_try = False
        for i, line in enumerate(lines):
            if 'try:' in line and 'Loading AraSpell' in lines[i+1]:
                in_try = True
            elif 'return _spell_checker' in line and in_try:
                lines[i] = '        return _spell_checker'
                in_try = False
            elif in_try and line.startswith('    '):
                if not line.startswith('        '):
                    lines[i] = '    ' + line
        content = '\n'.join(lines)
    elif 'punctuation_service' in file:
        content = content.replace('        if _load_error is not None:\n            raise RuntimeError(f"Punctuation model previously failed to load: {_load_error}")\n\n    try:', '        if _load_error is not None:\n            raise RuntimeError(f"Punctuation model previously failed to load: {_load_error}")\n\n        try:')
        lines = content.split('\n')
        in_try = False
        for i, line in enumerate(lines):
            if 'try:' in line and 'Loading PuncAra-v1' in lines[i+1]:
                in_try = True
            elif 'return _punctuation_checker' in line and in_try:
                lines[i] = '        return _punctuation_checker'
                in_try = False
            elif in_try and line.startswith('    '):
                if not line.startswith('        '):
                    lines[i] = '    ' + line
        content = '\n'.join(lines)
    elif 'autocomplete_service' in file:
        content = content.replace('    with _load_lock:\n        if _autocomplete_engine is not None:\n            return _autocomplete_engine\n\n    t0 = time.time()', '    with _load_lock:\n        if _autocomplete_engine is not None:\n            return _autocomplete_engine\n\n        t0 = time.time()')
        lines = content.split('\n')
        in_try = False
        for i, line in enumerate(lines):
            if 't0 = time.time()' in line and '[Autocomplete] Initializing' in lines[i+1]:
                in_try = True
            elif 'return _autocomplete_engine' in line and in_try:
                lines[i] = '        return _autocomplete_engine'
                in_try = False
            elif in_try and line.startswith('    '):
                if not line.startswith('        '):
                    lines[i] = '    ' + line
        content = '\n'.join(lines)
        
    with open(file, 'w', encoding='utf-8') as f:
        f.write(content)
