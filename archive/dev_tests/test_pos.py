import sys
sys.stdout.reconfigure(encoding='utf-8')
from camel_tools.tokenizers.word import simple_word_tokenize
from camel_tools.disambig.mle import MLEDisambiguator

mle = MLEDisambiguator.pretrained()
t = simple_word_tokenize('فتاتان جميل')
print([a.analyses[0].analysis for a in mle.disambiguate(t)])
