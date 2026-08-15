// ═══════════════════════════════════════════════════════
// NOVA PAY — ТРАНЗАКЦИИ
// ═══════════════════════════════════════════════════════

const Transactions = {

  icons: {
    bonus:    { icon: "🎁", color: "rgba(16,185,129,0.2)",  border: "rgba(16,185,129,0.3)"  },
    transfer: { icon: "💸", color: "rgba(124,58,237,0.2)",  border: "rgba(124,58,237,0.3)"  },
    payment:  { icon: "🛒", color: "rgba(239,68,68,0.2)",   border: "rgba(239,68,68,0.3)"   },
    check:    { icon: "🎰", color: "rgba(245,158,11,0.2)",  border: "rgba(245,158,11,0.3)"  },
    refill:   { icon: "💰", color: "rgba(16,185,129,0.2)",  border: "rgba(16,185,129,0.3)"  },
    default:  { icon: "💫", color: "rgba(124,58,237,0.15)", border: "rgba(124,58,237,0.2)"  },
  },

  render(txs, containerId, uid, limit = null) {
    const el = document.getElementById(containerId);
    if (!el) return;

    const list = limit ? txs.slice(0, limit) : txs;

    if (!list.length) {
      el.innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">💸</div>
          <div class="empty-title">Транзакций пока нет</div>
          <div class="empty-desc">Здесь появится история ваших операций</div>
        </div>
      `;
      return;
    }

    el.innerHTML = list.map(t => this._renderItem(t, uid)).join("");
  },

  _renderItem(t, uid) {
    const isIncoming = t.to_id == uid;
    const sign       = isIncoming ? "+" : "−";
    const amtColor   = isIncoming ? "var(--success)" : "var(--danger)";
    const meta       = this.icons[t.type] || this.icons.default;
    const dateStr    = Utils.formatDateTime(t.created_at);

    return `
      <div class="tx-item" style="
        display:flex;align-items:center;gap:14px;
        padding:14px 16px;
        background:var(--card-bg);
        border:1px solid var(--card-border);
        border-radius:14px;
        margin-bottom:8px;
        transition:.2s;
      ">
        <div style="
          width:44px;height:44px;flex-shrink:0;
          border-radius:14px;
          background:${meta.color};
          border:1px solid ${meta.border};
          display:flex;align-items:center;justify-content:center;
          font-size:20px;
        ">${meta.icon}</div>

        <div style="flex:1;min-width:0;">
          <div style="font-size:14px;font-weight:600;color:var(--text);
            white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
            ${t.description || t.type}
          </div>
          <div style="font-size:11px;color:var(--text2);margin-top:3px;">
            ${dateStr}
          </div>
        </div>

        <div style="
          font-size:16px;font-weight:800;
          color:${amtColor};flex-shrink:0;
        ">${sign}${t.amount} NVC</div>
      </div>
    `;
  },

  // ─── ФИЛЬТРАЦИЯ ───────────────────────────────────
  filter(txs, uid, type) {
    switch (type) {
      case "plus":  return txs.filter(t => t.to_id   == uid);
      case "minus": return txs.filter(t => t.from_id == uid);
      default:      return txs;
    }
  }
};