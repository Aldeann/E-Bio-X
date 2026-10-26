import json
from urllib import request

base = "http://localhost:5000"
data = json.dumps({"email":"guru1@ebiox.com","password":"123123123"}).encode()
req = request.Request(base+"/api/login", data=data, headers={"Content-Type":"application/json"})
with request.urlopen(req, timeout=30) as r:
    tok = json.loads(r.read().decode())["access_token"]

req = request.Request(base+"/api/materials/107", headers={"Authorization":"Bearer "+tok})
with request.urlopen(req, timeout=120) as r:
    j = json.loads(r.read().decode())

with open(r"D:\Aldeann\virus_material_full.json","w",encoding="utf-8") as f:
    json.dump(j,f,indent=2,ensure_ascii=False)
print("OK", len(j.get("material",j).get("sections",[])))
