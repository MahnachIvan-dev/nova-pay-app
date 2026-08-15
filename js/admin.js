// ═══════════════════════════════════════════════════════
// NOVA PAY — ADMIN ПАНЕЛЬ ВЛАДЕЛЬЦА
// ═══════════════════════════════════════════════════════

const Admin = {

  // ─── ГЛАВНАЯ ПАНЕЛЬ ───────────────────────────────
  async render() {
    const el = document.getElementById("adminContent");
    if (!el) return;

    // Проверка
    if (!App.state.isOwner) {
      el.innerHTML = `<div class="empty-state">
        <div class="empty-icon">🔒</div>
        <div class="empty-title">Нет доступа</div>
      </div>`;
      return;
    }

    el.innerHTML = `<div class="loading-center"><div class="loader-ring"></div></div>`;

    // Подгружаем данные
    const [users, pending, checks, txs] = await Promise.all([
      API.getAllUsers(),
      API.getPending(),
      API.getAllChecks(),
      API.getAllTransactions()
    ]);

    const totalUsers    = Object.keys(users).length;
    const pendingCount  = Object.values(pending).filter(r => r.status === "pending").length;
    const activeChecks  = Object.values(checks).filter(c => !c.is_used).length;
    const totalNVC      = Object.values(users).reduce((s,u) => s + (u.balance||0), 0);

    el.innerHTML = `
      <!-- Сводка -->
      <div class="stats-grid" style="grid-template-columns:repeat(2,1fr);margin-bottom:16px;">
        <div class="stat-card">
          <div class="stat-val" style="color:var(--violet);">${totalUsers}</div>
          <div class="stat-label">Пользователей</div>
        </div>
        <div class="stat-card">
          <div class="stat-val" style="color:${pendingCount>0?'var(--gold)':'var(--success)'};">
            ${pendingCount}
          </div>
          <div class="stat-label">Заявок</div>
        </div>
        <div class="stat-card">
          <div class="stat-val" style="color:var(--pink);">${activeChecks}</div>
          <div class="stat-label">Активных чеков</div>
        </div>
        <div class="stat-card">
          <div class="stat-val" style="color:var(--success);">${totalNVC}</div>
          <div class="stat-label">NVC в обороте</div>
        </div>
      </div>

      <!-- Кнопки разделов -->
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:20px;">

        <button class="btn btn-primary" onclick="Admin.showPending()">
          💳 Заявки
          ${pendingCount > 0 ? `<span style="background:var(--gold);color:#000;
            border-radius:20px;padding:2px 8px;font-size:11px;margin-left:4px;">${pendingCount}</span>` : ""}
        </button>

        <button class="btn btn-primary" onclick="Admin.showCreateCheck()">
          🎰 Создать чек
        </button>

        <button class="btn btn-secondary" onclick="Admin.showGiveNVC()">
          💰 Выдать NVC
        </button>

        <button class="btn btn-secondary" onclick="Admin.showContestWinner()">
          🏆 Приз конкурса
        </button>

        <button class="btn btn-secondary" onclick="Admin.showRefLinks()">
          🔗 Реф. ссылки
        </button>

        <button class="btn btn-secondary" onclick="Admin.showAllChecks()">
          📋 Все чеки
        </button>

        <button class="btn btn-secondary" onclick="Admin.showUsers()">
          👥 Пользователи
        </button>

        <button class="btn btn-secondary" onclick="Admin.showAllTx()">
          📊 Транзакции
        </button>

      </div>

      <!-- Последние заявки -->
      <div class="section-title">🕐 Последние заявки на покупку NVC</div>
      <div id="adminPendingList"></div>
    `;

    // Рендерим последние заявки
    this._renderPendingList(pending, "adminPendingList", 5);
  },

  // ─── ЗАЯВКИ НА ПОКУПКУ NVC ───────────────────────
  async showPending() {
    const pending = await API.getPending();
    Sound.click();

    const rows = Object.values(pending)
      .filter(r => r.status === "pending")
      .reverse();

    App._showModal(`
      <div class="modal-title">💳 Заявки на пополнение</div>
      ${rows.length === 0
        ? `<div class="empty-state" style="padding:30px 0;">
             <div class="empty-icon">✅</div>
             <div class="empty-title">Новых заявок нет</div>
           </div>`
        : rows.map(r => `
            <div style="
              background:var(--card-bg);border:1px solid var(--card-border);
              border-radius:14px;padding:16px;margin-bottom:10px;
            ">
              <div style="display:flex;justify-content:space-between;margin-bottom:10px;">
                <div>
                  <div style="font-weight:700;">${r.full_name}</div>
                  <div style="font-size:12px;color:var(--text2);">
                    @${r.username || "—"} · ${r.uid}
                  </div>
                  <div style="font-size:11px;color:var(--text2);margin-top:2px;">
                    ${Utils.formatDateTime(r.created_at)}
                  </div>
                </div>
                <div style="text-align:right;">
                  <div style="font-size:22px;font-weight:900;color:var(--violet);">${r.nvc}</div>
                  <div style="font-size:11px;color:var(--text2);">NVC</div>
                  <div style="font-size:12px;color:var(--gold);">⭐ ${r.stars} Stars</div>
                </div>
              </div>
              <div style="font-size:11px;color:var(--text2);margin-bottom:10px;">
                ID заявки: <code style="background:rgba(124,58,237,0.2);padding:2px 6px;border-radius:4px;">${r.req_id}</code>
              </div>
              <div style="display:flex;gap:8px;">
                <button class="btn btn-success" style="flex:1;padding:10px;"
                  onclick="Admin.approve('${r.req_id}')">
                  ✅ Подтвердить
                </button>
                <button class="btn btn-danger" style="flex:1;padding:10px;"
                  onclick="Admin.reject('${r.req_id}')">
                  ❌ Отклонить
                </button>
              </div>
            </div>
          `).join("")
      }
    `);
  },

  async approve(reqId) {
    Sound.click();
    const req = await API.approvePending(reqId, App.state.uid);
    if (!req) return Utils.toast("❌ Ошибка подтверждения", "error");

    Sound.bonus();
    Utils.toast(`✅ +${req.nvc} NVC → ${req.full_name}`, "success");
    App.closeModal();
    await Utils.sleep(300);
    this.showPending();
  },

  async reject(reqId) {
    Sound.click();
    await API.rejectPending(reqId, App.state.uid);
    Utils.toast("❌ Заявка отклонена", "warning");
    App.closeModal();
    await Utils.sleep(300);
    this.showPending();
  },

  // ─── СОЗДАНИЕ ЧЕКА ────────────────────────────────
  showCreateCheck() {
    Sound.click();
    App._showModal(`
      <div class="modal-title">🎰 Создать денежный чек</div>

      <div class="form-group">
        <label class="form-label">Сумма NVC</label>
        <input class="form-input" id="checkAmount" type="number"
          placeholder="100" min="1"/>
      </div>

      <div class="form-group">
        <label class="form-label">Описание</label>
        <input class="form-input" id="checkDesc"
          placeholder="Призовой чек конкурса"/>
      </div>

      <div class="form-group">
        <label class="form-label">Срок действия (дней)</label>
        <input class="form-input" id="checkDays" type="number"
          value="30" min="1" max="365"/>
      </div>

      <button class="btn btn-primary" onclick="Admin.createCheck()">
        🎰 Создать чек
      </button>
    `);
  },

  async createCheck() {
    const amount = parseInt(document.getElementById("checkAmount")?.value);
    const desc   = document.getElementById("checkDesc")?.value?.trim();
    const days   = parseInt(document.getElementById("checkDays")?.value) || 30;

    if (!amount || amount <= 0) {
      Sound.error();
      return Utils.toast("❌ Введите сумму", "error");
    }
    if (!desc) {
      Sound.error();
      return Utils.toast("❌ Введите описание", "error");
    }

    Sound.click();
    const check = await API.createCheck({
      amount, description: desc,
      createdBy: parseInt(App.state.uid),
      expiryDays: days
    });

    const botUser = CONFIG.BOT_USERNAME;
    const link    = `https://t.me/${botUser}?start=check_${check.check_id}`;

    App.closeModal();
    await Utils.sleep(200);

    Sound.bonus();

    App._showModal(`
      <div class="modal-title">✅ Чек создан!</div>

      <!-- Превью чека -->
      <div style="
        background:linear-gradient(135deg,#070714,#1E1B4B);
        border-radius:16px;padding:24px;text-align:center;
        border:1px solid rgba(124,58,237,0.3);margin-bottom:16px;
        position:relative;overflow:hidden;
      ">
        <div style="position:absolute;left:0;top:0;bottom:0;width:3px;
          background:linear-gradient(to bottom,var(--purple),var(--pink));"></div>
        <div style="font-size:11px;font-weight:800;letter-spacing:3px;
          color:rgba(255,255,255,0.5);margin-bottom:16px;">NOVA PAY · ЧЕК</div>
        <div style="font-size:56px;font-weight:900;color:#fff;
          text-shadow:0 0 40px rgba(167,139,250,0.8);">${amount}</div>
        <div style="font-size:16px;font-weight:700;letter-spacing:4px;
          color:rgba(167,139,250,0.8);margin-bottom:12px;">NVC</div>
        <div style="font-size:13px;color:rgba(255,255,255,0.5);">${desc}</div>
        <div style="font-size:11px;color:rgba(255,255,255,0.3);margin-top:8px;">
          ${check.check_id} · до ${Utils.formatDate(check.expires_at)}
        </div>
      </div>

      <div class="form-group">
        <label class="form-label">Ссылка на чек</label>
        <input class="form-input" value="${link}" readonly
          onclick="this.select()" style="font-size:12px;"/>
      </div>

      <div style="display:flex;gap:8px;">
        <button class="btn btn-primary" style="flex:1;"
          onclick="Admin.copyCheckLink('${link}')">
          📋 Скопировать
        </button>
        <button class="btn btn-secondary" style="flex:1;"
          onclick="Admin.shareCheck('${link}',${amount})">
          📤 Поделиться
        </button>
      </div>
    `);
  },

  async copyCheckLink(link) {
    try { await navigator.clipboard.writeText(link); } catch(e) {}
    Sound.click();
    Utils.toast("✅ Ссылка скопирована!", "success");
  },

  shareCheck(link, amount) {
    const text = `💰 Денежный чек на ${amount} NVC от NOVA CREATIVE STUDIO!\n\nАктивируй в Nova Pay 👇`;
    window.open(`https://t.me/share/url?url=${encodeURIComponent(link)}&text=${encodeURIComponent(text)}`,"_blank");
  },

  // ─── ВЫДАТЬ NVC ───────────────────────────────────
  showGiveNVC() {
    Sound.click();
    App._showModal(`
      <div class="modal-title">💰 Выдать NVC пользователю</div>
      <div class="form-group">
        <label class="form-label">Telegram ID пользователя</label>
        <input class="form-input" id="giveUid" type="number" placeholder="123456789"/>
      </div>
      <div class="form-group">
        <label class="form-label">Сумма NVC</label>
        <input class="form-input" id="giveAmount" type="number" placeholder="50"/>
      </div>
      <div class="form-group">
        <label class="form-label">Причина</label>
        <input class="form-input" id="giveReason" placeholder="Начисление от администратора"/>
      </div>
      <button class="btn btn-primary" onclick="Admin.giveNVC()">💰 Начислить</button>
    `);
  },

  async giveNVC() {
    const uid    = parseInt(document.getElementById("giveUid")?.value);
    const amount = parseInt(document.getElementById("giveAmount")?.value);
    const reason = document.getElementById("giveReason")?.value?.trim()
                || "Начисление от администратора";

    if (!uid || !amount || amount <= 0) {
      Sound.error();
      return Utils.toast("❌ Заполните поля", "error");
    }

    const user = await API.getUser(uid);
    if (!user) {
      Sound.error();
      return Utils.toast("❌ Пользователь не найден", "error");
    }

    Sound.click();
    await API.updateBalance(uid, amount, reason);
    Sound.bonus();
    Utils.toast(`✅ +${amount} NVC → ${user.full_name}`, "success");
    App.closeModal();
  },

  // ─── ПРИЗ КОНКУРСА ────────────────────────────────
  showContestWinner() {
    Sound.click();
    App._showModal(`
      <div class="modal-title">🏆 Вознаграждение за конкурс</div>

      <div class="form-group">
        <label class="form-label">Telegram ID победителя</label>
        <input class="form-input" id="winnerUid" type="number" placeholder="123456789"/>
      </div>

      <div class="form-group">
        <label class="form-label">Место</label>
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;">
          ${[
            {place:"1", nvc:100, emoji:"🥇"},
            {place:"2", nvc:60,  emoji:"🥈"},
            {place:"3", nvc:40,  emoji:"🥉"},
          ].map(p => `
            <button class="btn btn-secondary place-btn"
              data-nvc="${p.nvc}" data-place="${p.place}"
              onclick="Admin._selectPlace(this)"
              style="flex-direction:column;padding:12px;gap:4px;">
              <span style="font-size:24px;">${p.emoji}</span>
              <span style="font-size:11px;">${p.nvc} NVC</span>
            </button>
          `).join("")}
        </div>
      </div>

      <div class="form-group">
        <label class="form-label">Или своя сумма (NVC)</label>
        <input class="form-input" id="winnerAmount" type="number"
          placeholder="100" id="winnerAmount"/>
      </div>

      <div class="form-group">
        <label class="form-label">Название конкурса</label>
        <input class="form-input" id="contestName"
          placeholder="Конкурс рисунков #1"/>
      </div>

      <button class="btn btn-primary" style="background:linear-gradient(135deg,#F59E0B,#EF4444);"
        onclick="Admin.giveContestPrize()">
        🏆 Выдать приз
      </button>
    `);
  },

  _selectPlace(btn) {
    document.querySelectorAll(".place-btn").forEach(b => {
      b.style.borderColor = "var(--card-border)";
      b.style.background  = "var(--card-bg)";
    });
    btn.style.borderColor = "var(--gold)";
    btn.style.background  = "rgba(245,158,11,0.15)";
    document.getElementById("winnerAmount").value = btn.dataset.nvc;
  },

  async giveContestPrize() {
    const uid    = parseInt(document.getElementById("winnerUid")?.value);
    const amount = parseInt(document.getElementById("winnerAmount")?.value);
    const contest= document.getElementById("contestName")?.value?.trim() || "Конкурс";

    if (!uid || !amount || amount <= 0) {
      Sound.error();
      return Utils.toast("❌ Заполните поля", "error");
    }

    const user = await API.getUser(uid);
    if (!user) {
      Sound.error();
      return Utils.toast("❌ Пользователь не найден", "error");
    }

    Sound.click();
    await API.updateBalance(uid, amount, `🏆 Приз за ${contest}`);
    await API.addTransaction({
      from_id:0, to_id:uid, amount,
      type:"bonus",
      description:`🏆 Победа в конкурсе: ${contest}`
    });

    Sound.check();
    App.closeModal();
    Utils.toast(`🏆 Приз ${amount} NVC → ${user.full_name}`, "success");
  },

  // ─── РЕФЕРАЛЬНЫЕ ССЫЛКИ ───────────────────────────
  showRefLinks() {
    Sound.click();
    const botUser    = CONFIG.BOT_USERNAME;
    const ordersBot  = CONFIG.ORDERS_BOT;
    const channel    = CONFIG.CHANNEL;

    App._showModal(`
      <div class="modal-title">🔗 Реферальные ссылки</div>

      <div class="section-title">Ссылки для продвижения</div>

      ${[
        {
          title:  "🤖 Бот Nova Pay",
          desc:   "Ссылка на платёжный бот",
          link:   `https://t.me/${botUser}`,
          color:  "var(--purple)"
        },
        {
          title:  "🛒 Бот заказов",
          desc:   "Ссылка на бот оформления заказов",
          link:   `https://t.me/${ordersBot}`,
          color:  "var(--pink)"
        },
        {
          title:  "📢 Канал студии",
          desc:   "Ссылка на официальный канал",
          link:   `https://t.me/${channel.replace("@","")}`,
          color:  "#38BDF8"
        },
        {
          title:  "💳 Мини-приложение",
          desc:   "Прямая ссылка на Nova Pay",
          link:   `https://t.me/${botUser}?startapp=`,
          color:  "var(--gold)"
        }
      ].map(item => `
        <div style="
          background:var(--card-bg);border:1px solid var(--card-border);
          border-radius:14px;padding:14px;margin-bottom:10px;
          border-left:3px solid ${item.color};
        ">
          <div style="font-weight:700;margin-bottom:4px;">${item.title}</div>
          <div style="font-size:12px;color:var(--text2);margin-bottom:10px;">${item.desc}</div>
          <div style="
            font-size:12px;color:var(--violet);
            background:rgba(124,58,237,0.1);
            padding:6px 10px;border-radius:8px;
            word-break:break-all;margin-bottom:10px;
          ">${item.link}</div>
          <div style="display:flex;gap:8px;">
            <button class="btn btn-secondary" style="flex:1;padding:9px;"
              onclick="Admin.copyLink('${item.link}')">
              📋 Скопировать
            </button>
            <button class="btn btn-primary" style="flex:1;padding:9px;"
              onclick="Admin.shareLink('${item.link}','${item.title}')">
              📤 Поделиться
            </button>
          </div>
        </div>
      `).join("")}

      <div class="section-title" style="margin-top:16px;">Генератор реферального URL</div>
      <div class="form-group">
        <label class="form-label">Добавить реф. код (опционально)</label>
        <input class="form-input" id="customRefCode"
          placeholder="REF-ABCDEF или оставьте пустым"/>
      </div>
      <button class="btn btn-primary" onclick="Admin.generateRefUrl()">
        🔗 Сгенерировать ссылку
      </button>
      <div id="genRefResult" style="margin-top:12px;"></div>
    `);
  },

  async copyLink(link) {
    try { await navigator.clipboard.writeText(link); } catch(e) {}
    Sound.click();
    Utils.toast("✅ Скопировано!", "success");
  },

  shareLink(link, title) {
    const text = `${title} — NOVA CREATIVE STUDIO`;
    window.open(
      `https://t.me/share/url?url=${encodeURIComponent(link)}&text=${encodeURIComponent(text)}`,
      "_blank"
    );
  },

  generateRefUrl() {
    const code = document.getElementById("customRefCode")?.value?.trim();
    const base  = `https://t.me/${CONFIG.BOT_USERNAME}`;
    const link  = code ? `${base}?start=${code}` : base;
    const el    = document.getElementById("genRefResult");
    if (!el) return;
    el.innerHTML = `
      <div style="
        background:rgba(124,58,237,0.1);border:1px solid rgba(124,58,237,0.3);
        border-radius:10px;padding:12px;
        font-size:13px;color:var(--violet);word-break:break-all;
      ">${link}</div>
      <div style="display:flex;gap:8px;margin-top:8px;">
        <button class="btn btn-secondary" style="flex:1;padding:9px;"
          onclick="Admin.copyLink('${link}')">📋 Копировать</button>
        <button class="btn btn-primary" style="flex:1;padding:9px;"
          onclick="Admin.shareLink('${link}','Nova Pay')">📤 Поделиться</button>
      </div>
    `;
    Sound.click();
  },

  // ─── ВСЕ ЧЕКИ ─────────────────────────────────────
  async showAllChecks() {
    Sound.click();
    const checks = await API.getAllChecks();
    const list   = Object.values(checks).reverse();

    App._showModal(`
      <div class="modal-title">📋 Все чеки (${list.length})</div>
      <div style="max-height:60vh;overflow-y:auto;">
        ${list.length === 0
          ? `<div class="empty-state"><div class="empty-icon">🎰</div>
               <div class="empty-title">Чеков нет</div></div>`
          : list.map(c => `
              <div style="
                background:var(--card-bg);border:1px solid var(--card-border);
                border-radius:12px;padding:14px;margin-bottom:8px;
                border-left:3px solid ${c.is_used ? 'var(--danger)' : 'var(--success)'};
              ">
                <div style="display:flex;justify-content:space-between;margin-bottom:6px;">
                  <div>
                    <div style="font-weight:700;">${c.check_id}</div>
                    <div style="font-size:12px;color:var(--text2);">${c.description}</div>
                  </div>
                  <div style="text-align:right;">
                    <div style="font-size:20px;font-weight:800;color:var(--violet);">
                      ${c.amount} NVC
                    </div>
                    <div style="font-size:11px;color:${c.is_used?'var(--danger)':'var(--success)'};">
                      ${c.is_used ? "✗ Использован" : "✓ Активен"}
                    </div>
                  </div>
                </div>
                <div style="font-size:11px;color:var(--text2);">
                  Создан: ${Utils.formatDate(c.created_at)} ·
                  До: ${Utils.formatDate(c.expires_at)}
                  ${c.used_by ? `· Использовал: ${c.used_by}` : ""}
                </div>
              </div>
            `).join("")
        }
      </div>
    `);
  },

  // ─── ПОЛЬЗОВАТЕЛИ ─────────────────────────────────
  async showUsers() {
    Sound.click();
    const users = await API.getAllUsers();
    const list  = Object.values(users)
      .sort((a,b) => (b.balance||0) - (a.balance||0))
      .slice(0,20);

    App._showModal(`
      <div class="modal-title">👥 Пользователи (${Object.keys(users).length})</div>
      <div style="max-height:60vh;overflow-y:auto;">
        ${list.map((u, i) => `
          <div style="
            display:flex;align-items:center;gap:12px;
            padding:12px;background:var(--card-bg);
            border:1px solid var(--card-border);
            border-radius:12px;margin-bottom:8px;
          ">
            <div style="font-size:18px;font-weight:800;color:var(--text2);width:24px;">
              ${i+1}
            </div>
            <div style="flex:1;">
              <div style="font-weight:600;font-size:14px;">${u.full_name}</div>
              <div style="font-size:11px;color:var(--text2);">
                @${u.username||"—"} · ${u.telegram_id}
              </div>
            </div>
            <div style="text-align:right;">
              <div style="font-weight:800;color:var(--violet);">${u.balance||0}</div>
              <div style="font-size:10px;color:var(--text2);">NVC</div>
            </div>
            <button class="btn btn-secondary"
              style="width:auto;padding:8px 12px;font-size:12px;"
              onclick="Admin.quickGive(${u.telegram_id},'${u.full_name.replace(/'/g,"\\'")}')">
              +NVC
            </button>
          </div>
        `).join("")}
      </div>
    `);
  },

  async quickGive(uid, name) {
    const amount = prompt(`Сколько NVC начислить → ${name}?`);
    if (!amount || isNaN(parseInt(amount))) return;
    await API.updateBalance(uid, parseInt(amount), "Ручное начисление администратора");
    Sound.bonus();
    Utils.toast(`✅ +${amount} NVC → ${name}`, "success");
  },

  // ─── ВСЕ ТРАНЗАКЦИИ ───────────────────────────────
  async showAllTx() {
    Sound.click();
    const txs = await API.getAllTransactions();
    const last = txs.slice(0, 30);

    const icons = {
      bonus:"🎁",transfer:"💸",payment:"🛒",check:"🎰",default:"💫"
    };

    App._showModal(`
      <div class="modal-title">📊 Последние транзакции (${txs.length})</div>
      <div style="max-height:60vh;overflow-y:auto;">
        ${last.map(t => `
          <div style="
            display:flex;align-items:center;gap:10px;
            padding:12px;background:var(--card-bg);
            border:1px solid var(--card-border);
            border-radius:12px;margin-bottom:6px;
          ">
            <div style="font-size:20px;">${icons[t.type]||icons.default}</div>
            <div style="flex:1;min-width:0;">
              <div style="font-size:13px;font-weight:600;
                white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
                ${t.description||t.type}
              </div>
              <div style="font-size:11px;color:var(--text2);">
                ${Utils.formatDateTime(t.created_at)}
                ${t.from_id ? `· от ${t.from_id}` : ""}
                ${t.to_id   ? `· → ${t.to_id}`   : ""}
              </div>
            </div>
            <div style="font-size:15px;font-weight:800;color:var(--violet);">
              ${t.amount} NVC
            </div>
          </div>
        `).join("")}
      </div>
    `);
  },

  // ─── ВСПОМОГАТЕЛЬНЫЕ ──────────────────────────────
  _renderPendingList(pending, containerId, limit) {
    const el = document.getElementById(containerId);
    if (!el) return;

    const rows = Object.values(pending)
      .filter(r => r.status === "pending")
      .reverse()
      .slice(0, limit);

    if (!rows.length) {
      el.innerHTML = `<div class="empty-state" style="padding:20px 0;">
        <div class="empty-icon" style="font-size:28px;">✅</div>
        <div class="empty-desc">Новых заявок нет</div>
      </div>`;
      return;
    }

    el.innerHTML = rows.map(r => `
      <div style="
        background:var(--card-bg);border:1px solid rgba(245,158,11,0.3);
        border-radius:12px;padding:14px;margin-bottom:8px;
      ">
        <div style="display:flex;justify-content:space-between;margin-bottom:8px;">
          <div>
            <div style="font-weight:700;">${r.full_name}</div>
            <div style="font-size:12px;color:var(--text2);">⭐ ${r.stars} Stars</div>
          </div>
          <div style="font-size:20px;font-weight:800;color:var(--violet);">
            ${r.nvc} NVC
          </div>
        </div>
        <div style="display:flex;gap:8px;">
          <button class="btn btn-success" style="flex:1;padding:9px;font-size:13px;"
            onclick="Admin.approve('${r.req_id}')">✅ ОК</button>
          <button class="btn btn-danger" style="flex:1;padding:9px;font-size:13px;"
            onclick="Admin.reject('${r.req_id}')">❌ Нет</button>
        </div>
      </div>
    `).join("");
  }
};