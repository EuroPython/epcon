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
    setup_profile_picture_form(ctx);
    setup_cart_form(ctx);
    setup_tooltip(ctx);
    setup_toggles(ctx);
    setup_auto_tabs(ctx);
    // jQueryTools è bacato in tanti modi diversi; ad esempio l'overlay non si
    // aggancia ad elementi scollegati dal dom
    if(ctx === document) {
        setup_trigger_overlay(ctx);
    }
    else {
        setTimeout(function() { setup_trigger_overlay(ctx) }, 200);
    }
    setup_live_edit(ctx);
    setup_async_form(ctx);
    if(setup_conference_fields && !(ctx === document))
        setup_conference_fields(ctx);
    return ctx;
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
        function setup(i, tip) {
            var position = 'center right';
            if(i.length && i.get(0).nodeName.toUpperCase() == 'LABEL') {
                position = 'top center';
            }
            var relative = i.parents('.overlay').length != 0;
            i.tooltip({
                position: position,
                offset: [0, 10],
                effect: "fade",
                relative: relative,
                opacity: 0.9,
                tip: tip,
                events: {
                    def:     "mouseenter,mouseleave",    // default show/hide events for an element
                    input:   "focus,blur",               // for all input elements
                    widget:  "focus mouseenter,blur mouseleave",  // select, checkbox, radio, button
                    file:    "focus mouseenter,blur mouseleave",
                    tooltip: "mouseenter,mouseleave"     // the tooltip element
                }
            });
        }
        /* normalmente gli .help-text sono posti subito dopo i tag input,
         * questo si sposa perfettamente con il comportamento di default dei
         * tooltip che di solito cercano il testo da mostrare nell'elemento
         * successivo al trigger, ma...
         */
        setup($('.help-text', this).prev(':input'));
        /*
         * i radio vengono renderizzati in maniera diversa, qui l'help-text è
         * posto dopo un ul che contiene tutti gli input
         */
        $('.help-text', this).prev('ul').each(function() {
            var inputs = $('label', this);
            var ht = $(this).next();
            inputs.each(function() {
                setup($(this), ht);
            });
        });
        /*
         * altri input vengono invece renderizzati dentro la label, in questo
         * caso voglio che il tooltip sia attivo su tutta la label.
         */
        setup($('.help-text', this).prev('label'));
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
function setup_live_edit(ctx) {
    $('form.live-edit', ctx).each(function() {
        var fields = $('.field', this);
        var readonly = fields.prev();
        var switches = $('.live-edit-switch', this);
        var autosubmit = $('.autosubmit', this);
        switches.click(function(e) {
            e.preventDefault();
            var visible = $(':visible', fields).length > 0;
            if(visible) {
                readonly.show();
                fields.hide();
                autosubmit.hide();
            }
            else {
                readonly.hide();
                fields.show();
                autosubmit.show();
            }
            switches.show();
            $(this).hide();
        })
    });
}

function setup_async_form(ctx) {
    function _autosubmit() {
        $(this).parents('form').submit();
    }
    $('form .autosubmit select', ctx).change(_autosubmit);
    $('form .autosubmit input', ctx).change(_autosubmit);
    $('form a.autosubmit', ctx).click(function(e) {
        e.preventDefault();
        _autosubmit.call(this);
    });
    $('form.async', ctx).ajaxForm({
        success: function(response, status, xhr, form) {
            var rel = form.attr('rel');
            if(rel) {
                if(rel == 'self') {
                    var target = form;
                }
                else {
                    var target = $(rel);
                }
                var frag = setup_fragment($(response));
                target.replaceWith(frag);
                $('.async-feedback', frag).show().fadeOut(5000);
            }
            else if(form.hasClass('autorefresh')) {
                autorefresh(form);
            }
        },
        error: function() {
            //
        }
    });
};

function autorefresh(o) {
    var url = o.attr('data-refresh');
    if(!url) {
        var p = o.parents('[data-refresh]').eq(0);
        if(p.length) {
            url = p.attr('data-refresh');
            o = p;
        }
    }
    if(!url)
        return;
    $.get(url, function(data) {
        o.replaceWith(setup_fragment($(data)));
    });
}

