// ═══════════════════════════════════════════════════════
// NOVA PAY — API
// ═══════════════════════════════════════════════════════

const API = {
  _cache:     {},
  _cacheTime: {},
  CACHE_TTL:  4000,

  headers: () => ({
    "X-Master-Key":    CONFIG.JSONBIN_KEY,
    "Content-Type":    "application/json",
    "X-Bin-Versioning":"false"
  }),

  async get(binId) {
    const now = Date.now();
    if (this._cache[binId] && (now - this._cacheTime[binId]) < this.CACHE_TTL) {
      return this._cache[binId];
    }
    try {
      const r = await fetch(
        `https://api.jsonbin.io/v3/b/${binId}/latest`,
        { headers: this.headers() }
      );
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const d = await r.json();
      this._cache[binId]     = d.record || {};
      this._cacheTime[binId] = now;
      return this._cache[binId];
    } catch(e) {
      console.error(`API.get(${binId}):`, e);
      return this._cache[binId] || {};
    }
  },

  async put(binId, data) {
    this._cache[binId]     = data;
    this._cacheTime[binId] = Date.now();
    try {
      const r = await fetch(
        `https://api.jsonbin.io/v3/b/${binId}`,
        { method:"PUT", headers: this.headers(), body: JSON.stringify(data) }
      );
      return r.ok;
    } catch(e) {
      console.error(`API.put(${binId}):`, e);
      return false;
    }
  },

  invalidate(binId) {
    delete this._cache[binId];
    delete this._cacheTime[binId];
  },

  // ─── USERS ─────────────────────────────────────────
  async getUser(uid) {
    const d = await this.get(CONFIG.BIN_USERS);
    return d.users?.[String(uid)] || null;
  },

  async saveUser(uid, data) {
    const d = await this.get(CONFIG.BIN_USERS);
    if (!d.users) d.users = {};
    d.users[String(uid)] = data;
    return await this.put(CONFIG.BIN_USERS, d);
  },

  async updateBalance(uid, delta, description = "") {
    const d    = await this.get(CONFIG.BIN_USERS);
    const user = d.users?.[String(uid)];
    if (!user) return null;

    const newBal = Math.max(0, (user.balance || 0) + delta);
    d.users[String(uid)].balance = newBal;
    if (delta > 0) d.users[String(uid)].total_earned = (user.total_earned || 0) + delta;
    else           d.users[String(uid)].total_spent  = (user.total_spent  || 0) + Math.abs(delta);

    await this.put(CONFIG.BIN_USERS, d);
    await this.addTransaction({
      from_id:     delta < 0 ? parseInt(uid) : 0,
      to_id:       delta > 0 ? parseInt(uid) : 0,
      amount:      Math.abs(delta),
      type:        delta > 0 ? "bonus" : "payment",
      description
    });
    return newBal;
  },

  async getAllUsers() {
    const d = await this.get(CONFIG.BIN_USERS);
    return d.users || {};
  },

  // ─── CARDS ─────────────────────────────────────────
  async getCard(cardId) {
    const d = await this.get(CONFIG.BIN_CARDS);
    return d.cards?.[cardId] || null;
  },

  async createCard(uid, tier = "starter") {
    const cardId  = Utils.genId("CARD");
    const cardNum = Utils.genCardNumber();
    const d = await this.get(CONFIG.BIN_CARDS);
    if (!d.cards) d.cards = {};
    d.cards[cardId] = {
      card_id:         cardId,
      card_number:     cardNum,
      owner_id:        parseInt(uid),
      tier,
      created_at:      new Date().toISOString(),
      is_active:       true,
      avatar_linked:   false,
      nickname_linked: false,
      nickname:        null
    };
    await this.put(CONFIG.BIN_CARDS, d);
    return d.cards[cardId];
  },

  // ─── TRANSACTIONS ──────────────────────────────────
  async addTransaction({ from_id, to_id, amount, type, description }) {
    const d = await this.get(CONFIG.BIN_TX);
    if (!d.transactions) d.transactions = [];
    d.transactions.push({
      tx_id:       Utils.genId("TX", 8),
      from_id:     from_id || 0,
      to_id:       to_id   || 0,
      amount,
      currency:    "NVC",
      type,
      description: description || "",
      status:      "completed",
      created_at:  new Date().toISOString()
    });
    if (d.transactions.length > 1000) d.transactions = d.transactions.slice(-1000);
    return await this.put(CONFIG.BIN_TX, d);
  },

  async getUserTransactions(uid) {
    const d = await this.get(CONFIG.BIN_TX);
    return (d.transactions || [])
      .filter(t => t.from_id == uid || t.to_id == uid)
      .reverse();
  },

  async getAllTransactions() {
    const d = await this.get(CONFIG.BIN_TX);
    return (d.transactions || []).reverse();
  },

  // ─── CHECKS ────────────────────────────────────────
  async getCheck(checkId) {
    const d = await this.get(CONFIG.BIN_CHECKS);
    return d.checks?.[checkId] || null;
  },

  async getAllChecks() {
    const d = await this.get(CONFIG.BIN_CHECKS);
    return d.checks || {};
  },

  async createCheck({ amount, description, createdBy, expiryDays = 30 }) {
    const checkId = Utils.genId("CHK");
    const d = await this.get(CONFIG.BIN_CHECKS);
    if (!d.checks) d.checks = {};
    d.checks[checkId] = {
      check_id:    checkId,
      amount,
      currency:    "NVC",
      created_by:  createdBy,
      description,
      is_used:     false,
      used_by:     null,
      used_at:     null,
      created_at:  new Date().toISOString(),
      expires_at:  new Date(Date.now() + expiryDays * 86400000).toISOString()
    };
    await this.put(CONFIG.BIN_CHECKS, d);
    return d.checks[checkId];
  },

  async activateCheck(checkId, uid) {
    const d     = await this.get(CONFIG.BIN_CHECKS);
    const check = d.checks?.[checkId];
    if (!check)                                  return { ok:false, error:"not_found"  };
    if (check.is_used)                           return { ok:false, error:"used"       };
    if (new Date(check.expires_at) < new Date()) return { ok:false, error:"expired"   };
    if (check.created_by == uid)                 return { ok:false, error:"own_check" };

    d.checks[checkId].is_used = true;
    d.checks[checkId].used_by = parseInt(uid);
    d.checks[checkId].used_at = new Date().toISOString();
    await this.put(CONFIG.BIN_CHECKS, d);

    const newBal = await this.updateBalance(uid, check.amount, `Чек ${checkId}: ${check.description}`);
    return { ok:true, amount: check.amount, newBalance: newBal };
  },

  // ─── PENDING (заявки на покупку NVC) ───────────────
  async getPending() {
    const d = await this.get(CONFIG.BIN_PENDING);
    return d.pending || {};
  },

  async createPendingRequest({ uid, username, fullName, stars, nvc }) {
    const reqId = Utils.genId("REQ");
    const d = await this.get(CONFIG.BIN_PENDING);
    if (!d.pending) d.pending = {};
    d.pending[reqId] = {
      req_id:     reqId,
      uid:        parseInt(uid),
      username,
      full_name:  fullName,
      stars,
      nvc,
      status:     "pending",
      created_at: new Date().toISOString(),
      approved_at:null,
      approved_by:null
    };
    await this.put(CONFIG.BIN_PENDING, d);
    return d.pending[reqId];
  },

  async approvePending(reqId, adminUid) {
    const d   = await this.get(CONFIG.BIN_PENDING);
    const req = d.pending?.[reqId];
    if (!req || req.status !== "pending") return false;

    d.pending[reqId].status      = "approved";
    d.pending[reqId].approved_at = new Date().toISOString();
    d.pending[reqId].approved_by = adminUid;
    await this.put(CONFIG.BIN_PENDING, d);

    await this.updateBalance(req.uid, req.nvc, `Покупка NVC за ${req.stars} Stars`);
    return req;
  },

  async rejectPending(reqId, adminUid) {
    const d = await this.get(CONFIG.BIN_PENDING);
    if (!d.pending?.[reqId]) return false;
    d.pending[reqId].status      = "rejected";
    d.pending[reqId].approved_at = new Date().toISOString();
    d.pending[reqId].approved_by = adminUid;
    await this.put(CONFIG.BIN_PENDING, d);
    return true;
  },

  // ─── REGISTER ──────────────────────────────────────
  async registerUser(uid, username, fullName) {
    const existing = await this.getUser(uid);
    if (existing) return existing;

    const card    = await this.createCard(uid, "starter");
    const refCode = Utils.genRefCode(uid);

    const user = {
      telegram_id:        parseInt(uid),
      username:           username || "",
      full_name:          fullName || String(uid),
      balance:            20,
      referral_code:      refCode,
      referred_by:        null,
      referral_count:     0,
      card_tier:          "starter",
      card_id:            card.card_id,
      registered_at:      new Date().toISOString(),
      last_weekly_bonus:  new Date(Date.now() - 8 * 86400000).toISOString(),
      total_earned:       20,
      total_spent:        0,
      subscribed_channel: false,
      is_banned:          false,
      avatar_url:         null,
      nickname_linked:    false
    };

    await this.saveUser(uid, user);
    await this.addTransaction({
      from_id:0, to_id:parseInt(uid), amount:20,
      type:"bonus", description:"Стартовый бонус при регистрации"
    });
    return user;
  }
};