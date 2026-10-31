import { useEffect, useState } from "react";
import { Link, Navigate, useNavigate, useParams } from "react-router-dom";
import { api, readCompareList, useAuth, writeCompareList } from "./lib";
import carImg from "./assets/car_dealership.jpg";
import reviewIcon from "./assets/reviewicon.png";
import reviewButton from "./assets/reviewbutton.png";
import positive from "./assets/positive.png";
import negative from "./assets/negative.png";
import neutral from "./assets/neutral.png";

const senti = { positive, negative, neutral };

export function Home() {
  const { user } = useAuth();
  return (
    <div className="home-page">
      <section className="hero page-shell">
        <div className="hero-copy">
          <span className="eyebrow"><span className="eyebrow-dot" /> A better way to shop for your next car</span>
          <h1>Find a dealership worth <span>driving for.</span></h1>
          <p>Explore local dealers, browse their inventory, and hear from real customers before you make your move.</p>
          <div className="hero-actions">
            <Link className="button" to="/dealers">Explore dealerships <span aria-hidden="true">→</span></Link>
            {!user && <Link className="button button-quiet" to="/register">Join the community</Link>}
          </div>
          <div className="hero-note">
            <span className="avatar-stack" aria-hidden="true"><i>R</i><i>J</i><i>M</i></span>
            <span><strong>Real experiences.</strong><br />Helpful reviews from drivers like you.</span>
          </div>
        </div>
        <div className="hero-visual">
          <img className="hero-image" src={carImg} alt="A selection of cars at a dealership" />
          <div className="hero-image-caption"><span className="caption-mark">✦</span><span><strong>Your next chapter starts here</strong><small>Compare dealers with confidence</small></span></div>
          <span className="hero-decoration" aria-hidden="true" />
        </div>
      </section>

      <section className="benefits page-shell" aria-label="How Best Cars helps">
        <div className="benefit-item">
          <span className="benefit-number">01</span>
          <div><h2>Discover local dealers</h2><p>Find a dealership near you and get to know the team.</p></div>
        </div>
        <div className="benefit-item">
          <span className="benefit-number">02</span>
          <div><h2>Explore the inventory</h2><p>See what’s on the lot before you make the trip.</p></div>
        </div>
        <div className="benefit-item">
          <span className="benefit-number">03</span>
          <div><h2>Choose with confidence</h2><p>Learn from customer reviews and their experiences.</p></div>
        </div>
      </section>

      <section className="review-callout">
        <div className="page-shell review-callout-inner">
          <img src={reviewIcon} alt="" />
          <div><span className="eyebrow">Good experiences go both ways</span><h2>Found the right dealer?</h2><p>Share your experience and help the next driver find their way.</p></div>
          <Link className="button button-light" to={user ? "/dealers" : "/register"}>{user ? "Write a review" : "Get started"} <span aria-hidden="true">→</span></Link>
        </div>
      </section>
    </div>
  );
}

function AuthForm({ register }) {
  const { setUser, setIsStaff } = useAuth();
  const nav = useNavigate();
  const [f, setF] = useState({ userName: "", password: "", firstName: "", lastName: "", email: "" });
  const [err, setErr] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  async function submit(e) {
    e.preventDefault();
    setErr("");
    setSubmitting(true);
    try {
      const r = await api(register ? "register" : "login", f);
      if (r.status === "Authenticated") { setUser(r.userName); setIsStaff(Boolean(r.isStaff)); nav("/dealers"); }
      else setErr(r.error || "Invalid username or password");
    } finally {
      setSubmitting(false);
    }
  }
  const fld = (k, label, type = "text", extra = {}) => (
    <label className="form-field">{label}<input type={type} placeholder={`Enter ${label.toLowerCase()}`} value={f[k]} onChange={set(k)} required autoComplete={k === "password" ? (register ? "new-password" : "current-password") : k === "userName" ? "username" : k} {...extra} /></label>
  );
  return (
    <section className="auth-page">
      <form className={`auth-card${register ? " register-card" : ""}`} onSubmit={submit}>
        <span className="eyebrow">BEST CARS COMMUNITY</span>
        <h1>{register ? "Create your account" : "Welcome back"}</h1>
        <p className="auth-intro">{register ? "Join drivers sharing honest dealership experiences." : "Sign in to share your experience and find your next car."}</p>
        {register && <div className="form-row">{fld("firstName", "First name")}{fld("lastName", "Last name")}</div>}
        {register && fld("email", "Email address", "email", { autoComplete: "email" })}
        {fld("userName", "Username")}
        {fld("password", "Password", "password", register ? { minLength: 8 } : {})}
        {err && <p className="form-error" role="alert">{err}</p>}
        <button className="button auth-submit" type="submit" disabled={submitting}>{submitting ? "Please wait…" : register ? "Create account" : "Sign in"} <span aria-hidden="true">→</span></button>
        <p className="auth-switch">{register ? "Already have an account?" : "New to Best Cars?"} <Link to={register ? "/login" : "/register"}>{register ? "Sign in" : "Create an account"}</Link></p>
      </form>
    </section>
  );
}
export const Login = () => <AuthForm />;
export const Register = () => <AuthForm register />;

