import requests
from PIL import Image
from io import BytesIO

URL = "http://172.30.1.60:81/stream"
resp = requests.get(URL, stream=True, timeout=5)
buf = b''
for chunk in resp.iter_content(chunk_size=1024):
    buf += chunk
    a = buf.find(b'\xff\xd8')
    b = buf.find(b'\xff\xd9')
    if a != -1 and b != -1:
        jpg = buf[a:b+2]
        buf = buf[b+2:]
        img = Image.open(BytesIO(jpg))
        print("✅ 프레임 읽음:", img.size)
        break
