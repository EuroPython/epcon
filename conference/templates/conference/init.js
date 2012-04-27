conference = {{ conference_data|safe }};

function _render_tags(tags, selected) {
    if(!selected)
        selected = [];

    var wrapper = $('<div class="all-tags"></div>');

    var category_wrappers = {};
    var reverse = {};
    for(var category in conference.tags) {
        // reverse map, tag -> category
        for(var ix=0; ix<conference.tags[category].length; ix++)
            reverse[conference.tags[category][ix]] = category;

        // category, trigger
        var trigger = $('<h2 class="toggle">' + category + '</h2>');
        trigger.click(function(e) {
            e.preventDefault();
            $(this).next().toggle();
        });
        wrapper.append(trigger);

        // wrapper for the category tags
        var w = $('<div></div>');
        w.hide();
        category_wrappers[category] = w;
        wrapper.append(w);
    }

    for(var ix=0; ix<tags.length; ix++) {
        if(Object.prototype.toString.call(tags[ix]) === '[object Array]') {
            var t = tags[ix][0];
            var label = tags[ix][1];
        }
        else {
            var t = tags[ix];
            var label = t;
        }
        var a = $('<a class="tag" href="#" data-tag="' + t + '">' + label + '</a>');
        var w = category_wrappers[reverse[t]];
        w.append(a);
        if(selected.indexOf(t) != -1) {
            a.addClass('selected');
            w.show();
        }
    }

    return wrapper;
}
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
                for(var tag in conference.taggeditems) {
                    if(tag.toLowerCase().indexOf(needle) != -1)
                        tags.push(tag);
                }
                showChoices(tags);
            }
        });
        if(conference) {
            var tags = [];
            for(var key in conference.taggeditems) {
                tags.push(key);
            }
            tags.sort(function(a, b) {
                var a = a.toLowerCase();
                var b = b.toLowerCase();
                return a == b ? 0 : (a < b ? -1 : 1);
            });
            tfields.each(function() {
                var tag_field = $(this);
                var wrapper = _render_tags(tags, tag_field.tagit('assignedTags'));
                wrapper.find('a.tag').click(function(e) {
                    e.preventDefault();
                    $(this)
                        .parents('.field')
                        .children('.tag-field')
                        .tagit('createTag', this.innerHTML);
                });
                tag_field.
                    parent()
                    .children('ul.tagit')
                    .after(wrapper);
            });
        }
    }
    var tfields = $('.readonly-tag-field');
    if(tfields.length && conference) {
        var tags = [];
        for(var key in conference.taggeditems) {
            if(conference.taggeditems[key]['talk'] > 0) {
                tags.push([key, key + ' (' + conference.taggeditems[key]['talk'] +')']);
            }
        }
        tags.sort(function(a, b) {
            var a = a[0].toLowerCase();
            var b = b[0].toLowerCase();
            return a == b ? 0 : (a < b ? -1 : 1);
        });
        tfields
            .not('[data-conference-init]')
            .attr('data-conference-init', '1')
            .each(function() {
                var tag_field = $(this);
                var selected = $(this).val().split(',');
                $(selected).each(function(ix, v) {
                    selected[ix] = v.replace(new RegExp('"', 'g'), '');
                });
                var wrapper = _render_tags(tags, selected);
                wrapper.find('a.tag').click(function(e) {
                    var e = $(this);
                    var input = e.parents('.field').children('input');
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
                });

                tag_field.after(wrapper);
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

