<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { theme, THEME_OPTIONS, type ThemePref } from '$lib/theme.svelte';
	import { palette } from '$lib/palette.svelte';
	import { PALETTES, PALETTE_COLORS, type Palette } from '$lib/palettes';
	import { siteFont, SITE_FONTS, type SiteFont } from '$lib/siteFont.svelte';
	import { localizeHref } from '$lib/href';
	import { pageWidth } from '$lib/pageWidth.svelte';
	import { isReaderRoute } from '$lib/readerRoutes';
	import { i18n } from '$lib/i18n.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import { dismissable } from '$lib/actions/dismissable';

	// Take Root's quick-settings popover: the gear opens a small menu with the
	// look of the site — brightness (system / light / sepia / dark), library
	// colours, site style — and a page-width stepper, with no navigation to the
	// Settings page. Every control drives the same store Settings does, so the
	// two can never disagree. The stepper drives the shared pageWidth preference, so every browse
	// surface (`.page-col`) resizes together and the choice persists.
	const t = i18n.t;
	let open = $state(false);

	// A chapter and a sermon size their column from `--reading-measure`, which
	// their own `A a` popover owns — `.page-col` isn't on those pages at all. The
	// stepper still rendered there and still WORKED, in the sense that it stored a
	// new value and moved nothing: a width control sitting a few pixels from the
	// width control that does something. Hide the row rather than leave it lying;
	// the theme toggle below still applies everywhere.
	const inReader = $derived(isReaderRoute($page.route.id));

	onMount(() => pageWidth.init());

	// Swatches draw in the brightness showing (a dark ground under dark), like
	// PalettePicker's cards: a preview of the applied palette would show nothing.
	const mode = $derived(theme.current === 'dark' ? 'dark' : 'light');
	const PALETTE_NAME = $derived<Record<Palette, string>>({
		parchment: t('palette.parchment'),
		cathedral: t('palette.cathedral'),
		olive: t('palette.olive'),
		hearth: t('palette.hearth'),
		dawn: t('palette.dawn'),
		monastery: t('palette.monastery')
	});
	const FONT_NAME = $derived<Record<SiteFont, string>>({
		house: t('settings.siteFontHouse'),
		classic: t('settings.siteFontClassic'),
		hyperlegible: t('settings.siteFontHyperlegible')
	});

	/** Arrow keys move a radio group's choice, as PalettePicker's do. */
	function radioKeys<T extends string>(all: readonly T[], current: T, set: (v: T) => void, attr: string) {
		return (e: KeyboardEvent) => {
			const step = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[e.key];
			if (!step) return;
			e.preventDefault();
			const host = e.currentTarget as HTMLElement;
			const rtl = getComputedStyle(host).direction === 'rtl';
			const horizontal = e.key === 'ArrowLeft' || e.key === 'ArrowRight';
			const i = all.indexOf(current);
			const next = all[(i + (rtl && horizontal ? -step : step) + all.length) % all.length];
			set(next);
			host.querySelector<HTMLElement>(`[${attr}='${next}']`)?.focus();
		};
	}
</script>

