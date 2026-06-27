var _vendorCache = {};
function loadVendorScript(src) {
  if (_vendorCache[src]) return _vendorCache[src];
  _vendorCache[src] = new Promise(function(resolve, reject) {
    var s = document.createElement('script');
    s.src = src;
    s.onload = resolve;
    s.onerror = function() { delete _vendorCache[src]; reject(new Error('Failed to load ' + src)); };
    document.head.appendChild(s);
  });
  return _vendorCache[src];
}
