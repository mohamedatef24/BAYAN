import io
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(r'c:\Users\dell\PycharmProjects\JupyterProject1\PythonProject\BAYAN\src')))

from app import apply_patches

class TestPC003(unittest.TestCase):
    def test_pc003(self):
        orig_text = "البنات يذهبون الي المدرسه"
        spelling_corr = "البنات يذهبون إلى المدرسة"
        grammar_corr = "البنات يذهبن إلى المدرسة"
        
        from src.nlp.stage_locker import StageLocker
        class MockCtx:
            def __init__(self):
                self.stage_locker = StageLocker()
                self.current_text = orig_text
                from nlp.offset_mapper import OffsetMapper
                self._mapper = OffsetMapper()
                self._mapper.init(orig_text)
            
            def add_patch(self, stage, start, end, corr, **kwargs):
                self.stage_locker.add_patch(stage, start, end)
                orig_start, orig_end = self._mapper.map_range(start, end)
                print(f"Adding patch: {self.current_text[start:end]} -> {corr} (mapped to {orig_start}:{orig_end})")
            
            def mutate_text(self, new_text, mapper_cls):
                self.current_text = new_text
                self._mapper.init(new_text)

        ctx = MockCtx()
        
        # Apply spelling
        apply_patches(orig_text, orig_text, spelling_corr, "spelling", ctx)
        ctx.mutate_text(spelling_corr, None)
        
        # Apply grammar
        final = apply_patches(orig_text, spelling_corr, grammar_corr, "grammar", ctx)
        print("Final:", final)

if __name__ == '__main__':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    unittest.main()
