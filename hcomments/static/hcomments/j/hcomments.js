function bind(f, scope) {
    function wrapper() {
        return f.apply(scope, arguments);
    }
    return wrapper;
};

function isEmail(email) {
  var regex = /^([a-zA-Z0-9_.+-])+\@(([a-zA-Z0-9-])+\.)+([a-zA-Z0-9]{2,4})+$/;
  return regex.test(email);
}

hcomments = {
    comments: function(o) {
        this.form = o.form;
        this.wrapper = o.wrapper;
        this.comments = o.comments;
        this.remove = o.remove || '';

        this.form.append('<input type="hidden" name="async" value="1" />');
        this._prepareForm(o.form);
        this.addRemoveLink();
        this.addReplyLink();
    },
    filterOut: function(c) {
        /*
         * django comment è abbastanza furbo da non inserire due volte lo
         * stesso commento (double posting), quindi c potrebbe avere un id già
         * presente
         */
        return $('#' + c.attr('id')).length == 0 ? c : null
    },
    addRemoveLink: function(target) {
        if(!this.remove)
            return;
        if(!target)
            target = $('li.user-comment');
        $('<span><a href="#" class="remove-comment">Remove</a> | </span>')
            .click(bind(this._onRemoveComment, this))
            .insertBefore($('strong', target));
    },
    _onRemoveComment: function(e) {
        e.preventDefault();
        if(confirm('Are you sure?')) {
            var p = $(e.target).parents('li');
            var id = p.attr('id').split('-')[1];
            $.post(this.remove, { cid: id })
            p.hide("slow", function() { $(this).remove(); });
        }
    },
    addReplyLink: function(target) {
        if(!target)
            target = this.comments;
        $('<span><a href="#" class="reply-comment">Reply</a> | </span>')
            .click(bind(this._onReplyComment, this))
            .insertBefore($('strong', target));
    },
    _onReplyComment: function(e) {
        e.preventDefault();
        var p = $(e.target).parents('li');
        if($('form', p).length)
            return;
        $('li.replying form').remove();
        $('li.replying').removeClass('replying');
        p.addClass('replying');
        var id = p.attr('id').split('-')[1];
        var form = this.form.clone();
        $('input[name="parent"]', form).val(id);
        $('<button>Cancel</button>')
            .appendTo($('div.buttons', form))
            .click(function(e) {
                e.preventDefault();
                form.remove();
                p.removeClass('replying');
            });
        this
            ._prepareForm(form, p)
            .appendTo(p);
    },
    _prepareForm: function(form, comment) {
        var opts = {
            beforeSubmit: function(formData, jqForm, options) {
                var $comment = jqForm.find('[name=comment]');
                var $name = jqForm.find('[name=name]');
                var $email = jqForm.find('[name=email]');
                var $captcha = jqForm.find('[name=recaptcha_response_field]');

                var comment = $.trim($comment.val());
                var name = $.trim($name.val());
                var email = $.trim($email.val());
                var captcha = $.trim($captcha.val());

                var error = false;
                var $toFocus;

                if ($captcha.length > 0 && captcha === '') {
                    error = true;

                    $toFocus = $captcha.addClass('error');
                    $('#recaptcha_widget_div').addClass('error');
                }

                if ($email.length > 0 && (email === '' || !isEmail(email))) {
                    error = true;

                    $toFocus = $email.addClass('error');
                }

                if ($email.length > 0 && name === '') {
                    error = true;

                    $toFocus = $name.addClass('error');
                }

                if (comment === '') {
                    error = true;

                    $toFocus = $comment.addClass('error');
                }

                if ($toFocus) {
                    $toFocus.focus();
                }

                return !error;
            },
            error: bind(function(request, textStatus, errorThrown) {
                if(request.status == 403) {
                    if(request.responseText == 'captcha')
                        this.onCaptchaFailed(null);
                    else
                        this.onCommentModerated(null);
                }
                else
                    this.onCommentPostFailed(null, request.responseText);
            }, this),
            success: bind(function(data, textStatus) {
                var data = this.filterOut($(data));
                if(data) {
                    data.hide();
                    if(comment) {
                        comment.after(data);
                    }
                    else {
                        /*
                         * se per qualche motivo il wrapper dei commenti non
                         * dovesse esister ricarico la pagina, almeno l'utente
                         * riceve un po' di feedback.
                         */
                        if(!this.wrapper.length) {
                            document.location.reload();
                            return;
                        }
                        else
                            data.appendTo(this.wrapper);
                    }
                    data.fadeIn("slow");
                    this.addRemoveLink(data);
                    this.addReplyLink(data);
                }
            }, this)
        };
        if(comment) {
            opts.complete = function() { $(form).remove(); };
        }
        return form.ajaxForm(opts);
    },
    onCaptchaFailed: function(comment) {
        alert('You are not human');
    },
    onCommentModerated: function(comment) {
        alert('Your comment has been moderated');
    },
    onCommentPostFailed: function(comment, message) {
        var lbl = 'Cannot post your comment';
        if(message)
            lbl += ' (' + message + ')';
        alert(lbl);
    }
};
