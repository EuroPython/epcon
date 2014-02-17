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
    setup_voting_form(ctx);
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
    setup_disabled_form(ctx);
    if(setup_conference_fields && !(ctx === document))
        setup_conference_fields(ctx);
    if(typeof(twttr) != "undefined")
        twttr.widgets.load();
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
        setup($('.help-text', this).prev(':input').not('.markedit-widget'));
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
            var target = $(rel, ctx);
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

function supports_history_api() {
  return !!(window.history && history.pushState);
}

/*
 *
 */
function _async_form_push_state(form) {
    var fields = [];
    var state = {
        'type': 'async-form',
        'form_id': form.id,
        'fields': fields
    };
    var qstring = $(form).serialize();
    $('input,select,textarea', form).each(function() {
        fields.push($(this).val());
    })
    // aggiungo _pushed alla url in history.state perché alcuni browser, come
    // chrom*, si confondono se la url nella history è esattamente uguale a
    // quella richiesta via ajax, e in questo caso quando faccio un back
    // mostrano solo il frammento caricato tramite ajax.
    history.pushState(state, '', '?' + qstring + '&_pushed=1');
}

function _async_form_pop_event(e) {
    if(!e.state || e.state.type != 'async-form')
        return;
    var form = $('form#' + e.state.form_id);
    var fields = $('input,select,textarea', form);
    if(fields.length == e.state.fields.length) {
        fields.each(function(ix) {
            $(this).val(e.state.fields[ix]);
        });
        form.data('internal', 1);
        form.submit();
        form.data('internal', 0);
    }
}

if(supports_history_api()) {
    window.addEventListener("popstate", _async_form_pop_event, false);
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
            form.trigger('async-submit', response);
        },
        error: function() {
            //
        }
    }).submit(function() {
        var e = $(this);
        if(e.data('history-support') == 1 && e.data('internal') != 1) {
            _async_form_push_state(this);
        }
    }).each(function() {
        if(supports_history_api()
            && this.method.toLowerCase() == 'get'
            && this.id) {
            $(this).data('history-support', 1);
        }
    });
};

