import os, json, time, urllib.request, urllib.error
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


def fmt(j):
    ts = int(j.get("date_posted", 0))
    fallback = datetime.fromtimestamp(ts, timezone.utc).strftime("%b %d, %Y")
    return (f"*{j['company_name']}*, {j['title']}\n"
            f"Posted <!date^{ts}^{{date_short_pretty}}|{fallback}>\n"
            f"<{j['url']}|Apply>")


def post(text):
    """Send one message. Returns True on success, False if it gave up."""
    body = json.dumps({"text": text}).encode()
    for _ in range(5):
        req = urllib.request.Request(
            WEBHOOK, body, {"Content-Type": "application/json"})
        try:
            urllib.request.urlopen(req)
            return True
        except urllib.error.HTTPError as e:
            if e.code == 429:                      # rate limited: wait and retry
                wait = int(e.headers.get("Retry-After", 5))
                time.sleep(wait + 1)
                continue
            print(f"Slack error {e.code}: {e.read().decode()[:200]}")
            return False
        except urllib.error.URLError as e:         # network hiccup: retry
            print(f"Network error: {e}")
            time.sleep(3)
    return False


def save(seen):
    with open(SEEN_FILE, "w") as f:
        json.dump(sorted(seen), f)


listings = json.load(urllib.request.urlopen(LISTINGS))
current = {j["id"]: j for j in listings if wanted(j)}

# First run: record what exists now, post nothing
if not os.path.exists(SEEN_FILE):
    save(set(current))
    print(f"First run: recorded {len(current)} existing postings, nothing posted.")
    raise SystemExit

seen = set(json.load(open(SEEN_FILE)))
new = [j for i, j in current.items() if i not in seen]
new.sort(key=lambda j: j.get("date_posted", 0))    # oldest first
print(f"{len(new)} new posting(s) to send.")

for j in new:
    if not post(fmt(j)):
        print("Stopping early; remaining jobs will be retried next run.")
        break
    seen.add(j["id"])
    save(seen)                                     # persist after every success
    time.sleep(1.1)                                # stay under Slack's ~1 msg/sec

save(seen)
