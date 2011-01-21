
$(document).ready(function() {
    /*
     * ogni tag con classe "toggle" diventa un toggle-button
     * che mostra nasconde l'elemento successivo
     */
    $(".toggle").each(function() {
        // nasconde il contenuto e aggiunge il supporto per il mostra/nascondi
        $(this).next().hide();
        $(this).click(function() {
            $(this).next().toggle();
        });
    });
});
