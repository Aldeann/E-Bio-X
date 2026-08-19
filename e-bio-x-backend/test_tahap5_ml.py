# ============================================================
# TAHAP 5 - End-to-end API tests against the live server.
#
# Uses REAL data only. With a small dev dataset the training pipeline
# correctly reports INSUFFICIENT_DATA instead of faking metrics; the
# positive ML paths are covered deterministically by test_ml_unit.py.
# ============================================================
import requests

BASE = "http://127.0.0.1:5000"
PASS = "123123123"

results = []


def check(name, cond, extra=""):
    results.append((name, bool(cond), extra))
    mark = "PASS" if cond else "FAIL"
    print(f"[{mark}] {name}" + (f"  ({extra})" if extra else ""))


def login(email):
    r = requests.post(f"{BASE}/api/login", json={"email": email, "password": PASS}, timeout=10)
    assert r.status_code == 200, f"login {email}: {r.status_code} {r.text}"
    return r.json()["access_token"]


def auth(t):
    return {"Authorization": f"Bearer {t}"}


T = {}
for email in ("guru1@ebiox.com", "guru2test@ebiox.com", "murid1@ebiox.com", "murid2@ebiox.com", "wahyuniami@example.org"):
    T[email] = login(email)

MURID1 = 72      # in course 6 (teacher guru1)
MURID2 = 73      # in course 6
OUTSIDER = 4     # wahyuniami, courses 1&2, NOT course 6

print('===== SECURITY =====')
check("student cannot train model", requests.post(f"{BASE}/api/ml/train", headers=auth(T["murid1@ebiox.com"]), timeout=20).status_code == 403)
check("student cannot retrain model", requests.post(f"{BASE}/api/ml/retrain", headers=auth(T["murid2@ebiox.com"]), timeout=20).status_code == 403)
check("student cannot see teacher ml analytics", requests.get(f"{BASE}/api/teacher/analytics/ml", headers=auth(T["murid1@ebiox.com"]), timeout=20).status_code == 403)
check("student cannot predict others via ml endpoint", requests.post(f"{BASE}/api/ml/predict/72", headers=auth(T["murid1@ebiox.com"]), timeout=20).status_code == 403)
check("teacher cannot predict student outside class", requests.post(f"{BASE}/api/ml/predict/{OUTSIDER}", headers=auth(T["guru2test@ebiox.com"]), timeout=20).status_code == 403)

print('===== TRAINING (honest small-data path) =====')
tr = requests.post(f"{BASE}/api/ml/train", headers=auth(T["guru1@ebiox.com"]), timeout=60)
check("train endpoint 200", tr.status_code == 200, tr.text[:120])
tj = tr.json() if tr.status_code == 200 else {}
check("decision_tree status reported", "decision_tree" in tj and "status" in tj["decision_tree"])
check("kmeans status reported", "kmeans" in tj and "status" in tj["kmeans"])
if tj.get("decision_tree", {}).get("status") == "READY":
    check("dt metrics only when available", "metrics" in tj["decision_tree"])
else:
    check("insufficient data handled honestly", tj["decision_tree"]["status"] == "INSUFFICIENT_DATA")

print('===== STUDENT PROFILE & RECOMMENDATIONS =====')
prof = requests.get(f"{BASE}/api/student/learning-profile", headers=auth(T["murid1@ebiox.com"]), timeout=30)
check("student learning-profile 200", prof.status_code == 200)
pj = prof.json()
check("profile status valid", pj.get("status") in ("READY", "INSUFFICIENT_DATA", "MODEL_UNAVAILABLE"))
if pj.get("status") == "READY":
    check("mastery label present", bool(pj.get("mastery_label")))
    check("factors explainable", isinstance(pj.get("factors"), list))
else:
    check("insufficient message present", bool(pj.get("message")))

recs = requests.get(f"{BASE}/api/student/recommendations", headers=auth(T["murid1@ebiox.com"]), timeout=30)
check("student recommendations 200", recs.status_code == 200)
rj = recs.json()
rec_list = rj.get("recommendations") or []
check("recommendations list returned", isinstance(rec_list, list))
if rec_list:
    first = rec_list[0]
    check("recommendation has material + reasons", bool(first.get("material_id")) and isinstance(first.get("reasons"), list))
    click = requests.post(f"{BASE}/api/student/recommendations/click",
                          headers=auth(T["murid1@ebiox.com"]),
                          json={"material_id": first["material_id"]}, timeout=20)
    check("recommendation click recorded", click.status_code == 200, click.text[:120])
else:
    print("  (no recommendations row to click - acceptable on tiny dataset)")

print('===== TEACHER ML ANALYTICS =====')
ml = requests.get(f"{BASE}/api/teacher/analytics/ml", headers=auth(T["guru1@ebiox.com"]), timeout=30)
check("teacher ml analytics 200", ml.status_code == 200)
mj = ml.json()
for key in ("analyzed", "insufficient_data", "mastery_distribution", "profile_distribution",
            "top_recommendations", "topics_needing_reinforcement", "model", "clusters"):
    check(f"ml analytics has {key}", key in mj)
ms = requests.get(f"{BASE}/api/teacher/analytics/ml/mastery", headers=auth(T["guru1@ebiox.com"]), timeout=30)
check("teacher ml mastery 200", ms.status_code == 200 and "mastery_distribution" in ms.json())
cm = requests.get(f"{BASE}/api/teacher/analytics/ml/clusters", headers=auth(T["guru1@ebiox.com"]), timeout=30)
check("teacher ml clusters 200", cm.status_code == 200)
if cm.json().get("status") == "READY":
    check("cluster silhouette info present", "silhouette" in cm.json())

print('===== REGRESSION (prompt 1-4 untouched) =====')
check("student dashboard still works", requests.get(f"{BASE}/api/student/dashboard", headers=auth(T["murid1@ebiox.com"]), timeout=20).status_code == 200)
check("student quizzes still works", requests.get(f"{BASE}/api/student/quizzes", headers=auth(T["murid1@ebiox.com"]), timeout=20).status_code == 200)
check("teacher analytics still works", requests.get(f"{BASE}/api/teacher/analytics", headers=auth(T["guru1@ebiox.com"]), timeout=20).status_code == 200)
check("feature dataset endpoint works", requests.get(f"{BASE}/api/analytics/dataset", headers=auth(T["guru1@ebiox.com"]), timeout=30).status_code == 200)
check("materials list still works", requests.get(f"{BASE}/api/materials", headers=auth(T["guru1@ebiox.com"]), timeout=20).status_code == 200)

print("\n===== SUMMARY =====")
passed = sum(1 for _, ok, _ in results if ok)
print(f"TOTAL: {len(results)}  PASS: {passed}  FAIL: {len(results) - passed}")
for name, ok, extra in results:
    if not ok:
        print(f"  FAIL> {name} {extra}")
import sys
sys.exit(1 if passed != len(results) else 0)