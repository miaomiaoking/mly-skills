# -*- coding: utf-8 -*-
"""把本地文件 PUT 到 ima create_media 返回的预签名 URL（upload_mode=1）。

用法：
  python ima_put.py --url "<presigned_url>" --file <本地文件> --headers '<auth_headers JSON>'

说明：auth_headers 必须原样携带（含 Content-Type / Content-Length），
      否则签名校验失败。上传成功返回 HTTP 200/204。
"""
import argparse, json, os, sys, urllib.request


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--file", required=True)
    ap.add_argument("--headers", default="{}")
    ap.add_argument("--no-proxy", action="store_true", help="绕过系统代理直连")
    args = ap.parse_args()

    data = open(args.file, "rb").read()
    headers = json.loads(args.headers) if args.headers.strip() else {}
    # Content-Length 必须与 create_media 申报的 file_size 一致，这里按实际文件重设
    headers = {k: v for k, v in headers.items() if k.lower() != "content-length"}
    req = urllib.request.Request(args.url, data=data, method="PUT")
    for k, v in headers.items():
        req.add_header(k, v)
    req.add_header("Content-Length", str(len(data)))
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({})) if args.no_proxy \
            else urllib.request.build_opener()
        with opener.open(req, timeout=300) as r:
            print(f"PUT ok: HTTP {r.status}, {len(data)} bytes")
            return 0
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode(errors="replace")[:600]
        except Exception:
            pass
        print(f"PUT failed: HTTP {e.code}\n{body}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"PUT failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
