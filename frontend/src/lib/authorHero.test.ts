/**
 * The author page's masthead (AuthorHero.svelte), held to design review #13.
 *
 * It used to be a dark band of the era's colour with the portrait printed as
 * a duotone, and this file measured that band's ink against every era over
 * every palette. The band is gone: the hero is the book page's light layout on
 * the page's own ground, so its text is the page's text (palettes.test holds
 * those), and the --hero-* tokens it used are measured there for the home hero
 * that still wears them. What is guarded here is the new rule itself.
 */
import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

const read = (p: string) => readFileSync(join(process.cwd(), 'src', p), 'utf-8');
const HERO = read('lib/components/AuthorHero.svelte').replace(/\/\*[\s\S]*?\*\/|<!--[\s\S]*?-->/g, '');
const PAGE = read('routes/authors/[slug]/+page.svelte').replace(/<!--[\s\S]*?-->/g, '');
const markup = (src: string) => src.replace(/<script[\s\S]*?<\/script>|<style[\s\S]*?<\/style>/g, '');

describe('author hero', () => {
	it('shows the real portrait: no duotone, no grayscale', () => {
		expect(markup(HERO)).not.toMatch(/duotone|grayscale/);
		expect(HERO).not.toMatch(/--duotone-hue|filter:\s*grayscale/);
	});

	it('sits on the page ground, not a dark slab', () => {
		expect(HERO).not.toMatch(/--hero-(tint|ink|gilt|mat)/);
	});

	it('the visible H1 is the person’s name; the long phrase is the title only', () => {
		const h1s = [...markup(PAGE).matchAll(/<h1[^>]*>([\s\S]*?)<\/h1>/g)].map((m) => m[1].trim());
		expect(h1s).toEqual(['{author.name}']);
		expect(PAGE).toMatch(/title="\{seoTitle\} — Ochorus"/);
	});
});
