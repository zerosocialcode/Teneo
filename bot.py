# =============================================================================
# Teneo-BOT Dashboard
# Original Author: vonssy
# Developed & modernized by: zerosocialcode
# =============================================================================

import asyncio
import json
import os
from typing import Any, Dict, List, Optional, Tuple

import pytz
from aiohttp import ClientSession, ClientTimeout
from aiohttp_socks import ProxyConnector
from fake_useragent import FakeUserAgent
from datetime import datetime
from colorama import Fore, Style, init

# ----------- CONFIGURABLE CONSTANTS -----------
BOX_WIDTH = 64
TIMEZONE = 'Asia/Jakarta'

# ----------- COLOR AND STYLE KIT --------------
init(autoreset=True)
wib = pytz.timezone(TIMEZONE)

class StyleKit:
    TEAL = Fore.CYAN
    PURPLE = Fore.MAGENTA
    ORANGE = Fore.YELLOW
    WHITE = Fore.WHITE
    GRAY = Fore.LIGHTBLACK_EX
    RED = Fore.LIGHTRED_EX
    GREEN = Fore.LIGHTGREEN_EX
    RESET = Style.RESET_ALL
    BOLD = Style.BRIGHT

    HEADER = TEAL + BOLD
    SUBHEADER = PURPLE + BOLD
    INFO = ORANGE + BOLD
    OK = GREEN + BOLD
    WARN = ORANGE + BOLD
    ERR = RED + BOLD

    @staticmethod
    def box_line(char="═"):
        return f"╔{char * (BOX_WIDTH-2)}╗"

    @staticmethod
    def box_sep():
        return f"╟{'─' * (BOX_WIDTH-2)}╢"

    @staticmethod
    def box_bottom():
        return f"╚{'═' * (BOX_WIDTH-2)}╝"

    @staticmethod
    def box_text(text, color=Fore.WHITE):
        return f"║{color}{text.center(BOX_WIDTH-2)}{Style.RESET_ALL}║"

    @staticmethod
    def log_line(status, email, proxy, message, color=Fore.GREEN):
        return (
            f"[{color}{status:<4}{Style.RESET_ALL}] "
            f"{email:<20} | Proxy={proxy:<14} | {message}"
        )

