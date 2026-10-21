from model.recommender import load_model, recommend_movies, search_movies, is_model_ready

load_model()
print("ready:", is_model_ready())
r = recommend_movies("Avatar", top_n=5)
print("keys:", sorted(r[0].keys()))
for x in r:
    print(f"{x['similarity_score']:.4f} {x['title']} :: {x['reason']}")
s = search_movies("batm", limit=5)
print("search keys:", sorted(s[0].keys()), "| score:", s[0]["similarity_score"], "| reason:", s[0]["reason"])
for x in s:
    print(x["title"], x.get("genres"))
print("reason key present:", "reason" in r[0], "| old key absent:", "recommendation_reason" not in r[0])
try:
    recommend_movies("")
except Exception as e:
    print("empty title ->", type(e).__name__, str(e)[:60])
try:
    recommend_movies("Avatar", top_n=0)
except Exception as e:
    print("top_n=0 ->", type(e).__name__, str(e)[:60])
try:
    recommend_movies("Avatar", year="abc")
except Exception as e:
    print("year=abc ->", type(e).__name__, str(e)[:60])
try:
    recommend_movies("Avatar", genre="Nope")
except Exception as e:
    print("genre=Nope ->", type(e).__name__, str(e)[:80])
try:
    recommend_movies("ZzzqNotAMovie")
except Exception as e:
    print("unknown ->", type(e).__name__, str(e)[:100])