<!-- The four brightness icons. System is a disc half lit, sepia a page with a
     turned corner; sun and moon come from the shared set. -->
{#snippet themeIcon(v: ThemePref)}
	{#if v === 'light'}
		<Icon name="sun" size={17} />
	{:else if v === 'dark'}
		<Icon name="moon" size={17} />
	{:else if v === 'system'}
		<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
			<circle cx="12" cy="12" r="8.5" />
			<path d="M12 3.5a8.5 8.5 0 0 1 0 17z" fill="currentColor" stroke="none" />
		</svg>
	{:else}
		<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
			<path d="M6 3h9l4 4v14H6z" />
			<path d="M15 3v4h4" />
			<path d="M9 12h7M9 16h5" />
		</svg>
	{/if}
{/snippet}

<div class="prefs" use:dismissable={{ open, onDismiss: () => (open = false) }}>
	<!-- aria-controls only while the panel exists: it is rendered by {#if open},
	     and an IDREF pointing at nothing is worse than none. aria-expanded stays
	     on both states — that IS the closed state's information. -->
	<button
		class="prefs-btn"
		aria-expanded={open}
		aria-controls={open ? 'quick-settings' : undefined}
		aria-label={t('settings.title')}
		title={t('settings.title')}
		onclick={() => (open = !open)}
	>
		<Icon name="gear" size={19} />
		<!-- The palette in use, as a dot on the gear: says there are colours in
		     here to choose. Hidden on the house palette, where it would say
		     nothing. -->
		{#if palette.current !== 'parchment'}
			<span class="prefs-badge" style:background={PALETTE_COLORS[palette.current].swatch[mode][1]} aria-hidden="true"></span>
		{/if}
	</button>
	{#if open}
		<!-- A labelled GROUP of controls, not a menu. role="menu" promises
		     menuitem children and arrow-key navigation between them; this popover
		     holds a theme toggle (and, off the reading surfaces, a width stepper)
		     with their labels, and under that role a screen reader hides the
		     labels as foreign content and announces a menu whose items don't
		     respond to the keys it just promised. It borrows the account menu's
		     LOOK, not its semantics. -->
		<div id="quick-settings" class="account-menu prefs-menu" role="group" aria-label={t('settings.title')}>
			<div class="prefs-row">
				<span class="prefs-label" id="qs-theme">{t('nav.theme')}</span>
				<div
					class="prefs-seg"
					role="radiogroup"
					aria-labelledby="qs-theme"
					tabindex="-1"
					onkeydown={radioKeys(
						THEME_OPTIONS.map((o) => o.v),
						theme.preference,
						(v) => theme.set(v),
						'data-theme-option'
					)}
				>
					{#each THEME_OPTIONS as o (o.v)}
						<button
							type="button"
							role="radio"
							aria-checked={theme.preference === o.v}
							tabindex={theme.preference === o.v ? 0 : -1}
							data-theme-option={o.v}
							aria-label={t(o.k)}
							title={t(o.k)}
							onclick={() => theme.set(o.v)}
						>
							{@render themeIcon(o.v)}
						</button>
					{/each}
				</div>
			</div>
			<div class="prefs-row prefs-row--stack">
				<span class="prefs-label" id="qs-palette">{t('settings.palette')}</span>
				<div
					class="prefs-swatches"
					role="radiogroup"
					aria-labelledby="qs-palette"
					tabindex="-1"
					onkeydown={radioKeys(PALETTES, palette.current, (v) => palette.set(v), 'data-palette-option')}
				>
					{#each PALETTES as p (p)}
						{@const [ground, accent, second] = PALETTE_COLORS[p].swatch[mode]}
						<button
							type="button"
							role="radio"
							aria-checked={palette.current === p}
							tabindex={palette.current === p ? 0 : -1}
							data-palette-option={p}
							aria-label={PALETTE_NAME[p]}
							title={PALETTE_NAME[p]}
							class="prefs-swatch"
							style:--sw-ground={ground}
							style:--sw-accent={accent}
							style:--sw-second={second}
							onclick={() => palette.set(p)}
						></button>
					{/each}
				</div>
			</div>
			<div class="prefs-row prefs-row--stack">
				<span class="prefs-label" id="qs-font">{t('settings.siteFont')}</span>
				<div
					class="prefs-seg prefs-seg--fonts"
					role="radiogroup"
					aria-labelledby="qs-font"
					tabindex="-1"
					onkeydown={radioKeys(SITE_FONTS, siteFont.current, (v) => siteFont.set(v), 'data-font-option')}
				>
					{#each SITE_FONTS as f (f)}
						<button
							type="button"
							role="radio"
							aria-checked={siteFont.current === f}
							tabindex={siteFont.current === f ? 0 : -1}
							data-font-option={f}
							aria-label={FONT_NAME[f]}
							title={FONT_NAME[f]}
							class="prefs-font prefs-font--{f}"
							onclick={() => siteFont.set(f)}
						>
							<span aria-hidden="true">Aa</span>
						</button>
					{/each}
				</div>
			</div>
			{#if !inReader}
				<div class="prefs-row">
					<span class="prefs-label">{t('nav.pageWidth')}</span>
					<div class="widthctl">
						<button
							onclick={() => pageWidth.step(-1)}
							disabled={pageWidth.atMin}
							aria-label={t('a11y.narrower')}
							title={t('a11y.narrower')}
						>
							<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
								<path d="M3 12h6" /><path d="M6 9l3 3-3 3" />
								<path d="M21 12h-6" /><path d="M18 9l-3 3 3 3" />
							</svg>
						</button>
						<button
							onclick={() => pageWidth.step(1)}
							disabled={pageWidth.atMax}
							aria-label={t('a11y.wider')}
							title={t('a11y.wider')}
						>
							<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
								<path d="M9 12H3" /><path d="M6 9l-3 3 3 3" />
								<path d="M15 12h6" /><path d="M18 9l3 3-3 3" />
							</svg>
						</button>
					</div>
				</div>
			{/if}
			<a class="prefs-more" href={localizeHref('/settings')} onclick={() => (open = false)}>
				{t('settings.title')}
				<Icon name="chevron-right" size={14} />
			</a>
		</div>
	{/if}
</div>
