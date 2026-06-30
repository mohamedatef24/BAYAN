import base64
import re

with open('LOGOS/icon128.png', 'rb') as img:
    data_uri = 'data:image/png;base64,' + base64.b64encode(img.read()).decode('utf-8')

with open('src/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

html = re.sub(r'src="data:image/png;base64,[A-Za-z0-9+/=]+"', 'src="' + data_uri + '"', html)

with open('src/index.html', 'w', encoding='utf-8') as f:
    f.write(html)
