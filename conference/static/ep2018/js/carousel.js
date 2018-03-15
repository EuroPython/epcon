(function() {

    // This is double the speed for testing purposes,
    // on production we probably want something closer to 7s for carousel with
    // 2s animation
    var CAROUSEL_DELAY_IN_MILISECONDS = 3000;
    var ANIMATION_DELAY = 1000;
    var MINIMAL_WINDOW_WIDTH_FOR_CAROUSEL = 1024; // arbitrary width

    function carousel() {
        $('header img.carousel-image').first().appendTo('header').fadeOut(ANIMATION_DELAY);
        $('header img.carousel-image').first().fadeIn(ANIMATION_DELAY);

        setTimeout(carousel, CAROUSEL_DELAY_IN_MILISECONDS);
    }

    if($(window).width() > MINIMAL_WINDOW_WIDTH_FOR_CAROUSEL) {
        setTimeout(
            function() { $('header').css('background-image', 'none') },
            CAROUSEL_DELAY_IN_MILISECONDS
        );
        $('header img.carousel-image').first().fadeIn(ANIMATION_DELAY);
        setTimeout(carousel, CAROUSEL_DELAY_IN_MILISECONDS);
    }

})()
