/**
 * Função Serverless: Monitora métricas do Google Analytics
 * Envia email quando atingir metas (hit targets)
 *
 * Configuração necessária:
 * - Variáveis de ambiente no Netlify:
 *   SENDGRID_API_KEY (para enviar email)
 *   GA_PROPERTY_ID (seu Property ID do GA4)
 *   RECIPIENT_EMAIL (seu email)
 */

const fetch = require('node-fetch');

// Metas (Hit Targets)
const TARGETS = {
  QUIZ_STARTS: 15,        // Quando atingir 15 quiz starts
  CLICK_RATE: 30,         // Quando atingir 30% de clique
  CONVERSIONS: 1,         // Quando atingir 1ª conversão
  MONTHLY_REVENUE: 500    // Quando atingir R$ 500
};

// Rastrear quais notificações já foram enviadas (em memória)
let notificationsSent = {
  quizStarts: false,
  clickRate: false,
  conversions: false,
  revenue: false
};

async function sendEmail(subject, message) {
  if (!process.env.SENDGRID_API_KEY || !process.env.RECIPIENT_EMAIL) {
    console.log('⚠️ SendGrid não configurado. Email não enviado.');
    console.log(`Assunto: ${subject}`);
    console.log(`Mensagem: ${message}`);
    return false;
  }

  try {
    const response = await fetch('https://api.sendgrid.com/v3/mail/send', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${process.env.SENDGRID_API_KEY}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        personalizations: [{
          to: [{ email: process.env.RECIPIENT_EMAIL }]
        }],
        from: { email: 'noreply@tenisideal.com.br', name: 'Tenis Ideal' },
        subject: subject,
        content: [{
          type: 'text/html',
          value: `
            <h2>${subject}</h2>
            <p>${message}</p>
            <hr>
            <p><small>Essa é uma notificação automática do seu quiz de recomendação de tênis.</small></p>
          `
        }]
      })
    });

    if (response.ok) {
      console.log('✅ Email enviado com sucesso');
      return true;
    } else {
      console.error('❌ Erro ao enviar email:', response.status);
      return false;
    }
  } catch (error) {
    console.error('❌ Erro na função de email:', error);
    return false;
  }
}

async function checkMetrics() {
  try {
    // Simular métricas (em produção, viria do Google Analytics API)
    // TODO: Integrar com Google Analytics API
    const metrics = {
      quizStarts: parseInt(localStorage.getItem('quizStartsToday') || '0'),
      totalClicks: parseInt(localStorage.getItem('clicksToday') || '0'),
      totalVisitors: parseInt(localStorage.getItem('visitorsToday') || '0'),
      conversions: parseInt(localStorage.getItem('conversionsToday') || '0'),
      revenue: parseFloat(localStorage.getItem('revenueToday') || '0')
    };

    // Calcular taxa de clique
    const clickRate = metrics.totalVisitors > 0
      ? Math.round((metrics.totalClicks / metrics.totalVisitors) * 100)
      : 0;

    // Meta 1: Quiz Starts
    if (metrics.quizStarts >= TARGETS.QUIZ_STARTS && !notificationsSent.quizStarts) {
      await sendEmail(
        `🎉 Meta Atingida: ${metrics.quizStarts} Pessoas Começaram o Quiz!`,
        `Parabéns! Você atingiu a meta de ${TARGETS.QUIZ_STARTS} quiz starts.
         <br>Atualmente: <strong>${metrics.quizStarts} pessoas</strong> responderam o quiz hoje.
         <br><br>Próxima meta: Atingir 30% de taxa de clique em "Comprar".`
      );
      notificationsSent.quizStarts = true;
    }

    // Meta 2: Taxa de Clique
    if (clickRate >= TARGETS.CLICK_RATE && !notificationsSent.clickRate) {
      await sendEmail(
        `🚀 Meta Atingida: ${clickRate}% de Taxa de Clique!`,
        `Excelente! Você atingiu ${clickRate}% de taxa de clique.
         <br>Isso significa que ${metrics.totalClicks} de ${metrics.totalVisitors} pessoas clicaram em "Comprar".
         <br><br>Próxima meta: Obter 1ª conversão de venda.`
      );
      notificationsSent.clickRate = true;
    }

    // Meta 3: Conversões
    if (metrics.conversions >= TARGETS.CONVERSIONS && !notificationsSent.conversions) {
      await sendEmail(
        `💰 Meta Atingida: Primeira Conversão!`,
        `Parabéns! Você tem ${metrics.conversions} conversão(ões) confirmada(s)!
         <br>Receita gerada: R$ ${metrics.revenue.toFixed(2)}
         <br><br>Próxima meta: Atingir R$ 500 em receita mensal.`
      );
      notificationsSent.conversions = true;
    }

    // Meta 4: Receita
    if (metrics.revenue >= TARGETS.MONTHLY_REVENUE && !notificationsSent.revenue) {
      await sendEmail(
        `💵 Meta Atingida: R$ ${metrics.revenue.toFixed(2)} em Receita!`,
        `Fantástico! Você atingiu R$ ${metrics.revenue.toFixed(2)} em receita!
         <br>Total de conversões: ${metrics.conversions}
         <br><br>Você está no caminho certo! Continue otimizando.`
      );
      notificationsSent.revenue = true;
    }

    return {
      statusCode: 200,
      body: JSON.stringify({
        success: true,
        metrics: metrics,
        clickRate: clickRate,
        targets: TARGETS,
        notificationsSent: notificationsSent
      })
    };

  } catch (error) {
    console.error('Erro ao verificar métricas:', error);
    return {
      statusCode: 500,
      body: JSON.stringify({ error: error.message })
    };
  }
}

// Export para Netlify Functions
exports.handler = async (event, context) => {
  return await checkMetrics();
};
