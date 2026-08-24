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

T = {k: login(k) for k in [
    "guru1@ebiox.com", "guru2test@ebiox.com", "guru@ebiox.com",
    "murid1@ebiox.com",     # 72, in course 6
    "murid2@ebiox.com",     # 73, in course 6
    "wahyuniami@example.org",  # 4, course 1&2, NOT course 6
]}

MATERIAL = 28  # VIRUS, owned by guru1 (71), course 6, section 19, contents 35(text)36(pdf)38(video)39(question)
SECTION = 19
VIDEO_CONTENT = 38
QUESTION_CONTENT = 39

print("===== TRACKING (murid1) =====")
r = requests.post(f"{BASE}/api/materials/{MATERIAL}/session/ping", headers=auth(T["murid1@ebiox.com"]), json={}, timeout=10)
check("session ping 200 + session_id", r.status_code == 200 and r.json().get("session_id"), str(r.json()))
check("ping total_seconds int", isinstance(r.json().get("total_seconds"), int))

r = requests.post(f"{BASE}/api/materials/{MATERIAL}/activity", headers=auth(T["murid1@ebiox.com"]),
                  json={"event_type": "content_viewed", "section_id": SECTION, "content_id": QUESTION_CONTENT}, timeout=10)
check("activity content_viewed 201", r.status_code == 201, str(r.json()))

r = requests.post(f"{BASE}/api/materials/{MATERIAL}/activity", headers=auth(T["murid1@ebiox.com"]),
                  json={"event_type": "not-a-real-event"}, timeout=10)
check("invalid event_type rejected 400", r.status_code == 400)

r = requests.post(f"{BASE}/api/materials/{MATERIAL}/activity", headers=auth(T["murid1@ebiox.com"]),
                  json={"event_type": "section_completed", "section_id": 999}, timeout=10)
check("foreign section rejected 404", r.status_code == 404)

r = requests.post(f"{BASE}/api/materials/{MATERIAL}/video-progress", headers=auth(T["murid1@ebiox.com"]),
                  json={"section_id": SECTION, "content_id": VIDEO_CONTENT, "video_duration": 300,
                        "watched_duration": 285, "last_position": 285, "completed": True}, timeout=10)
check("video-progress 200 completed", r.status_code == 200 and r.json().get("completed"))

r = requests.post(f"{BASE}/api/materials/{MATERIAL}/video-progress", headers=auth(T["murid1@ebiox.com"]),
                  json={"section_id": SECTION, "content_id": 99999, "video_duration": 30,
                        "watched_duration": 0, "last_position": 0}, timeout=10)
check("video-progress foreign content 404", r.status_code == 404)

r = requests.get(f"{BASE}/api/materials/{MATERIAL}/content-track", headers=auth(T["murid1@ebiox.com"]), timeout=10)
check("content-track lists viewed", r.status_code == 200 and len(r.json()) >= 1)

print("===== STUDENT DASHBOARD / PROGRESS =====")
r = requests.get(f"{BASE}/api/student/dashboard", headers=auth(T["murid1@ebiox.com"]), timeout=10)
check("student dashboard 200", r.status_code == 200)
check("dashboard summary has materials_total", "materials_total" in r.json()["summary"])
check("dashboard continue_learning list", isinstance(r.json().get("continue_learning"), list))

r = requests.get(f"{BASE}/api/student/progress", headers=auth(T["murid1@ebiox.com"]), timeout=10)
check("progress list 200", r.status_code == 200 and "materials" in r.json())
check("progress row has mastery_label", all("mastery" in m for m in r.json()["materials"]))

r = requests.get(f"{BASE}/api/student/progress/{MATERIAL}", headers=auth(T["murid1@ebiox.com"]), timeout=10)
check("material detail 200", r.status_code == 200)
d = r.json()
check("detail has sections", "sections" in d and len(d["sections"]) >= 1)
check("detail has mastery_rows", "mastery_rows" in d and len(d["mastery_rows"]) >= 1)
check("detail has quiz_performance", "quiz_performance" in d)
check("detail has video stats", "video" in d)
check("detail has activities", isinstance(d.get("activities"), list))
check("detail has interactive", "interactive" in d)

