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
            print(f"Login Status: {resp.status_code}")
            if resp.status_code == 200:
                token = resp.json()["access_token"]
                headers = {"Authorization": f"Bearer {token}"}
                
                # Check dashboard 15
                d_resp = await client.get("http://superset:8088/api/v1/dashboard/15", headers=headers)
                print(f"Dashboard 15 Detail Status: {d_resp.status_code}")
                if d_resp.status_code == 200:
                    print(f"Dashboard 15 Detail: {json.dumps(d_resp.json(), indent=2)}")
                else:
                    print(f"Dashboard 15 Detail Error: {d_resp.text}")
                
                # Check dashboard list
                l_resp = await client.get("http://superset:8088/api/v1/dashboard/?q=(columns:!(uuid,id))", headers=headers)
                print(f"Dashboard List Status: {l_resp.status_code}")
                if l_resp.status_code == 200:
                    print(f"Dashboard List: {json.dumps(l_resp.json(), indent=2)}")
            else:
                print(f"Login Error: {resp.text}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_superset())
