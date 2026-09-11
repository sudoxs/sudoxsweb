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
    useAltHeader: true,

    // HTML for the alternative header (shown only when useAltHeader=true)
    altHeaderHTML: `
        <header style="display:flex;align-items:center;justify-content:space-between;
                padding:.7rem 0 1.1rem;margin-bottom:1.5rem;
                border-bottom:1px solid var(--border, #232a23);gap:1rem;flex-wrap:wrap;">
            <a href="#/" style="color:var(--ink-bright,#e8ebe5);
                font-family:var(--font-display,sans-serif);
                font-size:clamp(1rem, 0.95rem + 0.3vw, 1.2rem);
                font-weight:900;letter-spacing:.13em;
                text-decoration:none;">
                <span style="color:var(--danger-bright,#cf4a50)">[</span>SUDOXS<span style="color:var(--danger-bright,#cf4a50)">]</span>
            </a>
            <span style="color:var(--ink-dim,#7a837a);
                font-size:clamp(0.7rem, 0.65rem + 0.25vw, 0.82rem);
                letter-spacing:.17em;">
                DOCUMENTATION MODE
            </span>
        </header>`,

    // Set to true to use a DIFFERENT footer on MD pages
    useAltFooter: true,

    // HTML for the alternative footer
    altFooterHTML: `
        <footer style="margin-top:4rem;padding-top:1.5rem;
                border-top:1px solid var(--border,#232a23);
                text-align:center;color:var(--ink-faint,#4a534b);
                font-size:clamp(0.68rem, 0.62rem + 0.25vw, 0.8rem);
                letter-spacing:.12em;">
            END OF DOCUMENT · <a href="#/" style="color:var(--danger-bright,#cf4a50);">RETURN TO ROOT</a>
        </footer>`,

    // Extra CSS classes added to <body> when viewing an MD file
    bodyClass: "viewing-md",
};
