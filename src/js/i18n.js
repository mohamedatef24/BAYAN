// M4 — Basic i18n support
// Lightweight translation layer. Arabic is default; English fallback available.
// Usage: i18n('key') returns translated string. setLang('en') switches language.

var _i18n = (function() {
  var _lang = 'ar';

  var _strings = {
    ar: {
      'app.title': 'بيان',
      'editor.placeholder': 'ابدأ الكتابة هنا...',
      'editor.analyze': 'تحليل',
      'editor.clear': 'مسح',
      'editor.copy': 'نسخ',
      'editor.wordCount': 'كلمات',
      'editor.charCount': 'أحرف',
      'suggestions.spelling': 'إملاء',
      'suggestions.grammar': 'نحو',
      'suggestions.punctuation': 'ترقيم',
      'suggestions.empty': 'لا توجد اقتراحات',
      'toast.copied': '✓ تم النسخ',
      'toast.saved': '✓ تم الحفظ',
      'toast.corrected': '✓ تم التصحيح',
      'toast.error': 'حدث خطأ',
      'nav.home': 'الرئيسية',
      'nav.editor': 'المحرر',
      'summary.generate': 'توليد ملخص',
      'summary.copy': 'نسخ الملخص',
      'summary.long': 'طويل',
      'summary.medium': 'متوسط',
      'summary.short': 'قصير',
      'dialect.convert': 'تحويل إلى الفصحى',
      'quran.search': 'بحث وتدقيق',
      'settings.theme': 'المظهر',
      'settings.dark': 'داكن',
      'settings.light': 'فاتح',
      'auth.login': 'تسجيل الدخول',
      'auth.logout': 'تسجيل الخروج',
      'auth.signup': 'إنشاء حساب',
    },
    en: {
      'app.title': 'Bayan',
      'editor.placeholder': 'Start typing here...',
      'editor.analyze': 'Analyze',
      'editor.clear': 'Clear',
      'editor.copy': 'Copy',
      'editor.wordCount': 'words',
      'editor.charCount': 'characters',
      'suggestions.spelling': 'Spelling',
      'suggestions.grammar': 'Grammar',
      'suggestions.punctuation': 'Punctuation',
      'suggestions.empty': 'No suggestions',
      'toast.copied': '✓ Copied',
      'toast.saved': '✓ Saved',
      'toast.corrected': '✓ Corrected',
      'toast.error': 'Error occurred',
      'nav.home': 'Home',
      'nav.editor': 'Editor',
      'summary.generate': 'Generate Summary',
      'summary.copy': 'Copy Summary',
      'summary.long': 'Long',
      'summary.medium': 'Medium',
      'summary.short': 'Short',
      'dialect.convert': 'Convert to MSA',
      'quran.search': 'Search & Verify',
      'settings.theme': 'Theme',
      'settings.dark': 'Dark',
      'settings.light': 'Light',
      'auth.login': 'Sign In',
      'auth.logout': 'Sign Out',
      'auth.signup': 'Sign Up',
    }
  };

  function t(key) {
    var dict = _strings[_lang] || _strings['ar'];
    return dict[key] || _strings['ar'][key] || key;
  }

  function setLang(lang) {
    if (_strings[lang]) {
      _lang = lang;
      localStorage.setItem('bayan_lang', lang);
      document.documentElement.dir = lang === 'ar' ? 'rtl' : 'ltr';
      document.documentElement.lang = lang;
    }
  }

  function getLang() {
    return _lang;
  }

  function init() {
    var saved = localStorage.getItem('bayan_lang');
    if (saved && _strings[saved]) {
      _lang = saved;
    }
  }

  init();

  return { t: t, setLang: setLang, getLang: getLang };
})();

function i18n(key) {
  return _i18n.t(key);
}

function setLang(lang) {
  _i18n.setLang(lang);
}
