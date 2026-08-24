"""
author:poch1 
saluran : https://whatsapp.com/channel/0029Vb8LEvhKWEKsTzWeNw30
 
 tutor make nya : 👇
    python3 animein_scraper.py home
    python3 animein_scraper.py search "one piece"
    python3 animein_scraper.py search "frieren" --sort rating --genres 14
    python3 animein_scraper.py genres
    python3 animein_scraper.py schedule --day JUM
    python3 animein_scraper.py detail 426
    python3 animein_scraper.py episodes 426 --last 5
    python3 animein_scraper.py stream 7364
    python3 animein_scraper.py watch 426 --ep 1 --quality 720p
    python3 animein_scraper.py download 7364 -q 480p -o one_piece_ep1.mp4
    python3 animein_scraper.py export "naruto" --out naruto.csv
"""

import argparse
import csv
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

PROXY = "https://www.animeinweb.com/api/proxy"
IMG_BASE = "https://xyz-api.animein.net"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0 Safari/537.36"
SLEEP = 0.35


def api(path, params=None, timeout=20):
    """GET ke backend AnimeIn via proxy. Path tanpa awalan /3/2 boleh."""
    url = PROXY + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "application/json",
        "Referer": "https://www.animeinweb.com/",
        "x-proxy-secret": "animein-secure-proxy-key-123",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            j = json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise SystemExit(f"[HTTP {e.code}] {url}")
    if j.get("error") or j.get("status") != 200:
        raise SystemExit(f"[API error] {path}: {j.get('message', j)}")
    return j.get("data")


def fix_img(u):
    if not u:
        return u
    if u.startswith("http"):
        return u
    return IMG_BASE + ("" if u.startswith("/") else "/") + u


def movie_row(m):
    g = m.get("genre") or []
    if isinstance(g, str):
        genres = g
    elif isinstance(g, list):
        genres = ",".join(x.get("name", "") if isinstance(x, dict) else str(x) for x in g)
    else:
        genres = str(g)
    return {
        "id": m.get("id"),
        "title": m.get("title"),
        "type": m.get("type"),
        "year": m.get("year"),
        "status": m.get("status") or m.get("key_status"),
        "views": m.get("views"),
        "favorites": m.get("favorites"),
        "studio": m.get("studio"),
        "genres": genres,
        "poster": fix_img(m.get("image_poster")),
        "synopsis": (m.get("synopsis") or "")[:200].replace("\n", " "),
        "url": f"https://www.animeinweb.com/anime/{m.get('id')}",
    }


CSV_FIELDS = ["id", "title", "type", "year", "status", "views", "favorites",
              "studio", "genres", "poster", "synopsis", "url"]


