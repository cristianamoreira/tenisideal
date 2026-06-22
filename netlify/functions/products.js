const https = require('https');
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

const SHEET_ID = "1SrOeEOwQsR5BcNcVni0W20c5npazOn5iKHpIr3Zy42Y";

// Carregar credenciais (do env var ou arquivo local)
let creds;
if (process.env.GOOGLE_CREDENTIALS) {
  try {
    creds = JSON.parse(process.env.GOOGLE_CREDENTIALS);
  } catch (e) {
    console.error("Error parsing GOOGLE_CREDENTIALS env var:", e);
  }
}

if (!creds) {
  try {
    const credPath = path.join(__dirname, '../../credenciais.json');
    if (fs.existsSync(credPath)) {
      creds = JSON.parse(fs.readFileSync(credPath, 'utf8'));
    }
  } catch (e) {
    console.error("Error loading local credenciais.json:", e);
  }
}

function getAccessToken(clientEmail, privateKey) {
  return new Promise((resolve, reject) => {
    const header = JSON.stringify({ alg: "RS256", typ: "JWT" });
    const iat = Math.floor(Date.now() / 1000);
    const exp = iat + 3600;
    const claim = JSON.stringify({
      iss: clientEmail,
      scope: "https://www.googleapis.com/auth/spreadsheets.readonly",
      aud: "https://oauth2.googleapis.com/token",
      exp: exp,
      iat: iat
    });

    const base64url = (str) => Buffer.from(str).toString("base64").replace(/=/g, "").replace(/\+/g, "-").replace(/\//g, "_");
    const signatureInput = base64url(header) + "." + base64url(claim);
    const sign = crypto.createSign("RSA-SHA256");
    sign.update(signatureInput);
    const signature = base64url(sign.sign(privateKey));
    const jwt = signatureInput + "." + signature;

    const postData = `grant_type=urn:ietf:params:oauth:grant-type:jwt-bearer&assertion=${jwt}`;
    const req = https.request({
      hostname: "oauth2.googleapis.com",
      path: "/token",
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded"
      }
    }, (res) => {
      let data = "";
      res.on("data", chunk => data += chunk);
      res.on("end", () => {
        try {
          const parsed = JSON.parse(data);
          if (parsed.access_token) {
            resolve(parsed.access_token);
          } else {
            reject(new Error("Failed to get token: " + data));
          }
        } catch (err) {
          reject(err);
        }
      });
    });
    req.on("error", reject);
    req.write(postData);
    req.end();
  });
}

function parsePrice(str) {
  if (!str) return 0;
  const cleaned = str.replace(/[^\d,.-]/g, '').replace('.', '').replace(',', '.');
  const val = parseFloat(cleaned);
  return isNaN(val) ? 0 : val;
}

