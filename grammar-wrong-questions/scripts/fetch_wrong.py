"""步骤 1：登录（会话失效自动重登）并抓取全部错题
输出：<cwd>/.grammar_wrong/wrong_all.json、dict_points.json
用法：python fetch_wrong.py [--relogin]
"""
import asyncio, json, sys
from common import load_config, state_path, wrong_json, dict_json

cfg = load_config()
JS_GET = """
async (u) => {
  const raw = localStorage.getItem('cloud-ui:token');
  if (!raw) return {__err: 'no token'};
  const t = JSON.parse(raw);
  const res = await fetch(u, {headers: {'Authorization': 'Bearer ' + t}});
  if (!res.ok) return {__err: res.status + ' ' + (await res.text()).slice(0, 200)};
  return await res.json();
}
"""


async def get(page, url, tries=3):
    for _ in range(tries):
        r = await page.evaluate(JS_GET, url)
        if isinstance(r, dict) and "__err" in r:
            print("ERR", url[:110], r["__err"])
            await asyncio.sleep(1)
            continue
        return r
    return None


async def open_session(p, force=False):
    b = await p.chromium.launch(headless=True, channel="chrome")
    sp = state_path(cfg)
    if sp.exists() and not force:
        ctx = await b.new_context(storage_state=str(sp), locale="zh-CN")
        page = await ctx.new_page()
        await page.goto(cfg["home_url"], wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(1500)
        probe = await get(page, f"{cfg['api_base']}/examination/grammarStudent/{cfg['student_id']}", tries=1)
        if probe:
            return b, ctx, page
        await b.close()

    b = await p.chromium.launch(headless=True, channel="chrome")
    ctx = await b.new_context(locale="zh-CN")
    page = await ctx.new_page()
    await page.goto(cfg["login_url"], wait_until="networkidle", timeout=60000)
    await page.wait_for_timeout(2000)
    inputs = await page.query_selector_all("input")
    await inputs[0].fill(cfg["phone"])
    await inputs[1].fill(cfg["password"])
    boxes = await page.query_selector_all("input[type=checkbox]")
    if boxes:
        await boxes[-1].check(force=True)
    await page.click("button:has-text('登')")
    await page.wait_for_timeout(6000)
    await ctx.storage_state(path=str(sp))
    print("已登录并保存会话:", sp)
    page = await ctx.new_page()
    await page.goto(cfg["home_url"], wait_until="networkidle", timeout=60000)
    await page.wait_for_timeout(1500)
    return b, ctx, page


async def main():
    from playwright.async_api import async_playwright
    force = "--relogin" in sys.argv
    api, sid = cfg["api_base"], cfg["student_id"]
    async with async_playwright() as p:
        b, ctx, page = await open_session(p, force)

        lst = await get(page, f"{api}/examination/grammarWrongQuestions/getWrongGrammarList"
                              f"?studentId={sid}&correctFlag=1&current=1&size=100")
        grammars = (lst or {}).get("data") or []
        print("语法模块:", grammars)

        allq = {}
        for g in grammars:
            cur = 1
            while True:
                r = await get(page, f"{api}/examination/grammarWrongQuestions/getWrongQuestions"
                                    f"?studentId={sid}&correctFlag=1&grammarItemValue={g}&current={cur}&size=100")
                data = (r or {}).get("data") or []
                if not data:
                    break
                for q in data:
                    k = q["questionId"]
                    if k not in allq or q.get("createTime", "") > allq[k].get("createTime", ""):
                        allq[k] = q
                print(f"  {g} p{cur}: +{len(data)} 累计 {len(allq)}")
                if len(data) < 100:
                    break
                cur += 1
        print("错题去重后:", len(allq))

        details = {}
        for i, qid in enumerate(allq):
            r = await get(page, f"{api}/examination/grammarTopicsQuestion/{qid}")
            if r and r.get("data"):
                details[qid] = r["data"]
            if (i + 1) % 25 == 0:
                print(f"  详情进度 {i+1}/{len(allq)}")

        out = [{"record": rec, "question": details.get(qid)} for qid, rec in allq.items()]
        json.dump(out, open(wrong_json(cfg), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        d = await get(page, f"{api}/admin/businessDict/grammar_points")
        json.dump(d, open(dict_json(cfg), "w", encoding="utf-8"), ensure_ascii=False)
        print("已保存:", wrong_json(cfg), "/", dict_json(cfg))
        await b.close()

asyncio.run(main())
