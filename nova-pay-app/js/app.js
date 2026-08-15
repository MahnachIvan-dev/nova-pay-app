// ═══════════════════════════════════════════════════════
// NOVA PAY — ГЛАВНЫЙ ФАЙЛ
// ═══════════════════════════════════════════════════════

const App = {
  state: {
    uid:          null,
    user:         null,
    card:         null,
    transactions: [],
    page:         "home",
    txFilter:     "all",
    isOwner:      false
  },

  // ─── ИНИЦИАЛИЗАЦИЯ ────────────────────────────────
  async init() {
    const tg = window.Telegram?.WebApp;
    if (tg) {
      tg.ready(); tg.expand();
      tg.setHeaderColor("#0A0A1A");
      tg.setBackgroundColor("#0A0A1A");
    }

    const params = new URLSearchParams(location.search);
    this.state.uid =
      params.get("uid") ||
      tg?.initDataUnsafe?.user?.id ||
      null;

    this._createStars();

    if (!this.state.uid) {
      this._showError("Откройте через Telegram бота Nova Pay");
      return;
    }

    try {
      let user = await API.getUser(this.state.uid);

      if (!user) {
        const tgUser = tg?.initDataUnsafe?.user;
        user = await API.registerUser(
          this.state.uid,
          tgUser?.username || "",
          tgUser?.first_name
            ? `${tgUser.first_name} ${tgUser.last_name || ""}`.trim()
            : String(this.state.uid)
        );
        const refCode = params.get("start") || params.get("ref");
        if (refCode?.startsWith("REF-")) await this._processReferral(refCode);
      }

      this.state.user    = user;
      this.state.card    = await API.getCard(user.card_id);
      this.state.transactions = await API.getUserTransactions(this.state.uid);
      this.state.isOwner = parseInt(this.state.uid) === CONFIG.OWNER_ID;

      this._showApp();
      this.renderAll();

      // Показываем кнопку админа если владелец
      if (this.state.isOwner) {
        this._injectAdminNavBtn();
      }

      // Чек из URL
      const checkParam = params.get("check");
      if (checkParam) {
        await Utils.sleep(400);
        await Checks.loadCheckPage(checkParam);
        return;
      }

      this._startPolling();

    } catch(e) {
      console.error("App.init:", e);
      this._showError("Ошибка загрузки. Попробуйте позже.");
    }
  },

  // Добавляем кнопку Админ в навбар
  _injectAdminNavBtn() {
    const nav = document.querySelector(".nav");
    if (!nav || nav.querySelector("[data-page='admin']")) return;
    const btn = document.createElement("button");
    btn.className = "nav-item";
    btn.dataset.page = "admin";
    btn.onclick = () => this.navigate("admin");
    btn.innerHTML = `
      <svg viewBox="0 0 24 24">
        <path d="M12 1l3 6 6 1-4.5 4 1 6L12 15l-5.5 3 1-6L3 8l6-1z"/>
      </svg>
      <span class="nav-label">Админ</span>
    `;
    nav.appendChild(btn);

    // Добавляем страницу если нет
    if (!document.getElementById("page-admin")) {
      const page = document.createElement("div");
      page.className = "page";
      page.id = "page-admin";
      page.innerHTML = `
        <div class="page-title">⚙️ Панель владельца</div>
        <div class="page-subtitle">NOVA CREATIVE STUDIO</div>
        <div id="adminContent"></div>
      `;
      document.querySelector(".nav").before(page);
    }
  },

  // ─── POLLING ──────────────────────────────────────
  _startPolling() {
    setInterval(async () => {
      if (document.hidden) return;
      try {
        API.invalidate(CONFIG.BIN_USERS);
        const freshUser = await API.getUser(this.state.uid);
        if (!freshUser) return;
        if (freshUser.balance !== this.state.user.balance) {
          const diff = freshUser.balance - this.state.user.balance;
          this.state.user = freshUser;
          this.state.transactions = await API.getUserTransactions(this.state.uid);
          this.renderHeader();
          if (this.state.page === "history") this.renderHistory();
          if (diff > 0) {
            Utils.toast(`💰 +${diff} NVC зачислено!`, "success");
            Sound.bonus();
          }
        }
      } catch(e) {}
    }, 15000);
  },

  // ─── РЕНДЕР ───────────────────────────────────────
  renderAll() {
    this.renderHeader();
    this.renderHome();
  },

  renderHeader() {
    const el = document.getElementById("headerBalance");
    if (el) el.textContent = `${this.state.user?.balance || 0} NVC`;
  },

  renderHome() {
    CardRenderer.render(this.state.user, this.state.card, "cardContainer");
    Transactions.render(this.state.transactions, "recentTxList", this.state.uid, 5);

    const se = document.getElementById("statEarned");
    const ss = document.getElementById("statSpent");
    const sr = document.getElementById("statRefs");
    if (se) se.textContent = `${this.state.user.total_earned || 0}`;
    if (ss) ss.textContent = `${this.state.user.total_spent  || 0}`;
    if (sr) sr.textContent = `${this.state.user.referral_count || 0}`;
  },

  renderCards() {
    ["starter","creative","elite"].forEach(tier => {
      CardRenderer.renderMini(
        tier,
        this.state.user.card_tier === tier,
        this.state.user.balance,
        `tierCard_${tier}`
      );
    });
  },

  renderHistory() {
    const filtered = Transactions.filter(
      this.state.transactions, this.state.uid, this.state.txFilter
    );
    Transactions.render(filtered, "historyList", this.state.uid);
  },

  renderBonuses() { Bonuses.render(this.state.user, "bonusPageContent"); },

  renderProfile() {
    const u   = this.state.user;
    const c   = this.state.card;
    const el  = document.getElementById("profileContent");
    if (!el) return;

    const tierNames = { starter:"Starter", creative:"Creative", elite:"Nova Elite" };
    const tierEmoji = { starter:"🟣", creative:"💜", elite:"👑" };

    el.innerHTML = `
      <div class="glass" style="text-align:center;margin-bottom:14px;padding:28px 20px;">
        <div style="font-size:60px;margin-bottom:12px;">👤</div>
        <div style="font-size:20px;font-weight:800;">${u.full_name}</div>
        <div style="color:var(--text2);margin-top:4px;font-size:14px;">
          @${u.username || "—"}
        </div>
        <div style="margin-top:12px;">
          <code style="background:rgba(124,58,237,0.2);padding:5px 12px;
            border-radius:10px;font-size:13px;">${u.telegram_id}</code>
        </div>
        ${this.state.isOwner
          ? `<div style="margin-top:10px;background:rgba(245,158,11,0.2);
              border:1px solid rgba(245,158,11,0.4);border-radius:10px;
              padding:6px 14px;font-size:12px;color:#FCD34D;font-weight:700;
              display:inline-block;">👑 ВЛАДЕЛЕЦ</div>`
          : ""
        }
      </div>

      <div class="glass" style="margin-bottom:14px;">
        <div class="section-title">💳 Карточка</div>
        <div class="profile-row">
          <span>Тариф</span>
          <span>${tierEmoji[u.card_tier]} <b>${tierNames[u.card_tier]}</b></span>
        </div>
        <div class="profile-row">
          <span>Номер</span>
          <span style="font-size:13px;letter-spacing:2px;">${Utils.maskCard(c?.card_number)}</span>
        </div>
        <div class="profile-row">
          <span>Создана</span>
          <span>${Utils.formatDate(c?.created_at)}</span>
        </div>
      </div>

      <div class="glass" style="margin-bottom:14px;">
        <div class="section-title">📊 Статистика</div>
        <div class="profile-row">
          <span>Всего получено</span>
          <span style="color:var(--success);font-weight:700;">+${u.total_earned||0} NVC</span>
        </div>
        <div class="profile-row">
          <span>Всего потрачено</span>
          <span style="color:var(--danger);font-weight:700;">−${u.total_spent||0} NVC</span>
        </div>
        <div class="profile-row">
          <span>Рефералов</span>
          <span style="font-weight:700;">${u.referral_count||0}</span>
        </div>
        <div class="profile-row">
          <span>С нами с</span>
          <span>${Utils.formatDate(u.registered_at)}</span>
        </div>
      </div>
    `;
  },

  // ─── НАВИГАЦИЯ ────────────────────────────────────
  navigate(pageName) {
    this.state.page = pageName;
    document.querySelectorAll(".page").forEach(p => p.classList.remove("active"));
    document.querySelectorAll(".nav-item").forEach(b => b.classList.remove("active"));

    const page    = document.getElementById(`page-${pageName}`);
    const navItem = document.querySelector(`[data-page="${pageName}"]`);
    if (page)    page.classList.add("active");
    if (navItem) navItem.classList.add("active");

    switch(pageName) {
      case "cards":   this.renderCards();   break;
      case "history": this.renderHistory(); break;
      case "bonuses": this.renderBonuses(); break;
      case "profile": this.renderProfile(); break;
      case "admin":   Admin.render();       break;
    }
  },

  // ─── МОДАЛЫ ───────────────────────────────────────
  _showModal(content) {
    const overlay = document.getElementById("modalOverlay");
    const body    = document.getElementById("modalBody");
    if (!overlay || !body) return;
    body.innerHTML = `<div class="modal-handle"></div>${content}`;
    overlay.style.display = "flex";
    requestAnimationFrame(() => overlay.classList.add("visible"));
  },

  closeModal() {
    const o = document.getElementById("modalOverlay");
    if (!o) return;
    o.classList.remove("visible");
    setTimeout(() => o.style.display = "none", 300);
  },

  showTransferModal() {
    Sound.click();
    this._showModal(`
      <div class="modal-title">📤 Перевод NVC</div>
      <div class="form-group">
        <label class="form-label">Telegram ID получателя</label>
        <input class="form-input" id="mTransferTo" type="number" placeholder="123456789"/>
      </div>
      <div class="form-group">
        <label class="form-label">Сумма NVC</label>
        <input class="form-input" id="mTransferAmt" type="number" placeholder="50"/>
      </div>
      <div style="font-size:13px;color:var(--text2);margin-bottom:16px;">
        Доступно: <b style="color:var(--text);">${this.state.user.balance} NVC</b>
      </div>
      <button class="btn btn-primary" onclick="App.doTransfer()">📤 Перевести</button>
    `);
  },

  showReceiveModal() {
    Sound.click();
    this._showModal(`
      <div class="modal-title">📥 Получить NVC</div>
      <div class="glass" style="text-align:center;margin-bottom:16px;">
        <div style="font-size:13px;color:var(--text2);margin-bottom:8px;">Ваш Telegram ID</div>
        <div style="font-size:36px;font-weight:900;color:var(--violet);">${this.state.uid}</div>
        <div style="font-size:12px;color:var(--text2);margin-top:8px;">
          Отправьте этот ID отправителю
        </div>
      </div>
      <button class="btn btn-primary" onclick="App.copyUID()">📋 Скопировать ID</button>
    `);
  },

  showBuyModal() {
    Sound.click();
    this._showModal(`
      <div class="modal-title">💫 Пополнить баланс</div>
      <div style="font-size:13px;color:var(--text2);margin-bottom:16px;line-height:1.6;">
        Выберите пакет и отправьте подарок владельцу студии на указанную сумму звёзд.
        После подтверждения NVC поступят на ваш счёт.
      </div>
      ${CONFIG.STARS_RATES.map(r => `
        <div style="display:flex;align-items:center;justify-content:space-between;
          padding:14px;background:var(--card-bg);border:1px solid var(--card-border);
          border-radius:12px;margin-bottom:8px;cursor:pointer;"
          onclick="App.requestBuyNVC(${r.stars},${r.nvc})">
          <div>
            <div style="font-weight:700;font-size:15px;">⭐ ${r.stars} Stars</div>
            ${r.label ? `<div style="font-size:11px;color:var(--gold);">${r.label}</div>` : ""}
          </div>
          <div style="text-align:right;">
            <div style="font-size:20px;font-weight:900;color:var(--violet);">${r.nvc}</div>
            <div style="font-size:11px;color:var(--text2);">NVC</div>
          </div>
        </div>
      `).join("")}
    `);
  },

  async requestBuyNVC(stars, nvc) {
    this.closeModal();
    const req = await API.createPendingRequest({
      uid:      this.state.uid,
      username: this.state.user.username,
      fullName: this.state.user.full_name,
      stars,
      nvc
    });

    this._showModal(`
      <div class="modal-title">⭐ Заявка создана!</div>
      <div class="glass" style="margin-bottom:16px;text-align:center;">
        <div style="font-size:13px;color:var(--text2);margin-bottom:8px;">Номер заявки</div>
        <div style="font-size:20px;font-weight:800;color:var(--violet);">${req.req_id}</div>
      </div>
      <div style="font-size:14px;line-height:1.8;margin-bottom:16px;">
        <b>Шаг 1:</b> Отправьте подарок на <b>⭐ ${stars} Stars</b>
        владельцу студии в Telegram.<br><br>
        <b>Шаг 2:</b> Напишите в бот <b>@${CONFIG.BOT_USERNAME}</b>
        номер заявки: <code style="background:rgba(124,58,237,0.2);
        padding:2px 8px;border-radius:6px;">${req.req_id}</code><br><br>
        <b>Шаг 3:</b> После подтверждения <b>${nvc} NVC</b> поступят на счёт.
      </div>
      <button class="btn btn-primary" onclick="App.closeModal()">Понятно 💜</button>
    `);
  },

  showPayServicesModal() {
    Sound.click();
    this._showModal(`
      <div class="modal-title">🛒 Оплата услуг</div>
      <div style="font-size:13px;color:var(--text2);margin-bottom:16px;">
        💰 Ваш баланс: <b style="color:var(--text);">${this.state.user.balance} NVC</b>
      </div>
      ${Object.entries(CONFIG.PAID_SERVICES).map(([key, s]) => `
        <div style="display:flex;align-items:center;justify-content:space-between;
          padding:14px;background:var(--card-bg);border:1px solid var(--card-border);
          border-radius:12px;margin-bottom:8px;">
          <div>
            <div style="font-weight:600;font-size:15px;">${s.name}</div>
            <div style="font-size:12px;color:var(--text2);">${s.price} NVC</div>
          </div>
          <button class="btn btn-primary"
            style="width:auto;padding:9px 16px;font-size:13px;"
            onclick="App.payService('${key}','${s.name}',${s.price})">
            Оплатить
          </button>
        </div>
      `).join("")}
    `);
  },

  // ─── ДЕЙСТВИЯ ─────────────────────────────────────
  async doTransfer() {
    const toId  = parseInt(document.getElementById("mTransferTo")?.value);
    const amount= parseInt(document.getElementById("mTransferAmt")?.value);

    if (!toId || isNaN(amount) || amount <= 0) {
      Sound.error();
      return Utils.toast("❌ Заполните поля", "error");
    }
    if (toId == this.state.uid) {
      Sound.error();
      return Utils.toast("❌ Нельзя переводить себе", "error");
    }
    if (amount > this.state.user.balance) {
      Sound.error();
      return Utils.toast("❌ Недостаточно NVC", "error");
    }

    this.closeModal();
    this._showPayAnim(amount, "transfer");

    const toUser = await API.getUser(toId);
    if (!toUser) {
      this._hidePayAnim();
      Sound.error();
      return Utils.toast("❌ Пользователь не найден", "error");
    }

    const d = await API.get(CONFIG.BIN_USERS);
    d.users[String(this.state.uid)].balance -= amount;
    d.users[String(this.state.uid)].total_spent =
      (d.users[String(this.state.uid)].total_spent || 0) + amount;
    d.users[String(toId)].balance += amount;
    d.users[String(toId)].total_earned =
      (d.users[String(toId)].total_earned || 0) + amount;
    await API.put(CONFIG.BIN_USERS, d);

    await API.addTransaction({
      from_id: parseInt(this.state.uid),
      to_id:   toId, amount, type:"transfer",
      description:`Перевод → ${toUser.full_name}`
    });

    this.state.user.balance -= amount;
    this.state.transactions  = await API.getUserTransactions(this.state.uid);

    await Utils.sleep(2000);
    this._hidePayAnim();
    Sound.transfer();
    this.renderAll();
    Utils.toast(`✅ Отправлено ${amount} NVC!`, "success");
  },

  async payService(key, name, price) {
    if (this.state.user.balance < price) {
      Sound.error();
      return Utils.toast(`❌ Нужно ${price} NVC`, "error");
    }
    this.closeModal();
    this._showPayAnim(price, "payment");

    const newBal = await API.updateBalance(
      this.state.uid, -price, `Оплата: ${name}`
    );
    this.state.user.balance = newBal;
    this.state.transactions = await API.getUserTransactions(this.state.uid);

    await Utils.sleep(2200);
    this._hidePayAnim();
    Sound.payment();
    this.renderAll();
    Utils.toast(`✅ ${name} оплачена!`, "success");
  },

  async buyCard(tier) {
    const prices = { starter:0, creative:200, elite:500 };
    const price  = prices[tier];
    if (this.state.user.balance < price) {
      Sound.error();
      return Utils.toast(`❌ Нужно ${price} NVC`, "error");
    }

    Sound.click();
    const d = await API.get(CONFIG.BIN_USERS);
    d.users[String(this.state.uid)].balance    -= price;
    d.users[String(this.state.uid)].total_spent = (d.users[String(this.state.uid)].total_spent||0) + price;
    d.users[String(this.state.uid)].card_tier   = tier;
    await API.put(CONFIG.BIN_USERS, d);

    this.state.user.balance   -= price;
    this.state.user.card_tier  = tier;
    this.state.card            = await API.getCard(this.state.user.card_id);

    Sound.payment();
    this.renderAll();
    this.renderCards();
    Utils.toast(`✅ Карточка активирована!`, "success");
  },

  async copyUID() {
    try { await navigator.clipboard.writeText(String(this.state.uid)); } catch(e) {}
    Utils.toast("✅ ID скопирован!", "success");
    this.closeModal();
  },

  setTxFilter(filter, btn) {
    this.state.txFilter = filter;
    document.querySelectorAll(".chip").forEach(c => c.classList.remove("active"));
    btn.classList.add("active");
    this.renderHistory();
  },

  // ─── АНИМАЦИЯ ОПЛАТЫ ──────────────────────────────
  _showPayAnim(amount, type) {
    const el = document.getElementById("payAnimation");
    if (!el) return;
    el.style.display = "flex";

    const titles = { transfer:"Выполняем перевод...", payment:"Обрабатываем оплату..." };
    const colors  = { transfer:["#7C3AED","#C026D3"], payment:["#059669","#10B981"] };
    const [c1, c2] = colors[type] || colors.payment;

    el.innerHTML = `
      <div style="text-align:center;">

        <!-- Анимированные карточки -->
        <div style="display:flex;align-items:center;justify-content:center;
          height:80px;margin-bottom:28px;position:relative;">
          <div id="pCardA" style="
            width:90px;height:56px;border-radius:12px;
            background:linear-gradient(135deg,#1E1B4B,${c1});
            transform:rotate(-10deg) translateX(10px);
            box-shadow:0 12px 40px rgba(124,58,237,0.5);
            transition:all 1.2s cubic-bezier(.34,1.56,.64,1);
            position:relative;z-index:1;
          "></div>
          <div id="pCardB" style="
            width:90px;height:56px;border-radius:12px;
            background:linear-gradient(135deg,#1E1B4B,${c2});
            transform:rotate(10deg) translateX(-10px);
            box-shadow:0 12px 40px rgba(192,38,211,0.5);
            transition:all 1.2s cubic-bezier(.34,1.56,.64,1);
            position:relative;z-index:0;
          "></div>
        </div>

        <!-- Сумма -->
        <div style="
          font-size:56px;font-weight:900;color:#fff;line-height:1;
          text-shadow:0 0 50px rgba(167,139,250,0.8);
          margin-bottom:8px;
        ">${amount}</div>
        <div style="font-size:20px;font-weight:700;
          color:rgba(167,139,250,0.7);letter-spacing:4px;margin-bottom:24px;">NVC</div>

        <!-- Статус -->
        <div style="color:rgba(255,255,255,0.5);font-size:15px;margin-bottom:20px;">
          ${titles[type] || "Обработка..."}
        </div>

        <!-- Лоадер -->
        <div style="
          width:44px;height:44px;margin:0 auto;
          border:3px solid rgba(124,58,237,0.2);
          border-top-color:#7C3AED;
          border-radius:50%;
          animation:spin .7s linear infinite;
        "></div>
      </div>
    `;

    // Сводим карточки
    setTimeout(() => {
      const a = document.getElementById("pCardA");
      const b = document.getElementById("pCardB");
      if (a) a.style.transform = "rotate(0deg) translateX(22px)";
      if (b) b.style.transform = "rotate(0deg) translateX(-22px)";
    }, 200);
  },

  _hidePayAnim() {
    const el = document.getElementById("payAnimation");
    if (el) el.style.display = "none";
  },

  // ─── РЕФЕРАЛ ──────────────────────────────────────
  async _processReferral(refCode) {
    const d = await API.get(CONFIG.BIN_USERS);
    for (const [uid, user] of Object.entries(d.users || {})) {
      if (user.referral_code === refCode && uid != this.state.uid) {
        d.users[uid].referral_count = (user.referral_count || 0) + 1;
        await API.put(CONFIG.BIN_USERS, d);
        await API.updateBalance(uid, 50, `Реферал: пользователь ${this.state.uid}`);
        break;
      }
    }
  },

  // ─── ВСПОМОГАТЕЛЬНЫЕ ──────────────────────────────
  _createStars() {
    const bg = document.getElementById("bgStars");
    if (!bg) return;
    for (let i = 0; i < 70; i++) {
      const s  = document.createElement("div");
      const sz = Math.random() * 2 + 0.5;
      const op = Math.random() * 0.5 + 0.1;
      s.style.cssText = `
        position:absolute;border-radius:50%;background:white;
        width:${sz}px;height:${sz}px;
        top:${Math.random()*100}%;left:${Math.random()*100}%;
        --op:${op};opacity:${op};
        animation:twinkle ${Math.random()*3+2}s infinite;
        animation-delay:${Math.random()*3}s;
      `;
      bg.appendChild(s);
    }
  },

  _showApp() {
    const loader = document.getElementById("loader");
    const app    = document.getElementById("app");
    if (loader) { loader.style.opacity="0"; setTimeout(()=>loader.style.display="none",500); }
    if (app)    { app.style.display="block"; requestAnimationFrame(()=>app.classList.add("visible")); }
  },

  _showError(msg) {
    const l = document.getElementById("loader");
    if (l) l.innerHTML = `
      <div style="text-align:center;padding:40px;">
        <div style="font-size:48px;margin-bottom:16px;">⚠️</div>
        <div style="color:rgba(255,255,255,0.6);font-size:15px;line-height:1.6;">${msg}</div>
      </div>
    `;
  }
};

// Старт
document.addEventListener("DOMContentLoaded", () => App.init());