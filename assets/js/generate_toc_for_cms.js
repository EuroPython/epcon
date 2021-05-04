// Build a table of contents based on the headers in the CMS section
// of the page and place it into a <div id="toc">, if available.

function addTOC() {
  var div_toc = $("#toc");
  if (!div_toc) return;
  var toc =
    "<p role='navigation' class='table-of-contents'>" +
    "<h3>Table of contents</h3>" +
    "<ul>";
  var newLine, el, title, link;

  $("div.epcms_content")
    .find("h1, h2, h3, h4")
    .each(function() {
      var header = $(this);
      var title = header.text();
      var header_id = title
        .replace(/[ \n\t:&\/\$\xa0()]/g, "-")
        .replace(/--+/g, "-")
        .replace(/[\?!,.\'\"]|^-|-$/g, "");
      header.attr("id", header_id);
      toc +=
        '<li class="toc-li table-of-contents-' +
        header.prop("tagName") +
        '"><a href="#' +
        encodeURIComponent(header_id) +
        '">' +
        title +
        "</a></li>";
    });
  toc += "</ul>" + "</p>";
  div_toc.replaceWith(toc);
  $(document).scrollTop( $($(location).attr("hash")).offset().top );
}
$(document).ready(addTOC);