r = requests.get(f"{BASE}/api/student/performance", headers=auth(T["murid1@ebiox.com"]), timeout=10)
check("performance 200 + quizzes list", r.status_code == 200 and "quizzes" in r.json())

r = requests.get(f"{BASE}/api/student/activity", headers=auth(T["murid1@ebiox.com"]), timeout=10)
check("activity 200 + total", r.status_code == 200 and r.json()["total"] >= 1)

print("===== STUDENT SECURITY =====")
r = requests.get(f"{BASE}/api/student/dashboard", headers=auth(T["guru1@ebiox.com"]), timeout=10)
check("teacher blocked from student dashboard 403", r.status_code == 403)

# student not in course 6 cannot read material 28 detail
r = requests.get(f"{BASE}/api/student/progress/{MATERIAL}", headers=auth(T["wahyuniami@example.org"]), timeout=10)
check("student outside course blocked from material detail 403", r.status_code == 403)

print("===== FEATURE EXTRACTION =====")
r = requests.post(f"{BASE}/api/analytics/features/{MATERIAL}", headers=auth(T["murid1@ebiox.com"]), timeout=10)
check("features 200", r.status_code == 200, r.text[:200])
f = r.json()["features"]
for col in ["progress_percentage", "learning_seconds", "interactive_answered", "interactive_accuracy",
            "content_viewed", "content_total", "view_ratio", "video_completion_avg", "quiz_attempts",
            "quiz_average", "quiz_best", "mastery_score", "mastery_label", "status_learning",
            "days_since_first_access", "active_days", "activity_count"]:
    check(f"feature column {col}", col in f)

r = requests.get(f"{BASE}/api/analytics/dataset", headers=auth(T["guru1@ebiox.com"]), timeout=30)
check("teacher dataset 200 + columns", r.status_code == 200 and "columns" in r.json() and r.json()["count"] >= 1)

r = requests.post(f"{BASE}/api/analytics/features/{MATERIAL}", headers=auth(T["guru1@ebiox.com"]), timeout=10)
check("teacher blocked from student features 403", r.status_code == 403)

print("===== TEACHER ANALYTICS =====")
r = requests.get(f"{BASE}/api/teacher/analytics", headers=auth(T["guru1@ebiox.com"]), timeout=15)
check("overview 200", r.status_code == 200, r.text[:120])
check("overview has mastery_distribution", "mastery_distribution" in r.json())

r = requests.get(f"{BASE}/api/teacher/analytics/options", headers=auth(T["guru1@ebiox.com"]), timeout=15)
check("options 200 + courses/materials", r.status_code == 200 and len(r.json()["courses"]) >= 1 and len(r.json()["materials"]) >= 1)

r = requests.get(f"{BASE}/api/teacher/analytics/materials", headers=auth(T["guru1@ebiox.com"]), timeout=20)
check("materials summary 200", r.status_code == 200 and isinstance(r.json(), list) and len(r.json()) >= 1, r.text[:120])
check("materials summary fields", bool(r.json()) and "interactive" in r.json()[0] and "quiz" in r.json()[0])

r = requests.get(f"{BASE}/api/teacher/analytics/materials/{MATERIAL}", headers=auth(T["guru1@ebiox.com"]), timeout=20)
check("material analytics 200", r.status_code == 200, r.text[:200])
ma = r.json()
for k in ["section_completion", "per_student", "interactive", "quiz", "mastery_distribution", "status_distribution", "difficulty"]:
    check(f"material analytics has {k}", k in ma)

r = requests.get(f"{BASE}/api/teacher/analytics/students", headers=auth(T["guru1@ebiox.com"]), timeout=20)
check("students table 200 + pagination", r.status_code == 200 and "total_pages" in r.json() and r.json()["total"] >= 3,
      f"total={r.json().get('total')}")

r = requests.get(f"{BASE}/api/teacher/analytics/students?search=murid&page=1&per_page=5", headers=auth(T["guru1@ebiox.com"]), timeout=20)
check("students search filter", r.status_code == 200 and all("urid" in s["name"] or "urid" in s["email"] for s in r.json()["students"]))

