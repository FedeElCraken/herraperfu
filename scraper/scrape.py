"""Lee la tienda Perfu Luxe y actualiza data/products.json (nuevos, cambios de precio, stock)."""
import json, re, sys, datetime, pathlib

URL = "https://perfu-luxe.callbell.shop/"
ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA, DEBUG = ROOT / "data", ROOT / "debug"

def parse_price(txt):
    m = re.search(r"\$\s*([\d.,]+)", txt or "")
    if not m:
        return None
    s = m.group(1).strip(".,")
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s or "." in s:
        sep = "," if "," in s else "."
        a, b = s.rsplit(sep, 1)
        s = a.replace(sep, "") + (b if len(b) == 3 else "." + b)
    try:
        return float(s)
    except ValueError:
        return None

# Cada tarjeta tiene un botón "Agregar por $X" o "Sin Stock". Se parte de ese botón y se
# sube hasta la tarjeta completa (el ancestro más grande que tiene un solo botón).
EXTRACT = r"""() => {
  const priceRe = /\$\s*[\d.,]+/;
  const skip = /^(\$|agregar|comprar|añadir|anadir|ver |agotado|sin stock|no disponible|-?\d+\s*%?$)/i;
  const bad = l => skip.test(l) || /^\W*nuevo\W*$/i.test(l);
  const cnt = e => ((e.innerText || "").match(/\$\s*[\d.,]+/g) || []).length;
  const ok = u => u && !u.startsWith("data:") && !/\.svg(\?|$)/i.test(u);
  const photoOf = card => {
    let best = "", area = 0;
    for (const n of [card, ...card.querySelectorAll("*")]) {
      const r = n.getBoundingClientRect(), a = r.width * r.height;
      const m = (getComputedStyle(n).backgroundImage || "").match(/url\(["']?([^"')]+)["']?\)/);
      const u = m ? m[1] : (n.tagName === "IMG" ? (n.currentSrc || n.src || n.getAttribute("data-src") || "") : "");
      if (ok(u) && a >= area) { best = u; area = a; }
    }
    return best;
  };
  const anchors = [], tw = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  for (let n; (n = tw.nextNode());)
    if (/^\s*(agregar por|sin stock)/i.test(n.textContent) && n.parentElement) anchors.push(n.parentElement);
  const count = e => anchors.filter(a => e.contains(a)).length;
  const seen = new Set(), out = [];
  for (const a of anchors) {
    let el = a;
    while (el.parentElement && el.parentElement !== document.body && count(el.parentElement) === 1) el = el.parentElement;
    if (seen.has(el)) continue;
    seen.add(el);
    const n = cnt(el);
    if (n < 1 || n > 4) continue;
    const txt = el.innerText || "";
    const lines = txt.split("\n").map(s => s.trim()).filter(Boolean);
    const pi = lines.findIndex(l => priceRe.test(l));
    if (pi < 1) continue;
    let name = "";
    for (let k = pi - 1; k >= 0; k--) if (lines[k].length >= 3 && !bad(lines[k])) { name = lines[k]; break; }
    if (!name) continue;
    out.push({ name, prices: lines.filter(l => priceRe.test(l)), img: photoOf(el), out: /agotad|sin stock|no disponible/i.test(txt) });
  }
  return out;
}"""

MORE = """() => { for (const b of document.querySelectorAll('button,a'))
  if (/^(ver|cargar|mostrar) m[aá]s/i.test((b.innerText || '').trim())) b.click(); }"""

def collect(page):
    found, still = {}, 0
    for _ in range(80):
        for it in page.evaluate(EXTRACT):
            vals = [v for v in map(parse_price, it["prices"]) if v]
            name = re.sub(r"\s+", " ", it["name"]).strip()
            if vals and name:
                img = it["img"] or found.get(name, {}).get("img", "")
                found[name] = {"name": name, "buy": min(vals), "img": img, "stock": not it["out"]}
        try:
            page.evaluate(MORE)
        except Exception:
            pass
        before = len(found)
        page.mouse.wheel(0, 2500)
        page.wait_for_timeout(900)
        still = still + 1 if len(found) == before else 0
        if still >= 5:
            break
    return list(found.values())

def load(p):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}

def main():
    from playwright.sync_api import sync_playwright
    DEBUG.mkdir(exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900}, locale="es-AR")
        page.goto(URL, wait_until="networkidle", timeout=90000)
        page.wait_for_selector("img", state="attached", timeout=30000)
        try:
            page.wait_for_function("document.body.innerText.includes('$')", timeout=45000)
        except Exception:
            pass
        page.wait_for_timeout(3000)
        page.screenshot(path=str(DEBUG / "pagina.png"))
        (DEBUG / "pagina.html").write_text(page.content(), encoding="utf-8")
        products = collect(page)
        browser.close()

    prev_doc = load(DATA / "products.json")
    prev = {p["name"]: p for p in prev_doc.get("products", [])}
    if len(products) < 5 or (prev and len(products) < len(prev) * 0.5):
        print(f"Solo se leyeron {len(products)} productos (antes {len(prev)}). No se guarda nada; mirá debug/.")
        sys.exit(1)

    known = load(DATA / "known.json")
    first_run = not known
    today = datetime.date.today().isoformat()
    for p in products:
        old = prev.get(p["name"])
        p["status"] = "new" if (p["name"] not in known and not first_run) else "same"
        if old and old["buy"] != p["buy"]:
            p["status"] = "up" if p["buy"] > old["buy"] else "down"
            p["prev_buy"] = old["buy"]
        known.setdefault(p["name"], today)
    names = {p["name"] for p in products}
    removed = [n for n in prev if n not in names]

    DATA.mkdir(exist_ok=True)
    out = {"updated": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
           "first_run": first_run, "products": sorted(products, key=lambda p: p["name"].lower()), "removed": removed}
    (DATA / "products.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    (DATA / "known.json").write_text(json.dumps(known, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"OK: {len(products)} perfumes, {sum(p['status']=='new' for p in products)} nuevos, {len(removed)} salieron.")

if __name__ == "__main__":
    main()
