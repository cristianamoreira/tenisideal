// TenisIdeal API — Pure Node.js Backend
const http = require('http');
const https = require('https');
const fs = require('fs');
const path = require('path');
const url = require('url');

const PORT = process.env.PORT || 3001;
const DB_PATH = path.join(__dirname, 'db.json');
const CSV_PATH = path.join(__dirname, 'tenisideal-planilha.csv');

// ─── CORS ────────────────────────────────────────────────────────────────────
const ALLOWED_ORIGINS = [
  'https://www.tenisideal.com.br',
  'https://tenisideal.com.br',
  'https://tenisideal.netlify.app',
  'http://localhost',
  'http://localhost:5500',
  'http://localhost:3000',
  'http://127.0.0.1:5500',
  'http://127.0.0.1:3000',
  'null'  // for file:// requests
];

function setCors(req, res) {
  const origin = req.headers.origin || '';
  if (ALLOWED_ORIGINS.includes(origin) || origin.startsWith('http://localhost')) {
    res.setHeader('Access-Control-Allow-Origin', origin);
  } else {
    res.setHeader('Access-Control-Allow-Origin', 'https://www.tenisideal.com.br');
  }
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
}

// ─── DATABASE ────────────────────────────────────────────────────────────────
let db = {
  products: [],
  offers: {},  // { productId: [{ store, url, price, scraped_at }] }
  last_import: null,
  last_scrape: null,
  sheets_id: process.env.SHEETS_ID || '',
  sheets_gid: process.env.SHEETS_GID || '0',
  cron_active: false,
  scraping_in_progress: false
};

function loadDB() {
  try {
    if (fs.existsSync(DB_PATH)) {
      const data = fs.readFileSync(DB_PATH, 'utf8');
      db = { ...db, ...JSON.parse(data) };
      console.log(`[DB] Loaded ${db.products.length} products`);
    }
  } catch (e) {
    console.error('[DB] Error loading:', e.message);
  }
}

function saveDB() {
  try {
    fs.writeFileSync(DB_PATH, JSON.stringify(db, null, 2));
  } catch (e) {
    console.error('[DB] Error saving:', e.message);
  }
}

// ─── CSV PARSING ─────────────────────────────────────────────────────────────
function parseCSVRow(row) {
  const cols = [];
  let cur = '', inQ = false;
  for (let i = 0; i < row.length; i++) {
    const c = row[i];
    if (c === '"') { inQ = !inQ; }
    else if (c === ',' && !inQ) { cols.push(cur.trim()); cur = ''; }
    else { cur += c; }
  }
  cols.push(cur.trim());
  return cols;
}

function parsePrice(str) {
  if (!str) return 0;
  const cleaned = str.replace(/[R$\s.]/g, '').replace(',', '.');
  const val = parseFloat(cleaned);
  return isNaN(val) ? 0 : val;
}

function splitPipe(str) {
  if (!str) return [];
  return str.split('|').map(s => s.trim()).filter(Boolean);
}

