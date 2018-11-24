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
    },
    filterOut: function(c) {
        /*
         * django comment è abbastanza furbo da non inserire due volte lo
         * stesso commento (double posting), quindi c potrebbe avere un id già
         * presente
         */
        return $('#' + c.attr('id')).length == 0 ? c : null
    },
    _prepareForm: function(form, comment) {
        var opts = {
            beforeSubmit: function(formData, jqForm, options) {
                var $comment = jqForm.find('[name=comment]');
                var $name = jqForm.find('[name=name]');
                var $email = jqForm.find('[name=email]');

                var comment = $.trim($comment.val());
                var name = $.trim($name.val());
                var email = $.trim($email.val());

                var error = false;
                var $toFocus;

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
                }
            }, this)
        };
        if(comment) {
            opts.complete = function() { $(form).remove(); };
        }
        return form.ajaxForm(opts);
    },
    onCommentPostFailed: function(comment, message) {
        var lbl = 'Cannot post your comment';
        if(message)
            lbl += ' (' + message + ')';
        alert(lbl);
    }
};
