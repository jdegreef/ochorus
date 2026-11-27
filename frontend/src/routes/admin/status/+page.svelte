<script lang="ts">
	import { adminResource } from '$lib/adminResource.svelte';
	import AdminGate from '$lib/components/AdminGate.svelte';
	import { getAdminStatus, type JobState, type StatusJob } from '$lib/library-admin';
	import { relativeTime } from '$lib/relativeTime';

	const res = adminResource(getAdminStatus, 'Something went wrong loading the system status.');

	const ago = (iso: string | null, now: string) =>
		iso ? relativeTime(Date.parse(iso), 'en', 'just now', Date.parse(now)) : 'never';

	// One word and one tone per state. Only a failing or late job is coloured;
	// paused is expected while sending is off, so it stays quiet.
	const STATE: Record<JobState, { label: string; cls: string }> = {
		ok: { label: 'Running', cls: 'border-accent-soft-border bg-accent-soft text-accent' },
		late: { label: 'Late', cls: 'border-warning bg-warning/10 text-warning' },
		failing: { label: 'Failing', cls: 'border-danger bg-danger/10 text-danger' },
		paused: { label: 'Paused', cls: 'border-border bg-surface-2 text-muted' },
		never: { label: 'No report yet', cls: 'border-border bg-surface-2 text-muted' }
	};

	function detail(j: StatusJob, now: string): string {
		if (j.state === 'failing')
			return `Last run failed ${ago(j.last_started_at, now)}. Last good run: ${ago(j.last_ok_at, now)}.`;
		if (j.state === 'late')
			return `No good run for ${ago(j.last_ok_at, now).replace(' ago', '')}. It should run at least every ${j.late_after_minutes} minutes.`;
		if (j.state === 'paused')
			return j.last_ok_at ? `Last ran ${ago(j.last_ok_at, now)}.` : 'Has not run here yet.';
		if (j.state === 'never') return 'Has not reported since heartbeats were added.';
		return `Last ran ${ago(j.last_ok_at, now)}.`;
	}
</script>

<svelte:head>
	<title>Admin · System status — Ochorus</title><meta name="robots" content="noindex" />
</svelte:head>

<div class="mx-auto max-w-4xl px-5 py-10">
	<a href="/admin" class="text-small text-accent hover:underline">← Back to dashboard</a>

	<AdminGate
		resource={res}
		errorTitle="Couldn't load the system status"
		loadingText="Loading…"
		panelClass="mt-6"
	>
		{#snippet children(d)}
			<header class="mb-6 mt-3">
				<p class="eyebrow mb-2 text-accent">Admin · Settings</p>
				<h1 class="text-display">System status</h1>
				<p class="mt-2 text-body text-muted">
					The jobs that run on their own: the email cron every 15 minutes, the nightly content audit
					and each deploy's release chain. If one stops or starts failing, it shows here before a
					reader notices.
				</p>
			</header>

			<section class="mb-8 rounded-card border border-border bg-surface p-5">
				<h2 class="mb-3 text-h3">Email sending</h2>
				{#if d.sending.enabled}
					<p class="text-body text-text">
						Email is <b>on</b>.{#if d.sending.allowlist_size}
							Review mode: only {d.sending.allowlist_size} allowlisted address{d.sending
								.allowlist_size === 1
								? ''
								: 'es'} receive mail.{/if}
					</p>
				{:else}
					<p class="text-body text-text">
						Email is <b>off</b>, so nothing is sent and the email cron is suspended on Render on
						purpose. Its jobs show as paused.
					</p>
					<ul class="mt-2 list-disc ps-5 text-small text-muted">
						{#if !d.sending.switch_on}<li>The <code>EMAIL_ENABLED</code> switch is off.</li>{/if}
						{#if !d.sending.provider_key_set}<li>No Resend API key is set.</li>{/if}
						{#if !d.sending.base_urls_set}<li>
								The public site and API addresses aren't set, so links would be broken.
							</li>{/if}
					</ul>
				{/if}
			</section>

			<section class="mb-8">
				<h2 class="mb-3 text-h3">Scheduled jobs</h2>
				<ul class="divide-y divide-border rounded-card border border-border bg-surface">
					{#each d.jobs as j (j.name)}
						<li class="flex flex-wrap items-start justify-between gap-3 px-4 py-3">
							<div class="min-w-0">
								<p class="font-semibold text-text">{j.label}</p>
								<p class="text-small text-muted">{detail(j, d.now)}</p>
								{#if j.last_error}
									<p class="mt-1 break-words font-mono text-micro text-danger">{j.last_error}</p>
								{/if}
							</div>
							<span
								class="shrink-0 rounded-full border px-2.5 py-0.5 text-small font-semibold {STATE[
									j.state
								].cls}"
							>
								{STATE[j.state].label}
							</span>
						</li>
					{/each}
				</ul>
			</section>

			<section class="rounded-card border border-border bg-surface p-5">
				<h2 class="mb-3 text-h3">Content and reports</h2>
				<dl class="grid gap-x-6 gap-y-2 text-small sm:grid-cols-[auto_1fr]">
					<dt class="text-muted">Waiting for a rebuild</dt>
					<dd class="text-text">
						{d.content.unbuilt_changes
							? `${d.content.unbuilt_changes} change${d.content.unbuilt_changes === 1 ? '' : 's'} made in the admin since the last rebuild`
							: 'Nothing'}
					</dd>
					<dt class="text-muted">Last rebuild requested</dt>
					<dd class="text-text">{ago(d.content.deploy_fired_at, d.now)}</dd>
					<dt class="text-muted">Last content audit</dt>
					<dd class="text-text">{ago(d.content.last_audit_scan_at, d.now)}</dd>
					<dt class="text-muted">Last language-health snapshot</dt>
					<dd class="text-text">{d.content.last_health_snapshot ?? 'never'}</dd>
				</dl>
			</section>
		{/snippet}
	</AdminGate>
</div>