function parseCSVToProducts(csv) {
  const allRows = csv.split('\n');
  const headerCols = parseCSVRow(allRows[0]);

  // Build column map from header
  const colMap = {};
  headerCols.forEach((h, i) => {
    colMap[h.replace(/^#\s*/, '').trim().toLowerCase()] = i;
  });

  function findCol(partials) {
    for (const partial of partials) {
      const search = partial.toLowerCase();
      for (const key of Object.keys(colMap)) {
        if (key.includes(search)) return colMap[key];
      }
    }
    return -1;
  }

  const CI = {
    sexo: findCol(['masculino', 'feminino', 'sexo', 'gender']),
    brand: findCol(['marca', 'brand']),
    name: findCol(['nome do tênis', 'name', 'nome']),
    img: findCol(['url da imagem', 'img', 'imagem']),
    emoji: findCol(['emoji']),
    tags: findCol(['tag1', 'tags']),
    price: findCol(['r$ 000', 'price', 'preço', 'preco']),
    budget: findCol(['price_range', 'ate300', 'budget', 'orçamento', 'orcamento']),
    levels: findCol(['iniciante|intermediario', 'levels', 'nível', 'nivel']),
    pisadas: findCol(['neutra|pronada', 'pisadas', 'pronation', 'pisada']),
    terrenos: findCol(['asfalto|trilha', 'terrenos', 'terrain', 'terreno']),
    priors: findCol(['amortecimento|leveza', 'priors', 'prioridade']),
    reason: findCol(['motivo', 'reason', 'descrição', 'descricao']),
    amazon_link: findCol(['link afiliado amazon', 'link_amazon', 'amazon']),
    popular: findCol(['popular', 'best_seller']),
    awin_link: findCol(['link_awin', 'awin', 'afiliado mizuno', 'oficial', 'link loja']),
    netshoes_link: findCol(['netshoes', 'link_netshoes']),
  };

  console.log('[CSV] Column indices:', JSON.stringify(CI));

  function gc(cols, key) {
    const idx = CI[key];
    if (idx === undefined || idx < 0 || idx >= cols.length) return '';
    return (cols[idx] || '').replace(/\r/g, '').trim();
  }

  const rows = allRows.slice(1).filter(r => r.trim());
  const products = [];

  rows.forEach((row, i) => {
    const cols = parseCSVRow(row);
    const id = `prod_${i}`;
    const priceStr = gc(cols, 'price');
    const price = parsePrice(priceStr);
    const amazonLink = gc(cols, 'amazon_link');
    const awinLink = gc(cols, 'awin_link');
    const netshoesLink = gc(cols, 'netshoes_link');

    const product = {
      id,
      sexo: splitPipe(gc(cols, 'sexo')),
      brand: gc(cols, 'brand'),
      name: gc(cols, 'name'),
      image_url: gc(cols, 'img'),
      emoji: gc(cols, 'emoji') || '👟',
      tags: splitPipe(gc(cols, 'tags')),
      price,
      price_formatted: priceStr,
      budget: gc(cols, 'budget'),
      levels: splitPipe(gc(cols, 'levels')),
      pisadas: splitPipe(gc(cols, 'pisadas')),
      terrenos: splitPipe(gc(cols, 'terrenos')),
      priors: splitPipe(gc(cols, 'priors')),
      reason: gc(cols, 'reason'),
      popular: gc(cols, 'popular').toLowerCase() === 'sim' || gc(cols, 'popular').toLowerCase() === 'true',
      stores: {}
    };

    // Build offers from links
    if (amazonLink && amazonLink !== '-') {
      product.stores.amazon = { url: amazonLink, price, scraped_price: null };
    }
    if (awinLink && awinLink !== '-') {
      product.stores.oficial = { url: awinLink, price: 0, scraped_price: null };
    }
    if (netshoesLink && netshoesLink !== '-') {
      product.stores.netshoes = { url: netshoesLink, price: 0, scraped_price: null };
    }

    products.push(product);
  });

  return products;
}

// ─── GOOGLE SHEETS IMPORT ────────────────────────────────────────────────────
function fetchSheets(sheetsId, gid) {
  return new Promise((resolve, reject) => {
    const sheetsUrl = `https://docs.google.com/spreadsheets/d/e/${sheetsId}/pub?gid=${gid || '0'}&single=true&output=csv`;
    console.log(`[Sheets] Fetching: ${sheetsUrl}`);

    https.get(sheetsUrl, { headers: { 'User-Agent': 'TenisIdeal-Bot/1.0' } }, (res) => {
      if (res.statusCode === 301 || res.statusCode === 302) {
        // Follow redirect
        https.get(res.headers.location, (res2) => {
          let data = '';
          res2.on('data', chunk => data += chunk);
          res2.on('end', () => resolve(data));
          res2.on('error', reject);
        }).on('error', reject);
        return;
      }
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        if (res.statusCode !== 200) {
          reject(new Error(`HTTP ${res.statusCode}`));
        } else {
          resolve(data);
        }
      });
      res.on('error', reject);
    }).on('error', reject);
  });
}

async function importFromSheets(sheetsId, gid) {
  const csv = await fetchSheets(sheetsId, gid);
  const products = parseCSVToProducts(csv);
  db.products = products;
  db.last_import = new Date().toISOString();
  if (sheetsId) db.sheets_id = sheetsId;
  if (gid) db.sheets_gid = gid;
  saveDB();
  console.log(`[Import] ${products.length} products imported from Sheets`);
  return products.length;
}

// ─── PRICE SCRAPING ──────────────────────────────────────────────────────────
function fetchPage(pageUrl) {
  return new Promise((resolve, reject) => {
    const mod = pageUrl.startsWith('https') ? https : http;
    const options = {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml',
        'Accept-Language': 'pt-BR,pt;q=0.9'
      },
      timeout: 15000
    };

    mod.get(pageUrl, options, (res) => {
      // Follow up to 5 redirects
      if ((res.statusCode === 301 || res.statusCode === 302) && res.headers.location) {
        fetchPage(res.headers.location).then(resolve).catch(reject);
        return;
      }
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => resolve(data));
      res.on('error', reject);
    }).on('error', reject);
  });
}

