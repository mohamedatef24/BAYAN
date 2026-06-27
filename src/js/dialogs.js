/* Bayan — Custom Modal Dialogs
 * Replaces native prompt()/confirm() with themed RTL dialogs.
 */

(function() {
  var _overlay = null;

  function _getOverlay() {
    if (_overlay) return _overlay;
    _overlay = document.createElement('div');
    _overlay.className = 'bayan-dialog-overlay';
    _overlay.addEventListener('click', function(e) {
      if (e.target === _overlay) _dismiss();
    });
    document.body.appendChild(_overlay);
    return _overlay;
  }

  var _currentReject = null;

  function _dismiss() {
    if (_currentReject) { _currentReject('dismissed'); _currentReject = null; }
    var ov = _getOverlay();
    ov.classList.remove('bayan-dialog-visible');
    setTimeout(function() { ov.innerHTML = ''; }, 200);
  }

  function _show(html) {
    var ov = _getOverlay();
    ov.innerHTML = html;
    requestAnimationFrame(function() { ov.classList.add('bayan-dialog-visible'); });
    var input = ov.querySelector('.bayan-dialog-input');
    if (input) setTimeout(function() { input.focus(); input.select(); }, 50);
  }

  /**
   * Custom confirm dialog.
   * @param {string} message
   * @returns {Promise<boolean>}
   */
  window.bayanConfirm = function(message) {
    return new Promise(function(resolve) {
      _currentReject = function() { resolve(false); };
      _show(
        '<div class="bayan-dialog">' +
          '<div class="bayan-dialog-body">' + _esc(message) + '</div>' +
          '<div class="bayan-dialog-actions">' +
            '<button type="button" class="bayan-dialog-btn bayan-dialog-btn--cancel">إلغاء</button>' +
            '<button type="button" class="bayan-dialog-btn bayan-dialog-btn--confirm">تأكيد</button>' +
          '</div>' +
        '</div>'
      );
      var ov = _getOverlay();
      ov.querySelector('.bayan-dialog-btn--cancel').addEventListener('click', function() { _dismiss(); resolve(false); });
      ov.querySelector('.bayan-dialog-btn--confirm').addEventListener('click', function() { _dismiss(); resolve(true); });
    });
  };

  /**
   * Custom prompt dialog.
   * @param {string} message
   * @param {string} [defaultValue='']
   * @returns {Promise<string|null>} null if cancelled
   */
  window.bayanPrompt = function(message, defaultValue) {
    return new Promise(function(resolve) {
      _currentReject = function() { resolve(null); };
      _show(
        '<div class="bayan-dialog">' +
          '<div class="bayan-dialog-body">' + _esc(message) + '</div>' +
          '<input type="text" class="bayan-dialog-input" dir="rtl" value="' + _escAttr(defaultValue || '') + '">' +
          '<div class="bayan-dialog-actions">' +
            '<button type="button" class="bayan-dialog-btn bayan-dialog-btn--cancel">إلغاء</button>' +
            '<button type="button" class="bayan-dialog-btn bayan-dialog-btn--confirm">موافق</button>' +
          '</div>' +
        '</div>'
      );
      var ov = _getOverlay();
      var input = ov.querySelector('.bayan-dialog-input');
      ov.querySelector('.bayan-dialog-btn--cancel').addEventListener('click', function() { _dismiss(); resolve(null); });
      ov.querySelector('.bayan-dialog-btn--confirm').addEventListener('click', function() { _dismiss(); resolve(input.value); });
      input.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') { _dismiss(); resolve(input.value); }
        if (e.key === 'Escape') { _dismiss(); resolve(null); }
      });
    });
  };

  function _esc(s) { return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
  function _escAttr(s) { return String(s || '').replace(/"/g,'&quot;'); }
})();
