CSS_FILES=./stylesheets/rock-hammer.scss:./stylesheets/all.css
CSS_FILES_IE8=./stylesheets/lte-ie8.scss:./stylesheets/lte-ie8.css

all: update updateie8

update:
	sass -f -t compact --update $(CSS_FILES)

updateie8:
	sass -f -t compact --update $(CSS_FILES_IE8)

watch:
	sass -g -l   --sourcemap --watch $(CSS_FILES)

clean:
	rm -r ./.sass-cache
	
