import gradio as gr

import re
from AraSpell import initialize

# تهيئة المصحح الإملائي وتحميل الموديل
sc = initialize(use_contextual=True)

import Levenshtein

def align_words(in_words, out_words):
    n = len(in_words)
    m = len(out_words)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    
    for i in range(1, n + 1):
        dp[i][0] = dp[i-1][0] + len(in_words[i-1])
    for j in range(1, m + 1):
        dp[0][j] = dp[0][j-1] + len(out_words[j-1])
        
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost_replace = Levenshtein.distance(in_words[i-1], out_words[j-1])
            dp[i][j] = min(
                dp[i-1][j-1] + cost_replace,
                dp[i-1][j] + len(in_words[i-1]),
                dp[i][j-1] + len(out_words[j-1])
            )
            
    i, j = n, m
    ops = []
    while i > 0 or j > 0:
        if i > 0 and j > 0:
            cost_replace = Levenshtein.distance(in_words[i-1], out_words[j-1])
            if dp[i][j] == dp[i-1][j-1] + cost_replace:
                if cost_replace == 0:
                    ops.append(('equal', [in_words[i-1]], [out_words[j-1]]))
                else:
                    ops.append(('replace', [in_words[i-1]], [out_words[j-1]]))
                i -= 1
                j -= 1
                continue
        if i > 0 and dp[i][j] == dp[i-1][j] + len(in_words[i-1]):
            ops.append(('delete', [in_words[i-1]], []))
            i -= 1
        else:
            ops.append(('insert', [], [out_words[j-1]]))
            j -= 1
            
    ops.reverse()
    
    merged_ops = []
    for op, in_w, out_w in ops:
        if not merged_ops:
            merged_ops.append([op, in_w, out_w])
            continue
            
        prev_op = merged_ops[-1][0]
        if op != 'equal' and prev_op != 'equal' and not (op == 'replace' and prev_op == 'replace'):
            merged_ops[-1][0] = 'replace'
            merged_ops[-1][1].extend(in_w)
            merged_ops[-1][2].extend(out_w)
        else:
            merged_ops.append([op, in_w, out_w])
            
    return merged_ops

def generate_highlights(input_text):
    if not input_text or not input_text.strip():
        return [], {}
        
    corrected_text = sc.correct(input_text)
    
    in_words = input_text.split()
    out_words = corrected_text.split()
    
    ops = align_words(in_words, out_words)
    
    highlight_list = []
    suggestions_map = {}
    
    idx = 0
    for tag, in_w, out_w in ops:
        if tag == 'equal':
            for w in in_w:
                highlight_list.append((w, None))
                highlight_list.append((" ", None))
                idx += 2
        elif tag == 'replace' or tag == 'insert' or tag == 'delete':
            in_phrase = " ".join(in_w) if in_w else "[ناقص]"
            out_phrase = " ".join(out_w) if out_w else "(حذف الكلمة)"
            
            highlight_list.append((in_phrase, " "))
            sugs = [out_phrase]
            
            if len(in_w) == 1 and len(out_w) == 1:
                clean_w = re.sub(r'[^\w]', '', in_w[0])
                try:
                    edit_cands = sc.edit_corrector.known(sc.edit_corrector.edits1(clean_w))
                    if edit_cands:
                        edit_cands = sorted(list(edit_cands), key=lambda x: sc.vocab_manager.get_frequency_rank(x))
                        for c in edit_cands:
                            if c not in sugs and len(sugs) < 3:
                                sugs.append(c)
                except Exception:
                    pass
                    
            suggestions_map[idx] = sugs
            highlight_list.append((" ", None))
            idx += 2
            
    if highlight_list and highlight_list[-1] == (" ", None):
        highlight_list.pop()
        
    return highlight_list, suggestions_map

