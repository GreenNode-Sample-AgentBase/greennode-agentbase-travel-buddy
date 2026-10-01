/* ============================================================
   Travel Buddy — trợ lý du lịch có trí nhớ
   Frontend vanilla JS: không build step, không CDN, không framework.
   Backend phục vụ tĩnh tại GET / (cùng origin → fetch tương đối).
   ============================================================ */

"use strict";

/* ------------------- Hằng số & tiện ích chung ------------------- */

const $ = (id) => document.getElementById(id);

const API = {
  INVOCATIONS: "/invocations",
  INFO: "/api/info",
  MEMORY: "/api/memory",
  HISTORY: "/api/history",
  ACTORS: "/api/actors",
  STREAM: "/api/chat/stream",
};

// API key (khi backend bật AGENT_API_KEY) — lưu localStorage, tự đính kèm mọi request
const KEY_STORAGE = "travel_buddy_api_key";
function apiKey() { try { return localStorage.getItem(KEY_STORAGE) || ""; } catch { return ""; } }
function authHeaders(extra = {}) {
  const h = Object.assign({}, extra);
  const k = apiKey();
  if (k) h["X-API-Key"] = k;
  return h;
}

// Header bắt buộc khi POST /invocations
const HDR_USER = "X-GreenNode-AgentBase-User-Id";
const HDR_SESSION = "X-GreenNode-AgentBase-Session-Id";

const state = {
  actors: [],     // [{ actorId, sessions: [string] }]
  actor: null,    // actorId đang chọn
  session: null,  // sessionId đang chọn
  info: null,     // kết quả GET /api/info
  sending: false, // đang chờ agent trả lời
  viewToken: 0,   // tăng mỗi khi đổi phiên → bỏ qua response cũ
};

let memoryToken = 0; // tránh race khi tải /api/memory

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
  ));
}

function truncate(s, n) {
  s = String(s);
  return s.length > n ? s.slice(0, n - 1) + "…" : s;
}

// Tên user mới → slug chữ thường (bỏ dấu tiếng Việt)
function slugify(s) {
  return String(s)
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/đ/g, "d")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 48);
}

// Thời gian tương đối ("x phút trước"), fallback về chuỗi gốc
function relativeTime(raw) {
  if (!raw) return "";
  const t = new Date(raw).getTime();
  if (Number.isNaN(t)) return String(raw);
  const min = Math.floor((Date.now() - t) / 60000);
  if (min < 1) return "vừa xong";
  if (min < 60) return `${min} phút trước`;
  const h = Math.floor(min / 60);
  if (h < 24) return `${h} giờ trước`;
  const d = Math.floor(h / 24);
  if (d < 30) return `${d} ngày trước`;
  return String(raw);
}

/* ------------------- Markdown tối giản -------------------
   Escape HTML TRƯỚC, rồi xử lý: **bold**, `code`, ```khối code```,
   link [text](url) / URL trần (target=_blank), heading in đậm. */

