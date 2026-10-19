/* ═══════════════════════════════════════════════════════════════════
   md-layout.js — Customize header & footer for .md file pages
   ═══════════════════════════════════════════════════════════════════

   This file lets you change how .md file pages look WITHOUT editing index.html.
   Just edit the object below and make sure this file is in the same folder as index.html.

   Usage in index.html: add this script tag AFTER the main SX script:
   <script src="md-layout.js"></script>

   Then index.html will detect `window.SX_MD_LAYOUT` and use it.
   ═══════════════════════════════════════════════════════════════════ */

window.SX_MD_LAYOUT = {

    // Set to true to use a DIFFERENT header on MD pages
    useAltHeader: false,

    // HTML for the alternative header (shown only when useAltHeader=true)
    altHeaderHTML: '',

    // Set to true to use a DIFFERENT footer on MD pages
    useAltFooter: false,

    // HTML for the alternative footer
    altFooterHTML: '',

    // Extra CSS classes added to <body> when viewing an MD file
    bodyClass: "viewing-md",
};
