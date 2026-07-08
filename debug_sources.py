import requests, json

H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

print("=== Safebooru full check ===")
try:
    r = requests.get("https://safebooru.org/index.php?page=dapi&s=post&q=index&json=1&tags=Rurouni_Kenshin&limit=2", headers=H, timeout=15)
    data = r.json()
    for p in data:
        print(f"Keys: {list(p.keys())}")
        print(f"  file_url: {p.get('file_url','')[:80]}")
        print(f"  sample_url: {p.get('sample_url','')[:80]}")
        print(f"  source: {p.get('source','')[:80]}")
except Exception as e:
    print(f"Error: {e}")

print("\n=== AniList Character lookup ===")
try:
    q = "query($s:String){Page(page:1,perPage:3){characters(search:$s){name{full}image{large}}}}"
    r = requests.post("https://graphql.anilist.co", json={"query": q, "variables": {"s": "Kenshin"}}, headers={"Content-Type": "application/json"}, timeout=15)
    print(f"Status: {r.status_code}")
    chars = r.json().get("data",{}).get("Page",{}).get("characters",[])
    print(f"Characters: {len(chars)}")
    for c in chars[:2]:
        print(f'  {c.get("name",{}).get("full","")} -> {c.get("image",{}).get("large","")[:60]}')
except Exception as e:
    print(f"Error: {e}")

print("\n=== Zerochan specific thumb check ===")
try:
    r = requests.get("https://www.zerochan.net/Rurouni+Kenshin?s=rating", headers=H, timeout=15)
    # Look for thumb images
    import re
    # Try different patterns
    for pat_name, pat in [
        ("full", r'(https://static\.zerochan\.net/[^"\'\s\\]+\.(?:jpg|jpeg|png|webp))'),
        ("thumb", r'(https://static\.zerochan\.net/\d+/\d+\.thumb\.\d+\.(?:jpg|jpeg|png|webp))'),
    ]:
        urls = re.findall(pat, r.text)
        print(f"{pat_name}: {len(urls)} found")
        for u in urls[:3]:
            print(f"  {u[:80]}")
except Exception as e:
    print(f"Error: {e}")
