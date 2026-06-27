// L5 — Onboarding flow
// Shows a welcome overlay on first visit. Dismissed permanently.

function initOnboarding() {
  if (localStorage.getItem('bayan_onboarded')) return;

  var overlay = document.createElement('div');
  overlay.id = 'onboarding-overlay';
  overlay.style.cssText = 'position:fixed;inset:0;z-index:10000;background:rgba(0,0,0,.85);display:flex;align-items:center;justify-content:center;padding:24px';
  overlay.innerHTML =
    '<div style="background:var(--surface-1,#1a1a2e);border-radius:16px;max-width:480px;width:100%;padding:32px;text-align:center;direction:rtl;color:var(--text-primary,#f0f0f5)">' +
      '<h2 style="font-size:28px;margin-bottom:12px;background:linear-gradient(135deg,#6BA3E0,#A594E8);-webkit-background-clip:text;-webkit-text-fill-color:transparent">مرحبًا بك في بيان</h2>' +
      '<p style="color:var(--text-secondary,#9898ad);line-height:1.8;margin-bottom:24px">' +
        'منصة ذكاء اصطناعي متكاملة للكتابة العربية.<br>' +
        'تصحيح إملائي ونحوي وترقيمي، تلخيص نصوص، تدقيق قرآني، وتحويل لهجات.' +
      '</p>' +
      '<div style="display:flex;flex-direction:column;gap:12px;text-align:right;margin-bottom:24px;font-size:14px;color:var(--text-secondary,#9898ad)">' +
        '<div>📝 <strong>اكتب</strong> في المحرر وسيُحلّل النص تلقائيًا</div>' +
        '<div>✨ <strong>انقر</strong> على أي اقتراح لتطبيقه فورًا</div>' +
        '<div>📚 <strong>استخدم</strong> أدوات التلخيص والتدقيق القرآني وتحويل اللهجات</div>' +
        '<div>☁️ <strong>سجّل دخولك</strong> لحفظ مستنداتك في السحابة</div>' +
      '</div>' +
      '<button id="onboarding-start" style="background:linear-gradient(135deg,#6366f1,#8b5cf6);color:#fff;border:none;padding:12px 32px;border-radius:10px;font-size:16px;cursor:pointer;font-family:inherit">ابدأ الكتابة</button>' +
    '</div>';

  document.body.appendChild(overlay);

  document.getElementById('onboarding-start').addEventListener('click', function() {
    overlay.style.opacity = '0';
    overlay.style.transition = 'opacity 300ms';
    setTimeout(function() {
      overlay.remove();
    }, 300);
    localStorage.setItem('bayan_onboarded', '1');
  });

  overlay.addEventListener('click', function(e) {
    if (e.target === overlay) {
      overlay.remove();
      localStorage.setItem('bayan_onboarded', '1');
    }
  });
}
