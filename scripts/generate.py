import copy
import html
import json
import os
import re
import shutil
from pathlib import Path
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = BASE_DIR / "_template"
TEMPLATE_FILE = TEMPLATE_DIR / "index.html"
DATA_FILE = BASE_DIR / "data" / "clients.json"
ASSETS_DIR = BASE_DIR / "assets"
OUTPUT_DIR = BASE_DIR / "public"

# Base URL opsional untuk og:image absolut (otomatis terbaca di Cloudflare Pages lewat CF_PAGES_URL)
SITE_URL = (os.environ.get("SITE_URL") or os.environ.get("CF_PAGES_URL") or "").rstrip("/")

RESERVED_SLUGS = {"_template", "scripts", "data", "assets", "public", ".git", ".github"}
ALLOWED_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg", ".avif", ".ico"}

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
HEX_COLOR_PATTERN = re.compile(r"^#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?$")
WHATSAPP_PATTERN = re.compile(r"^\d{8,15}$")
ICON_PATTERN = re.compile(r"^fa-[a-z0-9-]+$")

REQUIRED_CONFIG_KEYS = {
    "namaBisnis",
    "kategori",
    "tagline",
    "warnaUtama",
    "warnaHover",
    "fotoHero",
    "whatsapp",
    "pesanDefaultWA",
    "layanan",
    "alamat",
    "jamBuka",
    "linkGoogleMaps",
}


