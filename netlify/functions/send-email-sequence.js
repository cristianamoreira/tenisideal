/**
 * 📧 Função Serverless: Email Nurturing Sequence
 * 
 * Envia 4 emails automáticos para não-converters:
 * - Day 0: "Seu resultado está pronto!"
 * - Day 1: "Você deixou o tênis ideal para trás"
 * - Day 2: "10% OFF cupom especial"
 * - Day 3: "Apenas 3 unidades em estoque"
 */

const fetch = require('node-fetch');

const SENDGRID_API = 'https://api.sendgrid.com/v3/mail/send';
const SENDGRID_KEY = process.env.SENDGRID_API_KEY;
const SENDER_EMAIL = 'noreply@tenisideal.com.br';

// Sequência de emails
const EMAIL_SEQUENCE = {
  day0: {
    subject: '🎯 Seu Tênis Ideal Está Aqui! Veja a Recomendação',
    delay: 0,
    html: `
      <div style="max-width: 600px; margin: 0 auto; font-family: 'DM Sans', sans-serif; background: #0a0a0a; color: #fff; padding: 40px 20px;">
        <div style="border-bottom: 2px solid #c8ff00; padding-bottom: 20px; margin-bottom: 30px;">
          <h1 style="margin: 0; font-size: 24px; letter-spacing: 2px;">TENIS<span style="color: #c8ff00;">IDEAL</span></h1>
        </div>
        
        <h2 style="font-size: 20px; margin-bottom: 16px;">🎯 Seu Resultado Está Pronto!</h2>
        
        <p style="font-size: 16px; line-height: 1.6; margin-bottom: 20px;">
          Olá! 👟 Você respondeu nosso quiz e já temos a recomendação perfeita para você.
        </p>
        
        <p style="font-size: 16px; line-height: 1.6; margin-bottom: 30px;">
          O tênis que escolhemos é baseado em seu tipo de pisada, terreno favorito e orçamento. Clique no botão abaixo para ver sua recomendação e aproveitar os melhores preços:
        </p>
        
        <div style="text-align: center; margin: 40px 0;">
          <a href="https://tenisideal.com.br/#results" style="background: #c8ff00; color: #000; padding: 16px 40px; text-decoration: none; font-weight: bold; font-size: 16px; border-radius: 4px; display: inline-block; text-transform: uppercase;">VER MEU RESULTADO</a>
        </div>
        
        <p style="font-size: 14px; color: #888; margin-top: 30px;">
          Você tem acesso exclusivo a preços especiais em múltiplas lojas. Não perca!
        </p>
      </div>
    `
  },
  
  day1: {
    subject: '⏰ Você deixou o tênis ideal para trás... Ele ainda está aqui',
    delay: 86400000, // 24 horas
    html: `
      <div style="max-width: 600px; margin: 0 auto; font-family: 'DM Sans', sans-serif; background: #0a0a0a; color: #fff; padding: 40px 20px;">
        <div style="border-bottom: 2px solid #c8ff00; padding-bottom: 20px; margin-bottom: 30px;">
          <h1 style="margin: 0; font-size: 24px; letter-spacing: 2px;">TENIS<span style="color: #c8ff00;">IDEAL</span></h1>
        </div>
        
        <h2 style="font-size: 20px; margin-bottom: 16px;">⏰ Espera aí! Seu tênis ainda está esperando</h2>
        
        <p style="font-size: 16px; line-height: 1.6; margin-bottom: 20px;">
          Você respondeu nosso quiz e achou o tênis perfeito, mas não finalizou a compra ainda...
        </p>
        
        <p style="font-size: 16px; line-height: 1.6; margin-bottom: 30px;">
          Nós conseguimos os melhores preços em múltiplas lojas. Seu tênis pode estar com desconto <strong>AGORA</strong>. Não deixa passar!
        </p>
        
        <div style="text-align: center; margin: 40px 0;">
          <a href="https://tenisideal.com.br/#results" style="background: #c8ff00; color: #000; padding: 16px 40px; text-decoration: none; font-weight: bold; font-size: 16px; border-radius: 4px; display: inline-block; text-transform: uppercase;">VER PREÇOS AGORA</a>
        </div>
        
        <p style="font-size: 14px; color: #888; margin-top: 30px;">
          Amanhã você receberá um cupom especial. Aproveita!
        </p>
      </div>
    `
  },
  
  day2: {
    subject: '🎁 Cupom Exclusivo: 10% OFF em Seu Tênis Ideal',
    delay: 172800000, // 48 horas
    html: `
      <div style="max-width: 600px; margin: 0 auto; font-family: 'DM Sans', sans-serif; background: #0a0a0a; color: #fff; padding: 40px 20px;">
        <div style="border-bottom: 2px solid #c8ff00; padding-bottom: 20px; margin-bottom: 30px;">
          <h1 style="margin: 0; font-size: 24px; letter-spacing: 2px;">TENIS<span style="color: #c8ff00;">IDEAL</span></h1>
        </div>
        
        <div style="background: #c8ff00; color: #000; padding: 20px; border-radius: 8px; text-align: center; margin-bottom: 30px;">
          <h2 style="margin: 0; font-size: 28px; font-weight: bold;">10% OFF</h2>
          <p style="margin: 10px 0 0 0; font-size: 14px;">Cupom exclusivo só para você!</p>
        </div>
        
        <h2 style="font-size: 20px; margin-bottom: 16px;">🎁 Seu Cupom Chegou!</h2>
        
        <p style="font-size: 16px; line-height: 1.6; margin-bottom: 20px;">
          Como você não finalizou a compra, conseguimos um cupom especial de <strong>10% OFF</strong> para o seu tênis ideal.
        </p>
        
        <div style="background: rgba(200, 255, 0, 0.1); border: 2px solid #c8ff00; padding: 20px; border-radius: 8px; margin: 30px 0;">
          <p style="font-size: 12px; color: #888; margin: 0 0 10px 0;">CÓDIGO DO CUPOM:</p>
          <p style="font-size: 24px; font-weight: bold; color: #c8ff00; margin: 0; letter-spacing: 2px;">TENISIDEAL10</p>
        </div>
        
        <div style="text-align: center; margin: 30px 0;">
          <a href="https://tenisideal.com.br/#results" style="background: #c8ff00; color: #000; padding: 16px 40px; text-decoration: none; font-weight: bold; font-size: 16px; border-radius: 4px; display: inline-block; text-transform: uppercase;">COMPRAR COM DESCONTO</a>
        </div>
        
        <p style="font-size: 14px; color: #888; margin-top: 30px;">
          Cupom válido por 7 dias. Aproveita enquanto puder! 🏃
        </p>
      </div>
    `
  },
  
  day3: {
    subject: '⚠️ Urgente: Apenas 3 Unidades Restantes',
    delay: 259200000, // 72 horas
    html: `
      <div style="max-width: 600px; margin: 0 auto; font-family: 'DM Sans', sans-serif; background: #0a0a0a; color: #fff; padding: 40px 20px;">
        <div style="border-bottom: 2px solid #c8ff00; padding-bottom: 20px; margin-bottom: 30px;">
          <h1 style="margin: 0; font-size: 24px; letter-spacing: 2px;">TENIS<span style="color: #c8ff00;">IDEAL</span></h1>
        </div>
        
        <div style="background: #ff3b30; padding: 15px; border-radius: 4px; margin-bottom: 30px;">
          <h2 style="margin: 0; font-size: 18px;">⚠️ ESTOQUE BAIXÍSSIMO!</h2>
        </div>
        
        <h2 style="font-size: 20px; margin-bottom: 16px;">Apenas 3 Unidades Restantes em Estoque</h2>
        
        <p style="font-size: 16px; line-height: 1.6; margin-bottom: 20px;">
          Seu tênis ideal está saindo rapidinho do estoque. Temos apenas <strong>3 unidades</strong> restantes em nosso catálogo de fornecedores.
        </p>
        
        <p style="font-size: 16px; line-height: 1.6; margin-bottom: 30px; color: #ff3b30; font-weight: bold;">
          Se perder esse, pode ficar indisponível por semanas ou meses!
        </p>
        
        <div style="text-align: center; margin: 40px 0;">
          <a href="https://tenisideal.com.br/#results" style="background: #ff3b30; color: #fff; padding: 18px 40px; text-decoration: none; font-weight: bold; font-size: 16px; border-radius: 4px; display: inline-block; text-transform: uppercase;">GARANTIR AGORA</a>
        </div>
        
        <p style="font-size: 14px; color: #888; margin-top: 30px;">
          Seu cupom 10% OFF ainda está válido! Aproveita essa chance.
        </p>
      </div>
    `
  }
};

