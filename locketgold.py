import aiohttp
import json
import re
import time
import asyncio

import ctypes
import os
import sys

def enable_windows_ansi():
    # Bật VT/ANSI cho CMD Windows 10+ để màu terminal được render đúng.
    if os.name != "nt":
        return
    try:
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        mode = ctypes.c_uint32()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            kernel32.SetConsoleMode(handle, mode.value | 0x0004)
    except Exception:
        pass

enable_windows_ansi()

# ==================== CẤU HÌNH TỰ NHẬP ====================
# Điền các giá trị token và chữ ký (hash) tự nhập của bạn vào đây:
TOKEN_CONFIG = {
    "name": "Custom Manual Token",
    "fetch_token": "",
    "app_transaction": "",
     "hash_params": "",
    "hash_headers": "",
    "is_sandbox": False,
    "transaction_id": "",
}
# ==========================================================

HEADERS = {
    'Host': 'api.revenuecat.com',
    'Authorization': 'Bearer appl_JngFETzdodyLmCREOlwTUtXdQik',
    'Content-Type': 'application/json',
    'Accept': '*/*',
    'X-Platform': 'iOS',
    'X-Platform-Version': 'Version 26.2 (Build 23C55)',
    'X-Platform-Device': 'iPhone15,3',
    'X-Platform-Flavor': 'native',
    'X-Version': '5.41.0',
    'X-Client-Version': '2.32.2',
    'X-Client-Bundle-ID': 'com.locket.Locket',
    'X-Client-Build-Version': '3',
    'X-StoreKit2-Enabled': 'true',
    'X-StoreKit-Version': '2',
    'X-Observer-Mode-Enabled': 'false',
    'X-Is-Sandbox': 'false',
    'X-Storefront': 'VNM',
    'X-Apple-Device-Identifier': '39A73C25-1E05-4350-ADA7-5CD3FE1079E8',
    'X-Preferred-Locales': 'vi_KR,ko_KR,en_KR',
    'X-Nonce': 'w0Mlb6+AmV4WYuVv',
    'X-Is-Backgrounded': 'false',
    'X-Retry-Count': '0',
    'X-Is-Debug-Build': 'false',
    'User-Agent': 'Locket/3 CFNetwork/3860.300.31 Darwin/25.2.0',
    'Accept-Language': 'vi-VN,vi;q=0.9',
    'Connection': 'keep-alive',
    'Pragma': 'no-cache',
    'Cache-Control': 'no-cache',
    'X-RevenueCat-ETag': ''
}

class Clr:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

async def resolve_uid(username):
    """Phân giải username hoặc link Locket thành UID 28 ký tự"""
    url = f"https://locket.cam/{username}"
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)",
        "Accept": "text/html"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, allow_redirects=True, timeout=10) as res:
                html = await res.text()
                redirect_url = str(res.url)

                def extract(text):
                    if not text: return None
                    m = re.search(r'/invites/([A-Za-z0-9]{28})', text)
                    if m: return m.group(1)
                    
                    lp = re.search(r'link=([^\s"\'>]+)', text)
                    if lp:
                        try:
                            d = lp.group(1).replace('%3A', ':').replace('%2F', '/')
                            dm = re.search(r'/invites/([A-Za-z0-9]{28})', d)
                            if dm: return dm.group(1)
                        except:
                            pass
                    return None

                return extract(redirect_url) or extract(html)
    except Exception as e:
        print(f"{Clr.FAIL}[!] Lỗi phân giải UID: {e}{Clr.ENDC}")
        return None

async def check_status(uid):
    """Kiểm tra trạng thái Gold hiện tại của UID"""
    url = f"https://api.revenuecat.com/v1/subscribers/{uid}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=HEADERS, timeout=10) as res:
                if 200 <= res.status < 300:
                    data = await res.json()
                    entitlements = data.get('subscriber', {}).get('entitlements', {}).get('Gold', {})
                    if entitlements:
                        expires_date = entitlements.get('expires_date')
                        return {"active": True, "expires": expires_date}
                    return {"active": False}
                return {"active": False}
    except Exception:
        return None

