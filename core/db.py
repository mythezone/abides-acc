import redis

r = redis.Redis(host="127.0.0.1", port=6379, decode_responses=True)
r.set("name", "runoob")
print(r["name"])
print(r.get("name"))
print(type(r.get("name")))