function FavoriteButton({ dealer, onChange }) {
  const { user } = useAuth();
  const [favorite, setFavorite] = useState(Boolean(dealer.is_favorite));
  const [error, setError] = useState("");
  async function toggle() {
    if (!user) return;
    const result = await api(`dealer/${dealer.id}/favorite`, { favorite: !favorite });
    if (result.status === 200) { setFavorite(result.is_favorite); setError(""); onChange?.(result.is_favorite); }
    else setError(result.message || "Could not update saved dealerships.");
  }
  if (!user) return null;
  return <span className="favorite-control"><button className={`favorite-button${favorite ? " is-favorite" : ""}`} type="button" onClick={toggle} aria-pressed={favorite} aria-label={favorite ? "Remove saved dealership" : "Save dealership"}>{favorite ? "♥" : "♡"}</button>{error && <span className="inline-error" role="alert">{error}</span>}</span>;
}

export function Dealers() {
  const { user } = useAuth();
  const [all, setAll] = useState([]);
  const [options, setOptions] = useState({ states: [], makes: [], body_types: [] });
  const [state, setState] = useState("");
  const [q, setQ] = useState("");
  const [city, setCity] = useState("");
  const [make, setMake] = useState("");
  const [bodyType, setBodyType] = useState("");
  const [sort, setSort] = useState("rating");
  const [page, setPage] = useState(1);
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [comparison, setComparison] = useState(readCompareList);
  const [refresh, setRefresh] = useState(0);
  useEffect(() => {
    let active = true;
    const params = new URLSearchParams({ page: String(page), page_size: "9", sort });
    if (state) params.set("state", state);
    if (q) params.set("q", q);
    if (city) params.set("city", city);
    if (make) params.set("make", make);
    if (bodyType) params.set("body_type", bodyType);
    api(`get_dealers?${params}`).then((r) => {
      if (!active) return;
      if (r.status !== 200) { setError(r.message || "Could not load dealerships."); return; }
      setData(r);
      setAll(r.dealers || []);
      setOptions({ states: r.states || [], makes: r.makes || [], body_types: r.body_types || [] });
      setError("");
    });
    return () => { active = false; };
  }, [page, state, q, city, make, bodyType, sort, refresh]);
  function update(setter, value) { setter(value); setPage(1); }
  function toggleCompare(dealer) {
    const exists = comparison.some((item) => item.id === dealer.id);
    if (!exists && comparison.length >= 3) return;
    const next = exists ? comparison.filter((item) => item.id !== dealer.id) : [...comparison, dealer];
    setComparison(next);
    writeCompareList(next);
  }
  if (!data && !error) return <div className="page-shell page-loading">Finding dealerships…</div>;
  return (
    <section className="page-shell directory-page">
      <div className="page-heading">
        <span className="eyebrow">THE DEALER DIRECTORY</span>
        <h1>Meet your next dealership.</h1>
        <p>Explore local teams, check out their inventory, and see what customers have to say.</p>
      </div>
      <div className="dealer-toolbar">
        <label className="search-field"><span aria-hidden="true">⌕</span><input aria-label="Search dealerships" placeholder="Search by dealer name" value={q} onChange={(e) => update(setQ, e.target.value)} /></label>
        <label className="dealer-filter"><span className="visually-hidden">Filter by state</span><select value={state} onChange={(e) => update(setState, e.target.value)}><option value="">All states</option>{options.states.map((s) => <option key={s}>{s}</option>)}</select></label>
        <label className="dealer-filter"><span className="visually-hidden">Filter by city</span><input placeholder="City" value={city} onChange={(e) => update(setCity, e.target.value)} /></label>
        <label className="dealer-filter"><span className="visually-hidden">Filter by vehicle make</span><select value={make} onChange={(e) => update(setMake, e.target.value)}><option value="">All makes</option>{options.makes.map((v) => <option key={v}>{v}</option>)}</select></label>
        <label className="dealer-filter"><span className="visually-hidden">Filter by body type</span><select value={bodyType} onChange={(e) => update(setBodyType, e.target.value)}><option value="">All body types</option>{options.body_types.map((v) => <option key={v}>{v}</option>)}</select></label>
        <label className="dealer-filter"><span className="visually-hidden">Sort dealerships</span><select value={sort} onChange={(e) => update(setSort, e.target.value)}><option value="rating">Top rated</option><option value="reviews">Most reviewed</option><option value="name">Name A–Z</option><option value="name_desc">Name Z–A</option></select></label>
      </div>
      <div className="directory-meta"><span className="result-count">{data?.total || 0} {(data?.total || 0) === 1 ? "dealership" : "dealerships"}</span>{user && <Link className="text-link" to="/saved">View saved dealerships →</Link>}<Link className="compare-link" to="/compare">Compare ({comparison.length}/3)</Link></div>
      {error && <div className="form-error" role="alert">{error}<button className="text-link" onClick={() => setRefresh(refresh + 1)}>Retry</button></div>}
      {all.length ? (
        <div className="dealer-grid">
          {all.map((d) => {
            const compared = comparison.some((item) => item.id === d.id);
            return <article className="dealer-card" key={d.id}>
              <div className="dealer-card-top"><span className="dealer-monogram" aria-hidden="true">{d.full_name?.charAt(0)}</span><span className="dealer-state">{d.state}</span><FavoriteButton dealer={d} /></div>
              <h2><Link to={`/dealer/${d.id}`}>{d.full_name}</Link></h2>
              <p className="dealer-location"><span aria-hidden="true">⌖</span> {d.city}, {d.state}</p>
              <p className="dealer-rating"><strong>{d.average_rating ? `★ ${Number(d.average_rating).toFixed(1)}` : "New"}</strong><span>{d.review_count} {d.review_count === 1 ? "review" : "reviews"}</span></p>
              <p className="dealer-address">{d.address}{d.zip ? ` · ${d.zip}` : ""}</p>
              <div className="dealer-card-actions"><Link className="text-link" to={`/dealer/${d.id}`}>Explore dealer <span aria-hidden="true">→</span></Link><button className={`compare-toggle${compared ? " selected" : ""}`} type="button" onClick={() => toggleCompare(d)} disabled={!compared && comparison.length >= 3} aria-pressed={compared}>{compared ? "✓ Comparing" : "+ Compare"}</button>{user && <Link className="review-shortcut" to={`/postreview/${d.id}`} aria-label={`Write a review for ${d.full_name}`}><img src={reviewButton} alt="" /></Link>}</div>
            </article>;
          })}
        </div>
      ) : !error && <div className="empty-state"><h2>No dealerships found</h2><p>Try a different search or clear the filters.</p><button className="text-link" onClick={() => { setQ(""); setCity(""); setState(""); setMake(""); setBodyType(""); }}>Clear filters <span aria-hidden="true">→</span></button></div>}
      {data?.pages > 1 && <nav className="pagination" aria-label="Dealership pages"><button disabled={page <= 1} onClick={() => setPage(page - 1)}>← Previous</button><span>Page {data.page} of {data.pages}</span><button disabled={page >= data.pages} onClick={() => setPage(page + 1)}>Next →</button></nav>}
    </section>
  );
}

