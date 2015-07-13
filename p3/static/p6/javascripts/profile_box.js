function loadProfileData(p, callback) {
    var cached = p.data('profile-data');
    if(cached) {
        callback(cached);
        return;
    }
    var hurl = p.find('.person-card-picture a')
        .attr('href');

    var _ = hurl.split('/');
    _.reverse();
    if(!_[0])
        _.shift();
    var slug = _[0];

    var jurl = '/p3/p/profile/' + slug + '.json';
    $.getJSON(jurl, function(data) {
        p.data('profile-data', data);
        callback(data);
    });
}
/*
 * I link "see more" caricano il contenuto via ajax
 */
$('.tags a')
    .live('click', function(ev) {
        var e = $(this);
        var p = e.parents('.person-card');
        var tags = e.parents('.tags');
        tags.html('loading...');
        loadProfileData(p, function(data) {
            var h = [];
            for(var ix=0, ex=data.interests.length; ix<ex; ix++) {
                h.push('<span class="tag">' + data.interests[ix] + '</span>');
            }
            tags.html(h.join(' '));
        })
        return false;
    })
$('.person-card-bio a.see-more')
    .live('click', function(ev) {
        var e = $(this);
        var p = e.parents('.person-card');
        var bio = e.parents('.bio');
        bio.html('loading...');
        loadProfileData(p, function(data) {
            bio.html(data.bio);
        });
        return false;
    });
$('.user-message i')
    .live('click', function(ev) {
        var p = $(this).next();
        p.toggle();
        if(p.data('clicked') == 1)
            return;
        p.data('clicked', 1);
        if(user.tickets.length == 0) {
            p.html('<p>You need a conference ticket in order to send a private message</p>');
            return;
        }
        var form = $(''
            + '<form class="async" method="POST">'
            + ' <fieldset>'
            + '  <div class="field"><label>From: <strong>' + user.name +' &lt;' + user.email + '&gt;</strong></label></div>'
            + '  <div class="field"><label>Subject <input type="text" name="subject" /></label></div>'
            + '  <div class="field"><label>Message <textarea rows="3" name="message"></textarea></label></div>'
            + '  <button type="submit">Send an e-mail</button>'
            + ' </fieldset>'
            + '</form>'
        );
        var slug = p.parents('.person-card').attr('id');
        form.attr('action', '/p3/p/profile/' + slug + '/message');
        p.append(form);
        form.ajaxForm({
            beforeSubmit: function(data, form, options) {
                var check = {}
                for(var ix=0, ex=data.length; ix<ex; ix++) {
                    check[data[ix].name] = data[ix].value;
                }
                if(!check['subject'] || !check['message']) {
                    alert('Both fields are required');
                    return false;
                }
            },
            success: function(response, status, jhq, form) {
                var s = form.find('input[name=subject]').val();
                p.toggle().before('<p title="' + s + '">Message sent</p>');
                form.get(0).reset();
            }
        });
    });