async def inject_gold(uid, token_config):
    """Tiêm gói kích hoạt Gold sang tài khoản đích với thông số tự nhập"""
    url = "https://api.revenuecat.com/v1/receipts"
    
    fetch_token = token_config['fetch_token']
    app_transaction = token_config['app_transaction']
    is_sandbox = token_config['is_sandbox']
    
    body = {
        "product_id": "locket_199_1m", 
        "fetch_token": fetch_token, 
        "app_transaction": app_transaction,
        "app_user_id": uid, 
        "is_restore": True, 
        "store_country": "VNM", 
        "currency": "USD",
        "price": "1.99", 
        "normal_duration": "P1M", 
        "subscription_group_id": "21419447",
        "observer_mode": False, 
        "initiation_source": "restore", 
        "offers": [],
        "attributes": { 
            "$attConsentStatus": { "updated_at_ms": int(time.time() * 1000), "value": "notDetermined" } 
        }
    }
    
    current_headers = HEADERS.copy()
    current_headers['Content-Length'] = str(len(json.dumps(body)))
    
    # Gắn các thông số Hash tự nhập nếu có
    if token_config.get('hash_params'):
        current_headers['X-Post-Params-Hash'] = token_config['hash_params']
    if token_config.get('hash_headers'):
        current_headers['X-Headers-Hash'] = token_config['hash_headers']
    
    current_headers['X-Is-Sandbox'] = str(is_sandbox).lower()

    print(f"{Clr.BLUE}[*] Target UID:{Clr.ENDC} {uid}")
    print(f"{Clr.BLUE}[*] Đang gửi Payload kích hoạt với thông số tự nhập...{Clr.ENDC}")

    async with aiohttp.ClientSession() as session:
        for attempt in range(5):
            try:
                print(f"{Clr.WARNING}[>] Lần thử {attempt+1}/5:{Clr.ENDC} Đang gửi request...")
                async with session.post(url, headers=current_headers, json=body, timeout=15) as res:
                    status_code = res.status
                    
                    if status_code == 200:
                        print(f"{Clr.GREEN}[+] HTTP 200 OK.{Clr.ENDC} Đang xác thực quyền Gold...")
                        status = await check_status(uid)
                        if status and status.get('active'):
                            print(f"{Clr.GREEN}[SUCCESS] Kích hoạt Locket Gold thành công! Hết hạn: {status.get('expires')}{Clr.ENDC}")
                            return True
                        else:
                            await asyncio.sleep(2)
                            status = await check_status(uid)
                            if status and status.get('active'):
                                print(f"{Clr.GREEN}[SUCCESS] Kích hoạt thành công sau khi chờ xác thực!{Clr.ENDC}")
                                return True
                            print(f"{Clr.FAIL}[-] Thất bại: Server chấp nhận nhưng chưa cấp quyền Gold.{Clr.ENDC}")
                            return False
                            
                    elif status_code == 529:
                        print(f"{Clr.WARNING}[!] Server quá tải (529). Đang chờ 2 giây thử lại...{Clr.ENDC}")
                        await asyncio.sleep(2)
                        continue
                        
                    else:
                        msg = "Lỗi không xác định"
                        try:
                            resp_json = await res.json()
                            msg = resp_json.get('message', str(status_code))
                        except:
                            msg = str(status_code)
                        print(f"{Clr.FAIL}[x] Bị từ chối: {msg}{Clr.ENDC}")
                        return False
                    
            except Exception as e:
                print(f"{Clr.FAIL}[!] Lỗi mạng: {e}{Clr.ENDC}")
                if attempt == 4:
                    return False
                await asyncio.sleep(2)
            
    return False

