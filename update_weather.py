# -*- coding: utf-8 -*-
"""
Update weather_forecast.json for Dashboard Vung Ken V6.7 RC.
Source: Open-Meteo public forecast API.
No external library required. Run: python update_weather.py
"""
import json, os, sys, time, urllib.parse, urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

STORE_COORDS = {
    "YODY LONG XUYÊN": {"lat": 10.3864, "lon": 105.4352, "city": "Long Xuyên"},
    "YODY LONG XUYÊN 2": {"lat": 10.3864, "lon": 105.4352, "city": "Long Xuyên"},
    "YODY 30 - 4 CẦN THƠ": {"lat": 10.0452, "lon": 105.7469, "city": "Cần Thơ"},
    "YODY CẦN THƠ 3": {"lat": 10.0452, "lon": 105.7469, "city": "Cần Thơ"},
    "YODY SÓC TRĂNG": {"lat": 9.6036, "lon": 105.9739, "city": "Sóc Trăng"},
    "YODY BẠC LIÊU": {"lat": 9.2940, "lon": 105.7216, "city": "Bạc Liêu"},
    "YODY RẠCH SỎI - KIÊN GIANG": {"lat": 9.9633, "lon": 105.1119, "city": "Rạch Sỏi / Kiên Giang"},
    "YODY NGÃ BẢY": {"lat": 9.8167, "lon": 105.8167, "city": "Ngã Bảy / Hậu Giang"},
}
PEAK_HOURS = {17,18,19,20,21}
TRAFFIC_WEIGHT = {8:.04,9:.05,10:.06,11:.06,12:.07,13:.07,14:.08,15:.09,16:.10,17:.12,18:.13,19:.13,20:.12,21:.08}

def weather_code_text(code):
    code = int(code or 0)
    if code == 0: return "Nắng"
    if code in (1,2): return "Ít mây"
    if code == 3: return "Nhiều mây"
    if code in (45,48): return "Sương mù"
    if code in (51,53,55,56,57): return "Mưa phùn"
    if code in (61,63,65,66,67,80,81,82): return "Mưa lớn" if code in (65,81,82) else "Mưa"
    if code in (95,96,99): return "Dông"
    return "Theo dõi"

def icon(text):
    if "Dông" in text: return "⛈️"
    if "Mưa lớn" in text: return "🌧️"
    if "Mưa" in text: return "🌦️"
    if "Nắng" in text: return "☀️"
    if "mây" in text or "Mây" in text: return "⛅"
    return "🌤️"

def hour_from_time(t):
    try: return int(str(t).split('T')[1][:2])
    except Exception: return 0

def build_hourly_rows(hourly):
    times = hourly.get('time', [])
    codes = hourly.get('weather_code', [])
    pops = hourly.get('precipitation_probability', [])
    prec = hourly.get('precipitation', hourly.get('rain', []))
    winds = hourly.get('wind_speed_10m', [])
    rows = []
    for i,t in enumerate(times):
        h = hour_from_time(t)
        date = str(t)[:10]
        code = codes[i] if i < len(codes) else 0
        pop = float(pops[i] or 0) if i < len(pops) else 0
        mm = float(prec[i] or 0) if i < len(prec) else 0
        wind = float(winds[i] or 0) if i < len(winds) else 0
        weather = weather_code_text(code)
        rainy = pop >= 45 or mm >= .2 or 'Mưa' in weather or 'Dông' in weather
        severe = pop >= 70 or mm >= 2 or 'Mưa lớn' in weather or 'Dông' in weather
        peak = h in PEAK_HOURS
        tw = TRAFFIC_WEIGHT.get(h, .03)
        impact_points = (1 if rainy else 0) * (2 if severe else 1) * (2.2 if peak else 1) * tw * 100
        rows.append({"time":t,"date":date,"hour":h,"weather":weather,"pop":pop,"mm":mm,"wind":wind,"rainy":rainy,"severe":severe,"peak":peak,"trafficWeight":tw,"impactPoints":impact_points})
    return rows

