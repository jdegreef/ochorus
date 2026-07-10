// Emit build/404.html as a copy of the SPA shell (200.html).
//
// The static host (Render) rewrites /books/:slug -> /books/:slug.html. When a
// book is unpublished or the slug is unknown, that .html doesn't exist, and the
// host serves its 404.html instead of the /* -> /200.html SPA catch-all. Giving
// it the SPA shell lets the app boot on those URLs, run the route's load (which
// 404s from the API), and render the designed +error.svelte not-found page —
// with a correct 404 status. Without this, missing-book URLs serve a blank page.
import { copyFileSync, existsSync } from 'node:fs';

const shell = 'build/200.html';
const notFound = 'build/404.html';

if (!existsSync(shell)) {
	console.error(`emit-404: ${shell} not found — did the static build run?`);
	process.exit(1);
}
copyFileSync(shell, notFound);
console.log(`emit-404: wrote ${notFound} from ${shell}`);
