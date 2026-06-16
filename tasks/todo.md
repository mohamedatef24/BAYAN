# Task List: Phase 1 Editor Stabilization Refactor

## Milestone 1: Modularize Editor Logic
- [ ] Create folder `src/js/` if it doesn't exist
- [ ] Create `src/js/api.js` to handle all API communications
- [ ] Create `src/js/editor.js` to manage editor elements, events, and debouncing
- [ ] Create `src/js/renderer.js` to handle HTML escape and offset-based highlighting
- [ ] Create `src/js/selection.js` to save and restore range/cursor selections
- [ ] Create `src/js/ui.js` to handle tooltips, lists, scores, and loading spinners
- [ ] Update `src/index.html` to load modular JS files instead of inline scripts
- [ ] Verify that the frontend loads correctly and contains no console errors

## Milestone 2: Selection & Caret Preservation
- [ ] Implement `saveSelection` and `restoreSelection` based on character offset in `src/js/selection.js`
- [ ] Implement `getCaretCharacterOffsetWithin` and `setCaretCharacterOffsetWithin`
- [ ] Integrate selection restore before and after highlight updates
- [ ] Verify that typing does not cause cursor jumps or selection losses

## Milestone 3: Backend Offset Support
- [x] Implement `get_word_positions` in `src/app.py`
- [x] Implement `OffsetMapper` coordinate transform class in `src/app.py`
- [x] Rewrite `/api/analyze` in `src/app.py` to calculate exact character offsets (`start`, `end`) for all suggestions
- [ ] Verify using the test script `reproduce_issue.py` or `test_analyze_api.py` that the backend returns `start` and `end` offsets for all suggestions

## Milestone 4: Offset-Based Rendering
- [ ] Write offset-based rendering parser in `src/js/renderer.js`
- [ ] Ensure the renderer splits the text into highlighted spans and normal text nodes based on sorted, non-overlapping suggestions
- [ ] Support multiple occurrences of duplicate words by matching exact start/end offsets

## Milestone 5: Secure Rendering
- [ ] Implement `escapeHtml` utility in `src/js/renderer.js`
- [ ] Ensure all user inputs, suggestion corrections, and text are escaped before DOM insertion to prevent XSS

## Milestone 6: Tooltip Mapping
- [ ] Assign unique `data-suggestion-id` (index in suggestions list) to each highlight span
- [ ] Wire click event listeners on the editor container to detect suggestion spans, retrieve the suggestion, and open the tooltip dynamically

## Milestone 7: Integration & Validation
- [ ] Launch backend local server using `run_app.py`
- [ ] Run end-to-end browser check to verify that highlights, suggestions, cursor, and metrics work perfectly
- [ ] Document final results in `tasks/todo.md` and lessons in `tasks/lessons.md`