r = requests.get(f"{BASE}/api/teacher/analytics/students/72", headers=auth(T["guru1@ebiox.com"]), timeout=20)
check("student detail 200 (own student)", r.status_code == 200 and "summary" in r.json())

# cari siswa di luar cakupan guru1 secara dinamis (tahan terhadap data demo)
own_ids = set()
r = requests.get(f"{BASE}/api/teacher/analytics/students?per_page=500", headers=auth(T["guru1@ebiox.com"]), timeout=20)
if r.status_code == 200:
    own_ids = {s.get("student_id") for s in r.json().get("students", [])}
outside_code = None
for sid in [4] + [i for i in range(2, 90) if i != 71]:
    if sid in own_ids:
        continue
    rr = requests.get(f"{BASE}/api/teacher/analytics/students/{sid}", headers=auth(T["guru1@ebiox.com"]), timeout=10)
    outside_code = rr.status_code
    if rr.status_code == 403:
        break
check("student detail outside teacher course 403", outside_code == 403, f"last={outside_code}")

r = requests.get(f"{BASE}/api/teacher/analytics/topics", headers=auth(T["guru1@ebiox.com"]), timeout=20)
check("topics 200", r.status_code == 200 and isinstance(r.json(), list))

r = requests.get(f"{BASE}/api/teacher/analytics/difficulty", headers=auth(T["guru1@ebiox.com"]), timeout=20)
check("difficulty 200", r.status_code == 200 and "interactive" in r.json() and "quiz" in r.json())

print("===== TEACHER SECURITY =====")
r = requests.get(f"{BASE}/api/teacher/analytics/materials/{MATERIAL}", headers=auth(T["guru2test@ebiox.com"]), timeout=15)
check("other teacher blocked from material analytics 403", r.status_code == 403)

r = requests.get(f"{BASE}/api/teacher/analytics/students/72", headers=auth(T["guru2test@ebiox.com"]), timeout=15)
check("other teacher blocked from student detail 403", r.status_code == 403)

r = requests.get(f"{BASE}/api/teacher/analytics", headers=auth(T["murid1@ebiox.com"]), timeout=15)
check("student blocked from teacher analytics 403", r.status_code == 403)

r = requests.get(f"{BASE}/api/teacher/analytics/materials/1", headers=auth(T["guru1@ebiox.com"]), timeout=15)
check("course teacher can manage legacy material after backfill 200", r.status_code == 200)

r = requests.get(f"{BASE}/api/teacher/analytics/materials/28", headers=auth(T["guru2test@ebiox.com"]), timeout=15)
check("other teacher blocked from class material analytics 403", r.status_code == 403)

print("===== QUIZ FLOWS STILL WORK (regression) =====")
quizzes = requests.get(f"{BASE}/api/student/quizzes", headers=auth(T["murid1@ebiox.com"]), timeout=15)
check("student quizzes 200", quizzes.status_code == 200)

