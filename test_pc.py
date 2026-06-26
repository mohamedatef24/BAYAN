import io
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(r'c:\Users\dell\PycharmProjects\JupyterProject1\PythonProject\BAYAN\src')))

import logging
from app import app as flask_app

class TestPC004(unittest.TestCase):
    def test_pc004(self):
        text = "الرجال يعملون في المصنعو"
        client = flask_app.test_client()
        response = client.post('/api/analyze', json={'text': text})
        res = response.get_json()
        print("Final:", res.get('corrected_text', res))

if __name__ == '__main__':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    unittest.main()