exports.handler = async function(event, context) {
  if (!creds) {
    return {
      statusCode: 500,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*'
      },
      body: JSON.stringify({ error: "Google credentials not configured" })
    };
  }

  try {
    const token = await getAccessToken(creds.client_email, creds.private_key);
    
    return new Promise((resolve) => {
      const url = `https://sheets.googleapis.com/v4/spreadsheets/${SHEET_ID}/values/Catálogo`;
      https.get(url, {
        headers: {
          "Authorization": `Bearer ${token}`
        }
      }, (res) => {
        let data = "";
        res.on("data", chunk => data += chunk);
        res.on("end", () => {
          try {
            const parsed = JSON.parse(data);
            if (!parsed.values) {
              resolve({
                statusCode: 200,
                headers: {
                  'Content-Type': 'application/json',
                  'Access-Control-Allow-Origin': '*'
                },
                body: JSON.stringify([])
              });
              return;
            }

            const rows = parsed.values;
            const products = [];
            
            // Loop data rows (rows[0] is the header)
            for (let i = 1; i < rows.length; i++) {
              const cols = rows[i];
              if (cols.length < 14) continue;

              // FILTRO EXCLUSÃO LÓGICA: Exibir apenas se ativo === "sim"
              const ativo = (cols[1] || '').toLowerCase().trim();
              if (ativo !== 'sim') continue;

              // Parsing per-store offers
              const offers = [];

              // Amazon (indices 14, 15, 16)
              if (cols[14] && cols[14] !== "" && cols[14] !== "-") {
                offers.push({
                  store: "Amazon",
                  link: cols[14],
                  price: parsePrice(cols[15]),
                  price_pix: parsePrice(cols[15]),
                  installments: cols[16] || ""
                });
              }

              // Loja Oficial (indices 17, 18, 19, 20)
              if (cols[17] && cols[17] !== "" && cols[17] !== "-") {
                offers.push({
                  store: "Loja Oficial",
                  link: cols[17],
                  price: parsePrice(cols[18]),
                  price_pix: parsePrice(cols[20] || cols[18]),
                  installments: cols[19] || ""
                });
              }

              // Netshoes (indices 21, 22, 23, 24)
              if (cols[21] && cols[21] !== "" && cols[21] !== "-") {
                offers.push({
                  store: "Netshoes",
                  link: cols[21],
                  price: parsePrice(cols[22]),
                  price_pix: parsePrice(cols[23] || cols[22]),
                  installments: cols[24] || ""
                });
              }

              // Determinar o menor preço listado para o campo 'price' global
              let minPrice = Infinity;
              let bestPriceFormatted = '';
              let cheapestOffer = null;
              offers.forEach(o => {
                const p = o.price_pix > 0 ? o.price_pix : o.price;
                if (p > 0 && p < minPrice) {
                  minPrice = p;
                  cheapestOffer = o;
                }
              });

              if (cheapestOffer) {
                if (cheapestOffer.store === "Amazon") {
                  bestPriceFormatted = cols[15] || "";
                } else if (cheapestOffer.store === "Loja Oficial") {
                  bestPriceFormatted = cols[20] || cols[18] || "";
                } else if (cheapestOffer.store === "Netshoes") {
                  bestPriceFormatted = cols[23] || cols[22] || "";
                }
                if (!bestPriceFormatted || bestPriceFormatted === "") {
                  bestPriceFormatted = `R$ ${minPrice.toFixed(2).replace('.', ',')}`;
                }
              }

              if (minPrice === Infinity) {
                minPrice = 0;
              }

              const product = {
                id: cols[0] || `prod_${i}`,
                sexo: (cols[5] || '').split('|'),
                brand: cols[2] || '',
                name: cols[3] || '',
                images: [(cols[6] || '')],
                emoji: cols[7] || '👟',
                tags: (cols[8] || '').split('|'),
                price: minPrice,
                price_formatted: bestPriceFormatted || (minPrice > 0 ? `R$ ${minPrice.toFixed(2).replace('.', ',')}` : ''),
                budget: cols[25] || '',
                levels: (cols[9] || '').split('|'),
                pisadas: (cols[10] || '').split('|'),
                terrenos: (cols[11] || '').split('|'),
                priors: (cols[12] || '').split('|'),
                reason: cols[13] || '',
                offers: offers
              };

              // Compatibilidade com o formato antigo de links de afiliados
              product.affiliate_links = {};
              const amazonOffer = offers.find(o => o.store === "Amazon");
              if (amazonOffer) {
                product.affiliate_links.amazon = { url: amazonOffer.link, price: amazonOffer.price };
              }
              const netshoesOffer = offers.find(o => o.store === "Netshoes");
              if (netshoesOffer) {
                product.affiliate_links.netshoes = { url: netshoesOffer.link, price: netshoesOffer.price };
              }
              const brandLower = (product.brand || "").toLowerCase();
              const brandOffer = offers.find(o => o.store.toLowerCase() === brandLower);
              if (brandOffer) {
                product.affiliate_links.oficial = { url: brandOffer.link, price: brandOffer.price };
              } else {
                const officialOffer = offers.find(o => o.store === "Loja Oficial");
                if (officialOffer) {
                  product.affiliate_links.oficial = { url: officialOffer.link, price: officialOffer.price };
                }
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
            resolve({
              statusCode: 500,
              headers: {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
              },
              body: JSON.stringify({ error: e.message })
            });
          }
        });
      });
    });
  } catch (err) {
    return {
      statusCode: 500,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*'
      },
      body: JSON.stringify({ error: err.message })
    };
  }
};
