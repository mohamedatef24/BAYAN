from pathlib import Path
import sys
import json
from pprint import pprint

# Make sure src is importable when running from repo root
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from model_loader import SummarizationModel, SUMMARIZATION_PATH

text = (
    "سيلعب المنتخب المغربي اليوم بقياده سفيان امرابط ووليد الركراكي امام المنتخب البرازيلي "
    "بقياده فينيسيوس وكارول انشيلوتي ورافينها في كاس العالم الساعه الواحده صباحا"
)

print("Summarization path:", SUMMARIZATION_PATH)
print("Files:", list(Path(SUMMARIZATION_PATH).iterdir()))

print("\nLoading model (this may take a while)...")
m = SummarizationModel(SUMMARIZATION_PATH)
print("Model loaded. Device:", m.device)


def show_tokenization(text):
    tok = m.tokenizer(text, truncation=True, padding=True, return_tensors="pt")
    print('\n=== Tokenization ===')
    print('Decoded back (tokenizer):', m.tokenizer.decode(tok['input_ids'][0], skip_special_tokens=False))
    print('Input ids (first 60):', tok['input_ids'][0][:60].tolist())
    print('Tokenizer special tokens:', m.tokenizer.special_tokens_map)


def show_config():
    print('\n=== Model Config ===')
    cfg = m.model.config
    # print a subset for readability
    info = {k: getattr(cfg, k) for k in ['vocab_size', 'max_length', 'min_length', 'num_beams', 'early_stopping', 'decoder_start_token_id'] if hasattr(cfg, k)}
    pprint(info)


def generate_and_print(desc, **gen_kwargs):
    print(f"\n--- Generating: {desc} ---")
    try:
        inputs = m.tokenizer(text, truncation=True, padding=True, return_tensors='pt')
        inputs = {k: v.to(m.device) for k, v in inputs.items()}

        # Ensure generation config has sensible defaults if missing
        if gen_kwargs.get('num_beams') is None:
            gen_kwargs['num_beams'] = 1

        # Use return_dict_in_generate to capture sequences
        gen_kwargs.setdefault('return_dict_in_generate', True)
        gen_kwargs.setdefault('output_scores', True)

        out = m.model.generate(**inputs, **gen_kwargs)

        # support both GenerationOutput and plain tensor
        seq = None
        if hasattr(out, 'sequences'):
            seq = out.sequences[0].cpu().tolist()
        else:
            seq = out[0].cpu().tolist()

        print('Generated token ids (truncated 128):', seq[:128])
        decoded = m.tokenizer.decode(seq, skip_special_tokens=True)
        print('Decoded generated:', decoded)
    except Exception as e:
        print('Generation failed:', repr(e))


show_tokenization(text)
show_config()

# Read training history to look for input formatting / prompts
train_hist_path = Path(SUMMARIZATION_PATH) / 'training_history.json'
if train_hist_path.exists():
    try:
        th = json.load(open(train_hist_path, 'r', encoding='utf-8'))
        print('\n=== training_history.json keys ===')
        pprint(list(th.keys())[:20])
        # print any example prompts if present
        if 'example' in th:
            print('\nExample from training_history.json:')
            pprint(th['example'])
        else:
            # try common keys
            for k in ('prompt', 'template', 'examples'):
                if k in th:
                    print(f'Found {k}:')
                    pprint(th[k])
    except Exception as e:
        print('Could not read training_history.json:', e)


# 1) Baseline (current defaults)
generate_and_print('baseline (defaults)')

# 2) Beam search (reduce hallucination)
generate_and_print('beam search (num_beams=6, no_repeat_ngram_size=3)', num_beams=6, early_stopping=True, no_repeat_ngram_size=3, max_length=150, min_length=20)

# 3) Force decoder_start to BOS (some models expect it)
try:
    m.model.config.forced_bos_token_id = m.tokenizer.bos_token_id
    generate_and_print('forced_bos_token_id set to tokenizer.bos_token_id (beam=6)', num_beams=6, early_stopping=True, no_repeat_ngram_size=3, max_length=150, min_length=20)
except Exception as e:
    print('Could not set forced_bos_token_id:', e)

# 4) Sampling variations (may increase relevance or diversity)
generate_and_print('sampling (do_sample=True, top_p=0.9, temp=0.8)', do_sample=True, top_p=0.9, temperature=0.8, max_length=120)

# 5) Try adding a short explicit prefix (if model was trained with templates)
for prefix in ['','تلخيص: ', 'summarize: ', '<s> تلخيص: ']:
    prefix_text = prefix + text
    print(f"\n>>> Trying prefix: '{prefix}'")
    try:
        inputs = m.tokenizer(prefix_text, truncation=True, padding=True, return_tensors='pt')
        inputs = {k: v.to(m.device) for k, v in inputs.items()}
        out = m.model.generate(**inputs, num_beams=6, early_stopping=True, no_repeat_ngram_size=3, max_length=150, min_length=20, return_dict_in_generate=True, output_scores=True)
        seq = out.sequences[0].cpu().tolist() if hasattr(out, 'sequences') else out[0].cpu().tolist()
        print('Decoded generated with prefix:', m.tokenizer.decode(seq, skip_special_tokens=True))
    except Exception as e:
        print('Prefix generation failed:', e)

print('\nAll experiments completed.')
