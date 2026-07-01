import httpx
import asyncio
import json

async def check_superset():
    url = "http://superset:8088/api/v1/security/login"
    payload = {
        "username": "admin",
        "password": "admin",
        "provider": "db",
        "refresh": True
    }
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                token = resp.json()["access_token"]
                headers = {"Authorization": f"Bearer {token}"}
                
                # Check dashboard list - specifically for ID 15 and its UUID
                l_resp = await client.get("http://superset:8088/api/v1/dashboard/?q=(columns:!(id,uuid,dashboard_title))", headers=headers)
                print(f"List Result: {json.dumps(l_resp.json(), indent=2)}")
                
                # Try ID 15 detail again but check full keys
                d_resp = await client.get("http://superset:8088/api/v1/dashboard/15", headers=headers)
                print(f"ID 15 Detail Keys: {list(d_resp.json().get('result', {}).keys())}")
                if "uuid" in d_resp.json().get('result', {}):
                    print(f"UUID found in detail: {d_resp.json()['result']['uuid']}")
            else:
                print(f"Login Error: {resp.text}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_superset())
