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
    var mfields = $('.markedit-widget', ctx);
    if(mfields.length) {
        mfields.markedit({
            'preview_markup': '<div class="markedit-preview cms ui-widget-content"></div>',
            'toolbar': {
                'layout': 'heading bold italic bulletlist | link quote code image '
            }
        }).blur();
    }
    $('.pseudo-radio').click(function(e) {
        var pseudo = $(this);
        var p = pseudo.parent();
        var input = $('input[type=hidden]', p);
        input.val(pseudo.attr('data-value'));
        input.change();
        $('.pseudo-radio', p).removeClass('checked');
        pseudo.addClass('checked');
    });
    $('.pseudo-radio-field input').each(function() {
        var initial = $(this).val();
        $('.pseudo-radio[data-value=' + initial + ']', $(this).parent()).click();
    });
}
$(function() {
    setup_conference_fields();
});

