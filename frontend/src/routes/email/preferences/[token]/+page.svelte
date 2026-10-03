<script lang="ts">
	import { onMount } from 'svelte';
	import { ApiError } from '$lib/api';
	import { i18n } from '$lib/i18n.svelte';
	import {
		getEmailPreferences,
		saveEmailPreferences,
		type EmailPreferences,
		type EmailPreferencesUpdate
	} from '$lib/library-public';

	const t = i18n.t;

	let { data }: { data: { token: string } } = $props();

	let loading = $state(true);
	let invalid = $state(false);
	let prefs = $state<EmailPreferences | null>(null);
	let error = $state(false);
	// Shows the transient "Saved" note; cleared after a beat. Only one timer is
	// ever outstanding (each save clears the last), so no tick/guard is needed.
	let saved = $state(false);
	let saveTimer: ReturnType<typeof setTimeout> | undefined;

	onMount(async () => {
		try {
			prefs = await getEmailPreferences(data.token);
		} catch (e) {
			if (e instanceof ApiError && e.status === 404) invalid = true;
			else error = true;
		} finally {
			loading = false;
		}
	});

	async function save(update: EmailPreferencesUpdate) {
		error = false;
		try {
			// The server returns the full resolved state — adopt it rather than
			// trusting the request (a rejected locale, say, comes back unchanged).
			// The controls render straight off `prefs`, so there is nothing
			// optimistic to roll back: on failure `prefs` is untouched and still
			// shows the last confirmed state.
			prefs = await saveEmailPreferences(data.token, update);
			saved = true;
			clearTimeout(saveTimer);
			saveTimer = setTimeout(() => (saved = false), 2000);
		} catch {
			error = true;
		}
	}

	// Per-stream and language controls are inert while the master switch is off
	// (wants_stream returns false regardless), so disable them to show they're
	// overridden — the master toggle itself stays usable to turn it back on.
	const disabled = $derived(!prefs || prefs.suppressed || prefs.unsubscribed_all);
</script>

<svelte:head>
	<title>{t('email_prefs.title')} — Ochorus</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<div class="mx-auto max-w-[34rem] px-5 py-12">
	<h1 class="text-h1 mb-1">{t('email_prefs.title')}</h1>

	{#if loading}
		<p class="text-body text-muted">{t('email_prefs.loading')}</p>
	{:else if invalid}
		<div class="rounded-card border border-border bg-surface p-6">
			<h2 class="text-h3 mb-2">{t('email_prefs.invalid')}</h2>
			<p class="text-body text-muted">{t('email_prefs.invalid_body')}</p>
		</div>
	{:else if prefs}
		<p class="mb-6 text-body text-muted">{t('email_prefs.intro')}</p>

		{#if prefs.suppressed}
			<p class="rounded-card mb-6 border border-warning/40 bg-warning/5 p-4 text-small text-warning">
				{t('email_prefs.suppressed')}
			</p>
		{/if}

		<section class="rounded-card border border-border bg-surface p-5">
			<h2 class="text-h3 mb-3">{t('email_prefs.streams_heading')}</h2>
			<ul class="flex flex-col divide-y divide-border">
				{#each prefs.streams as stream (stream.key)}
					<li class="flex items-start justify-between gap-4 py-3">
						<div>
							<p class="text-body font-medium">{stream.label}</p>
							<p class="text-small text-muted">{stream.description}</p>
						</div>
						<button
							type="button"
							role="switch"
							aria-checked={stream.enabled}
							aria-label={stream.label}
							{disabled}
							onclick={() => save({ streams: { [stream.key]: !stream.enabled } })}
							class="switch"
							class:switch-on={stream.enabled}
						>
							<span class="switch-knob"></span>
						</button>
					</li>
				{/each}
			</ul>
		</section>

		<section class="rounded-card mt-5 border border-border bg-surface p-5">
			<h2 class="text-h3 mb-1">{t('email_prefs.language_heading')}</h2>
			<p class="mb-3 text-small text-muted">{t('email_prefs.language_help')}</p>
			<select
				{disabled}
				value={prefs.email_locale}
				onchange={(e) => save({ email_locale: e.currentTarget.value })}
				class="field w-full"
			>
				<option value="">{t('email_prefs.language_default')}</option>
				{#each prefs.locales as loc (loc.code)}
					<option value={loc.code}>{loc.name}</option>
				{/each}
			</select>
		</section>

		<section class="rounded-card mt-5 border border-border bg-surface p-5">
			<div class="flex items-start justify-between gap-4">
				<div>
					<h2 class="text-h3 mb-1">{t('email_prefs.unsub_heading')}</h2>
					<p class="text-small text-muted">{t('email_prefs.unsub_help')}</p>
				</div>
				<button
					type="button"
					role="switch"
					aria-checked={prefs.unsubscribed_all}
					aria-label={t('email_prefs.unsub_heading')}
					disabled={prefs.suppressed}
					onclick={() => prefs && save({ unsubscribed_all: !prefs.unsubscribed_all })}
					class="switch"
					class:switch-on={prefs.unsubscribed_all}
				>
					<span class="switch-knob"></span>
				</button>
			</div>
		</section>

		<p class="mt-4 h-5 text-small" aria-live="polite">
			{#if error}
				<span class="text-warning">{t('email_prefs.error')}</span>
			{:else if saved}
				<span class="text-accent">{t('email_prefs.saved')}</span>
			{/if}
		</p>
	{:else}
		<p class="text-body text-warning">{t('email_prefs.error')}</p>
	{/if}
</div>

<style>
	.switch {
		position: relative;
		flex: none;
		width: 2.6rem;
		height: 1.5rem;
		border-radius: 9999px;
		background: var(--color-border);
		transition: background 0.15s ease;
		cursor: pointer;
	}
	.switch:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}
	.switch-on {
		background: var(--color-accent);
	}
	.switch-knob {
		position: absolute;
		top: 0.15rem;
		inset-inline-start: 0.15rem;
		width: 1.2rem;
		height: 1.2rem;
		border-radius: 9999px;
		background: #fff; /* hex-ok: the toggle knob is always white, on both the grey and accent tracks */
		transition: transform 0.15s ease;
	}
	.switch-on .switch-knob {
		transform: translateX(1.1rem);
	}
	:global([dir='rtl']) .switch-on .switch-knob {
		transform: translateX(-1.1rem);
	}
</style>