def validate_http_url(url, slug, field_label):
    """Pastikan URL eksternal hanya memakai skema http/https dengan host yang valid."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError(
            f"URL tidak valid untuk '{slug}' ({field_label}): '{url}' (harus https:// atau http://)"
        )
    return url


def resolve_asset_path(raw_value, slug, field_label):
    """Ubah nama file lokal (mis. 'hero.jpg') menjadi './assets/hero.jpg' dengan proteksi path traversal."""
    if not raw_value:
        return ""

    value = str(raw_value).strip()
    if value.startswith(("http://", "https://")):
        return validate_http_url(value, slug, field_label)

    # Tolak skema berbahaya seperti javascript:, data:, file:
    if ":" in value.split("/")[0]:
        raise ValueError(
            f"Skema URL tidak diizinkan untuk '{slug}' ({field_label}): '{value}'"
        )

    cleaned = value.lstrip("./")
    if cleaned.startswith("assets/"):
        cleaned = cleaned[len("assets/") :]

    client_assets_root = (ASSETS_DIR / slug).resolve()
    expected_file = (client_assets_root / cleaned).resolve()

    if not expected_file.is_relative_to(client_assets_root):
        raise ValueError(
            f"Path traversal terdeteksi untuk '{slug}' ({field_label}): '{value}'"
        )

    if expected_file.suffix.lower() not in ALLOWED_IMAGE_EXTS:
        raise ValueError(
            f"Ekstensi file gambar tidak diizinkan untuk '{slug}' ({field_label}): '{expected_file.suffix}'"
        )

    if not expected_file.is_file() or expected_file.is_symlink():
        raise FileNotFoundError(
            f"Aset gambar tidak ditemukan untuk '{slug}' ({field_label}): "
            f"taruh file di 'assets/{slug}/{cleaned}' atau gunakan URL https://"
        )

    rel_posix = expected_file.relative_to(client_assets_root).as_posix()
    return f"./assets/{rel_posix}"


def to_absolute_og_url(asset_url, slug):
    """Pastikan og:image memakai URL absolut jika SITE_URL / CF_PAGES_URL tersedia."""
    if not asset_url or asset_url.startswith(("http://", "https://")):
        return asset_url
    if SITE_URL:
        rel = asset_url.lstrip("./")
        return f"{SITE_URL}/{slug}/{rel}"
    return asset_url


def copy_client_assets(slug, client_output_dir):
    """Salin file gambar valid di assets/<slug>/ ke public/<slug>/assets/ (abaikan dotfile & symlink)."""
    src_dir = (ASSETS_DIR / slug).resolve()
    if not src_dir.is_dir():
        return 0

    dst_dir = client_output_dir / "assets"
    copied = 0
    for item in src_dir.rglob("*"):
        if (
            item.is_file()
            and not item.is_symlink()
            and not item.name.startswith(".")
            and item.suffix.lower() in ALLOWED_IMAGE_EXTS
        ):
            rel_path = item.relative_to(src_dir)
            target = dst_dir / rel_path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)
            copied += 1
    return copied


def serialize_safe_json(data):
    """Serialisasi JSON aman untuk disisipkan langsung di dalam tag <script>."""
    return (
        json.dumps(data, ensure_ascii=False, indent=6)
        .replace("</", "<\\/")
        .replace("<!--", "<\\!--")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def prepare_client_config(slug, raw_config):
    """Validasi & sanitasi seluruh field config klien sebelum build."""
    config = copy.deepcopy(raw_config)

    for color_key in ("warnaUtama", "warnaHover"):
        color_val = str(config.get(color_key, "")).strip()
        if not HEX_COLOR_PATTERN.match(color_val):
            raise ValueError(
                f"Format warna hex tidak valid untuk '{slug}' ({color_key}): '{color_val}'"
            )
        config[color_key] = color_val

    wa_val = str(config.get("whatsapp", "")).strip()
    if not WHATSAPP_PATTERN.match(wa_val):
        raise ValueError(
            f"Nomor WhatsApp tidak valid untuk '{slug}': '{wa_val}' (harus 8–15 digit angka, mis. 62812xxx)"
        )
    config["whatsapp"] = wa_val

    config["linkGoogleMaps"] = validate_http_url(
        str(config.get("linkGoogleMaps", "")).strip(), slug, "linkGoogleMaps"
    )

    for i, item in enumerate(config.get("keunggulan", [])):
        icon_val = str(item.get("icon", "")).strip()
        if not ICON_PATTERN.match(icon_val):
            raise ValueError(
                f"Nama ikon Font Awesome tidak valid untuk '{slug}' (keunggulan[{i}].icon): '{icon_val}'"
            )
        item["icon"] = icon_val

    config["logo"] = resolve_asset_path(config.get("logo", ""), slug, "logo")
    config["fotoHero"] = resolve_asset_path(config.get("fotoHero", ""), slug, "fotoHero")

    for i, item in enumerate(config.get("layanan", [])):
        if item.get("foto"):
            item["foto"] = resolve_asset_path(item["foto"], slug, f"layanan[{i}].foto")

    resolved_galeri = []
    for i, entry in enumerate(config.get("galeri", [])):
        if isinstance(entry, str):
            resolved_galeri.append(resolve_asset_path(entry, slug, f"galeri[{i}]"))
        elif isinstance(entry, dict) and entry.get("foto"):
            new_entry = dict(entry)
            new_entry["foto"] = resolve_asset_path(
                entry["foto"], slug, f"galeri[{i}].foto"
            )
            resolved_galeri.append(new_entry)
    config["galeri"] = resolved_galeri

    return config


def build_client_pages():
    if not TEMPLATE_FILE.exists():
        raise FileNotFoundError(f"Template tidak ditemukan: {TEMPLATE_FILE}")
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Data klien tidak ditemukan: {DATA_FILE}")

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        clients = json.load(f)

    if not isinstance(clients, list):
        raise ValueError("Format data/clients.json harus berupa JSON array.")

    template_html = TEMPLATE_FILE.read_text(encoding="utf-8")
    config_placeholder = "{{CONFIG_JSON}}"
    if config_placeholder not in template_html:
        raise ValueError(f"Placeholder '{config_placeholder}' tidak ditemukan di template.")

    # Validasi seluruh data & aset klien sebelum menyentuh folder output
    seen_slugs = set()
    validated_clients = []
    for idx, client in enumerate(clients):
        if "slug" not in client or "config" not in client:
            raise ValueError(f"Entri ke-{idx} harus memiliki key 'slug' dan 'config'.")

        slug = str(client["slug"]).strip().lower()
        if not slug or slug in RESERVED_SLUGS or not SLUG_PATTERN.match(slug):
            raise ValueError(f"Slug tidak valid atau terlarang: '{slug}'")
        if slug in seen_slugs:
            raise ValueError(f"Slug duplikat ditemukan: '{slug}'")
        seen_slugs.add(slug)

        raw_config = client["config"]
        missing_keys = REQUIRED_CONFIG_KEYS - set(raw_config.keys())
        if missing_keys:
            raise ValueError(
                f"Klien '{slug}' kekurangan field wajib: {sorted(missing_keys)}"
            )

        resolved_config = prepare_client_config(slug, raw_config)
        validated_clients.append((slug, resolved_config))

    # Bersihkan folder public/ agar klien yang dihapus/diubah slug-nya tidak meninggalkan file usang
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Salin file root statis untuk Cloudflare Pages (index.html, 404.html, _headers)
    static_files = {
        "home.html": "index.html",
        "404.html": "404.html",
        "_headers": "_headers",
    }
    for src_name, dst_name in static_files.items():
        src_path = TEMPLATE_DIR / src_name
        if src_path.exists():
            shutil.copy2(src_path, OUTPUT_DIR / dst_name)
            print(f"[OK] Copied: /{dst_name}")

    for slug, config in validated_clients:
        client_dir = OUTPUT_DIR / slug
        client_dir.mkdir(parents=True, exist_ok=True)

        asset_count = copy_client_assets(slug, client_dir)

        meta_title = f"{config['namaBisnis']} - {config['kategori']}"
        og_image = to_absolute_og_url(config["fotoHero"], slug)
        favicon_tag = (
            f'<link rel="icon" href="{html.escape(config["logo"], quote=True)}" />'
            if config.get("logo")
            else ""
        )

        replacements = {
            "{{META_TITLE}}": html.escape(meta_title, quote=True),
            "{{META_DESCRIPTION}}": html.escape(config["tagline"], quote=True),
            "{{META_IMAGE}}": html.escape(og_image, quote=True),
            "{{THEME_COLOR}}": config["warnaUtama"],
            "{{THEME_HOVER}}": config["warnaHover"],
            "{{FAVICON_TAG}}": favicon_tag,
            "{{CONFIG_JSON}}": serialize_safe_json(config),
        }

        new_html = template_html
        for placeholder, value in replacements.items():
            new_html = new_html.replace(placeholder, value)

        (client_dir / "index.html").write_text(new_html, encoding="utf-8")
        asset_info = f" (+{asset_count} aset)" if asset_count else ""
        print(f"[OK] Generated: /{slug}/index.html{asset_info}")

    print(f"\nSelesai! Total {len(validated_clients)} halaman klien siap di folder: public/")


if __name__ == "__main__":
    build_client_pages()