def summarize(rows):
    if not rows:
        return {"risk":"Chưa có","summary":"Chưa có dữ liệu hourly","rain_days":0,"max_pop":0,"impact_score":0,"segments":[],"today":[],"action":"Theo dõi thời tiết thủ công."}
    by_date = {}
    for r in rows: by_date.setdefault(r['date'], []).append(r)
    dates = sorted(by_date)
    today = by_date[dates[0]]
    rain_days = sum(1 for d in dates if any(x['rainy'] for x in by_date[d]))
    max_pop = max([r['pop'] for r in rows] or [0])
    score = sum(r['impactPoints'] for r in today)
    risk = 'Cao' if score >= 65 else ('Trung bình' if score >= 28 else 'Thấp')
    segments=[]; cur=None
    for r in today:
        label=f"{icon(r['weather'])} {r['weather']}"
        if not cur or cur['label'] != label:
            if cur: segments.append(cur)
            cur={"label":label,"start":r['hour'],"end":r['hour']+1,"maxPop":r['pop'],"maxMm":r['mm'],"peak":r['peak'],"score":r['impactPoints']}
        else:
            cur['end']=r['hour']+1; cur['maxPop']=max(cur['maxPop'],r['pop']); cur['maxMm']=max(cur['maxMm'],r['mm']); cur['peak']=cur['peak'] or r['peak']; cur['score'] += r['impactPoints']
    if cur: segments.append(cur)
    worst = sorted(segments, key=lambda x: x.get('score',0), reverse=True)[0] if segments else None
    if worst:
        summary = f"{worst['label']} {worst['start']:02d}h-{worst['end']:02d}h, POP tối đa {round(worst['maxPop'])}%. " + ("Trùng giờ vàng bán hàng." if worst['peak'] else "Không trùng giờ vàng chính.")
    else:
        summary = "Thời tiết thuận lợi."
    if risk == 'Cao': action = 'Ưu tiên Zalo KH cũ, gọi khách giữ hàng, hẹn khách trước/sau khung mưa, livestream hoặc chốt đơn từ xa.'
    elif risk == 'Trung bình': action = 'Theo dõi khung mưa, dồn hoạt động kéo khách vào giờ tạnh, chuẩn bị kịch bản gọi khách cũ.'
    else: action = 'Có thể đẩy walk-in/local activation; nếu nắng nóng, tập trung Polo/UV/nhóm sản phẩm dễ mua.'
    return {"risk":risk,"impact":risk,"summary":summary,"rain_days":rain_days,"max_pop":round(max_pop),"impact_score":score,"segments":segments,"today":today,"peak_rain_hours":sum(1 for r in today if r['rainy'] and r['peak']),"action":action}

def fetch_store_weather(store, coord):
    params = {
        "latitude": coord["lat"], "longitude": coord["lon"],
        "hourly": "weather_code,precipitation_probability,precipitation,wind_speed_10m",
        "daily": "weather_code,precipitation_sum,precipitation_probability_max",
        "timezone": "Asia/Bangkok", "forecast_days": 7,
    }
    url = "https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent":"Dashboard-Vung-Ken/6.7-RC"})
    with urllib.request.urlopen(req, timeout=20) as res:
        data=json.loads(res.read().decode('utf-8'))
    hourly_rows=build_hourly_rows(data.get('hourly', {}))
    w=summarize(hourly_rows)
    return {"store":store,"city":coord['city'],"source":"Open-Meteo","risk":w['risk'],"impact":w['impact'],"impact_score":w['impact_score'],"summary":w['summary'],"rain_days":w['rain_days'],"max_pop":w['max_pop'],"segments":w['segments'],"today":w['today'],"peak_rain_hours":w['peak_rain_hours'],"action":w['action'],"daily":data.get('daily',{}),"hourly":data.get('hourly',{})}

def main():
    root=os.path.dirname(os.path.abspath(__file__))
    data_dir=os.path.join(root,'data'); os.makedirs(data_dir, exist_ok=True)
    out_path=os.path.join(data_dir,'weather_forecast.json')
    stores=[]; errors=[]
    for store, coord in STORE_COORDS.items():
        try:
            item=fetch_store_weather(store, coord); stores.append(item)
            print(f"OK  {store}: {item['risk']} · {item['summary']}")
            time.sleep(.15)
        except Exception as exc:
            errors.append(f"{store}: {exc}"); print(f"ERR {store}: {exc}")
    if not stores:
        print('\nKhông lấy được dữ liệu weather. Kiểm tra Internet hoặc thử lại sau.')
        if os.path.exists(out_path): print('Giữ nguyên file weather_forecast.json cũ.')
        sys.exit(1)
    now=datetime.now(ZoneInfo('Asia/Ho_Chi_Minh')).strftime('%d/%m/%Y %H:%M')
    payload={"updated_at":now,"source":"Open-Meteo API · Weather Intelligence V2 · updated by UPDATE_WEATHER.bat","mode":"local_hourly_generated","stores":stores}
    if errors: payload['errors']=errors
    with open(out_path,'w',encoding='utf-8') as f: json.dump(payload,f,ensure_ascii=False,indent=2)
    print(f"\nĐã cập nhật: {out_path}")
    print(f"Số cửa hàng có weather: {len(stores)}/{len(STORE_COORDS)}")
    if errors:
        print('\nCó lỗi ở một số cửa hàng:'); [print('-',e) for e in errors]
if __name__ == '__main__': main()
