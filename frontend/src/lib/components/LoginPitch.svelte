<script lang="ts">
	import { i18n } from '$lib/i18n.svelte';

	/**
	 * The left-hand pitch on /login when the reader arrived from a My Bookshelf or
	 * My Notebook link (footer, signed out). A bare "Welcome back" sold nothing to
	 * someone who has no account yet, so each destination explains itself — what
	 * the page does, drawn — beside the sign-up form.
	 *
	 * The drawings are markup, not images: they theme with the tokens and their
	 * words translate. The sample passage is Murray's own line from Humility, ch. 1,
	 * taken from each language's edition of that book (`login.pitchSampleQuote`,
	 * with the highlighted span between [[ ]]), so no reader sees English in it.
	 */
	export type PitchKind = 'shelf' | 'notebook';
	/**
	 * Rendered twice by /login — the `intro` (headline + drawing) and the
	 * `features` list — so a phone can put the form between them instead of
	 * making the reader scroll past three benefit blurbs to reach it.
	 */
	let { kind, part }: { kind: PitchKind; part: 'intro' | 'features' } = $props();

	const t = i18n.t;
	const p = $derived(kind === 'shelf' ? 'login.pitchShelf' : 'login.pitchNotebook');

	/** Split "before [[marked]] after" into its three parts; no markers → all plain. */
	const quote = $derived.by(() => {
		const m = /^(.*?)\[\[(.*?)\]\](.*)$/s.exec(t('login.pitchSampleQuote'));
		return m ? { pre: m[1], mark: m[2], post: m[3] } : { pre: t('login.pitchSampleQuote'), mark: '', post: '' };
	});

	// Spines on the drawn shelf: [x, y, width, tone]. Tones are token mixes so the
	// shelf follows the theme rather than carrying its own palette.
	const SPINES: [number, number, number, string][] = [
		[30, 58, 34, 'var(--accent)'],
		[66, 76, 28, 'color-mix(in srgb, var(--hl-rose) 55%, var(--text))'],
		[96, 46, 38, 'color-mix(in srgb, var(--hl-green) 45%, var(--text))'],
		[136, 68, 26, 'var(--gold)'],
		[164, 84, 32, 'color-mix(in srgb, var(--accent) 60%, var(--text))'],
		[350, 62, 30, 'color-mix(in srgb, var(--text) 80%, var(--surface-2))'],
		[382, 80, 36, 'color-mix(in srgb, var(--accent) 65%, var(--surface-2))'],
		[420, 56, 28, 'color-mix(in srgb, var(--gold) 75%, var(--surface-2))'],
		[450, 90, 32, 'color-mix(in srgb, var(--hl-rose) 45%, var(--surface-2))']
	];
</script>