function ReviewCard({ review, isStaff, user }) {
  const [helpfulCount, setHelpfulCount] = useState(review.helpful_count || 0);
  const [voted, setVoted] = useState(Boolean(review.helpful_by_me));
  const [reportOpen, setReportOpen] = useState(false);
  const [reason, setReason] = useState("");
  const [reportMessage, setReportMessage] = useState("");
  const [reply, setReply] = useState("");
  const [replyMessage, setReplyMessage] = useState("");
  const [response, setResponse] = useState(review.response);
  async function helpful() {
    const result = await api(`reviews/${review.id}/helpful`, {});
    if (result.status === 201 || result.status === 200) { setHelpfulCount(result.helpful_count); setVoted(true); }
    else setReportMessage(result.message || "Could not record your vote.");
  }
  async function report(e) {
    e.preventDefault();
    const result = await api(`reviews/${review.id}/report`, { reason });
    setReportMessage(result.message || "Could not submit report.");
    if (result.status === 201) { setReportOpen(false); setReason(""); }
  }
  async function postReply(e) {
    e.preventDefault();
    const result = await api(`reviews/${review.id}/response`, { response: reply });
    if (result.status === 200) {
      setResponse({ text: result.response, author: result.author, created_at: new Date().toISOString() });
      setReply("");
      setReplyMessage("");
    } else setReplyMessage(result.message || "Could not post dealership response.");
  }
  return (
    <article className="review-card">
      <div className="review-card-top"><img src={senti[review.sentiment] || neutral} className="emotion-icon" alt={`${review.sentiment || "neutral"} sentiment`} /><span className={`sentiment-label sentiment-${senti[review.sentiment] ? review.sentiment : "neutral"}`}>{review.sentiment || "neutral"}</span>
        {review.verified_purchase && <span className="verified-badge">✓ Verified purchase</span>}
      </div>
      <div className="review-rating" aria-label={`${review.rating || "Unrated"} out of 5 stars`}>{"★".repeat(Number(review.rating || 0))}<span>{"☆".repeat(5 - Number(review.rating || 0))}</span><small>{review.rating ? `${review.rating}/5` : "Unrated"}</small></div>
      <p className="review-copy">“{review.review}”</p>
      {review.photos?.length > 0 && <div className="review-photos">{review.photos.map((photo, index) => <a href={photo} target="_blank" rel="noreferrer" key={photo}><img src={photo} alt={`Review photo ${index + 1}`} loading="lazy" /></a>)}</div>}
      <div className="review-author"><strong>{review.name || "A Best Cars driver"}</strong>{(review.car_make || review.car_model) && <span>{[review.car_year, review.car_make, review.car_model].filter(Boolean).join(" ")}</span>}<time dateTime={review.created_at}>{new Date(review.created_at).toLocaleDateString()}</time></div>
      {review.recommend !== null && <p className={`recommend-tag ${review.recommend ? "recommended" : ""}`}>{review.recommend ? "✓ Recommends this dealer" : "Does not recommend"}</p>}
      {response && <div className="dealer-response"><strong>Dealer response · {response.author}</strong><p>{response.text}</p></div>}
      <div className="review-actions">
        {user ? <button type="button" className={`review-action${voted ? " voted" : ""}`} onClick={helpful} disabled={voted}>👍 Helpful ({helpfulCount})</button> : <Link className="review-action" to="/login">👍 Helpful ({helpfulCount})</Link>}
        {user && <button type="button" className="review-action" onClick={() => { setReportOpen(!reportOpen); setReportMessage(""); }}>Report</button>}
      </div>
      {reportOpen && <form className="report-form" onSubmit={report}><label className="visually-hidden" htmlFor={`report-${review.id}`}>Report reason</label><select id={`report-${review.id}`} value={reason} onChange={(e) => setReason(e.target.value)} required><option value="">Choose a reason</option><option>Spam or advertising</option><option>Abusive or inappropriate</option><option>Appears to be fake</option><option>Other</option></select><button className="text-link" type="submit">Send report</button></form>}
      {isStaff && <form className="dealer-reply-form" onSubmit={postReply}><label className="visually-hidden" htmlFor={`reply-${review.id}`}>Official dealer response</label><textarea id={`reply-${review.id}`} placeholder="Write an official response…" maxLength={2000} value={reply} onChange={(e) => setReply(e.target.value)} required /><button className="text-link" type="submit">{response ? "Update response" : "Post dealer response"}</button></form>}
      {reportMessage && <p className="inline-message" role="status">{reportMessage}</p>}
      {replyMessage && <p className="form-error" role="alert">{replyMessage}</p>}
    </article>
  );
}

