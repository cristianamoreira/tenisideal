const https = require('https');

// URL pública de exportação da sua planilha
const SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/1SrOeEOwQsR5BcNcVni0W20c5npazOn5iKHpIr3Zy42Y/export?format=csv&gid=507148502";

// Helper para ler CSV (simplificado)
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
  const cleaned = str.replace(/[^\d,.-]/g, '').replace('.', '').replace(',', '.');
  const val = parseFloat(cleaned);
  return isNaN(val) ? 0 : val;
}

exports.handler = async function(event, context) {
  return new Promise((resolve) => {
    https.get(SHEET_CSV_URL, (res) => {
      // Seguir redirecionamento do Google
      if (res.statusCode === 301 || res.statusCode === 302 || res.statusCode === 307) {
        https.get(res.headers.location, processResponse).on('error', handleError);
      } else {
        processResponse(res);
      }

      function processResponse(response) {
        let data = '';
        response.on('data', chunk => data += chunk);
        response.on('end', () => {
          try {
            const rows = data.split('\n');
            const products = [];
            
            // Pula o cabeçalho
            for (let i = 1; i < rows.length; i++) {
              if (!rows[i].trim()) continue;
              const cols = parseCSVRow(rows[i]);
              if (cols.length < 13) continue;

              const priceStr = cols[6] || '';
              const product = {
                id: `prod_${i}`,
                sexo: (cols[0] || '').split('|'),
                brand: cols[1] || '',
                name: cols[2] || '',
                images: [(cols[3] || '')],
                emoji: cols[4] || '👟',
                tags: (cols[5] || '').split('|'),
                price: parsePrice(priceStr),
                price_formatted: priceStr,
                budget: cols[7] || '',
                levels: (cols[8] || '').split('|'),
                pisadas: (cols[9] || '').split('|'),
                terrenos: (cols[10] || '').split('|'),
                priors: (cols[11] || '').split('|'),
                reason: cols[12] || '',
                amazon_link: cols[13] || '',
                popular: (cols[14] || '').toLowerCase() === 'sim',
                awin_link: cols[15] || '',
                netshoes_link: cols[16] || ''
              };

              // Compatibilidade com o formato antigo de links de afiliados
              product.affiliate_links = {};
              if (product.amazon_link && product.amazon_link !== '-') {
                  product.affiliate_links.amazon = { url: product.amazon_link, price: product.price };
              }
              if (product.awin_link && product.awin_link !== '-') {
                  product.affiliate_links.oficial = { url: product.awin_link, price: product.price }; // Assumindo mesmo preco
              }
              if (product.netshoes_link && product.netshoes_link !== '-') {
                  product.affiliate_links.netshoes = { url: product.netshoes_link, price: product.price };
              }

              products.push(product);
            }

            resolve({
              statusCode: 200,
              headers: {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
              },
              body: JSON.stringify(products)
            });
          } catch (e) {
            handleError(e);
          }
        });
      }

      function handleError(e) {
        resolve({
          statusCode: 500,
          body: JSON.stringify({ error: e.message })
        });
      }
    }).on('error', (e) => {
      resolve({
        statusCode: 500,
        body: JSON.stringify({ error: e.message })
      });
    });
  });
};