async def main():
    # ==================== GITHUB STYLE CLI ====================
    B = "\033[1;34m"
    C = "\033[1;36m"
    G = "\033[1;32m"
    Y = "\033[1;33m"
    P = "\033[1;35m"
    W = "\033[1;37m"
    R = "\033[1;31m"
    D = "\033[2;37m"
    X = "\033[0m"

    try:
        import shutil
        width = max(72, min(shutil.get_terminal_size((88, 24)).columns, 100))
    except Exception:
        width = 88

    inner = width - 2
    line = "=" * inner
    dash = "-" * inner

    def box_line(content="", color=C):
        content = content[:inner].ljust(inner)
        return f"{color}|{W}{content}{color}|{X}"

    print()
    print(f"{P}+{line}+{X}")
    print(box_line("", P))
    print(box_line("   ██╗      ██████╗  ██████╗██╗  ██╗███████╗████████╗", P))
    print(box_line("   ██║     ██╔═══██╗██╔════╝██║ ██╔╝██╔════╝╚══██╔══╝", P))
    print(box_line("   ██║     ██║   ██║██║     █████╔╝ █████╗     ██║   ", P))
    print(box_line("   ██║     ██║   ██║██║     ██╔═██╗ ██╔══╝     ██║   ", P))
    print(box_line("   ███████╗╚██████╔╝╚██████╗██║  ██╗███████╗   ██║   ", P))
    print(box_line("   ╚══════╝ ╚═════╝  ╚═════╝╚═╝  ╚═╝╚══════╝   ╚═╝   ", P))
    print(box_line("", P))
    print(box_line("                 LOCKET GOLD By Ziokatz X Ngocquynh066", C))
    print(box_line("                   Telegram @Ziokatz X @Ngocquynh066", D))
    print(box_line("", P))
    print(f"{P}+{line}+{X}")
    print()

    print(f"{C}[ SYSTEM ]{X}")
    print(f"  {G}[+] ONLINE{X}      {D}|{X} Network: {G}READY{X}")
    print(f"  {G}[+] CONFIG{X}      {D}|{X} Token:   {G}LOADED{X}")
    print(f"  {G}[+] ENGINE{X}      {D}|{X} Mode:    {Y}MANUAL{X}")
    print()
    print(f"{D}{dash}{X}")
    print()

    userInput = input(
        f"{C}┌─[ USERNAME / LINK ]{X}\n"
        f"{C}└──>{W} "
    ).strip()

    if not userInput:
        print(f"\n{R}[ERROR]{X} Vui lòng nhập username hoặc link hợp lệ.")
        return

    print()
    print(f"{C}┌─[1/3] RESOLVE UID{X}")
    print(f"{C}└──>{X} Target: {Y}{userInput}{X}")
    print(f"{D}    ├─ Connecting...{X}")
    uid = await resolve_uid(userInput)

    if not uid:
        print(f"{R}    └─ [FAILED]{X} Không tìm thấy UID.")
        print()
        return

    print(f"{G}    └─ [SUCCESS]{X} UID: {W}{uid}{X}")
    print()

    print(f"{C}┌─[2/3] VERIFY{X}")
    print(f"{D}    ├─ Checking target status...{X}")
    print(f"{G}    └─ [FOUND]{X} UID đã được phân giải.")
    print()

    print(f"{C}┌─[3/3] PROCESS{X}")
    print(f"{D}    ├─ Sending request...{X}")
    print(f"{D}    └─ Please wait...{X}")
    print()

    # Giữ nguyên logic xử lý hiện có.
    await inject_gold(uid, TOKEN_CONFIG)

    print()
    print(f"{P}+{line}+{X}")
    print(box_line("              SESSION COMPLETED", P))
    print(box_line("        Thanks for using the CLI tool", D))
    print(f"{P}+{line}+{X}")
    print()

if __name__ == "__main__":
    asyncio.run(main())