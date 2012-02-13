/*
 * In tutto il sito vengono utilizzate classi e altri attributi dei tag html
 * per specificare del comportamento aggiuntivo realizzato tramite javascript;
 * questa funzione attiva tali comportamenti e viene chiamata automaticamente
 * in seguito al caricamento della pagina su tutto il document.
 *
 * `ctx` è il nodo dom dentro cui limitare l'analisi dei tag, *deve* essere
 * utilizzato ogni qual volta si inserisce del nuovo markup dinamicamente (ad
 * esempio in seguito ad una chiamata ajax).
 */
function setup_fragment(ctx) {
    ctx = ctx || document;
    setup_talkform(ctx);
    setup_tooltip(ctx);
    setup_toggles(ctx);
    setup_trigger_overlay(ctx);
}

/*
 * Tutti gli elementi con classe `.show-tooltip` e tutti gli `.help-text` di
 * una form vengono mostrati in un overlay sul mouseover.
 */
function setup_tooltip(ctx) {
    $('.show-tooltip', ctx).each(function() {
        var e = $(this);
        var rel = e.attr('rel');
        var fx = jQuery.browser.msie ? "toggle" : "fade";

        e.tooltip({
            position: "bottom center",
            offset: [5, 0],
            predelay: 200,
            relative: e.hasClass('relative'),
            tip: rel ? rel : null,
            effect: fx,
            opacity: 0.9
        }).dynamic();
    });

    $('form', ctx).each(function() {
        var i = $('.help-text', this).prev(':input');
        var relative = i.parents('.overlay').length != 0;
        i.tooltip({
            position: "center right",
            offset: [0, 10],
            effect: "fade",
            relative: relative,
            opacity: 0.9,
            events: {
                def:     "mouseenter,mouseleave",    // default show/hide events for an element
                input:   "focus,blur",               // for all input elements
                widget:  "focus mouseenter,blur mouseleave",  // select, checkbox, radio, button
                file:    "focus mouseenter,blur mouseleave",
                tooltip: "mouseenter,mouseleave"     // the tooltip element
            }
        });
    });
}
/*
 * Tramite la classe `.trigger-overlay` è possibile mostrare del contenuto in
 * una div in overlay. Il contenuto può provenire da una url remota (recuperata
 * tramite chiamata ajax) oppure da un div nascosto.
 *
 * Tramite gli attributi `rel` ed `href` si può specificare che div portare in
 * overlay e cosa mostrarci dentro.
 *
 *  <a class="trigger-overlay" rel="#id1" href="#">Click</a>
 *
 * Questo tag porta l'elemento $("#id1") in overlay; l'attributo `rel` è
 * formattato come un selettore jQuery e deve puntare ad un elemento
 * configurato secondo le specifiche di jQueryTools.
 *
 * Se `href` è presente e diverso da "#" rappresenta la url da mostrare
 * nell'overlay.
 *
 *  <a class="trigger-overlay" href="/url/to/document">Click</a>
 *
 * Se `rel` è omesso viene utilizzato un overlay di default.
 */
function setup_trigger_overlay(ctx) {
    $('.trigger-overlay', ctx).each(function() {
        var e = $(this);
        var rel = e.attr('rel') || $('#global-overlay');
        var href = e.attr('href');
        e.overlay({
            target: rel,
            onBeforeLoad: function() {
                if(href && href != '#') {
                    var wrap = this.getOverlay().find(".contentWrap");
                    if(!wrap)
                        throw "to use a remote content the overlay must have a .contentWrap element";
                    wrap.load(this.getTrigger().attr("href"));
                }
            },
            onLoad: function() {
                var code = e.attr('data-overlay-onload');
                if(code)
                    eval(code);
            }
        });
    });
}
/*
 * Tutti gli elementi con classe `.toggle` si permettono di aprire/chiudere
 * l'elemento specificato tramite l'attributo `rel` (formattato come un
 * selettore jQuery). Se l'attributo `rel` manca viene utilizzato come target
 * l'elemento successivo al toggle.
 *
 * Il target può specificare una url da cui scaricare dinamicamente il
 * contenuto tramite l'attributo `href` o `data-url`.
 */