def write_csv(rows, path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


# ------------------------------- endpoints --------------------------------

def ep_home(day="1", limit="16"):
    return api("/3/2/home/data", {"day": day, "limit": limit})

def ep_explore(page=0, sort="views", keyword="", genre_in=None):
    p = {"page": page, "sort": sort, "keyword": keyword}
    if genre_in:
        p["genre_in"] = ",".join(genre_in) if isinstance(genre_in, list) else genre_in
    return api("/3/2/explore/movie", p)

def ep_genres():
    return api("/3/2/explore/genre")

def ep_schedule(day="RANDOM"):
    return api("/3/2/schedule/data", {"day": day})

def ep_detail(movie_id):
    return api(f"/3/2/movie/detail/{movie_id}")

def ep_episode_list(movie_id, page=0):
    return api(f"/3/2/movie/episode/{movie_id}", {"page": page})

def ep_stream(episode_id):
    return api(f"/3/2/episode/streamnew/{episode_id}")


def pick_stream(stream_data, quality=None):
    """Pilih link terbaik dari daftar server.
    Prioritas: type=direct > semi; kualitas sesuai (default: tertinggi)."""
    servers = stream_data.get("server") or []
    if not servers:
        return None
    if quality:
        cands = [s for s in servers if (s.get("quality") or "").lower() == quality.lower()]
    else:
        cands = []
    if not cands:
        order = {"1080p": 5, "720p": 4, "480p": 3, "360p": 2, "240p": 1}
        cands = sorted(servers, key=lambda s: order.get((s.get("quality") or "").lower(), 0),
                       reverse=True)
    cands = sorted(cands, key=lambda s: 0 if (s.get("type") == "direct") else 1)
    return cands[0]


def find_episode(movie_id, episode_index):
    """Cari episode berdasarkan nomor index (list paginasi 30/halaman,
    urut TERBARU duluan -> indeks menurun seiring halaman bertambah).
    Pakai binary search setelah ekspansi eksponensial mencari batas atas."""
    target = float(episode_index)
    page_cache = {}

    def get_page(p):
        if p not in page_cache:
            page_cache[p] = ep_episode_list(movie_id, p).get("episode") or []
        return page_cache[p]

    def match(eps):
        for e in eps:
            try:
                if abs(float(e.get("index")) - target) < 1e-9:
                    return e
            except (TypeError, ValueError):
                pass
        return None

    eps0 = get_page(0)
    if not eps0:
        return None
    if match(eps0):
        return match(eps0)
    if target > float(eps0[0].get("index")):
        return None  # lebih baru dari yang tersedia

    # cari batas atas: halaman pertama yang kosong
    hi = 1
    while get_page(hi):
        if match(get_page(hi)):
            return match(get_page(hi))
        hi *= 2
        if hi > 5000:
            break
    lo = hi // 2
    # binary search di [lo, hi)
    while lo < hi:
        mid = (lo + hi) // 2
        eps = get_page(mid)
        if not eps:
            hi = mid
            continue
        first_p = float(eps[0].get("index"))
        last_p = float(eps[-1].get("index"))
        m = match(eps)
        if m:
            return m
        if target > first_p:
            hi = mid          # target lebih baru -> halaman lebih awal
        else:
            lo = mid + 1      # target lebih lama -> halaman lebih akhir
    return None


def resolve_watch(movie_id, episode_index, quality=None):
    """movie_id + nomor episode -> (info episode, data stream, link terpilih)."""
    detail = ep_detail(movie_id)
    movie = detail.get("movie") or {}
    target = find_episode(movie_id, episode_index)
    if target is None:
        raise SystemExit(f"Episode {episode_index} tidak ditemukan untuk movie {movie_id}")
    time.sleep(SLEEP)
    stream = ep_stream(target["id"])
    link = pick_stream(stream, quality)
    return movie, target, stream, link


# --------------------------------- CLI -------------------------------------

def main():
    ap = argparse.ArgumentParser(description="Scraper AnimeIn (animeinweb.com)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("home", help="data halaman utama")
    p.add_argument("--day", default="1")
    p.add_argument("--limit", default="16")

    p = sub.add_parser("search", help="cari anime (explore/movie)")
    p.add_argument("keyword")
    p.add_argument("--page", type=int, default=0)
    p.add_argument("--sort", default="views",
                   help="views (default) / rating / new")
    p.add_argument("--genres", default=None, help="id genre dipisah koma (cek: genres)")

    sub.add_parser("genres", help="daftar genre + id")

    p = sub.add_parser("schedule", help="jadwal tayang")
    p.add_argument("--day", default="RANDOM",
                   choices=["SEN", "SEL", "RAB", "KAM", "JUM", "SAB", "MIN", "RANDOM"])

    p = sub.add_parser("detail", help="detail anime")
    p.add_argument("movie_id", type=int)

    p = sub.add_parser("episodes", help="daftar episode (paginasi 30/halaman, terbaru duluan)")
    p.add_argument("movie_id", type=int)
    p.add_argument("--page", type=int, default=0, help="halaman (0=terbaru)")
    p.add_argument("--last", type=int, default=0, help="tampilkan N episode terakhir dari halaman ini")

    p = sub.add_parser("stream", help="server & link MP4 untuk 1 episode")
    p.add_argument("episode_id", type=int)
    p.add_argument("--quality", default=None, help="360p/480p/720p (default: terbaik)")

    p = sub.add_parser("watch", help="movie_id + no. episode -> link MP4 langsung")
    p.add_argument("movie_id", type=int)
    p.add_argument("--ep", type=int, default=1)
    p.add_argument("--quality", default=None)
    p.add_argument("--json", action="store_true", help="output mentah (semua server)")

    p = sub.add_parser("download", help="download MP4 episode")
    p.add_argument("episode_id", type=int)
    p.add_argument("-q", "--quality", default=None)
    p.add_argument("-o", "--out", default=None)

    p = sub.add_parser("export", help="export hasil search ke CSV")
    p.add_argument("keyword")
    p.add_argument("--pages", type=int, default=1)
    p.add_argument("--sort", default="views")
    p.add_argument("--out", default="animein_export.csv")

    args = ap.parse_args()

    if args.cmd == "home":
        d = ep_home(args.day, args.limit)
        # slider = banner promo (bukan anime)
        for s in d.get("slider") or []:
            print(f"BANNER: {s.get('type')} -> {s.get('link')}")
        for k in ("hot", "new", "today", "popular", "trailer", "waiting", "random"):
            items = d.get(k) or []
            print(f"\n== {k} ({len(items)}) ==")
            for m in items[:8]:
                if not m.get("title"):
                    continue
                print(f"   {str(m.get('id')):>5}  {str(m.get('views') or '-'):>10} views  "
                      f"{(m.get('title') or '')[:55]}")
        return

    elif args.cmd == "search":
        d = ep_explore(args.page, args.sort, args.keyword,
                       args.genres.split(",") if args.genres else None)
        items = d.get("movie") or []
        print(f"{len(items)} hasil halaman {args.page} (sort={args.sort}):\n")
        for m in items:
            print(f"   {m.get('id'):>5}  {str(m.get('year') or '-'):>5}  "
                  f"{str(m.get('views') or '0'):>10} views  {m.get('title')[:60]}")

    elif args.cmd == "genres":
        for g in ep_genres().get("genre") or []:
            print(f"   {g['id']:>3}  {g.get('group', ''):<8} {g['name']}")

    elif args.cmd == "schedule":
        items = ep_schedule(args.day).get("movie") or []
        print(f"Jadwal {args.day}: {len(items)} anime\n")
        for m in items:
            print(f"   {m.get('id'):>5}  {m.get('title')[:60]}  "
                  f"({m.get('type')}, {m.get('year')})")

    elif args.cmd == "detail":
        d = ep_detail(args.movie_id)
        m, e = d.get("movie") or {}, d.get("episode") or {}
        g = m.get("genre") or []
        print(f"ID        : {m.get('id')}")
        print(f"Title     : {m.get('title')}")
        print(f"Type/Year : {m.get('type')} / {m.get('year')}  status: {m.get('status')}")
        print(f"Studio    : {m.get('studio')}")
        print(f"Views     : {m.get('views')}  favorites: {m.get('favorites')}")
        print(f"Aired     : {m.get('aired_start')} -> {m.get('aired_end')}")
        gn = g if isinstance(g, str) else [x.get("name", "") if isinstance(x, dict) else str(x) for x in g]
        print(f"Genres    : " + (gn if isinstance(gn, str) else ", ".join(gn)))
        print(f"Poster    : {fix_img(m.get('image_poster'))}")
        print(f"Synopsis  : {(m.get('synopsis') or '')[:300]}...")
        if e:
            print(f"\nEpisode pertama: {e.get('title')} (id={e.get('id')}, views={e.get('views')})")

    elif args.cmd == "episodes":
        items = ep_episode_list(args.movie_id, args.page).get("episode") or []
        if not items:
            raise SystemExit(f"Halaman {args.page} kosong (coba page lebih kecil)")
        print(f"Page {args.page}: {len(items)} episode (urut terbaru\n")
        for e in (items[-args.last:] if args.last else items):
            print(f"   ep {str(e.get('index')):>6}  id={e.get('id'):>7}  "
                  f"views={str(e.get('views') or 0):>8}  {e.get('key_time', '')}")

    elif args.cmd in ("stream", "watch", "download"):
        if args.cmd == "watch":
            movie, target, d, link = resolve_watch(args.movie_id, args.ep, args.quality)
            if args.json:
                print(json.dumps(d, ensure_ascii=False, indent=1))
            else:
                print(f"{movie.get('title')} - {target.get('title')}")
                print(f"Episode id : {target.get('id')}")
                print(f"URL watch  : https://www.animeinweb.com/anime/{movie.get('id')}?ep={target.get('index')}")
                if link:
                    print(f"[{link.get('quality')}] {link.get('name')} ({link.get('type')})")
                    print(link.get("link"))
                print(f"\nSemua server: {len(d.get('server') or [])} "
                      "(pakai: stream %s)" % target.get("id"))
            return
        if args.cmd == "download":
            d = ep_stream(args.episode_id)
            link = pick_stream(d, args.quality)
        else:
            d = ep_stream(args.episode_id)
        if args.cmd == "stream":
            print(f"Episode: {d.get('episode', {}).get('title')} (id={d.get('episode', {}).get('id')})\n")
            for s in d.get("server") or []:
                mark = " *" if s is pick_stream(d, args.quality) else ""
                print(f"   [{s.get('quality'):>5}] {s.get('name'):<10} {s.get('type'):<7} "
                      f"{s.get('key_file_size') or '?'} MB{mark}")
                print(f"          {s.get('link')}")
        else:  # download
            if not link:
                raise SystemExit("Tidak ada stream")
            out = args.out or f"animein_ep{args.episode_id}_{link.get('quality')}.mp4"
            url = link["link"]
            print(f"Download [{link.get('quality')}] {link.get('name')} -> {out}")
            req = urllib.request.Request(url, headers={"User-Agent": UA,
                                                        "Referer": "https://www.animeinweb.com/"})
            with urllib.request.urlopen(req, timeout=120) as r, open(out, "wb") as f:
                total = int(r.headers.get("Content-Length") or 0)
                done = 0
                while True:
                    chunk = r.read(1024 * 256)
                    if not chunk:
                        break
                    f.write(chunk)
                    done += len(chunk)
                    if total:
                        print(f"\r   {done/1e6:8.1f} / {total/1e6:.1f} MB "
                              f"({100*done//total}%)", end="", flush=True)
            print(f"\nSelesai: {out} ({done/1e6:.1f} MB)")

    elif args.cmd == "export":
        rows, page = [], 0
        while True:
            d = ep_explore(page, args.sort, args.keyword)
            items = d.get("movie") or []
            if not items:
                break
            rows += [movie_row(m) for m in items]
            page += 1
            if page >= args.pages or len(items) < 18:
                break
        write_csv(rows, args.out)
        print(f"Tersimpan {len(rows)} baris -> {args.out}")
        for r in rows[:5]:
            print(f"   {r['id']:>5}  {r['title'][:60]}")


if __name__ == "__main__":
    main()
