(function() {
    var supports_history_api = !!(window.history && history.pushState);

    var nav = $('#schedule-navigator');

    $('#schedule-navigator .opener').click(function(e) {
        $("#schedule-navigator .content").animate({width:'toggle'}, 350, function() {
            var e = $(this);
            if(e.css('display') == 'none') {
                e.prev().removeClass('opened').addClass('closed');
            }
            else {
                e.prev().removeClass('closed').addClass('opened');
            }
        });
    });
    /*
        * Ricerca full text nello schedule: l'utente inserisce i termini da
        * ricercare, quando tenta di fare il submit della form:
        *  * se il testo inserito è diverso dall'ultima ricerca fatta viene
        *  esgeuita una richiesta AJAX, i risultati vengono evidenziati e il
        *  browser scorre alla prima occorrenza
        * 
        *  * se il testo è uguale viene scrollato il browser alla occorrenza
        *  successiva
        *
        * la form viene automaticamente submittata, dopo 400ms, se vengono
        * inseriti almeno 3 caratteri
        */
    var autocomplete = { 'timeout': null, 'last_search': '' };
    function highlight_search_results(ids) {
        if(!ids.length) {
            $('.event[data-event-id]').removeClass('search-result-ok').removeClass('search-result-ko');
        }
        else {
            $('.event[data-event-id]').not('.event.t-break').not('.event.t-special').each(function() {
                var e = $(this);
                if(ids.indexOf(e.attr('data-event-id')) == -1) {
                    e.removeClass('search-result-ok').addClass('search-result-ko');
                }
                else {
                    e.removeClass('search-result-ko').addClass('search-result-ok');
                }
            });
        }
    }

    var _search_results = {
        'data': [],
        'scrollTo': -1
    };
    var _search_results = [];
    var _show_search_result = -1;
    function set_search_results(events_ids) {
        _search_results.data = events_ids;
        _search_results.scrollTo = -1;
        highlight_search_results(events_ids);
        scroll_to_next_result();
    }
    function scroll_to_next_result() {
        var data = _search_results.data;

        if(data.length <= 0)
            return;

        _search_results.scrollTo += 1;
        if(_search_results.scrollTo >= data.length)
            _search_results.scrollTo = 0;

        scroll_to($('.event[data-event-id=' + data[_search_results.scrollTo] + ']'));
    }
    function _searchSchedule() {
        var i = $('.search input', nav);
        var value = $.trim(i.val());
        autocomplete['timeout'] = null;
        if(value == '') {
            set_search_results([]);
            autocomplete['last_search'] = i.val();
        }
        else if(value != autocomplete['last_search']) {
            autocomplete['last_search'] = i.val();
            $.ajax({
                url: '{% url "p3-schedule-search" conference=params.conference%}?q=' + i.val(),
                dataType: 'json',
                success: function(data, status, jqXHR) {
                    var events_ids = [];
                    for(var ix=0; ix<data.length; ix++) {
                        events_ids.push(data[ix].pk);
                    }
                    set_search_results(events_ids);
                },
                complete: function() {
                }
            });
        }
        else {
            scroll_to_next_result();
        }
    }
    $('.search', nav).submit(function() {
        if(autocomplete['timeout']) {
            clearTimeout(autocomplete['timeout']);
            autocomplete['timeout'] = null;
        }
        _searchSchedule();
        return false;
    });
    $('.search input', nav).keyup(function(e) {
        if(e.keyCode == 13)
            return;
        if(autocomplete['timeout']) {
            clearTimeout(autocomplete['timeout']);
        }
        autocomplete['timeout'] = setTimeout(_searchSchedule, 400);
    });

    var flags = {
        'show-training': function(visible) {
            var form = $('.show-flags', nav);
            var v = visible ? 1 : 0;
            $.each(['show-training1', 'show-training2', 'show-trackx'], function(ix, name) {
                var i = $('input[name=' + name + ']');
                if(i.length) 
                    i.val(v)
                else
                    form.append('<input type="hidden" name="' + name + '" value="' + v + '" />')
            });
            return true;
        },
        'show-partner-program': function(visible) {
            var form = $('.show-flags', nav);
            var v = visible ? 1 : 0;
            $.each(['show-partner0', 'show-partner1'], function(ix, name) {
                var i = $('input[name=' + name + ']');
                if(i.length) 
                    i.val(v)
                else
                    form.append('<input type="hidden" name="' + name + '" value="' + v + '" />')
            });
            return true;
        },
        'show-sprint': function(visible) {
            var form = $('.show-flags', nav);
            var v = visible ? 1 : 0;
            $.each(['show-sprint0', 'show-sprint1'], function(ix, name) {
                var i = $('input[name=' + name + ']');
                if(i.length) 
                    i.val(v)
                else
                    form.append('<input type="hidden" name="' + name + '" value="' + v + '" />')
            });
            return true;
        }
    };
    var form_flags = $('.show-flags', nav);
    function changeShowFlag(name, value) {
        var input = $('input[name=' + name + ']', form_flags);
        if(input.length == 0)
            return;
        var label = input.parents('label');
        var visible = value;
        if(visible == null)
                visible = input.val() == 0;

        if(visible) {
            input.val(1);
            label.removeClass('inactive').addClass('active');
        }
        else {
            input.val(0);
            label.removeClass('active').addClass('inactive');
        }
        if(name in flags)
            var submit = flags[name](visible);
        else
            var submit = true;
        if(submit && value == null)
            form_flags.submit();
    }
    function syncFormWithQueryString() {
        var opts = parseQueryString();
        for(var k in opts) {
            if(opts[k] != '1')
                changeShowFlag(k, false);
        }
    }

    var page_load = true;

    $('label', form_flags).click(function(e) {
        e.preventDefault();
        if(form_flags.attr('data-wait') > 0)
            return;
        changeShowFlag($('input', this).attr('name'))
    });

    function refreshSchedule() {
        var qa = $.param($.extend(parseQueryString(), parseQueryString(form_flags.serialize())));
        if(supports_history_api) {
            var url = document.location.href;
            if(url.indexOf('?') != -1) {
                url = url.slice(0, url.indexOf('?'));
            }
            url += '?' + qa;
            history.pushState(null, null, url);
        }
        var schedules = $('.schedule-wrapper')
        if(schedules.length) {
            var h3 = form_flags.prev();
            h3.prepend('<img src="{{ STATIC_URL }}p6/i/ajax-loader.gif" width="16" />');
            form_flags.attr('data-wait', schedules.length);
            schedules.each(function() {
                var schedule = $(this);
                schedule.load(schedule.attr('data-schedule-url') + '?' + qa, function() {
                    var queue = form_flags.attr('data-wait') - 1;
                    if(queue <= 0)
                        $('img', h3).remove();
                    form_flags.attr('data-wait', queue);
                }); 
            });
        }
    }

    form_flags.submit(function() {
        refreshSchedule();
        return false;
    });

    if(supports_history_api) {
        $(window).bind('popstate', function(e) {
            syncFormWithQueryString();
            if(page_load) {
                page_load = false
            }
            else {
                refreshSchedule();
            }
        });
    }

    /*
     * devo simulare quello che già fa il browser, perchè anche il click su un
     * anchor che cambia solo il fragment causa un evento popstate (e non
     * voglio cercare di capire in che caso mi trovo nell'event listener)
     */
    $('.jump-list li').click(function(e) {
        e.preventDefault();
        scroll_to($(e.target.href.substring(e.target.href.indexOf('#'))));
    });
})();

