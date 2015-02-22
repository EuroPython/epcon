/*
 * Adding this to a javascript file that is included on your site will ensure
 * that AJAX POST requests that are made via jQuery will not be caught by the
 * CSRF protection.
 *
 * https://docs.djangoproject.com/en/dev/ref/contrib/csrf/#ajax
 */
$(document).ajaxSend(function(event, xhr, settings) {
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
    function sameOrigin(url) {
        // url could be relative or scheme relative or absolute
        var host = document.location.host; // host + port
        var protocol = document.location.protocol;
        var sr_origin = '//' + host;
        var origin = protocol + sr_origin;
        // Allow absolute or scheme relative URLs to same origin
        return (url == origin || url.slice(0, origin.length + 1) == origin + '/') ||
            (url == sr_origin || url.slice(0, sr_origin.length + 1) == sr_origin + '/') ||
            // or any other URL that isn't scheme relative or absolute i.e relative.
            !(/^(\/\/|http:|https:).*/.test(url));
    }
    function safeMethod(method) {
        return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
    }

    if (!safeMethod(settings.type) && sameOrigin(settings.url)) {
        xhr.setRequestHeader("X-CSRFToken", getCookie('csrftoken'));
    }
});

/*
 * Update the selection status of one or more tags.
 * `field` is the input field (or the ".all-tags" tag)
 * `tags` is the tag (or an array of) on which operate
 * `mode` is the action to perform:
 *  - exclusive
 *      select only the specified tags
 *  - toggle
 *      select/unselect the tags according to the current status
 *  - add
 *      select the tags
 *  - remove
 *      unselect the tags
 **/
function select_tag(field, tags, mode) {
    mode = mode || "toggle";
    if(mode != "toggle" && mode != "exclusive" && mode != "add" && mode != "remove")
        return false;

    if(Object.prototype.toString.call(tags) != '[object Array]') {
        tags = [ tags ];
    }

    field = $(field);
    if(!field.hasClass('all-tags')) {
        field = field.next();
        if(!field.hasClass('all-tags'))
            return false;
    }

    var t = $();
    for(var ix=0, ex=tags.length; ix<ex; ix++)
        t = t.add($('.tag[data-tag=' + tags[ix] + ']'));
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
    t.each(function() {
        var lmode = mode;
        var e = $(this);
        var tag = e.attr('data-tag');
        if(lmode == "toggle") {
            lmode = input.val().indexOf(tag) == -1 ? 'add': 'remove';
        }
        var wrapper = e.parent();
        if(lmode == "add") {
            e.addClass('selected');
            wrapper.show();
        }
        else {
            e.removeClass('selected');
            /*
            if(wrapper.children('.tag.selected').length == 0) {
                wrapper.hide();
            }
            */
        }

        var v = input.val();
        var found = v.indexOf(tag) != -1;
        if(!found && lmode == "add") {
            v = '"' + tag + '",' + v;
        }
        else if(found && lmode == "remove") {
            var r = new RegExp('"' + tag + '",?');
            v = v.replace(r, '');
        }
        if(v.substr(v.length-1) == ',')
            v = v.slice(0, -1);

        input.val(v);
    });

    input.change();

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
        var trigger = $('<h2 class="tag-toggle">' + (category || 'Other') + '</h2>');
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
        var counter = tag_field.parents('[data-conference-tags-counter]').attr('data-conference-tags-counter');
        for(var key in conference.taggeditems) {
            if(!counter) {
                tags.push([key, key]);
            }
            else if(conference.taggeditems[key][counter] > 0) {
                tags.push([key, key + ' (' + conference.taggeditems[key][counter] +')']);
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
                        .parents('.all-tags')
                            .prevAll('.tag-field')
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
