/**
 * Whether the home hero's own search field is on screen (design review
 * 2026-11, #5). While it is, the header's search pill is a second search box
 * 150px above the first, so the layout hides it; once the hero field scrolls
 * away (or on any other page, where nothing sets this) the pill is back.
 */
class HeroSearch {
	visible = $state(false);
}

export const heroSearch = new HeroSearch();
