$(function() {
    $('.tag-field').tagit({
    	//availableTags: ['ciao', 'mondo']
    	tagSource: function(search, showChoices) {
    		var tags = conference ? conference.tags : [];
    		showChoices(tags);
        }
    });
});
