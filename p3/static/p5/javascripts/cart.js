(function($) {
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

        var period_start = new Date(e.parent().parent().attr('data-period-start'));
        var label = e.prevAll('p');

        function format_date(d) {
            return d.getDate() + ' ' + months[d.getMonth()];
        }
        function set_label(values) {
            if(!values) {
                values = e.slider('values');
            }
            var checkin = new Date(period_start);
            checkin.setDate(checkin.getDate() + values[0]);

            var checkout = new Date(period_start);
            checkout.setDate(checkout.getDate() + values[1]);

            var txt = "checkin <b>" + format_date(checkin) + "</b>, ";
            txt += "checkout <b>" + format_date(checkout) + "</b> morning ";
            txt += "(<b>" + ((checkout-checkin) / (60000 * 60 * 24)) + " nights</b>)";
            label.html(txt);
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
        function cap_values(slider, handle, values) {
            var hix = handle.data('index.uiSliderHandle');
            var max = slider.slider('option', 'max');
            var min = slider.slider('option', 'min');
            if(hix == 1) {
                values = [ values[1] - 3, values[1] ];
            }
            else {
                values = [ values[0], values[0] + 3 ];
            }
            if(values[0] <= min) {
                values[0] = min;
                values[1] = min + 3;
            }
            else if(values[1] >= max) {
                values[0] = max - 3;
                values[1] = max;
            }
            return values;
        }
        e.html('').slider({
            range: true,
            min: 0,
            max: days,
            values: [ Number(inputs.eq(0).val()), Number(inputs.eq(1).val())],
            slide: function(evt, ui) {
                var values = ui.values;
                var diff = values[1] - values[0];
                if(diff < 3) {
                    var w = $(this);
                    w.slider('values', cap_values(w, $(ui.handle), values));
                }
                else {
                    set_label(values);
                    inputs.eq(0).val(values[0]);
                    inputs.eq(1).val(values[1]);
                    $('input[type=text]', e.parent().next()).change();
                }
            },
            change: function(evt, ui) {
                if(!evt.originalEvent)
                    return;
                var w = $(this);
                var values = ui.values;
                var diff = values[1] - values[0];
                if(diff < 3) {
                    values = cap_values(w, $(ui.handle), values);
                    w.slider('values', values);
                }
                set_label(values);
                inputs.eq(0).val(values[0]);
                inputs.eq(1).val(values[1]);
                $('input[type=text]', e.parent().next()).change();
            }
        });
        set_label();
    };

    function calcTotal() {

        function _clearTotals() {
            $('fieldset .total', form)
                .data('total', 0)
                .children('b')
                .html('€ 0');
        }

        form.ajaxSubmit({
            url: '/p3/cart/calculator/',
            dataType: 'json',
            success: function(data, text, jqHXR) {
                _clearTotals()

                /*
                 * data contiene il totale generale, lo sconto ottenuto tramite
                 * coupon e il dettaglio dei costi dei singoli biglietti
                 */
                var feedback = $('.coupon .total');
                if (data.coupon) {
                    feedback.css('display', 'inline');
                    feedback.find('b').html('€ ' + (data.coupon || 0));
                }
                else {
                    feedback.css('display', 'none');
                }
                $('.grand.total b', form).html('€ ' + (data.total || 0));

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
                function update_total(parent, value) {
                    var e = $('.total', parent);
                    var total = e.data('total') + Number(value);
                    e.data('total', total);
                    e.children('b').html('€ ' + total.toFixed(2));
                }
                $(data.tickets).each(function() {
                    var code = this[0];
                    var params = this[1];
                    var total = this[2];
                    /*
                     * per tutti i biglietti, ad eccezioni delle prenotazioni
                     * alberghiere, posso limitarmi ad aggiungere il valore nel
                     * totale di sezione (identificato con la prima lettera del
                     * codice tariffa)...
                     */
                    var group = '';
                    switch(code.substr(0, 1)) {
                        case 'T':
                            if(code.length == 4)
                                group = 'T';
                            break;
                        case 'P':
                            group = 'P';
                            break;
                    }
                    switch(group) {
                        case 'T':
                            update_total($('.conference-tickets', form), total);
                            break;
                        case 'P':
                            update_total($('.partner-program', form), total);
                            break;
                        default:
                            update_total($('.other-goodies', form), total);
                            break;
                    }
                });
            },
            error: function(response) {
                var err = null;
                if(response.status == 400) {
                    try {
                        err = JSON.parse(response.responseText);
                    }
                    catch(_) {
                    }
                }

                _clearTotals();
                if(err == null) {
                    //alert(response.responseText);
                    return;
                }

                /* la validazione della form passata ha ritornato un errore,
                 * devo mostrare i messaggi accanto ai campi corrispondenti
                 */

                /* XXX: in teoria qualunque campo della form potrebbe avere
                 * problemi di validazione, in pratica solo quelli relativi
                 * alle prenotazioni alberghiere.
                 */

                for(var fname in err) {
                    switch(fname) {
                        case '__all__':
                            break;
                        default:
                            // ops qualcosa di inatteso
                            throw("invalid field");
                            break;
                    }
                }
                return;
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
        $('td.fare[data-recipient]', form).each(function() {
            var td = $(this);
            var recipient = td.attr('data-recipient');
            var e = ((recipient == "p") && personal) || ((recipient == "c") && !personal);
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
})(jQuery);
