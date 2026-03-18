function main() {
    // Ajuste esse valor de acordo com a sua margem. Ex: Queremos que o ROAS seja no mínimo 3.0 (300%)
    var targetROAS = 3.0;

    var keywords = AdsApp.keywords()
        .withCondition("Status = ENABLED")
        .withCondition("CampaignStatus = ENABLED")
        .withCondition("AdGroupStatus = ENABLED")
        .forDateRange("LAST_30_DAYS")
        .get();

    while (keywords.hasNext()) {
        var keyword = keywords.next();
        var stats = keyword.getStatsFor("LAST_30_DAYS");

        var cost = stats.getCost();
        var conversionValue = stats.getConversionValue();

        // Calcula o ROAS atual da palavra-chave
        var currentROAS = cost > 0 ? (conversionValue / cost) : 0;

        // Se o ROAS for menor que o desejado e o custo for maior que R$20 (para ter alguma relevância estatística)
        if (currentROAS < targetROAS && cost > 20) {
            Logger.log("Atenção: A palavra-chave '" + keyword.getText() + "' está com ROAS de " + currentROAS.toFixed(2) + " (Abaixo da meta de " + targetROAS + "). Diminuindo o lance (CPC Máx) em 10%.");

            // Diminui o lance em 10%
            var currentBid = keyword.bidding().getCpc();
            if (currentBid) {
                keyword.bidding().setCpc(currentBid * 0.90);
            }
        }
        // Se o ROAS for MUITO bom (ex: 50% maior que a meta), aumenta o lance para forçar mais impressões
        else if (currentROAS > (targetROAS * 1.5)) {
            Logger.log("Sucesso: A palavra-chave '" + keyword.getText() + "' está com ótimo ROAS (" + currentROAS.toFixed(2) + ")! Aumentando o lance em 5%.");

            var currentBid = keyword.bidding().getCpc();
            if (currentBid) {
                keyword.bidding().setCpc(currentBid * 1.05);
            }
        }
    }
}