# Full interactive quiz attempt cycle for material 28 (creates a new quiz as test data)
quiz_id = None
try:
    r = requests.post(f"{BASE}/api/teacher/quizzes", headers=auth(T["guru1@ebiox.com"]),
                      json={"title": "Tahap4 Regression Quiz", "material_id": MATERIAL,
                            "duration": 30, "passing_grade": 75, "max_attempts": 5,
                            "shuffle_questions": False, "shuffle_options": False}, timeout=15)
    check("create quiz (material-linked)", r.status_code in (200, 201), r.text[:200])
    if r.status_code in (200, 201):
        quiz_id = r.json().get("id") or r.json().get("quiz", {}).get("id")
    if not quiz_id:
        quiz_id = r.json().get("data", {}).get("id")
    check("quiz created with id", bool(quiz_id), str(quiz_id))

    if quiz_id:
        q1 = requests.post(f"{BASE}/api/teacher/quizzes/{quiz_id}/questions", headers=auth(T["guru1@ebiox.com"]),
                           json={"question_text": "Test Q1", "question_type": "multiple_choice", "difficulty": "easy",
                                 "points": 10, "options": [
                                     {"option_text": "A", "is_correct": True}, {"option_text": "B", "is_correct": False}]}, timeout=15)
        q2 = requests.post(f"{BASE}/api/teacher/quizzes/{quiz_id}/questions", headers=auth(T["guru1@ebiox.com"]),
                           json={"question_text": "Test Q2", "question_type": "multiple_choice", "difficulty": "hard",
                                 "points": 10, "options": [
                                     {"option_text": "A", "is_correct": False}, {"option_text": "B", "is_correct": True}]}, timeout=15)
        check("add quiz questions", q1.status_code in (200, 201) and q2.status_code in (200, 201),
              f"q1={q1.status_code} q2={q2.status_code}")
        pub = requests.post(f"{BASE}/api/teacher/quizzes/{quiz_id}/publish", headers=auth(T["guru1@ebiox.com"]),
                            json={"status": "published"}, timeout=15)
        check("publish quiz", pub.status_code == 200, pub.text[:150])

        start = requests.post(f"{BASE}/api/student/quizzes/{quiz_id}/start", headers=auth(T["murid1@ebiox.com"]), timeout=15)
        check("student start attempt", start.status_code in (200, 201), start.text[:150])
        attempt_id = start.json().get("attempt_id") or start.json().get("attempt", {}).get("id")
        check("attempt id present", bool(attempt_id), str(attempt_id))
        qs = start.json().get("questions") or start.json().get("attempt", {}).get("questions") or []
        check("attempt has questions", len(qs) >= 1)

        if attempt_id and qs:
            for i, qst in enumerate(qs):
                correct = 0 if i == 0 else 1  # q1 correct=A(first), q2 correct=B(second)
                ans = requests.post(f"{BASE}/api/student/attempts/{attempt_id}/answer",
                                    headers=auth(T["murid1@ebiox.com"]),
                                    json={"question_id": qst["question_id"],
                                          "selected_option_id": (qst.get("options") or [])[correct]["option_id"]},
                                    timeout=15)
            sub = requests.post(f"{BASE}/api/student/attempts/{attempt_id}/submit", headers=auth(T["murid1@ebiox.com"]), timeout=15)
            check("student submit attempt", sub.status_code == 200, sub.text[:200])
            pct = sub.json().get("result", {}).get("percentage", sub.json().get("percentage"))
            check("attempt scored 100%", pct == 100.0 or pct == 100, str(pct))
        res = requests.get(f"{BASE}/api/student/quizzes/{quiz_id}/result", headers=auth(T["murid1@ebiox.com"]), timeout=15)
        check("quiz result endpoint", res.status_code == 200)
        tq = requests.get(f"{BASE}/api/teacher/quizzes/{quiz_id}/analytics", headers=auth(T["guru1@ebiox.com"]), timeout=15)
        check("teacher quiz analytics (legacy route intact)", tq.status_code == 200, tq.text[:120])
        ta = requests.get(f"{BASE}/api/teacher/analytics/quizzes/{quiz_id}", headers=auth(T["guru1@ebiox.com"]), timeout=15)
        check("teacher analytics per quiz", ta.status_code == 200 and "per_question" in ta.json() and "difficulty" in ta.json())
        check("quiz difficulty breakdown has easy+hard", "easy" in ta.json()["difficulty"] and "hard" in ta.json()["difficulty"])

        # activity logging from quiz hooks
        acts = requests.get(f"{BASE}/api/student/activity?material_id={MATERIAL}&per_page=50", headers=auth(T["murid1@ebiox.com"]), timeout=15)
        events = [a["event_type"] for a in acts.json().get("activities", [])]
        check("quiz_started activity logged", "quiz_started" in events)
        check("quiz_submitted activity logged", "quiz_submitted" in events)
except Exception as e:
    print(f"  ERROR creating/taking quiz: {e!r}")

print("\n===== SUMMARY =====")
passed = sum(1 for _, ok, _ in results if ok)
failed = sum(1 for _, ok, _ in results if not ok)
print(f"TOTAL: {len(results)}  PASS: {passed}  FAIL: {failed}")
for name, ok, extra in results:
    if not ok:
        print(f"  FAIL> {name} {extra}")
import sys
sys.exit(1 if failed else 0)