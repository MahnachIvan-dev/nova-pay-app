// ═══════════════════════════════════════════════════════
// NOVA PAY — СИСТЕМА ЧЕКОВ
// ═══════════════════════════════════════════════════════

const Checks = {

  // ─── РЕНДЕР ЧЕКА ──────────────────────────────────
  renderCheckCard(check, containerId) {
    const el = document.getElementById(containerId);
    if (!el || !check) return;

    const bgUrl   = `${CONFIG.CDN}/checks/check-bg.png`;
    const expDate = Utils.formatDate(check.expires_at);
    const created = Utils.formatDateTime(check.created_at);

    el.innerHTML = `
      <div class="check-card" id="checkCardEl">

        <!-- Фон чека -->
        <img src="${bgUrl}" class="check-bg-img" alt=""
          onerror="this.style.background='linear-gradient(135deg,#070714,#1E1B4B)'"/>

        <!-- Оверлей -->
        <div class="check-overlay"></div>

        <!-- Декоративная линия слева -->
        <div class="check-side-line"></div>

        <!-- Контент -->
        <div class="check-content">

          <!-- Верх: логотип -->
          <div class="check-header">
            <div class="check-logo">
              <span class="check-logo-n">N</span>
              <span class="check-logo-text">NOVA PAY</span>
            </div>
            <div class="check-id-badge">${check.check_id}</div>
          </div>

          <!-- Пунктирная линия -->
          <div class="check-divider"></div>

          <!-- Главное: сумма -->
          <div class="check-amount-wrap">
            <div class="check-amount-num" id="checkAmountNum">
              ${check.amount}
            </div>
            <div class="check-amount-cur">NVC</div>
          </div>

          <!-- Описание -->
          <div class="check-description">${check.description || "Денежный чек"}</div>

          <!-- Пунктирная линия -->
          <div class="check-divider"></div>

          <!-- Инфо строки -->
          <div class="check-info-rows">
            <div class="check-info-row">
              <span class="check-info-label">Создан</span>
              <span class="check-info-value">${created}</span>
            </div>
            <div class="check-info-row">
              <span class="check-info-label">Действует до</span>
              <span class="check-info-value ${new Date(check.expires_at) < new Date() ? 'expired' : ''}">${expDate}</span>
            </div>
            <div class="check-info-row">
              <span class="check-info-label">Статус</span>
              <span class="check-info-value ${check.is_used ? 'used' : 'active'}">
                ${check.is_used ? "✗ Использован" : "✓ Активен"}
              </span>
            </div>
          </div>

          <!-- Кнопка активации -->
          ${!check.is_used ? `
            <button class="btn btn-primary check-activate-btn"
              onclick="Checks.activate('${check.check_id}')">
              💰 Активировать чек
            </button>
          ` : `
            <div class="check-used-stamp">ИСПОЛЬЗОВАН</div>
          `}

        </div>
      </div>
    `;

    // Анимация появления числа
    this._animateAmount(check.amount);
  },

  // ─── АНИМАЦИЯ СУММЫ ───────────────────────────────
  _animateAmount(targetAmount) {
    const el = document.getElementById("checkAmountNum");
    if (!el) return;

    let current = 0;
    const step  = Math.ceil(targetAmount / 30);
    const timer = setInterval(() => {
      current = Math.min(current + step, targetAmount);
      el.textContent = current;
      if (current >= targetAmount) clearInterval(timer);
    }, 40);
  },

  // ─── АКТИВАЦИЯ ЧЕКА ───────────────────────────────
  async activate(checkId) {
    const uid = App.state.uid;
    if (!uid) return Utils.toast("❌ Нет авторизации", "error");

    // Анимация обработки
    this._showProcessing();

    const result = await API.activateCheck(checkId, uid);

    this._hideProcessing();

    if (!result.ok) {
      const errors = {
        not_found:  "❌ Чек не найден",
        used:       "❌ Чек уже использован",
        expired:    "❌ Срок действия чека истёк",
        own_check:  "❌ Нельзя активировать свой чек"
      };
      return Utils.toast(errors[result.error] || "❌ Ошибка", "error");
    }

    // Обновляем состояние
    App.state.user.balance = result.newBalance;
    App.renderHeader();

    // Анимация успеха
    this._showSuccess(result.amount, result.newBalance);
  },

  _showProcessing() {
    const overlay = document.createElement("div");
    overlay.id = "checkProcessing";
    overlay.style.cssText = `
      position:fixed;inset:0;z-index:500;
      background:rgba(0,0,0,0.85);
      display:flex;flex-direction:column;
      align-items:center;justify-content:center;gap:20px;
    `;
    overlay.innerHTML = `
      <div style="
        width:80px;height:80px;
        border:3px solid rgba(124,58,237,0.2);
        border-top-color:var(--purple);
        border-radius:50%;
        animation:spin .8s linear infinite;
      "></div>
      <div style="color:#fff;font-size:16px;font-weight:600;">Активируем чек...</div>
    `;
    document.body.appendChild(overlay);
  },

  _hideProcessing() {
    document.getElementById("checkProcessing")?.remove();
  },

  _showSuccess(amount, newBalance) {
    const overlay = document.createElement("div");
    overlay.style.cssText = `
      position:fixed;inset:0;z-index:500;
      background:rgba(0,0,0,0.9);
      display:flex;flex-direction:column;
      align-items:center;justify-content:center;gap:16px;
      animation:fadeIn .3s ease;
    `;
    overlay.innerHTML = `
      <div style="font-size:72px;animation:bounceIn .5s ease;">🎉</div>
      <div style="font-size:48px;font-weight:900;color:#fff;
        text-shadow:0 0 40px rgba(167,139,250,0.8);">
        +${amount} NVC
      </div>
      <div style="font-size:16px;color:rgba(255,255,255,0.6);">
        Новый баланс: <b style="color:#A78BFA;">${newBalance} NVC</b>
      </div>
      <button onclick="this.parentElement.remove();App.navigate('home');"
        style="margin-top:16px;padding:14px 32px;
          background:linear-gradient(135deg,#7C3AED,#C026D3);
          border:none;border-radius:12px;color:#fff;
          font-size:15px;font-weight:700;cursor:pointer;">
        💳 Перейти к кошельку
      </button>
    `;
    document.body.appendChild(overlay);

    // Автозакрытие через 5 секунд
    setTimeout(() => {
      overlay.remove();
      App.navigate("home");
    }, 5000);
  },

  // ─── СТРАНИЦА ЧЕКА ────────────────────────────────
  async loadCheckPage(checkId) {
    App.navigate("check");
    const el = document.getElementById("checkPageContent");
    if (!el) return;

    el.innerHTML = `<div class="loading-center"><div class="loader-ring"></div></div>`;

    const check = await API.getCheck(checkId);

    if (!check) {
      el.innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">❌</div>
          <div class="empty-title">Чек не найден</div>
          <div class="empty-desc">Проверьте ссылку и попробуйте снова</div>
        </div>
      `;
      return;
    }

    this.renderCheckCard(check, "checkPageContent");
  }
};