function setup_disabled_form(ctx) {
    $('form.disabled input', ctx).attr('disabled', 'disabled');
    $('form.disabled button', ctx).click(function() { return false; });
    $('form.disabled .button a', ctx).off('click').click(function() { return false; });
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
// http://blog.yjl.im/2012/01/datenow-in-ie8-or-before-ie9.html
if (!Date.now) {
  Date.now = function() {
    return new Date().valueOf();
  }
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

function setup_voting_form(ctx) {
    $('#form-options', ctx).submit(function() {
        /*
         * form asincrona con supporto per la history del browser,
         * ad ogni submit devo mantenere coerenti i widget custom.
         */
        var input = $('input[name=tags]', this);
        var tags = input.val().split(',');
        var r = new RegExp('"', 'g');
        for(var ix=0; ix<tags.length; ix++) {
            tags[ix] = tags[ix].replace(r, '');
        }
        $('a.tag', input.next()).each(function() {
            var e = $(this);
            if(tags.indexOf(e.attr('data-tag')) != -1) {
                e.addClass('selected');
            }
            else {
                e.removeClass('selected');
            }
        });

        $('.pseudo-radio-field input', this).each(function() {
            var e = $(this);
            $('.pseudo-radio', e.parent()).each(function() {
                var p = $(this);
                if(p.attr('data-value') == e.val()) {
                    p.addClass('checked');
                }
                else {
                    p.removeClass('checked');
                }
            });
        });
    });
}

function setup_talkform(ctx) {
    $('form.talk-form', ctx).each(function() {
        var f = $(this);
        var field_type = $('input[name=type]', f);
        var field_duration = $('select[name=duration]', f);
        var field_language = $('select[name=language]', f);
        var field_level = $('select[name=level]', f);
        /* se viene scelto "training" voglio impostare la duration a 4 ore e
         * renderla readonly */
        var original_durations = [];
        $('option', field_duration).each(function() {
            var o = $(this);
            original_durations.push([ o.val(), o.text() ]);
        });

        /*
         * in questa form voglio che i campi disabilitati vengano comunque inviati al server)
         */
        function disable_field(field) {
            field.attr('disabled', 'disabled');
            var value = field.val();
            var name = field.get(0).name;
            var p = field.parent();
            var shadow = p.children('input._shadow[type=hidden][name=' + name + ']');
            if(shadow.length) {
                shadow.val(value);
            }
            else {
                p.append($('<input type="hidden" class="_shadow" name="' + name + '" value="' + value + '" />'));
            }
        }
        function enable_field(field) {
            field.attr('disabled', null);
            var name = field.get(0).name;
            field
                .parent()
                .children('input._shadow[type=hidden][name=' + name + ']')
                    .remove();
        }
        function syncPage(last_run) {
            var talk_type = $('input[name=type]', f).val();
            switch(talk_type) {
                case 's':
                    $('option[value=240]', field_duration).remove();
                    enable_field(field_duration);
                    field_duration.parent().show();

                    enable_field(field_language);

                    enable_field(field_level);
                    field_level.parent().show();
                    break;
                case 't':
                case 'h':
                    var h = $('option[value=240]', field_duration);
                    if(h.length == 0) {
                        var label = "";
                        for(var ix=0; ix<original_durations.length; ix++) {
                            if(original_durations[ix][0] == 240) {
                                label = original_durations[ix][1];
                                break;
                            }
                        }
                        var h = $('<option value="240">' + label + '</option>');
                        field_duration.append(h);
                    }
                    h.attr('selected', 'selected');
                    disable_field(field_duration);
                    field_duration.parent().show();

                    var h = $('option[value=en]', field_language);
                    h.attr('selected', 'selected');
                    disable_field(field_language);

                    if(talk_type == 'h') {
                        var h = $('option[value=beginner]', field_level);
                        h.attr('selected', 'selected');
                        disable_field(field_level);
                        field_level.parent().hide();
                    }
                    else {
                        enable_field(field_level);
                        field_level.parent().show();
                    }
                    break;
                case 'p':
                    var h = $('option[value=45]', field_duration);
                    h.attr('selected', 'selected');
                    disable_field(field_duration);
                    field_duration.parent().hide();

                    var h = $('option[value=en]', field_language);
                    h.attr('selected', 'selected');
                    disable_field(field_language);

                    enable_field(field_level);
                    field_level.parent().show();
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

function form_errors(form, errors) {
    form = $(form);
    $('.field', form)
        .removeClass('error')
        .children('.errorlist')
        .remove();
    form.children('.error-notice').remove();
    for(var key in errors) {
        var error = errors[key];
        if(key != '__all__') {
            var elist = $('<ul class="errorlist"></ul>');
            for(var ix=0; ix<error.length; ix++) {
                elist.append('<li>' + error[ix]);
            }
            $('#id_' + key, form)
                .parent()
                .addClass('error')
                .append(elist);
        }
        else {
            var enotice = $('<div class="error-notice"></div>');
            for(var ix=0; ix<error.length; ix++) {
                enotice.append('<div>↓ ' + error[ix] + '</div>');
            }
            form.prepend(enotice);
        }
    }
}

(function($) {
    var _tm_helper = null;
    var _tt_helper = null;
    $.fn.extend({
        'verticalAlign': function(mode) {
            this.each(function() {
                var e = $(this);
                var ph = e.parent().height() / 2 +
                    (parseInt(e.parent().css('padding-top')) || 0) / 2 +
                    (parseInt(e.parent().css('padding-bottom')) || 0) / 2;
                var offset = ph - e.height() / 2;
                if(e.offsetParent().index(e.parent()) != -1) {
                    var top = offset;
                }
                else {
                    console.log('TODO: vertical_align')
                    return this;
                }
                mode = mode || 'relative';
                if(mode == 'relative') {
                    var pos = e.position();
                    var top = pos.top - (parseInt(e.css('top')) || 0);
                    e.css('position', 'relative');
                    e.css('top', (offset - top));
                }
            })
            return this;
        },
        'copyFontStylesTo': function(dst) {
            var src = this.eq(0);
            var styles = [
                'font-size', 'font-style', 'font-weight',
                'font-family', 'font-variant',
                'line-height', 'text-transform', 'letter-spacing'
            ];
            for(var ix=0, end=styles.length; ix<end; ix++) {
                dst.css(styles[ix], src.css(styles[ix]));
            }
            return this;
        },
        'copyFontStyles': function(src) {
            src.copyFontStylesTo(this);
            return this;
        },
        'textMetrics': function(width) {
            var output = {
                width: 0,
                height: 0
            };
            if(this.length == 0)
                return output;

            var src = this.eq(0);
            if(!_tm_helper) {
                _tm_helper = $('<div id="_tm_helper"></div>')
                    .appendTo(document.body)
                    .css({
                        position: 'absolute',
                        top: -1000,
                        visibility: 'hidden'
                    });
            }
            _tm_helper
                .copyFontStyles(src)
                .css('width', width || 'auto')
                .html(src.html());

            output['height'] = _tm_helper.outerHeight();
            output['width'] = _tm_helper.outerWidth();

            return output;
        },
        'truncateText': function(height) {
            if(!_tt_helper) {
                _tt_helper = $('<div id="_tt_helper"></div>')
                    .appendTo(document.body)
                    .css({
                        visibility: 'hidden',
                        display: 'inline-block'
                    })
            }
            return this.each(function() {
                var e = $(this);
                var h = height || e.height();
                _tt_helper
                    .css('width', e.width())
                    .copyFontStyles(e);
                var text = e.text();
                var ex = text.length;
                var cx = ex;
                var counter = 0
                while(true) {
                    var t = text.substr(0, cx);
                    _tt_helper.text(t);
                    if(_tt_helper.height() > h) {
                        ex = cx;
                        cx = Math.floor(ex / 2);
                    }
                    else {
                        if(ex == cx) {
                            break;
                        }
                        var w = cx;
                        cx += Math.floor(Math.abs(ex-cx) / 2);
                        ex = w;
                    }
                    counter += 1;
                }
                if(counter > 0) {
                    var tx = t.length;
                    while(tx > 0 && t.substr(tx, 1) != ' ')
                        tx--;
                    e.html(
                        '<span>' + text.substr(0, tx) + '</span>'
                        + '<span class="ellipsis">\u2026</span>'
                        + '<span class="after-ellipsis">' + text.substr(tx) + '</span>'
                    );
                }
            });
        }
    });
})(jQuery);

// based on http://javascript.crockford.com/remedial.html
// modified to support object path: "{o.attr}".format({o: {attr: 'foo'}});
if(!String.prototype.supplant) {
    String.prototype.supplant = function (o) {
        return this.replace(
            /\{([^{}]*)\}/g,
            function (a, b) {
                var r = o[b];
                if(typeof r === 'undefined' && typeof o === 'object' && b.indexOf('.') != -1) {
                    var path = b.split('.');
                    var ctx = o;
                    for(var ix=0; ix<path.length; ix++) {
                        r = ctx = ctx[path[ix]];
                        if(typeof r === 'undefined')
                            break;
                    }
                }
                return typeof r === 'string' || typeof r === 'number' ? r : a;
            }
        );
    };
}
