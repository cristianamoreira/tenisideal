// templates.js — gera HTML de um slide para cada estilo + arquétipo.
// Canvas 1080x1440. Arquétipos: capa, conteudo, cta.
// data: { kicker, titulo, corpo, cta, plug }  (campos usados variam por arquétipo)

const FONTS = "https://fonts.googleapis.com/css2?family=Sora:wght@400;600;700;800&family=Plus+Jakarta+Sans:wght@400;600;700;800&family=Fraunces:opsz,wght@9..144,400;9..144,600;9..144,900&family=Source+Serif+4:wght@400;600&family=Anton&family=Spectral:wght@400;600&family=Inter+Tight:wght@600;800&family=Inter:wght@400;600;700&family=IBM+Plex+Mono:wght@400;600;700&family=Nunito:wght@700;800&family=Playfair+Display:wght@700;900&family=Lato:wght@400;700&family=JetBrains+Mono:wght@400;700&display=swap";

function esc(s = "") {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
// quebra por finalizador .?! -> <br> (regra de carrossel: uma frase por linha no titulo)
function br(s = "") {
  return esc(s).replace(/([.?!])\s+/g, "$1<br>");
}
// realce inline: *texto* -> <span class="hl">texto</span>
function hl(s = "") {
  return esc(s).replace(/\*(.+?)\*/g, '<span class="hl">$1</span>');
}

// formato: "tiktok" -> 1080x1920 com safe-zone (evita botoes/legenda do TikTok);
//          default (undefined | "carrossel") -> 1080x1350 (4:5 feed do Instagram).
// Safe-zone TikTok: conteudo fica numa faixa superior-central. Reservado:
//   topo 240px (tabs Seguindo/Pra voce), base 540px (legenda + @user + audio),
//   direita 160px (coluna curtir/comentar/compartilhar), esquerda 72px.
function page(css, inner, formato) {
  const tiktok = formato === "tiktok";
  const H = tiktok ? 1920 : 1350;
  // aplicado DEPOIS do css do estilo -> sobrescreve o padding proprio do estilo.
  const safe = tiktok
    ? `#s{height:1920px!important;padding:320px 160px 540px 72px!important}`
    : "";
  return `<!DOCTYPE html><html><head><meta charset="utf-8">
<link href="${FONTS}" rel="stylesheet">
<style>*{margin:0;padding:0;box-sizing:border-box}
.slide{width:1080px;height:${H}px;position:relative;overflow:hidden;display:flex;flex-direction:column}
.hl{color:var(--accent)}
${css}
${safe}</style></head><body><div class="slide" id="s">${inner}</div></body></html>`;
}

// ---- estilos ----
const STYLES = {
  "glassmorphism-ibeia": {
    accent: "#F84F2E",
    css: `.slide{background:radial-gradient(circle at 20% 15%,#AF6DFF55,transparent 45%),radial-gradient(circle at 85% 80%,#F84F2E55,transparent 45%),#14110f;justify-content:center;padding:90px;--accent:#F84F2E}
    .card{background:rgba(255,255,255,.10);backdrop-filter:blur(24px);border:1px solid rgba(255,255,255,.22);border-radius:40px;padding:80px 70px}
    .kicker{font:700 30px 'Plus Jakarta Sans';color:#AF6DFF;text-transform:uppercase;letter-spacing:2px;margin-bottom:28px}
    h1{font:800 92px/1.02 'Sora';color:#fff}
    h2{font:800 76px/1.05 'Sora';color:#fff}
    p{font:400 36px/1.42 'Plus Jakarta Sans';color:#e8e2da;margin-top:32px}
    .cta{margin-top:40px;font:700 34px 'Plus Jakarta Sans';color:#fff;background:#F84F2E;display:inline-block;padding:20px 34px;border-radius:16px}
    .plug{margin-top:26px;font:600 24px 'Plus Jakarta Sans';color:#AF6DFF}`,
    capa: d => `<div class="card"><div class="kicker">${esc(d.kicker||'')}</div><h1>${hl(d.titulo)}</h1>${d.corpo?`<p>${br(d.corpo)}</p>`:''}</div>`,
    conteudo: d => `<div class="card"><div class="kicker">${esc(d.kicker||'')}</div><h2>${hl(d.titulo)}</h2>${d.corpo?`<p>${br(d.corpo)}</p>`:''}</div>`,
    cta: d => `<div class="card"><div class="kicker">${esc(d.kicker||'')}</div><h2>${hl(d.titulo)}</h2>${d.corpo?`<p>${br(d.corpo)}</p>`:''}${d.cta?`<div class="cta">${esc(d.cta)}</div>`:''}${d.plug?`<div class="plug">${esc(d.plug)}</div>`:''}</div>`,
  },

  "ticket-zerotoui": {
    accent: "#F84F2E",
    css: `.slide{background:#0a0a0a;align-items:center;justify-content:center;--accent:#F84F2E}
    .card{position:relative;width:860px;background:#FBF9F4;border-radius:44px;padding:96px 74px}
    .card:before,.card:after{content:'';position:absolute;left:50%;transform:translateX(-50%);width:120px;height:60px;background:#0a0a0a}
    .card:before{top:-1px;border-radius:0 0 120px 120px}.card:after{bottom:-1px;border-radius:120px 120px 0 0}
    .kicker{font:700 26px 'JetBrains Mono';color:#F84F2E;text-transform:uppercase;margin-bottom:26px}
    h1{font:900 92px/1.0 'Fraunces';color:#141414}
    h2{font:900 74px/1.03 'Fraunces';color:#141414}
    p{font:400 34px/1.45 'Source Serif 4';color:#333;margin-top:30px}
    .cta{margin-top:36px;font:700 32px 'Source Serif 4';color:#fff;background:#141414;display:inline-block;padding:18px 30px;border-radius:12px}
    .plug{margin-top:22px;font:600 22px 'JetBrains Mono';color:#F84F2E}`,
    capa: d => `<div class="card"><div class="kicker">${esc(d.kicker||'')}</div><h1>${hl(d.titulo)}</h1>${d.corpo?`<p>${br(d.corpo)}</p>`:''}</div>`,
    conteudo: d => `<div class="card"><div class="kicker">${esc(d.kicker||'')}</div><h2>${hl(d.titulo)}</h2>${d.corpo?`<p>${br(d.corpo)}</p>`:''}</div>`,
    cta: d => `<div class="card"><div class="kicker">${esc(d.kicker||'')}</div><h2>${hl(d.titulo)}</h2>${d.corpo?`<p>${br(d.corpo)}</p>`:''}${d.cta?`<div class="cta">${esc(d.cta)}</div>`:''}${d.plug?`<div class="plug">${esc(d.plug)}</div>`:''}</div>`,
  },

  "editorial-magazine": {
    accent: "#141414",
    css: `.slide{background:#F84F2E;padding:80px;justify-content:flex-end;--accent:#141414}
    .strip{position:absolute;top:0;left:0;right:0;padding:26px 40px;background:#141414;color:#fff;font:600 22px 'IBM Plex Mono';display:flex;justify-content:space-between}
    .kicker{font:400 30px 'Spectral';color:#141414;text-transform:uppercase;letter-spacing:2px;margin-bottom:18px}
    h1{font:400 140px/.86 'Anton';text-transform:uppercase;color:#fff}
    h2{font:400 104px/.9 'Anton';text-transform:uppercase;color:#fff}
    p{font:400 34px/1.4 'Spectral';color:#1c1109;margin-top:34px;max-width:840px}
    .cta{margin-top:36px;font:700 30px 'IBM Plex Mono';color:#F84F2E;background:#141414;display:inline-block;padding:18px 28px}
    .plug{margin-top:20px;font:400 24px 'Spectral';color:#141414}`,
    capa: d => `<div class="strip"><span>TÊNIS IDEAL</span><span>@tenisideal_br</span></div><div class="kicker">${esc(d.kicker||'')}</div><h1>${hl(d.titulo)}</h1>${d.corpo?`<p>${br(d.corpo)}</p>`:''}`,
    conteudo: d => `<div class="kicker">${esc(d.kicker||'')}</div><h2>${hl(d.titulo)}</h2>${d.corpo?`<p>${br(d.corpo)}</p>`:''}`,
    cta: d => `<div class="kicker">${esc(d.kicker||'')}</div><h2>${hl(d.titulo)}</h2>${d.corpo?`<p>${br(d.corpo)}</p>`:''}${d.cta?`<div class="cta">${esc(d.cta)}</div>`:''}${d.plug?`<div class="plug">${esc(d.plug)}</div>`:''}`,
  },

  "swiss-grid": {
    accent: "#F84F2E",
    css: `.slide{background:#f4f2ec;padding:96px;justify-content:space-between;--accent:#F84F2E}
    .top{border-top:6px solid #141414;padding-top:24px;display:flex;justify-content:space-between;font:600 24px 'Inter';text-transform:uppercase;letter-spacing:1px}
    .mid{margin-top:auto}
    .kicker{font:600 26px 'Inter';color:#F84F2E;text-transform:uppercase;letter-spacing:2px;margin-bottom:20px}
    h1{font:800 118px/.98 'Inter Tight';color:#141414;letter-spacing:-3px}
    h2{font:800 92px/1.0 'Inter Tight';color:#141414;letter-spacing:-2px}
    p{font:400 32px/1.42 'Inter';color:#333;margin-top:34px;max-width:760px;border-left:6px solid #F84F2E;padding-left:28px}
    .cta{margin-top:34px;font:700 30px 'Inter';color:#fff;background:#141414;display:inline-block;padding:18px 28px}
    .plug{margin-top:20px;font:600 22px 'Inter';color:#F84F2E}`,
    capa: d => `<div class="top"><span>TÊNIS IDEAL</span><span>${esc(d.kicker||'')}</span></div><div class="mid"><h1>${hl(d.titulo)}</h1>${d.corpo?`<p>${br(d.corpo)}</p>`:''}</div>`,
    conteudo: d => `<div class="top"><span>TÊNIS IDEAL</span><span>${esc(d.kicker||'')}</span></div><div class="mid"><h2>${hl(d.titulo)}</h2>${d.corpo?`<p>${br(d.corpo)}</p>`:''}</div>`,
    cta: d => `<div class="top"><span>TÊNIS IDEAL</span><span>${esc(d.kicker||'')}</span></div><div class="mid"><h2>${hl(d.titulo)}</h2>${d.corpo?`<p>${br(d.corpo)}</p>`:''}${d.cta?`<div class="cta">${esc(d.cta)}</div>`:''}${d.plug?`<div class="plug">${esc(d.plug)}</div>`:''}</div>`,
  },

  "brutalism": {
    accent: "#F84F2E",
    css: `.slide{background:#84CC16;padding:80px;justify-content:center;--accent:#F84F2E}
    .kicker{display:inline-block;font:700 26px 'IBM Plex Mono';background:#141414;color:#84CC16;padding:10px 18px;margin-bottom:40px;align-self:flex-start}
    h1{font:400 118px/1.18 'Anton';text-transform:uppercase;color:#141414;background:#fff;border:6px solid #141414;box-shadow:16px 16px 0 #141414;padding:40px 34px}
    h2{font:400 92px/1.04 'Anton';text-transform:uppercase;color:#141414;background:#fff;border:6px solid #141414;box-shadow:14px 14px 0 #141414;padding:34px 30px}
    p{font:600 34px/1.35 'IBM Plex Mono';color:#141414;margin-top:44px}
    .cta{margin-top:40px;font:700 32px 'IBM Plex Mono';color:#84CC16;background:#141414;display:inline-block;padding:20px 30px;box-shadow:10px 10px 0 rgba(0,0,0,.35)}
    .plug{margin-top:22px;font:600 22px 'IBM Plex Mono';color:#141414}`,
    capa: d => `<div class="kicker">${esc(d.kicker||'')}</div><h1>${hl(d.titulo)}</h1>${d.corpo?`<p>${br(d.corpo)}</p>`:''}`,
    conteudo: d => `<div class="kicker">${esc(d.kicker||'')}</div><h2>${hl(d.titulo)}</h2>${d.corpo?`<p>${br(d.corpo)}</p>`:''}`,
    cta: d => `<div class="kicker">${esc(d.kicker||'')}</div><h2>${hl(d.titulo)}</h2>${d.corpo?`<p>${br(d.corpo)}</p>`:''}${d.cta?`<div class="cta">${esc(d.cta)}</div>`:''}${d.plug?`<div class="plug">${esc(d.plug)}</div>`:''}`,
    // arquetipos com foto full-bleed (estilo do vencedor viral): imagem cobre a tela,
    // texto em overlay dentro da safe-zone do TikTok. Requer d.imgData (data URI, inlined no render).
    fotocss: `.ph{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;object-position:center 82%;transform:scale(1.12) translateY(70px);z-index:0}
    .fc-grad{position:absolute;inset:0;z-index:1;background:linear-gradient(180deg,rgba(0,0,0,.62) 0%,rgba(0,0,0,.12) 45%,rgba(0,0,0,.4) 100%)}
    .fc-h{position:absolute;top:340px;left:72px;right:150px;z-index:2;font:400 100px/1.04 'Anton';text-transform:uppercase;color:#fff;text-shadow:5px 5px 0 #141414}
    .fc-h .hl{color:#84CC16}
    .fc-sub{position:absolute;left:72px;right:150px;bottom:400px;z-index:2;font:600 38px/1.3 'IBM Plex Mono';color:#fff;background:rgba(20,20,20,.82);padding:22px 28px;text-align:center}
    /* foto (slides de valor): tenis inteiro e centralizado sobre fundo claro; numero a esquerda do nome; caixa de texto baixa e centralizada */
    .pv-bg{position:absolute;inset:0;z-index:0;background:#f2f0ea}
    .pv{position:absolute;top:450px;left:60px;width:960px;height:840px;object-fit:contain;z-index:1}
    .ph-head{position:absolute;top:320px;left:72px;right:150px;z-index:3;display:flex;gap:16px;align-items:stretch}
    .ph-num{font:700 34px 'IBM Plex Mono';color:#141414;background:#fff;border:5px solid #141414;padding:0 20px;display:flex;align-items:center;box-shadow:8px 8px 0 #141414}
    .ph-chip{font:400 54px/1 'Anton';text-transform:uppercase;color:#141414;background:#84CC16;border:6px solid #141414;box-shadow:10px 10px 0 #141414;padding:14px 24px;display:flex;align-items:center}
    .ph-cap{position:absolute;left:72px;right:150px;bottom:400px;z-index:3;font:600 38px/1.32 'IBM Plex Mono';color:#fff;background:rgba(20,20,20,.9);padding:24px 28px;text-align:center}
    .ph-cap .hl{color:#84CC16}`,
    fotocapa: d => `<img class="ph" src="${d.imgData||''}"><div class="fc-grad"></div><div class="fc-h">${hl(d.titulo)}</div>${d.corpo?`<div class="fc-sub">${br(d.corpo)}</div>`:''}`,
    foto: d => `<div class="pv-bg"></div><img class="pv" src="${d.imgData||''}"><div class="ph-head">${d.kicker?`<div class="ph-num">${esc(d.kicker)}</div>`:''}<div class="ph-chip">${esc(d.titulo)}</div></div>${d.corpo?`<div class="ph-cap">${br(d.corpo)}</div>`:''}`,
  },

  "claymorphism": {
    accent: "#8B5CF6",
    css: `.slide{background:#EAE2F8;padding:96px;justify-content:center;--accent:#8B5CF6}
    .card{background:#F3EEFC;border-radius:44px;padding:84px 70px;box-shadow:inset 0 4px 8px #ffffff,0 26px 50px #b9a8dd80}
    .kicker{font:800 28px 'Plus Jakarta Sans';color:#8B5CF6;text-transform:uppercase;letter-spacing:1px;margin-bottom:26px}
    h1{font:800 92px/1.02 'Nunito';color:#3b2c63}
    h2{font:800 74px/1.05 'Nunito';color:#3b2c63}
    p{font:400 34px/1.42 'Plus Jakarta Sans';color:#5a4b7d;margin-top:30px}
    .cta{margin-top:36px;font:800 32px 'Nunito';color:#fff;background:#8B5CF6;display:inline-block;padding:20px 32px;border-radius:22px;box-shadow:0 12px 22px #8b5cf655}
    .plug{margin-top:22px;font:700 22px 'Plus Jakarta Sans';color:#8B5CF6}`,
    capa: d => `<div class="card"><div class="kicker">${esc(d.kicker||'')}</div><h1>${hl(d.titulo)}</h1>${d.corpo?`<p>${br(d.corpo)}</p>`:''}</div>`,
    conteudo: d => `<div class="card"><div class="kicker">${esc(d.kicker||'')}</div><h2>${hl(d.titulo)}</h2>${d.corpo?`<p>${br(d.corpo)}</p>`:''}</div>`,
    cta: d => `<div class="card"><div class="kicker">${esc(d.kicker||'')}</div><h2>${hl(d.titulo)}</h2>${d.corpo?`<p>${br(d.corpo)}</p>`:''}${d.cta?`<div class="cta">${esc(d.cta)}</div>`:''}${d.plug?`<div class="plug">${esc(d.plug)}</div>`:''}</div>`,
  },

  "neo-newspaper": {
    accent: "#F84F2E",
    css: `.slide{background:#F5F0E8;padding:88px;justify-content:center;--accent:#F84F2E}
    .dateline{font:700 24px 'JetBrains Mono';color:#F84F2E;text-transform:uppercase;letter-spacing:1px;border-top:2px solid #141414;border-bottom:2px solid #141414;padding:14px 0;display:flex;justify-content:space-between}
    h1{font:900 116px/.98 'Playfair Display';color:#141414;margin:38px 0;text-align:center}
    h2{font:900 92px/1.0 'Playfair Display';color:#141414;margin:34px 0;text-align:center}
    p{font:400 33px/1.5 'Lato';color:#2a2a2a;column-count:2;column-gap:40px;text-align:justify}
    p:first-letter{font:900 88px 'Playfair Display';float:left;line-height:.7;margin:8px 10px 0 0;color:#F84F2E}
    .cta{margin-top:34px;font:700 30px 'JetBrains Mono';color:#fff;background:#141414;display:block;text-align:center;padding:18px 28px}
    .plug{margin-top:20px;font:400 24px 'Lato';color:#141414;text-align:center}`,
    capa: d => `<div class="dateline"><span>TÊNIS IDEAL</span><span>${esc(d.kicker||'')}</span></div><h1>${hl(d.titulo)}</h1>${d.corpo?`<p>${br(d.corpo)}</p>`:''}`,
    conteudo: d => `<div class="dateline"><span>TÊNIS IDEAL</span><span>${esc(d.kicker||'')}</span></div><h2>${hl(d.titulo)}</h2>${d.corpo?`<p>${br(d.corpo)}</p>`:''}`,
    cta: d => `<div class="dateline"><span>TÊNIS IDEAL</span><span>${esc(d.kicker||'')}</span></div><h2>${hl(d.titulo)}</h2>${d.corpo?`<p>${br(d.corpo)}</p>`:''}${d.cta?`<div class="cta">${esc(d.cta)}</div>`:''}${d.plug?`<div class="plug">${esc(d.plug)}</div>`:''}`,
  },

  "sticker-cutout": {
    accent: "#0058D4",
    css: `.slide{background:#0058D4;padding:90px;justify-content:center;gap:36px;background-image:radial-gradient(#ffffff18 2px,transparent 2px);background-size:34px 34px;--accent:#fff}
    .kicker{align-self:flex-start;font:800 26px 'Plus Jakarta Sans';background:#fff;color:#0058D4;border:5px solid #141414;box-shadow:6px 6px 0 #141414;padding:12px 20px}
    h1{font:800 100px/.98 'Sora';color:#fff;text-shadow:6px 6px 0 #141414}
    h2{font:800 80px/1.0 'Sora';color:#fff;text-shadow:5px 5px 0 #141414}
    p{font:600 34px/1.35 'Plus Jakarta Sans';color:#fff;background:#141414;padding:22px 28px;border-radius:16px;align-self:flex-start}
    .cta{font:800 32px 'Sora';color:#0058D4;background:#fff;border:5px solid #141414;box-shadow:6px 6px 0 #141414;display:inline-block;padding:18px 28px;align-self:flex-start}
    .plug{font:600 22px 'Plus Jakarta Sans';color:#fff;align-self:flex-start}`,
    capa: d => `<div class="kicker">${esc(d.kicker||'')}</div><h1>${hl(d.titulo)}</h1>${d.corpo?`<p>${br(d.corpo)}</p>`:''}`,
    conteudo: d => `<div class="kicker">${esc(d.kicker||'')}</div><h2>${hl(d.titulo)}</h2>${d.corpo?`<p>${br(d.corpo)}</p>`:''}`,
    cta: d => `<div class="kicker">${esc(d.kicker||'')}</div><h2>${hl(d.titulo)}</h2>${d.corpo?`<p>${br(d.corpo)}</p>`:''}${d.cta?`<div class="cta">${esc(d.cta)}</div>`:''}${d.plug?`<div class="plug">${esc(d.plug)}</div>`:''}`,
  },

  "terminal-mono": {
    accent: "#00FF66",
    css: `.slide{background:#0a0a0a;padding:80px;justify-content:center;background-image:repeating-linear-gradient(#ffffff08 0 1px,transparent 1px 40px);--accent:#00FF66}
    .kicker{font:400 26px 'IBM Plex Mono';color:#FFB000;margin-bottom:30px}
    h1{font:700 84px/1.05 'IBM Plex Mono';color:#00FF66}
    h1:before{content:'$ ';color:#666}
    h2{font:700 66px/1.1 'IBM Plex Mono';color:#00FF66}
    h2:before{content:'> ';color:#666}
    p{font:400 32px/1.5 'IBM Plex Mono';color:#d0d0d0;margin-top:34px;border-left:2px solid #00FF66;padding-left:26px}
    .cta{margin-top:36px;font:700 30px 'IBM Plex Mono';color:#0a0a0a;background:#00FF66;display:inline-block;padding:18px 28px}
    .plug{margin-top:22px;font:400 24px 'IBM Plex Mono';color:#FFB000}`,
    capa: d => `<div class="kicker">${esc(d.kicker||'# readme.md')}</div><h1>${hl(d.titulo)}</h1>${d.corpo?`<p>${br(d.corpo)}</p>`:''}`,
    conteudo: d => `<div class="kicker">${esc(d.kicker||'')}</div><h2>${hl(d.titulo)}</h2>${d.corpo?`<p>${br(d.corpo)}</p>`:''}`,
    cta: d => `<div class="kicker">${esc(d.kicker||'')}</div><h2>${hl(d.titulo)}</h2>${d.corpo?`<p>${br(d.corpo)}</p>`:''}${d.cta?`<div class="cta">${esc(d.cta)}</div>`:''}${d.plug?`<div class="plug">${esc(d.plug)}</div>`:''}`,
  },

  "flat-editorial-colorido": {
    accent: "#AF6DFF",
    css: `.slide{background:#AF6DFF;padding:90px;justify-content:center;--accent:#AF6DFF}
    .card{background:#FBF9F4;border-radius:32px;padding:84px 70px}
    .kicker{font:700 28px 'Plus Jakarta Sans';color:#AF6DFF;text-transform:uppercase;letter-spacing:2px;margin-bottom:26px}
    h1{font:800 96px/1.0 'Sora';color:#1c1c1c}
    h2{font:800 76px/1.04 'Sora';color:#1c1c1c}
    p{font:600 34px/1.4 'Plus Jakarta Sans';color:#444;margin-top:30px}
    .cta{margin-top:36px;font:800 32px 'Sora';color:#fff;background:#AF6DFF;display:inline-block;padding:20px 32px;border-radius:16px}
    .plug{margin-top:22px;font:600 22px 'Plus Jakarta Sans';color:#AF6DFF}`,
    capa: d => `<div class="card"><div class="kicker">${esc(d.kicker||'')}</div><h1>${hl(d.titulo)}</h1>${d.corpo?`<p>${br(d.corpo)}</p>`:''}</div>`,
    conteudo: d => `<div class="card"><div class="kicker">${esc(d.kicker||'')}</div><h2>${hl(d.titulo)}</h2>${d.corpo?`<p>${br(d.corpo)}</p>`:''}</div>`,
    cta: d => `<div class="card"><div class="kicker">${esc(d.kicker||'')}</div><h2>${hl(d.titulo)}</h2>${d.corpo?`<p>${br(d.corpo)}</p>`:''}${d.cta?`<div class="cta">${esc(d.cta)}</div>`:''}${d.plug?`<div class="plug">${esc(d.plug)}</div>`:''}</div>`,
  },
};

function render(style, archetype, data, formato) {
  const s = STYLES[style];
  if (!s) throw new Error("estilo desconhecido: " + style + " | disponiveis: " + Object.keys(STYLES).join(", "));
  const fn = s[archetype];
  if (typeof fn !== "function") throw new Error("arquetipo desconhecido: " + archetype + " (use capa|conteudo|cta|foto|fotocapa)");
  // arquetipos com foto precisam do bloco fotocss (se o estilo suportar).
  const isFoto = archetype === "foto" || archetype === "fotocapa";
  const css = isFoto && s.fotocss ? s.css + "\n" + s.fotocss : s.css;
  return page(css, fn(data), formato);
}

module.exports = { render, STYLES, listStyles: () => Object.keys(STYLES) };