function renderInlineMd(s) {
  const stash = [];
  const keep = (html) => { stash.push(html); return `\u0001${stash.length - 1}\u0001`; };

  // Inline code giữ token để bold/link không đụng vào nội dung
  s = s.replace(/`([^`\n]+)`/g, (m, code) => keep(`<code class="md-code">${code}</code>`));
  s = s.replace(/\*\*([^*\n]+)\*\*/g, "<strong>$1</strong>");
  s = s.replace(/\[([^\]\n]+)\]\((https?:\/\/[^)\s]+)\)/g,
    '<a class="md-link" href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
  s = s.replace(/(^|[\s(])(https?:\/\/[^\s<)"]+)/g,
    (m, p, url) => `${p}<a class="md-link" href="${url}" target="_blank" rel="noopener noreferrer">${url}</a>`);
  s = s.replace(/\u0001(\d+)\u0001/g, (m, i) => stash[Number(i)]);
  return s;
}

function renderMarkdown(raw) {
  const esc = escapeHtml(raw ?? "");
  const stash = [];
  const keep = (html) => { stash.push(html); return `\u0000${stash.length - 1}\u0000`; };

  // 1) Khối code ```...``` → token (nội dung đã escape, giữ nguyên)
  let text = esc.replace(/```[^\n]*\n?([\s\S]*?)```/g, (m, code) =>
    keep(`<pre class="md-pre"><code>${code.replace(/\n$/, "")}</code></pre>`));

  // 2) Từng dòng: heading in đậm, danh sách gạch đầu dòng, đoạn văn
  const out = [];
  let list = null;
  const flushList = () => {
    if (list) {
      out.push(`<ul class="md-ul">${list.map((li) => `<li>${li}</li>`).join("")}</ul>`);
      list = null;
    }
  };

  for (const rawLine of text.split("\n")) {
    const line = rawLine.trim();

    // Dòng là token khối code → đẩy nguyên, không bọc <p>
    if (/^\u0000\d+\u0000$/.test(line)) { flushList(); out.push(line); continue; }

    const heading = line.match(/^(#{1,6})\s+(.+)$/);
    if (heading) {
      flushList();
      out.push(`<div class="md-h md-h${heading[1].length}"><strong>${renderInlineMd(heading[2])}</strong></div>`);
      continue;
    }

    const item = line.match(/^(?:[-*•]|\d+[.)])\s+(.+)$/);
    if (item) { (list ??= []).push(renderInlineMd(item[1])); continue; }

    if (!line) { flushList(); continue; }

    flushList();
    out.push(`<p class="md-p">${renderInlineMd(line)}</p>`);
  }
  flushList();

  // 3) Phục hồi khối code từ token
  return out.join("\n").replace(/\u0000(\d+)\u0000/g, (m, i) => stash[Number(i)]);
}

/* ------------------- Lớp gọi API (cùng origin) ------------------- */

async function requestJson(url, options = {}) {
  options.headers = authHeaders(options.headers || {});
  let res;
  try {
    res = await fetch(url, options);
  } catch (e) {
    throw new Error(`không kết nối được server (${e.message})`);
  }
  let data = null;
  try { data = await res.json(); } catch { /* body rỗng hoặc không phải JSON */ }
  if (!res.ok) throw new Error((data && (data.error || data.message)) || `HTTP ${res.status}`);
  if (data && data.status === "error") throw new Error(data.error || "Agent trả về lỗi.");
  return data;
}

const getJson = (url) => requestJson(url);

function postInvocation(message) {
  return requestJson(API.INVOCATIONS, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      [HDR_USER]: state.actor,
      [HDR_SESSION]: state.session,
    },
    body: JSON.stringify({ message }),
  });
}

/* ---------- Streaming SSE: POST /api/chat/stream ---------- */

// Bong bóng live cho token stream (render text thô khi đang stream)
function appendLiveBotBubble() {
  const wrap = document.createElement("div");
  wrap.className = "msg bot";
  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.textContent = "🧭";
  const body = document.createElement("div");
  body.className = "msg-body";
  const name = document.createElement("div");
  name.className = "msg-name";
  name.textContent = "Travel Buddy";
  const bubble = document.createElement("div");
  bubble.className = "bubble md streaming";
  const cursor = document.createElement("span");
  cursor.className = "stream-cursor";
  cursor.textContent = "▍";
  bubble.appendChild(cursor);
  body.appendChild(name);
  body.appendChild(bubble);
  wrap.appendChild(avatar);
  wrap.appendChild(body);
  $("chatMessages").appendChild(wrap);
  scrollToBottom();
  return { wrap: wrap, bubble: bubble, body: body };
}

// Gọi stream; mỗi token → render dần; xong → markdown + callout như bubble thường
async function postStream(message, typing) {
  const res = await fetch(API.STREAM, {
    method: "POST",
    headers: authHeaders({
      "Content-Type": "application/json",
      [HDR_USER]: state.actor,
      [HDR_SESSION]: state.session,
    }),
    body: JSON.stringify({ message }),
  });
  const ct = res.headers.get("content-type") || "";
  if (!res.ok || !ct.includes("text/event-stream")) {
    let data = null;
    try { data = await res.json(); } catch { /* không phải JSON */ }
    throw new Error((data && (data.error || data.message)) || `HTTP ${res.status}`);
  }

  const live = appendLiveBotBubble();
  let full = "";
  let memoriesUsed = [];

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    const parts = buf.split("\n\n");
    buf = parts.pop() || "";
    for (const part of parts) {
      const line = part.split("\n").find((l) => l.startsWith("data:"));
      if (!line) continue;
      let ev = null;
      try { ev = JSON.parse(line.slice(5).trim()); } catch { continue; }
      if (ev.type === "token") {
        full += ev.text || "";
        live.bubble.textContent = full;
        const cursor = document.createElement("span");
        cursor.className = "stream-cursor";
        cursor.textContent = "▍";
        live.bubble.appendChild(cursor);
        scrollToBottom();
      } else if (ev.type === "done") {
        full = ev.response || full;
        memoriesUsed = ev.memories_used || [];
        live.bubble.classList.remove("streaming");
        live.bubble.innerHTML = renderMarkdown(full);
        if (memoriesUsed.length) live.body.appendChild(buildMemoryCallout(memoriesUsed));
        scrollToBottom();
      } else if (ev.type === "error") {
        throw new Error(ev.error || "Lỗi stream.");
      }
    }
  }
  if (!full) throw new Error("Stream kết thúc mà không có nội dung.");
  return { status: "success", response: full, memories_used: memoriesUsed };
}

/* ------------------- Chat: bong bóng tin nhắn ------------------- */

function scrollToBottom() {
  const box = $("chatMessages");
  box.scrollTop = box.scrollHeight;
}

function appendBubble(role, text, memoriesUsed) {
  const wrap = document.createElement("div");
  wrap.className = "msg " + (role === "user" ? "user" : "bot");

  if (role === "user") {
    // Tin nhắn của user: bên phải, giữ nguyên text (textContent → an toàn)
    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.textContent = text;
    wrap.appendChild(bubble);
  } else {
    const avatar = document.createElement("div");
    avatar.className = "avatar";
    avatar.textContent = "🧭";
    avatar.title = "Travel Buddy";

    const body = document.createElement("div");
    body.className = "msg-body";

    const name = document.createElement("div");
    name.className = "msg-name";
    name.textContent = "Travel Buddy";

    const bubble = document.createElement("div");
    bubble.className = "bubble md";
    bubble.innerHTML = renderMarkdown(text); // renderMarkdown tự escape trước

    body.appendChild(name);
    body.appendChild(bubble);
    if (Array.isArray(memoriesUsed) && memoriesUsed.length > 0) {
      body.appendChild(buildMemoryCallout(memoriesUsed));
    }

    wrap.appendChild(avatar);
    wrap.appendChild(body);
  }

  $("chatMessages").appendChild(wrap);
  scrollToBottom();
  return wrap;
}

function buildMemoryCallout(facts) {
  const box = document.createElement("div");
  box.className = "mem-callout";
  const title = document.createElement("div");
  title.className = "mem-callout-title";
  title.textContent = "✨ Agent vừa nhớ lại:";
  const ul = document.createElement("ul");
  for (const fact of facts) {
    const li = document.createElement("li");
    li.textContent = fact;
    ul.appendChild(li);
  }
  box.appendChild(title);
  box.appendChild(ul);
  return box;
}

function renderEmptyChat() {
  const hasTarget = state.actor && state.session;
  $("chatMessages").innerHTML = `
    <div class="chat-empty">
      <div class="chat-empty-icon">🧭</div>
      <div class="chat-empty-title">${hasTarget
        ? "Bắt đầu trò chuyện với Travel Buddy"
        : "Chọn người dùng &amp; phiên để bắt đầu"}</div>
      <div class="chat-empty-sub">${hasTarget
        ? "Hỏi về lịch trình, chỗ ở, ẩm thực… Agent sẽ dần ghi nhớ sở thích và chi tiết chuyến đi của bạn."
        : "Chọn một người dùng và phiên hội thoại ở cột bên trái, hoặc bấm “+ Phiên mới”."}</div>
    </div>`;
}

/* ------------------- Chỉ báo "đang gõ" (3 chấm + đồng hồ) ------------------- */

function showTypingIndicator() {
  const wrap = document.createElement("div");
  wrap.className = "msg bot typing";

  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.textContent = "🧭";

  const body = document.createElement("div");
  body.className = "msg-body";

  const name = document.createElement("div");
  name.className = "msg-name";
  name.textContent = "Travel Buddy";

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.innerHTML =
    '<span class="typing-dots"><span></span><span></span><span></span></span>' +
    '<span class="typing-timer">0.0 giây</span>';

  body.appendChild(name);
  body.appendChild(bubble);
  wrap.appendChild(avatar);
  wrap.appendChild(body);
  $("chatMessages").appendChild(wrap);
  scrollToBottom();

  const startedAt = Date.now();
  const timerEl = bubble.querySelector(".typing-timer");
  const timer = setInterval(() => {
    timerEl.textContent = ((Date.now() - startedAt) / 1000).toFixed(1) + " giây";
  }, 100);

  return { wrap, stop: () => { clearInterval(timer); wrap.remove(); } };
}

/* ------------------- Trạng thái chat & chấm trạng thái ------------------- */

function clearChat() {
  state.viewToken += 1;
  $("chatMessages").innerHTML = "";
}

function setDot(kind) {
  const dot = $("statusDot");
  dot.classList.remove("ok", "err");
  if (kind) dot.classList.add(kind);
}

/* ------------------- GET /api/info ------------------- */

async function loadInfo() {
  try {
    const data = await getJson(API.INFO);
    state.info = data;
    $("infoAgent").textContent = data.agent || "—";
    $("infoMemory").textContent = String(data.memory_id || "—").slice(0, 8); // memory_id rút gọn 8 ký tự
    $("infoModel").textContent = data.llm_model || "—";
    $("infoGateway").textContent = truncate(data.gateway || data.mcp_url || "—", 30);
    setDot("ok");
  } catch (e) {
    setDot("err");
    showToast("Không tải được /api/info: " + e.message);
  }
}

// Backend bật AGENT_API_KEY nhưng chưa có key → hỏi 1 lần, lưu localStorage
function ensureApiKey() {
  if (!state.info || !state.info.auth_required || apiKey()) return;
  const k = window.prompt(
    "Endpoint này được bảo vệ bằng API key (biến AGENT_API_KEY khi deploy).\nNhập API key:",
  );
  if (k) {
    try { localStorage.setItem(KEY_STORAGE, k.trim()); } catch { /* private mode */ }
  }
}

/* ------------------- Người dùng & phiên (GET /api/actors) ------------------- */

// Gộp danh sách actor từ server với các actor/phiên tạo cục bộ (chưa sync)
function mergeActors(remoteActors) {
  const byId = new Map();
  for (const a of remoteActors) {
    byId.set(a.actorId, {
      actorId: a.actorId,
      sessions: Array.isArray(a.sessions) ? [...a.sessions] : [],
    });
  }
  for (const local of state.actors) {
    const remote = byId.get(local.actorId);
    if (!remote) {
      byId.set(local.actorId, { actorId: local.actorId, sessions: [...(local.sessions || [])] });
    } else {
      for (const s of local.sessions || []) {
        if (!remote.sessions.includes(s)) remote.sessions.push(s);
      }
    }
  }
  state.actors = [...byId.values()];
}

function renderUsers() {
  const box = $("usersList");
  box.innerHTML = "";
  if (!state.actors.length) {
    box.innerHTML = '<div class="list-empty">Chưa có người dùng nào.</div>';
    return;
  }
  for (const actor of state.actors) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "list-item" + (actor.actorId === state.actor ? " active" : "");

    const icon = document.createElement("span");
    icon.className = "list-item-icon";
    icon.textContent = (actor.actorId || "?").charAt(0);

    const main = document.createElement("span");
    main.className = "list-item-main";
    main.textContent = actor.actorId;
    const sub = document.createElement("span");
    sub.className = "list-item-sub";
    sub.textContent = `${(actor.sessions || []).length} phiên`;

    btn.appendChild(icon);
    btn.appendChild(main);
    btn.appendChild(sub);
    btn.addEventListener("click", () => selectUser(actor.actorId));
    box.appendChild(btn);
  }
}

function renderSessions() {
  const box = $("sessionsList");
  box.innerHTML = "";
  if (!state.actor) {
    box.innerHTML = '<div class="list-empty">Chọn người dùng trước.</div>';
    return;
  }
  const actor = state.actors.find((a) => a.actorId === state.actor);
  const sessions = actor ? actor.sessions || [] : [];
  if (!sessions.length) {
    box.innerHTML = '<div class="list-empty">Chưa có phiên nào.</div>';
    return;
  }
  for (const sessionId of sessions) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "list-item" + (sessionId === state.session ? " active" : "");
    const icon = document.createElement("span");
    icon.className = "list-item-icon";
    icon.textContent = "#";
    const main = document.createElement("span");
    main.className = "list-item-main";
    main.textContent = sessionId;
    btn.appendChild(icon);
    btn.appendChild(main);
    btn.addEventListener("click", () => selectSession(sessionId));
    box.appendChild(btn);
  }
}

function updateChips() {
  $("chipUser").textContent = state.actor ? "@" + state.actor : "@—";
  $("chipSession").textContent = state.session || "—";
  $("memoryTitle").textContent = state.actor ? `🧠 Bộ nhớ của ${state.actor}` : "🧠 Bộ nhớ";
}

function selectUser(actorId) {
  state.actor = actorId;
  const actor = state.actors.find((a) => a.actorId === actorId);
  const sessions = actor ? actor.sessions || [] : [];
  if (!state.session || !sessions.includes(state.session)) {
    state.session = sessions[0] || null;
  }
  renderUsers();
  renderSessions();
  updateChips();
  clearChat();
  loadHistory();
  loadMemory(); // tự làm mới bộ nhớ khi đổi user
}

function selectSession(sessionId) {
  state.session = sessionId;
  renderSessions();
  updateChips();
  clearChat();
  loadHistory();
  loadMemory();
}

// "+ Người dùng mới": input → slug chữ thường, chọn ngay
function createUser() {
  const input = $("newUserInput");
  const slug = slugify(input.value);
  if (!slug) {
    showToast("Nhập tên người dùng (chữ/số/gạch ngang, không dấu) trước đã!");
    return;
  }
  if (!state.actors.some((a) => a.actorId === slug)) {
    state.actors.push({ actorId: slug, sessions: [] });
  }
  input.value = "";
  selectUser(slug);
}

// "+ Phiên mới": id = "s-" + timestamp
function createSession() {
  if (!state.actor) {
    showToast("Hãy chọn hoặc tạo người dùng trước.");
    return;
  }
  const sessionId = "s-" + Date.now();
  const actor = state.actors.find((a) => a.actorId === state.actor);
  if (actor && !actor.sessions.includes(sessionId)) actor.sessions.unshift(sessionId);
  selectSession(sessionId);
}

async function loadActors() {
  try {
    const data = await getJson(API.ACTORS);
    mergeActors(Array.isArray(data.actors) ? data.actors : []);
  } catch (e) {
    showToast("Không tải được danh sách người dùng: " + e.message);
  }
  if (!state.actor && state.actors.length) {
    selectUser(state.actors[0].actorId);
  } else {
    renderUsers();
    renderSessions();
    updateChips();
  }
}

// Làm mới danh sách actor sau khi agent trả lời (không đổi lựa chọn)
async function refreshActorsSilently() {
  try {
    const data = await getJson(API.ACTORS);
    mergeActors(Array.isArray(data.actors) ? data.actors : []);
    renderUsers();
    renderSessions();
  } catch { /* im lặng — không làm phiền người dùng */ }
}

/* ------------------- GET /api/history ------------------- */

async function loadHistory() {
  const token = state.viewToken;
  if (!state.actor || !state.session) {
    renderEmptyChat();
    return;
  }
  try {
    const data = await getJson(
      `${API.HISTORY}?actor=${encodeURIComponent(state.actor)}&session=${encodeURIComponent(state.session)}`
    );
    if (token !== state.viewToken) return; // đã đổi phiên trong lúc chờ
    const events = Array.isArray(data.events) ? data.events : [];
    if (!events.length) {
      renderEmptyChat();
      return;
    }
    for (const ev of events) {
      appendBubble(ev.role === "user" ? "user" : "bot", ev.message || "", []);
    }
  } catch (e) {
    if (token !== state.viewToken) return;
    renderEmptyChat();
    showToast("Không tải được lịch sử hội thoại: " + e.message);
  }
}

/* ------------------- Gửi tin nhắn → POST /invocations ------------------- */

async function sendMessage() {
  const input = $("composerInput");
  const text = input.value.trim();

  if (!text || state.sending) return;
  if (!state.actor || !state.session) {
    showToast("Chưa chọn người dùng / phiên hội thoại — hãy chọn ở cột bên trái.");
    return;
  }

  state.sending = true;
  $("sendBtn").disabled = true;

  appendBubble("user", text, []);
  input.value = "";
  autosizeComposer();

  const typing = showTypingIndicator();

  try {
    // ① Thử streaming SSE — token render dần trong bong bóng live
    let data;
    try {
      data = await postStream(text, typing);
    } catch (streamErr) {
      // ② Streaming không khả dụng (404/401/lỗi mạng) → fallback /invocations
      const fallback = await postInvocation(text);
      if (!fallback || fallback.status !== "success") {
        throw new Error((fallback && fallback.error) || streamErr.message || "Agent trả về lỗi.");
      }
      data = fallback;
    }
    typing.stop();
    if (!data || data.status === "error") {
      throw new Error((data && data.error) || "Agent trả về lỗi.");
    }
    setDot("ok");
    loadMemory();            // tự làm mới bộ nhớ sau mỗi câu trả lời của bot
    refreshActorsSilently(); // actor/phiên mới có thể xuất hiện trên server
  } catch (e) {
    typing.stop();
    setDot("err");
    appendBubble("bot", `⚠️ **Không gọi được agent:** ${e.message}`, []);
    showToast("Gọi agent thất bại: " + e.message);
  } finally {
    state.sending = false;
    $("sendBtn").disabled = false;
    $("composerInput").focus();
  }
}

/* ------------------- Panel "Bộ nhớ" → GET /api/memory ------------------- */

// Tên nhóm: map strategy_id/strategy → tiêu đề tiếng Việt, fallback tên gốc
function strategyTitle(group) {
  const sid = String(group.strategy_id || "").toLowerCase();
  const sname = String(group.strategy || "");
  const lower = sname.toLowerCase();
  if (sid.includes("preference") || lower.includes("preference")) return "⭐ Sở thích";
  if (sid.includes("trip") || lower.includes("trip")) return "📌 Sự kiện chuyến đi";
  return sname || group.strategy_id || "Nhóm khác";
}

function buildGroupCard(group) {
  const sec = document.createElement("div");
  sec.className = "mem-group";

  const title = document.createElement("div");
  title.className = "mem-group-title";
  title.textContent = strategyTitle(group);
  sec.appendChild(title);

  // Lỗi của nhóm → ghi chú đỏ
  if (group.error) {
    const err = document.createElement("div");
    err.className = "mem-group-error";
    err.textContent = "⚠️ " + group.error;
    sec.appendChild(err);
    return sec;
  }

  const records = Array.isArray(group.records) ? group.records : [];
  if (!records.length) {
    const empty = document.createElement("div");
    empty.className = "mem-group-empty";
    empty.textContent = "Chưa có bản ghi trong nhóm này.";
    sec.appendChild(empty);
    return sec;
  }

  for (const rec of records) {
    const card = document.createElement("div");
    card.className = "mem-card";
    const fact = document.createElement("div");
    fact.className = "mem-card-fact";
    fact.textContent = rec.memory || "";
    const time = document.createElement("div");
    time.className = "mem-card-time";
    time.textContent = relativeTime(rec.createdAt);
    card.appendChild(fact);
    card.appendChild(time);
    sec.appendChild(card);
  }
  return sec;
}

async function loadMemory() {
  const token = ++memoryToken;
  const body = $("memoryBody");

  if (!state.actor) {
    body.innerHTML = '<div class="mem-empty">Chưa có dữ liệu — hãy trò chuyện để agent học về bạn</div>';
    renderRecent([]);
    return;
  }

  body.innerHTML = '<div class="mem-loading">Đang tải bộ nhớ…</div>';
  try {
    const data = await getJson(`${API.MEMORY}?actor=${encodeURIComponent(state.actor)}`);
    if (token !== memoryToken) return; // đã đổi user trong lúc chờ
    const groups = Array.isArray(data.groups) ? data.groups : [];
    body.innerHTML = "";
    if (!groups.length) {
      body.innerHTML = '<div class="mem-empty">Chưa có dữ liệu — hãy trò chuyện để agent học về bạn</div>';
    }
    for (const group of groups) body.appendChild(buildGroupCard(group));
  } catch (e) {
    if (token !== memoryToken) return;
    body.innerHTML = `<div class="mem-error">Không tải được bộ nhớ: ${escapeHtml(e.message)}</div>`;
  }
  loadRecent();
}

/* ------------------- "Hội thoại gần đây" (5 sự kiện cuối) ------------------- */

function renderRecent(events) {
  const box = $("recentList");
  box.innerHTML = "";
  if (!events.length) {
    box.innerHTML = '<div class="recent-empty">Chưa có hội thoại nào.</div>';
    return;
  }
  for (const ev of events) {
    const item = document.createElement("div");
    item.className = "recent-item" + (ev.role === "user" ? " from-user" : "");
    const role = document.createElement("span");
    role.className = "recent-role";
    role.textContent = ev.role === "user" ? "Bạn" : "Travel Buddy";
    const msg = document.createElement("span");
    msg.className = "recent-msg";
    msg.textContent = truncate(ev.message || "", 80); // cắt 80 ký tự
    item.appendChild(role);
    item.appendChild(msg);
    box.appendChild(item);
  }
}

async function loadRecent() {
  if (!state.actor || !state.session) {
    renderRecent([]);
    return;
  }
  try {
    const data = await getJson(
      `${API.HISTORY}?actor=${encodeURIComponent(state.actor)}&session=${encodeURIComponent(state.session)}`
    );
    const events = Array.isArray(data.events) ? data.events : [];
    renderRecent(events.slice(-5).reverse()); // mới nhất lên đầu
  } catch {
    $("recentList").innerHTML = '<div class="recent-empty">Không tải được hội thoại gần đây.</div>';
  }
}

/* ------------------- Toast lỗi (tự ẩn, đóng được) ------------------- */

let toastTimer = null;

function showToast(message) {
  const toast = $("toast");
  $("toastMsg").textContent = message;
  toast.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove("show"), 6000);
}

/* ------------------- Composer (textarea tự giãn) ------------------- */

function autosizeComposer() {
  const el = $("composerInput");
  el.style.height = "auto";
  el.style.height = Math.min(el.scrollHeight, 160) + "px";
}

/* ------------------- Gắn sự kiện & khởi động ------------------- */

function bindEvents() {
  $("sendBtn").addEventListener("click", sendMessage);

  const composer = $("composerInput");
  composer.addEventListener("input", autosizeComposer);
  composer.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) { // Enter gửi, Shift+Enter xuống dòng
      e.preventDefault();
      sendMessage();
    }
  });

  $("newUserBtn").addEventListener("click", createUser);
  $("newUserInput").addEventListener("keydown", (e) => {
    if (e.key === "Enter") { e.preventDefault(); createUser(); }
  });

  $("newSessionBtn").addEventListener("click", createSession);
  $("memoryRefreshBtn").addEventListener("click", loadMemory);

  // Panel "Bộ nhớ" mở/thu trên màn hình hẹp
  $("memoryToggle").addEventListener("click", () => $("layout").classList.toggle("show-memory"));
  $("panelClose").addEventListener("click", () => $("layout").classList.remove("show-memory"));

  $("toastClose").addEventListener("click", () => {
    clearTimeout(toastTimer);
    $("toast").classList.remove("show");
  });
}

async function init() {
  bindEvents();
  await loadInfo();
  ensureApiKey(); // nếu backend bật AGENT_API_KEY mà chưa có key → hỏi 1 lần
  await loadActors();
}

document.addEventListener("DOMContentLoaded", init);
