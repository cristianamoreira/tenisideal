// Função serverless do Vercel — adiciona um contato no Brevo com segurança.
// A chave fica no servidor (env var BREVO_API_KEY), nunca exposta no site.
export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  let body = req.body;
  if (typeof body === 'string') {
    try { body = JSON.parse(body); } catch (e) { body = {}; }
  }
  const { email, tenis, link } = body || {};

  if (!email || typeof email !== 'string' || email.indexOf('@') < 0) {
    return res.status(400).json({ error: 'email inválido' });
  }

  const key = process.env.BREVO_API_KEY;
  if (!key) {
    return res.status(500).json({ error: 'BREVO_API_KEY não configurada no Vercel' });
  }

  try {
    const r = await fetch('https://api.brevo.com/v3/contacts', {
      method: 'POST',
      headers: {
        'api-key': key,
        'Content-Type': 'application/json',
        'accept': 'application/json',
      },
      body: JSON.stringify({
        email: email.trim(),
        listIds: [3], // lista de assinantes do quiz no Brevo
        updateEnabled: true,
        attributes: {
          ORIGEM: 'Quiz Tenisideal',
          TENIS_RECOMENDADO: tenis || '',
          LINK_TENIS: link || '',
        },
      }),
    });

    // 201 (criado) ou 204 (atualizado) = sucesso
    if (r.ok || r.status === 204) {
      return res.status(200).json({ ok: true });
    }
    const txt = await r.text();
    return res.status(502).json({ error: 'brevo', detail: txt.slice(0, 200) });
  } catch (e) {
    return res.status(500).json({ error: String(e) });
  }
}