function setup_auto_tabs(ctx) {
     $('.auto-tabs', ctx).tabs();
}

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
            var talk_type = $('input[name=type]', f).val();
            var field_duration = $('select[name=duration]', f);
            var field_language = $('select[name=language]', f);
            switch(talk_type) {
                case 's':
                    $('option[value=240]', field_duration).remove();
                    field_duration.attr('disabled', null);
                    field_duration.parent().show();

                    field_language.attr('disabled', null);
                    break;
                case 't':
                    var h = $('option[value=240]', field_duration);
                    if(h.length == 0) {
                        var h = $('<option value="240">4 hours</option>');
                        field_duration.append(h);
                    }
                    h.attr('selected', 'selected');
                    field_duration.attr('disabled', 'disabled');
                    field_duration.parent().show();

                    var h = $('option[value=en]', field_language);
                    h.attr('selected', 'selected');
                    field_language.attr('disabled', 'disabled');
                    break;
                case 'p':
                    var h = $('option[value=45]', field_duration);
                    h.attr('selected', 'selected');
                    field_duration.attr('disabled', 'disabled');
                    field_duration.parent().hide();

                    var h = $('option[value=en]', field_language);
                    h.attr('selected', 'selected');
                    field_language.attr('disabled', 'disabled');
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

function setup_profile_picture_form(ctx) {
    var form = $('#profile-picture-form', ctx);
    var radios = $('input[type=radio]', form);
    radios.change(function() {
        $('input', radios.parent().next()).attr('readonly', 'readonly');
        $('input', $(this).parent().next())
            .attr('readonly', null)
            .focus();
    });
    $(':checked', form).change();
}

function setup_cart_form(ctx) {
    var months = new Array(12);
    months[0] = "January";
    months[1] = "February";
    months[2] = "March";
    months[3] = "April";
    months[4] = "May";
    months[5] = "June";
    months[6] = "July";
    months[7] = "August";
    months[8] = "September";
    months[9] = "October";
    months[10] = "November";
    months[11] = "December";

    var form = $('#form-cart');
    if(!form.length)
        return;

    function setup_period_range(e) {
        var days = Number(e.attr('data-steps'));

        var period_start = new Date(e.parent().parent().prev().attr('data-period-start'));
        var label = e.prevAll('p');

        function format_date(d) {
            return d.getDate() + ' ' + months[d.getMonth()];
        }
        function set_label(values) {
            if(!values) {
                values = e.slider('values');
            }
            var txt = "from ";
            var d = new Date(period_start);
            d.setDate(d.getDate() + values[0]);
            txt += format_date(d) + " to ";
            d.setDate(d.getDate() + (values[1]-values[0]));
            txt += format_date(d);
            label.text(txt);
        }
        /*
         * questi sono gli input da mantenere sincronizzati con i valore dello
         * slider
         */
        var inputs = $('input[type=hidden]', e.parent());
        /*
         * questa funzione viene chiamata anche su elementi clonati dove è già
         * presente il markup dello slider; la chiamata .html('') anche se poco
         * elegante mi permette di fare tabula rasa e ripartire da zero.
         */
        e.html('').slider({
            range: true,
            min: 0,
            max: days,
            values: [ Number(inputs.eq(0).val()), Number(inputs.eq(1).val())],
            slide: function(evt, ui) {
                set_label(ui.values);
                inputs.eq(0).val(ui.values[0]);
                inputs.eq(1).val(ui.values[1]);
            }
        });
        set_label();
    };

    function setup_reservation_rows(rows) {
        $(rows).each(function() {
            var reservation = $(this);
            var details = reservation.next();
            $('.room-type', reservation).click(function(e) {
                e.preventDefault();
                var a = $(this);
                var code = a.attr('data-fare');
                a.parent()
                    .children('.room-type')
                    .removeClass('selected');
                a.addClass('selected');

                $('td[data-fare]', details)
                    .attr('data-fare', code)
                    .children('input[type=hidden]')
                    .val(code);
            });
            var init = $('td[data-fare] input[type=hidden]', details).val();
            $('.room-type-' + init, reservation).click();

            setup_period_range($('.period', details));
        });
    }

    setup_reservation_rows($('.hotel-reservation-type', form));

    $('.cart-hotel-another-reservation', form).click(function(e) {
        e.preventDefault();
        var type = $(this).attr('data-type');
        var rows = $('tr[data-reservation-type=' + type + ']', form);

        var orig = rows.eq(rows.length-1);
        var main = orig.clone();
        var details = orig.next().clone();

        orig.parents('tbody')
            .append(main)
            .append(details);

        setup_reservation_rows(main);
        setup_cart_input($('input', main));
        setup_cart_input($('input', details));
    });

    function calcTotal() {

        form.ajaxSubmit({
            url: '/p3/cart/calculator/',
            dataType: 'json',
            success: function(data, text, jqHXR) {
                /*
                 * data contiene il totale generale, lo sconto ottenuto tramit
                 * coupon e il dettaglio dei costi dei singoli biglietti
                 */
                var feedback = $('.coupon .cms span');
                feedback.text(data.coupon != 0 ? 'coupon accepted' : '');
                $('.coupon .total b', form).html('€ ' + data.coupon);
                $('.grand.total b', form).html('€ ' + data.total);

                /*
                 * ...il problema con i costi dei singoli biglietti è quello di
                 * mostrare per ogni prenotazione alberghiera il prezzo
                 * corrispondente.
                 * Il prezzo degli altri biglietti non varia con i parametri
                 * inseriti dall'utente, ad esempio non abbiamo lo sconto
                 * quantità, quindi posso mostrare il prezzo del singolo
                 * biglietto in anticipo inserendolo nell'html. Con le
                 * prenotazioni alberghiere invece il prezzo varia sia con il
                 * tipo di camera (ma qui sono fare diverse è la nostra UI che
                 * le vuol far vedere su una singola riga) sia con il periodo
                 * di pernottamento, inoltre possiamo avere più biglietti dello
                 * stesso tipo ma con periodi diversi (ad esempio potrei voler
                 * prenotare 1 biglietto HB3 per le date X e Y e 1 biglietto
                 * sempre HB3 ma per le date X' e Y')
                 */
                $('fieldset .total').data('total', 0);
                function update_total(parent, value) {
                    var e = $('.total', parent);
                    var total = e.data('total') + Number(value);
                    e.data('total', total);
                    e.html('€ ' + total.toFixed(2));
                }
                $(data.tickets).each(function() {
                    var code = this[0];
                    var params = this[1];
                    var total = this[2];
                    var group = code.substr(0, 1);
                    /*
                     * per tutti i biglietti, ad eccezioni delle prenotazioni
                     * alberghiere, posso limitarmi ad aggiungere il valore nel
                     * totale di sezione (identificato con la prima lettera del
                     * codice tariffa)...
                     */
                    switch(group) {
                        case 'H':
                            /*
                             * ...ma per le tariffe alberghiere devo anche
                             * mostrare il valore del biglietto nella riga
                             * corrispondente. E non basta usare il codice
                             * tariffa, devo fare anche il match con il periodo
                             */
                            $('.hotel-reservations td[data-fare=' + code + ']', form).each(function() {
                                var qty = $(this);
                                if($('input[type=text]', qty).val() == params.qty) {
                                    // ho trovato un input con la stessa quantità e
                                    // lo stesso codice tariffa, ora devo
                                    // controllare il periodo
                                    var period = $('.period', qty.prev()).slider('values');
                                    if(params.period[0] == period[0] && params.period[1] == period[1]) {
                                        // trovato!
                                        var price = qty.next();
                                        price.html('€ ' + total);
                                        update_total(price.parents('.hotel-reservations'), total);
                                    }
                                }
                            });
                            break;
                        default:
                            update_total($('.conference-tickets', form), total);
                            break;
                    }
                });
            }
        });
    }
    function setup_cart_input(inputs) {
        inputs
            .change(calcTotal)
            .not('[name=coupon]')
            .keypress(function(e) {
                if((e.which < 48 || e.which > 57) && e.which != 13 && e.which != 0 && e.which != 8) {
                    e.preventDefault()
                }
            });
    }
    setup_cart_input($('input', form));

    function _enableFares(personal) {
        $('.conference-tickets td.fare', form).each(function() {
            var td = $(this);
            var fare_code = td.attr('data-fare');
            var e = ((fare_code.substr(3, 1) == 'C' && !personal) || (fare_code.substr(3, 1) != 'C' && personal));
            var inputs = $('input', td);
            if(e) {
                td.removeClass('disabled');
                inputs.attr('disabled', false);
            }
            else {
                td.addClass('disabled');
                inputs.attr('disabled', true);
            }
        });
    }
    $('#id_order_type').change(function() {
        _enableFares($(this).val() != 'deductible');
        calcTotal();
    });

    if(document.location.search.substr(0, 3) == '?f=') {
        var highligh_fare = document.location.search.substr(3);
        var i = $('td[data-fare=' + highligh_fare + '] input');
        if(!i.val())
            i.val(1);
        i.addClass('selected')
            .focus()
            .parents('tr')
            .addClass('selected');
        i.eq(0)[0].scrollIntoView();
    }

    $('#id_order_type').change();
}
