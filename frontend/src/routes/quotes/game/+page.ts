export const prerender = true;
export const trailingSlash = 'always';

// "Whose words?" — English-only, like the quotations it plays with. The page
// (head, title, how to play) prerenders so it can be found and shared; the
// day's puzzle is fetched in the browser, by the reader's own date, because a
// prerendered puzzle would freeze on the day of the deploy (see WhoseWords).