function setup_toggles(ctx) {
    $('.toggle', ctx).each(function() {
        var trigger = $(this);
        var rel = trigger.attr('rel');
        if(rel)
            var target = $(rel);
        else
            var target = trigger.next();

        target.hide();
        trigger.addClass('trigger-collapsed');

        trigger.click(function(e) {
            e.preventDefault();
            target.toggle();
            if(target.is(":visible")) {
                trigger.removeClass('trigger-collapsed');
                trigger.addClass('trigger-expanded');
                var href = target.attr('href') || target.attr('data-url');
                if(href && href!='#') {
                    if(!target.data('target-loaded')) {
                        // devo recuperare il contenuto puntato da href e mostrarlo
                        // in target.
                        target.addClass('loading');
                        target.load(href, function() {
                            target.removeClass('loading');
                            setup_fragment(target);
                        });
                        target.data('target-loaded', 1);
                    }
                }
            }
            else {
                trigger.addClass('trigger-collapsed');
                trigger.removeClass('trigger-expanded');
            }
        });
    });
}
$(document).ready(function() {
    setup_fragment();
});

/*
 * Adding this to a javascript file that is included on your site will ensure
 * that AJAX POST requests that are made via jQuery will not be caught by the
 * CSRF protection.
 *
 * https://docs.djangoproject.com/en/dev/ref/contrib/csrf/#ajax
 */
$(document).ajaxSend(function(event, xhr, settings) {
    function getCookie(name) {
        var cookieValue = null;
        if (document.cookie && document.cookie != '') {
            var cookies = document.cookie.split(';');
            for (var i = 0; i < cookies.length; i++) {
                var cookie = jQuery.trim(cookies[i]);
                // Does this cookie string begin with the name we want?
                if (cookie.substring(0, name.length + 1) == (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    function sameOrigin(url) {
        // url could be relative or scheme relative or absolute
        var host = document.location.host; // host + port
        var protocol = document.location.protocol;
        var sr_origin = '//' + host;
        var origin = protocol + sr_origin;
        // Allow absolute or scheme relative URLs to same origin
        return (url == origin || url.slice(0, origin.length + 1) == origin + '/') ||
            (url == sr_origin || url.slice(0, sr_origin.length + 1) == sr_origin + '/') ||
            // or any other URL that isn't scheme relative or absolute i.e relative.
            !(/^(\/\/|http:|https:).*/.test(url));
    }
    function safeMethod(method) {
        return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
    }

    if (!safeMethod(settings.type) && sameOrigin(settings.url)) {
        xhr.setRequestHeader("X-CSRFToken", getCookie('csrftoken'));
    }
});

/*
 * crea un div di feedback per mostrare il testo passato all'utente; il div
 * viene distrutto dopo un po' di tempo
 */
function feedback(msg) {
    $('div.feedback').remove();
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

// http://stackoverflow.com/questions/1418050/string-strip-for-javascript
if(typeof(String.prototype.trim) === "undefined")
{
    String.prototype.trim = function() 
    {
        return String(this).replace(/^\s+|\s+$/g, '');
    };
}
// http://stackoverflow.com/questions/901115/get-querystring-values-in-javascript
function parseQueryString(qs) {
    if(!qs)
        qs = document.location.search;
    var urlParams = {};
    var e,
        a = /\+/g,  // Regex for replacing addition symbol with a space
        r = /([^&=]+)=?([^&]*)/g,
        d = function (s) { return decodeURIComponent(s.replace(a, " ")); };
    var q = qs.slice(0, 1) == '?' ? qs.substring(1) : qs;

    while(e = r.exec(q))
        urlParams[d(e[1])] = d(e[2]);
    return urlParams;
}


function scroll_to(e, duration) {
    $('html, body').animate({
        scrollTop: e.offset().top
    }, duration || 1000);
}

function setup_talkform(ctx) {
    $('form.talk-form', ctx).each(function() {
        var f = $(this);
        var field_type = $('input[name=type]', f);
        /* se viene scelto "training" voglio impostare la duration a 4 ore e
         * renderla readonly */
        function syncPage(last_run) {
            var talk_type = $('input[name=type]:checked', f).val();
            var field_duration = $('select[name=duration]', f);
            switch(talk_type) {
                case 's':
                    $('option[value=240]', field_duration).remove();
                    field_duration.attr('disabled', null);
                    break;
                case 't':
                    var h = $('option[value=240]', field_duration);
                    if(h.length == 0) {
                        var h = $('<option value="240">4 hours</option>');
                        field_duration.append(h);
                    }
                    h.attr('selected', 'selected');
                    field_duration.attr('disabled', 'disabled');
                    break;
                default:
                    $('input[name=type][value=s]', f).attr('checked', 'checked');
                    /* last_run viene usato come misura cautelativa, per evitare
                     * una ricorsione infinita nel caso il markup sia cambiato */
                    if(last_run != 1)
                        syncPage(1);
                    break;
            }
        }
        field_type.change(syncPage);
        syncPage();
    });
}