# ------------- MAIN BOT CLASS -----------------
class TeneoBot:
    def __init__(self) -> None:
        ua = FakeUserAgent()
        self.WS_HEADERS = {
            "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
            "Cache-Control": "no-cache",
            "Connection": "Upgrade",
            "Host": "secure.ws.teneo.pro",
            "Origin": "chrome-extension://emcclcoaglgcpoognfiggmhnhgabppkm",
            "Pragma": "no-cache",
            "Sec-WebSocket-Extensions": "permessage-deflate; client_max_window_bits",
            "Sec-WebSocket-Key": "g0PDYtLWQOmaBE5upOBXew==",
            "Sec-WebSocket-Version": "13",
            "Upgrade": "websocket",
            "User-Agent": ua.random
        }
        self.WS_API = "wss://secure.ws.teneo.pro/websocket"
        self.proxies: List[str] = []
        self.proxy_index: int = 0
        self.account_proxies: Dict[str, str] = {}
        self.access_tokens: Dict[str, str] = {}

    @staticmethod
    def clear_terminal() -> None:
        os.system('cls' if os.name == 'nt' else 'clear')

    @staticmethod
    def log(message: str, color: str = StyleKit.INFO) -> None:
        timestamp = datetime.now().astimezone(wib).strftime('%Y-%m-%d %H:%M:%S')
        print(
            f"{StyleKit.GRAY}[{timestamp}]{StyleKit.RESET} {color}{message}{StyleKit.RESET}"
        )

    @staticmethod
    def section(title: str) -> None:
        print(StyleKit.box_sep())
        print(StyleKit.box_text(title, StyleKit.SUBHEADER))

    @staticmethod
    def welcome() -> None:
        print(StyleKit.box_line())
        print(StyleKit.box_text("🟧  Teneo-BOT Dashboard  🟧", StyleKit.HEADER))
        print(StyleKit.box_text("Original Author: vonssy", StyleKit.SUBHEADER))
        print(StyleKit.box_text("Developed by: zerosocialcode", StyleKit.PURPLE))
        print(StyleKit.box_sep())
        print(StyleKit.box_text("Secure, Modern, and Robust!", StyleKit.ORANGE))
        print(StyleKit.box_bottom())

    @staticmethod
    def format_seconds(seconds: int) -> str:
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"

    @staticmethod
    def mask_account(account: str) -> str:
        if "@" in account:
            local, domain = account.split('@', 1)
            masked = local[:3] + "***" + local[-3:]
            return f"{masked}@{domain}"
        return f"{account[:3]}***{account[-3:]}"

    def load_accounts(self, filename: str = "tokens.json") -> List[Dict[str, str]]:
        if not os.path.exists(filename):
            self.log(f"File {filename} Not Found.", StyleKit.ERR)
            return []
        try:
            with open(filename, "r") as file:
                data = json.load(file)
            if isinstance(data, list):
                return data
            self.log("Invalid tokens.json format. Should be a list of dicts.", StyleKit.ERR)
        except (json.JSONDecodeError, IOError) as e:
            self.log(f"Failed to load tokens.json: {e}", StyleKit.ERR)
        return []

    async def load_proxies(self, use_proxy_choice: int, filename: str = "proxy.txt") -> None:
        self.proxies = []
        try:
            if use_proxy_choice == 1:
                async with ClientSession(timeout=ClientTimeout(total=30)) as session:
                    async with session.get(
                        "https://api.proxyscrape.com/v4/free-proxy-list/get?request=display_proxies&proxy_format=protocolipport&format=text"
                    ) as response:
                        content = await response.text()
                with open(filename, "w") as f:
                    f.write(content)
                self.proxies = [line.strip() for line in content.splitlines() if line.strip()]
            else:
                if not os.path.exists(filename):
                    self.log(f"File {filename} Not Found.", StyleKit.ERR)
                    return
                with open(filename, "r") as f:
                    self.proxies = [line.strip() for line in f.read().splitlines() if line.strip()]

            if not self.proxies:
                self.log("No Proxies Found.", StyleKit.WARN)
            else:
                self.log(f"Loaded {len(self.proxies)} proxies.", StyleKit.OK)
        except Exception as e:
            self.log(f"Failed To Load Proxies: {e}", StyleKit.ERR)

    @staticmethod
    def check_proxy_schemes(proxy: str) -> str:
        schemes = ["http://", "https://", "socks4://", "socks5://"]
        if any(proxy.startswith(scheme) for scheme in schemes):
            return proxy
        return f"http://{proxy}"

    def get_next_proxy_for_account(self, email: str) -> Optional[str]:
        if not self.proxies:
            return None
        if email not in self.account_proxies:
            proxy = self.check_proxy_schemes(self.proxies[self.proxy_index])
            self.account_proxies[email] = proxy
            self.proxy_index = (self.proxy_index + 1) % len(self.proxies)
        return self.account_proxies[email]

    def rotate_proxy_for_account(self, email: str) -> Optional[str]:
        if not self.proxies:
            return None
        proxy = self.check_proxy_schemes(self.proxies[self.proxy_index])
        self.account_proxies[email] = proxy
        self.proxy_index = (self.proxy_index + 1) % len(self.proxies)
        return proxy

    def print_message(self, account: str, proxy: Optional[str], status: str, message: str) -> None:
        masked_email = self.mask_account(account)
        proxy_disp = proxy or "No Proxy"
        color = {
            "ok": StyleKit.OK,
            "warn": StyleKit.WARN,
            "err": StyleKit.ERR,
            "info": StyleKit.INFO,
        }.get(status, StyleKit.INFO)
        print(StyleKit.log_line(status.upper(), masked_email, proxy_disp, message, color))

    def print_question(self) -> Tuple[int, bool]:
        print(StyleKit.box_line())
        print(StyleKit.box_text("Proxy Usage:", StyleKit.ORANGE))
        print(StyleKit.box_text("1. Use Free Proxyscrape Proxy", StyleKit.WHITE))
        print(StyleKit.box_text("2. Use Private Proxy", StyleKit.WHITE))
        print(StyleKit.box_text("3. Run Without Proxy", StyleKit.WHITE))
        print(StyleKit.box_bottom())
        while True:
            try:
                choose = int(input(f"{StyleKit.ORANGE}Select [1/2/3]: {StyleKit.RESET}").strip())
                if choose in [1, 2, 3]:
                    break
                print(f"{StyleKit.ERR}Please enter either 1, 2 or 3.{StyleKit.RESET}")
            except ValueError:
                print(f"{StyleKit.ERR}Invalid input. Enter 1, 2 or 3.{StyleKit.RESET}")

        rotate = False
        if choose in [1, 2]:
            while True:
                rot = input(f"{StyleKit.ORANGE}Rotate Proxy on Fail? [y/n]: {StyleKit.RESET}").strip().lower()
                if rot in ["y", "n"]:
                    rotate = rot == "y"
                    break
                print(f"{StyleKit.ERR}Invalid input. Enter 'y' or 'n'.{StyleKit.RESET}")
        return choose, rotate

    async def connect_websocket(self, email: str, use_proxy: bool, rotate_proxy: bool) -> None:
        wss_url = f"{self.WS_API}?accessToken={self.access_tokens[email]}&version=v0.2"
        connected = False
        while True:
            proxy = self.get_next_proxy_for_account(email) if use_proxy else None
            connector = ProxyConnector.from_url(proxy) if proxy else None
            async with ClientSession(connector=connector, timeout=ClientTimeout(total=300)) as session:
                try:
                    async with session.ws_connect(wss_url, headers=self.WS_HEADERS) as wss:
                        async def send_heartbeat_message():
                            while True:
                                await asyncio.sleep(10)
                                await wss.send_json({"type": "PING"})
                                self.print_message(email, proxy, "info", "PING Sent")

                        if not connected:
                            self.print_message(email, proxy, "ok", "Websocket Connected")
                            connected = True
                            send_ping = asyncio.create_task(send_heartbeat_message())

                        while connected:
                            try:
                                response = await wss.receive_json()
                                msg = response.get("message", "")
                                today_point = response.get("pointsToday", 0)
                                total_point = response.get("pointsTotal", 0)
                                if msg == "Connected successfully":
                                    self.print_message(
                                        email, proxy, "ok",
                                        f"Connected | Today: {today_point} PTS | Total: {total_point} PTS"
                                    )
                                elif msg == "Pulse from server":
                                    heartbeat_today = response.get("heartbeats", 0)
                                    self.print_message(
                                        email, proxy, "info",
                                        f"Pulse | Today: {today_point} PTS | Heartbeats: {heartbeat_today}"
                                    )
                            except Exception as e:
                                self.print_message(
                                    email, proxy, "warn",
                                    f"Websocket Closed: {e}"
                                )
                                send_ping.cancel()
                                try:
                                    await send_ping
                                except asyncio.CancelledError:
                                    self.print_message(email, proxy, "warn", "PING Cancelled")
                                await asyncio.sleep(5)
                                connected = False
                                break

                except Exception as e:
                    self.print_message(
                        email, proxy, "err",
                        f"Websocket Not Connected: {e}"
                    )
                    if rotate_proxy and use_proxy:
                        self.rotate_proxy_for_account(email)
                    await asyncio.sleep(5)
                except asyncio.CancelledError:
                    self.print_message(email, proxy, "warn", "Websocket Closed")
                    break

    async def main(self) -> None:
        try:
            self.clear_terminal()
            self.welcome()
            tokens = self.load_accounts()
            if not tokens:
                self.log("No Accounts Loaded.", StyleKit.ERR)
                return

            use_proxy_choice, rotate_proxy = self.print_question()
            use_proxy = use_proxy_choice in [1, 2]

            if use_proxy:
                await self.load_proxies(use_proxy_choice)

            print(StyleKit.box_line())
            print(StyleKit.box_text("Accounts Loaded", StyleKit.HEADER))
            self.log(f"Loaded {len(tokens)} account(s).", StyleKit.OK)
            print(StyleKit.box_bottom())

            tasks = []
            for idx, token in enumerate(tokens, start=1):
                email = token.get("Email")
                access_token = token.get("accessToken")
                if not (email and access_token and "@" in email):
                    self.print_message(str(idx), "N/A", "err", "Invalid Account Data")
                    continue
                self.access_tokens[email] = access_token
                tasks.append(self.connect_websocket(email, use_proxy, rotate_proxy))

            await asyncio.gather(*tasks)
        except Exception as e:
            self.log(f"Error: {e}", StyleKit.ERR)
            raise

# --------------- SCRIPT ENTRY POINT ---------------
if __name__ == "__main__":
    try:
        bot = TeneoBot()
        asyncio.run(bot.main())
    except KeyboardInterrupt:
        timestamp = datetime.now().astimezone(wib).strftime('%Y-%m-%d %H:%M:%S')
        print(f"{StyleKit.GRAY}[{timestamp}]{StyleKit.RESET} {StyleKit.ERR}[EXIT] Teneo - BOT{StyleKit.RESET}")