function extractPrice(html) {
  // Try JSON-LD priceAmount
  const jsonLdMatch = html.match(/"priceAmount"\s*:\s*"?([\d.,]+)"?/);
  if (jsonLdMatch) {
    const p = parsePrice(jsonLdMatch[1]);
    if (p > 0) return p;
  }

  // Try price patterns  R$ X.XXX,XX
  const brPriceMatch = html.match(/R\$\s*([\d.]+,\d{2})/);
  if (brPriceMatch) {
    const p = parsePrice(brPriceMatch[1]);
    if (p > 0) return p;
  }

  // Try data attribute patterns
  const dataMatch = html.match(/data-price="([\d.,]+)"/);
  if (dataMatch) {
    const p = parsePrice(dataMatch[1]);
    if (p > 0) return p;
  }

  return null;
}

async function scrapeProduct(product) {
  const results = {};
  for (const [store, info] of Object.entries(product.stores || {})) {
    if (!info.url || info.url === '-') continue;
    try {
      console.log(`[Scrape] ${product.name} @ ${store}: ${info.url}`);
      const html = await fetchPage(info.url);
      const price = extractPrice(html);
      if (price && price > 0) {
        results[store] = { price, scraped_at: new Date().toISOString() };
        info.scraped_price = price;
        console.log(`[Scrape] ✓ ${product.name} @ ${store}: R$${price.toFixed(2)}`);
      } else {
        console.log(`[Scrape] ✗ ${product.name} @ ${store}: price not found`);
      }
    } catch (e) {
      console.log(`[Scrape] ✗ ${product.name} @ ${store}: ${e.message}`);
    }
    // Delay between requests to avoid rate limiting
    await new Promise(r => setTimeout(r, 2000));
  }
  return results;
}

async function scrapeAll() {
  if (db.scraping_in_progress) {
    console.log('[Scrape] Already in progress, skipping');
    return;
  }
  db.scraping_in_progress = true;
  saveDB();

  console.log(`[Scrape] Starting full scrape of ${db.products.length} products...`);
  let scraped = 0;
  for (const product of db.products) {
    try {
      const results = await scrapeProduct(product);
      if (Object.keys(results).length > 0) scraped++;
    } catch (e) {
      console.error(`[Scrape] Error on ${product.name}:`, e.message);
    }
  }

  db.last_scrape = new Date().toISOString();
  db.scraping_in_progress = false;
  saveDB();
  console.log(`[Scrape] Done. ${scraped}/${db.products.length} products scraped.`);
}

// ─── CRON ────────────────────────────────────────────────────────────────────
let cronInterval = null;

function startCron() {
  if (cronInterval) return;
  db.cron_active = true;
  saveDB();

  // Run every 24 hours
  cronInterval = setInterval(async () => {
    console.log('[Cron] Daily job starting...');
    try {
      if (db.sheets_id) {
        await importFromSheets(db.sheets_id, db.sheets_gid);
      }
      await scrapeAll();
    } catch (e) {
      console.error('[Cron] Error:', e.message);
    }
  }, 24 * 60 * 60 * 1000);

  console.log('[Cron] Started (every 24h)');
}

function stopCron() {
  if (cronInterval) {
    clearInterval(cronInterval);
    cronInterval = null;
  }
  db.cron_active = false;
  saveDB();
  console.log('[Cron] Stopped');
}

// ─── HELPERS ─────────────────────────────────────────────────────────────────
function json(res, data, status = 200) {
  res.writeHead(status, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify(data));
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    let body = '';
    req.on('data', chunk => body += chunk);
    req.on('end', () => {
      try {
        resolve(body ? JSON.parse(body) : {});
      } catch (e) {
        resolve({});
      }
    });
    req.on('error', reject);
  });
}

function getBestOffer(product) {
  const offers = [];
  for (const [store, info] of Object.entries(product.stores || {})) {
    if (!info.url || info.url === '-') continue;
    const price = info.scraped_price || info.price || 0;
    offers.push({
      store,
      url: info.url,
      price,
      scraped_price: info.scraped_price,
      original_price: info.price
    });
  }
  offers.sort((a, b) => {
    if (!a.price || a.price <= 0) return 1;
    if (!b.price || b.price <= 0) return -1;
    return a.price - b.price;
  });
  return { best: offers[0] || null, all: offers };
}

