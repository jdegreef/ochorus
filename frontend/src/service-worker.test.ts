// @vitest-environment node
//
// The worker runs in a ServiceWorkerGlobalScope, not a window, so this file
// stands up the few pieces of one it touches — `self`, Cache Storage, fetch —
// rather than paying for a jsdom that has none of them anyway.
import {
  afterEach,
  beforeAll,
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

vi.mock("$service-worker", () => ({
  version: "v2",
  build: [
    "/_app/immutable/entry/start.A1.js",
    "/_app/immutable/chunks/shared.B2.js",
    "/_app/immutable/assets/app.C3.css",
  ],
}));

const ORIGIN = "https://ochorus.test";
const abs = (u: string | Request) =>
  new URL(typeof u === "string" ? u : u.url, ORIGIN).href;

/** Node's Response is `type: 'default'`; a same-origin browser fetch is 'basic'. */
class BasicResponse extends Response {
  get type(): ResponseType {
    return "basic";
  }
  clone(): Response {
    return Object.setPrototypeOf(super.clone(), BasicResponse.prototype);
  }
}
const html = (body: string) =>
  new BasicResponse(body, { headers: { "content-type": "text/html" } });

/** The page a build-`v2` document looks like: it loads these three files. */
const PAGE = `<link href="/_app/immutable/assets/app.C3.css" rel="stylesheet">
<link rel="modulepreload" href="/_app/immutable/entry/start.A1.js">
<script>import("/_app/immutable/chunks/shared.B2.js")</script>`;
const PAGE_FILES = [
  "/_app/immutable/assets/app.C3.css",
  "/_app/immutable/entry/start.A1.js",
  "/_app/immutable/chunks/shared.B2.js",
];

/** An in-memory Cache Storage — insertion-ordered, re-`put` moves to the end. */
const stores = new Map<string, Map<string, Response>>();
function fakeCache(name: string): Cache {
  if (!stores.has(name)) stores.set(name, new Map());
  const entries = stores.get(name)!;
  return {
    async match(req: RequestInfo | URL) {
      return entries
        .get(abs(String(req instanceof Request ? req.url : req)))
        ?.clone();
    },
    async put(req: RequestInfo | URL, res: Response) {
      const key = abs(String(req instanceof Request ? req.url : req));
      entries.delete(key);
      entries.set(key, res);
    },
    async add(req: RequestInfo | URL) {
      const res = await fetch(abs(String(req)));
      if (!res.ok) throw new TypeError("bad");
      entries.set(abs(String(req)), res);
    },
    async keys() {
      return [...entries.keys()].map((k) => new Request(k));
    },
    async delete(req: RequestInfo | URL) {
      return entries.delete(
        abs(String(req instanceof Request ? req.url : req)),
      );
    },
  } as unknown as Cache;
}
const names = (name: string) => [...(stores.get(name)?.keys() ?? [])];

type Handler = (event: unknown) => void;
const handlers: Record<string, Handler> = {};
const enablePreload = vi.fn(async () => {});
const fetchMock =
  vi.fn<(input: RequestInfo | URL, init?: RequestInit) => Promise<Response>>();

beforeAll(async () => {
  Object.assign(globalThis, {
    self: {
      location: new URL(ORIGIN),
      registration: { navigationPreload: { enable: enablePreload } },
      clients: { claim: async () => {} },
      skipWaiting: () => {},
      addEventListener: (type: string, fn: Handler) => (handlers[type] = fn),
    },
    caches: {
      open: async (name: string) => fakeCache(name),
      keys: async () => [...stores.keys()],
      delete: async (name: string) => stores.delete(name),
    },
  });
  vi.stubGlobal("fetch", fetchMock);
  await import("./service-worker");
});

beforeEach(() => {
  stores.clear();
  fetchMock.mockReset();
  vi.useFakeTimers();
});
afterEach(() => vi.useRealTimers());

/** Dispatch a fetch event; resolves to what the worker answered (or undefined). */
function dispatch(
  url: string,
  {
    mode = "no-cors",
    preload,
  }: { mode?: string; preload?: Promise<Response | undefined> } = {},
) {
  const request = new Request(abs(url));
  Object.defineProperty(request, "mode", { value: mode });
  const extended: Promise<unknown>[] = [];
  let response: Promise<Response> | undefined;
  handlers.fetch({
    request,
    preloadResponse: preload ?? Promise.resolve(undefined),
    respondWith: (p: Promise<Response>) => (response = p),
    waitUntil: (p: Promise<unknown>) => extended.push(p),
  });
  // Settled once the response and every lifetime extension — including those
  // the worker only registers after an await — have finished.
  const settled = async () => {
    await response?.catch(() => {});
    for (let seen = -1; seen !== extended.length; ) {
      seen = extended.length;
      await Promise.all(extended);
    }
  };
  return { response, settled };
}
const navigate = (
  url: string,
  opts: { preload?: Promise<Response | undefined> } = {},
) => dispatch(url, { mode: "navigate", ...opts });

async function seedPage(url: string, files = PAGE_FILES) {
  await fakeCache("ochorus-pages-v2").put(abs(url), html(PAGE));
  for (const f of files)
    await fakeCache("ochorus-cache-v2").put(f, new BasicResponse("x"));
}
const never = () => new Promise<Response>(() => {});

describe("navigations", () => {
  it("answers from the network and keeps a copy of the page", async () => {
    fetchMock.mockImplementation(async () => html("fresh"));
    const { response, settled } = navigate("/books/humility/");
    expect(await (await response!).text()).toBe("fresh");
    await settled();
    expect(names("ochorus-pages-v2")).toEqual([abs("/books/humility/")]);
  });

  it("uses the navigation preload rather than fetching again", async () => {
    const { response } = navigate("/books/humility/", {
      preload: Promise.resolve(html("pre")),
    });
    expect(await (await response!).text()).toBe("pre");
    // Only the shell self-heal fetches (by path); the page itself never twice.
    expect(
      fetchMock.mock.calls.some(([input]) => input instanceof Request),
    ).toBe(false);
  });

  it("settles for a complete cached copy when the network is slow", async () => {
    await seedPage("/books/humility/");
    fetchMock.mockImplementation(never);
    const { response } = navigate("/books/humility/");
    await vi.advanceTimersByTimeAsync(2500);
    expect(await (await response!).text()).toBe(PAGE);
  });

  it("keeps waiting for the network when the cached copy is missing a chunk", async () => {
    // The page from a build whose route chunk never reached this cache — after
    // a deploy the server no longer has it either, so serving it would strand
    // the reader on markup that cannot hydrate.
    await seedPage("/books/humility/", PAGE_FILES.slice(0, 2));
    let answer!: (r: Response) => void;
    fetchMock.mockImplementation((input) =>
      String(input instanceof Request ? input.url : input).includes("/books/")
        ? new Promise((r) => (answer = r))
        : never(),
    );
    const { response } = navigate("/books/humility/");
    let done = false;
    void response!.then(() => (done = true));
    await vi.advanceTimersByTimeAsync(10_000);
    expect(done).toBe(false);
    answer(html("fresh"));
    expect(await (await response!).text()).toBe("fresh");
  });

  it("offline: the complete cached page, else the SPA shell", async () => {
    fetchMock.mockRejectedValue(new TypeError("offline"));
    await fakeCache("ochorus-cache-v2").put("/200.html", html("shell"));
    await seedPage("/books/humility/");
    expect(await (await navigate("/books/humility/").response!).text()).toBe(
      PAGE,
    );

    await fakeCache("ochorus-pages-v2").put(
      abs("/books/other/"),
      html(PAGE + '<script src="/_app/immutable/nodes/9.Z.js"></script>'),
    );
    expect(await (await navigate("/books/other/").response!).text()).toBe(
      "shell",
    );
  });

  it("does not keep redirects, query-string variants or non-HTML", async () => {
    class Redirected extends BasicResponse {
      get redirected() {
        return true;
      }
      clone(): Response {
        return Object.setPrototypeOf(super.clone(), Redirected.prototype);
      }
    }
    fetchMock.mockResolvedValueOnce(
      new Redirected("r", { headers: { "content-type": "text/html" } }),
    );
    await navigate("/books/humility").settled();
    fetchMock.mockImplementation(async () => html("q"));
    await navigate("/search/?q=prayer").settled();
    fetchMock.mockImplementation(async () => new BasicResponse("{}"));
    await navigate("/feed.json").settled();
    expect(names("ochorus-pages-v2")).toEqual([]);
  });

  it("caps the page cache, dropping the least recently fetched", async () => {
    fetchMock.mockImplementation(async () => html("p"));
    for (let i = 0; i < 61; i++) await navigate(`/p/${i}/`).settled();
    await navigate("/p/0/").settled(); // revisited → newest again
    const kept = names("ochorus-pages-v2");
    expect(kept).toHaveLength(60);
    expect(kept).not.toContain(abs("/p/1/"));
    expect(kept.at(-1)).toBe(abs("/p/0/"));
  });
});

describe("SvelteKit version check", () => {
  it("is never answered from a cache", () => {
    expect(dispatch("/_app/version.json").response).toBeUndefined();
  });
});

describe("images", () => {
  it("stale-while-revalidate from the durable image cache", async () => {
    await fakeCache("ochorus-images").put(
      "/covers/humility.webp",
      new BasicResponse("old"),
    );
    fetchMock.mockImplementation(async () => new BasicResponse("new"));
    const { response, settled } = dispatch("/covers/humility.webp");
    expect(await (await response!).text()).toBe("old");
    await settled();
    const again = await fakeCache("ochorus-images").match(
      "/covers/humility.webp",
    );
    expect(await again!.text()).toBe("new");
  });

  it("caps the image cache", async () => {
    fetchMock.mockImplementation(async () => new BasicResponse("i"));
    for (let i = 0; i < 305; i++) await dispatch(`/covers/${i}.webp`).settled();
    const kept = names("ochorus-images");
    expect(kept).toHaveLength(300);
    expect(kept[0]).toBe(abs("/covers/5.webp"));
  });

  it("leaves hashed build images to the versioned cache", async () => {
    fetchMock.mockImplementation(async () => new BasicResponse("svg"));
    await (
      await dispatch("/_app/immutable/assets/logo.D4.svg").response!
    ).text();
    await vi.runAllTimersAsync();
    expect(names("ochorus-images")).toEqual([]);
    expect(names("ochorus-cache-v2")).toContain(
      abs("/_app/immutable/assets/logo.D4.svg"),
    );
  });
});

describe("activate", () => {
  it("drops old versions, keeps the durable caches, enables navigation preload", async () => {
    for (const n of [
      "ochorus-cache-v1",
      "ochorus-pages-v1",
      "ochorus-cache-v2",
      "ochorus-pages-v2",
      "ochorus-offline",
      "ochorus-images",
    ])
      fakeCache(n);
    let done!: Promise<unknown>;
    handlers.activate({ waitUntil: (p: Promise<unknown>) => (done = p) });
    await done;
    expect([...stores.keys()].sort()).toEqual([
      "ochorus-cache-v2",
      "ochorus-images",
      "ochorus-offline",
      "ochorus-pages-v2",
    ]);
    expect(enablePreload).toHaveBeenCalled();
  });
});
