"use client";
import { useEffect, useState, useRef } from "react";
import {
  api,
  unwrap,
  defaultAttributes,
  slots,
  colors,
  type Garment,
  type Attributes,
  type Context,
  type Outfit,
  type User,
  type Insight,
  type Event,
  type Analysis,
} from "@/lib/api";

const initialContext: Context = {
  occasion: "job interview",
  temperature: 12,
  precipitation: "dry",
  wind: 8,
  min_formality: 2,
  max_formality: 4,
  required: [],
  excluded: [],
  outerwear: true,
  accessory: false,
};
type Tab = "planner" | "wardrobe" | "insights" | "profile";
const emptyProfile = { display_name: "", outfit_style: "all" as "all" | "men" | "women", default_occasion: "job interview" as "job interview" | "everyday" | "dinner" | "weekend" };
const styleLabel = (style?: string) => style === "men" ? "Men’s / male outfits" : style === "women" ? "Women’s / female outfits" : "All styles";
function Select({
  label,
  value,
  onChange,
  values,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  values: readonly string[];
}) {
  return (
    <label>
      {label}
      <select aria-label={label} value={value} onChange={(e) => onChange(e.target.value)}>
        {values.map((v) => (
          <option key={v} value={v}>
            {v.replaceAll("_", " ")}
          </option>
        ))}
      </select>
    </label>
  );
}
function Photo({ g, large = false }: { g: Garment; large?: boolean }) {
  return g.image_url ? (
    <a
      href={g.image_url}
      target="_blank"
      rel="noreferrer"
      aria-label={`Enlarge ${g.name}`}
    >
      <img
        src={(large ? g.image_url : g.thumbnail_url) || g.image_url}
        alt={g.name}
      />
    </a>
  ) : (
    <div className="photo-placeholder">
      {g.slot}
      <span>No image uploaded</span>
    </div>
  );
}
export default function Home() {
  const [user, setUser] = useState<User | null>(null),
    [checking, setChecking] = useState(true),
    [tab, setTab] = useState<Tab>("planner");
  const cameraRequest = useRef(0);
  useEffect(() => () => { cameraRequest.current++; }, []);
  const deviceCameraInput = useRef<HTMLInputElement>(null);
  const cameraVideo = useRef<HTMLVideoElement>(null);
  const [cameraOpen, setCameraOpen] = useState(false);
  const [cameraStream, setCameraStream] = useState<MediaStream | null>(null);
  const [cameraError, setCameraError] = useState("");
  function closeCamera() {
    cameraRequest.current++;
    cameraStream?.getTracks().forEach(track => track.stop());
    setCameraStream(null); setCameraOpen(false); setCameraError("");
  }
  useEffect(() => {
    if (cameraStream && cameraVideo.current) cameraVideo.current.srcObject = cameraStream;
    return () => cameraStream?.getTracks().forEach(track => track.stop());
  }, [cameraStream]);
  async function openCamera() {
    if (!navigator.mediaDevices?.getUserMedia) {
      closeCamera();
      deviceCameraInput.current?.click();
      return;
    }
    const request = ++cameraRequest.current;
    setCameraOpen(true); setCameraError("");
    try {
      if (!navigator.mediaDevices?.getUserMedia) throw new Error("Camera access needs HTTPS or localhost. You can still choose a photo or use your device camera below.");
      const stream = await navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:"environment"}},audio:false});
      if (request !== cameraRequest.current) { stream.getTracks().forEach(track => track.stop()); return; }
      setCameraStream(stream);
    } catch (e) {
      if (request !== cameraRequest.current) return;
      setCameraError(e instanceof DOMException && (e.name === "NotAllowedError" || e.name === "SecurityError")
        ? "Camera permission was denied. Allow camera access in your browser, or choose a photo below."
        : e instanceof DOMException && e.name === "NotFoundError" ? "No camera was found. Choose a photo or use your phone camera instead."
        : e instanceof Error ? e.message : "The camera could not open. Choose a photo instead.");
    }
  }
  async function capturePhoto() {
    const video = cameraVideo.current;
    if (!video?.videoWidth || !video.videoHeight) { setCameraError("The camera is still starting. Please try again in a moment."); return; }
    const canvas = document.createElement("canvas");
    const scale = Math.min(1, 1600 / Math.max(video.videoWidth, video.videoHeight));
    canvas.width = Math.round(video.videoWidth * scale); canvas.height = Math.round(video.videoHeight * scale);
    canvas.getContext("2d")?.drawImage(video,0,0,canvas.width,canvas.height);
    const blob = await new Promise<Blob | null>(resolve => canvas.toBlob(resolve,"image/jpeg",0.9));
    if (!blob) { setCameraError("Could not capture the photo. Please try again."); return; }
    closeCamera();
    await upload(new File([blob],"wardrobe-camera.jpg",{type:"image/jpeg"}));
  }
  const [searchError, setSearchError] = useState("");
  const [searching, setSearching] = useState(false);
  const [searched, setSearched] = useState(false);
  const [profile, setProfile] = useState(emptyProfile);
  const [garments, setGarments] = useState<Garment[]>([]),
    [outfits, setOutfits] = useState<Outfit[]>([]),
    [context, setContext] = useState<Context>(initialContext);
  const [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [email, setEmail] = useState(""),
    [password, setPassword] = useState("");
  const [insights, setInsights] = useState<Insight | null>(null),
    [events, setEvents] = useState<Event[]>([]),
    [editing, setEditing] = useState<Garment | null>(null),
    [review, setReview] = useState(false),
    [analysis, setAnalysis] = useState<Analysis | null>(null),
    [attrs, setAttrs] = useState<Attributes>(defaultAttributes);
  useEffect(() => { if (!review) closeCamera(); }, [review]);
  const [filter, setFilter] = useState({
      category: "all",
      color: "all",
      laundry: "all",
      warmth: "all",
      formality: "all",
    }),
    [archived, setArchived] = useState(false),
    [changed, setChanged] = useState<Record<string, string>>({}),
    [explanations, setExplanations] = useState<Record<string, string>>({}),
    [reason, setReason] = useState<Record<string, string>>({});
  async function loadWardrobe(archive = archived) {
    setGarments(
      unwrap(
        await api.GET("/garments", {
          params: { query: { archived: archive } },
        }),
      ),
    );
  }
  async function loadInsights() {
    setInsights(unwrap(await api.GET("/preferences")));
    setEvents(unwrap(await api.GET("/feedback")));
  }
  async function run(action: () => Promise<void>) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await action();
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Something went wrong. Please retry.",
      );
    } finally {
      setBusy(false);
    }
  }
  useEffect(() => {
    api
      .GET("/auth/me")
      .then((r) => {
        if (r.data) {
          setUser(r.data);
        }
      })
      .finally(() => setChecking(false));
  }, []);
  useEffect(() => {
    if (user) {
      const saved = { ...emptyProfile, ...user.profile };
      setProfile(saved);
      setContext({ ...initialContext, occasion: saved.default_occasion, min_formality: saved.default_occasion === "weekend" ? 0 : saved.default_occasion === "everyday" ? 1 : 2 });
      if (!user.demo && !saved.display_name) setTab("profile");
      run(async () => {
        await loadWardrobe();
        await loadInsights();
      });
    }
  }, [user]); // session loading
  useEffect(() => {
    if (!review) return;
    const previous = document.activeElement as HTMLElement | null;
    const dialog = document.querySelector<HTMLElement>(".review-modal");
    const focusable = () =>
      Array.from(
        dialog?.querySelectorAll<HTMLElement>(
          "button:not(:disabled),input:not(:disabled),select:not(:disabled),textarea:not(:disabled),a[href]",
        ) || [],
      );
    focusable()[0]?.focus();
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !busy) setReview(false);
      if (e.key === "Tab") {
        const nodes = focusable(),
          first = nodes[0],
          last = nodes[nodes.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last?.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first?.focus();
        }
      }
    };
    document.addEventListener("keydown", handler);
    return () => {
      document.removeEventListener("keydown", handler);
      previous?.focus();
    };
  }, [review, busy]);
  async function signIn(mode: "demo" | "login" | "register") {
    await run(async () => {
      const u =
        mode === "demo"
          ? unwrap(await api.POST("/auth/demo"))
          : mode === "login"
            ? unwrap(
                await api.POST("/auth/login", { body: { email, password } }),
              )
            : unwrap(
                await api.POST("/auth/register", { body: { email, password } }),
              );
      setOutfits([]);
      setSearchError(""); setSearched(false);
      setTab("planner");
      setArchived(false);
      setUser(u);
    });
  }
  async function generate() {
    setTab("planner");
    setSearched(true);
    setSearchError("");
    setOutfits([]);
    setSearching(true);
    await run(async () => {
      try {
        const result = unwrap(await api.POST("/outfits/generate", { body: context }));
        setOutfits(result.outfits);
        if (!result.outfits.length) setSearchError("No outfits matched these filters. Try wider formality bounds, review required pieces, or add more clean clothes.");
        setChanged({});
        setExplanations({});
        if (result.outfits.length) setNotice("Your outfits are ready. All hard constraints passed.");
      } catch (e) {
        setSearchError(!garments.length
          ? "Your wardrobe is empty. Add your own clothes before searching: a top and bottom (or a one-piece), plus shoes. Add outerwear if you want a layer."
          : e instanceof Error ? e.message : "The search could not finish. Please try again.");
      } finally { setSearching(false); }
    });
  }
  useEffect(() => {
    if (searched && !searching && tab === "planner") {
      document.getElementById("outfit-results")?.scrollIntoView({behavior:"smooth",block:"start"});
    }
  }, [searched, searching, tab]);
  async function adjust(
    o: Outfit,
    direction: "warmer" | "cooler" | "casual" | "formal",
  ) {
    await run(async () => {
      const result = unwrap(
        await api.POST("/outfits/{id}/adjust", {
          params: { path: { id: o.id } },
          body: { direction },
        }),
      );
      setOutfits((old) => old.map((x) => (x.id === o.id ? result.outfit : x)));
      setChanged((old) => ({
        ...old,
        [result.outfit.id]: result.replacement_id,
      }));
      setExplanations((old) => ({
        ...old,
        [result.outfit.id]: result.explanation,
      }));
    });
  }
  async function feedback(
    o: Outfit,
    event: "liked" | "disliked" | "wore" | "skipped",
  ) {
    await run(async () => {
      await api
        .POST("/outfits/{id}/feedback", {
          params: { path: { id: o.id } },
          body: {
            event,
            reason: (reason[o.id] || null) as "too formal" | null,
          },
        })
        .then(unwrap);
      await loadInsights();
      setNotice(
        `${event[0].toUpperCase() + event.slice(1)} recorded. ${event === "skipped" ? "Skips leave your preferences unchanged." : "Future rankings now include this feedback."}`,
      );
    });
  }
  function openReview(g?: Garment) {
    setEditing(g || null);
    setAttrs(
      g
        ? (Object.fromEntries(
            Object.keys(defaultAttributes).map((k) => [
              k,
              g[k as keyof Garment],
            ]),
          ) as Attributes)
        : { ...defaultAttributes },
    );
    setAnalysis(null);
    setReview(true);
  }
  async function preparePhoto(file: File): Promise<File> {
    const url = URL.createObjectURL(file);
    try {
      const image = new Image();
      image.src = url;
      await image.decode();
      if (image.naturalWidth < 64 || image.naturalHeight < 64) return file;
      const scale = Math.min(1,1600/Math.max(image.naturalWidth,image.naturalHeight));
      const canvas=document.createElement("canvas");
      canvas.width=Math.round(image.naturalWidth*scale); canvas.height=Math.round(image.naturalHeight*scale);
      const ctx=canvas.getContext("2d"); if (!ctx) return file;
      ctx.fillStyle="#ffffff"; ctx.fillRect(0,0,canvas.width,canvas.height);
      ctx.drawImage(image,0,0,canvas.width,canvas.height);
      const blob=await new Promise<Blob | null>(resolve=>canvas.toBlob(resolve,"image/jpeg",0.9));
      return blob ? new File([blob],"wardrobe-photo.jpg",{type:"image/jpeg"}) : file;
    } catch { return file; }
    finally { URL.revokeObjectURL(url); }
  }
  async function upload(file: File) {
    await run(async () => {
      const form = new FormData();
      const prepared = await preparePhoto(file);
      form.append("file", prepared);
      const response = await fetch("/api/uploads", {
        method: "POST",
        body: form,
      });
      const json = await response.json();
      if (!response.ok)
        throw new Error(json.detail?.message || "Upload failed");
      const a = json as Analysis;
      setAnalysis(a);
      setAttrs(a.proposed);
      if ((a.provider === "vision" || a.provider === "local") && !a.warning) {
        unwrap(await api.POST("/garments", {body:{...a.proposed, laundry:"clean", suggestion_id:a.id}}));
        setReview(false);
        await loadWardrobe();
        setNotice("Photo added to your wardrobe. Clothing details were estimated automatically; you can edit them anytime.");
      }

    });
  }
  async function save() {
    await run(async () => {
      if (editing)
        unwrap(
          await api.PUT("/garments/{id}", {
            params: { path: { id: editing.id } },
            body: attrs,
          }),
        );
      else
        unwrap(
          await api.POST("/garments", {
            body: { ...attrs, suggestion_id: analysis?.id || null },
          }),
        );
      setReview(false);
      await loadWardrobe();
      setNotice(
        "Garment saved. Your confirmed attributes are used for planning.",
      );
    });
  }
  const visible = garments.filter(
    (g) =>
      (filter.category === "all" || g.category === filter.category) &&
      (filter.color === "all" || g.primary_color === filter.color) &&
      (filter.laundry === "all" || g.laundry === filter.laundry) &&
      (filter.warmth === "all" || g.warmth === Number(filter.warmth)) &&
      (filter.formality === "all" || g.formality === Number(filter.formality)),
  );
  if (checking)
    return (
      <main className="entry">
        <p role="status">Opening your wardrobe…</p>
      </main>
    );
  if (!user)
    return (
      <main className="entry">
        <div className="entry-copy">
          <div className="brand">
            closetwise<span>✳</span>
          </div>
          <p className="eyebrow">YOUR WARDROBE, REIMAGINED</p>
          <h1>
            Good style.
            <br />
            Already yours.
          </h1>
          <p className="lede">Style what I already own.</p>
          <p>
            Thoughtful outfits from your own clothes, shaped around your day,
            the weather, and what feels like you.
          </p>
          <button
            className="primary"
            disabled={busy}
            onClick={() => signIn("demo")}
          >
            {busy ? "Opening…" : "Explore the demo wardrobe →"}
          </button>
          <small>
            32 real garment photographs · isolated, resettable demo · no
            API key needed
          </small>
        </div>
        <div className="entry-panel">
          <div className="paper-stack">
            <span>THE EVERYDAY EDIT</span>
            <svg viewBox="0 0 240 200" aria-hidden="true">
              <path
                d="M65 35 90 25 120 43 150 25 175 35 220 92 190 115 170 85 170 180 70 180 70 85 50 115 20 92Z"
                fill="#72816e"
                stroke="#374d40"
                strokeWidth="2"
              />
              <path
                d="M90 25 108 57 120 43 132 57 150 25"
                fill="none"
                stroke="#374d40"
                strokeWidth="2"
              />
            </svg>
            <p>
              Less shopping.
              <br />
              More possibility.
            </p>
          </div>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              signIn("login");
            }}
          >
            <h2>Your own closet</h2>
            <label>
              Email
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
              />
            </label>
            <label>
              Password
              <input
                type="password"
                minLength={8}
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
              />
            </label>
            <div className="actions">
              <button disabled={busy} className="primary">
                Sign in
              </button>
              <button
                type="button"
                disabled={busy || !email || password.length < 8}
                onClick={() => signIn("register")}
              >
                Create account
              </button>
            </div>
          </form>
        </div>
        {error && (
          <div role="alert" className="banner error">
            {error}
          </div>
        )}
      </main>
    );
  return (
    <div className="shell">
      <aside className="sidebar">
        <a className="brand" href="/">
          closetwise<span>✳</span>
        </a>
        <p className="tagline">Style what I already own.</p>
        <nav aria-label="Main navigation">
          {(
            [
              ["planner", "✧", "Outfit planner"],
              ["wardrobe", "▦", "My wardrobe"],
              ["insights", "↗", "Your preferences"],
              ["profile", "◎", "Your profile"],
            ] as const
          ).map(([key, icon, title]) => (
            <button
              key={key}
              aria-current={tab === key ? "page" : undefined}
              className={tab === key ? "active" : ""}
              onClick={() => {
                setTab(key);
                if (key === "insights") run(loadInsights);
              }}
            >
              <span>{icon}</span>
              {title}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="demo-label">
            {user.demo ? "DEMO WARDROBE" : "PRIVATE WARDROBE"}
          </div>
          <p>
            {user.demo
              ? "A photo wardrobe to explore. Real clothes, fresh possibilities."
              : user.profile?.display_name || user.email}
          </p>
          {user.demo && (
            <button
              disabled={busy}
              onClick={() =>
                run(async () => {
                  unwrap(await api.POST("/demo/reset"));
                  setOutfits([]);
                  setContext(initialContext);
                  await loadWardrobe();
                  await loadInsights();
                  setNotice("Demo reset to its original wardrobe.");
                })
              }
            >
              Reset demo data
            </button>
          )}
          <button
            onClick={() =>
              run(async () => {
                unwrap(await api.POST("/auth/logout"));
                setUser(null);
                setGarments([]);
                setOutfits([]);
              })
            }
          >
            Sign out
          </button>
        </div>
      </aside>
      <main className="content">
        <header className="topbar">
          <span>A LITTLE INTENTION GOES A LONG WAY</span>
          <span className="avatar" aria-label="Account">
            {(user.profile?.display_name || (user.demo ? "D" : user.email))[0].toUpperCase()}
          </span>
        </header>
        {error && (
          <div role="alert" className="banner error">
            {error}
            <button onClick={() => setError("")} aria-label="Dismiss error">
              ×
            </button>
          </div>
        )}
        {notice && (
          <div role="status" className="banner">
            {notice}
          </div>
        )}
        {busy && (
          <div className="loading" role="status">
            Working on your wardrobe…
          </div>
        )}
        {tab === "planner" && (
          <>
            <div className="page-heading">
              <div>
                <p className="eyebrow">MAKE ROOM FOR POSSIBILITY</p>
                <h1>What’s on your agenda?</h1>
                <p>{user.profile?.display_name ? `${user.profile.display_name}, a fresh way to wear what you own.` : "A few details. A fresh way to wear what you own."}</p>
                <button className="profile-shortcut" onClick={() => setTab("profile")}>Outfits for: {styleLabel(user.profile?.outfit_style)} · Change</button>
              </div>
              <span className="pill">
                ✳ {garments.filter((g) => g.laundry === "clean").length} clean
                pieces
              </span>
            </div>
            <section className="planner-layout">
              <form
                className="planner-card"
                onSubmit={(e) => {
                  e.preventDefault();
                  generate();
                }}
              >
                <div className="section-title">
                  <span className="step">01</span>
                  <h2>Set the scene</h2>
                </div>
                <Select
                  label="Occasion"
                  value={context.occasion}
                  values={["job interview", "everyday", "dinner", "weekend"]}
                  onChange={(v) =>
                    setContext({
                      ...context,
                      occasion: v,
                      min_formality:
                        v === "job interview" ? 2 : v === "dinner" ? 1 : 0,
                      max_formality: 4,
                    })
                  }
                />
                <p className="hint">
                  Occasion suggests defaults. You control the bounds below.
                </p>
                <div className="section-title">
                  <span className="step">02</span>
                  <h2>Check the forecast</h2>
                </div>
                <div className="weather-presets">
                  <button
                    type="button"
                    className={context.temperature === 12 ? "selected" : ""}
                    onClick={() =>
                      setContext({
                        ...context,
                        temperature: 12,
                        wind: 8,
                        precipitation: "dry",
                        outerwear: true,
                      })
                    }
                  >
                    ☁ Cool weather
                  </button>
                  <button
                    type="button"
                    className={context.temperature === 26 ? "selected" : ""}
                    onClick={() =>
                      setContext({
                        ...context,
                        temperature: 26,
                        wind: 0,
                        precipitation: "dry",
                        outerwear: false,
                      })
                    }
                  >
                    ☀ Warm weather
                  </button>
                </div>
                <div className="fields">
                  <label>
                    Temperature (°C)
                    <input
                      type="number"
                      min="-10"
                      max="40"
                      step="1"
                      value={context.temperature}
                      onChange={(e) =>
                        setContext({
                          ...context,
                          temperature: Number(e.target.value),
                        })
                      }
                    />
                  </label>
                  <label>
                    Wind (km/h)
                    <input
                      type="number"
                      min="0"
                      max="100"
                      value={context.wind}
                      onChange={(e) =>
                        setContext({ ...context, wind: Number(e.target.value) })
                      }
                    />
                  </label>
                </div>
                <Select
                  label="Precipitation"
                  value={context.precipitation || "dry"}
                  values={["dry", "rain"]}
                  onChange={(v) =>
                    setContext({
                      ...context,
                      precipitation: v as "dry" | "rain",
                    })
                  }
                />
                <div className="section-title">
                  <span className="step">03</span>
                  <h2>Your ground rules</h2>
                </div>
                <div className="fields">
                  <Select
                    label="Minimum formality"
                    value={String(context.min_formality)}
                    values={["0", "1", "2", "3", "4"]}
                    onChange={(v) =>
                      setContext({ ...context, min_formality: Number(v) })
                    }
                  />
                  <Select
                    label="Maximum formality"
                    value={String(context.max_formality)}
                    values={["0", "1", "2", "3", "4"]}
                    onChange={(v) =>
                      setContext({ ...context, max_formality: Number(v) })
                    }
                  />
                </div>
                <p className="hint">
                  0 relaxed · 1 casual · 2 smart casual · 3 business · 4 formal
                </p>
                <label className="check">
                  <input
                    type="checkbox"
                    checked={context.outerwear}
                    onChange={(e) =>
                      setContext({ ...context, outerwear: e.target.checked })
                    }
                  />
                  Include outerwear
                </label>
                <label className="check">
                  <input
                    type="checkbox"
                    checked={context.accessory}
                    onChange={(e) =>
                      setContext({ ...context, accessory: e.target.checked })
                    }
                  />
                  Include an accessory
                </label>
                <details className="item-rules">
                  <summary>Required & excluded pieces</summary>
                  {garments.map((g) => (
                    <div key={g.id} className="rule-row">
                      <span>{g.name}</span>
                      <label>
                        <input
                          aria-label={`Require ${g.name}`}
                          type="checkbox"
                          checked={context.required?.includes(g.id)}
                          onChange={(e) =>
                            setContext({
                              ...context,
                              required: e.target.checked
                                ? [...(context.required || []), g.id]
                                : (context.required || []).filter(
                                    (id) => id !== g.id,
                                  ),
                            })
                          }
                        />
                        Keep
                      </label>
                      <label>
                        <input
                          aria-label={`Exclude ${g.name}`}
                          type="checkbox"
                          checked={context.excluded?.includes(g.id)}
                          onChange={(e) =>
                            setContext({
                              ...context,
                              excluded: e.target.checked
                                ? [...(context.excluded || []), g.id]
                                : (context.excluded || []).filter(
                                    (id) => id !== g.id,
                                  ),
                            })
                          }
                        />
                        Exclude
                      </label>
                    </div>
                  ))}
                </details>
                <button className="primary generate" disabled={busy}>
                  {searching ? "Finding outfits…" : "Find my outfits"} <span>→</span>
                </button>
                <small>Only your clothes. Your rules, respected.</small>
              </form>
              <div className="results" id="outfit-results" aria-busy={searching}>
                <div className="results-heading">
                  <h2>
                    {outfits.length
                      ? "Your outfit edit"
                      : "A closet full of potential"}
                  </h2>
                  <span>
                    {outfits.length
                      ? `${outfits.length} considered options`
                      : "READY WHEN YOU ARE"}
                  </span>
                </div>
                {searching && <div className="search-state" role="status"><h3>Finding your outfits…</h3><p>Checking your wardrobe against your selected filters.</p></div>}
                {searchError && <div className="search-state search-failed" role="alert"><h3>{garments.length ? "No outfits matched this search" : "Add clothes to get started"}</h3><p>{searchError}</p><p className="hint">Current style: {styleLabel(user.profile?.outfit_style)}. Your selected filters remain in place.</p><button onClick={() => { setTab("wardrobe"); setArchived(false); run(() => loadWardrobe(false)); }}>Go to my wardrobe</button><button onClick={() => setTab("profile")}>Review my style profile</button></div>}
                {!outfits.length && !searching && !searchError && (
                  <div className="empty-planner">
                    <span className="spark">✳</span>
                    <h3>
                      Your next great outfit
                      <br />
                      is already in your closet.
                    </h3>
                    <p>
                      Set your occasion and weather to discover up to three
                      combinations made from your clean, available pieces.
                    </p>
                    <div className="preview-grid">
                      {garments
                        .filter((g) =>
                          [
                            "Oxford shirt",
                            "Charcoal trousers",
                            "Brown dress shoes",
                          ].includes(g.name),
                        )
                        .map((g) => (
                          <div key={g.id}>
                            <Photo g={g} />
                            <span>{g.slot}</span>
                          </div>
                        ))}
                    </div>
                    <p className="hint">
                      Real garment photography · styled demo wardrobe. <a href="/photo-credits" target="_blank" rel="noreferrer">Photo credits ↗</a>
                    </p>
                  </div>
                )}
                {outfits.map((o, i) => (
                  <article
                    className="outfit-card"
                    key={o.id}
                    data-testid="outfit"
                  >
                    <header>
                      <div>
                        <span className="eyebrow">OPTION 0{i + 1}</span>
                        <h3>
                          {i === 0
                            ? "A considered classic"
                            : i === 1
                              ? "A fresh perspective"
                              : "Another way to wear it"}
                        </h3>
                      </div>
                      <span className="pill">✓ Constraints passed</span>
                    </header>
                    <div className="outfit-board">
                      {o.garments.map((g) => (
                        <div
                          key={g.id}
                          data-testid="board-item"
                          data-garment-id={g.id}
                          data-slot={g.slot}
                          className={
                            changed[o.id] === g.id
                              ? "board-item changed"
                              : "board-item"
                          }
                        >
                          <span className="slot-label">{g.slot}</span>
                          <Photo g={g} />
                          <strong>{g.name}</strong>
                          <p>
                            {g.primary_color} · warmth {g.warmth} · formality{" "}
                            {g.formality}
                          </p>
                          {changed[o.id] === g.id && (
                            <span className="changed-label">
                              ↻ Replaced this piece
                            </span>
                          )}
                        </div>
                      ))}
                    </div>
                    {explanations[o.id] && (
                      <p className="substitution" role="status">
                        {explanations[o.id]}
                      </p>
                    )}
                    <div className="adjustments">
                      <span>Make it feel more you</span>
                      {(
                        [
                          ["casual", "More casual"],
                          ["formal", "More formal"],
                          ["warmer", "Make this warmer"],
                          ["cooler", "Make this cooler"],
                        ] as const
                      ).map(([d, t]) => (
                        <button
                          disabled={busy}
                          key={d}
                          onClick={() => adjust(o, d)}
                        >
                          {t}
                        </button>
                      ))}
                    </div>
                    <details className="why">
                      <summary>
                        Why this works · score {o.scores.total.toFixed(2)}
                      </summary>
                      <ul>
                        {o.explanations.map((x) => (
                          <li key={x}>{x}</li>
                        ))}
                      </ul>
                      <div className="score-grid">
                        {Object.entries(o.scores)
                          .filter(([k]) => k !== "total")
                          .map(([k, v]) => (
                            <span key={k}>
                              {k}
                              <strong>{v.toFixed(2)}</strong>
                            </span>
                          ))}
                      </div>
                    </details>
                    <div className="feedback">
                      <span>Would you wear this?</span>
                      <div className="actions">
                        {(
                          ["liked", "disliked", "wore", "skipped"] as const
                        ).map((e) => (
                          <button
                            key={e}
                            disabled={busy}
                            onClick={() => feedback(o, e)}
                          >
                            {e === "liked"
                              ? "♡ Liked"
                              : e === "disliked"
                                ? "Disliked"
                                : e === "wore"
                                  ? "✓ Wore"
                                  : "Skipped"}
                          </button>
                        ))}
                      </div>
                      <select
                        aria-label={`Feedback reason option ${i + 1}`}
                        value={reason[o.id] || ""}
                        onChange={(e) =>
                          setReason({ ...reason, [o.id]: e.target.value })
                        }
                      >
                        <option value="">Optional reason</option>
                        {[
                          "too formal",
                          "too casual",
                          "too cold",
                          "too warm",
                          "don’t like the colors",
                        ].map((r) => (
                          <option key={r}>{r}</option>
                        ))}
                      </select>
                    </div>
                  </article>
                ))}
              </div>
            </section>
          </>
        )}
        {tab === "wardrobe" && (
          <>
            <div className="page-heading">
              <div>
                <p className="eyebrow">LESS SHOPPING, MORE POSSIBILITY</p>
                <h1>Your wardrobe</h1>
                <p>{garments.length} pieces. Countless ways to wear them.</p>
              </div>
              <button className="primary" onClick={() => openReview()}>
                + Add garment
              </button>
            </div>
            <div className="filters">
              <Select
                label="Category"
                value={filter.category}
                values={["all", ...Object.keys(slots)]}
                onChange={(v) => setFilter({ ...filter, category: v })}
              />
              <Select
                label="Color"
                value={filter.color}
                values={["all", ...colors]}
                onChange={(v) => setFilter({ ...filter, color: v })}
              />
              <Select
                label="Availability"
                value={filter.laundry}
                values={["all", "clean", "dirty", "unavailable"]}
                onChange={(v) => setFilter({ ...filter, laundry: v })}
              />
              <Select
                label="Warmth"
                value={filter.warmth}
                values={["all", "0", "1", "2", "3", "4"]}
                onChange={(v) => setFilter({ ...filter, warmth: v })}
              />
              <Select
                label="Formality"
                value={filter.formality}
                values={["all", "0", "1", "2", "3", "4"]}
                onChange={(v) => setFilter({ ...filter, formality: v })}
              />
              <label className="check">
                <input
                  type="checkbox"
                  checked={archived}
                  onChange={(e) => {
                    setArchived(e.target.checked);
                    run(() => loadWardrobe(e.target.checked));
                  }}
                />
                Show archived
              </label>
            </div>
            {!visible.length && (
              <div className="empty">
                No garments here yet. Add a piece or change your filters.
              </div>
            )}
            <div className="wardrobe-grid">
              {visible.map((g) => (
                <article className="garment-card" key={g.id}>
                  <Photo g={g} />
                  <div className="garment-copy">
                    <span className={`laundry ${g.laundry}`}>{g.laundry}</span>
                    <h3>{g.name}</h3>
                    <p>
                      {g.primary_color} · {g.category}
                    </p>
                    <p>
                      Warmth {g.warmth} / Formality {g.formality}
                    </p>
                    <div className="actions">
                      <button onClick={() => openReview(g)}>Edit</button>
                      <button
                        disabled={busy}
                        onClick={() =>
                          run(async () => {
                            unwrap(
                              await api.PATCH("/garments/{id}/archive", {
                                params: { path: { id: g.id } },
                                body: { archived: !g.archived },
                              }),
                            );
                            await loadWardrobe();
                          })
                        }
                      >
                        {g.archived ? "Restore" : "Archive"}
                      </button>
                      <button
                        disabled={busy}
                        onClick={() =>
                          run(async () => {
                            unwrap(
                              await api.DELETE("/garments/{id}", {
                                params: { path: { id: g.id } },
                              }),
                            );
                            await loadWardrobe();
                          })
                        }
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                </article>
              ))}
            </div>
          </>
        )}
        {tab === "profile" && (
          <section className="profile-panel">
            <p className="eyebrow">A WARDROBE THAT KNOWS YOU</p>
            <h1>{user.profile?.display_name ? "Your style profile" : "Let’s make this yours"}</h1>
            <p>Choose whose outfits you want to style. These are clothing preferences; anyone can choose any style.</p>
            <form onSubmit={e => { e.preventDefault(); run(async () => {
              const saved = unwrap(await api.PUT("/profile", {body: profile}));
              setUser(saved); setOutfits([]); setChanged({}); setTab("planner");
              setNotice("Profile saved. We’ll remember it whenever you sign in.");
            }); }}>
              <label>Your name<input required maxLength={80} autoComplete="given-name" value={profile.display_name} onChange={e => setProfile({...profile, display_name:e.target.value})}/></label>
              <label>Outfits for<select aria-label="Outfits for" value={profile.outfit_style} onChange={e => setProfile({...profile,outfit_style:e.target.value as typeof profile.outfit_style})}><option value="men">Men’s / male outfits</option><option value="women">Women’s / female outfits</option><option value="all">All styles</option></select></label>
              <Select label="Usual occasion" value={profile.default_occasion} values={["job interview", "everyday", "dinner", "weekend"]} onChange={v => setProfile({...profile,default_occasion:v as typeof profile.default_occasion})}/>
              <p className="hint">Your name, outfit style and usual occasion are saved to your account. Your wardrobe and feedback history are private to you. Add your own clothes in My wardrobe; new accounts start with an empty closet.</p>
              <button className="primary" disabled={busy}>Save my profile</button>
            </form>
          </section>
        )}
        {tab === "insights" && (
          <>
            <div className="page-heading">
              <div>
                <p className="eyebrow">A LITTLE MORE YOU, EVERY TIME</p>
                <h1>Your preferences</h1>
                <p>
                  Small signals help us order your options with more intention.
                </p>
              </div>
              <span className="pill">
                {insights?.count || 0} learning events
              </span>
            </div>
            <section className="insight-card">
              <h2>What your feedback is shaping</h2>
              <p>{insights?.explanation}</p>
              <div className="preference-bars">
                {insights?.feature_names.map((name, i) => (
                  <div key={name}>
                    <span>{name}</span>
                    <div className="bar">
                      <span
                        style={{
                          left:
                            insights.vector[i] >= 0
                              ? "50%"
                              : `${50 + insights.vector[i] * 50}%`,
                          width: `${Math.abs(insights.vector[i]) * 50}%`,
                        }}
                      />
                    </div>
                    <strong>{insights.vector[i].toFixed(3)}</strong>
                  </div>
                ))}
              </div>
              <p className="hint">
                Positive values favor more of this feature. The zero prior keeps
                sparse feedback modest. These are transparent ranking weights,
                not confidence scores.
              </p>
              <button
                disabled={busy}
                onClick={() => {
                  setTab("planner");
                  generate();
                }}
              >
                Generate with current preferences →
              </button>
            </section>
            <section className="insight-card">
              <h2>Feedback history</h2>
              {!events.length ? (
                <p>
                  No feedback yet. Try an outfit, then tell us how it feels.
                </p>
              ) : (
                <ul className="history">
                  {events.map((e) => (
                    <li key={e.id}>
                      <span className="pill">{e.event}</span>
                      <span>{e.reason || "No reason added"}</span>
                      <time dateTime={e.created_at}>
                        {new Date(e.created_at).toLocaleString()}
                      </time>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </>
        )}
      </main>
      {review && (
        <div className="modal-backdrop">
          <section
            className="review-modal"
            role="dialog"
            aria-modal="true"
            aria-label="Review garment attributes"
          >
            <header>
              <div>
                <p className="eyebrow">YOUR CLOTHES, YOUR FINAL SAY</p>
                <h2>{editing ? "Edit garment" : "Add to your wardrobe"}</h2>
              </div>
              <button
                aria-label="Close garment editor"
                disabled={busy}
                onClick={() => setReview(false)}
              >
                ×
              </button>
            </header>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                save();
              }}
            >
              {!editing && (
                <div className="photo-options">
                  <button type="button" disabled={busy || cameraOpen} onClick={openCamera}>📷 Take photo</button>
                  <p className="hint">Photograph one garment in good light. When photo recognition is connected, we identify it and add it to your wardrobe automatically.</p>
                  {cameraOpen && <section className="camera-panel" aria-label="Garment camera">
                    <video ref={cameraVideo} autoPlay playsInline muted aria-label="Live camera preview" />
                    {cameraError && <p role="alert">{cameraError}</p>}
                    <button type="button" disabled={!cameraStream || busy} onClick={capturePhoto}>Capture photo</button>
                    <button type="button" onClick={closeCamera}>Cancel camera</button>
                  </section>}
                  <label className="upload">Choose a garment photo
                    <input type="file" accept="image/*,.heic,.heif,.avif" disabled={busy} onChange={e => {const f=e.target.files?.[0]; if(f) {closeCamera(); upload(f);} e.target.value="";}} />
                    <small>Gallery photos are resized automatically. JPEG, PNG, HEIC, AVIF and other common image formats are supported.</small>
                  </label>
                  <label className="device-camera">Use device camera (phones)
                    <input ref={deviceCameraInput} aria-label="Device camera photo" type="file" accept="image/*" capture="environment" disabled={busy} onChange={e => {const f=e.target.files?.[0]; if(f) {closeCamera(); upload(f);} e.target.value="";}} />
                  </label>
                  <p className="hint">Phone browsers can open the device camera directly. Your camera stops after capture or when you close this editor.</p>
                </div>
              )}
              {analysis && (
                <div className="analysis">
                  <img src={analysis.image_url} alt="Uploaded garment" />
                  <div>
                    <span className="pill">{analysis.provider === "mock" || analysis.warning ? "PHOTO SAVED — RECOGNITION NOT AVAILABLE" : "CLOTHING IDENTIFIED"}</span>
                    <p>{analysis.provider === "mock" || analysis.warning ? "A vision model has not identified this photo. Enter a name, clothing type and color below. You don’t need to fill in weather or seasons." : analysis.uncertainty}</p>
                    {analysis.warning && <p role="alert">{analysis.warning}</p>}
                    <p>Choose weather and occasion when requesting outfits. Clothing estimates remain editable in your wardrobe.</p>
                  </div>
                </div>
              )}
              <label>
                Garment name
                <input
                  required
                  maxLength={100}
                  value={attrs.name}
                  onChange={(e) => setAttrs({ ...attrs, name: e.target.value })}
                />
              </label>
              {analysis && <div className="fields">
                <Select label="Type of clothing" value={attrs.category} values={Object.keys(slots)} onChange={v => {
                  const category=v as Attributes["category"];
                  const warmth=category === "coat" ? 3 : category === "knit" ? 3 : category === "jacket" ? 2 : category === "boots" ? 2 : 1;
                  const formality=category === "dress_shoes" || category === "loafers" ? 3 : category === "sneakers" || category === "jeans" ? 1 : 2;
                  setAttrs({...attrs,category,slot:slots[v],warmth,formality,seasons:warmth >= 2 ? ["spring","autumn","winter"] : ["spring","summer","autumn"],weather:["dry","wind"]});
                }}/>
                <Select label="Clothing color" value={attrs.primary_color} values={colors} onChange={v => setAttrs({...attrs,primary_color:v as Attributes["primary_color"]})}/>
                <p className="hint">Without photo recognition, warmth and dressiness use approximate category defaults. Edit them below only if needed.</p>
              </div>}
              <details className="optional-attributes"><summary>Optional clothing details</summary>
              <div className="fields">
                <Select
                  label="Clothing style"
                  value={attrs.audience || "unisex"}
                  values={["men", "women", "unisex"]}
                  onChange={v => setAttrs({...attrs,audience:v as Attributes["audience"]})}
                />
                <Select
                  label="Category"
                  value={attrs.category}
                  values={Object.keys(slots)}
                  onChange={(v) =>
                    setAttrs({
                      ...attrs,
                      category: v as Attributes["category"],
                      slot: slots[v],
                    })
                  }
                />
                <label>
                  Outfit slot
                  <input readOnly value={attrs.slot} />
                  <small>Determined by category.</small>
                </label>
                <Select
                  label="Primary color"
                  value={attrs.primary_color}
                  values={colors}
                  onChange={(v) =>
                    setAttrs({
                      ...attrs,
                      primary_color: v as Attributes["primary_color"],
                    })
                  }
                />
                <Select
                  label="Secondary color"
                  value={attrs.secondary_color || "none"}
                  values={["none", ...colors]}
                  onChange={(v) =>
                    setAttrs({
                      ...attrs,
                      secondary_color:
                        v === "none"
                          ? null
                          : (v as Attributes["primary_color"]),
                    })
                  }
                />
                <Select
                  label="Pattern"
                  value={attrs.pattern || "solid"}
                  values={["solid", "striped", "checked", "floral", "graphic"]}
                  onChange={(v) =>
                    setAttrs({ ...attrs, pattern: v as Attributes["pattern"] })
                  }
                />
                <Select
                  label="Laundry status"
                  value={attrs.laundry || "clean"}
                  values={["clean", "dirty", "unavailable"]}
                  onChange={(v) =>
                    setAttrs({ ...attrs, laundry: v as Attributes["laundry"] })
                  }
                />
                <Select
                  label="Warmth (0 airy → 4 insulated)"
                  value={String(attrs.warmth)}
                  values={["0", "1", "2", "3", "4"]}
                  onChange={(v) => setAttrs({ ...attrs, warmth: Number(v) })}
                />
                <Select
                  label="Formality (0 relaxed → 4 formal)"
                  value={String(attrs.formality)}
                  values={["0", "1", "2", "3", "4"]}
                  onChange={(v) => setAttrs({ ...attrs, formality: Number(v) })}
                />
              </div>
              <fieldset>
                <legend>Suitable seasons</legend>
                <div className="actions">
                  {(["spring", "summer", "autumn", "winter"] as const).map(
                    (s) => (
                      <label className="check" key={s}>
                        <input
                          type="checkbox"
                          checked={attrs.seasons?.includes(s)}
                          onChange={(e) =>
                            setAttrs({
                              ...attrs,
                              seasons: e.target.checked
                                ? [...(attrs.seasons || []), s]
                                : (attrs.seasons || []).filter((x) => x !== s),
                            })
                          }
                        />
                        {s}
                      </label>
                    ),
                  )}
                </div>
              </fieldset>
              <fieldset>
                <legend>Suitable weather</legend>
                <div className="actions">
                  {(["dry", "rain", "wind"] as const).map((w) => (
                    <label className="check" key={w}>
                      <input
                        type="checkbox"
                        checked={attrs.weather?.includes(w)}
                        onChange={(e) =>
                          setAttrs({
                            ...attrs,
                            weather: e.target.checked
                              ? [...(attrs.weather || []), w]
                              : (attrs.weather || []).filter((x) => x !== w),
                          })
                        }
                      />
                      {w}
                    </label>
                  ))}
                </div>
              </fieldset>
              <label>
                Tags (comma separated)
                <input
                  maxLength={300}
                  value={attrs.tags?.join(", ") || ""}
                  onChange={(e) =>
                    setAttrs({
                      ...attrs,
                      tags: e.target.value
                        .split(",")
                        .map((x) => x.trim())
                        .filter(Boolean),
                    })
                  }
                />
              </label>
              <label>
                Notes
                <textarea
                  maxLength={1000}
                  value={attrs.notes || ""}
                  onChange={(e) =>
                    setAttrs({ ...attrs, notes: e.target.value })
                  }
                />
              </label>
              </details>
              {error && (
                <p role="alert" className="error">
                  {error}
                </p>
              )}
              <button className="primary" disabled={busy}>
                Confirm attributes & save
              </button>
            </form>
          </section>
        </div>
      )}
    </div>
  );
}

