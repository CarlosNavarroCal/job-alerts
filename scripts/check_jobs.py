import os, json, urllib.request
from datetime import datetime, timezone

LISTINGS = ("https://raw.githubusercontent.com/SimplifyJobs/Summer2027-Internships/"
            "refs/heads/dev/.github/scripts/listings.json")
SEEN_FILE = "seen.json"
WEBHOOK = os.environ["SLACK_WEBHOOK_URL"]

# Optional filters (leave empty to allow everything)
CATEGORIES = set()            # e.g. {"Software", "Quant"}
TERM_CONTAINS = ""            # e.g. "Summer 2027"

def wanted(j):
    if not (j.get("active") and j.get("is_visible")):
        return False
    if CATEGORIES and j.get("category") not in CATEGORIES:
        return False
    if TERM_CONTAINS and not any(TERM_CONTAINS in t for t in j.get("terms", [])):
        return False
    return True

def post(text):
    req = urllib.request.Request(
        WEBHOOK, json.dumps({"text": text}).encode(),
        {"Content-Type": "application/json"})
    urllib.request.urlopen(req)

def fmt(j):
    ts = int(j.get("date_posted", 0))
    fallback = datetime.fromtimestamp(ts, timezone.utc).strftime("%b %d, %Y")
    return (f"*{j['company_name']}*, {j['title']}\n"
            f"Posted <!date^{ts}^{{date_short_pretty}}|{fallback}>\n"
            f"<{j['url']}|Apply>")

listings = json.load(urllib.request.urlopen(LISTINGS))
current = {j["id"]: j for j in listings if wanted(j)}

first_run = not os.path.exists(SEEN_FILE)
seen = set() if first_run else set(json.load(open(SEEN_FILE)))
new = [j for i, j in current.items() if i not in seen]
new.sort(key=lambda j: j.get("date_posted", 0))

if new and not first_run:
    for i in range(0, len(new), 15):
        post("\n\n".join(fmt(j) for j in new[i:i + 15]))

json.dump(sorted(seen | set(current)), open(SEEN_FILE, "w"))
