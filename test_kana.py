from camel_tools.tokenizers.word import simple_word_tokenize
from camel_tools.disambig.mle import MLEDisambiguator

def check_cases():
    mle = MLEDisambiguator.pretrained()
    text = "كان المعلمين نائمين"
    tokens = simple_word_tokenize(text)
    disambig_tokens = mle.disambiguate(tokens)
    for t in disambig_tokens:
        if t.analyses:
            a = t.analyses[0].analysis
            print(f"Word: {t.word}, POS: {a.get('pos')}, Case: {a.get('cas')}, Num: {a.get('num')}")

if __name__ == '__main__':
    check_cases()
