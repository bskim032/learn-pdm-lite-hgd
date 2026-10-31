"""learn-pdm-lite-hgd 정답 예시 — Block 1 노이즈 vs 추세 판정과 그래프 한 장 대시보드.

실행: python build_lite.py   (작업 폴더 안에서 — data/ 아래에 Day5_설비센서_50건_가상.csv 가 있어야 한다)
출력: outputs/trend.csv, 작업 폴더에 index.html (GitHub Pages 첫 화면),
      현재 폴더에 expected.json (course-forge 검증용)

원본 강의: keerhee/kma-auto-genai-3-1 · Day5_예지보전 본 강의 ④ 분석 1 (Main p14·p20)
판정 규칙: 보충교재 learn-auto-pdm block3 (기준선 처음 12점, 평균 + 3σ, 3번 연속)
"""
import csv
import json
import statistics as st
from pathlib import Path

DATA = Path("data") / "Day5_설비센서_50건_가상.csv"
OUT = Path("outputs")
BASE_N = 12   # 기준선: 처음 12점(08:00~11:40) — 정상 운전 구간
K_SIGMA = 3   # 상한: 기준선 평균 + 3σ
RUN = 3       # 3번 연속 넘으면 추세
A = "설비A(프레스 메인모터)"
B = "설비B(차체 용접로봇 감속기)"
SERIES = [(A, "진동(mm/s)"), (B, "진동(mm/s)"), (B, "온도(℃)")]


