import socket
import uvicorn

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

if __name__ == "__main__":
    local_ip = get_local_ip()
    print("=" * 65)
    print("  ServEase FastAPI Backend Server (Development)")
    print("=" * 65)
    print(f"  • Localhost (Laptop):     http://127.0.0.1:8000")
    print(f"  • Wi-Fi LAN (Phones):     http://{local_ip}:8000")
    print(f"  • Android Emulator:       http://10.0.2.2:8000")
    print(f"  • API Documentation:      http://{local_ip}:8000/docs")
    print("=" * 65)
    print("Starting server on 0.0.0.0:8000...")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
