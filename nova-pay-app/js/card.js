// ═══════════════════════════════════════════════════════
// NOVA PAY — РЕНДЕР КАРТОЧЕК
// ═══════════════════════════════════════════════════════

const CardRenderer = {

  // URL картинок с GitHub CDN
  images: {
    starter:  `${CONFIG.CDN}/cards/starter.png`,
    creative: `${CONFIG.CDN}/cards/creative.png`,
    elite:    `${CONFIG.CDN}/cards/elite.png`,
  },

  tierLabels: {
    starter:  { emoji: "🟣", label: "STARTER",     color: "#C4B5FD" },
    creative: { emoji: "💜", label: "CREATIVE",    color: "#F0ABFC" },
    elite:    { emoji: "👑", label: "NOVA ELITE",  color: "#FCD34D" },
  },

  tierBadgeBg: {
    starter:  "rgba(124,58,237,0.35)",
    creative: "rgba(192,38,211,0.35)",
    elite:    "rgba(245,158,11,0.35)",
  },

  tierBorder: {
    starter:  "rgba(124,58,237,0.5)",
    creative: "rgba(192,38,211,0.5)",
    elite:    "rgba(245,158,11,0.6)",
  },

  // ─── ОСНОВНАЯ КАРТОЧКА ────────────────────────────
  render(user, card, containerId, opts = {}) {
    const el = document.getElementById(containerId);
    if (!el) return;

    const tier      = user.card_tier || "starter";
    const tierInfo  = this.tierLabels[tier];
    const rawNum    = card?.card_number || "0000 0000 0000 0000";
    const masked    = Utils.maskCard(rawNum);
    const imgUrl    = this.images[tier];
    const animate   = opts.animate !== false;

    el.innerHTML = `
      <div class="card-3d-wrap" id="card3d_${containerId}">
        <div class="card-3d-inner">

          <!-- ЛИЦЕВАЯ СТОРОНА -->
          <div class="card-face card-front">
            <!-- Фоновое изображение -->
            <img
              src="${imgUrl}"
              class="card-bg-img"
              alt=""
              onerror="this.style.display='none'"
            />

            <!-- Затемняющий оверлей -->
            <div class="card-overlay"></div>

            <!-- Анимированный блик -->
            <div class="card-shimmer-bar"></div>

            <!-- ВЕРХ: логотип + тариф -->
            <div class="card-row card-top">
              <div class="card-brand">
                <span class="card-brand-name">NOVA PAY</span>
                <span class="card-brand-sub">NOVA CREATIVE STUDIO</span>
              </div>
              <div class="card-tier-badge"
                style="
                  background:${this.tierBadgeBg[tier]};
                  border:1px solid ${this.tierBorder[tier]};
                  color:${tierInfo.color};
                ">
                ${tierInfo.emoji} ${tierInfo.label}
              </div>
            </div>

            <!-- ЧИПОВАННЫЙ ЭЛЕМЕНТ -->
            <div class="card-chip-row">
              <div class="card-chip">
                <div class="chip-line h"></div>
                <div class="chip-line v"></div>
                <div class="chip-center"></div>
              </div>
              <div class="card-nfc">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                  <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z"
                    stroke="rgba(255,255,255,0.3)" stroke-width="1.5" fill="none"/>
                  <path d="M12 6c-3.31 0-6 2.69-6 6s2.69 6 6 6 6-2.69 6-6-2.69-6-6-6z"
                    stroke="rgba(255,255,255,0.3)" stroke-width="1.5" fill="none"/>
                  <path d="M12 10c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2z"
                    fill="rgba(255,255,255,0.4)"/>
                </svg>
              </div>
            </div>

            <!-- НОМЕР КАРТЫ -->
            <div class="card-number-row"
              data-full="${rawNum}"
              data-masked="${masked}"
              data-shown="false"
              id="cardNum_${containerId}"
            >${masked}</div>

            <!-- НИЗ: держатель + баланс -->
            <div class="card-row card-bottom">
              <div class="card-holder-block">
                <div class="card-holder-label">Держатель</div>
                <div class="card-holder-name">
                  ${(user.full_name || "NOVA USER").toUpperCase().slice(0, 20)}
                </div>
              </div>
              <div class="card-balance-block">
                <div class="card-balance-label">Баланс</div>
                <div class="card-balance-amount">${user.balance || 0}</div>
                <div class="card-balance-currency">NVC</div>
              </div>
            </div>

          </div>

          <!-- ОБРАТНАЯ СТОРОНА -->
          <div class="card-face card-back">
            <img src="${imgUrl}" class="card-bg-img" alt="" onerror="this.style.display='none'"/>
            <div class="card-overlay" style="background:rgba(0,0,0,0.6)"></div>

            <div class="card-magstripe"></div>

            <div class="card-back-content">
              <div class="card-cvv-label">CVV</div>
              <div class="card-cvv-band">
                <div class="card-cvv-value">•••</div>
              </div>
              <div class="card-back-num">
                ${rawNum}
              </div>
              <div class="card-back-info">
                <div>ID: <code>${user.telegram_id}</code></div>
                <div>Выдана: ${Utils.formatDate(card?.created_at)}</div>
              </div>
            </div>
          </div>

        </div>
      </div>

      <!-- Подсказка -->
      <div class="card-hint">
        <span>👆 Нажмите для переворота</span>
        <span>🔢 Двойной клик — показать номер</span>
      </div>
    `;

    this._bindEvents(containerId, animate);
  },

  // ─── МИНИ КАРТОЧКА (для страницы тарифов) ────────
  renderMini(tier, isActive, userBalance, containerId) {
    const el = document.getElementById(containerId);
    if (!el) return;

    const tierData = {
      starter:  { name: "Starter",    price: 0,   features: ["Базовые переводы","Оплата услуг","Еженедельный бонус"] },
      creative: { name: "Creative",   price: 200, features: ["Всё из Starter","Приоритет поддержки","+10% к бонусам"] },
      elite:    { name: "Nova Elite", price: 500, features: ["Всё из Creative","VIP поддержка","Эксклюзивные конкурсы","+25% к бонусам"] },
    };

    const info   = tierData[tier];
    const tInfo  = this.tierLabels[tier];
    const imgUrl = this.images[tier];
    const canBuy = !isActive && userBalance >= info.price;

    el.innerHTML = `
      <div class="tier-card-wrap ${isActive ? 'is-active' : ''}">

        <!-- Мини превью карточки -->
        <div class="tier-card-preview" style="position:relative;height:120px;border-radius:16px;overflow:hidden;margin-bottom:16px;">
          <img src="${imgUrl}" style="width:100%;height:100%;object-fit:cover;" alt="" onerror="this.style.display='none'"/>
          <div style="position:absolute;inset:0;background:linear-gradient(135deg,rgba(0,0,0,0.2),rgba(0,0,0,0));"></div>
          <div style="position:absolute;top:12px;left:14px;">
            <div style="font-size:11px;font-weight:900;letter-spacing:3px;color:rgba(255,255,255,0.9);">NOVA PAY</div>
          </div>
          <div style="position:absolute;top:12px;right:12px;">
            <div class="card-tier-badge"
              style="background:${this.tierBadgeBg[tier]};border:1px solid ${this.tierBorder[tier]};color:${tInfo.color};">
              ${tInfo.emoji} ${tInfo.label}
            </div>
          </div>
          <div style="position:absolute;bottom:12px;right:14px;text-align:right;">
            <div style="font-size:9px;color:rgba(255,255,255,0.5);letter-spacing:2px;">БАЛАНС</div>
            <div style="font-size:18px;font-weight:800;color:#fff;text-shadow:0 0 20px rgba(167,139,250,0.8);">
              ${isActive ? userBalance : "—"}
            </div>
            <div style="font-size:9px;color:rgba(255,255,255,0.5);letter-spacing:2px;">NVC</div>
          </div>
          ${isActive ? '<div style="position:absolute;bottom:12px;left:14px;background:rgba(16,185,129,0.3);border:1px solid rgba(16,185,129,0.5);color:#6EE7B7;font-size:10px;font-weight:700;padding:3px 8px;border-radius:8px;">✅ АКТИВНА</div>' : ''}
        </div>

        <!-- Особенности -->
        <ul style="list-style:none;margin-bottom:16px;">
          ${info.features.map(f => `
            <li style="display:flex;align-items:center;gap:8px;font-size:13px;color:rgba(255,255,255,0.8);margin-bottom:8px;">
              <span style="color:var(--violet);font-size:10px;">✦</span>${f}
            </li>
          `).join("")}
        </ul>

        <!-- Цена / кнопка -->
        <div style="text-align:center;">
          <div style="font-size:28px;font-weight:800;color:#fff;margin-bottom:12px;">
            ${info.price === 0 ? "Бесплатно" : `${info.price} <span style="font-size:16px;color:var(--violet);">NVC</span>`}
          </div>
          ${isActive
            ? `<button class="btn btn-success" disabled>✅ Ваша карточка</button>`
            : canBuy
              ? `<button class="btn btn-primary" onclick="App.buyCard('${tier}')">Получить ${tInfo.emoji}</button>`
              : `<button class="btn btn-secondary" disabled>Нужно ${info.price} NVC</button>`
          }
        </div>
      </div>
    `;
  },

  // ─── СОБЫТИЯ ──────────────────────────────────────
  _bindEvents(containerId, animate) {
    const wrap   = document.getElementById(`card3d_${containerId}`);
    const numEl  = document.getElementById(`cardNum_${containerId}`);
    if (!wrap) return;

    let clickCount = 0;
    let flipped = false;

    // Одиночный клик — перевернуть
    wrap.addEventListener("click", (e) => {
      clickCount++;
      setTimeout(() => {
        if (clickCount === 1) {
          flipped = !flipped;
          wrap.classList.toggle("is-flipped", flipped);
        }
        clickCount = 0;
      }, 250);
    });

    // Двойной клик — показать/скрыть номер
    wrap.addEventListener("dblclick", () => {
      if (!numEl) return;
      const shown = numEl.dataset.shown === "true";
      numEl.textContent = shown ? numEl.dataset.masked : numEl.dataset.full;
      numEl.dataset.shown = String(!shown);
      Utils.toast(shown ? "🔒 Номер скрыт" : "🔓 Номер показан");
    });

    // 3D наклон мышью (десктоп)
    if (animate) {
      wrap.addEventListener("mousemove", (e) => {
        const rect = wrap.getBoundingClientRect();
        const x = (e.clientX - rect.left) / rect.width  - 0.5;
        const y = (e.clientY - rect.top)  / rect.height - 0.5;
        wrap.style.transform = `rotateY(${x * 15}deg) rotateX(${-y * 10}deg)`;
      });
      wrap.addEventListener("mouseleave", () => {
        wrap.style.transform = "";
      });
    }

    // Касание (мобильный наклон)
    wrap.addEventListener("touchmove", (e) => {
      const touch = e.touches[0];
      const rect  = wrap.getBoundingClientRect();
      const x = (touch.clientX - rect.left) / rect.width  - 0.5;
      const y = (touch.clientY - rect.top)  / rect.height - 0.5;
      wrap.style.transform = `rotateY(${x * 10}deg) rotateX(${-y * 8}deg)`;
    }, { passive: true });
    wrap.addEventListener("touchend", () => {
      wrap.style.transform = "";
    });
  }
};