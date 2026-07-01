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
                
                # Check ALL dashboards with all columns
                l_resp = await client.get("http://superset:8088/api/v1/dashboard/", headers=headers)
                data = l_resp.json()
                print(f"Count: {data.get('count')}")
                for d in data.get('result', []):
                    print(f"ID: {d.get('id')}, UUID: {d.get('uuid')}, Title: {d.get('dashboard_title')}")
                
            else:
                print(f"Login Error: {resp.text}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_superset())
