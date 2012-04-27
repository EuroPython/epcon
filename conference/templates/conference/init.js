conference = {{ conference_data|safe }};

function select_tag(field, tag, mode) {
    mode = mode || "toggle";
    field = $(field);
    if(!field.hasClass('all-tags')) {
        field = field.next();
        if(!field.hasClass('all-tags'))
            return false;
    }

    var t = field.find('.tag[data-tag=' + tag + ']');
    if(!t.length)
        return false;

    var input = field
        .parents('.field')
        .children('input');

    if(mode == "exclusive") {
        field
            .find('.tag')
                .removeClass('selected')
                .end()
            .children('div')
                .hide()
        input.val('');
        mode = 'add';
    }
    if(mode == "toggle") {
        mode = input.val().indexOf(tag) == -1 ? 'add': 'remove';
    }
    var wrapper = t.parent();
    if(mode == "add") {
        t.addClass('selected');
        wrapper.show();
    }
    else if(mode == "remove") {
        t.removeClass('selected');
        /*
        if(wrapper.children('.tag.selected').length == 0) {
            wrapper.hide();
        }
        */
    }
    else {
        return false;
    }

    var v = input.val();
    var found = v.indexOf(tag) != -1;
    if(!found && mode == "add") {
        v = '"' + tag + '",' + v;
    }
    else if(found && mode == "remove") {
        var r = new RegExp('"' + tag + '",?');
        v = v.replace(r, '');
    }
    if(v.substr(v.length-1) == ',')
        v = v.slice(0, -1);

    input.val(v).change();

    return true;
}
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
        var trigger = $('<h2 class="tag-toggle">' + category + '</h2>');
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
function _setup_readonly_tag_field(tag_field) {
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

        var selected = tag_field.val().split(',');
        $(selected).each(function(ix, v) {
            selected[ix] = v.replace(new RegExp('"', 'g'), '');
        });
        var wrapper = _render_tags(tags, selected);
        wrapper.find('a.tag').click(function(e) {
            select_tag(tag_field, $(this).attr('data-tag'));
            return false;
        });

        tag_field.after(wrapper);
}
function setup_tag_field(field) {
    field = $(field);
    var check = field.data('data-conference-init');
    if(check)
        return;
    field.data('data-conference-init', 1);
    if(field.hasClass('tag-field')) {

    }
    else if(field.hasClass('readonly-tag-field')) {
        _setup_readonly_tag_field(field);
    }
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
    $('.readonly-tag-field').each(function() { setup_tag_field(this) });

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