// ─── SERVER ──────────────────────────────────────────────────────────────────
const server = http.createServer(async (req, res) => {
  setCors(req, res);

  // Handle preflight
  if (req.method === 'OPTIONS') {
    res.writeHead(204);
    res.end();
    return;
  }

  const parsed = url.parse(req.url, true);
  const pathname = parsed.pathname;

  try {
    // ── Health ──
    if (pathname === '/health') {
      return json(res, { status: 'ok', uptime: process.uptime() });
    }

    // ── Status ──
    if (pathname === '/api/status') {
      return json(res, {
        products: db.products.length,
        last_import: db.last_import,
        last_scrape: db.last_scrape,
        sheets_id: db.sheets_id ? '***' + db.sheets_id.slice(-8) : null,
        cron_active: db.cron_active,
        scraping_in_progress: db.scraping_in_progress
      });
    }

    // ── GET Products ──
    if (pathname === '/api/products' && req.method === 'GET') {
      const products = db.products.map(p => {
        const { best, all } = getBestOffer(p);
        return {
          ...p,
          best_offer: best,
          offers_count: all.length
        };
      });
      return json(res, { products, total: products.length });
    }

    // ── GET Product by ID ──
    const productMatch = pathname.match(/^\/api\/products\/(.+)$/);
    if (productMatch && req.method === 'GET') {
      const id = productMatch[1];
      const product = db.products.find(p => p.id === id);
      if (!product) return json(res, { error: 'Product not found' }, 404);
      const { best, all } = getBestOffer(product);
      return json(res, { ...product, best_offer: best, all_offers: all });
    }

    // ── Import CSV (local file fallback) ──
    if (pathname === '/api/import' && req.method === 'POST') {
      if (!fs.existsSync(CSV_PATH)) {
        return json(res, { error: 'CSV file not found' }, 404);
      }
      const csv = fs.readFileSync(CSV_PATH, 'utf8');
      db.products = parseCSVToProducts(csv);
      db.last_import = new Date().toISOString();
      saveDB();
      return json(res, { imported: db.products.length, source: 'local_csv' });
    }

    // ── Import from Google Sheets ──
    if (pathname === '/api/import/sheets' && req.method === 'POST') {
      const body = await readBody(req);
      const sheetsId = body.sheets_id || db.sheets_id;
      const gid = body.gid || db.sheets_gid || '0';
      if (!sheetsId) {
        return json(res, { error: 'sheets_id is required' }, 400);
      }
      try {
        const count = await importFromSheets(sheetsId, gid);
        return json(res, { imported: count, source: 'google_sheets' });
      } catch (e) {
        return json(res, { error: e.message }, 500);
      }
    }

    // ── Scrape all ──
    if (pathname === '/api/scrape' && req.method === 'POST') {
      if (db.products.length === 0) {
        return json(res, { error: 'No products to scrape. Import first.' }, 400);
      }
      // Run in background
      scrapeAll();
      return json(res, { message: 'Scraping started in background', products: db.products.length });
    }

    // ── Scrape single product ──
    const scrapeMatch = pathname.match(/^\/api\/scrape\/(.+)$/);
    if (scrapeMatch && req.method === 'POST') {
      const id = scrapeMatch[1];
      const product = db.products.find(p => p.id === id);
      if (!product) return json(res, { error: 'Product not found' }, 404);
      const results = await scrapeProduct(product);
      saveDB();
      return json(res, { product: product.name, results });
    }

    // ── Cron start ──
    if (pathname === '/api/cron/start' && req.method === 'POST') {
      startCron();
      return json(res, { cron: 'started', interval: '24h' });
    }

    // ── Cron stop ──
    if (pathname === '/api/cron/stop' && req.method === 'POST') {
      stopCron();
      return json(res, { cron: 'stopped' });
    }

    // ── 404 ──
    json(res, { error: 'Not found' }, 404);

  } catch (err) {
    console.error('[Server] Error:', err);
    json(res, { error: 'Internal server error' }, 500);
  }
});

// ─── STARTUP ─────────────────────────────────────────────────────────────────
loadDB();

// Auto-import from Sheets on startup if we have an ID and no products
if (db.sheets_id && db.products.length === 0) {
  console.log('[Startup] Auto-importing from Sheets...');
  importFromSheets(db.sheets_id, db.sheets_gid).catch(e => {
    console.error('[Startup] Auto-import failed:', e.message);
    // Try local CSV fallback
    if (fs.existsSync(CSV_PATH)) {
      console.log('[Startup] Falling back to local CSV...');
      const csv = fs.readFileSync(CSV_PATH, 'utf8');
      db.products = parseCSVToProducts(csv);
      db.last_import = new Date().toISOString();
      saveDB();
      console.log(`[Startup] Loaded ${db.products.length} products from local CSV`);
    }
  });
}

// Resume cron if it was active
if (db.cron_active) {
  startCron();
}

server.listen(PORT, () => {
  console.log(`\n🏃 TenisIdeal API running on port ${PORT}`);
  console.log(`   Health:   http://localhost:${PORT}/health`);
  console.log(`   Status:   http://localhost:${PORT}/api/status`);
  console.log(`   Products: http://localhost:${PORT}/api/products\n`);
});
