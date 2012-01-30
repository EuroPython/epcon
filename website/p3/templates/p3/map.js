{% load i18n %}
function initGMAP(mapId, show, zoom) {
    if(!show) {
        show = [
            'conf-hq',
            'pyevents',
            'hotel',
            'hotel_conv'
        ];
    }
    if(!zoom)
        zoom = 15;
    var icons = {
        'conf-hq': "{{ STATIC_URL }}p5/i/marker_pycon.png",
        'pyevents': "{{ STATIC_URL }}p5/i/marker_pycon.png",
        'hotel': "{{ STATIC_URL }}p5/i/marker_hotel.png",
        'hotel_conv': "{{ STATIC_URL }}p5/i/marker_hotel_conv.png"
    };

    var mapOptions = {
        'zoom': zoom || 15,
        // inizio con il duomo di Firenze, questo permette alla mappa di
        // renderizzarsi mentre scarico le coordinate dei luoghi da mostrare.
        'center': new google.maps.LatLng(43.773281, 11.25721),
        'mapTypeId': google.maps.MapTypeId.ROADMAP
    };
    var map = new google.maps.Map(document.getElementById(mapId), mapOptions);
    if($('#' + mapId).width() < 300) {
        /*
         * se la mappa è piccola riduco il testo del footer (con le indicazioni
         * del copyright) perché altrimenti sfonda il bordo della mappa
         */
        function reduceFontText() {
            $('#' + mapId + ' div span').each(function() {
                var s = $(this);
                if(s.text().indexOf('Map data') != -1) {
                    s.parent().css('font-size', '9px');
                }
            });
        }
        /*
         * ritardo l'esecuzione perché in questo momento gli elementi che sto
         * cercando non sono stati creati.
         */
        setTimeout(reduceFontText, 500);
    }
    var infos = [];
    var hqs = [];
    function addMarker() {
        var htype = this.type;
        if(htype == 'hotel' && this.affiliated)
            htype = 'hotel_conv';
        if($.inArray(htype, show) == -1)
            return;

        var marker = new google.maps.Marker({
            position: new google.maps.LatLng(this.lat, this.lng),
            map: map,
            title: this.name,
            icon: icons[htype]
        });
        var infowindow = new google.maps.InfoWindow({
            content: this.html
        });
        infos.push(infowindow);
        if(htype=='conf-hq')
            hqs.push(marker);
        google.maps.event.addListener(marker, 'click', function() {
            $.each(infos, function() { this.close() });
            infowindow.open(map, marker);
        });
    }
    $.getJSON('/conference/places/', function(data) {
        $.each(data, addMarker);
        if(hqs.length > 0)
            map.setCenter(hqs[0].position);
    });
}

