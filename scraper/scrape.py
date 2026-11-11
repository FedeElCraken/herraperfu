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

# Busca "tarjetas": el ancestro más chico de cada <img> que tenga precio y nombre.
EXTRACT = r"""() => {
  const priceRe = /\$\s*[\d.,]+/, skip = /^(\$|agregar|comprar|añadir|anadir|ver |agotado|sin stock|no disponible|\d+$)/i;
  const out = [];
  for (const img of document.querySelectorAll("img")) {
    let el = img.parentElement;
    while (el && el !== document.body && el.querySelectorAll("img").length === 1) {
      const lines = (el.innerText || "").split("\n").map(s => s.trim()).filter(Boolean);
      const prices = lines.filter(l => priceRe.test(l));
      const names = lines.filter(l => !priceRe.test(l) && l.length >= 3 && !skip.test(l));
      if (prices.length && names.length) {
        const txt = el.innerText || "";
        out.push({
          name: names[0], prices,
          img: img.currentSrc || img.src || img.getAttribute("data-src") || "",
          out: /agotad|sin stock|no disponible/i.test(txt) || !!el.querySelector("button:disabled")
        });
        break;
      }
      el = el.parentElement;
    }
  }
  return out;
}"""

def collect(page):
    found, still = {}, 0
    for _ in range(80):
        for it in page.evaluate(EXTRACT):
            vals = [v for v in map(parse_price, it["prices"]) if v]
            name = re.sub(r"\s+", " ", it["name"]).strip()
            if vals and name:
                found[name] = {"name": name, "buy": min(vals), "img": it["img"], "stock": not it["out"]}
        for btn in page.query_selector_all("button, a"):
            try:
                if re.search(r"(ver|cargar|mostrar) m[aá]s", btn.inner_text() or "", re.I):
                    btn.click(timeout=1500)
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
        page.screenshot(path=str(DEBUG / "pagina.png"))
        (DEBUG / "pagina.html").write_text(page.content(), encoding="utf-8")
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