# ==========================================
# تصميم واجهة المستخدم التفاعلية (Gradio Blocks)
# ==========================================
with gr.Blocks(theme=gr.themes.Soft(), css="""
    .highlight-error { background-color: #ffcccc !important; border-radius: 4px; padding: 2px; }
    .rtl-text { direction: rtl !important; text-align: right !important; }
""") as iface:
    
    gr.Markdown("# 📝 AraSpell - المصحح الإملائي التفاعلي")
    gr.Markdown("أدخل النص أدناه واضغط على **فحص النص**. سيقوم النظام بتلوين الأخطاء باللون الأحمر. **انقر على الكلمة الملونة** لتظهر لك خيارات التصحيح أسفلها!")
    
    # متغيرات حالة (State) لحفظ البيانات خلف الكواليس
    suggestions_state = gr.State({})
    current_edit_index = gr.State(None)
    highlight_list_state = gr.State([])
    
    with gr.Row():
        with gr.Column(scale=1):
            input_box = gr.Textbox(lines=8, label="النص الأصلي", placeholder="أدخل النص العربي هنا...")
            check_btn = gr.Button("🔍 فحص النص", variant="primary")
            
        with gr.Column(scale=1):
            output_highlights = gr.HighlightedText(
                label="النتيجة (اضغط على الكلمات الملونة للتصحيح)",
                combine_adjacent=False,
                show_legend=False,
                color_map={" ": "red"},
                elem_classes="rtl-text"
            )
            
            # لوحة الاقتراحات (مخفية في البداية)
            with gr.Group(visible=False) as suggestion_panel:
                gr.Markdown("### 💡 اختر التصحيح المناسب:")
                suggestion_radio = gr.Radio(choices=[], label="")
                apply_btn = gr.Button("✅ تطبيق التصحيح", variant="secondary")

    # 1. عند الضغط على فحص النص
    def process_text(text):
        h_list, s_map = generate_highlights(text)
        # إرجاع: النص المظلل، قاموس الاقتراحات، قائمة التظليل (State)، وإخفاء لوحة الاقتراحات
        return h_list, s_map, h_list, gr.update(visible=False)

    check_btn.click(
        fn=process_text,
        inputs=[input_box],
        outputs=[output_highlights, suggestions_state, highlight_list_state, suggestion_panel]
    )
    
    # 2. عند النقر على أي كلمة داخل النص المظلل
    def on_highlight_click(evt: gr.SelectData, s_map):
        index = evt.index
        # معالجة مشكلة تحويل المفاتيح إلى نصوص (Strings) في Gradio State
        if index in s_map:
            choices = s_map[index]
        elif str(index) in s_map:
            choices = s_map[str(index)]
        else:
            # إخفاء اللوحة إذا ضغط على كلمة صحيحة
            return gr.update(visible=False), gr.update(), None
            
        # إظهار اللوحة وتحديث الخيارات
        return gr.update(visible=True), gr.update(choices=choices, value=choices[0]), index

    output_highlights.select(
        fn=on_highlight_click,
        inputs=[suggestions_state],
        outputs=[suggestion_panel, suggestion_radio, current_edit_index]
    )
    
    # 3. عند اختيار اقتراح والضغط على "تطبيق"
    def apply_correction(choice, edit_idx, h_list):
        if edit_idx is not None and choice:
            # تحديث الكلمة في قائمة التظليل (بدون إعادة تشغيل الموديل لتكون سريعة جداً)
            if choice == "(حذف الكلمة)":
                h_list[edit_idx] = ("", None)
            else:
                h_list[edit_idx] = (choice, None)
                
            # إعادة بناء النص الجديد
            new_text = "".join([t[0] for t in h_list])
            
            # إرجاع: تحديث مربع الإدخال، التظليل الجديد، بقاء الاقتراحات كما هي، State الجديد، وإخفاء اللوحة
            return new_text, h_list, gr.update(), h_list, gr.update(visible=False)
            
        return gr.update(), gr.update(), gr.update(), gr.update(), gr.update()

    apply_btn.click(
        fn=apply_correction,
        inputs=[suggestion_radio, current_edit_index, highlight_list_state],
        outputs=[input_box, output_highlights, suggestions_state, highlight_list_state, suggestion_panel]
    )

if __name__ == "__main__":
    iface.launch()
