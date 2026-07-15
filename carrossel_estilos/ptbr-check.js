// ptbr-check.js — verificador de ortografia/acentuacao PT-BR para os textos dos slides.
// Roda automaticamente no render.js ANTES de gerar as imagens.
//
// Duas listas:
//  - AUTO: a forma sem acento NAO e palavra valida do portugues -> corrige sozinho.
//  - AMBIG: a forma sem acento TAMBEM e palavra valida (e/é, a/à, esta/está) -> so ALERTA,
//           nunca corrige sozinho (precisa de olho humano pra decidir pelo contexto).

// mapa base em minusculas (a funcao preserva a capitalizacao original da palavra)
const AUTO = {
  voce: "você", voces: "vocês", tenis: "tênis",
  ultimo: "último", ultima: "última", ultimos: "últimos", ultimas: "últimas",
  numero: "número", numeros: "números",
  rapido: "rápido", rapida: "rápida", rapidos: "rápidos", rapidas: "rápidas",
  nao: "não", sao: "são", estao: "estão", entao: "então", nada: "nada",
  tres: "três", alem: "além", apos: "após",
  proximo: "próximo", proxima: "próxima",
  tambem: "também", porem: "porém",
  ninguem: "ninguém", alguem: "alguém",
  saude: "saúde", ciencia: "ciência", experiencia: "experiência",
  distancia: "distância", nivel: "nível", inicio: "início",
  historia: "história", musica: "música", facil: "fácil", dificil: "difícil",
  chao: "chão", coracao: "coração", versao: "versão", opiniao: "opinião",
  duvida: "dúvida", saida: "saída", pes: "pés", mes: "mês", meses: "meses",
  otimo: "ótimo", pessimo: "péssimo", unico: "único", unica: "única",
  maximo: "máximo", minimo: "mínimo", basico: "básico",
  periodo: "período", serie: "série", area: "área", memoria: "memória",
  codigo: "código", camera: "câmera", sera: "será", ate: "até", so: "só",
  ja: "já", la: "lá", ca: "cá", pra: "pra",
};

// imperativo: a marca fala no "voce" (imperativo formal). Formas de "tu" (descobre, olha...)
// muitas vezes tambem sao indicativo valido -> so ALERTA a forma "voce" sugerida (nao troca sozinho).
const IMPER = {
  descobre: "descubra", escolhe: "escolha", aprende: "aprenda", confere: "confira",
  clica: "clique", salva: "salve", comenta: "comente", segue: "siga", pega: "pegue",
  olha: "olhe", experimenta: "experimente", compara: "compare", baixa: "baixe",
  acessa: "acesse", ativa: "ative", comeca: "comece", tenta: "tente", evita: "evite",
  corre: "corra", vem: "venha", entra: "entre", aproveita: "aproveite", imagina: "imagine",
};

// homografos: sem acento tambem e valido -> so avisa
const AMBIG = {
  e: "é", esta: "está", estas: "estás", as: "às", a: "à",
  pais: "país", publico: "público", pratico: "prático",
  media: "média", pagina: "página", analise: "análise",
  secretaria: "secretária", duvida: "dúvida", sabia: "sábia",
};

function keepCase(orig, repl) {
  if (orig[0] === orig[0].toUpperCase()) return repl[0].toUpperCase() + repl.slice(1);
  return repl;
}

// corrige AUTO e coleta alertas AMBIG. Retorna {text, changes:[{from,to}], warnings:[{word,sug}]}
function fixPtBr(text = "") {
  const changes = [];
  const warnings = [];
  // \p{L} pra bater letras acentuadas tambem; processa token a token
  const out = String(text).replace(/[A-Za-zÀ-ÿ]+/g, (w) => {
    const low = w.toLowerCase();
    if (AUTO[low]) {
      const to = keepCase(w, AUTO[low]);
      if (to !== w) changes.push({ from: w, to });
      return to;
    }
    if (AMBIG[low]) warnings.push({ word: w, sug: keepCase(w, AMBIG[low]), kind: "acento" });
    if (IMPER[low]) warnings.push({ word: w, sug: keepCase(w, IMPER[low]), kind: "imperativo" });
    return w;
  });
  return { text: out, changes, warnings };
}

// aplica em todos os campos de texto de um slide (muta e retorna relatorio)
const FIELDS = ["kicker", "titulo", "corpo", "cta", "plug"];
function fixSlide(slide, idx) {
  const report = { idx, changes: [], warnings: [] };
  for (const f of FIELDS) {
    if (typeof slide[f] !== "string") continue;
    const r = fixPtBr(slide[f]);
    slide[f] = r.text;
    r.changes.forEach((c) => report.changes.push({ field: f, ...c }));
    r.warnings.forEach((w) => report.warnings.push({ field: f, ...w }));
  }
  return report;
}

module.exports = { fixPtBr, fixSlide };
