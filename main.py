import customtkinter
import os
import json
import sys

import urllib.parse
import subprocess
import psutil
from tkinter import PhotoImage

customtkinter.set_appearance_mode("System")
customtkinter.set_default_color_theme("blue")

# تعیین مسیر آیکون و فایل اجرایی
if getattr(sys, 'frozen', False):
    WORK_DIR = os.path.dirname(sys.executable)
else:
    WORK_DIR = os.path.dirname(os.path.abspath(__file__))

EXE_PATH = os.path.join(WORK_DIR, "purwint")  # بدون .exe
CONFIG_FILE = os.path.join(WORK_DIR, "myconfig.json")
ICON_PATH = os.path.join(WORK_DIR, "icon.png")  # برای لینوکس بهتره از .png استفاده شه

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(WORK_DIR, relative_path)

icon_path = resource_path("icon.png")

def parse_link_to_json(link):
    link = link.strip()
    if link.startswith("wireguard://"):
        try:
            raw = link[len("wireguard://"):]
            if "#" in raw:
                raw, tag = raw.split("#", 1)
            else:
                tag = "warp"

            priv_key, rest = raw.split("@", 1)
            server_host_port, query = rest.split("?", 1)
            server, port = server_host_port.split(":", 1)
            params = urllib.parse.parse_qs(query)

            address_raw = params.get("address", [""])[0]
            address = [a.strip() for a in address_raw.split(",") if a.strip() != ""]

            reserved_str = params.get("reserved", [""])[0]
            reserved = [int(x) for x in reserved_str.split(",") if x.isdigit()]

            peer_public_key = params.get("publickey", [""])[0]
            mtu = int(params.get("mtu", [1280])[0])

            # decode percent encoding
            priv_key = urllib.parse.unquote(priv_key)
            peer_public_key = urllib.parse.unquote(peer_public_key)

            return {
                "type": "wireguard",
                "tag": "warp",
                "server": server,
                "server_port": int(port),
                "local_address": address,
                "private_key": priv_key,
                "peer_public_key": peer_public_key,
                "reserved": reserved,
                "mtu": mtu
            }
        except Exception as e:
            print("Wireguard parse error:", e)
            return None
    else:
        return None

def save_config_json(link_text):
    lines = link_text.strip().splitlines()
    wireguard_outbounds = []
    for line in lines:
        js = parse_link_to_json(line)
        if js:
            wireguard_outbounds.append(js)

    fixed_outbounds = [
        {"type": "dns", "tag": "dns"},
        {"type": "direct", "tag": "warp-IPv4", "detour": "warp", "domain_strategy": "ipv4_only"},
        {"type": "direct", "tag": "warp-IPv6", "detour": "warp", "domain_strategy": "ipv6_only"},
        {"tag": "direct", "type": "direct"}
    ]

    outbounds = fixed_outbounds + wireguard_outbounds

    config = {
        "log": {"level": "info"},
        "dns": {
            "servers": [
                {
                    "tag": "default",
                    "address": "8.8.8.8",
                    "detour": "warp"
                }
            ]
        },
        "inbounds": [
            {
                "type": "tun",
                "interface_name": "purwintun",
                "inet4_address": "10.8.0.200/30",
                "inet6_address": "fdfe:dcba:9876::1/126",
                "auto_route": True,
                "stack": "gvisor",
                "sniff": True
            }
        ],
        "outbounds": outbounds,
        "route": {
            "rules": [
                {"protocol": "dns", "outbound": "dns"},
                {"domain": ["ikcosales.ir", "chatgpt.com"], "outbound": "direct"}
            ],
            "final": "warp",
            "auto_detect_interface": True
        }
    }

    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

def kill_purwint_process():
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if proc.info['name'] and "purwint" in proc.info['name'].lower():
                proc.kill()
                print(f"Killed purwint process with PID {proc.pid}")
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass


def run_purwint():
    purwint_path = os.path.join(os.path.dirname(sys.argv[0]), "purwint")

    try:
        subprocess.Popen(["pkexec", purwint_path])
        print("purwint started with root permission")
    except Exception as e:
        print("خطا در اجرای purwint با pkexec:", e)

def toggle_vpn():
    if switch_var.get() == 1:
        save_config_json(textbox.get("1.0", "end"))
        try:
            subprocess.Popen(
               ["pkexec", EXE_PATH, "run", "-c", CONFIG_FILE],
                 cwd=WORK_DIR,
                 stdout=subprocess.DEVNULL,
                 stderr=subprocess.DEVNULL
                                          )

            status_label.configure(text="وضعیت: متصل", text_color="green")
        except Exception as e:
            status_label.configure(text=f"خطا: {e}", text_color="red")
            switch_var.set(0)
    else:
        try:
            kill_purwint_process()
        except:
            pass
        status_label.configure(text="وضعیت: قطع", text_color="gray")

def right_click_paste(event):
    try:
        clipboard_text = app.clipboard_get()
        textbox.insert("insert", clipboard_text)
    except:
        pass
    return "break"

# ---------- رابط کاربری ----------
app = customtkinter.CTk()

# آیکون لینوکس (PNG)
try:
    app.iconphoto(False, PhotoImage(file=icon_path))
except:
    pass

window_width = 400
window_height = 300
screen_width = app.winfo_screenwidth()
screen_height = app.winfo_screenheight()
x = (screen_width // 2) - (window_width // 2)
y = (screen_height // 2) - (window_height // 2)
app.geometry(f"{window_width}x{window_height}+{x}+{y}")
app.title("PurNet VPN")

switch_var = customtkinter.IntVar()
vpn_switch = customtkinter.CTkSwitch(master=app, text="اتصال VPN", variable=switch_var, command=toggle_vpn)
vpn_switch.pack(pady=10)

textbox = customtkinter.CTkTextbox(master=app, width=380, height=180)
textbox.pack(padx=10, pady=10)
textbox.bind("<Button-3>", right_click_paste)

status_label = customtkinter.CTkLabel(master=app, text="وضعیت: قطع", text_color="gray")
status_label.pack(pady=5)

app.mainloop()
