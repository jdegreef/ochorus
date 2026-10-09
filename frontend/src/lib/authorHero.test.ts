/**
 * The author page's masthead (AuthorHero.svelte) — measured, not trusted.
 *
 * Its band is an era hue mixed 28% into --hero-tint (the palette's night
 * shade), and its text is --hero-ink, the secondary lines at 85% opacity. An
 * era's hue is a mid-tone and every palette sets its own tint, so each pair is
 * computed here against WCAG AA rather than eyeballed on one author. The mat
 * under a portrait-less writer carries their initials in --hero-mat-ink over a
 * 16% wash of the era hue.
 */
import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { contrastRatio } from './coverArt';
import { ERA_HUE } from './eras';

const CSS = readFileSync(join(process.cwd(), 'src/app.css'), 'utf-8').replace(/\/\*[\s\S]*?\*\//g, '');
const rgb = (hex: string) => [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16));
const mix = (a: number[], b: number[], p: number) => a.map((v, i) => v * p + b[i] * (1 - p));

/** Every value a custom property is declared with anywhere in app.css. */
const declared = (prop: string): string[] =>
	[...CSS.matchAll(new RegExp(`${prop}:\\s*(#[0-9a-fA-F]{6})\\s*;`, 'g'))].map((m) => m[1]);

describe('author hero', () => {
	const tints = declared('--hero-tint');
	const [ink] = declared('--hero-ink');
	const [mat] = declared('--hero-mat');
	const [matInk] = declared('--hero-mat-ink');

	it('finds the tokens it measures', () => {
		expect(tints.length).toBeGreaterThan(1);
		for (const v of [ink, mat, matInk]) expect(v).toMatch(/^#[0-9a-f]{6}$/i);
	});

	it('hero ink clears 4.5:1 on every era over every palette tint, full and at 85%', () => {
		const failures: string[] = [];
		for (const [era, hue] of Object.entries(ERA_HUE)) {
			for (const tint of tints) {
				const ground = mix(rgb(hue), rgb(tint), 0.28);
				const full = contrastRatio(rgb(ink), ground);
				const soft = contrastRatio(mix(rgb(ink), ground, 0.85), ground);
				if (full < 4.5 || soft < 4.5) failures.push(`${era} over ${tint}: ${full.toFixed(2)} / ${soft.toFixed(2)}`);
			}
		}
		expect(failures, failures.join('\n')).toEqual([]);
	});

	it('the mat initials clear 4.5:1 on every era wash', () => {
		for (const [era, hue] of Object.entries(ERA_HUE)) {
			const ratio = contrastRatio(rgb(matInk), mix(rgb(hue), rgb(mat), 0.16));
			expect(ratio, era).toBeGreaterThanOrEqual(4.5);
		}
	});
});
