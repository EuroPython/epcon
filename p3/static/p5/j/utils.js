function setup_trigger_overlay(jq) {
    jq.each(function() {
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
            }
        });
    });
}
$(document).ready(function() {
    /*
     * ogni tag con classe "toggle" diventa un toggle-button
     * che mostra nasconde l'elemento successivo
     */
    $(".toggle").each(function() {
        // nasconde il contenuto e aggiunge il supporto per il mostra/nascondi
        if($(this).attr('rel'))
            var target = $($(this).attr('rel'));
        else
            var target = $(this).next();
        var trigger = $(this);
        target.hide();
        trigger.addClass('trigger-collapsed');
        trigger.click(function() {
            target.toggle();
            if(target.is(":visible")) {
                trigger.removeClass('trigger-collapsed');
                trigger.addClass('trigger-expanded');
            }
            else {
                trigger.addClass('trigger-collapsed');
                trigger.removeClass('trigger-expanded');
            }
        });
    });

     $('.show-tooltip').each(function() {
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

    setup_trigger_overlay($('.trigger-overlay'));

    $('form').each(function() {
        var i = $('.help-text', this).prev(':input');
        var relative = i.parents('.overlay').length != 0;
        i.tooltip({
            position: "center right",
            offset: [0, 10],
            effect: "fade",
            relative: relative,
            opacity: 0.9
        })
    });
});

$('html').ajaxSend(function(event, xhr, settings) {
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
    if (!(/^http:.*/.test(settings.url) || /^https:.*/.test(settings.url))) {
        // Only send the token to relative URLs i.e. locally.
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