{#if part === 'intro'}
	<section class="pitch">
		<p class="eyebrow pitch-eyebrow">{t(kind === 'shelf' ? 'fav.yourFavorites' : 'notebook.title')}</p>
		<h1 class="pitch-title">{t(`${p}Title`)}</h1>
		<p class="lede">{t(`${p}Lede`)}</p>

		<div class="art" class:nb={kind === 'notebook'} aria-hidden="true">
			{#if kind === 'shelf'}
				<svg class="shelf" viewBox="0 0 520 230" preserveAspectRatio="xMinYMax slice">
					<rect x="0" y="178" width="520" height="14" class="plank" />
					<rect x="0" y="192" width="520" height="38" class="plank-edge" />
					{#each SPINES as [x, y, w, tone] (x)}
						<rect {x} {y} width={w} height={178 - y} rx="3" style="fill: {tone}" />
					{/each}
					<path d="M120 178v22l5-5 5 5v-22z" style="fill: var(--gold)" />
					<rect
						x="200"
						y="72"
						width="30"
						height="106"
						rx="3"
						transform="rotate(-10 215 178)"
						style="fill: color-mix(in srgb, var(--gold) 50%, var(--text))"
					/>
					<rect x="252" y="108" width="72" height="16" rx="2" style="fill: var(--accent)" />
					<rect x="246" y="124" width="84" height="18" rx="2" style="fill: color-mix(in srgb, var(--hl-rose) 55%, var(--text))" />
					<rect x="250" y="142" width="78" height="36" rx="2" style="fill: color-mix(in srgb, var(--hl-green) 45%, var(--text))" />
				</svg>
				<div class="float resume">
					<span class="k">{t('continue.title')}</span>
					<span class="book">{t('login.pitchSampleBook')}</span>
					<span class="by">Andrew Murray</span>
					<span class="bar"><i></i></span>
				</div>
			{:else}
				<div class="float page-card">
					<span class="k">{t('login.pitchSampleBook')}</span>
					<p class="passage">{quote.pre}<mark>{quote.mark}</mark>{quote.post}</p>
					<span class="line"></span>
				</div>
				<div class="float note">
					<span class="k">
						<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9" /><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z" /></svg>
						{t('login.pitchYourNote')}
					</span>
					<p>{t('login.pitchSampleNote')}</p>
				</div>
			{/if}
		</div>
	</section>
{:else}
	<ul class="feats">
		{#each [1, 2, 3] as n (n)}
			<li>
				<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
					{#if kind === 'shelf'}
						{#if n === 1}<path d="M6 3h12v18l-6-4-6 4z" />
						{:else if n === 2}<path d="M4 12a8 8 0 1 0 3-6.2" /><path d="M4 4v4h4" />
						{:else}<rect x="3" y="4" width="13" height="10" rx="1.5" /><rect x="15" y="9" width="6" height="11" rx="1.5" /><path d="M7 18h6" />{/if}
					{:else if n === 1}<path d="M9 11l-5 5v4h4l5-5" /><path d="M14 6l4 4" /><path d="M11 9l6-6 4 4-6 6" />
					{:else if n === 2}<path d="M12 20h9" /><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z" />
					{:else}<circle cx="11" cy="11" r="7" /><path d="M20 20l-4-4" />{/if}
				</svg>
				<b>{t(`${p}F${n}Title`)}</b>
				<span>{t(`${p}F${n}Body`)}</span>
			</li>
		{/each}
	</ul>
{/if}

<style>
	.pitch {
		display: flex;
		flex-direction: column;
		gap: 1.25rem;
		min-width: 0;
	}
	.pitch-eyebrow {
		margin: 0;
		color: var(--gold);
	}
	.pitch-title {
		margin: 0;
		font-family: var(--font-display);
		font-weight: 600;
		font-size: var(--fs-display);
		line-height: 1.1;
		letter-spacing: -0.01em;
		text-wrap: balance;
	}
	.lede {
		margin: 0;
		max-width: 34em;
		font-size: var(--fs-body);
		line-height: 1.55;
		color: var(--muted);
	}

	.art {
		position: relative;
		height: 14.5rem;
		overflow: hidden;
		border: 1px solid var(--border);
		border-radius: var(--radius-card);
		background: var(--surface-2);
	}
	.shelf {
		display: block;
		width: 100%;
		height: 100%;
	}
	.plank {
		fill: color-mix(in srgb, var(--gold) 45%, var(--surface-2));
	}
	.plank-edge {
		fill: color-mix(in srgb, var(--gold) 60%, var(--text));
		opacity: 0.55;
	}
	.float {
		position: absolute;
		display: flex;
		flex-direction: column;
		gap: 0.3rem;
		padding: 0.75rem 0.9rem;
		border: 1px solid var(--border);
		border-radius: 0.75rem;
		background: var(--surface);
		box-shadow: 0 8px 24px -8px color-mix(in srgb, var(--text) 30%, transparent);
	}
	.k {
		display: flex;
		align-items: center;
		gap: 0.35rem;
		font-size: var(--fs-micro);
		font-weight: 600;
		letter-spacing: 0.08em;
		text-transform: uppercase;
		color: var(--muted);
	}
	.resume {
		inset-inline-end: 1rem;
		top: 1rem;
		width: min(13.5rem, 55%);
	}
	.book {
		font-family: var(--font-display);
		font-weight: 600;
	}
	.by {
		font-size: var(--fs-small);
		color: var(--muted);
	}
	.bar {
		height: 5px;
		border-radius: 3px;
		background: var(--accent-soft);
	}
	.bar i {
		display: block;
		width: 58%;
		height: 100%;
		border-radius: 3px;
		background: var(--accent);
	}

	/* The notebook drawing flows rather than floats: the note tucks under the
	   page's blank last line, so it can never cover the highlighted words at
	   any width or in any language's line breaks. */
	.art.nb {
		height: auto;
		display: flex;
		flex-direction: column;
		padding: 1.1rem 1.25rem 1.25rem;
	}
	.nb .float {
		position: relative;
	}
	.page-card {
		width: 88%;
		padding-bottom: 1.75rem;
		transform: rotate(-1.2deg);
	}
	.passage {
		margin: 0;
		font-family: var(--font-display);
		font-size: var(--fs-small);
		line-height: 1.55;
	}
	.passage mark {
		background: color-mix(in srgb, var(--hl-gold) 32%, transparent);
		color: inherit;
		border-radius: 2px;
	}
	.line {
		height: 6px;
		width: 55%;
		border-radius: 3px;
		background: var(--surface-2);
	}
	.note {
		align-self: flex-end;
		width: min(15rem, 62%);
		margin-top: -1.35rem;
		transform: rotate(1.5deg);
		border-color: var(--accent-soft-border);
		background: var(--accent-soft);
	}
	.note .k {
		color: var(--accent);
	}
	.note p {
		margin: 0;
		font-size: var(--fs-small);
		font-style: italic;
		line-height: 1.45;
	}

	.feats {
		display: grid;
		grid-template-columns: repeat(3, minmax(0, 1fr));
		gap: 1rem;
		margin: 0;
		padding: 0;
		list-style: none;
	}
	.feats li {
		display: flex;
		flex-direction: column;
		gap: 0.2rem;
	}
	.feats svg {
		margin-bottom: 0.2rem;
		color: var(--accent);
	}
	.feats span {
		font-size: var(--fs-small);
		line-height: 1.45;
		color: var(--muted);
	}

	@media (max-width: 40rem) {
		.art {
			height: 12.5rem;
		}
		.feats {
			grid-template-columns: minmax(0, 1fr);
		}
	}
</style>
