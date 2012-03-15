conference = {{ conference_data|safe }};

function setup_conference_fields(ctx) {
    ctx = ctx || document;
    var tfields = $('.tag-field', ctx);
    if(tfields.length) {
        tfields.tagit({
            tagSource: function(search, showChoices) {
                if(!conference)
                    return;
                var needle = search.term.toLowerCase();
                var tags = [];
                for(var ix=0; ix<conference.tags.length; ix++) {
                    var t = conference.tags[ix];
                    if(t.toLowerCase().indexOf(needle) != -1)
                        tags.push(t);
                }
                showChoices(tags);
            }
        });
        if(conference) {
            var wrapper = $('<ul class="all-tags"></ul>');
            wrapper.insertAfter(tfields.parent().children('ul.tagit').eq(0));
            for(var ix=0; ix<conference.tags.length; ix++) {
                var t = conference.tags[ix];
                wrapper.append('<a class="tag" href="#">' + t + '</a>');
            }
            $('a.tag', wrapper).click(function(e) {
                e.preventDefault();
                tfields.tagit('createTag', $(this).text());
            });
        }
    }
    var tfields = $('.readonly-tag-field');
    if(tfields.length && conference) {
        var wrapper = $('<div class="all-tags"></div>');
        var tags = [];
        for(var key in conference.taggeditems) {
            if(conference.taggeditems[key]['talk'] > 0) {
                tags.push(key);
            }
        }
        tags.sort();
        for(var ix=0; ix<tags.length; ix++) {
            var t = tags[ix];
            var count = conference.taggeditems[t]['talk'];
            var a = $('<a class="tag" href="#" data-tag="' + t + '">' + t + ' (' + count + ')' + '</a>');
            a.click(function(e) {
                var e = $(this);
                var input = e.parent().prev();
                var name = e.attr('data-tag');
                var v = input.val();
                if(v.indexOf(name) == -1) {
                    v = '"' + name + '",' + v;
                    e.addClass('selected');
                }
                else {
                    var r = new RegExp('"' + name + '",?');
                    v = v.replace(r, '');
                    e.removeClass('selected');
                }
                if(v.substr(v.length-1) == ',')
                    v = v.slice(0, -1);
                input.val(v).change();
                return false;
            })
            wrapper.append(a);
        }
        tfields
            .not('[data-conference-init]')
            .attr('data-conference-init', '1')
            .after(wrapper)
            .each(function() {
                var tags = $(this).val().split(',');
                $(tags).each(function(ix, v) {
                    tags[ix] = v.replace(new RegExp('"', 'g'), '');
                });
                $(this)
                    .next()
                    .children('a.tag')
                    .each(function() {
                        var e = $(this);
                        if(tags.indexOf(e.attr('data-tag')) != -1)
                            e.addClass('selected');
                    });
            });
    }
    var mfields = $('.markedit-widget', ctx);
    if(mfields.length) {
        mfields.markedit({
            'preview_markup': '<div class="markedit-preview cms ui-widget-content"></div>',
            'toolbar': {
                'layout': 'heading bold italic bulletlist | link quote code image '
            }
        }).blur();
    }
    $('.pseudo-radio', ctx).click(function(e) {
        var pseudo = $(this);
        var p = pseudo.parent();
        var input = $('input[type=hidden]', p);
        input.val(pseudo.attr('data-value'));
        input.change();
        $('.pseudo-radio', p).removeClass('checked');
        pseudo.addClass('checked');
    });
    $('.pseudo-radio-field input', ctx).each(function() {
        var initial = $(this).val();
        $('.pseudo-radio', $(this).parent()).removeClass('checked');
        $('.pseudo-radio[data-value=' + initial + ']', $(this).parent()).addClass('checked');
    });
}
$(function() {
    setup_conference_fields();
});

