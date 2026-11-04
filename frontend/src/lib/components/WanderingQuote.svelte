<script lang="ts">
	import { citeLine, quoteHref, type SavedQuote } from '$lib/library-public';
	import { localizeHref } from '$lib/href';
	import { featuredPool } from '$lib/quotePool';
	import QuoteText from '$lib/components/QuoteText.svelte';

	/**
	 * The footer's wandering quote: a quill by the tagline. Pressed, a small
	 * scroll unrolls beneath it with a line from one of the library's writers
	 * (the featured pool HomeQuote also draws from), its author and its place
	 * in the work, each a way in. Pressed again, the quill wanders to another
	 * line; "Roll it up" puts the scroll away.
	 *
	 * English only, as the quotations are (an English hub — see the footer's
	 * Discover column), so its few words are plain English rather than catalogue
	 * keys; the footer renders it only for English readers. Nothing is fetched
	 * until the quill is pressed: the footer is on every page.
	 */
	let quote = $state<SavedQuote | null>(null);
	// Bumped per quotation, so each one unrolls afresh.
	let turn = $state(0);
	let busy = $state(false);
	// The last press found no quotations (offline, the API down): said so.
	let dry = $state(false);
	let quill = $state<HTMLButtonElement>();

	async function wander() {
		if (busy) return;
		busy = true;
		try {
			const pool = await featuredPool();
			// Somewhere new each time: never the line already showing (unless
			// it is the only one there is).
			const fresh = pool.filter((q) => q.slug !== quote?.slug);
			const from = fresh.length ? fresh : pool;
			if (!from.length) throw new Error('no quotations');
			quote = from[Math.floor(Math.random() * from.length)];
			dry = false;
			turn++;
		} catch {
			dry = true;
		} finally {
			busy = false;
		}
	}
</script>

<div class="wandering">
	<button
		bind:this={quill}
		type="button"
		class="quill"
		aria-expanded={quote !== null}
		aria-controls="wandering-quote"
		aria-busy={busy}
		onclick={wander}
	>
		<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" focusable="false">
			<path
				class="feather"
				d="M20.5 3.2c-5.6.4-10.4 4.4-12.2 10.3l-1 3.4 1.4-.6c.9-2.6 2.3-4.6 4.3-6.1.6 1 1.9 1.4 3.3.9-.8-.4-1.3-.9-1.6-1.6 2.5-.9 4.3-2.8 5.1-5.2-.9.3-1.8.4-2.7.4 1.8-.4 3-1 3.4-1.5z"
			/>
			<path class="nib" d="M8.3 16.6 4 21" />
		</svg>
		<span>{quote ? 'Another quotation' : 'A word from the library'}</span>
	</button>

	<div id="wandering-quote" aria-live="polite">
		{#if quote}
			{#key turn}
				<figure class="scroll">
					<span class="rod" aria-hidden="true"></span>
					<div class="paper">
						<blockquote class="font-display"><QuoteText text={quote.text} /></blockquote>
						<p class="cite">
							<a href={localizeHref(`/quotes/${quote.author.slug}/`)}>{quote.author.name}</a>
							<span aria-hidden="true"> · </span>
							<a href={quoteHref(quote)}>{citeLine(quote)}</a>
						</p>
					</div>
					<span class="rod" aria-hidden="true"></span>
				</figure>
			{/key}
			<!-- Rolled up, focus goes back to the quill rather than falling to
			     the page with the button that held it. -->
			<button
				type="button"
				class="roll-up"
				onclick={() => {
					quote = null;
					quill?.focus();
				}}>Roll it up</button
			>
		{:else if dry}
			<p class="dry">The ink has run dry. Try again in a moment.</p>
		{/if}
	</div>
</div>

<style>
	.wandering {
		margin-top: 1rem;
		max-width: 20rem;
	}
	.quill {
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.3rem 0.75rem 0.3rem 0.45rem;
		border: 1px solid var(--color-border);
		border-radius: 999px;
		background: var(--color-surface);
		color: var(--color-muted);
		font-size: var(--fs-small);
		cursor: pointer;
	}
	.quill:hover,
	.quill:focus-visible {
		color: var(--color-text);
		border-color: var(--color-accent);
	}
	.quill svg {
		flex: none;
	}
	.feather {
		fill: var(--color-accent);
	}
	.nib {
		stroke: var(--color-accent);
		stroke-width: 1.4;
		stroke-linecap: round;
		fill: none;
	}
	@media (prefers-reduced-motion: no-preference) {
		.quill svg {
			transition: rotate var(--duration-fast) ease;
			transform-origin: 30% 80%;
		}
		.quill:hover svg {
			/* tilt-ok: a quill dipping toward the page, not a book */
			rotate: -12deg;
		}
	}
	/* The scroll: the gallery mat's cream and its ink (--hero-mat /
	   --hero-mat-ink, a pair measured together, the same in every theme),
	   wound between two gilt rods. */
	.scroll {
		margin: 0.85rem 0 0;
	}
	.rod {
		display: block;
		height: 0.45rem;
		margin-inline: -0.4rem;
		border-radius: 999px;
		background: linear-gradient(to bottom, var(--hero-gilt), var(--hero-gilt-deep));
		box-shadow: 0 1px 2px rgb(0 0 0 / 0.3);
	}
	.paper {
		padding: 0.8rem 1rem 0.75rem;
		background: linear-gradient(
			to right,
			color-mix(in srgb, var(--hero-mat) 88%, var(--hero-mat-ink)),
			var(--hero-mat) 18%,
			var(--hero-mat) 82%,
			color-mix(in srgb, var(--hero-mat) 88%, var(--hero-mat-ink))
		);
		color: var(--hero-mat-ink);
		text-align: center;
	}
	blockquote {
		margin: 0;
		font-size: var(--fs-small);
		font-style: italic;
		line-height: 1.5;
	}
	.cite {
		margin-top: 0.45rem;
		font-size: var(--fs-micro);
	}
	.cite a {
		color: inherit;
		text-decoration: underline;
		text-decoration-color: color-mix(in srgb, var(--hero-mat-ink) 40%, transparent);
	}
	.cite a:hover {
		text-decoration-color: currentColor;
	}
	.dry {
		margin-top: 0.5rem;
		font-size: var(--fs-micro);
		color: var(--color-muted);
	}
	.roll-up {
		margin-top: 0.4rem;
		font-size: var(--fs-micro);
		color: var(--color-muted);
		text-decoration: underline;
	}
	.roll-up:hover {
		color: var(--color-text);
	}
	/* Unrolled from the top rod down: the scroll is uncovered as the lower rod
	   is drawn down to its place. */
	@media (prefers-reduced-motion: no-preference) {
		.scroll {
			animation: unroll 700ms cubic-bezier(0.4, 0, 0.2, 1) backwards;
		}
	}
	@keyframes unroll {
		/* Negative side insets: the rods' ends stand out past the paper. */
		from {
			clip-path: inset(-0.5rem -1rem calc(100% - 0.45rem) -1rem);
		}
		to {
			clip-path: inset(-0.5rem -1rem -0.5rem -1rem);
		}
	}
</style>
