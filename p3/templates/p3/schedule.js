(function() {


    var nav = $('#schedule-navigator');

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

        var e = $('.event[data-event-id=' + data[_search_results.scrollTo] + ']')
        $('html, body').animate({
            scrollTop: e.offset().top
        }, 1000);
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
                url: '{% url p3-schedule-search conference=params.conference%}?q=' + i.val(),
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

    /*
     * Gestione Filtri di visualizzazione: ad ogni filtro corrisponde una
     * funzione js che viene eseguita quando cambia il valore.  Le scelte
     * dell'utente vengono salvate in un cookie locale.
     */
    function _get() {
        var opts = {}
        var raw = $.cookie('schedule_opts');
        if(raw) {
            $.each(raw.split(','), function(ix, val) {
                opts[val] = '';
            });
        }
        return opts;
    }
    function _set(opts) {
        var raw = [];
        for(var k in opts) {
            raw.push(k);
        }
        $.cookie('schedule_opts', raw.join(','), { expires: 60 });
    }
    function setQueryArgument(qs, name, value) {
        if(qs.indexOf(name) != -1) {
            var r = new RegExp("(&?)" + name + "=[^&]*&?");
            qs = qs.replace(r, '$1');
        }
        if(value==null)
            return;
        var t = name + '=' + value;
        if(qs.length == 0)
            qs = '?' + t;
        else if(qs == '?' || qs.slice(-1) == '&')
            qs += t;
        else
            qs += '&' + t;
        return qs;
    }
    var opts = _get();
    var flags = {
        'show-training': function(visible) {
            var form = $('.show-flags', nav);
            var v = visible ? 1 : 0;
            $.each([ 'show-training1', 'show-training2', 'show-trackx'], function(ix, name) {
                var i = $('input[name=' + name + ']');
                if(i.length) 
                    i.val(v)
                else
                    form.append('<input type="hidden" name="' + name + '" value="' + v + '" />')
            });
            return true;
        },
        'show-votes': function(visible, init) {
            $('.schedule .talk-vote').each(function(ix, dom) {
                if(!visible)
                    $(dom).hide();
                else
                    $(dom).show();
            });
        }
    }
    var form_flags = $('.show-flags', nav);
    function changeShowFlag(name, value) {
        var input = $('input[name=' + name + ']', form_flags);
        if(input.length == 0)
            return;
        var action = input.next();
        var visible = value;
        if(visible == null)
                visible = input.val() == 0;

        if(visible) {
            delete opts[name];
            input.val(1);
            action.text('Hide');
        }
        else {
            opts[name] = '';
            input.val(0);
            action.text('Show');
        }
        _set(opts);
        if(name in flags)
            var submit = flags[name](visible);
        else
            var submit = true;
        if(submit && value == null)
            form_flags.submit();
    }
    for(var k in opts) {
        changeShowFlag(k, false);
    }
    $('label', form_flags).click(function(e) {
        e.preventDefault();
        changeShowFlag($('input', this).attr('name'))
    });
})();

