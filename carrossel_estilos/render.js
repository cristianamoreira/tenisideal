// carrossel-estilos — engine. Renderiza um roteiro em PNGs 1080x1440 (@2x) num dos 10 estilos.
// Uso: node render.js job.json
// job.json:
// {
//   "estilo": "brutalism",
//   "outDir": "saida",
//   "slides": [
//     { "type": "capa",     "kicker": "OPINIAO", "titulo": "Prompt nao e skill.", "corpo": "..." },
//     { "type": "conteudo", "kicker": "01", "titulo": "...", "corpo": "..." },
//     { "type": "cta",      "titulo": "...", "cta": "linkna.bio", "plug": "Formacao X" }
//   ]
// }
const { chromium } = require("playwright");
const path = require("path");
const fs = require("fs");
const { render, listStyles } = require("./templates.js");
const { fixSlide } = require("./ptbr-check.js");

const W = 1080;

(async () => {
  const jobPath = process.argv[2];
  if (!jobPath) { console.error("uso: node render.js job.json"); process.exit(1); }
  const base = path.dirname(path.resolve(jobPath));
  const job = JSON.parse(fs.readFileSync(jobPath, "utf8"));
  const estilo = job.estilo;
  if (!listStyles().includes(estilo)) {
    console.error("estilo invalido: " + estilo + "\ndisponiveis:\n  " + listStyles().join("\n  "));
    process.exit(1);
  }
  // formato: "tiktok" -> 1080x1920 (9:16); default -> 1080x1440 (4:5 carrossel)
  const formato = job.formato === "tiktok" ? "tiktok" : "carrossel";
  const H = formato === "tiktok" ? 1920 : 1440;
  const outDir = path.resolve(base, job.outDir || "saida");
  fs.mkdirSync(outDir, { recursive: true });

  // Local (Mac): usa o Chrome do sistema via channel. No GitHub Actions: usa o
  // binário instalado pelo setup-chrome, cujo caminho vem em CHROME_PATH.
  const exe = process.env.CHROME_PATH || "";
  const browser = await chromium.launch(exe ? { executablePath: exe } : { channel: "chrome" });
  const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 2 });

  const MIME = { ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp" };
  const inlineImg = (rel) => {
    const p = path.resolve(base, rel);
    const ext = path.extname(p).toLowerCase();
    const b64 = fs.readFileSync(p).toString("base64");
    return "data:" + (MIME[ext] || "image/jpeg") + ";base64," + b64;
  };

  // === verificacao de ortografia PT-BR (roda ANTES de renderizar) ===
  const allWarnings = [];
  job.slides.forEach((slide, i) => {
    const rep = fixSlide(slide, i + 1);
    if (rep.changes.length) {
      console.log("[ptbr] slide " + (i + 1) + " corrigido: " +
        rep.changes.map((c) => c.from + " -> " + c.to).join(", "));
    }
    rep.warnings.forEach((w) => allWarnings.push({ n: i + 1, ...w }));
  });
  if (allWarnings.length) {
    console.log("\n[ptbr] ⚠ REVISAR MANUALMENTE (ambiguos, o lint nao decide):");
    allWarnings.forEach((w) =>
      console.log("  slide " + w.n + " campo " + w.field + " [" + (w.kind || "?") + "]: \"" + w.word + "\" (seria \"" + w.sug + "\"?)"));
    console.log("");
  }

  let n = 0;
  for (const slide of job.slides) {
    n++;
    if (slide.img && !slide.imgData) slide.imgData = inlineImg(slide.img);
    const html = render(estilo, slide.type, slide, formato);
    await page.setContent(html, { waitUntil: "networkidle" });
    await page.evaluate(() => document.fonts.ready);
    await page.waitForTimeout(300);
    const out = path.join(outDir, "slide-" + String(n).padStart(2, "0") + ".png");
    await (await page.$("#s")).screenshot({ path: out });
    console.log("ok", out);
  }
  await browser.close();
  console.log("\n" + n + " slides (" + estilo + ", " + formato + " " + W + "x" + H + " @2x) em " + outDir);
})();
