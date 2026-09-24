<script lang="ts">
	import { dismissable } from '$lib/actions/dismissable';
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { theme } from '$lib/theme.svelte';
	import { pageWidth } from '$lib/pageWidth.svelte';
	import { isReaderRoute } from '$lib/readerRoutes';
	import { i18n } from '$lib/i18n.svelte';
	import Icon from '$lib/components/Icon.svelte';

	// Take Root's quick-settings popover: the gear opens a small menu with a
	// theme toggle and a page-width stepper — no navigation to the Settings
	// page. The stepper drives the shared pageWidth preference, so every browse
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
</script>

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
		onclick={(e) => {
			e.stopPropagation();
			open = !open;
		}}
	>
		<Icon name="gear" size={19} />
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
				<span class="prefs-label">{t('nav.theme')}</span>
				<button
					class="prefs-toggle"
					onclick={() => theme.toggle()}
					aria-label={theme.current === 'dark' ? t('settings.themeLight') : t('settings.themeDark')}
					title={theme.current === 'dark' ? t('settings.themeLight') : t('settings.themeDark')}
				>
					<Icon name={theme.current === 'dark' ? 'moon' : 'sun'} size={17} />
				</button>
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
		</div>
	{/if}
</div>