export function Dealer() {
  const { id } = useParams();
  const { user, isStaff } = useAuth();
  const [d, setD] = useState(null);
  const [reviews, setReviews] = useState([]);
  const [cars, setCars] = useState([]);
  const [reviewSort, setReviewSort] = useState("newest");
  const [reviewPage, setReviewPage] = useState(1);
  const [reviewPagination, setReviewPagination] = useState({ page: 1, pages: 0, total: 0 });
  const [reviewError, setReviewError] = useState("");
  useEffect(() => {
    api(`dealer/${id}`).then((r) => setD(r.dealer?.[0] ?? false));
    api(`cars/dealer/${id}`).then((r) => setCars(r.cars || []));
  }, [id]);
  useEffect(() => {
    let active = true;
    api(`reviews/dealer/${id}?sort=${reviewSort}&page=${reviewPage}&page_size=6`).then((r) => {
      if (!active) return;
      if (r.status === 200) {
        setReviews(r.reviews || []);
        setReviewPagination({ page: r.page, pages: r.pages, total: r.total });
        setReviewError("");
      } else setReviewError(r.message || "Could not load reviews.");
    });
    return () => { active = false; };
  }, [id, reviewSort, reviewPage]);
  if (d === false) return <section className="page-shell empty-state"><h1>Dealership not found</h1><Link className="button" to="/dealers">Browse dealerships</Link></section>;
  if (!d) return <div className="page-shell page-loading">Loading dealership…</div>;
  const lat = Number(d.lat);
  const lon = Number(d.long);
  const hasCoordinates = Number.isFinite(lat) && Number.isFinite(lon) && Math.abs(lat) <= 90 && Math.abs(lon) <= 180;
  const mapUrl = `https://www.openstreetmap.org/export/embed.html?bbox=${lon - .012}%2C${lat - .008}%2C${lon + .012}%2C${lat + .008}&layer=mapnik&marker=${lat}%2C${lon}`;
  const directionsUrl = `https://www.openstreetmap.org/directions?engine=fossgis_osrm_car&route=;${lat}%2C${lon}`;
  return (
    <section className="page-shell dealer-detail">
      <Link className="back-link" to="/dealers"><span aria-hidden="true">←</span> All dealerships</Link>
      <div className="dealer-hero">
        <div><span className="eyebrow">DEALERSHIP PROFILE</span><h1>{d.full_name}</h1><p className="dealer-location"><span aria-hidden="true">⌖</span> {d.city}, {d.state}</p><p className="dealer-address">{d.address}{d.zip ? ` · ${d.zip}` : ""}</p><p className="profile-rating">{d.average_rating ? `★ ${Number(d.average_rating).toFixed(1)}` : "No ratings yet"} <span>· {d.review_count} customer reviews</span></p></div>
        <div className="dealer-hero-actions"><FavoriteButton dealer={d} /><Link className="button" to={user ? `/postreview/${id}` : "/login"}><img src={reviewIcon} alt="" /> Write a review <span aria-hidden="true">→</span></Link></div>
      </div>
      <div className="dealer-info-grid">
        <section className="dealer-info-card"><span className="eyebrow">VISIT OR GET IN TOUCH</span><h2>Contact & hours</h2><p>{d.address}, {d.city}, {d.state} {d.zip}</p>{d.phone && <p><a href={`tel:${d.phone}`}>{d.phone}</a></p>}{d.website && <p><a href={d.website} target="_blank" rel="noreferrer">{d.website.replace(/^https?:\/\//, "")} ↗</a></p>}{d.hours && <p className="dealer-hours">{d.hours}</p>}{!d.phone && !d.website && !d.hours && <p className="muted-copy">Contact details haven’t been added yet.</p>}</section>
        {hasCoordinates && <section className="map-card"><iframe title={`Map showing ${d.full_name}`} src={mapUrl} loading="lazy" referrerPolicy="no-referrer" /><a href={directionsUrl} target="_blank" rel="noreferrer">Get directions ↗</a></section>}
      </div>
      <section className="content-section">
        <div className="section-heading"><div><span className="eyebrow">ON THE LOT</span><h2>Inventory</h2></div><span className="section-count">{cars.length} {cars.length === 1 ? "vehicle" : "vehicles"}</span></div>
        {cars.length ? <div className="inventory-wrap"><table className="inventory-table"><thead><tr><th>Vehicle</th><th>Year</th><th>Body type</th><th>Mileage</th></tr></thead><tbody>{cars.map((c) => <tr key={c.id}><td><strong>{c.make} {c.model}</strong></td><td>{c.year}</td><td>{c.body_type}</td><td>{Number(c.mileage).toLocaleString()} mi</td></tr>)}</tbody></table></div> : <p className="section-empty">No inventory is listed right now.</p>}
      </section>
      <section className="content-section">
        <div className="section-heading"><div><span className="eyebrow">DRIVER STORIES</span><h2>Customer reviews</h2></div><label className="review-sort">Sort reviews<select value={reviewSort} onChange={(e) => { setReviewSort(e.target.value); setReviewPage(1); }}><option value="newest">Newest</option><option value="oldest">Oldest</option><option value="rating">Highest rated</option><option value="helpful">Most helpful</option></select></label></div>
        {reviewError && <p className="form-error" role="alert">{reviewError}</p>}
        {reviews.length ? <div className="reviews-grid">{reviews.map((review) => <ReviewCard key={review.id} review={review} isStaff={isStaff} user={user} />)}</div> : !reviewError && <div className="section-empty"><p>No approved reviews yet. Be the first to share your experience.</p><Link className="text-link" to={user ? `/postreview/${id}` : "/login"}>Write the first review <span aria-hidden="true">→</span></Link></div>}
        {reviewPagination.pages > 1 && <nav className="pagination" aria-label="Review pages"><button disabled={reviewPage <= 1} onClick={() => setReviewPage(reviewPage - 1)}>← Previous</button><span>Page {reviewPagination.page} of {reviewPagination.pages} · {reviewPagination.total} reviews</span><button disabled={reviewPage >= reviewPagination.pages} onClick={() => setReviewPage(reviewPage + 1)}>Next →</button></nav>}
      </section>
    </section>
  );
}

export function PostReview() {
  const { id } = useParams();
  const { user, ready } = useAuth();
  const [dealer, setDealer] = useState(null);
  const [models, setModels] = useState([]);
  const [f, setF] = useState({ review: "", rating: "", recommend: "", purchase: false, purchase_date: "", car: "", car_year: "" });
  const [photos, setPhotos] = useState([]);
  const [err, setErr] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  useEffect(() => {
    api(`dealer/${id}`).then((r) => setDealer(r.dealer?.[0]));
    api("get_cars").then((r) => setModels([...new Set((r.CarModels || []).map((c) => `${c.CarMake}|${c.CarModel}`))].sort()));
  }, [id]);
  if (ready && !user) return <Navigate to="/login" replace />;
  const set = (k) => (e) => setF({ ...f, [k]: e.target.type === "checkbox" ? e.target.checked : e.target.value });
  async function submit(e) {
    e.preventDefault();
    setErr("");
    if (!f.rating) { setErr("Choose a star rating before submitting."); return; }
    if (photos.length > 3) { setErr("Choose up to 3 photos."); return; }
    if (photos.some((photo) => photo.size > 5 * 1024 * 1024)) { setErr("Each photo must be 5 MB or smaller."); return; }
    setSubmitting(true);
    const [car_make, car_model] = f.car ? f.car.split("|") : ["", ""];
    try {
      const body = new FormData();
      body.append("dealership", id);
      body.append("review", f.review);
      body.append("rating", f.rating);
      body.append("recommend", f.recommend);
      body.append("purchase", String(f.purchase));
      body.append("purchase_date", f.purchase ? f.purchase_date : "");
      body.append("car_make", car_make);
      body.append("car_model", car_model);
      body.append("car_year", f.purchase ? f.car_year : "");
      photos.forEach((photo) => body.append("photos", photo));
      const r = await api("add_review", body);
      if (r.status === 200) setSubmitted(true); else setErr(r.message || "Could not post review");
    } finally {
      setSubmitting(false);
    }
  }
  if (submitted) return <section className="auth-page review-page"><div className="auth-card review-confirmation"><span className="eyebrow">THANK YOU</span><h1>Your review is in moderation.</h1><p className="auth-intro">Thanks for sharing. A moderator will review your submission before it appears publicly.</p><Link className="button auth-submit" to={`/dealer/${id}`}>Return to dealership</Link></div></section>;
  return (
    <section className="auth-page review-page">
      <form className="auth-card review-form" onSubmit={submit}>
        <Link className="back-link" to={`/dealer/${id}`}><span aria-hidden="true">←</span> Back to dealership</Link>
        <span className="eyebrow">YOUR EXPERIENCE MATTERS</span>
        <h1>Write a review</h1>
        <p className="auth-intro">{dealer?.full_name ? `Tell other drivers about your visit to ${dealer.full_name}.` : "Tell other drivers about your dealership experience."}</p>
        <fieldset className="rating-picker"><legend>Your rating {f.rating && <span>({f.rating}/5)</span>}</legend><div role="radiogroup" aria-label="Rating from one to five stars">{[1, 2, 3, 4, 5].map((rating) => <button key={rating} type="button" className={Number(f.rating) >= rating ? "star-selected" : ""} onClick={() => { setF({ ...f, rating: String(rating) }); setErr(""); }} aria-label={`${rating} ${rating === 1 ? "star" : "stars"}`} aria-pressed={Number(f.rating) === rating}>★</button>)}</div></fieldset>
        <label className="form-field">Your review<textarea rows={5} maxLength={5000} placeholder="What stood out about your experience?" value={f.review} onChange={set("review")} required /><small>{f.review.length}/5,000 characters</small></label>
        <label className="form-field">Would you recommend this dealership?<select value={f.recommend} onChange={set("recommend")} required><option value="">Choose one</option><option value="true">Yes, I would recommend them</option><option value="false">No, I would not recommend them</option></select></label>
        <label className="form-field">Add photos (optional)<input type="file" accept="image/jpeg,image/png,image/webp" multiple onChange={(e) => { setPhotos([...e.target.files]); setErr(""); }} /><small>Up to 3 JPG, PNG, or WebP images, 5 MB each.</small></label>
        {photos.length > 0 && <p className="photo-count">{photos.length} of 3 photos selected</p>}
        <label className="purchase-toggle"><input type="checkbox" checked={f.purchase} onChange={set("purchase")} /><span><strong>I purchased a car here</strong><small>Share the vehicle details to help other shoppers.</small></span></label>
        {f.purchase && <div className="purchase-fields">
          <label className="form-field">Purchase date<input type="date" value={f.purchase_date} onChange={set("purchase_date")} required /></label>
          <label className="form-field">Vehicle<select value={f.car} onChange={set("car")} required><option value="">Select a vehicle</option>{models.map((m) => <option key={m} value={m}>{m.replace("|", " ")}</option>)}</select></label>
          <label className="form-field">Model year<input type="number" min="1990" max="2030" placeholder="e.g. 2022" value={f.car_year} onChange={set("car_year")} required /></label>
        </div>}
        {err && <p className="form-error" role="alert">{err}</p>}
        <button className="button auth-submit" type="submit" disabled={submitting}>{submitting ? "Posting review…" : "Post review"} <span aria-hidden="true">→</span></button>
      </form>
    </section>
  );
}

export function SavedDealers() {
  const { user, ready } = useAuth();
  const [dealers, setDealers] = useState([]);
  const [error, setError] = useState("");
  useEffect(() => {
    if (!user) return;
    api("saved_dealers").then((r) => {
      if (r.status === 200) setDealers(r.dealers || []);
      else setError(r.message || "Could not load saved dealerships.");
    });
  }, [user]);
  if (ready && !user) return <Navigate to="/login" replace />;
  return <section className="page-shell directory-page"><div className="page-heading"><span className="eyebrow">YOUR SHORTLIST</span><h1>Saved dealerships</h1><p>Keep the dealerships you’re considering close at hand.</p></div>
    {error && <p className="form-error" role="alert">{error}</p>}
    {dealers.length ? <div className="dealer-grid">{dealers.map((d) => <article className="dealer-card" key={d.id}><div className="dealer-card-top"><span className="dealer-monogram">{d.full_name.charAt(0)}</span><FavoriteButton dealer={d} onChange={(saved) => { if (!saved) setDealers((items) => items.filter((item) => item.id !== d.id)); }} /></div><h2><Link to={`/dealer/${d.id}`}>{d.full_name}</Link></h2><p className="dealer-location">{d.city}, {d.state}</p><p className="dealer-rating"><strong>{d.average_rating ? `★ ${Number(d.average_rating).toFixed(1)}` : "New"}</strong><span>{d.review_count} reviews</span></p><Link className="text-link" to={`/dealer/${d.id}`}>Explore dealer →</Link></article>)}</div> : !error && <div className="empty-state"><h2>No saved dealerships yet</h2><p>Save a dealer from the directory to build your shortlist.</p><Link className="button" to="/dealers">Browse dealerships</Link></div>}
  </section>;
}

export function Compare() {
  const [selected, setSelected] = useState(readCompareList);
  const [details, setDetails] = useState([]);
  const [error, setError] = useState("");
  const selectedIds = selected.map((d) => d.id).join(",");
  useEffect(() => {
    if (!selected.length) { setDetails([]); return; }
    Promise.all(selected.map(async (d) => {
      const [dealer, inventory] = await Promise.all([api(`dealer/${d.id}`), api(`cars/dealer/${d.id}`)]);
      if (dealer.status !== 200 || inventory.status !== 200) throw new Error(dealer.message || inventory.message || "Could not load dealer comparison.");
      return { ...(dealer.dealer?.[0] || d), cars: inventory.cars || [] };
    })).then((rows) => { setDetails(rows); setError(""); }).catch((failure) => {
      console.error("Could not load dealer comparison:", failure);
      setError(failure.message || "Could not load dealer comparison.");
    });
  }, [selectedIds]);
  function remove(id) {
    const next = selected.filter((item) => item.id !== id);
    setSelected(next);
    writeCompareList(next);
  }
  if (!selected.length) return <section className="page-shell empty-state"><h1>Compare dealerships</h1><p>Add up to three dealerships from the directory to compare their ratings, location, and inventory.</p><Link className="button" to="/dealers">Choose dealerships</Link></section>;
  return <section className="page-shell directory-page"><div className="page-heading"><span className="eyebrow">SIDE-BY-SIDE</span><h1>Compare dealerships</h1><p>Compare up to three dealers to help decide where to visit.</p></div>
    {error && <p className="form-error" role="alert">{error}</p>}
    <div className="comparison-wrap"><table className="comparison-table"><thead><tr><th>At a glance</th>{details.map((d) => <th key={d.id}><Link to={`/dealer/${d.id}`}>{d.full_name}</Link><button className="remove-compare" onClick={() => remove(d.id)}>Remove</button></th>)}</tr></thead><tbody>
      <tr><th>Location</th>{details.map((d) => <td key={d.id}>{d.city}, {d.state}<br />{d.address}</td>)}</tr>
      <tr><th>Average rating</th>{details.map((d) => <td key={d.id}>{d.average_rating ? `★ ${Number(d.average_rating).toFixed(1)} / 5` : "No ratings yet"}</td>)}</tr>
      <tr><th>Customer reviews</th>{details.map((d) => <td key={d.id}>{d.review_count || 0}</td>)}</tr>
      <tr><th>Inventory</th>{details.map((d) => <td key={d.id}>{d.cars?.length ?? d.inventory_count ?? 0} vehicles</td>)}</tr>
      <tr><th>Contact</th>{details.map((d) => <td key={d.id}>{d.phone ? <a href={`tel:${d.phone}`}>{d.phone}</a> : "Not listed"}{d.website && <><br /><a href={d.website} target="_blank" rel="noreferrer">Website ↗</a></>}</td>)}</tr>
      <tr><th>Actions</th>{details.map((d) => <td key={d.id}><Link className="text-link" to={`/dealer/${d.id}`}>View dealer →</Link></td>)}</tr>
    </tbody></table></div><Link className="back-link" to="/dealers">← Browse more dealerships</Link>
  </section>;
}

export function Moderation() {
  const { isStaff, ready } = useAuth();
  const [queue, setQueue] = useState({ reviews: [], reports: [] });
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [refresh, setRefresh] = useState(0);
  useEffect(() => {
    if (!isStaff) return;
    api("moderation").then((r) => {
      if (r.status === 200) { setQueue(r); setError(""); }
      else setError(r.message || "Could not load moderation queue.");
    });
  }, [isStaff, refresh]);
  async function moderate(path, action, success) {
    const r = await api(path, { action });
    if (r.status === 200) { setNotice(success); setRefresh((value) => value + 1); }
    else setError(r.message || "Moderation action failed.");
  }
  if (!ready) return <div className="page-shell page-loading">Checking moderator access…</div>;
  if (ready && !isStaff) return <section className="page-shell empty-state"><h1>Staff access required</h1><p>Review moderation is available to authorized moderators.</p><Link className="button" to="/">Back home</Link></section>;
  return <section className="page-shell moderation-page"><div className="page-heading"><span className="eyebrow">STAFF TOOLS</span><h1>Review moderation</h1><p>Approve reviews before publishing, verify purchase claims, and action reader reports.</p></div>
    {error && <p className="form-error" role="alert">{error}</p>}{notice && <p className="moderation-notice" role="status">{notice}</p>}
    <section className="moderation-section"><h2>Reviews awaiting action <span>{queue.reviews.length}</span></h2>{queue.reviews.length ? queue.reviews.map((r) => <article className="moderation-card" key={r.id}><div className="moderation-card-heading"><strong>{r.dealer}</strong><span>{r.rating}/5 · {new Date(r.created_at).toLocaleDateString()}</span></div><p>{r.text}</p>{r.photos.length > 0 && <div className="review-photos">{r.photos.map((src) => <a href={src} target="_blank" rel="noreferrer" key={src}><img src={src} alt="Review upload" /></a>)}</div>}<div className="moderation-actions"><button className="button" onClick={() => moderate(`moderation/reviews/${r.id}`, "approve", "Review approved.")}>Approve</button><button className="moderation-secondary" onClick={() => moderate(`moderation/reviews/${r.id}`, "reject", "Review rejected.")}>Reject</button>{r.purchase && !r.verified_purchase && <button className="moderation-secondary" onClick={() => moderate(`moderation/reviews/${r.id}`, "verify_purchase", "Purchase verified.")}>Verify purchase</button>}</div></article>) : <p className="section-empty">No reviews awaiting action.</p>}</section>
    <section className="moderation-section"><h2>Reader reports <span>{queue.reports.length}</span></h2>{queue.reports.length ? queue.reports.map((r) => <article className="moderation-card" key={r.id}><div className="moderation-card-heading"><strong>{r.dealer}</strong><span>Reported by {r.reporter}</span></div><blockquote>{r.review}</blockquote><p><strong>Reason:</strong> {r.reason}</p><div className="moderation-actions"><button className="button" onClick={() => moderate(`moderation/reports/${r.id}`, "resolve", "Report resolved; review removed.")}>Remove review</button><button className="moderation-secondary" onClick={() => moderate(`moderation/reports/${r.id}`, "dismiss", "Report dismissed.")}>Dismiss report</button></div></article>) : <p className="section-empty">No open reports.</p>}</section>
  </section>;
}
