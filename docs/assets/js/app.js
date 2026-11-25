/* =====================================================================
   Operation Tangerine 🍊 - site behaviour
   (progress lives in this browser only - localStorage, best effort)
   ===================================================================== */
(function () {
  "use strict";

  // ------------------------------------------------------------ data --

  const LABS = [
    // Day 1 - Launch Pad
    { id: "1.1", day: 1, title: "Deploy the Rescue Base", xp: 150, mins: 30 },
    { id: "1.2", day: 1, title: "Seed the Citrus Database", xp: 100, mins: 15 },
    { id: "1.3", day: 1, title: "IAM Detective", xp: 120, mins: 25 },
    { id: "1.4", day: 1, title: "Secrets Safari", xp: 100, mins: 20 },
    { id: "1.5", day: 1, title: "Lambda Liftoff", xp: 120, mins: 25 },
    { id: "1.6", day: 1, title: "CloudWatch Mission Control", xp: 120, mins: 30 },
    { id: "1.7", day: 1, title: "First Break-Fix: The Wrong Key", xp: 150, mins: 20, drill: true },
    // Day 2 - The Vector Vault
    { id: "2.1", day: 2, title: "Data API & Query Editor", xp: 100, mins: 20 },
    { id: "2.2", day: 2, title: "Agent ↔ Aurora Tools", xp: 150, mins: 25, drill: true },
    { id: "2.3", day: 2, title: "pgvector Fruit Playground", xp: 120, mins: 25 },
    { id: "2.4", day: 2, title: "Semantic Support Notes", xp: 150, mins: 30 },
    { id: "2.5", day: 2, title: "Build the KB Vector Store", xp: 150, mins: 25 },
    { id: "2.6", day: 2, title: "Knowledge Base on Aurora", xp: 200, mins: 40 },
    { id: "2.7", day: 2, title: "Metadata Filters & Hybrid Search", xp: 120, mins: 20 },
    { id: "2.8", day: 2, title: "Break-Fix: The Vault Collapses", xp: 200, mins: 30, drill: true },
    // Day 3 - Memory Lane & the MCP Bridge
    { id: "3.1", day: 3, title: "Design Agent Memory in DynamoDB", xp: 150, mins: 30 },
    { id: "3.2", day: 3, title: "Wire Memory into Zest", xp: 150, mins: 30 },
    { id: "3.3", day: 3, title: "Break-Fix: Amnesia", xp: 150, mins: 20, drill: true },
    { id: "3.4", day: 3, title: "Aurora PostgreSQL MCP Server", xp: 200, mins: 40 },
    { id: "3.5", day: 3, title: "DynamoDB MCP Server", xp: 150, mins: 25 },
    { id: "3.6", day: 3, title: "Optimize Product Search", xp: 200, mins: 40 },
    { id: "3.7", day: 3, title: "Break-Fix: Slow & Scrambled", xp: 150, mins: 25, drill: true },
    // Day 4 - Operation Tangerine
    { id: "4.1", day: 4, title: "Drill Roulette (5 spins)", xp: 250, mins: 60, drill: true },
    { id: "4.2", day: 4, title: "Triple-Fault Speedrun", xp: 200, mins: 30, drill: true },
    { id: "4.3", day: 4, title: "Mock Exam: Operation Tangerine", xp: 500, mins: 140, drill: true, boss: true },
    { id: "4.4", day: 4, title: "Debrief & Teardown", xp: 100, mins: 20 },
  ];

  const QUIZ_XP = 20;
  const QUIZ_COUNT = 24; // questions across day1-day4 pages

  const RANKS = [
    { xp: 0, name: "Seedling", emoji: "🌱" },
    { xp: 400, name: "Peel Cadet", emoji: "🍊" },
    { xp: 1200, name: "Pulp Pilot", emoji: "🛩️" },
    { xp: 2200, name: "Juice Engineer", emoji: "🧃" },
    { xp: 3200, name: "Citrus Architect", emoji: "🏗️" },
    { xp: 4200, name: "Tangerine Legend", emoji: "👑" },
  ];

  const DRILLS = [
    { name: "wrong-secret", desc: "Lambda points at the wrong Secrets Manager secret" },
    { name: "data-api", desc: "The Aurora Data API was switched off" },
    { name: "aurora-iam", desc: "A Data API permission vanished from the agent role" },
    { name: "vector-dims", desc: "The KB vector table has the wrong shape" },
    { name: "memory-iam", desc: "The agent can read memory but not write it" },
    { name: "memory-table", desc: "The agent points at a memory table that doesn't exist" },
    { name: "kb-role", desc: "The KB service role lost access to its DB secret" },
    { name: "kb-id", desc: "The agent forgot which Knowledge Base to use" },
    { name: "slow-search", desc: "Product search is crawling - indexes are gone" },
    { name: "mcp-config", desc: "The MCP config for Aurora + DynamoDB is scrambled" },
  ];

  const PAGES = [
    { href: "index.html", label: "Mission" },
    { href: "setup.html", label: "Setup" },
    { href: "day1.html", label: "Day 1" },
    { href: "day2.html", label: "Day 2" },
    { href: "day3.html", label: "Day 3" },
    { href: "day4.html", label: "Day 4 ⚡" },
    { href: "labs.html", label: "Quest Board" },
    { href: "cheatsheet.html", label: "Cheat Sheet" },
  ];

  const MASCOT = `
<svg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Zest, the tangerine robot">
  <defs>
    <radialGradient id="zg" cx="38%" cy="32%" r="70%">
      <stop offset="0" stop-color="#ffc06a"/><stop offset=".55" stop-color="#ff8a14"/><stop offset="1" stop-color="#e05f00"/>
    </radialGradient>
  </defs>
  <path d="M100 38 C104 22 112 14 122 10" stroke="#3b7d3a" stroke-width="6" stroke-linecap="round" fill="none"/>
  <circle cx="124" cy="9" r="7" fill="#ffd04d"><animate attributeName="opacity" values="1;.35;1" dur="1.6s" repeatCount="indefinite"/></circle>
  <path d="M100 42 C84 20 58 22 50 34 C70 34 86 40 100 46Z" fill="#3fae5a"/>
  <path d="M100 42 C84 20 58 22 50 34" stroke="#2a8243" stroke-width="2" fill="none"/>
  <circle cx="100" cy="112" r="74" fill="url(#zg)"/>
  <g fill="#ffb15a" opacity=".55"><circle cx="70" cy="80" r="3"/><circle cx="132" cy="70" r="2.5"/><circle cx="150" cy="120" r="3"/><circle cx="56" cy="130" r="2.5"/><circle cx="118" cy="160" r="3"/></g>
  <rect x="52" y="88" width="96" height="46" rx="23" fill="#2b1a0e"/>
  <g class="eyes">
    <ellipse cx="80" cy="111" rx="10" ry="12" fill="#7cf2ff"><animate attributeName="ry" values="12;12;1;12;12" keyTimes="0;.9;.93;.96;1" dur="4s" repeatCount="indefinite"/></ellipse>
    <ellipse cx="120" cy="111" rx="10" ry="12" fill="#7cf2ff"><animate attributeName="ry" values="12;12;1;12;12" keyTimes="0;.9;.93;.96;1" dur="4s" repeatCount="indefinite"/></ellipse>
    <circle cx="83" cy="106" r="3.5" fill="#fff"/><circle cx="123" cy="106" r="3.5" fill="#fff"/>
  </g>
  <path d="M84 150 Q100 162 116 150" stroke="#2b1a0e" stroke-width="5" stroke-linecap="round" fill="none"/>
  <circle cx="62" cy="146" r="7" fill="#ff6b6b" opacity=".45"/><circle cx="138" cy="146" r="7" fill="#ff6b6b" opacity=".45"/>
</svg>`;

  // --------------------------------------------------------- storage --

  const KEY = "tangerine-progress-v1";
  const EXAM_KEY = "tangerine-exam-v1";

  function load(key, fallback) {
    try {
      const raw = window.localStorage.getItem(key);
      return raw ? JSON.parse(raw) : fallback;
    } catch (e) {
      return fallback;
    }
  }
  function save(key, value) {
    try {
      window.localStorage.setItem(key, JSON.stringify(value));
    } catch (e) {
      /* private mode / blocked storage: progress just won't persist */
    }
  }

  let progress = load(KEY, { labs: {}, quiz: {}, roulette: [] });
  progress.labs = progress.labs || {};
  progress.quiz = progress.quiz || {};
  progress.roulette = progress.roulette || [];


  function xp() {
    const labXp = LABS.filter((l) => progress.labs[l.id]).reduce((s, l) => s + l.xp, 0);
    const quizXp = Object.values(progress.quiz).filter((v) => v === true).length * QUIZ_XP;
    return labXp + quizXp;
  }
  function rankFor(points) {
    let r = RANKS[0];
    RANKS.forEach((k) => { if (points >= k.xp) r = k; });
    return r;
  }
  function nextRank(points) {
    return RANKS.find((k) => k.xp > points);
  }

  // ------------------------------------------------------- nav/footer --

  function currentPage() {
    const p = location.pathname.split("/").pop();
    return p === "" ? "index.html" : p;
  }

  function renderNav() {
    const host = document.getElementById("site-nav");
    if (!host) return;
    const here = currentPage();
    host.innerHTML = `
      <nav class="topnav" aria-label="Main">
        <div class="bar">
          <a class="brand" href="index.html">${MASCOT}<span>Operation Tangerine<small>AWS DBs for Agentic AI</small></span></a>
          <div class="navlinks" id="navlinks">
            ${PAGES.map((p) => `<a href="${p.href}"${p.href === here ? ' aria-current="page"' : ""}>${p.label}</a>`).join("")}
          </div>
          <span class="spacer"></span>
          <a class="xp-pill" href="labs.html#ranks" title="Your XP and rank"><span class="rank-emoji" id="rank-emoji">🌱</span><span class="xp-text" id="xp-text">0 XP</span></a>
          <button class="icon-btn" id="theme-btn" type="button" aria-label="Toggle dark mode">🌓</button>
          <button class="icon-btn menu-btn" id="menu-btn" type="button" aria-label="Open menu" aria-expanded="false">☰</button>
        </div>
        <div class="progress-strip" aria-hidden="true"><span id="progress-strip"></span></div>
      </nav>`;
    const menuBtn = document.getElementById("menu-btn");
    const links = document.getElementById("navlinks");
    menuBtn.addEventListener("click", () => {
      const open = links.classList.toggle("open");
      menuBtn.setAttribute("aria-expanded", String(open));
      menuBtn.textContent = open ? "✕" : "☰";
    });
    document.getElementById("theme-btn").addEventListener("click", toggleTheme);
  }

  function renderFooter() {
    const host = document.getElementById("site-footer");
    if (!host) return;
    host.innerHTML = `
      <footer class="footer">
        <div class="container">
          <div>🍊 <strong>Operation Tangerine</strong> - a 4-day prep bootcamp for the
            <a href="https://skillbuilder.aws/learn/2MHE4K7STM/aws-databases-for-agentic-ai-demonstrated/NYCNC3CU6X" target="_blank" rel="noopener">AWS Databases for Agentic AI Demonstrated</a> exam lab.</div>
          <div>Independent study material - not affiliated with or endorsed by AWS. Citrus &amp; Co. and Zest are fictional.
            <button class="btn btn-ghost btn-sm" id="reset-progress" type="button" style="margin-left:.5rem">Reset my XP</button></div>
        </div>
      </footer>`;
    document.getElementById("reset-progress").addEventListener("click", () => {
      if (window.confirm("Reset all XP, lab checkmarks and quiz answers in this browser?")) {
        progress = { labs: {}, quiz: {}, roulette: [] };
        save(KEY, progress);
        location.reload();
      }
    });
  }

  // ----------------------------------------------------------- theme --

  function applyTheme(t) {
    if (t) document.documentElement.setAttribute("data-theme", t);
    else document.documentElement.removeAttribute("data-theme");
  }
  function toggleTheme() {
    const cur = document.documentElement.getAttribute("data-theme") ||
      (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    const next = cur === "dark" ? "light" : "dark";
    applyTheme(next);
    save("tangerine-theme", next);
  }
  applyTheme(load("tangerine-theme", null));

  // -------------------------------------------------------- XP UI ---

  function refreshXP(bump) {
    const points = xp();
    const r = rankFor(points);
    const nx = nextRank(points);
    const total = LABS.reduce((s, l) => s + l.xp, 0) + QUIZ_COUNT * QUIZ_XP;
    const elText = document.getElementById("xp-text");
    const elEmoji = document.getElementById("rank-emoji");
    if (elText) elText.textContent = `${points.toLocaleString()} XP · ${r.name}`;
    if (elEmoji) elEmoji.textContent = r.emoji;
    const strip = document.getElementById("progress-strip");
    const done = LABS.filter((l) => progress.labs[l.id]).length;
    if (strip) strip.style.width = `${Math.round((100 * done) / LABS.length)}%`;
    if (bump) {
      const pill = document.querySelector(".xp-pill");
      if (pill) { pill.classList.remove("bump"); void pill.offsetWidth; pill.classList.add("bump"); }
    }

    // day meters
    document.querySelectorAll("[data-day-progress]").forEach((el) => {
      const day = Number(el.getAttribute("data-day-progress"));
      const labs = LABS.filter((l) => l.day === day);
      const d = labs.filter((l) => progress.labs[l.id]).length;
      const bar = el.querySelector(".meter span");
      const label = el.querySelector(".meter-count");
      if (bar) bar.style.width = `${Math.round((100 * d) / labs.length)}%`;
      if (label) label.textContent = `${d}/${labs.length} labs`;
    });

    // overall meter
    document.querySelectorAll("[data-overall-progress]").forEach((el) => {
      const bar = el.querySelector(".meter span");
      const label = el.querySelector(".meter-count");
      if (bar) bar.style.width = `${Math.min(100, Math.round((100 * points) / RANKS[RANKS.length - 1].xp))}%`;
      if (label) label.textContent = nx ? `${points} / ${nx.xp} XP to ${nx.emoji} ${nx.name}` : `${points} XP - max rank!`;
    });

    // rank ladder
    document.querySelectorAll(".rank[data-xp]").forEach((el) => {
      const need = Number(el.getAttribute("data-xp"));
      el.classList.toggle("reached", points >= need);
      el.classList.toggle("current", r.xp === need);
    });

    // lab states
    document.querySelectorAll(".lab[data-lab]").forEach((el) => {
      const id = el.getAttribute("data-lab");
      const isDone = !!progress.labs[id];
      el.classList.toggle("done", isDone);
      const btn = el.querySelector(".complete-btn");
      if (btn) {
        btn.classList.toggle("is-done", isDone);
        btn.textContent = isDone ? "✓ Completed - nice!" : "Mark lab complete";
        btn.setAttribute("aria-pressed", String(isDone));
      }
    });
    document.querySelectorAll(".toc a[data-lab]").forEach((a) => {
      a.classList.toggle("done", !!progress.labs[a.getAttribute("data-lab")]);
    });

    const totalEl = document.getElementById("total-xp");
    if (totalEl) totalEl.textContent = total.toLocaleString();
    renderBoard();
  }

  // -------------------------------------------------------- labs ----

  function initLabs() {
    document.querySelectorAll(".lab[data-lab]").forEach((el) => {
      const id = el.getAttribute("data-lab");
      const meta = LABS.find((l) => l.id === id);
      if (!meta) return;
      if (meta.drill) el.classList.add("drill");
      if (meta.boss) el.classList.add("boss");
      if (!el.querySelector(".lab-foot")) {
        const foot = document.createElement("div");
        foot.className = "lab-foot";
        foot.innerHTML = `<span class="reward">🏅 Reward: +${meta.xp} XP</span><button class="complete-btn" type="button">Mark lab complete</button>`;
        el.appendChild(foot);
      }
      el.querySelector(".complete-btn").addEventListener("click", (ev) => {
        const wasDone = !!progress.labs[id];
        const before = rankFor(xp());
        if (wasDone) delete progress.labs[id];
        else progress.labs[id] = Date.now();
        save(KEY, progress);
        refreshXP(!wasDone);
        if (!wasDone) {
          const after = rankFor(xp());
          burst(ev.clientX, ev.clientY);
          toast("🍊", `Lab ${id} complete! +${meta.xp} XP`);
          if (after.name !== before.name) setTimeout(() => toast(after.emoji, `Rank up: ${after.name}!`), 700);
          const dayLabs = LABS.filter((l) => l.day === meta.day);
          if (dayLabs.every((l) => progress.labs[l.id])) {
            setTimeout(() => { rain(); toast("🏆", `Day ${meta.day} mission complete!`); }, 400);
          }
        }
      });
    });
  }

  function renderBoard() {
    const board = document.getElementById("board");
    if (!board) return;
    const filter = board.getAttribute("data-filter") || "all";
    const page = (d) => `day${d}.html`;
    board.innerHTML = LABS.filter((l) => filter === "all" || String(l.day) === filter || (filter === "drills" && l.drill))
      .map((l) => {
        const done = !!progress.labs[l.id];
        return `<a class="quest${done ? " done" : ""}${l.drill ? " drill" : ""}" href="${page(l.day)}#lab-${l.id.replace(".", "-")}">
          <div class="q-top"><span class="q-id">${l.boss ? "👾 BOSS" : l.drill ? "🔧 BREAK-FIX" : "🧪 LAB"} ${l.id}</span><span class="q-status">${done ? "✅" : "⬜"}</span></div>
          <h4>${l.title}</h4>
          <div class="q-meta">Day ${l.day} · ⏱ ${l.mins} min · +${l.xp} XP</div>
        </a>`;
      }).join("");
  }

  function initBoardFilters() {
    const wrap = document.getElementById("board-filters");
    const board = document.getElementById("board");
    if (!wrap || !board) return;
    wrap.addEventListener("click", (e) => {
      const b = e.target.closest("button[data-filter]");
      if (!b) return;
      wrap.querySelectorAll("button").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
      board.setAttribute("data-filter", b.getAttribute("data-filter"));
      renderBoard();
    });
  }

  // --------------------------------------------------------- quiz ---

  function initQuizzes() {
    document.querySelectorAll(".quiz").forEach((quiz) => {
      const qs = quiz.querySelectorAll(".q");
      const scoreEl = document.createElement("div");
      scoreEl.className = "quiz-score";
      quiz.appendChild(scoreEl);

      const updateScore = () => {
        let answered = 0, right = 0;
        qs.forEach((q) => {
          const v = progress.quiz[q.getAttribute("data-q")];
          if (v !== undefined) { answered++; if (v === true) right++; }
        });
        scoreEl.textContent = answered
          ? `Score: ${right}/${qs.length}${answered === qs.length ? (right === qs.length ? " - flawless! 🏆" : " - review the ones you missed 👀") : ""}`
          : `${qs.length} questions · +${QUIZ_XP} XP for each one you get right first try`;
      };

      qs.forEach((q) => {
        const id = q.getAttribute("data-q");
        const answer = Number(q.getAttribute("data-answer"));
        const opts = q.querySelectorAll("button.opt");
        const reveal = (picked) => {
          q.classList.add("answered");
          opts.forEach((o, i) => {
            o.disabled = true;
            if (i === answer) o.classList.add("right");
            if (i === picked && picked !== answer) o.classList.add("wrong");
          });
        };
        const prior = progress.quiz[id];
        if (prior !== undefined) reveal(prior === true ? answer : -1);
        opts.forEach((o, i) => {
          o.type = "button";
          o.addEventListener("click", (ev) => {
            if (q.classList.contains("answered")) return;
            const ok = i === answer;
            progress.quiz[id] = ok;
            save(KEY, progress);
            reveal(i);
            updateScore();
            refreshXP(ok);
            if (ok) { burst(ev.clientX, ev.clientY, 18); toast("✨", `Correct! +${QUIZ_XP} XP`); }
          });
        });
      });
      updateScore();
    });
  }

  // ------------------------------------------------------ code copy --

  function initCopy() {
    document.querySelectorAll("pre").forEach((pre) => {
      if (pre.querySelector(".copy-btn")) return;
      const btn = document.createElement("button");
      btn.className = "copy-btn";
      btn.type = "button";
      btn.textContent = "Copy";
      btn.addEventListener("click", async () => {
        const code = pre.querySelector("code") || pre;
        const text = code.innerText.replace(/\n$/, "");
        try {
          await navigator.clipboard.writeText(text);
        } catch (e) {
          const ta = document.createElement("textarea");
          ta.value = text; document.body.appendChild(ta); ta.select();
          try { document.execCommand("copy"); } catch (e2) { /* ignore */ }
          ta.remove();
        }
        btn.textContent = "Copied!";
        btn.classList.add("copied");
        setTimeout(() => { btn.textContent = "Copy"; btn.classList.remove("copied"); }, 1600);
      });
      pre.appendChild(btn);
    });
  }

  // ------------------------------------------------------------ TOC --

  function initToc() {
    const toc = document.getElementById("toc");
    const main = document.querySelector("main");
    if (!toc || !main) return;
    const heads = main.querySelectorAll("h2[id], .lab[id]");
    const items = [];
    heads.forEach((h) => {
      const isLab = h.classList.contains("lab");
      const label = isLab ? (h.querySelector("h3")?.textContent || h.id) : h.textContent;
      const labId = isLab ? h.getAttribute("data-lab") : null;
      items.push(`<li><a href="#${h.id}"${isLab ? ` class="lab-link" data-lab="${labId}"` : ""}>${isLab ? labId + " " : ""}${label}</a></li>`);
    });
    toc.innerHTML = `<h4>On this page</h4><ol>${items.join("")}</ol>`;
    const links = toc.querySelectorAll("a");
    if ("IntersectionObserver" in window) {
      const obs = new IntersectionObserver((entries) => {
        entries.forEach((en) => {
          if (en.isIntersecting) {
            links.forEach((a) => a.classList.toggle("active", a.getAttribute("href") === `#${en.target.id}`));
          }
        });
      }, { rootMargin: "-90px 0px -70% 0px" });
      heads.forEach((h) => obs.observe(h));
    }
  }

  // ------------------------------------------------- toast/confetti --

  let toastWrap;
  function toast(emoji, text) {
    if (!toastWrap) {
      toastWrap = document.createElement("div");
      toastWrap.className = "toast-wrap";
      toastWrap.setAttribute("role", "status");
      document.body.appendChild(toastWrap);
    }
    const t = document.createElement("div");
    t.className = "toast";
    t.innerHTML = `<span class="t-emoji">${emoji}</span><span>${text}</span>`;
    toastWrap.appendChild(t);
    setTimeout(() => { t.classList.add("out"); setTimeout(() => t.remove(), 400); }, 2600);
  }

  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  let canvas, ctx, particles = [], rafId = null;
  const COLORS = ["#ff7a00", "#ff9a2e", "#ffc27a", "#2f9e5a", "#ffd04d", "#e0445f", "#ffffff"];

  function ensureCanvas() {
    if (canvas) return;
    canvas = document.createElement("canvas");
    canvas.id = "confetti";
    document.body.appendChild(canvas);
    ctx = canvas.getContext("2d");
    const size = () => { canvas.width = innerWidth * devicePixelRatio; canvas.height = innerHeight * devicePixelRatio; };
    size();
    addEventListener("resize", size);
  }
  function spawn(x, y, n, spread, up) {
    for (let i = 0; i < n; i++) {
      const a = Math.random() * Math.PI * 2;
      const v = Math.random() * spread + 2;
      particles.push({
        x: x * devicePixelRatio, y: y * devicePixelRatio,
        vx: Math.cos(a) * v * devicePixelRatio,
        vy: (Math.sin(a) * v - up) * devicePixelRatio,
        r: (Math.random() * 5 + 3) * devicePixelRatio,
        c: COLORS[(Math.random() * COLORS.length) | 0],
        rot: Math.random() * 6, vr: Math.random() * 0.3 - 0.15,
        life: 90 + Math.random() * 40, round: Math.random() < 0.4,
      });
    }
    if (!rafId) rafId = requestAnimationFrame(tick);
  }
  function tick() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    particles = particles.filter((p) => p.life > 0);
    particles.forEach((p) => {
      p.vy += 0.22 * devicePixelRatio; p.vx *= 0.99; p.x += p.vx; p.y += p.vy; p.rot += p.vr; p.life--;
      ctx.save(); ctx.translate(p.x, p.y); ctx.rotate(p.rot); ctx.globalAlpha = Math.min(1, p.life / 30);
      ctx.fillStyle = p.c;
      if (p.round) { ctx.beginPath(); ctx.arc(0, 0, p.r * 0.6, 0, Math.PI * 2); ctx.fill(); }
      else ctx.fillRect(-p.r / 2, -p.r / 4, p.r, p.r / 2);
      ctx.restore();
    });
    rafId = particles.length ? requestAnimationFrame(tick) : null;
    if (!rafId) ctx.clearRect(0, 0, canvas.width, canvas.height);
  }
  function burst(x, y, n) {
    if (reduceMotion) return;
    ensureCanvas();
    spawn(x || innerWidth / 2, y || innerHeight / 2, n || 60, 9, 6);
  }
  function rain() {
    if (reduceMotion) return;
    ensureCanvas();
    for (let i = 0; i < 6; i++) setTimeout(() => spawn(Math.random() * innerWidth, -10, 40, 4, -2), i * 180);
  }

  // ---------------------------------------------------- exam timer --

  function initExam() {
    const root = document.getElementById("exam-console");
    if (!root) return;
    const LIMIT = 140 * 60 * 1000;
    const clock = root.querySelector(".clock");
    const startBtn = root.querySelector("[data-exam=start]");
    const pauseBtn = root.querySelector("[data-exam=pause]");
    const resetBtn = root.querySelector("[data-exam=reset]");
    let st = load(EXAM_KEY, { start: null, pausedAt: null, offset: 0, checks: {} });
    st.checks = st.checks || {};

    const elapsed = () => {
      if (!st.start) return 0;
      const end = st.pausedAt || Date.now();
      return end - st.start - st.offset;
    };
    const fmt = (ms) => {
      const s = Math.max(0, Math.round(ms / 1000));
      const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = s % 60;
      return `${h}:${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
    };
    let announced = {};
    const render = () => {
      const left = LIMIT - elapsed();
      clock.textContent = fmt(left);
      clock.classList.toggle("warn", left < 30 * 60000 && left >= 10 * 60000);
      clock.classList.toggle("danger", left < 10 * 60000);
      startBtn.disabled = !!st.start && !st.pausedAt;
      pauseBtn.disabled = !st.start;
      pauseBtn.textContent = st.pausedAt ? "▶ Resume" : "⏸ Pause";
      startBtn.textContent = st.start ? "▶ Running" : "▶ Start the clock";
      [30, 10].forEach((mark) => {
        if (st.start && !st.pausedAt && left < mark * 60000 && left > (mark - 1) * 60000 && !announced[mark]) {
          announced[mark] = true;
          toast("⏰", `${mark} minutes left - verify your fixes!`);
        }
      });
      if (left <= 0 && st.start && !st.pausedAt) { clock.textContent = "TIME!"; }
    };
    startBtn.addEventListener("click", () => {
      if (!st.start) { st.start = Date.now(); st.offset = 0; st.pausedAt = null; save(EXAM_KEY, st); toast("🚀", "Clock started - read ALL the guidance first."); }
      render();
    });
    pauseBtn.addEventListener("click", () => {
      if (!st.start) return;
      if (st.pausedAt) { st.offset += Date.now() - st.pausedAt; st.pausedAt = null; }
      else st.pausedAt = Date.now();
      save(EXAM_KEY, st);
      render();
    });
    resetBtn.addEventListener("click", () => {
      if (!window.confirm("Reset the exam clock and challenge checklist?")) return;
      st = { start: null, pausedAt: null, offset: 0, checks: {} };
      save(EXAM_KEY, st);
      root.querySelectorAll(".challenge-list input").forEach((i) => (i.checked = false));
      render();
    });
    root.querySelectorAll(".challenge-list input").forEach((input) => {
      const id = input.getAttribute("data-ch");
      input.checked = !!st.checks[id];
      input.addEventListener("change", (ev) => {
        st.checks[id] = input.checked;
        save(EXAM_KEY, st);
        if (input.checked) burst(ev.clientX || innerWidth / 2, ev.clientY || innerHeight / 2, 30);
        const all = [...root.querySelectorAll(".challenge-list input")].every((i) => i.checked);
        if (all) { rain(); toast("👑", "All 7 challenges done - run labctl exam check!"); }
      });
    });
    render();
    setInterval(render, 1000);
  }

  // ------------------------------------------------------- roulette --

  function initRoulette() {
    const root = document.getElementById("roulette");
    if (!root) return;
    const wheel = root.querySelector(".wheel");
    const picked = root.querySelector(".picked");
    const desc = root.querySelector(".picked-desc");
    const cmd = root.querySelector(".picked-cmd");
    const spun = root.querySelector(".spun-list");
    const btn = root.querySelector("button");
    const drawSpun = () => {
      spun.innerHTML = progress.roulette.length
        ? "Spun so far: " + progress.roulette.map((n) => `<code>${n}</code>`).join(" ")
        : "No spins yet. Five spins completes Lab 4.1.";
    };
    drawSpun();
    btn.addEventListener("click", () => {
      btn.disabled = true;
      wheel.classList.add("spinning");
      let n = 0;
      const pool = DRILLS.filter((d) => !progress.roulette.includes(d.name));
      const choices = pool.length ? pool : DRILLS;
      const iv = setInterval(() => {
        const d = DRILLS[(Math.random() * DRILLS.length) | 0];
        picked.textContent = d.name;
        if (++n > 14) {
          clearInterval(iv);
          const final = choices[(Math.random() * choices.length) | 0];
          picked.textContent = final.name;
          desc.textContent = final.desc;
          cmd.innerHTML = `<pre><code class="language-bash">labctl break ${final.name}\n# ...fix it (hints allowed after minute 8: labctl hint ${final.name})...\nlabctl check ${final.name}</code></pre>`;
          initCopy();
          if (window.Prism) window.Prism.highlightAllUnder(cmd);
          wheel.classList.remove("spinning");
          btn.disabled = false;
          if (!progress.roulette.includes(final.name)) progress.roulette.push(final.name);
          save(KEY, progress);
          drawSpun();
          burst(innerWidth / 2, innerHeight / 2, 40);
          if (progress.roulette.length === 5) toast("🎰", "Five spins! Finish the fixes, then mark Lab 4.1 complete.");
        }
      }, 80);
    });
  }

  // ------------------------------------------------- mascot slots ---

  function initMascots() {
    document.querySelectorAll("[data-mascot]").forEach((el) => {
      el.innerHTML = MASCOT;
      const svg = el.querySelector("svg");
      if (svg) svg.classList.add("mascot");
    });
  }

  // --------------------------------------------------------- boot ---

  function boot() {
    renderNav();
    renderFooter();
    initMascots();
    initLabs();
    initQuizzes();
    initCopy();
    initToc();
    initBoardFilters();
    initExam();
    initRoulette();
    refreshXP(false);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();

  window.Tangerine = { LABS, RANKS, DRILLS, xp, toast, burst, rain };
})();
