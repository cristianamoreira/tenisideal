var CONFIG = {
    EMAIL_TO: "seu.email@exemplo.com", // Coloque seu email aqui
    MIN_CTR: 1.5, // % mínima de CTR desejada (Abaixo disso, alerta de anúncio ruim)
    IMPRESSIONS_THRESHOLD: 1000 // Só analisa anúncios com mais de 1000 impressões
};

function main() {
    var adsIterator = AdsApp.ads()
        .withCondition("Status = ENABLED")
        .withCondition("CampaignStatus = ENABLED")
        .withCondition("AdGroupStatus = ENABLED")
        .forDateRange("LAST_14_DAYS")
        .get();

    var badAdsReport = "Relatório de Anúncios com Baixo Desempenho (Últimos 14 dias):\n\n";
    var hasBadAds = false;

    while (adsIterator.hasNext()) {
        var ad = adsIterator.next();
        var stats = ad.getStatsFor("LAST_14_DAYS");
        var impressions = stats.getImpressions();
        var ctr = stats.getCtr() * 100; // Converte para porcentagem

        if (impressions > CONFIG.IMPRESSIONS_THRESHOLD && ctr < CONFIG.MIN_CTR) {
            hasBadAds = true;
            badAdsReport += "Campanha: " + ad.getCampaign().getName() + " | Grupo: " + ad.getAdGroup().getName() + "\n";
            // badAdsReport += "Título do Anúncio: " + ad.getHeadlinePart1() + "\n"; // Dependendo do tipo de anúncio, pegue os campos relevantes.
            badAdsReport += "Impressões: " + impressions + " | CTR: " + ctr.toFixed(2) + "%\n";
            badAdsReport += "--------------------------------------------------\n";
        }
    }

    if (hasBadAds) {
        Logger.log("Enviando relatório de anúncios ruins para " + CONFIG.EMAIL_TO);
        MailApp.sendEmail(CONFIG.EMAIL_TO, "Alerta Google Ads: Anúncios com CTR Baixo - Tênis Ideal", badAdsReport);
    } else {
        Logger.log("Nenhum anúncio ruim detectado nos últimos 14 dias com base nos critérios.");
    }
}
