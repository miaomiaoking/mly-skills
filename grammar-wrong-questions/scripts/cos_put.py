"""步骤 4：上传文件到 ima 的 COS（两种模式都支持）
用法：python cos_put.py            # 读 <cwd>/.grammar_wrong/cos_job.json

create_media 可能返回两种模式：
  A) upload_mode=1 + upload_url.presigned_url → job 里放 {"file","file_size","presigned_url"}
     本脚本直接用该 URL + auth_headers 直传
  B) upload_mode=0 + cos_credential → job 里放 secret_id/secret_key/token/bucket_name/region/cos_key
     SDK 在沙箱装不上，本脚本用 q-sign-algorithm=sha1 手动签名 PUT
"""
import hashlib, hmac, json, time, urllib.parse, urllib.request
from common import load_config

cfg = load_config()
JOB = cfg["_data"] / "cos_job.json"
job = json.load(open(JOB, encoding="utf-8"))
src = cfg["_out"] / job["file"]
body = open(src, "rb").read()
assert len(body) == int(job.get("file_size", len(body))), "file_size 必须与 create_media 时一致"
content_type = job.get("content_type", "text/markdown")

# ---- 模式 A：预签名直传 ----
if job.get("presigned_url"):
    req = urllib.request.Request(job["presigned_url"], data=body, method="PUT")
    for k, v in (job.get("auth_headers") or {}).items():
        req.add_header(k, str(v))
    req.add_header("Content-Type", content_type)
    req.add_header("Content-Length", str(len(body)))
    try:
        r = urllib.request.urlopen(req, timeout=120)
        print(f"上传成功(预签名) {job['file']} HTTP {r.status} ETag {r.headers.get('ETag')}")
    except urllib.error.HTTPError as e:
        print("上传失败", e.code, e.read().decode()[:400])
    raise SystemExit(0)

# ---- 模式 B：STS 凭证手动签名 ----
host = f"{job['bucket_name']}.cos.{job['region']}.myqcloud.com"
url_path = "/" + job["cos_key"].lstrip("/")
now = int(time.time())
key_time = f"{now - 60};{now + 3600}"
sign_key = hmac.new(job["secret_key"].encode(), key_time.encode(), hashlib.sha1).hexdigest()

headers = {
    "host": host,
    "content-type": content_type,
    "content-length": str(len(body)),
    "x-cos-security-token": job["token"],
}
hlist = sorted(headers)
http_headers = "&".join(f"{k}={urllib.parse.quote(headers[k], safe='')}" for k in hlist)
http_string = f"put\n{url_path}\n\n{http_headers}\n"
string_to_sign = f"sha1\n{key_time}\n{hashlib.sha1(http_string.encode()).hexdigest()}\n"
signature = hmac.new(sign_key.encode(), string_to_sign.encode(), hashlib.sha1).hexdigest()

headers["Authorization"] = (f"q-sign-algorithm=sha1&q-ak={job['secret_id']}"
                            f"&q-sign-time={key_time}&q-key-time={key_time}"
                            f"&q-header-list={';'.join(hlist)}&q-url-param-list="
                            f"&q-signature={signature}")

req = urllib.request.Request(f"https://{host}{url_path}", data=body, method="PUT")
for k, v in headers.items():
    req.add_header(k, v)
try:
    r = urllib.request.urlopen(req, timeout=60)
    print(f"上传成功 {job['file']} HTTP {r.status} ETag {r.headers.get('ETag')}")
except urllib.error.HTTPError as e:
    print("上传失败", e.code, e.read().decode()[:500])
