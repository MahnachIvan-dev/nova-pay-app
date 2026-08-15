// ═══════════════════════════════════════════════════════
// NOVA PAY — КОНФИГУРАЦИЯ
// ═══════════════════════════════════════════════════════

const CONFIG = {
  JSONBIN_KEY:  "$2a$10$.lOzWFALIQMK3kQFqrStp.I6BkC8beqHqi9ya3//aPYCUHi9lRlt2",
  BIN_USERS:    "6a807735f5f4af5e291a29e9",
  BIN_CARDS:    "6a807750da38895dfee8a151",
  BIN_TX:       "6a807770da38895dfee8a1a7",
  BIN_CHECKS:   "6a807785da38895dfee8a1e0",
  BIN_SETTINGS: "6a80779bf5f4af5e291a2afe",
  BIN_PENDING:  "6a8077b5f5f4af5e291a2b37",   // новый бин — заявки на покупку NVC

  CDN:          "https://cdn.jsdelivr.net/gh/MahnachIvan-dev/nova-pay-assets@main",
  BOT_USERNAME: "NOVACreativePay_bot",
  ORDERS_BOT:   "Nova_creativestudiobot",
  CHANNEL:      "NOVA_creators",
  OWNER_ID:     7969709802,

  TIER_COLORS: {
    starter:  { primary: "#1E1B4B", secondary: "#4C1D95", accent: "#A78BFA" },
    creative: { primary: "#2D1B69", secondary: "#7C3AED", accent: "#F0ABFC" },
    elite:    { primary: "#050505", secondary: "#4C1D95", accent: "#F59E0B" }
  },

  PAID_SERVICES: {
    music_track:    { name: "🎵 Авторский трек",  price: 150 },
    design_sticker: { name: "😄 Стикер-пак",       price: 100 },
    video_anim:     { name: "✨ Анимация и моушн", price: 200 }
  },

  // Курс звёзд → NVC
  STARS_RATES: [
    { stars: 50,  nvc: 50,  label: ""           },
    { stars: 100, nvc: 110, label: ""           },
    { stars: 250, nvc: 300, label: "🔥 Выгодно" },
    { stars: 500, nvc: 650, label: "👑 Лучший"  }
  ]
};

// ─── ЗВУКИ ────────────────────────────────────────────
const Sound = {
  _ctx: null,

  _getCtx() {
    if (!this._ctx) {
      this._ctx = new (window.AudioContext || window.webkitAudioContext)();
    }
    return this._ctx;
  },

  // Успешная оплата — красивый аккорд
  async payment() {
    const ctx  = this._getCtx();
    const notes = [523.25, 659.25, 783.99, 1046.50]; // C5 E5 G5 C6
    for (let i = 0; i < notes.length; i++) {
      await Utils.sleep(i * 80);
      this._playNote(ctx, notes[i], 0.18, 0.4, "sine");
    }
  },

  // Успешный перевод — два тона
  async transfer() {
    const ctx = this._getCtx();
    this._playNote(ctx, 440,   0.2, 0.25, "sine");
    await Utils.sleep(160);
    this._playNote(ctx, 880,   0.15, 0.35, "sine");
  },

  // Ошибка
  async error() {
    const ctx = this._getCtx();
    this._playNote(ctx, 220, 0.2, 0.3, "sawtooth");
    await Utils.sleep(150);
    this._playNote(ctx, 180, 0.15, 0.3, "sawtooth");
  },

  // Бонус — восходящая трель
  async bonus() {
    const ctx   = this._getCtx();
    const steps = [523, 659, 784, 1047, 1319];
    for (let i = 0; i < steps.length; i++) {
      await Utils.sleep(i * 60);
      this._playNote(ctx, steps[i], 0.12, 0.25, "sine");
    }
  },

  // Активация чека — фанфары
  async check() {
    const ctx   = this._getCtx();
    const chord = [523, 659, 784, 1047];
    chord.forEach(f => this._playNote(ctx, f, 0.14, 0.6, "sine"));
    await Utils.sleep(350);
    chord.forEach(f => this._playNote(ctx, f * 1.5, 0.1, 0.5, "sine"));
  },

  // Клик / подтверждение
  click() {
    try {
      const ctx = this._getCtx();
      this._playNote(ctx, 800, 0.05, 0.08, "sine");
    } catch(e) {}
  },

  _playNote(ctx, freq, gain, duration, type) {
    try {
      const osc = ctx.createOscillator();
      const g   = ctx.createGain();
      osc.connect(g);
      g.connect(ctx.destination);
      osc.type      = type;
      osc.frequency.setValueAtTime(freq, ctx.currentTime);
      g.gain.setValueAtTime(gain, ctx.currentTime);
      g.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + duration);
      osc.start(ctx.currentTime);
      osc.stop(ctx.currentTime + duration);
    } catch(e) {}
  }
};

// ─── УТИЛИТЫ ──────────────────────────────────────────
const Utils = {
  genId: (prefix, len = 6) => {
    const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
    let r = prefix + "-";
    for (let i = 0; i < len; i++) r += chars[Math.floor(Math.random() * chars.length)];
    return r;
  },

  genCardNumber: () => {
    const g = [];
    for (let i = 0; i < 4; i++) g.push(String(Math.floor(Math.random() * 9000) + 1000));
    return g.join(" ");
  },

  genRefCode: (uid) => {
    const h = String(uid).split("").reduce((a,c) => a + c.charCodeAt(0), 0);
    return "REF-" + h.toString(36).toUpperCase().padStart(6,"0");
  },

  maskCard: (num) => {
    if (!num) return "•••• •••• •••• ••••";
    const p = num.split(" ");
    return `${p[0]} •••• •••• ${p[3]}`;
  },

  formatDate: (iso) => {
    if (!iso) return "—";
    return new Date(iso).toLocaleDateString("ru-RU",
      { day:"2-digit", month:"2-digit", year:"numeric" });
  },

  formatDateTime: (iso) => {
    if (!iso) return "—";
    return new Date(iso).toLocaleString("ru-RU",
      { day:"2-digit", month:"2-digit", hour:"2-digit", minute:"2-digit" });
  },

  sleep: (ms) => new Promise(r => setTimeout(r, ms)),

  toast: (text, type = "info") => {
    const colors = {
      info:    "rgba(124,58,237,0.95)",
      success: "rgba(16,185,129,0.95)",
      error:   "rgba(239,68,68,0.95)",
      warning: "rgba(245,158,11,0.95)"
    };
    // Убираем старые тосты
    document.querySelectorAll(".nova-toast").forEach(t => t.remove());

    const t = document.createElement("div");
    t.className = "nova-toast";
    t.style.cssText = `
      position:fixed;top:76px;left:50%;transform:translateX(-50%);
      background:${colors[type]||colors.info};color:#fff;
      padding:12px 24px;border-radius:14px;
      font-size:14px;font-weight:600;font-family:'Inter',sans-serif;
      z-index:9999;white-space:nowrap;max-width:90vw;
      box-shadow:0 8px 32px rgba(0,0,0,0.4);
      animation:toastIn .3s ease;
    `;
    t.textContent = text;
    document.body.appendChild(t);
    setTimeout(() => {
      t.style.animation = "toastOut .3s ease forwards";
      setTimeout(() => t.remove(), 300);
    }, 2800);
  }
};