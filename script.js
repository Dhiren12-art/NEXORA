
const menuBtn = document.getElementById("menuBtn");
const navbar = document.getElementById("navbar");

// Mobile navigation menu
menuBtn.addEventListener("click", function() {
  navbar.classList.toggle("show");
});

// Search articles
const searchBox = document.querySelector(
  '.hero input[type="search"]'
);

searchBox.addEventListener("input", function() {
  const query = searchBox.value.toLowerCase();

  document.querySelectorAll(".card").forEach(card => {
    const text = card.textContent.toLowerCase();

    card.style.display = text.includes(query)
      ? "block"
      : "none";
  });
});

// Navigation highlight
document.querySelectorAll("nav a").forEach(link => {
  link.addEventListener("click", function() {
    document.querySelectorAll("nav a").forEach(item => {
      item.style.color = "#cccccc";
    });

    this.style.color = "#D6AD55";
  });
});

console.log("Welcome to NEXORA!");
// NEXORA: Load published articles
async function loadNexoraArticles() {
  const section = document.getElementById("liveArticles");

  if (!section || !window.supabase) return;

  const SUPABASE_URL = "https://brqsolcojfxldrxfdnax.supabase.co";
  const SUPABASE_KEY = "sb_publishable_Se2OBOPmRlGVSIvMY-1W-w_tdJq3chD";

  const db = window.supabase.createClient(
    SUPABASE_URL,
    SUPABASE_KEY
  );

  const { data, error } = await db
    .from("cricket_feed")
    .select("id, title, summary, source_name, source_url, image_url, published_at, created_at")
    .order("published_at", { ascending: false });

  if (error) {
    section.innerHTML = "<p>Unable to load articles.</p>";
    console.error(error);
    return;
  }

  section.innerHTML = "<h2>Latest Articles from NEXORA</h2>";

  if (!data || data.length === 0) {
    section.innerHTML += "<p>No articles published yet.</p>";
    return;
  }

  data.forEach(article => {
    const card = document.createElement("a");
card.href = "read-article.html?slug=" + encodeURIComponent(article.slug);
card.className = "news-card";
card.style.display = "block";
card.style.textDecoration = "none";
card.style.color = "inherit";

    const title = document.createElement("h3");
    title.textContent = article.title;

    const description = document.createElement("p");
    description.textContent = article.excerpt;

    const category = document.createElement("span");
    category.textContent = article.category;

    card.append(category, title, description);

    if (article.image_url) {
      const image = document.createElement("img");
      image.src = article.image_url;
      image.alt = article.title;
      card.prepend(image);
    }

    section.appendChild(card);
  });
}

loadNexoraArticles();
