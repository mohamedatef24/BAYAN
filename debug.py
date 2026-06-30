import base64
import re

with open('LOGOS/icon128.png', 'rb') as img:
    data_uri = 'data:image/png;base64,' + base64.b64encode(img.read()).decode('utf-8')

with open('src/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

match = re.search(r'src="data:image/png;base64,([A-Za-z0-9+/=]+)"', html)
if match:
    old_b64 = match.group(1)
    print('Match found!')
    if old_b64 == data_uri.split(',')[1]:
        print('The base64 in index.html is EXACTLY THE SAME as LOGOS/icon128.png')
    else:
        print('They are DIFFERENT. Length old:', len(old_b64), 'Length new:', len(data_uri.split(',')[1]))
else:
    print('No match found for the regex!')
