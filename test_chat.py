import asyncio, httpx, json

BASE = "http://api:8000"

async def send(token, msg):
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(timeout=40) as c:
        res = await c.post(f"{BASE}/v1/chat/stream", json={"message": msg, "metadata": {}}, headers=headers)
        for line in res.text.splitlines():
            if line.startswith("data: "):
                d = json.loads(line[6:])
                if d["type"] == "report":
                    return d["report"]
    return None

async def main():
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.post(f"{BASE}/v1/auth/login", data={"username": "admin@omnibrain.local", "password": "OmniBrain@2026"})
        token = r.json()["data"]["access_token"]

    for label, msg in [
        ("MINIMIZE ALL WINDOWS", "Minimize all windows"),
        ("OPEN NOTEPAD", "Open notepad"),
        ("TYPE IN NOTEPAD", "Type in notepad: Hello Sir, I am Sara!"),
    ]:
        print(f"\n=== TEST: {label} ===")
        result = await send(token, msg)
        if result:
            print(f"  Status  : {result['status']}")
            print(f"  Done    : {result['what_was_done']}")
            print(f"  Problems: {result['any_problems']}")
        else:
            print("  No report received")
        await asyncio.sleep(3)

asyncio.run(main())
