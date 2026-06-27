// TD19 — Basic build system
// Concatenates JS files in dependency order into a single bundle.
// Run: node build.js

const fs = require('fs');
const path = require('path');

const SRC = path.join(__dirname, 'src');
const DIST = path.join(__dirname, 'dist');

const JS_ORDER = [
  'js/vendor/supabase.min.js',
  'js/auth/config.js',
  'js/vendor-loader.js',
  'js/auth/client.js',
  'js/auth/session.js',
  'js/auth/auth.js',
  'js/auth/auth-ui.js',
  'js/theme.js',
  'js/vendor/FileSaver.min.js',
  'js/dialogs.js',
  'js/i18n.js',
  'js/analytics.js',
  'js/onboarding.js',
  'js/renderer.js',
  'js/selection.js',
  'js/ui.js',
  'js/documents/doc-utils.js',
  'js/editor.js',
  'js/autocomplete.js',
  'js/format.js',
  'js/documents/import.js',
  'js/documents/export.js',
  'js/documents/documents.js',
  'js/sync/sync-queue.js',
  'js/sync/sync-resolver.js',
  'js/sync/sync-manager.js',
  'js/documents-cloud/documents-api.js',
  'js/documents-cloud/documents-state.js',
  'js/documents-cloud/documents-ui.js',
  'js/summaries/summaries-api.js',
  'js/summaries/summaries-ui.js',
  'js/settings-sync/settings-api.js',
  'js/settings-sync/settings-sync.js',
  'js/app.js',
];

if (!fs.existsSync(DIST)) fs.mkdirSync(DIST, { recursive: true });
if (!fs.existsSync(path.join(DIST, 'css'))) fs.mkdirSync(path.join(DIST, 'css'), { recursive: true });

// Bundle JS — also write to src/js/ for direct Flask serving
let bundle = '';
let skipped = [];
for (const file of JS_ORDER) {
  const fp = path.join(SRC, file);
  if (fs.existsSync(fp)) {
    bundle += `\n// === ${file} ===\n`;
    bundle += fs.readFileSync(fp, 'utf-8');
    bundle += '\n';
  } else {
    skipped.push(file);
  }
}
fs.writeFileSync(path.join(DIST, 'bayan.bundle.js'), bundle, 'utf-8');
fs.writeFileSync(path.join(SRC, 'js', 'bayan.bundle.js'), bundle, 'utf-8');

// Copy CSS
const CSS_FILES = ['tokens.css', 'base.css', 'components.css', 'tailwind-output.css'];
for (const cssFile of CSS_FILES) {
  const src = path.join(SRC, 'css', cssFile);
  if (fs.existsSync(src)) {
    fs.copyFileSync(src, path.join(DIST, 'css', cssFile));
  }
}

// Copy other static assets
const COPY_FILES = ['index.html', 'favicon.svg', 'sw.js'];
for (const f of COPY_FILES) {
  const src = path.join(SRC, f);
  if (fs.existsSync(src)) {
    fs.copyFileSync(src, path.join(DIST, f));
  }
}

console.log(`Build complete: ${JS_ORDER.length - skipped.length} JS files bundled`);
if (skipped.length) console.log(`Skipped (not found): ${skipped.join(', ')}`);
console.log(`Output: ${DIST}/`);
