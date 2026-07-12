(function () {
  "use strict";

  var cfg = window.TELEAGENT_CONFIG || {};

  // Fallbacks para valores conocidos (por si el env no está seteado en Railway).
  var GITHUB = cfg.githubUrl || "https://github.com/zzzbedream/teleagent";
  var CONTRACT = cfg.contractAddress || "0x78cce8C167583bf358B3EA1c9C409e13A7Da691a";
  var DISCORD = cfg.discordInvite || "";
  var BACKEND = (cfg.backendUrl || "").replace(/\/$/, "");
  var SNOWTRACE = "https://testnet.snowtrace.io/address/" + CONTRACT;

  // --- Wire de enlaces estáticos ---
  function setLink(id, href, opts) {
    var el = document.getElementById(id);
    if (!el) return;
    if (href) {
      el.href = href;
    } else if (opts && opts.disable) {
      el.href = "#";
      el.setAttribute("aria-disabled", "true");
      el.addEventListener("click", function (e) {
        e.preventDefault();
        alert("El enlace de invitación del bot aún no está configurado. Se activa al desplegar en Railway (variable DISCORD_INVITE_URL).");
      });
    }
  }

  setLink("nav-github", GITHUB);
  setLink("footer-github", GITHUB);
  setLink("cta-discord", DISCORD || null, { disable: !DISCORD });
  setLink("contract-link", SNOWTRACE);
  setLink("footer-contract", SNOWTRACE);

  var addr = document.getElementById("contract-addr");
  if (addr) addr.textContent = CONTRACT.slice(0, 6) + "…" + CONTRACT.slice(-4);

  // --- Demo en vivo ---
  var form = document.getElementById("demo-form");
  var input = document.getElementById("demo-input");
  var submit = document.getElementById("demo-submit");
  var output = document.getElementById("demo-output");
  var answerEl = document.getElementById("demo-answer");
  var sourcesEl = document.getElementById("demo-sources");
  var note = document.getElementById("demo-note");

  if (!BACKEND) {
    submit.disabled = true;
    note.textContent = "La demo se activa cuando el backend esté desplegado (variable BACKEND_URL).";
  }

  Array.prototype.forEach.call(document.querySelectorAll(".chip"), function (chip) {
    chip.addEventListener("click", function () {
      input.value = chip.textContent.trim();
      if (BACKEND) form.dispatchEvent(new Event("submit", { cancelable: true }));
    });
  });

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var q = input.value.trim();
    if (!q || !BACKEND) return;

    output.hidden = false;
    answerEl.className = "demo-answer loading";
    answerEl.textContent = "Consultando la documentación oficial…";
    sourcesEl.innerHTML = "";
    note.textContent = "";
    submit.disabled = true;

    var controller = new AbortController();
    var timer = setTimeout(function () { controller.abort(); }, 45000);

    fetch(BACKEND + "/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt: q }),
      signal: controller.signal
    })
      .then(function (r) {
        clearTimeout(timer);
        if (r.status === 503) throw new Error("La base de datos vectorial no está disponible ahora mismo. Intenta más tarde.");
        if (!r.ok) throw new Error("El servidor respondió con un error (HTTP " + r.status + ").");
        return r.json();
      })
      .then(function (data) {
        answerEl.className = "demo-answer";
        answerEl.textContent = data.answer || "No obtuve contenido para esta consulta.";
        sourcesEl.innerHTML = "";
        (data.sources || []).forEach(function (s) {
          var span = document.createElement("span");
          span.textContent = "📄 " + String(s).split(/[\\/]/).pop();
          sourcesEl.appendChild(span);
        });
      })
      .catch(function (err) {
        answerEl.className = "demo-answer";
        answerEl.textContent = "⚠️ " + (err.name === "AbortError"
          ? "La consulta tardó demasiado. Intenta de nuevo."
          : err.message);
      })
      .finally(function () {
        submit.disabled = false;
      });
  });
})();
