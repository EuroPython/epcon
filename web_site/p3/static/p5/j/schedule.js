(function($) {
    $.fn.extend({
        'events': function() {
            return this.filter('.event');
        },
        'highlight': function() {
            return this.events()
                .removeClass('dimmed')
                .addClass('highlighted');
        },
        'dim': function() {
            return this.events()
                .removeClass('highlighted')
                .addClass('dimmed');
        },
        'removeDimHighlight': function() {
            return this.events()
                .removeClass('dimmed highlighted')
        },
        'byTag': function(tag) {
            return this.events()
                .find('.tag:contains(' + tag + ')')
                .parents('.event')
        }
    });
})(jQuery);

function highlight_chart() {
    var slices = {};
    var srex = /time-(\d+)/;
    $('.event').dim()
    $('.track')
        .each(function() {
            var track = $(this);
            var sch = track.parents('.schedule').attr('id');
            if(!(sch in slices)) {
                var sslices = {};
                slices[sch] = sslices;
            }
            else {
                var sslices = slices[sch];
            }
            track.children('.event[data-talk]')
                .each(function() {
                    var start = parseInt(this.className.match(srex)[1]);
                    if(!(start in sslices)) {
                        sslices[start] = [];
                    }
                    sslices[start].push($(this));
                });
        })
    $.each(slices, function(schedule, subslice) {
        $.each(subslice, function(key, events) {
            var kvotes = [];
            for(var ix=0; ix<events.length; ix++) {
                var tid = events[ix].attr('data-talk');
                kvotes.push([ user_votes[tid] || 0, events[ix] ]);
            }
            kvotes.sort(function(a,b) { return a[0] - b[0]; }).reverse();
            var max = kvotes[0][0];
            if(max > 5) {
                for(var ix=0; ix<kvotes.length; ix++) {
                    var vote = kvotes[ix][0];
                    if(vote == max) {
                        kvotes[ix][1].highlight();
                    }
                }
            }
        });
    });
}
function highlighter(mode) {
    if($(document).data('highlighter') == mode)
        mode = '';
    switch(mode) {
        case 'chart':
            highlight_chart();
            break;
        default:
            $('.event').removeDimHighlight();
    }
    $(document).data('highlighter', mode);
}
(function() {
    var nav = $('#schedule-navigator');
    var options = nav.children('div');
    options
        .find('.disabled')
            .bind('click', function(ev) { ev.stopImmediatePropagation(); return false;})
            .end()
        .children('a')
            .bind('click', function(ev) {
                var e = $(this);
                var target = e.parent().children('div');
                var visible = !target.is(':hidden');
                options
                    .removeClass('selected')
                    .children('div')
                        .hide();
                if(!visible)
                    target
                        .show()
                        .parent()
                        .addClass('selected');
                return false;
            })
            .end()
        .children('div')
            .prepend('' +
                '<div class="close">' +
                '   <a href="#"><img src="' + STATIC_URL + 'p5/i/close.png" width="24" /></a>' +
                '</div>')
            .find('.close')
                .bind('click', function(ev) {
                    $(this).parent().hide();
                    return false;
                })

    options
        .find('.track-toggle')
            .bind('click', function(ev) {
                var e = $(this);
                var tracks = $([]);
                $(e.attr('data-tracks').split(',')).each(function(ix, val) {
                    tracks = tracks.add($('.track[data-track=' + val + ']'));
                })
                var visible = tracks.is(':hidden');
                /*
                 * nascondere/mostrare le track è semplice, il problema è
                 * accorciare gli eventi a sale unificate
                 */
                if(visible) {
                    tracks.show();
                    e.removeClass('filter-active');
                }
                else {
                    tracks.hide();
                    e.addClass('filter-active');
                }
                var sch = tracks.eq(0).parents('.schedule');
                var direction = sch.parent().get(0).className.indexOf('vertical') != -1 ? 'v' : 'h';
                var offset = direction == 'v' ? tracks.width() : tracks.height();
                if(!visible)
                    offset *= -1;
                /*
                 * devo accumulare le modifiche invece che applicarle
                 * subito perché c'è una transizione css e i metodi
                 * .width/.height non mi riportano la dimensione
                 * corretta fino a quando non è terminata l'animazione
                 */
                var sizes = {};
                tracks.each(function() {
                    var t = $(this)
                    /*
                     * gli eventi da manipolare sono tutti quelli presenti
                     * nelle track precedenti che coinvolgano anche la track corrente
                     */
                    var previous = t.prevAll('.track');
                    previous
                        .each(function(tix, val) {
                            /*
                             * mi interessano solo gli elementi di questa track
                             * che vanno a toccare una delle track manipolate
                             */
                            $(this)
                                .children('.event')
                                .not('.tracks-1')
                                .filter(function(ix) {
                                    var match = this.className.match(/tracks-(\d)/);
                                    if(!match)
                                        return false;
                                    return parseInt(match[1]) + (previous.length - tix -1) > previous.length;
                                })
                                .each(function() {
                                    var evt = $(this);
                                    if(!(this.id in sizes))
                                        sizes[this.id] = direction == 'v' ? evt.outerWidth() : evt.outerHeight();
                                    sizes[this.id] += offset;
                                });
                        });
                });
                for(var key in sizes) {
                    if(direction == 'v')
                        $(document.getElementById(key)).width(sizes[key]);
                    else
                        $(document.getElementById(key)).height(sizes[key]);
                }
                return false;
            })
        .end()
    .find('.highlight-chart')
        .each(function(ix, val) {
            if($.isEmptyObject(user_votes)) {
                $(this)
                    .addClass('disabled')
                    .after(' <a href="#" title="You have not participated to the community vote">?</a>');
            }
            else {
                $(this).bind('click', function(ev) {
                    highlighter('chart');
                    return false;
                })
            }
        })
})();
(function() {
    var user_interest_toolbar = '' +
    '   <div class="talk-interest">' +
    '       <a class="up" href="#" />' +
    '   </div>' +
    '';

    function expose(e) {
        e.addClass('exposed');
        e.trigger('exposed');
    }
    function unexpose(e) {
        e.removeClass('exposed');
        var dim = e.data('original');
        if(dim) {
            e.width(dim.width);
            e.height(dim.height);
            e.css('left', dim.left);
            e.css('top', dim.top);
        }
    }
    function event_url(base, evt) {
        var sch = evt.parents('.schedule');
        return base
            .replace('0', evt.attr('data-id'))
            .replace('_S_', sch.attr('id'))
            .replace('_C_', sch.parent().attr('data-conference'));
    }
    function update_booking_status(evt) {
        var be = $('<div class="book-event maximized">loading...</div>');
        $('.book-event', evt).remove();
        $('.tools', evt).append(be);
        var full = false;
        for(var ix=0; ix<user_tickets.length; ix++) {
            var t = user_tickets[ix];
            if(t[1] == 'conference' && t[2].substr(2, 1) == 'S') {
                full = true;
                break;
            }
        }
        if(!full) {
            be.html('<div class="restricted"><a href="/training">Restricted access</a></div>');
            return;
        }
        var base = "/conference/schedule/_C_/_S_/0/booking";
        $.get(event_url(base, evt), function(data) {
            if(data.user) {
                be.html('<div class="cancel"><a href="#">Cancel booking</a></div>');
            }
            else {
                if(data.available) {
                    be.html('<div class="book"><a href="#">Book this event</a></div>');
                }
                else {
                    be.html('<div class="sold-out">Sold out</div>');
                }
            }
            sync_event_book_status(evt, data);
        }, 'json');
    }
    function sync_event_book_status(evt, value) {
        evt.find('.info').remove();
        if(value.user) {
            evt.append(''
                + '<div class="info booked">'
                + ' BOOKED'
                + ' &bull;'
                + ' BOOKED'
                + ' &bull;'
                + ' BOOKED'
                + '</div>');
        }
        else {
            if(value.available > 0) {
                evt.append(''
                    + '<div class="info available">'
                    + ' AVAILABLE &bull; ' + value.available + ' SEATS LEFT'
                    + ' &bull;'
                    + ' AVAILABLE &bull; ' + value.available + ' SEATS LEFT'
                    + '</div>');
            }
            else {
                evt.append(''
                    + '<div class="info sold-out">'
                    + ' SOLD OUT'
                    + ' &bull;'
                    + ' SOLD OUT'
                    + ' &bull;'
                    + ' SOLD OUT'
                    + '</div>');
            }
        }
    }
    // eseguo la richiesta ajax prima della manipolazione del DOM, in questo
    // modo le due operazioni dovrebbero procedere parallelamente.
    (function() {
        $.getJSON('/conference/schedule/ep2012/events/booking', function(data) {
            $.each(data, function(key, value) {
                sync_event_book_status($('#e' + key), value);
            });
        });
    })();
    $('.track[data-track=training1] .event, .track[data-track=training2] .event')
        .bind('exposed', function(ev) {
            update_booking_status($(this));
            return false;
        });
    $('.book-event a').live('click', function(ev) {
        var b = $(this).parent();
        var base = "/conference/schedule/_C_/_S_/0/booking";
        var evt = b.parents('.event');
        var url = event_url(base, evt);
        if(b.hasClass('book')) {
            if(confirm('You are booking a seat in this training. You can cancel your booking at any time if you change your mind, to leave your seat available for someone else.')) {
                $.ajax({
                    url: url,
                    type: 'POST',
                    data: {
                        value: 1
                    },
                    success: function() {
                        update_booking_status(evt);
                    },
                    error: function(xhr, status, error_) {
                        var msg = 'Cannot proceed';
                        switch(xhr.responseText) {
                            case 'sold out':
                                msg = 'Training full';
                                break;
                            case 'time conflict':
                                msg = 'Another training booked in this time slot';
                                break;
                            case 'ticket error':
                                msg = 'Restricted access';
                                break;
                        }
                        alert(msg);
                    }
                });
            }
        }
        else if(b.hasClass('cancel')) {
            if(confirm('Are you sure to cancel your reservation?')) {
                $.ajax({
                    url: url,
                    type: 'POST',
                    data: {},
                    success: function() {
                        update_booking_status(evt);
                    }
                });
            }
        }
        else {
            return true;
        }
        return false;
    });
    $('.event')
        .filter(function(ix) {
            // escludo gli elementi "strutturali", non devo interagirci
            var e = $(this);
            return !e.hasClass('special') && !e.hasClass('break');
        })
        .filter('[data-talk]')
            .prepend('' +
                '<div class="maximized close-event">' +
                '   <a href="#"><img src="' + STATIC_URL + 'p5/i/close.png" width="24" /></a>' +
                '</div>')
            .bind('click', function(ev) {
                var e = $(this);
                if(e.hasClass('exposed'))
                    return;
                $('.exposed')
                    .not(e)
                    .each(function() { unexpose($(this)) });
                expose(e);
            })
            .find('a')
                .bind('click', function(ev) {
                    /*
                    * non voglio seguire i link su un evento collassato
                    */
                    var evt = $(this).parents('.event');
                    if(!evt.hasClass('exposed'))
                        ev.preventDefault();
                    return true;
                })
                .end()
            .find('.close-event a')
                .bind('click', function(ev) {
                    unexpose($(this).parents('.event'));
                    return false;
                })
                .end()
            .bind('exposed', function(ev) {
                var e = $(this);
                if(!e.data('loaded')) {
                    var talk = $('h3.name a', e).attr('href');
                    if(talk) {
                        var ab = $('.abstract', e)
                            .text('loading...');
                        $.ajax({
                            url: talk + '.xml',
                            dataType: 'xml',
                            success: function(data, text, xhr) {
                                ab.html($('talk abstract', data).html());
                            }
                        });
                    }
                    e.data('loaded', 1);
                }
            })
            .end()
        .each(function(ix, val) {
            var e = $(this);
            var tools = e.children('.tools');
            if(user_authenticated) {
                var tid = e.attr('data-talk');
                if(tid && tid in user_votes) {
                    tools.append('<div class="maximized talk-vote">' + user_votes[tid] + '/10</div>');
                }

                var track = e.parents('.track').attr('data-track');
                if(track != 'training1' && track != 'training2') {
                    var i = user_interest[e.attr('data-id')];
                    if(i == 1) {
                        e.addClass('interest-up');
                    }
                    else if(i == -1) {
                        e.addClass('interest-down');
                    }
                    tools.append(user_interest_toolbar);
                    if(i == 1) {
                        tools.find('a.up').addClass('active');
                    }
                    else if(i == -1) {
                        tools.find('a.down').addClass('active');
                    }
                }
            }
            var t0 = Date.now();
            /*
             * aggiunta elisione
             */
            var name = e.find('.name a');
            if(name.length) {
                // numero di linee visibili
                var lh = parseFloat(name.css('line-height'));
                var lines = Math.floor((e.height() - name.position().top) / lh);
                // nuova altezza del tag a
                var h = lines * lh;
                if(h < name.height()) {
                    name.truncateText(h);
                }
            }
        })
        .find('.toggle-notice')
            .bind('click', function(ev) {
                $(this)
                    .parents('.event')
                    .children('.notice')
                    .css('left', 0)
                return false;
            })
            .end()
        .find('.notice')
            .bind('click', function(ev) {
                $(this).css('left', '100%');
                return false;
            })
            .end()
        .find('.talk-interest a')
            .bind('click', function(ev) {
                var base = "/conference/schedule/_C_/_S_/0/interest"
                var e = $(this);
                var evt = e.parents('.event');
                var url = event_url(base, evt);
                var up = e.hasClass('up');
                if(!e.hasClass('active')) {
                    var val = up ? 1 : -1;
                }
                else {
                    var val = 0;
                }
                $.ajax({
                    url: url,
                    type: 'POST',
                    data: {
                        interest: val
                    },
                    success: function() {
                        evt.removeClass('interest-up interest-down');
                        var wrap = e.parents('.talk-interest');
                        $('a', wrap).removeClass('active');
                        if(val > 0) {
                            $('a.up', wrap).addClass('active');
                            evt.addClass('interest-up');
                        }
                        else if(val < 0) {
                            $('a.down', wrap).addClass('active');
                            evt.addClass('interest-down');
                        }
                    }
                });
                return false;
            })
            .end()
        .find('.tag')
            .bind('click', function(ev) {
                $('.event')
                    .removeDimHighlight()
                    .byTag($(this).text())
                    .highlight();
                return false;
            })
    $('.special > *:first-child').verticalAlign();
})();