def load():
    with open(DATA, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def judge(times, values):
    """기준선 상한을 구하고 노이즈/추세/정상을 판정한다."""
    base = values[:BASE_N]
    upper = st.mean(base) + K_SIGMA * st.stdev(base)
    over = [v > upper for v in values]
    start, streak = None, 0
    for i, o in enumerate(over):
        streak = streak + 1 if o else 0
        if streak == RUN and start is None:
            start = times[i - RUN + 1]   # 연속의 첫 점이 추세 시작
    n_over = sum(over)
    verdict = "추세" if start else ("노이즈" if n_over else "정상")
    return upper, n_over, verdict, start


def main():
    rows = load()
    OUT.mkdir(exist_ok=True)
    series, table = {}, []
    for eq, col in SERIES:
        g = [r for r in rows if r["설비"] == eq]
        times = [r["시간"][-5:] for r in g]
        values = [float(r[col]) for r in g]
        upper, n_over, verdict, start = judge(times, values)
        series[(eq, col)] = (times, values, upper)
        table.append({"설비": eq, "항목": col, "기준선 상한": round(upper, 2),
                      "상한 초과 점 수": n_over, "판정": verdict, "추세 시작": start or "—"})

    with open(OUT / "trend.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(table[0]))
        w.writeheader()
        w.writerows(table)

    a_vib, b_vib, b_temp = table
    times = series[(A, "진동(mm/s)")][0]
    data = {
        "t": times,
        "a_vib": series[(A, "진동(mm/s)")][1],
        "b_vib": series[(B, "진동(mm/s)")][1],
        "b_temp": series[(B, "온도(℃)")][1],
        "b_temp_ul": round(b_temp["기준선 상한"], 1),
    }
    rows_html = "".join(
        f"<tr><td>{r['설비']}</td><td>{r['항목']}</td><td>{r['기준선 상한']}</td>"
        f"<td>{r['상한 초과 점 수']}</td><td>{r['판정']}</td><td>{r['추세 시작']}</td></tr>" for r in table)
    title = (f"설비B는 온도가 {b_temp['추세 시작']}부터 추세적으로 올랐다(진동은 {b_vib['추세 시작']}부터) "
             f"— 설비A 진동 3.5는 한 번 튄 노이즈")
    html = TEMPLATE.replace("__TITLE__", title).replace("__ROWS__", rows_html) \
                   .replace("__DATA__", json.dumps(data, ensure_ascii=False))
    Path("index.html").write_text(html, encoding="utf-8")

    expected = {"values": {
        "a_vib_over_count": {"value": a_vib["상한 초과 점 수"], "decimals": 0, "block": 1},
        "a_vib_verdict": {"value": a_vib["판정"], "decimals": None, "block": 1},
        "b_temp_upper": {"value": b_temp["기준선 상한"], "decimals": 1, "block": 1},
        "b_temp_trend_start": {"value": b_temp["추세 시작"], "decimals": None, "block": 1},
        "b_vib_trend_start": {"value": b_vib["추세 시작"], "decimals": None, "block": 1},
    }}
    Path("expected.json").write_text(json.dumps(expected, ensure_ascii=False, indent=1), encoding="utf-8")


TEMPLATE = """<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>예지보전 실습판</title>
<style>
:root{--bg:#fff;--fg:#1f2328;--mute:#59636e;--line:#d1d9e0}
@media (prefers-color-scheme:dark){:root{--bg:#0d1117;--fg:#e6edf3;--mute:#9198a1;--line:#3d444d}}
body{margin:0;background:var(--bg);color:var(--fg);font-family:system-ui,"Malgun Gothic",sans-serif}
main{max-width:860px;margin:0 auto;padding:16px}
h1{font-size:1.15rem;line-height:1.5;margin:8px 0 12px}
.chart{position:relative;height:340px}
table{width:100%;border-collapse:collapse;font-size:.85rem;margin-top:14px}
th,td{border-bottom:1px solid var(--line);padding:6px 4px;text-align:left}
.scroll{overflow-x:auto}
.note{color:var(--mute);font-size:.8rem;line-height:1.6;margin-top:10px}
</style></head><body><main>
<h1>__TITLE__</h1>
<div class="chart"><canvas id="c"></canvas></div>
<div class="scroll"><table><tr><th>설비</th><th>항목</th><th>기준선 상한</th><th>상한 초과</th><th>판정</th><th>추세 시작</th></tr>__ROWS__</table></div>
<p class="note">판정 규칙: 설비·항목마다 처음 12점(08:00~11:40)의 평균 + 3σ를 기준선 상한으로 두고, 3번 연속 넘으면 추세(첫 점 = 추세 시작), 연속 3번 미만이면 노이즈.<br>
실습용 가상 데이터 · 출처: <a href="https://github.com/keerhee/kma-auto-genai-3-1">keerhee/kma-auto-genai-3-1</a> data/Day5/Day5_설비센서_50건_가상.csv · 2026-09-15 08:00~16:00, 20분 간격 · 원본 강의 Day5 예지보전 ④ 분석 1</p>
</main>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<script>
const D=__DATA__;
const dark=matchMedia('(prefers-color-scheme: dark)').matches;
Chart.defaults.color=dark?'#9198a1':'#59636e';
new Chart(document.getElementById('c'),{type:'line',data:{labels:D.t,datasets:[
{label:'설비A 진동 (mm/s)',data:D.a_vib,borderColor:'#8c959f',backgroundColor:'#8c959f',yAxisID:'v',pointRadius:2},
{label:'설비B 진동 (mm/s)',data:D.b_vib,borderColor:'#0969da',backgroundColor:'#0969da',yAxisID:'v',pointRadius:2},
{label:'설비B 온도 (℃)',data:D.b_temp,borderColor:'#cf222e',backgroundColor:'#cf222e',yAxisID:'t',pointRadius:2},
{label:'설비B 온도 기준선 상한 '+D.b_temp_ul.toFixed(1)+' ℃',data:D.t.map(()=>D.b_temp_ul),borderColor:'#cf222e',borderDash:[5,4],borderWidth:1,pointRadius:0,yAxisID:'t'}]},
options:{responsive:true,maintainAspectRatio:false,interaction:{mode:'index',intersect:false},
scales:{v:{position:'left',beginAtZero:true,title:{display:true,text:'진동 (mm/s)'}},
t:{position:'right',beginAtZero:true,grid:{drawOnChartArea:false},title:{display:true,text:'온도 (℃)'}}},
plugins:{legend:{position:'bottom',labels:{boxWidth:12}}}}});
</script></body></html>
"""

if __name__ == "__main__":
    main()
