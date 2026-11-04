// dungeonOS for Firefox: preferences the theme needs. Firefox reads this at every start and
// it overrides prefs.js, so these can't drift. Linked into the profile by firefox/install.sh.

// read chrome/userChrome.css and chrome/userContent.css
user_pref("toolkit.legacyUserProfileCustomizations.stylesheets", true);

// the page colour before a site paints, and for pages with no colours of their own
// (blank tabs, plain text, images): bg #1A1816 and fg #C8B8A0 instead of Firefox's #1C1B22
user_pref("browser.display.background_color.dark", "#1A1816");
user_pref("browser.display.foreground_color.dark", "#C8B8A0");

// find in page: the current match in brass, "Highlight All" matches on the band
user_pref("ui.textSelectAttentionBackground", "#A88A5B");
user_pref("ui.textSelectAttentionForeground", "#1A1816");
user_pref("ui.textHighlightBackground", "#463D34");
user_pref("ui.textHighlightForeground", "#DDD0BD");
