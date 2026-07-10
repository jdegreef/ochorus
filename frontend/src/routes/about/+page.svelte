<script lang="ts">
	import { localizeHref } from '$lib/paraglide/runtime';
</script>

<svelte:head><title>About Us — Ochorus</title></svelte:head>

<div class="mx-auto max-w-2xl px-5 py-12">
	<p class="mb-2 text-small font-semibold uppercase tracking-widest text-accent">About Us</p>
	<h1 class="text-display mb-8">About Ochorus</h1>

	<div class="reading-page space-y-5 text-body text-muted">
		<h2 class="text-h2 !text-text">Spreading the Gospel Through Literature</h2>
		<p>
			Based in Victoria BC, Canada and Kampala, Uganda, Ochorus is a dedicated ministry with a profound mission: providing
			exceptional classic Christian literature and resources at no cost, to readers everywhere.
		</p>
		<p>
			Established in 2021, Ochorus is fueled by an unwavering commitment to spreading the gospel to
			every corner of the world, ensuring accessibility across many languages and devices.
		</p>
		<p>
			Recognizing the transformative power of literature, we identify great Christian books within
			the public domain, thoroughly edit them for enhanced readability, and publish them on this
			platform — free to read and free to keep.
		</p>
		<p>
			Aligned with God's desire for the salvation of all people, it is our fervent aspiration to
			contribute to this divine purpose, that many would read, reflect, and be transformed.
		</p>
	</div>

	<div class="mt-10 flex flex-wrap gap-3">
		<a href={localizeHref('/books')} class="btn btn-primary">Browse the Library</a>
		<a href={localizeHref('/contact')} class="btn btn-ghost">Get in Touch</a>
	</div>
</div>