/**
 * Enviar email via SendGrid
 */
async function sendEmail(to, subject, html) {
  if (!SENDGRID_KEY) {
    console.error('❌ SENDGRID_API_KEY não configurada');
    return false;
  }

  try {
    const response = await fetch(SENDGRID_API, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${SENDGRID_KEY}`
      },
      body: JSON.stringify({
        personalizations: [{ to: [{ email: to }] }],
        from: { email: SENDER_EMAIL, name: 'Tenis Ideal' },
        subject: subject,
        content: [{ type: 'text/html', value: html }]
      })
    });

    const success = response.status === 202;
    console.log(`${success ? '✅' : '❌'} Email ${subject} enviado para ${to}`);
    return success;
  } catch (error) {
    console.error('❌ Erro ao enviar email:', error.message);
    return false;
  }
}

/**
 * Handler principal
 */
exports.handler = async (event) => {
  const body = JSON.parse(event.body || '{}');
  const { email, day = 0 } = body;

  if (!email) {
    return { statusCode: 400, body: JSON.stringify({ error: 'Email required' }) };
  }

  const template = EMAIL_SEQUENCE[`day${day}`];
  if (!template) {
    return { statusCode: 400, body: JSON.stringify({ error: 'Invalid day' }) };
  }

  const sent = await sendEmail(email, template.subject, template.html);

  return {
    statusCode: sent ? 200 : 500,
    body: JSON.stringify({
      success: sent,
      email: email,
      day: day,
      subject: template.subject
    })
  };
};
