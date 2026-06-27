// L2 — Lightweight local analytics
// Tracks feature usage counts in localStorage. No external services.

var _bayanAnalytics = (function() {
  var STORAGE_KEY = 'bayan_analytics';

  function _load() {
    try {
      var raw = localStorage.getItem(STORAGE_KEY);
      return raw ? JSON.parse(raw) : {};
    } catch (e) { return {}; }
  }

  function _save(data) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
    } catch (e) {}
  }

  function track(event) {
    var data = _load();
    data[event] = (data[event] || 0) + 1;
    data._last = Date.now();
    _save(data);
  }

  function getStats() {
    return _load();
  }

  return { track: track, getStats: getStats };
})();

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { _bayanAnalytics: _bayanAnalytics };
}
