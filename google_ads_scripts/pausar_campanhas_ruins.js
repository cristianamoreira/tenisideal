function main() {
    var limitCPA = 50.0; // Defina seu CPA limite (Custo Por Aquisição/Conversão) desejado

    var campaigns = AdsApp.campaigns()
        .withCondition("Status = ENABLED") // Somente campanhas ativas
        .forDateRange("LAST_30_DAYS") // Analisa os dados dos últimos 30 dias
        .get();

    while (campaigns.hasNext()) {
        var campaign = campaigns.next();
        var stats = campaign.getStatsFor("LAST_30_DAYS");
        var conversions = stats.getConversions();
        var cost = stats.getCost();

        Logger.log("Analisando campanha: " + campaign.getName());

        // Se gastou mais que o CPA limite, mas não teve NENHUMA conversão: PAUSAR
        if (cost > limitCPA && conversions == 0) {
            Logger.log("ALERTA: Campanha '" + campaign.getName() + "' gastou R$" + cost + " sem conversões. Pausando...");
            campaign.pause();
        }
        // Se teve conversão, mas o custo por conversão está acima do limite em 20%: AVISAR/PAUSAR
        else if (conversions > 0) {
            var currentCPA = cost / conversions;
            if (currentCPA > (limitCPA * 1.2)) {
                Logger.log("ALERTA: Campanha '" + campaign.getName() + "' está com CPA muito alto: R$" + currentCPA + " (Limite: R$" + limitCPA + "). Considere pausar ou otimizar.");
                // Para pausar automaticamente remova os "//" da linha abaixo
                // campaign.pause();
            }
        }
    }
}
