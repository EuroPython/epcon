
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

/*
 * crea un div di feedback per mostrare il testo passato all'utente; il div
 * viene distrutto dopo un po' di tempo
 */
function feedback(msg) {
    var f = $('#feedback-js');
    if(f.length != 0) {
        f.html(msg);
    }
    else {
        var f = $('<div id="feedback-js" class="feedback"></div>');
        f.html(msg);
        f.prependTo(document.body)
        setTimeout(function() { f.remove() }, 10000);
    }
}
