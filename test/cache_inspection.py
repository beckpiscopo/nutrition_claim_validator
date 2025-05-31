import diskcache

cache = diskcache.Cache('.cache')

print("Number of cached items:", len(cache))
for key in cache.iterkeys():
    print(f"Key: {key}")
    value = cache[key]
    print(f"Value: {value}\n")
    