// ═══════════════════════════════════════════════════════
// NOVA PAY — БОНУСЫ
// ═══════════════════════════════════════════════════════

const Bonuses = {

  async render(user, containerId) {
    const el = document.getElementById(containerId);
    if (!el) return;

    const lastBonus = new Date(user.last_weekly_bonus);
    const nextBonus = new Date(lastBonus.getTime() + 7 * 86400000);
    const canClaim  = new Date() >= nextBonus;
    const msLeft    = nextBonus - new Date();
    const daysLeft  = Math.ceil(msLeft / 86400000);
    const hoursLeft = Math.ceil(msLeft / 3600000);

    const timeStr = daysLeft > 1
      ? `${daysLeft} дн.`
      : `${hoursLeft} ч.`;

    el.innerHTML = `
      <!-- Еженедельный бонус -->
      <div class="bonus-card glass" style="margin-bottom:14px;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
          <div>
            <div style="font-size:16px;font-weight:700;margin-bottom:4px;">🗓 Еженедельный бонус</div>
            <div style="font-size:13px;color:var(--text2);">Каждые 7 дней — 20 NVC</div>
          </div>
          <div style="font-size:32px;font-weight:900;
            background:linear-gradient(135deg,var(--violet),var(--pink));
            -webkit-background-clip:text;-webkit-text-fill-color:transparent;">
            20
          </div>
        </div>

        ${canClaim
          ? `<button class="btn btn-primary" onclick="Bonuses.claimWeekly()">
               🎁 Получить 20 NVC
             </button>`
          : `<div class="bonus-timer">
               <div class="bonus-timer-bar">
                 <div class="bonus-timer-fill" style="width:${Math.max(5, 100 - (msLeft / 604800000) * 100)}%;"></div>
               </div>
               <div style="text-align:center;font-size:13px;color:var(--text2);margin-top:8px;">
                 ⏳ Следующий через <b style="color:var(--violet);">${timeStr}</b>
               </div>
             </div>`
        }
      </div>

      <!-- Реферальная программа -->
      <div class="bonus-card glass" style="margin-bottom:14px;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
          <div>
            <div style="font-size:16px;font-weight:700;margin-bottom:4px;">👥 Рефералы</div>
            <div style="font-size:13px;color:var(--text2);">50 NVC за каждого друга</div>
          </div>
          <div style="font-size:32px;font-weight:900;color:var(--gold);">50</div>
        </div>

        <div style="display:flex;gap:12px;margin-bottom:12px;">
          <div class="glass-sm" style="flex:1;text-align:center;">
            <div style="font-size:24px;font-weight:800;color:var(--violet);">
              ${user.referral_count || 0}
            </div>
            <div style="font-size:11px;color:var(--text2);">приглашено</div>
          </div>
          <div class="glass-sm" style="flex:1;text-align:center;">
            <div style="font-size:24px;font-weight:800;color:var(--success);">
              ${(user.referral_count || 0) * 50}
            </div>
            <div style="font-size:11px;color:var(--text2);">NVC заработано</div>
          </div>
        </div>

        <button class="btn btn-secondary" onclick="Bonuses.copyRefLink()">
          🔗 Скопировать реферальную ссылку
        </button>
        <button class="btn btn-primary" style="margin-top:8px;" onclick="Bonuses.shareRefLink()">
          📤 Поделиться
        </button>
      </div>

      <!-- Подписка на канал -->
      <div class="bonus-card glass" style="margin-bottom:14px;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
          <div>
            <div style="font-size:16px;font-weight:700;margin-bottom:4px;">📢 Канал студии</div>
            <div style="font-size:13px;color:var(--text2);">Подпишись и получи 30 NVC</div>
          </div>
          <div style="font-size:32px;font-weight:900;color:#38BDF8;">30</div>
        </div>
        ${user.subscribed_channel
          ? `<button class="btn btn-success" disabled>✅ Бонус получен</button>`
          : `<div style="display:flex;gap:8px;">
               <a href="https://t.me/nova_creative_studio" target="_blank" 
                 class="btn btn-secondary" style="flex:1;text-decoration:none;">
                 📢 Подписаться
               </a>
               <button class="btn btn-primary" style="flex:1;" onclick="Bonuses.checkSub()">
                 ✅ Проверить
               </button>
             </div>`
        }
      </div>

      <!-- Другие способы -->
      <div class="glass">
        <div style="font-size:14px;font-weight:700;margin-bottom:12px;">🏆 Ещё способы</div>
        <div class="glass-sm" style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
          <span style="font-size:14px;">🏅 Победа в конкурсе</span>
          <span style="font-weight:800;color:var(--gold);">+100 NVC</span>
        </div>
        <div class="glass-sm" style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
          <span style="font-size:14px;">⭐ Покупка за Telegram Stars</span>
          <span style="font-weight:800;color:var(--violet);">от 50 NVC</span>
        </div>
        <div class="glass-sm" style="display:flex;justify-content:space-between;align-items:center;">
          <span style="font-size:14px;">🎁 Чеки от администратора</span>
          <span style="font-weight:800;color:var(--pink);">∞ NVC</span>
        </div>
      </div>
    `;
  },

  async claimWeekly() {
    const user = App.state.user;
    const uid  = App.state.uid;
    const lastBonus = new Date(user.last_weekly_bonus);
    const nextBonus = new Date(lastBonus.getTime() + 7 * 86400000);

    if (new Date() < nextBonus) {
      return Utils.toast("⏳ Бонус ещё не доступен", "error");
    }

    const d = await API.get(CONFIG.BIN_USERS);
    d.users[String(uid)].last_weekly_bonus = new Date().toISOString();
    await API.put(CONFIG.BIN_USERS, d);

    const newBal = await API.updateBalance(uid, 20, "Еженедельный бонус");
    App.state.user.balance            = newBal;
    App.state.user.last_weekly_bonus  = new Date().toISOString();

    App.renderHeader();
    this.render(App.state.user, "bonusPageContent");
    Utils.toast("🎁 +20 NVC начислено!", "success");
  },

  async copyRefLink() {
    const botUsername = CONFIG.BOT_USERNAME;
    const refCode     = App.state.user.referral_code;
    const link = `https://t.me/${botUsername}?start=${refCode}`;
    try {
      await navigator.clipboard.writeText(link);
      Utils.toast("✅ Ссылка скопирована!", "success");
    } catch {
      Utils.toast("🔗 " + link);
    }
  },

  async shareRefLink() {
    const botUsername = CONFIG.BOT_USERNAME;
    const refCode     = App.state.user.referral_code;
    const link = `https://t.me/${botUsername}?start=${refCode}`;
    const tgUrl = `https://t.me/share/url?url=${encodeURIComponent(link)}&text=${encodeURIComponent("💜 Присоединяйся к Nova Pay — кошельку NOVA CREATIVE STUDIO!\n\nПо моей ссылке получишь 20 NVC стартового бонуса!")}`;
    window.open(tgUrl, "_blank");
  },

  async checkSub() {
    Utils.toast("⏳ Проверяем подписку...");
    await Utils.sleep(1500);
    // В реальности проверка идёт через бот
    Utils.toast("📢 Подписка будет проверена ботом", "info");
  }
};