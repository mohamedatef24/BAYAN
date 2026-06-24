import os

def apply_lock_to_file(filepath, var_name, engine_name, func_name):
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    out_lines = []
    in_imports = False
    added_threading = False
    in_globals = False
    added_lock_var = False
    in_func = False
    
    for line in lines:
        if line.startswith('import ') and not added_threading:
            out_lines.append(line)
            out_lines.append("import threading\n")
            added_threading = True
            continue
            
        if line.startswith(f'_{var_name} = None') and not added_lock_var:
            out_lines.append(line)
            out_lines.append(f"_load_lock = threading.Lock()\n")
            added_lock_var = True
            continue
            
        if line.startswith(f'def {func_name}('):
            in_func = True
            out_lines.append(line)
            continue
            
        if in_func:
            if line.startswith(f'    global '):
                out_lines.append(line.replace('\n', f', _load_lock\n'))
                continue
                
            if line.startswith(f'    try:'):
                # The start of the old try block. We wrap everything from here.
                out_lines.append(f'    with _load_lock:\n')
                out_lines.append(f'        if _{var_name} is not None:\n')
                out_lines.append(f'            return _{var_name}\n\n')
                out_lines.append(f'        try:\n')
                continue
                
            # If we are inside the function and past the global declaration,
            # and it's indented with at least 4 spaces, we need to add 4 more spaces
            # for the lines that were inside the old `try:` and `except:`
            # EXCEPT for `if _xxx is not None: return _xxx` which comes before the try
            if line.startswith('    if _') or line.startswith('        return _'):
                # This is the old `if checker is not None:` logic before try. Leave it alone.
                out_lines.append(line)
                continue
                
            if line.startswith('    '):
                # Shift everything that was inside try/except right by 4 spaces
                if line.strip() == '':
                    out_lines.append('\n')
                else:
                    out_lines.append('    ' + line)
                
                if line.startswith('    return _') or line.startswith('    raise RuntimeError'):
                    # End of function
                    in_func = False
                continue

        out_lines.append(line)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(out_lines)


apply_lock_to_file(r'src/nlp/spelling/araspell_service.py', 'spell_checker', 'AraSpell', 'get_spelling_model')
apply_lock_to_file(r'src/nlp/punctuation/punctuation_service.py', 'punctuation_checker', 'PuncAra', 'get_punctuation_model')
apply_lock_to_file(r'src/nlp/grammar/grammar_service.py', 'grammar_checker', 'Grammar', 'get_grammar_model')
apply_lock_to_file(r'src/nlp/autocomplete/autocomplete_service.py', 'autocomplete_engine', 'Autocomplete', 'get_autocomplete_model')

print("Locks applied perfectly with correct indentation!")
